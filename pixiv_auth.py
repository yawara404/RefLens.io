#!/usr/bin/env python3
"""Obtain a pixiv App API refresh token with PKCE for local RefLens use.

Run from the project root: python3 pixiv_auth.py login
This helper never asks for a pixiv password or writes tokens to disk.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
import webbrowser


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / "backend" / ".env"
LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
USER_AGENT = "PixivAndroidApp/5.90.0 (Android 9; Pixel 3)"


def read_client_credentials() -> tuple[str, str]:
    """Read only the two required keys; environment variables take precedence."""
    values: dict[str, str] = {}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            key = key.strip().removeprefix("export ")
            if separator and key in {"PIXIV_CLIENT_ID", "PIXIV_CLIENT_SECRET"}:
                values[key] = value.strip().strip('"\'')
    client_id = os.environ.get("PIXIV_CLIENT_ID") or values.get("PIXIV_CLIENT_ID", "")
    client_secret = os.environ.get("PIXIV_CLIENT_SECRET") or values.get("PIXIV_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise ValueError(
            "PIXIV_CLIENT_ID と PIXIV_CLIENT_SECRET を backend/.env に設定してください。"
            " 詳細: PIXIV_SETUP.md"
        )
    return client_id, client_secret


def code_from_input(value: str) -> str:
    """Accept a callback URL or just its code, without including other query values."""
    value = value.strip()
    if value.startswith("https://"):
        parsed = urlparse(value)
        expected = urlparse(REDIRECT_URI)
        if parsed.scheme != expected.scheme or parsed.netloc != expected.netloc or parsed.path != expected.path:
            raise ValueError("PixivのApp APIコールバックURLではありません。")
        value = parse_qs(parsed.query).get("code", [""])[0]
    if not value or any(character.isspace() for character in value):
        raise ValueError("認可コードが空、または無効です。")
    return value


def exchange_code(code: str, verifier: str, client_id: str, client_secret: str) -> str:
    body = urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "include_policy": "true",
        "redirect_uri": REDIRECT_URI,
    }).encode("utf-8")
    request = Request(
        TOKEN_URL,
        data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(
            f"Pixivのトークン交換に失敗しました（HTTP {exc.code}）。"
            " コードは短時間で失効します。設定を確認し、最初からやり直してください。"
        ) from exc
    except URLError as exc:
        raise RuntimeError("Pixivに接続できませんでした。ネットワーク接続を確認してください。") from exc
    if isinstance(data.get("response"), dict):
        data = data["response"]
    refresh_token = data.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise RuntimeError("PixivからRefresh Tokenが返されませんでした。")
    return refresh_token


def login() -> None:
    client_id, client_secret = read_client_credentials()
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    login_url = LOGIN_URL + "?" + urlencode({
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "client": "pixiv-android",
    })
    print("Pixivのログインページを開きます。開かない場合は次のURLをブラウザで開いてください:")
    print(login_url)
    webbrowser.open(login_url)
    print("\n開発者ツールのNetworkで Preserve log を有効にし、callback? を検索してください。")
    print("ログイン後、app-api.pixiv.net/web/v1/users/auth/pixiv/callback のURL、")
    print("またはそのURLの code パラメータだけを貼り付けてください。")
    code = code_from_input(input("Callback URL または code: "))
    refresh_token = exchange_code(code, verifier, client_id, client_secret)
    print("\nRefresh Token（他人に見せないでください）:")
    print(refresh_token)
    print("\nローカルの /view → 『Pixivに接続』に貼り付けてください。")


def main() -> int:
    parser = argparse.ArgumentParser(description="RefLens用のPixiv Refresh Token取得補助")
    parser.add_argument("command", choices=["login"], help="PKCEログインを開始")
    args = parser.parse_args()
    try:
        if args.command == "login":
            login()
    except (ValueError, RuntimeError, KeyboardInterrupt, EOFError) as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
