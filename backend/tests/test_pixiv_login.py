import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models.models import PixivAccount, User
from app.routers.auth import (
    GUEST_EMAIL, PixivLoginComplete, PixivLoginStart,
    _pixiv_code, complete_pixiv_login, start_pixiv_login,
)
from app.services.pixiv_client import PixivClient


class PixivLoginTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.guest = User(email=GUEST_EMAIL, username="Guest")
        self.db.add(self.guest)
        self.db.commit()
        self.config = patch.multiple(
            settings,
            ROOT_PATH="",
            PIXIV_CLIENT_ID="test-client",
            PIXIV_CLIENT_SECRET="test-secret",
            PIXIV_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )
        self.config.start()

    def tearDown(self):
        self.config.stop()
        self.db.close()
        self.engine.dispose()

    def test_callback_must_be_pixiv_domain(self):
        with self.assertRaises(HTTPException):
            _pixiv_code("https://example.com/callback?code=stolen")
        self.assertEqual(_pixiv_code("https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback?code=valid"), "valid")

    async def test_pixiv_login_creates_private_reflens_account(self):
        started = start_pixiv_login(PixivLoginStart(mode="login"), self.guest)
        token_data = {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "user": {"id": "12345", "name": "Artist", "account": "artist"},
        }
        with patch.object(PixivClient, "exchange_authorization_code", new_callable=AsyncMock, return_value=token_data):
            result = await complete_pixiv_login(
                PixivLoginComplete(state=started["state"], callback_url_or_code="a-code"), self.guest, self.db
            )
        account = self.db.query(PixivAccount).filter_by(pixiv_user_id="12345").one()
        self.assertNotEqual(account.user_id, self.guest.id)
        self.assertNotEqual(account.access_token, "access")
        self.assertEqual(result["user_id"], account.user_id)
        self.assertEqual(self.db.query(User).filter_by(id=account.user_id).one().username, "Artist")
        with self.assertRaises(HTTPException):
            await complete_pixiv_login(
                PixivLoginComplete(state=started["state"], callback_url_or_code="a-code"), self.guest, self.db
            )

    def test_guest_cannot_link_account(self):
        with self.assertRaises(HTTPException) as exc:
            start_pixiv_login(PixivLoginStart(mode="link"), self.guest)
        self.assertEqual(exc.exception.status_code, 401)

    async def test_link_uses_existing_reflens_account(self):
        member = User(email="member@example.com", username="Member")
        self.db.add(member)
        self.db.commit()
        started = start_pixiv_login(PixivLoginStart(mode="link"), member)
        token_data = {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "user": {"id": "67890", "name": "Artist"},
        }
        with patch.object(PixivClient, "exchange_authorization_code", new_callable=AsyncMock, return_value=token_data):
            result = await complete_pixiv_login(
                PixivLoginComplete(state=started["state"], callback_url_or_code="a-code"), member, self.db
            )
        self.assertEqual(result["user_id"], member.id)
        self.assertEqual(self.db.query(PixivAccount).filter_by(user_id=member.id).one().pixiv_user_id, "67890")


class PublicPreviewPixivTests(unittest.IsolatedAsyncioTestCase):
    """公開プレビュー（ROOT_PATH 設定時）で「Pixivでログイン」だけが使えること。

    Refresh Token を手で貼る接続（/pixiv/connect）は公開では 403 のまま維持し、
    Web ログイン（PKCE）だけで pixiv クライアントが使える状態を守る。
    """

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.guest = User(email=GUEST_EMAIL, username="Guest")
        self.member = User(email="member@example.com", username="Member")
        self.db.add_all([self.guest, self.member])
        self.db.commit()
        self.config = patch.multiple(
            settings,
            ROOT_PATH="/RefLens.io",
            PIXIV_CLIENT_ID="test-client",
            PIXIV_CLIENT_SECRET="test-secret",
            PIXIV_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode(),
        )
        self.config.start()

    def tearDown(self):
        self.config.stop()
        self.db.close()
        self.engine.dispose()

    async def test_web_login_is_available_on_public_preview(self):
        started = start_pixiv_login(PixivLoginStart(mode="login"), self.guest)
        self.assertTrue(started["login_url"].startswith("https://app-api.pixiv.net/web/v1/login?"))

        token_data = {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "user": {"id": "4242", "name": "Artist", "account": "artist"},
        }
        with patch.object(PixivClient, "exchange_authorization_code", new_callable=AsyncMock, return_value=token_data):
            result = await complete_pixiv_login(
                PixivLoginComplete(state=started["state"], callback_url_or_code="a-code"), self.guest, self.db
            )
        account = self.db.query(PixivAccount).filter_by(pixiv_user_id="4242").one()
        self.assertNotEqual(account.user_id, self.guest.id)
        self.assertEqual(result["user_id"], account.user_id)

    async def test_refresh_token_connect_stays_disabled_on_public_preview(self):
        from app.routers.pixiv import PixivConnectRequest, pixiv_connect

        with self.assertRaises(HTTPException) as exc:
            await pixiv_connect(PixivConnectRequest(refresh_token="a-refresh-token-value"), self.member, self.db)
        self.assertEqual(exc.exception.status_code, 403)

    def test_get_account_exposes_own_account_only(self):
        from app.routers.pixiv import _get_account

        account = PixivAccount(
            user_id=self.member.id, pixiv_user_id="4242", pixiv_username="Artist",
            access_token="encrypted-access", refresh_token="encrypted-refresh",
        )
        self.db.add(account)
        self.db.commit()

        # ログイン済みユーザーは公開プレビューでも自分の pixiv セッションを使える
        self.assertIsNotNone(_get_account(self.db, self.member))
        # 共通ゲストには絶対に渡さない
        self.assertIsNone(_get_account(self.db, self.guest))

    def test_status_reports_web_login_available_and_token_disabled(self):
        from app.routers.pixiv import pixiv_status

        status = pixiv_status(self.member, self.db)
        self.assertTrue(status["connect_available"])
        self.assertFalse(status["token_connect_available"])
        self.assertEqual(status["mode"], "auth_required")

    def test_me_reflects_pixiv_connection_on_public_preview(self):
        from app.routers.auth import get_me

        self.db.add(PixivAccount(
            user_id=self.member.id, pixiv_user_id="4242", pixiv_username="Artist",
            access_token="encrypted-access", refresh_token="encrypted-refresh",
        ))
        self.db.commit()
        self.db.refresh(self.member)
        me = get_me(self.member)
        self.assertTrue(me["pixiv_connected"])
        self.assertEqual(me["pixiv_username"], "Artist")


if __name__ == "__main__":
    unittest.main()
