"""Unofficial pixiv mobile App API proxy.

    * 未設定（PIXIV_CLIENT_ID 未設定）時は traditional デモフィードへフォールバック
    * 設定済み かつ 接続済みなら本物のpixiv API（検索 / ランキング / ブックマーク / フォロー / 詳細）
    * 作品ファイルの取得は常にサーバー経由（i.pximg.net は Referer 必須のため）
"""

from __future__ import annotations

from datetime import datetime, timedelta
import time
from typing import Annotated, List, Optional
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from PIL import Image

from app.core.config import settings
from app.core.pixiv_tokens import decrypt_token, encrypt_token
from app.core.database import get_db
from app.models.models import Board, CanvasItem, MediaItem, PixivAccount, User
from app.routers.auth import GUEST_EMAIL, get_current_user
from app.routers.media import perform_ai_analysis
from app.services.pixiv_ai_policy import resolve_pixiv_ai_policy
from app.services.pixiv_client import (
    PixivApiError,
    PixivClient,
    _next_cursor,
    is_configured,
    normalize_illust,
)

router = APIRouter(prefix="/pixiv", tags=["pixiv"])

PIXIV_BLUE = "#0096fa"
_feed_cache: dict[tuple, tuple[float, dict]] = {}


# ----------------------------------------------------------------------
# 認証済みクライアントの取得（トークン自動更新つき）
# ----------------------------------------------------------------------
def _get_account(db: Session, user: User) -> Optional[PixivAccount]:
    """そのユーザーに紐づく pixiv アカウントを返す。

    公開プレビューにも共通ゲスト（`creator@reflens.io`）がいるため、**ゲストだけ**は
    pixiv セッションを絶対に渡さない。ログイン済みユーザーは `user_id` が自分の行に
    限定されるので、他人の pixiv データには到達できない。
    """
    if user.email == GUEST_EMAIL:
        return None
    return db.query(PixivAccount).filter(PixivAccount.user_id == user.id).first()


async def _client_for(db: Session, user: User) -> PixivClient:
    """アクセストークンを（必要なら更新して）使い回せるクライアントを返す"""
    account = _get_account(db, user)
    if not account or not account.access_token:
        raise PixivApiError("pixivアカウントが未接続です。")

    # 期限切れ5分以内ならリフレッシュ
    needs_refresh = False
    if account.expires_at:
        expires_at = account.expires_at
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        needs_refresh = expires_at - datetime.utcnow() < timedelta(minutes=5)
    else:
        needs_refresh = True

    if needs_refresh and account.refresh_token:
        try:
            token_data = await PixivClient.refresh_access_token(decrypt_token(account.refresh_token))
            account.access_token = encrypt_token(token_data["access_token"])
            if token_data.get("refresh_token"):
                account.refresh_token = encrypt_token(token_data["refresh_token"])
            account.expires_at = token_data["expires_at"]
            db.commit()
        except PixivApiError:
            raise
        except Exception:
            pass

    return PixivClient(access_token=decrypt_token(account.access_token))


# ----------------------------------------------------------------------
# デモフィード（App ID 未設定時のフォールバック）
# ----------------------------------------------------------------------
DEMO_FEED_ITEMS = [
    {
        "id": "11984001",
        "title": "【ポーズ講座】コントラポストとS字重心の捉え方・立ち絵応用編",
        "author_name": "絵師ポーズ研究室",
        "author_avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80",
        "image_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=1000&auto=format&fit=crop&q=80",
        "category": "poses",
        "tags": ["ポーズ", "イラスト講座", "コントラポスト", "骨格", "立ち絵", "作画資料"],
        "likes": 4820,
        "bookmarks": 8940,
        "page_count": 4,
        "source_url": "https://www.pixiv.net/artworks/11984001",
    },
    {
        "id": "11984002",
        "title": "【シワ構造研究】布の厚みと引っ張りテンション・ドレーパリー完全解説",
        "author_name": "デジタル作画工房",
        "author_avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80",
        "image_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=1000&auto=format&fit=crop&q=80",
        "category": "costumes",
        "tags": ["衣装", "服のシワ", "シワ講座", "質感表現", "ビッグシルエット", "革ジャン"],
        "likes": 6120,
        "bookmarks": 12400,
        "page_count": 6,
        "source_url": "https://www.pixiv.net/artworks/11984002",
    },
    {
        "id": "11984003",
        "title": "【ライティング】夕景・逆光・リムライトで魅せるドラマティックポートレート",
        "author_name": "背景美術スタジオ",
        "author_avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=100&auto=format&fit=crop&q=80",
        "image_url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000&auto=format&fit=crop&q=80",
        "category": "lighting",
        "tags": ["逆光", "リムライト", "夕暮れ", "ライティング講座", "色彩設計", "透明感"],
        "likes": 9340,
        "bookmarks": 15800,
        "page_count": 2,
        "source_url": "https://www.pixiv.net/artworks/11984003",
    },
    {
        "id": "11984004",
        "title": "【背景パース】雨上がりの夜景サイバーシティ・遠近感と光の反射",
        "author_name": "コンセプト背景部",
        "author_avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop&q=80",
        "image_url": "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=1000&auto=format&fit=crop&q=80",
        "category": "backgrounds",
        "tags": ["背景", "パース", "夜景", "雨", "光の反射", "コンセプトアート"],
        "likes": 5120,
        "bookmarks": 9800,
        "page_count": 3,
        "source_url": "https://www.pixiv.net/artworks/11984004",
    },
    {
        "id": "11984005",
        "title": "【服飾マテリアル】シフォンとレースの透け感・風をはらむ布の動き",
        "author_name": "クチュール作画研究会",
        "author_avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80",
        "image_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=1000&auto=format&fit=crop&q=80",
        "category": "costumes",
        "tags": ["衣装", "シフォン", "ドレーパリー", "風の表現", "透け感", "キャラクターデザイン"],
        "likes": 7430,
        "bookmarks": 11200,
        "page_count": 5,
        "source_url": "https://www.pixiv.net/artworks/11984005",
    },
    {
        "id": "11984006",
        "title": "【色彩・バリュー研究】肌の固有色と環境光の影響・影色の選び方",
        "author_name": "色彩設計ラボ",
        "author_avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80",
        "image_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1000&auto=format&fit=crop&q=80",
        "category": "lighting",
        "tags": ["色彩", "肌塗り", "環境光", "バリュースタディ", "イラスト講座", "メイキング"],
        "likes": 8800,
        "bookmarks": 16400,
        "page_count": 8,
        "source_url": "https://www.pixiv.net/artworks/11984006",
    },
]

_DEMO_CATEGORY_TO_FILTER = {
    "poses": "illust",
    "lighting": "illust",
    "costumes": "illust",
    "backgrounds": "illust",
}


def _filter_demo(
    category: str,
    query: Optional[str],
    tag: Optional[str],
) -> List[dict]:
    items = DEMO_FEED_ITEMS
    if category and category not in ("all", "recommended", "ranking", "search"):
        items = [i for i in items if i["category"] == category]
    if tag:
        items = [i for i in items if tag.lower() in [t.lower() for t in i["tags"]]]
    if query:
        q = query.lower()
        items = [
            i for i in items
            if q in i["title"].lower()
            or q in i["author_name"].lower()
            or any(q in t.lower() for t in i["tags"])
        ]
    return items


# ----------------------------------------------------------------------
# 接続状態
# ----------------------------------------------------------------------
@router.get("/status")
def pixiv_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """pixivクライアントの現在の状態（接続可否・アカウント・モード）"""
    account = _get_account(db, user)
    configured = is_configured()
    return {
        "configured": configured,
        # 「Pixivの画面でログインする」接続は公開プレビューでも利用できる。
        "connect_available": configured,
        # Refresh Token を直接貼る接続はローカル専用（公開では平文入力を広めない）。
        "token_connect_available": configured and not bool(settings.ROOT_PATH),
        "connected": account is not None,
        "mode": "live" if account else ("demo" if not configured else "auth_required"),
        "account": {
            "id": account.pixiv_user_id,
            "name": account.pixiv_username,
            "account": account.pixiv_account,
            "avatar_url": "",
            "expires_at": account.expires_at.isoformat() if account and account.expires_at else None,
        } if account else None,
        "message": (
            "pixivに接続済み"
            if account
            else (
                "Pixiv接続のサーバー設定が未完了です。手順は PIXIV_SETUP.md を参照してください"
                if not configured
                else "Pixivでログインすると実データを表示できます"
            )
        ),
    }


class PixivConnectRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=4096)


@router.post("/connect")
async def pixiv_connect(
    request: PixivConnectRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exchange a refresh token and store it encrypted for this local user."""
    if settings.ROOT_PATH:
        # 公開プレビューでは「Pixivでログイン」だけを受け付ける。
        # Refresh Token の平文入力はローカル専用とする。
        raise HTTPException(status_code=403, detail="公開プレビューではRefresh Token接続は利用できません。「Pixivでログイン」を使ってください。")
    if user.email == "creator@reflens.io":
        raise HTTPException(status_code=401, detail="Refresh Token方式は先にRefLensアカウントへのログインが必要です。Pixivでログインも利用できます。")
    if not is_configured():
        raise HTTPException(status_code=503, detail="Pixiv接続のサーバー設定が未完了です。")
    try:
        token_data = await PixivClient.refresh_access_token(request.refresh_token.strip())
        profile = token_data.get("user") or await PixivClient(token_data["access_token"]).get_user_me()
    except PixivApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not profile.get("id"):
        raise HTTPException(status_code=502, detail="Pixivアカウント情報を取得できませんでした。")

    pixiv_id = str(profile["id"])
    other = db.query(PixivAccount).filter(
        PixivAccount.pixiv_user_id == pixiv_id,
        PixivAccount.user_id != user.id,
    ).first()
    if other:
        raise HTTPException(status_code=409, detail="このPixivアカウントは別のRefLensアカウントに連携済みです。")
    account = _get_account(db, user)
    if account and account.pixiv_user_id != pixiv_id:
        raise HTTPException(status_code=409, detail="別のPixivアカウントが連携済みです。先に接続を解除してください。")
    if not account:
        account = PixivAccount(user_id=user.id, pixiv_user_id=pixiv_id)
        db.add(account)

    account.pixiv_user_id = pixiv_id
    account.pixiv_username = profile.get("name") or account.pixiv_username
    account.pixiv_account = profile.get("account") or account.pixiv_account
    account.access_token = encrypt_token(token_data["access_token"])
    account.refresh_token = encrypt_token(token_data["refresh_token"])
    account.expires_at = token_data.get("expires_at")
    db.commit()
    _feed_cache.clear()
    return {"connected": True, "account": {"id": account.pixiv_user_id, "name": account.pixiv_username}}


@router.get("/image")
async def pixiv_image(
    url: Annotated[str, Query(max_length=2048)],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Serve only pixiv image CDN URLs through the backend with Referer."""
    if not _get_account(db, user):
        raise HTTPException(status_code=403, detail="Pixiv接続が必要です。")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "i.pximg.net" or parsed.port or parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="Pixiv画像URLのみ指定できます。")
    image, error = await PixivClient().download_image(url, settings.PIXIV_CACHE_DIR)
    if not image:
        raise HTTPException(status_code=502, detail=error or "画像の取得に失敗しました。")
    return FileResponse(image, headers={"Cache-Control": "private, max-age=86400"})


@router.post("/disconnect")
def pixiv_disconnect(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """pixiv接続を解除する"""
    account = _get_account(db, user)
    if not account:
        return {"success": True, "message": "既に切断されています"}

    db.delete(account)
    db.commit()
    _feed_cache.clear()
    return {"success": True, "message": "pixiv接続を解除しました"}


# ----------------------------------------------------------------------
# フィード / 検索
# ----------------------------------------------------------------------
@router.get("/feed")
async def get_pixiv_feed(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: str = "all",
    query: Optional[str] = None,
    tag: Optional[str] = None,
    sort: str = "date_desc",
    duration: Optional[str] = None,
    page: Annotated[int, Query(ge=1, le=100)] = 1,
    per_page: Annotated[int, Query(ge=1, le=60)] = 30,
    cursor: Annotated[Optional[str], Query(pattern=r"^[0-9]{1,20}$")] = None,
):
    """pixivフィード取得

    category:
        all / recommended / ranking / following / bookmarks / illust / manga /
        デモ用カテゴリ (poses, lighting, costumes, backgrounds)
    """
    account = _get_account(db, user)
    use_live = account is not None

    if not use_live:
        items = _filter_demo(category, query, tag)
        return {
            "mode": "demo",
            "category": category,
            "page": page,
            "total": len(items),
            "has_next": False,
            "items": items,
            "notice": (
                "Pixivでログインすると実データに切り替わります"
                if not is_configured()
                else "デモフィード表示中: 上の「Pixivに接続」からログインしてください"
            ),
        }

    if category in ("following", "bookmarks") and page > 1 and not cursor:
        raise HTTPException(status_code=400, detail="前ページから続けて読み込んでください。")

    cache_key = (user.id, account.pixiv_user_id, category, query, tag, sort, duration, page, per_page, cursor)
    cached = _feed_cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < 30:
        return cached[1]

    client = await _client_for(db, user)

    try:
        if category == "recommended":
            result = await client.get_recommended_illusts(page, per_page)
        elif category == "ranking":
            result = await client.get_illust_ranking(mode="daily", page=page, per_page=per_page)
        elif category == "following":
            result = await client.get_following_illusts(cursor=cursor)
        elif category == "bookmarks":
            result = await client.get_user_bookmarks(account.pixiv_user_id, cursor=cursor)
        elif category in ("illust", "manga", "ugoira"):
            result = await client.search_illust(
                word=query or tag or "",
                sort=sort,
                duration=duration,
                search_target={
                    "illust": "partial_match_for_tags",
                    "manga": "partial_match_for_tags",
                    "ugoira": "partial_match_for_tags",
                }.get(category, "partial_match_for_tags"),
                page=page,
                per_page=per_page,
            )
            # typeで絞る（カテゴリ指定時のみ）
            if category in ("illust", "manga"):
                target_type = category
                result["illusts"] = [i for i in result["illusts"] if i.get("type") == target_type]
        elif category in _DEMO_CATEGORY_TO_FILTER:
            # 旧カテゴリ（ポーズ/ライティング等）はタグ検索に読み替える
            keyword = {
                "poses": "ポーズ参考",
                "lighting": "ライティング参考",
                "costumes": "衣装_reference",
                "backgrounds": "背景美術",
            }.get(category, category)
            result = await client.search_illust(word=keyword, sort=sort, duration=duration, page=page, per_page=per_page)
        else:
            # キーワード検索（query / tag が無ければ人気作品）
            keyword = query or tag or ""
            if not keyword:
                result = await client.get_recommended_illusts(page, per_page)
            else:
                result = await client.search_illust(
                    word=keyword,
                    sort=sort,
                    duration=duration,
                    page=page,
                    per_page=per_page,
                )
    except PixivApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc))

    illusts = result.get("illusts", []) or []
    items = [normalize_illust(i) for i in illusts]
    cursor_config = {
        "following": ("/v2/illust/follow", "offset"),
        "bookmarks": ("/v1/user/bookmarks/illust", "max_bookmark_id"),
    }.get(category)
    next_cursor = _next_cursor(result.get("next_url"), *cursor_config) if cursor_config else None

    response = {
        "mode": "live",
        "category": category,
        "page": page,
        "total": len(items),
        "has_next": bool(next_cursor) if cursor_config else bool(result.get("next_url")),
        "next_cursor": next_cursor,
        "items": items,
        "notice": None,
    }
    if len(_feed_cache) >= 128:
        _feed_cache.clear()
    _feed_cache[cache_key] = (time.monotonic(), response)
    return response


@router.get("/illust/{illust_id}")
async def get_pixiv_illust(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    illust_id: str = Path(..., description="pixiv作品ID"),
):
    """作品詳細（全ページ画像URL・タグ・作者情報）"""
    account = _get_account(db, user)
    if not account:
        demo = next((i for i in DEMO_FEED_ITEMS if i["id"] == illust_id), None)
        if not demo:
            raise HTTPException(status_code=404, detail="作品が見つかりません（デモフィードのみ）")
        return {"mode": "demo", **demo, "pages": [{"image_url": demo["image_url"]}]}

    client = await _client_for(db, user)
    try:
        detail = await client.get_illust_detail(illust_id)
        pages = await client.get_illust_pages(illust_id, detail)
    except PixivApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc))

    if not detail:
        raise HTTPException(status_code=404, detail="作品が見つかりません")

    normalized = normalize_illust(detail)
    normalized["pages"] = [
        {"image_url": p.get("image_url"), "width": p.get("width", 0), "height": p.get("height", 0)}
        for p in pages
        if p.get("image_url")
    ]
    normalized["mode"] = "live"
    return normalized


# ----------------------------------------------------------------------
# ストック（Manager / Canvas へ取り込み）
# ----------------------------------------------------------------------
class StockPixivRequest(BaseModel):
    illust_id: str
    folder_name: Optional[str] = "All References"
    board_id: Optional[str] = None
    pos_x: Optional[float] = None
    pos_y: Optional[float] = None
    page_indexes: Optional[List[int]] = Field(
        None, description="特定ページのみ取り込む場合のページindex（0始まり）。未指定なら全ページ。"
    )


class BulkStockPixivRequest(BaseModel):
    illust_ids: List[str]
    folder_name: Optional[str] = "All References"
    board_id: Optional[str] = None
    pos_x: Optional[float] = None
    pos_y: Optional[float] = None
    include_all_pages: bool = True


def _pick_folder_for_category(category: str) -> str:
    return {
        "poses": "Poses & Anatomy",
        "lighting": "Lighting & Values",
        "costumes": "Costumes & Folds",
        "backgrounds": "Composition & Perspective",
    }.get(category, "All References")


def _scaled_dimensions(width: int, height: int, max_dim: float = 360.0) -> tuple:
    if width <= 0 or height <= 0:
        return max_dim, max_dim
    ratio = float(width) / float(height)
    if width >= height:
        return max_dim, max_dim / ratio
    return max_dim * ratio, max_dim


def _place_on_canvas(
    db: Session,
    board_id: str,
    media: MediaItem,
    caption: Optional[str] = None,
    pos_x: Optional[float] = None,
    pos_y: Optional[float] = None,
) -> Optional[str]:
    """MediaItemをキャンバスへ配置する。座標省略時は重複なく自動配置する"""
    if not db.query(Board).filter(Board.id == board_id).first():
        return None

    item_w, item_h = _scaled_dimensions(media.width, media.height)
    existing_count = db.query(CanvasItem).filter(CanvasItem.board_id == board_id).count()

    if pos_x is not None and pos_y is not None:
        place_x, place_y = pos_x, pos_y
    else:
        # 既存アイテムの重なりを避けて、列を切って上から積む
        occupied = {
            (round(c.pos_x, -1), round(c.pos_y, -1))
            for c in db.query(CanvasItem).filter(CanvasItem.board_id == board_id).all()
        }
        gap = 40.0
        place_x = place_y = 80.0
        for _ in range(200):
            key = (round(place_x, -1), round(place_y, -1))
            if key not in occupied:
                break
            place_y += item_h + gap
        else:
            place_x = 80.0 + (existing_count % 5) * (item_w + gap)
            place_y = 80.0

    canvas_item = CanvasItem(
        board_id=board_id,
        media_item_id=media.id,
        pos_x=place_x,
        pos_y=place_y,
        width=item_w,
        height=item_h,
        z_index=existing_count + 1,
        caption=caption or media.title,
    )
    db.add(canvas_item)
    db.commit()
    db.refresh(canvas_item)
    return canvas_item.id


async def _stock_one_illust(
    illust: dict,
    pages: List[dict],
    user: User,
    db: Session,
    background_tasks: BackgroundTasks,
    folder_name: str,
    board_id: Optional[str],
    pos_x: Optional[float] = None,
    pos_y: Optional[float] = None,
    page_indexes: Optional[List[int]] = None,
) -> dict:
    """1作品を（指定ページだけ）ダウンロードしてMediaItemとして登録し、任意でCanvasへ配置"""
    from app.core.database import SessionLocal

    # (元ページindex, page dict) の組を作る
    indexed_pages = list(enumerate(pages)) or [(0, {"image_url": illust.get("image_url")})]
    if page_indexes:
        wanted = {int(i) for i in page_indexes}
        selected = [(i, p) for i, p in indexed_pages if i in wanted]
        indexed_pages = selected or indexed_pages[:1]

    created: List[dict] = []
    errors: List[str] = []
    cursor_x = pos_x
    ai_policy = await resolve_pixiv_ai_policy(illust)

    for source_page_index, page in indexed_pages:
        image_url = page.get("image_url") or illust.get("image_url")
        if not image_url:
            errors.append(f"p{source_page_index + 1}: 画像URLが取得できませんでした")
            continue

        # 既に同じ作品・同じページを登録済みなら再利用する（重複ダウンロード防止）
        existing = (
            db.query(MediaItem)
            .filter(
                MediaItem.user_id == user.id,
                MediaItem.pixiv_illust_id == str(illust.get("id")),
                MediaItem.pixiv_page_index == source_page_index,
            )
            .first()
        )
        if existing:
            if existing.ai_analysis_policy != ai_policy:
                existing.ai_analysis_policy = ai_policy
                db.commit()
            entry = {"media_item_id": existing.id, "reused": True, "page_index": source_page_index}
            if board_id:
                entry["canvas_item_id"] = _place_on_canvas(
                    db, board_id, existing, existing.title,
                    cursor_x if cursor_x is not None else None,
                    pos_y if cursor_x is not None else None,
                )
                if cursor_x is not None:
                    cursor_x += 400.0
            created.append(entry)
            continue

        saved_path, dl_error = await PixivClient().download_image(image_url, settings.UPLOAD_DIR)
        if not saved_path:
            errors.append(dl_error or "画像の取得に失敗しました")
            continue

        try:
            with Image.open(saved_path) as img:
                img_w, img_h = img.size
        except Exception:
            img_w, img_h = illust.get("width") or 0, illust.get("height") or 0

        page_title = illust.get("title") or f"pixiv #{illust.get('id')}"
        if len(indexed_pages) > 1:
            page_title = f"{page_title} - p{source_page_index + 1}"

        media_item = MediaItem(
            user_id=user.id,
            board_id=board_id,
            source_type="pixiv",
            ai_analysis_policy=ai_policy,
            title=page_title,
            original_file_name=f"pixiv_{illust.get('id')}_{source_page_index}.jpg",
            author_name=illust.get("author_name"),
            favicon_url="https://www.pixiv.net/favicon.ico",
            file_path=f"/uploads/{saved_path.name}",
            source_url=illust.get("source_url"),
            pixiv_illust_id=str(illust.get("id")),
            pixiv_page_index=source_page_index,
            mime_type="image/jpeg",
            file_size=saved_path.stat().st_size if saved_path.exists() else 0,
            width=img_w,
            height=img_h,
            aspect_ratio=(float(img_w) / float(img_h)) if img_h else 1.0,
            folder_name=folder_name or "All References",
        )
        db.add(media_item)
        db.commit()
        db.refresh(media_item)

        # pixivの実タグ + Vision/heuristic解析（Geminiがあれば構図・光も解析される）
        background_tasks.add_task(
            perform_ai_analysis,
            media_item.id,
            str(saved_path),
            SessionLocal,
            list(illust.get("tags") or [])[:12],
        )

        entry = {"media_item_id": media_item.id, "reused": False, "page_index": source_page_index}
        if board_id:
            entry["canvas_item_id"] = _place_on_canvas(
                db, board_id, media_item, page_title,
                cursor_x, pos_y if cursor_x is not None else None,
            )
            if cursor_x is not None:
                cursor_x += 400.0
        created.append(entry)

    return {"created": created, "errors": errors}


@router.post("/stock")
async def stock_pixiv_artwork(
    payload: StockPixivRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """1作品を Raindrop Manager（+ 任意でCanvas）へ取り込む"""
    account = _get_account(db, user)
    if not account:
        # デモフィード: 従来どおりURL経由のブックマークへ委譲
        from app.routers.bookmarks import add_bookmark, BookmarkAddRequest

        url = f"https://www.pixiv.net/artworks/{payload.illust_id}"
        req = BookmarkAddRequest(
            url=url,
            folder_name=payload.folder_name or "All References",
            board_id=payload.board_id,
            pos_x=payload.pos_x or 0.0,
            pos_y=payload.pos_y or 0.0,
        )
        return await add_bookmark(req, background_tasks, user, db)

    client = await _client_for(db, user)
    try:
        detail = await client.get_illust_detail(payload.illust_id)
        pages = await client.get_illust_pages(payload.illust_id, detail)
    except PixivApiError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc))

    if not detail:
        raise HTTPException(status_code=404, detail="作品が見つかりません")

    illust = normalize_illust(detail)
    result = await _stock_one_illust(
        illust,
        pages,
        user,
        db,
        background_tasks,
        payload.folder_name or _pick_folder_for_category(illust.get("category", "")),
        payload.board_id,
        payload.pos_x,
        payload.pos_y,
        payload.page_indexes,
    )

    return {
        "success": True,
        "illust_id": payload.illust_id,
        "title": illust.get("title"),
        "count": len(result["created"]),
        "created": result["created"],
        "errors": result["errors"],
        "bookmark_id": result["created"][0]["media_item_id"] if result["created"] else None,
        "canvas_item_id": result["created"][0].get("canvas_item_id") if result["created"] else None,
    }


@router.post("/stock/bulk")
async def stock_pixiv_bulk(
    payload: BulkStockPixivRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """複数作品を一括で Manager（+ 任意でCanvas）へ取り込む"""
    account = _get_account(db, user)
    if not account:
        raise HTTPException(status_code=400, detail="pixivのログインが必要です。")

    client = await _client_for(db, user)
    all_created: List[dict] = []
    all_errors: List[str] = []

    for illust_id in payload.illust_ids:
        try:
            detail = await client.get_illust_detail(illust_id)
            if not detail:
                all_errors.append(f"#{illust_id}: 作品が見つかりません")
                continue
            pages = await client.get_illust_pages(illust_id, detail)
            illust = normalize_illust(detail)
            result = await _stock_one_illust(
                illust,
                pages if payload.include_all_pages else pages[:1],
                user,
                db,
                background_tasks,
                payload.folder_name or "All References",
                payload.board_id,
                payload.pos_x,
                payload.pos_y,
            )
            all_created.extend(result["created"])
            all_errors.extend(result["errors"])
        except PixivApiError as exc:
            all_errors.append(f"#{illust_id}: {exc}")
        except Exception as exc:  # noqa: BLE001
            all_errors.append(f"#{illust_id}: {exc}")

    return {
        "success": len(all_created) > 0,
        "count": len(all_created),
        "created": all_created,
        "errors": all_errors,
    }
