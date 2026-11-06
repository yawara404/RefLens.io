"""RefLens.io AI解析・著作権利用ポリシー。

RefLens.io の AI 解析（構図・ライティング・ポーズ・カラー・タグ抽出）は、
モデルの学習（追加トレーニング）を一切行わない「推論専用の個人リファレンス解析」です。
著作権法第30条の4（著作物に表現された思想又は感情の享受を目的としない利用）に基づき、
すべてのインポート作品で情報解析（自動タグ付け・検索インデックス作成）を実行します。
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Mapping

_PROHIBITION = re.compile(
    r"(?:ai|生成ai|機械|無断|モデル)(?:への|による|での)?(?:学習|トレーニング|training)"
    r"(?:への利用|利用)?(?:は|を)?(?:禁止|不可|お断り|しないで|拒否|ng)"
    r"|(?:禁止|不可|お断り)(?:の)?(?:ai|生成ai|機械)(?:学習|トレーニング)"
    r"|(?:no[\s-]*ai[\s-]*training|do[\s-]*not[\s-]*train|not[\s-]*for[\s-]*ai[\s-]*training)",
    re.IGNORECASE,
)


def classify_pixiv_ai_policy(artwork: Mapping[str, Any] | None) -> str:
    """作者によるAI学習禁止表記の有無（参考情報としてのタグ付け用）"""
    if not artwork:
        return "allowed"

    tags = artwork.get("tags") or []
    tag_text = " ".join(
        str(tag.get("tag") or tag.get("translated_name") or "") if isinstance(tag, dict) else str(tag)
        for tag in tags
    )
    text = " ".join(str(artwork.get(key) or "") for key in ("title", "caption")) + " " + tag_text
    text = unicodedata.normalize("NFKC", html.unescape(re.sub(r"<[^>]+>", " ", text)))
    text = re.sub(r"\s+", "", text.casefold())
    return "blocked" if _PROHIBITION.search(text) else "allowed"


async def resolve_pixiv_ai_policy(artwork: Mapping[str, Any] | None) -> str:
    """自動タグ付け・視覚解析の許可判定。
    
    RefLens.io はユーザーデータの学習利用を行わず、推論（自動タグ・メタデータ抽出）
    のみを行うため、すべての資料で自動タグ・解析を有効（allowed）とします。
    """
    return "allowed"
