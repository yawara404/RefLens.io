from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Board, InstagramAccount, User
from app.routers.auth import get_current_user
from app.services.instagram_client import InstagramClient
from app.routers.media import import_from_url, ImportUrlRequest

router = APIRouter(prefix="/instagram", tags=["instagram"])

class InstagramImportRequest(BaseModel):
    board_id: str
    media_urls: List[str]
    captions: Optional[List[str]] = None

@router.get("/auth-url")
def get_instagram_auth_url():
    """Instagram OAuth認可URLを返却"""
    client = InstagramClient()
    return {"auth_url": client.get_auth_url()}

@router.get("/callback")
async def instagram_callback(
    code: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """認可コードからアクセストークンを取得して保存"""
    client = InstagramClient()
    token_data = await client.exchange_code_for_token(code)
    
    # アカウントを保存または更新
    account = db.query(InstagramAccount).filter(InstagramAccount.user_id == user.id).first()
    if not account:
        account = InstagramAccount(
            user_id=user.id,
            instagram_user_id=token_data.get("user_id", "demo_ig_user"),
            instagram_username=token_data.get("username", "art_creator"),
            access_token=token_data.get("access_token", ""),
        )
        db.add(account)
    else:
        account.access_token = token_data.get("access_token", "")
        account.instagram_username = token_data.get("username", account.instagram_username)

    db.commit()
    return {
        "success": True,
        "username": account.instagram_username,
        "message": "Instagram account connected successfully"
    }

@router.post("/disconnect")
def disconnect_instagram(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Instagram連携を解除する"""
    account = db.query(InstagramAccount).filter(InstagramAccount.user_id == user.id).first()
    if not account:
        return {"success": True, "message": "既に切断されています"}

    db.delete(account)
    db.commit()
    return {"success": True, "message": "Instagramの連携を解除しました"}


@router.get("/media")
async def get_instagram_media(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """連携されたInstagram（またはデモギャラリー）からメディア一覧を取得"""
    account = db.query(InstagramAccount).filter(InstagramAccount.user_id == user.id).first()
    token = account.access_token if account else None
    client = InstagramClient(access_token=token)
    media_list = await client.get_user_media()
    return {
        "connected": account is not None,
        "username": account.instagram_username if account else "Demo Creator Feed",
        "media": media_list
    }

@router.post("/import")
async def import_instagram_media(
    payload: InstagramImportRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """選択されたInstagramメディアをキャンバスボードへ一括インポート"""
    board = db.query(Board).filter(Board.id == payload.board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    imported_items = []
    # 複数枚を適度に横並びに配置
    start_x = 50.0
    spacing = 380.0

    for idx, url in enumerate(payload.media_urls):
        cap = payload.captions[idx] if (payload.captions and idx < len(payload.captions)) else None
        req = ImportUrlRequest(
            board_id=payload.board_id,
            image_url=url,
            caption=cap,
            pos_x=start_x + (idx * spacing),
            pos_y=50.0
        )
        res = await import_from_url(req, background_tasks, user, db)
        imported_items.append(res["item"])

    return {
        "success": True,
        "imported_count": len(imported_items),
        "items": imported_items
    }
