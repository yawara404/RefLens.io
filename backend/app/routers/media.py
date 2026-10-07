import asyncio
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from PIL import Image
import httpx
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Board, MediaItem, CanvasItem, AIAnalysis, User
from app.routers.auth import get_current_user
from app.services.llm_analyzer import analyze_image_with_vision, describe_active_provider

router = APIRouter(prefix="/media", tags=["media"])
_analysis_slots = asyncio.Semaphore(2)

def _model_name() -> str:
    """解析に使ったプロバイダ／モデルの表示名"""
    from app.core.config import settings as s

    if s.LLM_PROVIDER.strip().lower() == "ollama":
        return f"ollama:{s.OLLAMA_MODEL}"
    if s.GEMINI_API_KEY:
        return f"gemini:{s.GEMINI_MODEL}"
    return "heuristic-vision-v1"

def _merge_tags(analysis_tags, extra_tags) -> list:
    """Vision解析のタグに取得元（pixivなど）のタグをマージして重複をなくす"""
    merged: list = []
    seen: set = set()
    for tag in list(extra_tags or []) + list(analysis_tags or []):
        if not tag:
            continue
        key = str(tag).strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(str(tag).strip())
    return merged

def _save_analysis(
    db: Session,
    media_id: str,
    analysis_data: Dict[str, Any],
    extra_tags: Optional[list] = None,
) -> None:
    """解析結果（＋取得元タグ）を新規作成 or 更新してコミットする"""
    tags = _merge_tags(extra_tags, analysis_data.get("tags", []))

    existing = db.query(AIAnalysis).filter(AIAnalysis.media_item_id == media_id).first()
    if existing:
        existing.composition = analysis_data.get("composition", "")
        existing.lighting = analysis_data.get("lighting", "")
        existing.pose_anatomy = analysis_data.get("pose_anatomy", "")
        existing.costume_structure = analysis_data.get("costume_structure", "")
        existing.palette_json = analysis_data.get("palette", [])
        existing.tags_json = tags
        existing.analysis_model = _model_name()
    else:
        db.add(AIAnalysis(
            media_item_id=media_id,
            composition=analysis_data.get("composition", ""),
            lighting=analysis_data.get("lighting", ""),
            pose_anatomy=analysis_data.get("pose_anatomy", ""),
            costume_structure=analysis_data.get("costume_structure", ""),
            palette_json=analysis_data.get("palette", []),
            tags_json=tags,
            analysis_model=_model_name(),
        ))
    db.commit()

async def perform_ai_analysis(
    media_id: str,
    file_path_str: str,
    db_factory,
    extra_tags: Optional[list] = None,
):
    """画像に対してVision LLM解析を実行してDBに保存（バックグラウンドタスク）

    extra_tags: pixiv等の取得元メタデータ由来のタグ。解析タグに優先してマージされる。
    """
    try:
        def can_analyze() -> bool:
            db = db_factory()
            try:
                media = db.query(MediaItem).filter(MediaItem.id == media_id).first()
                return bool(media) and (
                    media.source_type != "pixiv" or media.ai_analysis_policy == "allowed"
                )
            finally:
                db.close()

        if not await asyncio.to_thread(can_analyze):
            return

        # 大量取り込み時も画像解析がAPIのイベントループとCPUを占有しないようにする。
        async with _analysis_slots:
            analysis_data = await analyze_image_with_vision(Path(file_path_str))

        def save_result() -> None:
            db = db_factory()
            try:
                media = db.query(MediaItem).filter(MediaItem.id == media_id).first()
                if not media or (media.source_type == "pixiv" and media.ai_analysis_policy != "allowed"):
                    return
                _save_analysis(db, media_id, analysis_data, extra_tags)
            finally:
                db.close()

        await asyncio.to_thread(save_result)
    except Exception as e:
        print(f"Error during AI analysis for {media_id}: {e}")

@router.post("/upload")
async def upload_media(
    board_id: str = Form(...),
    pos_x: float = Form(0.0),
    pos_y: float = Form(0.0),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    ext = Path(file.filename or "image.jpg").suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        ext = ".jpg"

    unique_filename = f"{uuid.uuid4().hex}{ext}"
    saved_path = settings.UPLOAD_DIR / unique_filename

    # ファイルを保存
    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    # 画像のメタデータ（解像度）を取得
    try:
        with Image.open(saved_path) as img:
            w, h = img.size
            mime = file.content_type or f"image/{ext.replace('.', '')}"
    except Exception:
        w, h = 400, 400
        mime = "image/jpeg"

    aspect_ratio = float(w) / float(h) if h > 0 else 1.0

    # 初期キャンバスサイズ（長辺360px前後にスケール）
    max_dim = 360.0
    if w >= h:
        item_w = max_dim
        item_h = max_dim / aspect_ratio
    else:
        item_h = max_dim
        item_w = max_dim * aspect_ratio

    relative_url = f"/uploads/{unique_filename}"

    # MediaItem作成
    media_item = MediaItem(
        user_id=user.id,
        board_id=board_id,
        source_type="local_upload",
        original_file_name=file.filename,
        file_path=relative_url,
        mime_type=mime,
        file_size=len(content),
        width=w,
        height=h,
        aspect_ratio=aspect_ratio
    )
    db.add(media_item)
    db.commit()
    db.refresh(media_item)

    # 既存の最大z_index取得
    max_z = db.query(CanvasItem).filter(CanvasItem.board_id == board_id).count() + 1

    # CanvasItem作成
    canvas_item = CanvasItem(
        board_id=board_id,
        media_item_id=media_item.id,
        pos_x=pos_x,
        pos_y=pos_y,
        width=item_w,
        height=item_h,
        z_index=max_z
    )
    db.add(canvas_item)
    db.commit()
    db.refresh(canvas_item)

    # バックグラウンドでAI解析を実行
    from app.core.database import SessionLocal
    background_tasks.add_task(perform_ai_analysis, media_item.id, str(saved_path), SessionLocal)

    return {
        "item": {
            "id": canvas_item.id,
            "board_id": canvas_item.board_id,
            "media_item_id": media_item.id,
            "pos_x": canvas_item.pos_x,
            "pos_y": canvas_item.pos_y,
            "width": canvas_item.width,
            "height": canvas_item.height,
            "rotation": canvas_item.rotation,
            "z_index": canvas_item.z_index,
            "is_flipped_h": canvas_item.is_flipped_h,
            "is_flipped_v": canvas_item.is_flipped_v,
            "is_grayscale": canvas_item.is_grayscale,
            "opacity": canvas_item.opacity,
            "border_color": canvas_item.border_color,
            "border_width": canvas_item.border_width,
            "is_locked": canvas_item.is_locked,
            "media": {
                "id": media_item.id,
                "file_path": media_item.file_path,
                "source_type": media_item.source_type,
                "original_file_name": media_item.original_file_name,
                "width": media_item.width,
                "height": media_item.height,
                "aspect_ratio": media_item.aspect_ratio,
            },
            "ai_analysis": None  # バックグラウンド解析後にポーリング/取得可能
        }
    }

class ImportUrlRequest(BaseModel):
    board_id: str
    image_url: str
    caption: Optional[str] = None
    pos_x: float = 0.0
    pos_y: float = 0.0

@router.post("/import-url")
async def import_from_url(
    payload: ImportUrlRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """外部URL（またはInstagramメディアURL）から画像を取り込み"""
    board = db.query(Board).filter(Board.id == payload.board_id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    unique_filename = f"{uuid.uuid4().hex}.jpg"
    saved_path = settings.UPLOAD_DIR / unique_filename

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(payload.image_url)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch image from URL")
            with open(saved_path, "wb") as f:
                f.write(resp.content)
            content_len = len(resp.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image download error: {str(e)}")

    try:
        with Image.open(saved_path) as img:
            w, h = img.size
    except Exception:
        w, h = 400, 400

    aspect_ratio = float(w) / float(h) if h > 0 else 1.0
    max_dim = 360.0
    if w >= h:
        item_w = max_dim
        item_h = max_dim / aspect_ratio
    else:
        item_h = max_dim
        item_w = max_dim * aspect_ratio

    relative_url = f"/uploads/{unique_filename}"
    media_item = MediaItem(
        user_id=user.id,
        board_id=payload.board_id,
        source_type="external_url",
        original_file_name=payload.caption or "imported_reference.jpg",
        file_path=relative_url,
        source_url=payload.image_url,
        file_size=content_len,
        width=w,
        height=h,
        aspect_ratio=aspect_ratio
    )
    db.add(media_item)
    db.commit()
    db.refresh(media_item)

    max_z = db.query(CanvasItem).filter(CanvasItem.board_id == payload.board_id).count() + 1
    canvas_item = CanvasItem(
        board_id=payload.board_id,
        media_item_id=media_item.id,
        pos_x=payload.pos_x,
        pos_y=payload.pos_y,
        width=item_w,
        height=item_h,
        z_index=max_z,
        caption=payload.caption
    )
    db.add(canvas_item)
    db.commit()
    db.refresh(canvas_item)

    from app.core.database import SessionLocal
    background_tasks.add_task(perform_ai_analysis, media_item.id, str(saved_path), SessionLocal)

    return {
        "item": {
            "id": canvas_item.id,
            "board_id": canvas_item.board_id,
            "media_item_id": media_item.id,
            "pos_x": canvas_item.pos_x,
            "pos_y": canvas_item.pos_y,
            "width": canvas_item.width,
            "height": canvas_item.height,
            "rotation": canvas_item.rotation,
            "z_index": canvas_item.z_index,
            "media": {
                "id": media_item.id,
                "file_path": media_item.file_path,
                "source_type": media_item.source_type,
                "original_file_name": media_item.original_file_name,
                "width": media_item.width,
                "height": media_item.height,
                "aspect_ratio": media_item.aspect_ratio,
            },
            "ai_analysis": None
        }
    }

@router.post("/{media_id}/reanalyze")
async def reanalyze_media(
    media_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手動でAI解析を再実行・同期実行"""
    media = db.query(MediaItem).filter(MediaItem.id == media_id, MediaItem.user_id == user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if media.source_type == "pixiv":
        from app.routers.pixiv import _client_for, _get_account
        from app.services.pixiv_client import PixivApiError, normalize_illust
        from app.services.pixiv_ai_policy import resolve_pixiv_ai_policy

        if not media.pixiv_illust_id or not _get_account(db, user):
            raise HTTPException(status_code=403, detail="Pixiv作品の作者設定を確認できないためAI解析できません")
        try:
            client = await _client_for(db, user)
            detail = await client.get_illust_detail(media.pixiv_illust_id)
        except PixivApiError as exc:
            raise HTTPException(status_code=503, detail="Pixiv作品の作者設定を確認できません") from exc
        policy = await resolve_pixiv_ai_policy(normalize_illust(detail)) if detail else "unknown"
        media.ai_analysis_policy = policy
        db.commit()
        if policy != "allowed":
            reasons = {
                "blocked": "作者がAI学習禁止を明示しているためAI解析できません",
                "unlisted": "Danbooruで同じPixiv作品IDの掲載を確認できないためAI解析できません",
                "unknown": "Pixiv作品またはDanbooru掲載を確認できないためAI解析できません",
            }
            raise HTTPException(status_code=403, detail=reasons.get(policy, reasons["unknown"]))

    file_name = Path(media.file_path).name
    actual_path = settings.UPLOAD_DIR / file_name
    if not actual_path.exists():
        raise HTTPException(status_code=404, detail="File on disk not found")

    analysis = await analyze_image_with_vision(actual_path)
    _save_analysis(db, media_id, analysis)
    # 内部キー（_model）はレスポンスに含めない
    return {k: v for k, v in analysis.items() if not k.startswith("_")}


@router.get("/ai/provider")
def get_ai_provider():
    """現在どの AI プロバイダが使われるかを返す（デバッグ / UI 表示用）"""
    return describe_active_provider()
