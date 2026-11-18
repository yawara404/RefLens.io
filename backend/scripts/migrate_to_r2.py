#!/usr/bin/env python3
"""既存のローカル保存画像（uploads / public-uploads 等）を Cloudflare R2 へ一括移行するスクリプト。

使い方:
    backend/venv/bin/python backend/scripts/migrate_to_r2.py --dry-run
    backend/venv/bin/python backend/scripts/migrate_to_r2.py
    backend/venv/bin/python backend/scripts/migrate_to_r2.py --delete-local
"""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import mimetypes
from pathlib import Path
import sqlite3
import sys
from typing import Dict, List, Optional, Tuple

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.services.storage import PROTECTED_SEED_PREFIX, storage  # noqa: E402

DEFAULT_SOURCE_DIRS = [
    BACKEND_DIR / "uploads",
    BACKEND_DIR / "public-uploads",
    BACKEND_DIR / "pixiv-local-uploads",
]

DEFAULT_DBS = [
    BACKEND_DIR / "reflens.db",
    BACKEND_DIR / "reflens-public.db",
    BACKEND_DIR / "reflens-pixiv-local.db",
]


def _md5_hex(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _remote_matches(client, key: str, source: Path) -> bool:
    """Verify bytes, including multipart objects whose ETag is not an MD5 digest."""
    response = client.get_object(Bucket=storage.bucket_name, Key=key)
    body = response["Body"]
    digest = hashlib.md5()
    size = 0
    try:
        for chunk in body.iter_chunks(chunk_size=65536):
            digest.update(chunk)
            size += len(chunk)
    finally:
        body.close()
    return size == source.stat().st_size and digest.hexdigest() == _md5_hex(source)


def _list_existing_r2_objects(prefix: str) -> Dict[str, int]:
    """R2 バケット内の {object_key: size} マップを取得する。"""
    client = storage._get_client()
    bucket = storage.bucket_name
    existing: Dict[str, int] = {}
    paginator = client.get_paginator("list_objects_v2")
    list_prefix = f"{prefix}/" if prefix else ""
    for page in paginator.paginate(Bucket=bucket, Prefix=list_prefix):
        for obj in page.get("Contents", []) or []:
            key = obj.get("Key")
            size = int(obj.get("Size") or 0)
            if key:
                existing[key] = size
    return existing


def _collect_local_files(dirs: List[Path]) -> Tuple[Dict[str, List[Path]], List[str]]:
    """複数ディレクトリからファイル名ごとにパスをまとめる。同名異内容があれば警告リストへ記録する。"""
    files_by_name: Dict[str, List[Path]] = {}
    hashes_by_name: Dict[str, str] = {}
    conflicts: List[str] = []

    for d in dirs:
        if not d.is_dir():
            continue
        for entry in sorted(d.rglob("*")):
            name = entry.relative_to(d).as_posix()
            if not entry.is_file() or entry.is_symlink() or any(part.startswith(".") for part in Path(name).parts):
                continue
            digest = _md5_hex(entry)
            if name in hashes_by_name and hashes_by_name[name] != digest:
                conflicts.append(
                    f"衝突: {name} の内容がディレクトリ間で異なります ({files_by_name[name][0]} vs {entry})"
                )
                continue
            hashes_by_name[name] = digest
            files_by_name.setdefault(name, []).append(entry)

    return files_by_name, conflicts


def _audit_databases(existing_r2_keys: Dict[str, int], files_by_name: Dict[str, List[Path]]) -> None:
    """各 SQLite DB の media_items.file_path が移行対象カバーされているか確認する。"""
    for db_path in DEFAULT_DBS:
        if not db_path.is_file():
            continue
        with closing(sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
            has_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='media_items'"
            ).fetchone()
            if not has_table:
                continue
            rows = conn.execute("SELECT DISTINCT file_path FROM media_items WHERE file_path IS NOT NULL").fetchall()
        missing: List[str] = []
        managed = 0
        for (fp,) in rows:
            try:
                rel = storage.extract_relative_path(fp)
            except ValueError:
                continue
            if not rel:
                continue
            managed += 1
            key = storage.to_object_key(rel)
            if key not in existing_r2_keys and rel not in files_by_name:
                missing.append(fp)
        print(f"  DB 監査 ({db_path.name}): 管理対象パス {managed} 件 / 未存在 {len(missing)} 件")
        for m in missing[:5]:
            print(f"    - 欠損: {m}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        action="append",
        dest="dirs",
        help="移行元ローカルディレクトリ（複数指定可。未指定時は uploads / public-uploads / pixiv-local-uploads）",
    )
    parser.add_argument("--dry-run", action="store_true", help="アップロードせず対象の一覧のみ表示")
    parser.add_argument(
        "--force",
        action="store_true",
        help="R2 上にオブジェクトが存在しても再アップロードする",
    )
    parser.add_argument(
        "--delete-local",
        action="store_true",
        help="R2 上の内容一致を検証した後にローカル側の実ファイルを削除する",
    )
    parser.add_argument(
        "--delete-seeds",
        action="store_true",
        help="--delete-local 指定時に seed_ref_* 画像もローカルから削除対象に含める",
    )
    args = parser.parse_args()

    if not storage.is_r2_configured:
        print(
            "エラー: Cloudflare R2 の設定が不足しています。\n"
            "backend/.env に以下を設定してから再度実行してください:\n"
            f"  R2_ACCOUNT_ID={settings.R2_ACCOUNT_ID or '<Cloudflare Account ID>'}\n"
            f"  R2_BUCKET_NAME={settings.R2_BUCKET_NAME or 'reflens-io'}\n"
            "  R2_ACCESS_KEY_ID=<R2 API Token Access Key ID>\n"
            "  R2_SECRET_ACCESS_KEY=<R2 API Token Secret Access Key>",
            file=sys.stderr,
        )
        return 1

    target_dirs = [Path(d) for d in args.dirs] if args.dirs else DEFAULT_SOURCE_DIRS
    files_by_name, conflicts = _collect_local_files(target_dirs)

    print(f"Cloudflare R2 バケット: {storage.bucket_name} (prefix={storage.key_prefix or '-'})")
    print(f"ローカル検出ファイル（ユニーク）: {len(files_by_name)} 件")
    if conflicts:
        print("エラー: 同名異内容ファイルが検出されました。衝突を解消してから再実行してください:")
        for c in conflicts:
            print(f"  {c}")
        return 1

    try:
        existing_r2 = _list_existing_r2_objects(storage.key_prefix)
    except Exception as exc:
        print(f"エラー: R2 バケット '{storage.bucket_name}' への接続に失敗しました: {exc}", file=sys.stderr)
        return 1

    print(f"R2 既存オブジェクト: {len(existing_r2)} 件")
    _audit_databases(existing_r2, files_by_name)

    uploaded = 0
    skipped = 0
    deleted_local = 0
    total_bytes = 0
    client = storage._get_client()

    for name, paths in sorted(files_by_name.items()):
        src = paths[0]
        size = src.stat().st_size
        key = storage.to_object_key(name)
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"

        already_synced = False
        if key in existing_r2 and not args.force:
            already_synced = existing_r2[key] == size and _remote_matches(client, key, src)
            if not already_synced:
                print(f"エラー: R2 とローカルの内容が異なります: {key}（上書きせず停止）", file=sys.stderr)
                return 1
        if already_synced:
            skipped += 1
        elif args.dry_run:
            print(f"  [DRY-RUN] upload {src} -> r2://{storage.bucket_name}/{key} ({size} bytes, {mime})")
            uploaded += 1
            total_bytes += size
        else:
            data = src.read_bytes()
            client.put_object(
                Bucket=storage.bucket_name,
                Key=key,
                Body=data,
                ContentType=mime,
            )
            if not _remote_matches(client, key, src):
                print(f"エラー: アップロード後の内容検証に失敗しました: {key}", file=sys.stderr)
                return 1
            existing_r2[key] = size
            uploaded += 1
            total_bytes += size
            print(f"  [OK] {name} -> r2://{storage.bucket_name}/{key} ({size} bytes)")

        if args.delete_local and not args.dry_run and existing_r2.get(key) == size:
            if not args.delete_seeds and name.startswith(PROTECTED_SEED_PREFIX):
                continue
            for p in paths:
                try:
                    p.unlink()
                    deleted_local += 1
                except OSError as exc:
                    print(f"  [WARN] ローカル削除失敗 {p}: {exc}", file=sys.stderr)

    print("\n完了サマリー:")
    print(f"  アップロード: {uploaded} 件 ({total_bytes / (1024 * 1024):.2f} MB)")
    print(f"  スキップ済み: {skipped} 件")
    if args.delete_local:
        print(f"  ローカル削除: {deleted_local} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
