import unittest
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.pixiv_tokens import decrypt_token, encrypt_token
from app.routers.pixiv import _filter_demo, _get_account
from app.services.pixiv_client import PixivClient, _list_result, _next_cursor


class PixivConnectionTests(unittest.IsolatedAsyncioTestCase):
    def test_token_is_encrypted_for_database(self):
        key = Fernet.generate_key().decode()
        with patch.object(settings, "PIXIV_TOKEN_ENCRYPTION_KEY", key):
            stored = encrypt_token("sensitive-refresh-token")
            self.assertNotIn("sensitive-refresh-token", stored)
            self.assertEqual(decrypt_token(stored), "sensitive-refresh-token")

    def test_mobile_api_top_level_list(self):
        self.assertEqual(
            _list_result({"illusts": [{"id": 123}], "next_url": "next"}),
            {"illusts": [{"id": 123}], "next_url": "next"},
        )

    def test_public_preview_never_reads_shared_guest_pixiv_account(self):
        from app.routers.auth import GUEST_EMAIL
        from app.models.models import User

        guest = User(email=GUEST_EMAIL, username="Guest")
        with patch.object(settings, "ROOT_PATH", "/RefLens.io"):
            # 共通ゲストは DB を触る前に None を返す（共有 pixiv セッションを渡さない）
            self.assertIsNone(_get_account(None, guest))

    def test_recommended_demo_feed_is_not_empty(self):
        self.assertTrue(_filter_demo("recommended", None, None))

    def test_pixiv_pagination_cursor_checks_endpoint(self):
        url = "https://app-api.pixiv.net/v1/user/bookmarks/illust?user_id=12&max_bookmark_id=345"
        self.assertEqual(_next_cursor(url, "/v1/user/bookmarks/illust", "max_bookmark_id"), "345")
        self.assertIsNone(_next_cursor(url, "/v2/illust/follow", "offset"))
        self.assertIsNone(_next_cursor("https://example.com/v1/user/bookmarks/illust?max_bookmark_id=345", "/v1/user/bookmarks/illust", "max_bookmark_id"))

    async def test_follow_and_bookmark_use_pixiv_app_endpoints(self):
        client = PixivClient("test-token")
        with patch.object(client, "_get", new_callable=AsyncMock, return_value={"illusts": [], "next_url": None}) as get:
            await client.get_following_illusts(cursor="30")
            get.assert_awaited_with("/v2/illust/follow", {"restrict": "public", "offset": "30"})
            await client.get_user_bookmarks("123", cursor="456")
            get.assert_awaited_with("/v1/user/bookmarks/illust", {
                "user_id": "123", "restrict": "public", "filter": "for_ios", "max_bookmark_id": "456",
            })

    async def test_refresh_keeps_token_if_pixiv_does_not_rotate_it(self):
        with patch.object(settings, "PIXIV_CLIENT_ID", "client"), patch.object(
            settings, "PIXIV_CLIENT_SECRET", "secret"
        ), patch.object(settings, "PIXIV_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode()), patch.object(
            PixivClient, "_request_token", return_value={"access_token": "new-access", "expires_in": 3600}
        ):
            result = await PixivClient.refresh_access_token("old-refresh")
        self.assertEqual(result["access_token"], "new-access")
        self.assertEqual(result["refresh_token"], "old-refresh")


if __name__ == "__main__":
    unittest.main()
