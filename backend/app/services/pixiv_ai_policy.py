"""Author-declared AI-use restrictions for imported pixiv artworks.

pixiv's AI-generated-work setting is not an AI-training permission flag. This
module only reads explicit author statements; missing metadata stays unknown.
"""

import html
import re
import unicodedata
from typing import Any, Mapping

import httpx


_PROHIBITION = re.compile(
    r"(?:ai|生成ai|機械|無断|モデル)(?:への|による|での)?(?:学習|トレーニング|training)"
    r"(?:への利用|利用)?(?:は|を)?(?:禁止|不可|お断り|しないで|拒否|ng)"
    r"|(?:禁止|不可|お断り)(?:の)?(?:ai|生成ai|機械)(?:学習|トレーニング)"
    r"|(?:no[\s-]*ai[\s-]*training|do[\s-]*not[\s-]*train|not[\s-]*for[\s-]*ai[\s-]*training)",
    re.IGNORECASE,
)


def classify_pixiv_ai_policy(artwork: Mapping[str, Any] | None) -> str:
    """Return blocked / allowed / unknown from the artwork's own metadata.

    ``allowed`` here means only that no prohibition text was found; the
    Danbooru cross-post check is performed separately before AI analysis.
    """
    if not artwork:
        return "unknown"

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
    """Permit AI analysis only for unprohibited art with an exact Danbooru pixiv_id match."""
    author_policy = classify_pixiv_ai_policy(artwork)
    if author_policy != "allowed":
        return author_policy

    illust_id = str(artwork.get("id") or "") if artwork else ""
    if not re.fullmatch(r"[0-9]{1,20}", illust_id):
        return "unknown"

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(
                "https://danbooru.donmai.us/posts.json",
                params={"tags": f"pixiv_id:{illust_id}", "limit": 1},
                headers={"User-Agent": "RefLens/1.0 (pixiv AI policy check)"},
            )
        response.raise_for_status()
        posts = response.json()
        if not isinstance(posts, list):
            return "unknown"
        return "allowed" if any(isinstance(post, dict) and post.get("id") for post in posts) else "unlisted"
    except (httpx.HTTPError, ValueError):
        return "unknown"
