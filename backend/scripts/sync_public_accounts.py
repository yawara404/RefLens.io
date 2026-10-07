#!/usr/bin/env python3
"""ローカル用DBのアカウントを、公開プレビュー用DBへ同期する。

背景:
    `./start.sh public` / `./start.sh deploy` は `DATABASE_URL` を
    `backend/reflens-public.db` に向け直して起動するため、公開サイトとローカルは
    別々のユーザー一覧を持つ。ローカルで作ったアカウントは公開側に無いため、
    公開サイトで「メールアドレスまたはパスワードが正しくありません」(401) になる。

    このスクリプトはローカルDBを正として、公開側に無いユーザーを追加し、
    既存ユーザーの表示名・パスワードハッシュを最新に合わせる。
    あわせて、そのユーザーの作業データ（ボード / フォルダ / メディア /
    キャンバス配置 / AI解析結果）と画像ファイルも移すので、
    ログイン直後から同じボードが開ける。

同期しないもの:
    - `pixiv_accounts` / `instagram_accounts` … アクセストークンを含み、
      公開プレビューでは ROOT_PATH 設定によりこれらの連携自体が無効化されている
      (PIXIV_SETUP.md「公開プレビューと安全性」)。
    - 共通ゲスト `creator@reflens.io` … 各DBが自分の初期データを持つ。
      ここで触ると公開側のデモデータが壊れる。

使い方:
    backend/venv/bin/python backend/scripts/sync_public_accounts.py
    SOURCE_DB=... TARGET_DB=... backend/venv/bin/python backend/scripts/sync_public_accounts.py

start.sh の public / deploy はバックエンド起動直後にこれを実行する。
何度実行しても安全（冪等・削除はしない）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE_DB = BACKEND_DIR / "reflens.db"
DEFAULT_TARGET_DB = BACKEND_DIR / "reflens-public.db"

GUEST_EMAIL = "creator@reflens.io"

# PK の重複チェックだけで追記するテーブル（作業データ）
SYNCED_TABLES = (
    "boards",
    "folders",
    "media_items",
    "canvas_items",
    "ai_analyses",
)

# ユーザーが公開側で作業できる最低条件。無ければ空のボードを1つ作る。
STARTER_BOARD = {
    "title": "My Reference Board",
    "description": "リファレンスボード。画像をドラッグ＆ドロップして始めましょう。",
    "background_theme": "dark-grid",
    "viewport_x": 100.0,
    "viewport_y": 100.0,
    "viewport_zoom": 1.0,
}


def table_info(conn: sqlite3.Connection, table: str) -> dict[str, dict]:
    """PRAGMA table_info を {列名: 属性} で返す。"""
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    # (cid, name, type, notnull, dflt_value, pk)
    return {r[1]: {"notnull": r[2], "pk": r[5]} for r in rows}


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return bool(
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
    )


def pk_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    info = table_info(conn, table)
    pks = [name for name, meta in info.items() if meta["pk"]]
    if pks:
        return pks
    # PK 無しのテーブルは全列キーにして「完全一致行が無ければ追加」にしないと
    # 毎回重複するため、ここでは扱わない（発生しない想定）
    raise RuntimeError(f"{table} に主キーがありません")


def create_schema_from(source: sqlite3.Connection, target_path: Path) -> None:
    """公開DBが未作成なら、ローカルDBのスキーマだけ複製して初期化する。"""
    statements = [
        row[0]
        for row in source.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"
            " AND type IN ('table', 'index')"
        )
        if row[0]
    ]
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target_path) as conn:
        for stmt in statements:
            conn.execute(stmt)
        conn.commit()
    print(f"  公開DBを作成しました: {target_path}")


def sync_users(source: sqlite3.Connection, target: sqlite3.Connection) -> list[str]:
    """ユーザーを移す。返り値は同期したユーザーID。ゲストは対象外。"""
    columns = ["id", "email", "username", "hashed_password", "avatar_url", "created_at", "updated_at"]
    rows = source.execute(
        f"SELECT {', '.join(columns)} FROM users WHERE email != ?", (GUEST_EMAIL,)
    ).fetchall()

    synced: list[str] = []
    for row in rows:
        user = dict(zip(columns, row))
        existing = target.execute(
            "SELECT id FROM users WHERE email = ?", (user["email"],)
        ).fetchone()
        if existing:
            # ローカルを正とする（パスワード変更・表示名変更を公開側へ反映）
            target.execute(
                "UPDATE users SET username = ?, hashed_password = ?, avatar_url = ?"
                " WHERE id = ?",
                (
                    user["username"],
                    user["hashed_password"],
                    user["avatar_url"],
                    existing[0],
                ),
            )
        else:
            target.execute(
                f"INSERT INTO users ({', '.join(columns)}) VALUES"
                f" ({', '.join('?' * len(columns))})",
                tuple(user[c] for c in columns),
            )
        synced.append(user["id"])

    target.commit()
    return synced


def sync_table(
    source: sqlite3.Connection,
    target: sqlite3.Connection,
    table: str,
    user_ids: list[str],
) -> int:
    """user_ids に属する行を、PK が無い場合だけ追加する。"""
    if not table_exists(target, table) or not user_ids:
        return 0

    src_cols = list(table_info(source, table))
    tgt_cols = list(table_info(target, table))
    common = [c for c in src_cols if c in tgt_cols]
    if not common:
        return 0

    pks = pk_columns(target, table)
    placeholders = ",".join("?" * len(user_ids))

    # ユーザーに直結する列が無ければ、ユーザー→ボード→メディアと辿って絞る
    if "user_id" in src_cols:
        where = f"WHERE user_id IN ({placeholders})"
    elif "board_id" in src_cols:
        where = (
            "WHERE board_id IN (SELECT id FROM boards"
            f" WHERE user_id IN ({placeholders}))"
        )
    elif "media_item_id" in src_cols:
        where = (
            "WHERE media_item_id IN (SELECT id FROM media_items"
            f" WHERE user_id IN ({placeholders}))"
        )
    else:
        return 0
    args: tuple = tuple(user_ids)

    src_rows = source.execute(
        f"SELECT {', '.join(common)} FROM '{table}' {where}", args
    ).fetchall()

    existing_keys = {
        tuple(r) for r in target.execute(f"SELECT {', '.join(pks)} FROM '{table}'")
    }
    common_pks = [c for c in pks if c in common]
    if len(common_pks) != len(pks):
        # PK の片方が無いテーブルは安全のためスキップ
        return 0

    idx = {c: i for i, c in enumerate(common)}
    added = 0
    for row in src_rows:
        key = tuple(row[idx[c]] for c in common_pks)
        if key in existing_keys:
            continue
        target.execute(
            f"INSERT INTO '{table}' ({', '.join(common)}) VALUES"
            f" ({', '.join('?' * len(common))})",
            tuple(row),
        )
        existing_keys.add(key)
        added += 1

    target.commit()
    return added


def seed_starter_board_if_empty(
    source: sqlite3.Connection, target: sqlite3.Connection, user_ids: list[str]
) -> int:
    """公開側でボードが1つも無いユーザーへ、空の初期ボードを作る。"""
    created = 0
    for user_id in user_ids:
        row = target.execute(
            "SELECT 1 FROM boards WHERE user_id = ? LIMIT 1", (user_id,)
        ).fetchone()
        if row:
            continue
        email = target.execute(
            "SELECT email FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not email:
            continue
        now = source.execute("SELECT datetime('now')").fetchone()[0]
        target.execute(
            "INSERT INTO boards (id, user_id, title, description, thumbnail_url,"
            " viewport_x, viewport_y, viewport_zoom, background_theme, is_public,"
            " created_at, updated_at)"
            " VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, 0, ?, ?)",
            (
                str(uuid.uuid4()),
                user_id,
                STARTER_BOARD["title"],
                STARTER_BOARD["description"],
                STARTER_BOARD["viewport_x"],
                STARTER_BOARD["viewport_y"],
                STARTER_BOARD["viewport_zoom"],
                STARTER_BOARD["background_theme"],
                now,
                now,
            ),
        )
        created += 1
    target.commit()
    return created


def sync_upload_files(
    source: sqlite3.Connection, target: sqlite3.Connection, user_ids: list[str]
) -> int:
    """同期したユーザーのメディアが指す画像ファイルを公開側の保存先へコピーする。"""
    src_dir = Path(os.environ.get("SOURCE_UPLOAD_DIR") or BACKEND_DIR / "uploads")
    dst_dir = Path(os.environ.get("UPLOAD_DIR") or BACKEND_DIR / "public-uploads")
    if not src_dir.is_dir() or not user_ids:
        return 0
    dst_dir.mkdir(parents=True, exist_ok=True)

    placeholders = ",".join("?" * len(user_ids))
    copied = 0
    seen: set[str] = set()
    for col in ("file_path", "thumbnail_path"):
        if not table_exists(source, "media_items"):
            continue
        rows = source.execute(
            f"SELECT DISTINCT {col} FROM media_items"
            f" WHERE {col} IS NOT NULL AND user_id IN ({placeholders})",
            tuple(user_ids),
        ).fetchall()
        for (value,) in rows:
            if not value or not value.startswith("/uploads/") or value in seen:
                continue
            seen.add(value)
            name = value[len("/uploads/"):]
            src_file = src_dir / name
            dst_file = dst_dir / name
            if dst_file.exists() or not src_file.is_file():
                continue
            shutil.copy2(src_file, dst_file)
            copied += 1
    return copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=os.environ.get("SOURCE_DB") or DEFAULT_SOURCE_DB)
    parser.add_argument("--target", default=os.environ.get("TARGET_DB") or DEFAULT_TARGET_DB)
    parser.add_argument(
        "--quiet", action="store_true", help="同期が何も無かったときは出力しない"
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    target_path = Path(args.target)
    if not source_path.is_file():
        print(f"ローカルDBがありません: {source_path}", file=sys.stderr)
        return 1

    with sqlite3.connect(source_path) as source:
        if not table_exists(source, "users"):
            print(f"ローカルDBに users テーブルがありません: {source_path}", file=sys.stderr)
            return 1
        if not target_path.is_file():
            create_schema_from(source, target_path)

        with sqlite3.connect(target_path) as target:
            # SQLite は暗黙にBEGINするが、明示して Nagle 的な部分更新を避ける
            target.isolation_level = None
            user_ids = sync_users(source, target)
            counts = {
                table: sync_table(source, target, table, user_ids)
                for table in SYNCED_TABLES
            }
            boards = seed_starter_board_if_empty(source, target, user_ids)
            files = sync_upload_files(source, target, user_ids)

    total = sum(counts.values()) + boards + files
    if args.quiet and total == 0:
        return 0
    print(f"公開DB同期: {target_path}")
    print(f"  ユーザー: {len(user_ids)} 件を確認")
    for table, count in counts.items():
        if count:
            print(f"  {table}: +{count}")
    if boards:
        print(f"  初期ボード: +{boards}")
    if files:
        print(f"  画像ファイル: +{files}")
    if total == 0:
        print("  変更なし（同期済み）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
