import logging
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

# クリエイター向けデモ用リファレンスメディアプリセット（Instagram風の高品質なリファレンス画像）
DEMO_INSTAGRAM_POSTS = [
    {
        "id": "ig_demo_001",
        "caption": "Dramatic golden hour backlighting studies with dynamic rim light #conceptart #lighting #reference",
        "media_type": "IMAGE",
        "media_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop&q=80",
        "permalink": "https://instagram.com/p/demo001",
        "timestamp": "2026-10-01T10:00:00+0000",
        "username": "studio_artlens"
    },
    {
        "id": "ig_demo_002",
        "caption": "Cyberpunk character design costume folds and leather textile silhouette #costumedesign #folds",
        "media_type": "IMAGE",
        "media_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=800&auto=format&fit=crop&q=80",
        "permalink": "https://instagram.com/p/demo002",
        "timestamp": "2026-10-02T14:30:00+0000",
        "username": "studio_artlens"
    },
    {
        "id": "ig_demo_003",
        "caption": "Dynamic action pose with deep perspective foreshortening & diagonal line composition #anatomy #pose",
        "media_type": "IMAGE",
        "media_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&auto=format&fit=crop&q=80",
        "permalink": "https://instagram.com/p/demo003",
        "timestamp": "2026-10-03T09:15:00+0000",
        "username": "studio_artlens"
    },
    {
        "id": "ig_demo_004",
        "caption": "Architectural low angle low-key noir lighting reference #composition #noir #lowangle",
        "media_type": "IMAGE",
        "media_url": "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=800&auto=format&fit=crop&q=80",
        "permalink": "https://instagram.com/p/demo004",
        "timestamp": "2026-10-04T18:20:00+0000",
        "username": "studio_artlens"
    },
    {
        "id": "ig_demo_005",
        "caption": "Chiffon fabric motion & wind dynamics drapery anatomy sketch resource #fabric #drapery",
        "media_type": "IMAGE",
        "media_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=800&auto=format&fit=crop&q=80",
        "permalink": "https://instagram.com/p/demo005",
        "timestamp": "2026-10-05T12:00:00+0000",
        "username": "studio_artlens"
    },
    {
        "id": "ig_demo_006",
        "caption": "Moody atmospheric side-lighting portrait for palette & skin tone values #portrait #lighting",
        "media_type": "IMAGE",
        "media_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&auto=format&fit=crop&q=80",
        "permalink": "https://instagram.com/p/demo006",
        "timestamp": "2026-10-06T08:45:00+0000",
        "username": "studio_artlens"
    }
]

class InstagramClient:
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.base_url = "https://graph.instagram.com"

    def get_auth_url(self) -> str:
        """Instagram OAuth認証URLを生成"""
        if not settings.INSTAGRAM_APP_ID:
            # アプリID未設定時はデモコールバックへ
            return f"{settings.INSTAGRAM_REDIRECT_URI}?demo=true&code=demo_auth_code_reflens"

        return (
            f"https://api.instagram.com/oauth/authorize"
            f"?client_id={settings.INSTAGRAM_APP_ID}"
            f"&redirect_uri={settings.INSTAGRAM_REDIRECT_URI}"
            f"&scope=user_profile,user_media"
            f"&response_type=code"
        )

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """認可コードをアクセストークンに交換"""
        if code.startswith("demo_"):
            return {
                "access_token": "demo_access_token_reflens_art",
                "user_id": "demo_ig_creator",
                "username": "art_creator_official"
            }

        url = "https://api.instagram.com/oauth/access_token"
        data = {
            "client_id": settings.INSTAGRAM_APP_ID,
            "client_secret": settings.INSTAGRAM_APP_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
            "code": code,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(f"Failed to exchange token: {resp.text}")
                raise ValueError("Instagram token exchange failed")

    async def get_user_media(self, access_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """ユーザーのInstagram投稿メディア一覧を取得"""
        token = access_token or self.access_token

        if not token or token.startswith("demo_"):
            # デモメディアを返却
            return DEMO_INSTAGRAM_POSTS

        url = f"{self.base_url}/me/media"
        params = {
            "fields": "id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username",
            "access_token": token
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [])
            else:
                logger.warning(f"Instagram API error ({resp.status_code}): {resp.text}. Falling back to demo posts.")
                return DEMO_INSTAGRAM_POSTS
