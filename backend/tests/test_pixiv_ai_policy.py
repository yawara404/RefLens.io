"""pixiv AI解析ポリシーの現行仕様テスト。

現行実装（利用規約・プライバシーポリシーを実装へ合わせて統一）:
- AI解析はモデルの学習に使わない推論専用の情報解析で、取り込んだ作品はすべて対象。
- resolve_pixiv_ai_policy は、禁止表記の有無や外部サービスの掲載状況によらず
  常に "allowed" を返す。Danbooru への照会も行わない。
- classify_pixiv_ai_policy は禁止表記を検出する補助関数としてのみ残り、
  解析の実行可否には使わない。
"""

import unittest

from app.services.pixiv_ai_policy import classify_pixiv_ai_policy, resolve_pixiv_ai_policy


class PixivAiClassifyTests(unittest.TestCase):
    def test_explicit_japanese_tag_is_detected_as_blocked(self):
        self.assertEqual(
            classify_pixiv_ai_policy({"title": "作品", "tags": ["AI学習禁止"]}),
            "blocked",
        )

    def test_caption_and_english_statement_are_detected_as_blocked(self):
        self.assertEqual(
            classify_pixiv_ai_policy({"caption": "<p>Do not train AI on my work.</p>"}),
            "blocked",
        )

    def test_ai_generated_flag_is_not_a_training_prohibition(self):
        self.assertEqual(
            classify_pixiv_ai_policy({"title": "作品", "tags": ["AI生成作品"]}),
            "allowed",
        )

    def test_missing_metadata_classifies_as_allowed(self):
        # 現行の classify はメタデータが無い場合も "allowed" を返す。
        self.assertEqual(classify_pixiv_ai_policy(None), "allowed")


class PixivAiResolveTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_allows_artwork_with_id(self):
        self.assertEqual(
            await resolve_pixiv_ai_policy({"id": "12345", "title": "作品"}),
            "allowed",
        )

    async def test_resolve_allows_even_when_training_is_prohibited(self):
        # 禁止表記があっても、現行ポリシーでは解析を停止しない。
        self.assertEqual(
            await resolve_pixiv_ai_policy({"id": "12345", "tags": ["AI学習禁止"]}),
            "allowed",
        )

    async def test_resolve_allows_missing_metadata(self):
        self.assertEqual(await resolve_pixiv_ai_policy(None), "allowed")


if __name__ == "__main__":
    unittest.main()
