import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.routers.media import perform_ai_analysis
from app.services.pixiv_ai_policy import classify_pixiv_ai_policy, resolve_pixiv_ai_policy


class PixivAiPolicyTests(unittest.TestCase):
    def test_explicit_japanese_tag_blocks_analysis(self):
        self.assertEqual(
            classify_pixiv_ai_policy({"title": "作品", "tags": ["AI学習禁止"]}),
            "blocked",
        )

    def test_caption_and_english_statement_block_analysis(self):
        self.assertEqual(
            classify_pixiv_ai_policy({"caption": "<p>Do not train AI on my work.</p>"}),
            "blocked",
        )

    def test_ai_generated_flag_is_not_training_permission(self):
        self.assertEqual(
            classify_pixiv_ai_policy({"title": "作品", "tags": ["AI生成作品"]}),
            "allowed",
        )

    def test_missing_metadata_is_unknown(self):
        self.assertEqual(classify_pixiv_ai_policy(None), "unknown")


class PixivAiAnalysisGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocked_pixiv_never_reaches_vision_model(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            source_type="pixiv", ai_analysis_policy="blocked"
        )
        with patch("app.routers.media.analyze_image_with_vision", new_callable=AsyncMock) as analyze:
            await perform_ai_analysis("media-id", "/unused.jpg", lambda: db)
            analyze.assert_not_awaited()


class PixivDanbooruResolutionTests(unittest.IsolatedAsyncioTestCase):
    async def _resolve_with_response(self, status: int, payload):
        def respond(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.params["tags"], "pixiv_id:12345")
            return httpx.Response(status, json=payload)

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch("app.services.pixiv_ai_policy.httpx.AsyncClient", return_value=client):
            return await resolve_pixiv_ai_policy({"id": "12345", "title": "作品"})

    async def test_exact_pixiv_id_match_allows_analysis(self):
        self.assertEqual(await self._resolve_with_response(200, [{"id": 88}]), "allowed")

    async def test_absent_danbooru_post_does_not_allow_analysis(self):
        self.assertEqual(await self._resolve_with_response(200, []), "unlisted")

    async def test_danbooru_error_fails_closed(self):
        self.assertEqual(await self._resolve_with_response(429, {"error": "rate limited"}), "unknown")

    async def test_explicit_pixiv_ban_skips_danbooru(self):
        with patch("app.services.pixiv_ai_policy.httpx.AsyncClient") as client:
            policy = await resolve_pixiv_ai_policy({"id": "12345", "tags": ["AI学習禁止"]})
            client.assert_not_called()
        self.assertEqual(policy, "blocked")
