"""Encrypt pixiv credentials before they enter the application database."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

PREFIX = "fernet:"


def _cipher() -> Fernet:
    if not settings.PIXIV_TOKEN_ENCRYPTION_KEY:
        raise RuntimeError("PIXIV_TOKEN_ENCRYPTION_KEY を backend/.env に設定してください。")
    try:
        return Fernet(settings.PIXIV_TOKEN_ENCRYPTION_KEY.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("PIXIV_TOKEN_ENCRYPTION_KEY が無効です。Fernetキーを設定してください。") from exc


def encrypt_token(value: str) -> str:
    return PREFIX + _cipher().encrypt(value.encode()).decode()


def decrypt_token(value: str) -> str:
    if not value.startswith(PREFIX):
        # Read old installations; the caller replaces these values with encrypted ones.
        return value
    try:
        return _cipher().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Pixivトークンを復号できません。設定した暗号化キーを確認してください。") from exc
