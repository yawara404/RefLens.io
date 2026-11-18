"""
RefLens.io オブジェクトストレージ抽象化サービス（Cloudflare R2 / ローカルフォールバック）。

設計方針:
- `STORAGE_BACKEND=auto`（既定）のとき、R2 認証情報が揃っていれば Cloudflare R2 (S3 互換 API) を
  プライマリストレージとして使用し、未設定時はローカルディスク (`settings.UPLOAD_DIR`) を使用する。
- DB 内の `file_path` は互換性のため `/uploads/{filename}` を基本とし（`R2_PUBLIC_URL` が
  設定された場合のみ公開 URL を付与可能）、配信ルート `GET /uploads/{path}` がローカル未存在時に
  透過的に R2 から取得して返却する。
- AI 解析（Ollama / Gemini / heuristic）・色彩抽出・視覚検索などローカルファイルパスまたは
  バイト列を必要とする処理も、`local_file_path()` / `get_bytes()` 経由で R2 から透過的に取得できる。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime
import io
import logging
import mimetypes
import os
from pathlib import Path
import tempfile
import threading
from typing import Any, Dict, Iterator, Optional, Tuple, Union
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# 初期シード画像（フォールバック等で共有参照され得るため削除から保護する）
PROTECTED_SEED_PREFIX = "seed_ref_"

_PIL_FORMAT_MAP: Dict[str, Tuple[str, str]] = {
    "JPEG": (".jpg", "image/jpeg"),
    "JPG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
    "GIF": (".gif", "image/gif"),
}

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@dataclass(frozen=True)
class ImageMetadata:
    width: int
    height: int
    aspect_ratio: float
    extension: str
    mime_type: str


@dataclass
class DeliveryObject:
    """HTTP 配信用のストレージオブジェクト表現。"""

    content_type: str
    content_length: Optional[int] = None
    etag: Optional[str] = None
    last_modified: Optional[datetime] = None
    local_path: Optional[Path] = None
    stream_body: Any = None


def inspect_image_bytes(
    data: bytes,
    fallback_ext: str = ".jpg",
    fallback_mime: Optional[str] = None,
) -> ImageMetadata:
    """メモリ上の画像バイト列から解像度・アスペクト比・拡張子・MIMEタイプを安全に取得する。"""
    clean_ext = fallback_ext.lower()
    if clean_ext not in _ALLOWED_EXTENSIONS:
        clean_ext = ".jpg"

    w, h = 400, 400
    ext = clean_ext
    mime = fallback_mime or mimetypes.guess_type(f"image{clean_ext}")[0] or "image/jpeg"

    try:
        with Image.open(io.BytesIO(data)) as img:
            w, h = img.size
            fmt = (img.format or "").upper()
            if fmt in _PIL_FORMAT_MAP:
                ext, detected_mime = _PIL_FORMAT_MAP[fmt]
                mime = detected_mime
    except Exception:
        pass

    aspect_ratio = float(w) / float(h) if h > 0 else 1.0
    return ImageMetadata(
        width=w,
        height=h,
        aspect_ratio=aspect_ratio,
        extension=ext,
        mime_type=mime,
    )


def compute_canvas_dimensions(
    width: int,
    height: int,
    max_dim: float = 360.0,
) -> Tuple[float, float]:
    """キャンバス初期配置時の幅・高さを算出する（長辺を max_dim に揃える）。"""
    if width <= 0 or height <= 0:
        return max_dim, max_dim
    aspect_ratio = float(width) / float(height)
    if width >= height:
        return max_dim, max_dim / aspect_ratio
    return max_dim * aspect_ratio, max_dim


def _is_not_found_error(exc: ClientError) -> bool:
    err = exc.response.get("Error", {}) if isinstance(exc.response, dict) else {}
    code = str(err.get("Code") or "")
    status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") if isinstance(exc.response, dict) else None
    return code in {"NoSuchKey", "404", "NotFound"} or status == 404


class MediaStorageService:
    """Cloudflare R2 とローカルファイルシステムを統一的に扱うストレージマネージャ。"""

    def __init__(self) -> None:
        self._client_lock = threading.Lock()
        self._client: Any = None
        self._client_signature: Optional[Tuple[str, str, str]] = None

    # ------------------------------------------------------------------
    # 動的設定プロパティ（テストでの patch.object(settings, ...) にも即追従）
    # ------------------------------------------------------------------
    @property
    def is_r2_configured(self) -> bool:
        has_endpoint = bool((settings.R2_ENDPOINT_URL or "").strip() or (settings.R2_ACCOUNT_ID or "").strip())
        return bool(
            has_endpoint
            and (settings.R2_BUCKET_NAME or "").strip()
            and (settings.R2_ACCESS_KEY_ID or "").strip()
            and (settings.R2_SECRET_ACCESS_KEY or "").strip()
        )

    @property
    def mode(self) -> str:
        configured = (settings.STORAGE_BACKEND or "auto").strip().lower()
        if configured == "local":
            return "local"
        if configured == "r2":
            if not self.is_r2_configured:
                raise RuntimeError(
                    "STORAGE_BACKEND=r2 に設定されていますが、R2_ACCOUNT_ID / R2_BUCKET_NAME / "
                    "R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY のいずれかが未設定です。"
                )
            return "r2"
        return "r2" if self.is_r2_configured else "local"

    @property
    def is_r2_active(self) -> bool:
        return self.mode == "r2"

    @property
    def endpoint_url(self) -> str:
        explicit = (settings.R2_ENDPOINT_URL or "").strip()
        if explicit:
            return explicit.rstrip("/")
        account_id = (settings.R2_ACCOUNT_ID or "").strip()
        return f"https://{account_id}.r2.cloudflarestorage.com"

    @property
    def bucket_name(self) -> str:
        return (settings.R2_BUCKET_NAME or "").strip()

    @property
    def key_prefix(self) -> str:
        return (settings.R2_KEY_PREFIX or "uploads").strip().strip("/")

    @property
    def public_url_base(self) -> str:
        return (settings.R2_PUBLIC_URL or "").strip().rstrip("/")

    # ------------------------------------------------------------------
    # S3 クライアント
    # ------------------------------------------------------------------
    def _get_client(self) -> Any:
        signature = (
            self.endpoint_url,
            (settings.R2_ACCESS_KEY_ID or "").strip(),
            (settings.R2_SECRET_ACCESS_KEY or "").strip(),
        )
        with self._client_lock:
            if self._client is not None and self._client_signature == signature:
                return self._client

            self._client = boto3.client(
                service_name="s3",
                endpoint_url=signature[0],
                aws_access_key_id=signature[1],
                aws_secret_access_key=signature[2],
                region_name="auto",
                config=Config(
                    signature_version="s3v4",
                    # botocore 新バージョンの自動チェックサム付与による S3 互換エンドポイント不整合を防止
                    request_checksum_calculation="when_required",
                    response_checksum_validation="when_required",
                    retries={"max_attempts": 3, "mode": "standard"},
                    connect_timeout=10,
                    read_timeout=30,
                ),
            )
            self._client_signature = signature
            return self._client

    # ------------------------------------------------------------------
    # パス正規化 & サニタイズ
    # ------------------------------------------------------------------
    def extract_relative_path(self, raw_path: Optional[str]) -> Optional[str]:
        """DB 値や URL から管理対象ファイル（uploads 配下）の相対パスを取り出す。

        外部の Hotlink URL（https://images.unsplash.com/... など）は None を返す。
        パストラバーサル（.. 等）を含む不正なパスには ValueError を送出する。
        """
        if not raw_path:
            return None

        text = str(raw_path).strip()
        if not text:
            return None

        if "\x00" in text or "\\" in text:
            raise ValueError("Invalid storage path character")

        # HTTP(S) URL の場合: R2_PUBLIC_URL 配下のみ管理対象として受け入れる
        if text.startswith("http://") or text.startswith("https://"):
            pub_base = self.public_url_base
            if not pub_base or not text.startswith(f"{pub_base}/"):
                return None
            rel_candidate = urlparse(text[len(pub_base) :]).path
        else:
            parsed_path = urlparse(text).path
            if not parsed_path:
                return None
            # サブパス運用時（ROOT_PATH=/RefLens.io など）の先頭接頭辞を剥ぐ
            root_prefix = (settings.ROOT_PATH or "").strip().rstrip("/")
            if root_prefix and parsed_path.startswith(f"{root_prefix}/"):
                parsed_path = parsed_path[len(root_prefix) :]
            rel_candidate = parsed_path

        rel_candidate = rel_candidate.lstrip("/")
        prefix = self.key_prefix

        # "/uploads/..." や "{key_prefix}/..." を剥いで純粋な相対パスへ統一
        if prefix and rel_candidate.startswith(f"{prefix}/"):
            rel_candidate = rel_candidate[len(prefix) + 1 :]
        elif rel_candidate.startswith("uploads/"):
            rel_candidate = rel_candidate[len("uploads/") :]
        elif rel_candidate == "uploads" or (prefix and rel_candidate == prefix):
            return None

        if not rel_candidate:
            return None

        parts = [p for p in rel_candidate.split("/") if p != ""]
        if not parts or any(p in (".", "..") for p in parts):
            raise ValueError(f"Unsafe storage path: {raw_path}")

        normalized = "/".join(parts)
        # 解決結果が UPLOAD_DIR の外へ出ないことを二重確認
        self._safe_local_path(normalized)
        return normalized

    def _safe_local_path(self, relative_path: str) -> Path:
        base_dir = settings.UPLOAD_DIR.resolve()
        candidate = (base_dir / relative_path).resolve()
        if candidate == base_dir or base_dir not in candidate.parents:
            raise ValueError(f"Path escapes storage root: {relative_path}")
        return candidate

    def to_object_key(self, file_path_or_name: str) -> str:
        rel = self.extract_relative_path(file_path_or_name)
        if not rel:
            raise ValueError(f"Not a managed storage path: {file_path_or_name}")
        prefix = self.key_prefix
        return f"{prefix}/{rel}" if prefix else rel

    def file_path_for(self, filename: str) -> str:
        """DB に保存するべき file_path（公開 URL または /uploads/...）を返す。"""
        rel = self.extract_relative_path(filename)
        if not rel:
            raise ValueError(f"Invalid filename: {filename}")
        if self.is_r2_active and self.public_url_base:
            key = self.to_object_key(rel)
            return f"{self.public_url_base}/{key}"
        return f"/uploads/{rel}"

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------
    @staticmethod
    def _write_local_atomic(dest: Path, data: bytes) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".tmp_", dir=str(dest.parent))
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp_name, dest)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def save_bytes_sync(
        self,
        filename: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> str:
        rel = self.extract_relative_path(filename)
        if not rel:
            raise ValueError(f"Invalid target filename: {filename}")

        mime = content_type or mimetypes.guess_type(rel)[0] or "application/octet-stream"
        local_dest = self._safe_local_path(rel)

        if self.is_r2_active:
            key = self.to_object_key(rel)
            try:
                self._get_client().put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=data,
                    ContentType=mime,
                )
            except (ClientError, BotoCoreError) as exc:
                logger.error("Failed to upload object %s to R2 bucket %s: %s", key, self.bucket_name, exc)
                raise RuntimeError(f"Cloudflare R2 への保存に失敗しました: {exc}") from exc

            if settings.R2_LOCAL_CACHE:
                self._write_local_atomic(local_dest, data)
        else:
            self._write_local_atomic(local_dest, data)

        return self.file_path_for(rel)

    async def save_bytes(
        self,
        filename: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> str:
        return await asyncio.to_thread(self.save_bytes_sync, filename, data, content_type)

    async def save_file(
        self,
        filename: str,
        src_path: Path,
        content_type: Optional[str] = None,
        remove_source: bool = False,
    ) -> str:
        data = await asyncio.to_thread(src_path.read_bytes)
        result_path = await self.save_bytes(filename, data, content_type=content_type)
        if remove_source:
            try:
                src_path.unlink(missing_ok=True)
            except OSError:
                pass
        return result_path

    # ------------------------------------------------------------------
    # 読み出し / 配信
    # ------------------------------------------------------------------
    def get_bytes_sync(self, file_path_or_name: Optional[str]) -> Optional[bytes]:
        rel = self.extract_relative_path(file_path_or_name)
        if not rel:
            return None

        local_dest = self._safe_local_path(rel)
        if local_dest.is_file():
            return local_dest.read_bytes()

        if self.is_r2_active:
            key = self.to_object_key(rel)
            try:
                resp = self._get_client().get_object(Bucket=self.bucket_name, Key=key)
                body = resp["Body"]
                try:
                    data = body.read()
                finally:
                    body.close()
                if settings.R2_LOCAL_CACHE:
                    try:
                        self._write_local_atomic(local_dest, data)
                    except OSError:
                        pass
                return data
            except ClientError as exc:
                if _is_not_found_error(exc):
                    return None
                logger.warning("Failed to read object %s from R2: %s", key, exc)
                return None
            except BotoCoreError as exc:
                logger.warning("R2 connection error reading %s: %s", key, exc)
                return None

        return None

    async def get_bytes(self, file_path_or_name: Optional[str]) -> Optional[bytes]:
        return await asyncio.to_thread(self.get_bytes_sync, file_path_or_name)

    def get_delivery_sync(
        self,
        file_path_or_name: str,
        *,
        head_only: bool = False,
    ) -> Optional[DeliveryObject]:
        """HTTP 配信用のローカルファイルまたは R2 ストリーム情報を取得する。"""
        rel = self.extract_relative_path(file_path_or_name)
        if not rel:
            return None

        local_dest = self._safe_local_path(rel)
        if local_dest.is_file():
            stat = local_dest.stat()
            mime = mimetypes.guess_type(local_dest.name)[0] or "application/octet-stream"
            return DeliveryObject(
                content_type=mime,
                content_length=stat.st_size,
                local_path=local_dest,
            )

        if self.is_r2_active:
            key = self.to_object_key(rel)
            client = self._get_client()
            try:
                if head_only:
                    resp = client.head_object(Bucket=self.bucket_name, Key=key)
                    return DeliveryObject(
                        content_type=resp.get("ContentType") or mimetypes.guess_type(rel)[0] or "application/octet-stream",
                        content_length=resp.get("ContentLength"),
                        etag=resp.get("ETag"),
                        last_modified=resp.get("LastModified"),
                    )
                resp = client.get_object(Bucket=self.bucket_name, Key=key)
                return DeliveryObject(
                    content_type=resp.get("ContentType") or mimetypes.guess_type(rel)[0] or "application/octet-stream",
                    content_length=resp.get("ContentLength"),
                    etag=resp.get("ETag"),
                    last_modified=resp.get("LastModified"),
                    stream_body=resp["Body"],
                )
            except ClientError as exc:
                if _is_not_found_error(exc):
                    return None
                logger.warning("R2 delivery error for %s: %s", key, exc)
                return None
            except BotoCoreError as exc:
                logger.warning("R2 connection error during delivery of %s: %s", key, exc)
                return None

        return None

    async def get_delivery(
        self,
        file_path_or_name: str,
        *,
        head_only: bool = False,
    ) -> Optional[DeliveryObject]:
        return await asyncio.to_thread(self.get_delivery_sync, file_path_or_name, head_only=head_only)

    def exists_sync(self, file_path_or_name: Optional[str]) -> bool:
        rel = self.extract_relative_path(file_path_or_name)
        if not rel:
            return False

        local_dest = self._safe_local_path(rel)
        if local_dest.is_file():
            return True

        if self.is_r2_active:
            key = self.to_object_key(rel)
            try:
                self._get_client().head_object(Bucket=self.bucket_name, Key=key)
                return True
            except ClientError as exc:
                if _is_not_found_error(exc):
                    return False
                logger.warning("R2 head_object error for %s: %s", key, exc)
                return False
            except BotoCoreError as exc:
                logger.warning("R2 connection error checking %s: %s", key, exc)
                return False

        return False

    async def exists(self, file_path_or_name: Optional[str]) -> bool:
        return await asyncio.to_thread(self.exists_sync, file_path_or_name)

    def delete_sync(self, file_path_or_name: Optional[str], *, protect_seed: bool = True) -> bool:
        rel = self.extract_relative_path(file_path_or_name)
        if not rel:
            return False

        if protect_seed and Path(rel).name.startswith(PROTECTED_SEED_PREFIX):
            return False

        deleted = False
        if self.is_r2_active:
            key = self.to_object_key(rel)
            try:
                self._get_client().delete_object(Bucket=self.bucket_name, Key=key)
                deleted = True
            except (ClientError, BotoCoreError) as exc:
                logger.warning("Failed to delete R2 object %s: %s", key, exc)

        local_dest = self._safe_local_path(rel)
        if local_dest.is_file():
            try:
                local_dest.unlink()
                deleted = True
            except OSError as exc:
                logger.warning("Failed to delete local file %s: %s", local_dest, exc)

        return deleted

    async def delete(self, file_path_or_name: Optional[str], *, protect_seed: bool = True) -> bool:
        return await asyncio.to_thread(self.delete_sync, file_path_or_name, protect_seed=protect_seed)

    # ------------------------------------------------------------------
    # 一時ローカルパス確保（Pillow / Ollama / Gemini 等向け）
    # ------------------------------------------------------------------
    @contextmanager
    def local_file_path(self, file_path_or_name: Optional[Union[str, Path]]) -> Iterator[Optional[Path]]:
        """ローカルキャッシュまたは R2 から取得した実ファイルパスをコンテキスト内で提供する。"""
        if file_path_or_name is None:
            yield None
            return

        if isinstance(file_path_or_name, Path):
            if file_path_or_name.is_file():
                yield file_path_or_name
                return
            raw_str = str(file_path_or_name)
        else:
            raw_str = str(file_path_or_name).strip()

        if not raw_str:
            yield None
            return

        # 管理パスでない既存の絶対/相対ファイル（例: /tmp/crop_xxx.jpg 等）が渡された場合
        if not raw_str.startswith("/uploads/") and not raw_str.startswith("http"):
            direct = Path(raw_str)
            if direct.is_file():
                yield direct
                return

        rel = self.extract_relative_path(raw_str)
        if not rel:
            yield None
            return

        local_dest = self._safe_local_path(rel)
        if local_dest.is_file():
            yield local_dest
            return

        data = self.get_bytes_sync(rel)
        if data is None:
            yield None
            return

        if settings.R2_LOCAL_CACHE and local_dest.is_file():
            yield local_dest
            return

        suffix = Path(rel).suffix or ".jpg"
        fd, tmp_name = tempfile.mkstemp(prefix="reflens_r2_", suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            yield Path(tmp_name)
        finally:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass

    @asynccontextmanager
    async def async_local_file_path(self, file_path_or_name: Optional[Union[str, Path]]):
        """Download and clean up temporary images without blocking API requests."""
        context = self.local_file_path(file_path_or_name)
        path = await asyncio.to_thread(context.__enter__)
        try:
            yield path
        finally:
            await asyncio.to_thread(context.__exit__, None, None, None)

    # ------------------------------------------------------------------
    # ステータス・接続診断
    # ------------------------------------------------------------------
    def describe_status(self, verify_remote: bool = False) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "backend": self.mode,
            "r2_configured": self.is_r2_configured,
            "bucket": self.bucket_name or None,
            "prefix": self.key_prefix,
            "public_url": self.public_url_base or None,
            "local_cache": bool(settings.R2_LOCAL_CACHE),
        }
        if verify_remote and self.is_r2_active:
            try:
                self._get_client().head_bucket(Bucket=self.bucket_name)
                info["r2_reachable"] = True
            except (ClientError, BotoCoreError) as exc:
                info["r2_reachable"] = False
                info["r2_error"] = str(exc)
        return info


storage = MediaStorageService()
