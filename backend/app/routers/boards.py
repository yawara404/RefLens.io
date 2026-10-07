import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.models import Board, CanvasItem, MediaItem, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/boards", tags=["boards"])

class CanvasItemUpdate(BaseModel):
    id: str
    pos_x: float
    pos_y: float
    width: float
    height: float
    rotation: float = 0.0
    z_index: int = 1
    is_flipped_h: bool = False
    is_flipped_v: bool = False
    is_grayscale: bool = False
    opacity: float = 1.0
    border_color: str = "transparent"
    border_width: int = 0
    is_locked: bool = False
    caption: Optional[str] = None

class CanvasItemBatchUpdate(BaseModel):
    viewport_x: Optional[float] = None
    viewport_y: Optional[float] = None
    viewport_zoom: Optional[float] = None
    items: List[CanvasItemUpdate]

class BoardCreate(BaseModel):
    title: str = "Untitled Reference Board"
    description: Optional[str] = None
    background_theme: str = "dark-grid"

class BoardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    viewport_x: Optional[float] = None
    viewport_y: Optional[float] = None
    viewport_zoom: Optional[float] = None
    background_theme: Optional[str] = None

@router.get("", include_in_schema=False)
@router.get("/")
def list_boards(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザーのボード一覧を取得（サムネイルやアイテム数付き）"""
    boards = db.query(Board).filter(Board.user_id == user.id).order_by(Board.updated_at.desc()).all()
    
    # ボードが1つもない場合はデフォルトのデモリファレンスボードを作成
    if not boards:
        demo_board = Board(
            user_id=user.id,
            title="Character & Lighting Studies",
            description="コンセプトアート用リファレンスボード。逆光、ライティング、衣装ドレーパリーの分析。",
            background_theme="dark-dots",
            viewport_x=0.0,
            viewport_y=0.0,
            viewport_zoom=1.0,
        )
        db.add(demo_board)
        db.commit()
        db.refresh(demo_board)
        boards = [demo_board]

    res = []
    for b in boards:
        item_count = db.query(CanvasItem).filter(CanvasItem.board_id == b.id).count()
        # 最新のメディアアイテムのサムネイル
        first_item = (
            db.query(CanvasItem)
            .join(MediaItem)
            .filter(CanvasItem.board_id == b.id)
            .order_by(CanvasItem.z_index.desc())
            .first()
        )
        thumb = first_item.media_item.file_path if first_item else None

        res.append({
            "id": b.id,
            "title": b.title,
            "description": b.description,
            "thumbnail_url": thumb or b.thumbnail_url,
            "background_theme": b.background_theme,
            "item_count": item_count,
            "created_at": b.created_at.isoformat(),
            "updated_at": b.updated_at.isoformat(),
        })
    return res

@router.post("", status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", status_code=status.HTTP_201_CREATED)
def create_board(
    payload: BoardCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    board = Board(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        background_theme=payload.background_theme,
        viewport_x=0.0,
        viewport_y=0.0,
        viewport_zoom=1.0,
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return {
        "id": board.id,
        "title": board.title,
        "description": board.description,
        "background_theme": board.background_theme,
        "created_at": board.created_at.isoformat(),
    }

@router.get("/{board_id}")
def get_board_detail(
    board_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ボード詳細と配置されているキャンバスアイテム・AI解析データを取得"""
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    items = (
        db.query(CanvasItem)
        .options(
            joinedload(CanvasItem.media_item).joinedload(MediaItem.ai_analysis)
        )
        .filter(CanvasItem.board_id == board_id)
        .order_by(CanvasItem.z_index.asc())
        .all()
    )

    items_data = []
    for it in items:
        media = it.media_item
        ai = media.ai_analysis if media and (media.source_type != "pixiv" or media.ai_analysis_policy == "allowed") else None
        items_data.append({
            "id": it.id,
            "board_id": it.board_id,
            "media_item_id": it.media_item_id,
            "pos_x": it.pos_x,
            "pos_y": it.pos_y,
            "width": it.width,
            "height": it.height,
            "rotation": it.rotation,
            "z_index": it.z_index,
            "is_flipped_h": it.is_flipped_h,
            "is_flipped_v": it.is_flipped_v,
            "is_grayscale": it.is_grayscale,
            "opacity": it.opacity,
            "border_color": it.border_color,
            "border_width": it.border_width,
            "is_locked": it.is_locked,
            "caption": it.caption,
            "media": {
                "id": media.id,
                "file_path": media.file_path,
                "source_type": media.source_type,
                "ai_analysis_policy": media.ai_analysis_policy,
                "original_file_name": media.original_file_name,
                "width": media.width,
                "height": media.height,
                "aspect_ratio": media.aspect_ratio,
            } if media else None,
            "ai_analysis": {
                "composition": ai.composition,
                "lighting": ai.lighting,
                "pose_anatomy": ai.pose_anatomy,
                "costume_structure": ai.costume_structure,
                "palette": ai.palette_json,
                "tags": ai.tags_json,
                "analysis_model": ai.analysis_model,
            } if ai else None
        })

    return {
        "id": board.id,
        "title": board.title,
        "description": board.description,
        "thumbnail_url": board.thumbnail_url,
        "viewport_x": board.viewport_x,
        "viewport_y": board.viewport_y,
        "viewport_zoom": board.viewport_zoom,
        "background_theme": board.background_theme,
        "items": items_data
    }

@router.put("/{board_id}")
def update_board(
    board_id: str,
    payload: BoardUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    if payload.title is not None:
        board.title = payload.title
    if payload.description is not None:
        board.description = payload.description
    if payload.viewport_x is not None:
        board.viewport_x = payload.viewport_x
    if payload.viewport_y is not None:
        board.viewport_y = payload.viewport_y
    if payload.viewport_zoom is not None:
        board.viewport_zoom = payload.viewport_zoom
    if payload.background_theme is not None:
        board.background_theme = payload.background_theme

    db.commit()
    return {"message": "Board updated successfully"}

@router.post("/{board_id}/items/batch")
def batch_update_items(
    board_id: str,
    payload: CanvasItemBatchUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """PureRefキャンバス上の全配置アイテム座標・変換を一括保存"""
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    if payload.viewport_x is not None:
        board.viewport_x = payload.viewport_x
    if payload.viewport_y is not None:
        board.viewport_y = payload.viewport_y
    if payload.viewport_zoom is not None:
        board.viewport_zoom = payload.viewport_zoom

    for item_data in payload.items:
        item = db.query(CanvasItem).filter(CanvasItem.id == item_data.id, CanvasItem.board_id == board_id).first()
        if item:
            item.pos_x = item_data.pos_x
            item.pos_y = item_data.pos_y
            item.width = item_data.width
            item.height = item_data.height
            item.rotation = item_data.rotation
            item.z_index = item_data.z_index
            item.is_flipped_h = item_data.is_flipped_h
            item.is_flipped_v = item_data.is_flipped_v
            item.is_grayscale = item_data.is_grayscale
            item.opacity = item_data.opacity
            item.border_color = item_data.border_color
            item.border_width = item_data.border_width
            item.is_locked = item_data.is_locked
            item.caption = item_data.caption

    db.commit()
    return {"message": "Batch items saved successfully"}

@router.post("/{board_id}/arrange")
def arrange_items(
    board_id: str,
    layout_type: str = "grid", # grid, horizontal, vertical, pack
    spacing: float = 30.0,
    db: Session = Depends(get_db)
):
    """PureRefスタイルのアイテム自動整列（整列・グリッド配置）"""
    items = db.query(CanvasItem).filter(CanvasItem.board_id == board_id).order_by(CanvasItem.z_index.asc()).all()
    if not items:
        return {"message": "No items to arrange"}

    if layout_type == "grid":
        cols = max(1, math.ceil(math.sqrt(len(items))))
        curr_x = 0.0
        curr_y = 0.0
        row_max_h = 0.0
        col_idx = 0

        for it in items:
            it.pos_x = curr_x
            it.pos_y = curr_y
            it.rotation = 0.0  # 整列時は回転を水平にリセット
            row_max_h = max(row_max_h, it.height)
            curr_x += it.width + spacing
            col_idx += 1

            if col_idx >= cols:
                col_idx = 0
                curr_x = 0.0
                curr_y += row_max_h + spacing
                row_max_h = 0.0

    elif layout_type == "horizontal":
        curr_x = 0.0
        for it in items:
            it.pos_x = curr_x
            it.pos_y = 0.0
            it.rotation = 0.0
            curr_x += it.width + spacing

    elif layout_type == "vertical":
        curr_y = 0.0
        for it in items:
            it.pos_x = 0.0
            it.pos_y = curr_y
            it.rotation = 0.0
            curr_y += it.height + spacing

    db.commit()
    return {"message": f"Arranged {len(items)} items with layout {layout_type}"}

@router.delete("/{board_id}/items/{item_id}")
def delete_canvas_item(
    board_id: str,
    item_id: str,
    db: Session = Depends(get_db)
):
    item = db.query(CanvasItem).filter(CanvasItem.id == item_id, CanvasItem.board_id == board_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Canvas item not found")
    db.delete(item)
    db.commit()
    return {"message": "Item deleted"}

@router.delete("/{board_id}")
def delete_board(
    board_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    db.delete(board)
    db.commit()
    return {"message": "Board deleted"}
