"""パスワードハッシュのユーティリティ。

passlib 1.7.4 は bcrypt 5.x の `hashpw` が 72 バイト超で例外を投げる挙動に
対応しておらず、バックエンド起動時の wrap-bug 検出で落ちる。そのため passlib を
介さず bcrypt ライブラリを直接使う。

さらに sha256 → base64 の前処理を挟む。bcrypt は入力 72 バイトで
打ち切られるため、前処理後の 44 バイト（base64(sha256)）なら
パスワード長に関係なく全バイトがハッシュ計算に含まれる。
"""

import base64
import hashlib

import bcrypt

# 12 rounds は開発機でも 100ms 程度。認証はこの回数だけなので十分強い。
BCRYPT_ROUNDS = 12


def _prepare(password: str) -> bytes:
    """bcrypt に渡す 72 バイト以内の表現へ正規化する。"""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    """平文パスワードをハッシュ文字列（$2b$...）に変換する。"""
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_password(password: str, hashed: str) -> bool:
    """平文と保存済みハッシュが一致するか判定する。"""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_prepare(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # ハッシュ文字列が壊れている / 想定外の形式の場合は「不一致」扱い
        return False