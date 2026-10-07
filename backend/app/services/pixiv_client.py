"""Unofficial client for pixiv's private mobile App API."""

from __future__ import annotations

import hashlib
import logging
import re
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

APP_API_BASE = "https://app-api.pixiv.net"
AUTH_URL = "https://oauth.secure.pixiv.net/auth/token"

# Mobile App API headers. These may change without notice.
APP_USER_AGENT = "PixivAndroidApp/5.90.0 (Android 9; Pixel 3)"
APP_VERSION = "5.90.0"
APP_OS = "android"
APP_OS_VERSION = "28"

IMAGE_REFERER = "https://app-api.pixiv.net/"
_api_lock = asyncio.Lock()
_last_api_request = 0.0
_image_download_slots = asyncio.Semaphore(8)

# /c/1920x1080/img-master/... から元サイズを復元
_SIZE_RE = re.compile(r"/c/(\d+)x(\d+)(?:_[^/]*)?/")


def is_configured() -> bool:
    return bool(settings.PIXIV_CLIENT_ID and settings.PIXIV_CLIENT_SECRET and settings.PIXIV_TOKEN_ENCRYPTION_KEY)


def _api_headers(access_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": APP_USER_AGENT,
        "App-OS": APP_OS,
        "App-OS-Version": APP_OS_VERSION,
        "App-Version": APP_VERSION,
    }


def _dimensions_from_url(url: str) -> Tuple[int, int]:
    """pixiv画像URLに埋め込まれたサイズ（例: /c/1920x1080/）から寸法を取得"""
    match = _SIZE_RE.search(url or "")
    if match:
        return int(match.group(1)), int(match.group(2))
    return 0, 0


def _list_result(data: Dict[str, Any]) -> Dict[str, Any]:
    body = data.get("body") if isinstance(data.get("body"), dict) else data
    return {"illusts": body.get("illusts") or [], "next_url": body.get("next_url")}


def _next_cursor(next_url: Optional[str], path: str, parameter: str) -> Optional[str]:
    """Accept only the expected Pixiv endpoint's numeric pagination cursor."""
    if not next_url:
        return None
    parsed = urlparse(next_url)
    if (parsed.scheme != "https" or parsed.hostname != "app-api.pixiv.net"
            or parsed.port or parsed.username or parsed.password or parsed.path != path):
        return None
    values = parse_qs(parsed.query).get(parameter, [])
    return values[0] if len(values) == 1 and values[0].isascii() and values[0].isdigit() else None


class PixivApiError(RuntimeError):
    """pixiv API がエラーを返した際の例外（UI へ理由をそのまま伝えるため message を保持）"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        pixiv_error: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.pixiv_error = pixiv_error


class PixivClient:
    """1つのpixivアクセストークンに対するAPIクライアント"""

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token

    # ------------------------------------------------------------------
    # Token exchange
    # ------------------------------------------------------------------
    @staticmethod
    async def _request_token(payload: Dict[str, Any]) -> Dict[str, Any]:
        """oauth.secure.pixiv.net のトークンエンドポイントを叩く"""
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                AUTH_URL,
                data=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": APP_USER_AGENT,
                },
            )

        if resp.status_code != 200:
            logger.warning("Pixiv token request failed: HTTP %s", resp.status_code)
            raise PixivApiError(
                "Pixivの認証に失敗しました。Refresh Tokenとサーバー設定を確認してください。",
                status_code=resp.status_code,
            )

        data = resp.json()
        if isinstance(data.get("response"), dict):
            data = data["response"]
        if not data.get("access_token"):
            raise PixivApiError("pixivからアクセストークンが返されませんでした。")
        return data

    @classmethod
    async def exchange_authorization_code(cls, code: str, verifier: str) -> Dict[str, Any]:
        """Exchange a browser-login PKCE code without exposing tokens to the browser."""
        if not is_configured():
            raise PixivApiError("Pixivの接続設定が不足しています。")
        data = await cls._request_token({
            "client_id": settings.PIXIV_CLIENT_ID,
            "client_secret": settings.PIXIV_CLIENT_SECRET,
            "code": code,
            "code_verifier": verifier,
            "grant_type": "authorization_code",
            "include_policy": "true",
            "redirect_uri": "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback",
        })
        if not data.get("refresh_token"):
            raise PixivApiError("PixivからRefresh Tokenが返されませんでした。")
        data["expires_at"] = datetime.utcnow() + timedelta(seconds=int(data.get("expires_in", 3600)))
        return data

    @classmethod
    async def refresh_access_token(cls, refresh_token: str) -> Dict[str, Any]:
        """リフレッシュトークンから新しいアクセストークンを取得する"""
        if not is_configured():
            raise PixivApiError("Pixivの接続設定が不足しています。")

        data = await cls._request_token({
            "get_secure_url": 1,
            "grant_type": "refresh_token",
            "client_id": settings.PIXIV_CLIENT_ID,
            "client_secret": settings.PIXIV_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "include_policy": "true",
        })

        data["refresh_token"] = data.get("refresh_token") or refresh_token
        data["expires_at"] = datetime.utcnow() + timedelta(
            seconds=int(data.get("expires_in", 3600))
        )
        return data

    # ------------------------------------------------------------------
    # 内部: GET 実行
    # ------------------------------------------------------------------
    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        if not self.access_token:
            raise PixivApiError("pixivのアクセストークンがありません。")

        url = path if path.startswith("http") else f"{APP_API_BASE}{path}"
        if urlparse(url).scheme != "https" or urlparse(url).hostname != "app-api.pixiv.net":
            raise PixivApiError("許可されていないPixiv API URLです。")
        global _last_api_request
        async with _api_lock:
            delay = 0.2 - (time.monotonic() - _last_api_request)
            if delay > 0:
                await asyncio.sleep(delay)
            _last_api_request = time.monotonic()
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, params=params, headers=_api_headers(self.access_token))

        if resp.status_code == 401:
            raise PixivApiError("pixivのアクセストークンが無効です。再接続してください。", 401)
        if resp.status_code >= 400:
            logger.warning("Pixiv API %s -> %s %s", url, resp.status_code, resp.text[:300])
            raise PixivApiError("pixiv APIエラーが発生しました。", resp.status_code)

        return resp.json()

    # ------------------------------------------------------------------
    # API エンドポイント
    # ------------------------------------------------------------------
    async def get_user_me(self) -> Dict[str, Any]:
        data = await self._get("/v1/user/me")
        return data.get("user") or data.get("response", {}).get("user") or {}

    async def search_illust(
        self,
        word: str,
        *,
        sort: str = "date_desc",
        duration: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search_target: str = "partial_match_for_tags",
        page: int = 1,
        per_page: int = 30,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "word": word,
            "search_target": search_target,
            "sort": sort,
            "filter": "for_ios",
            "page": max(1, page),
            "per_page": min(60, max(1, per_page)),
        }
        if duration:
            params["duration"] = duration
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        data = await self._get("/v1/search/illust", params)
        return _list_result(data)

    async def get_recommended_illusts(self, page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        data = await self._get(
            "/v1/illust/recommended",
            {
                "filter": "for_ios",
                "include_ranking_label": "true",
                "include_privacy_policy": "true",
                "page": page,
                "per_page": min(60, per_page),
            },
        )
        return _list_result(data)

    async def get_illust_ranking(
        self,
        mode: str = "daily",
        date: Optional[str] = None,
        page: int = 1,
        per_page: int = 30,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "mode": mode,
            "filter": "for_ios",
            "page": page,
            "per_page": min(60, per_page),
        }
        if date:
            params["date"] = date
        data = await self._get("/v1/illust/ranking", params)
        return _list_result(data)

    async def get_user_illusts(self, user_id: str, page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        data = await self._get(
            "/v1/user/illusts",
            {
                "user_id": user_id,
                "filter": "for_ios",
                "page": page,
                "per_page": min(60, per_page),
            },
        )
        return _list_result(data)

    async def get_user_bookmarks(
        self, user_id: str, restrict: str = "public", cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"user_id": user_id, "restrict": restrict, "filter": "for_ios"}
        if cursor:
            params["max_bookmark_id"] = cursor
        data = await self._get(
            "/v1/user/bookmarks/illust",
            params,
        )
        return _list_result(data)

    async def get_following_illusts(
        self,
        restrict: str = "public",
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"restrict": restrict}
        if cursor:
            params["offset"] = cursor
        data = await self._get(
            "/v2/illust/follow",
            params,
        )
        return _list_result(data)

    async def get_illust_detail(self, illust_id: str) -> Dict[str, Any]:
        data = await self._get("/v1/illust/detail", {"illust_id": str(illust_id)})
        return data.get("illust") or (data.get("body") or {}).get("illust") or {}

    async def get_illust_pages(self, illust_id: str, illust: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """複数ページ作品の各ページ画像URLを取得する"""
        illust = illust or await self.get_illust_detail(illust_id)
        page_count = int(illust.get("page_count") or 1)

        if page_count <= 1:
            original = illust.get("meta_single_page_original_image_url") or (
                (illust.get("image_urls") or {}).get("original")
            )
            return [{"image_url": original, "width": 0, "height": 0}] if original else []

        # Mobile App API returns multi-page URLs in the detail response.
        meta_pages = illust.get("meta_pages") or []
        if meta_pages:
            return [
                {
                    "image_url": p.get("image_urls", {}).get("original"),
                    "width": 0,
                    "height": 0,
                }
                for p in meta_pages
            ]

        original = (illust.get("image_urls") or {}).get("original")
        return [{"image_url": original, "width": 0, "height": 0}] if original else []

    # ------------------------------------------------------------------
    # 画像取得（Referer 必須のため必ずサーバーを経由する）
    # ------------------------------------------------------------------
    async def download_image(
        self,
        image_url: str,
        dest_dir: Path,
    ) -> Tuple[Optional[Path], Optional[str]]:
        """pixiv画像を取得して dest_dir に保存する。失敗時は (None, エラー理由) を返す。"""
        if not image_url:
            return None, "画像URLが空です。"

        url = image_url.replace(
            "https://i.pximg.net", f"https://{settings.PIXIV_IMAGE_HOST}"
        )
        cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        suffix = Path(urlparse(url).path).suffix or ".jpg"
        if suffix not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            suffix = ".jpg"

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{cache_key}{suffix}"

        if dest.exists() and dest.stat().st_size > 0:
            return dest, None

        try:
            # 一覧表示の大量リクエストで接続数とメモリ使用量が膨らまないよう制限。
            async with _image_download_slots:
                if dest.exists() and dest.stat().st_size > 0:
                    return dest, None
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    resp = await client.get(
                        url,
                        headers={"Referer": IMAGE_REFERER, "User-Agent": APP_USER_AGENT},
                    )
                if resp.status_code != 200:
                    return None, (
                        f"画像の取得に失敗しました（HTTP {resp.status_code}）。"
                        "R-18指定画像は取り込めません。"
                    )
                await asyncio.to_thread(dest.write_bytes, resp.content)
                return dest, None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to download pixiv image: %s", exc)
            return None, f"画像の取得に失敗しました: {exc}"


def normalize_illust(illust: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize private mobile API JSON for the frontend."""
    user = illust.get("user") or {}
    image_urls = illust.get("image_urls") or {}
    profile_urls = user.get("profile_image_urls") or {}

    tags: List[str] = []
    for tag in illust.get("tags") or []:
        name = tag.get("tag") or tag.get("translated_name") if isinstance(tag, dict) else str(tag)
        if name:
            tags.append(name)

    width, height = _dimensions_from_url(
        image_urls.get("original") or image_urls.get("large") or ""
    )

    create_date_iso = None
    create_date = illust.get("create_date")
    if create_date:
        try:
            create_date_iso = datetime.utcfromtimestamp(int(create_date)).isoformat()
        except (TypeError, ValueError, OSError):
            create_date_iso = str(create_date)

    return {
        "id": str(illust.get("id", "")),
        "title": illust.get("title") or "Untitled",
        "caption": illust.get("caption") or "",
        "author_name": user.get("name") or "Unknown",
        "author_id": str(user.get("id", "")),
        "author_account": user.get("account") or "",
        "author_avatar": (
            profile_urls.get("px_16x16") or profile_urls.get("px_50x50") or ""
        ),
        "image_url": (
            image_urls.get("large")
            or image_urls.get("medium")
            or image_urls.get("square_medium")
            or ""
        ),
        "original_url": image_urls.get("original") or image_urls.get("large") or "",
        "category": illust.get("type") or "illust",
        "tags": tags,
        "likes": int(illust.get("total_bookmarks") or 0),
        "view_likes": int(illust.get("total_view") or 0),
        "bookmarks": int(illust.get("total_bookmarks") or 0),
        "page_count": int(illust.get("page_count") or 1),
        "width": width,
        "height": height,
        "is_r18": bool(illust.get("x_restrict") or illust.get("y_restrict")),
        "create_date": create_date_iso,
        "source_url": f"https://www.pixiv.net/artworks/{illust.get('id', '')}",
    }
