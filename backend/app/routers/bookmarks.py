import re
import uuid
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.models import AIAnalysis, Board, CanvasItem, Folder, MediaItem, User
from app.routers.auth import get_current_user
from app.routers.media import perform_ai_analysis
from app.services.pixiv_ai_policy import resolve_pixiv_ai_policy

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

class BookmarkAddRequest(BaseModel):
    url: str
    title: Optional[str] = None
    folder_name: Optional[str] = "All References"
    board_id: Optional[str] = None # 即座にボードに並べる場合は指定
    pos_x: Optional[float] = 0.0
    pos_y: Optional[float] = 0.0
    auto_tag: Optional[bool] = None

class PlaceBookmarkRequest(BaseModel):
    board_id: str
    bookmark_id: str
    pos_x: float = 0.0
    pos_y: float = 0.0

class UpdateTagsRequest(BaseModel):
    tags: List[str]

class AddTagRequest(BaseModel):
    tag: str

class FolderCreateRequest(BaseModel):
    name: str
    color: Optional[str] = "#6366f1"
    icon: Optional[str] = "folder"

class UpdateFolderRequest(BaseModel):
    folder_name: str

class BatchUpdateFolderRequest(BaseModel):
    bookmark_ids: List[str]
    folder_name: str

class BatchDeleteBookmarksRequest(BaseModel):
    bookmark_ids: List[str]

class FolderUpdateRequest(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None

# ----------------------------------------------------------------------
# pixiv 作品メタデータ取得（ローカル接続済みなら非公開App APIを使う）
# ----------------------------------------------------------------------
async def _fetch_pixiv_metadata(db: Session, user: User, illust_id: str) -> Optional[dict]:
    """非公開App APIから作品情報を取得する。失敗時は None。"""
    from app.services.pixiv_client import PixivApiError, normalize_illust
    from app.routers.pixiv import _client_for, _get_account

    # 未接続（共通ゲストを含む）は何もしない。
    if not _get_account(db, user):
        return None

    try:
        client = await _client_for(db, user)
        detail = await client.get_illust_detail(illust_id)
        if not detail:
            return None

        illust = normalize_illust(detail)
        image_url = illust.get("original_url") or illust.get("image_url")
        if not image_url:
            return None

        return {
            "id": illust_id,
            "title": illust["title"],
            "author_name": illust["author_name"],
            "image_url": image_url,
            "tags": illust.get("tags", []),
            "caption": illust.get("caption", ""),
            "pixiv_illust_id": illust_id,
        }
    except PixivApiError:
        return None
    except Exception:
        return None


# ユーティリティ: URLから簡易メタデータと画像を取得
async def extract_url_metadata(url: str, db: Session = None, user: User = None):
    """Instagramや一般WebページのURLから画像URLとタイトルを抽出"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Pixiv artwork URL判定 (https://www.pixiv.net/artworks/12345678 等)
    if "pixiv.net" in domain:
        art_id_match = re.search(r"artworks/(\d+)", url)
        art_id = art_id_match.group(1) if art_id_match else None

        # ローカル接続済みならApp APIから実データを取得する
        if art_id and db is not None and user is not None:
            real = await _fetch_pixiv_metadata(db, user, art_id)
            if real:
                return {
                    "source_type": "pixiv",
                    "title": real["title"],
                    "author_name": real["author_name"],
                    "favicon_url": "https://www.pixiv.net/favicon.ico",
                    "image_url": real["image_url"],
                    "folder_name": "All References",
                    "pixiv_illust_id": real["pixiv_illust_id"],
                    "tags": real["tags"],
                    "ai_analysis_policy": await resolve_pixiv_ai_policy(real),
                }

        # 未ログイン / API失敗時は従来のプリセットへフォールバック
        fallback_id = art_id or "artwork"
        pixiv_presets = [
            {
                "title": f"【ポーズ・骨格研究】コントラポストと重心の捉え方 (pixiv #{fallback_id})",
                "author": "絵師ポーズ研究室",
                "image": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=1000&auto=format&fit=crop&q=80",
                "folder": "Poses & Anatomy",
            },
            {
                "title": f"【衣装構造】服のシワ・生地のテンションと重力表現 (pixiv #{fallback_id})",
                "author": "デジタル作画工房",
                "image": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=1000&auto=format&fit=crop&q=80",
                "folder": "Costumes & Folds",
            },
            {
                "title": f"【ライティング講座】逆光とリムライトのドラマティック演出 (pixiv #{fallback_id})",
                "author": "背景美術スタジオ",
                "image": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000&auto=format&fit=crop&q=80",
                "folder": "Lighting & Values",
            },
        ]
        # IDからハッシュして一貫したプリセットを選択
        idx = hash(fallback_id) % len(pixiv_presets)
        preset = pixiv_presets[idx]

        return {
            "source_type": "pixiv",
            "title": preset["title"],
            "author_name": preset["author"],
            "favicon_url": "https://www.pixiv.net/favicon.ico",
            "image_url": preset["image"],
            "folder_name": preset["folder"],
        }

    # Instagram投稿の場合のフォールバック・推論
    if "instagram.com" in domain:
        favicon = "https://www.instagram.com/favicon.ico"
        author = "@studio_artlens"
        title = "Instagram Visual Reference"
        image_url = url if any(url.lower().endswith(ext) for ext in [".jpg", ".png", ".webp"]) else (
            "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000&auto=format&fit=crop&q=80"
        )
        return {
            "source_type": "instagram",
            "title": title,
            "author_name": author,
            "favicon_url": favicon,
            "image_url": image_url,
            "folder_name": "Instagram Sync"
        }

    # 通常の画像URL
    if any(parsed.path.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
        return {
            "source_type": "web_bookmark",
            "title": Path(parsed.path).name or "Web Image Reference",
            "author_name": domain,
            "favicon_url": f"https://{domain}/favicon.ico",
            "image_url": url
        }

    # 一般Webページ: OGP画像取得を試行
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 RefLens/1.0"})
            if resp.status_code == 200:
                html = resp.text
                # タイトル抽出
                title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else domain
                # OGP画像抽出
                og_image_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
                og_image = og_image_match.group(1) if og_image_match else None

                return {
                    "source_type": "web_bookmark",
                    "title": title[:200],
                    "author_name": domain,
                    "favicon_url": f"https://{domain}/favicon.ico",
                    "image_url": og_image or "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800&auto=format&fit=crop&q=80"
                }
    except Exception:
        pass

    return {
        "source_type": "web_bookmark",
        "title": f"Bookmark from {domain}",
        "author_name": domain,
        "favicon_url": f"https://{domain}/favicon.ico",
        "image_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=800&auto=format&fit=crop&q=80"
    }

_LOCAL_PALETTE_CACHE: dict[str, list[str]] = {}
_DUMMY_PALETTES = {
    ("#ffffff", "#000000", "#808080", "#cccccc", "#333333"),
    ("#ffffff", "#000000", "#808080", "#c0c0c0", "#e0e0e0"),
    ("#d3d3d3", "#ffffff", "#000000", "#808080", "#c0c0c0"),
    ("#d3d3d3", "#ffffff", "#000000", "#808080", "#a9a9a9"),
    ("#ffffff", "#333333", "#808080", "#eeeeee", "#000000"),
}


def _resolve_item_palette(file_path: Optional[str], ai_palette: Optional[list]) -> list[str]:
    """AI解析パレットが有効ならそれを使い、未解析やプレースホルダ時は画像から5色を抽出する。"""
    if ai_palette and len(ai_palette) > 0:
        normalized = tuple(str(c).lower() for c in ai_palette)
        if normalized not in _DUMMY_PALETTES:
            return list(ai_palette)

    if not file_path:
        return list(ai_palette or [])

    if file_path in _LOCAL_PALETTE_CACHE:
        return _LOCAL_PALETTE_CACHE[file_path]

    try:
        filename = Path(file_path).name
        local_file = settings.UPLOAD_DIR / filename
        if not local_file.exists():
            return list(ai_palette or [])

        with Image.open(local_file) as img:
            small = img.convert("RGB").resize((64, 64))
            quantized = small.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
            raw_pal = quantized.getpalette() or []
            counts = sorted(quantized.getcolors() or [], reverse=True)
            colors: list[str] = []
            for _cnt, idx in counts:
                base = idx * 3
                if base + 2 >= len(raw_pal):
                    continue
                r, g, b = raw_pal[base], raw_pal[base + 1], raw_pal[base + 2]
                hex_code = f"#{r:02x}{g:02x}{b:02x}"
                if hex_code not in colors:
                    colors.append(hex_code)
                if len(colors) >= 5:
                    break
            if colors:
                _LOCAL_PALETTE_CACHE[file_path] = colors
                return colors
    except Exception:
        pass

    return list(ai_palette or [])


@router.get("/ollama-search")
@router.get("/galaxy-search")
def ollama_ai_search(
    q: str = "",
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ollama AI ギャラリー風 視覚セマンティック画像検索（被写体・構図・色彩認識）"""
    from app.services.visual_intelligence import search_galaxy_ai
    return search_galaxy_ai(query=q, db=db, user_id=user.id, limit=limit)


@router.get("/search-suggest")
def get_search_suggestions(
    q: str = "",
    limit: int = 8,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """検索キーワードに対する予測タグ・同義語（Ollama / 辞書）および Ollama AI 認識結果を取得"""
    from app.services.search_suggest import predict_search_suggestions
    from app.services.visual_intelligence import search_galaxy_ai

    res = predict_search_suggestions(query=q, db=db, user_id=user.id, limit=limit)
    if q.strip():
        try:
            galaxy_res = search_galaxy_ai(query=q, db=db, user_id=user.id, limit=30)
            ai_data = {
                "intent": galaxy_res.get("intent"),
                "matched_ids": galaxy_res.get("matched_ids", []),
                "total": galaxy_res.get("total", 0),
                "matches": galaxy_res.get("matches", []),
            }
            res["ollama_ai"] = ai_data
            res["galaxy_ai"] = ai_data
        except Exception as exc:
            logger.debug("Ollama AI search integrate error: %s", exc)
            res["ollama_ai"] = None
            res["galaxy_ai"] = None
    else:
        res["ollama_ai"] = None
        res["galaxy_ai"] = None

    return res


@router.get("/")
def get_bookmarks(
    source_type: Optional[str] = None, # all, instagram, web_bookmark, local_upload
    folder_name: Optional[str] = None,
    tag: Optional[str] = None,
    query: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ストックされた全リファレンス資料・Webブックマーク一覧を取得"""
    q = (
        db.query(MediaItem)
        .options(joinedload(MediaItem.ai_analysis))
        .filter(MediaItem.user_id == user.id)
    )

    if source_type and source_type != "all":
        q = q.filter(MediaItem.source_type == source_type)

    if folder_name and folder_name != "All References":
        q = q.filter(MediaItem.folder_name == folder_name)

    items = q.order_by(MediaItem.created_at.desc()).all()

    results = []
    for it in items:
        ai = it.ai_analysis
        # タグフィルタリング
        if tag:
            if not ai or not ai.tags_json or tag.lower() not in [t.lower() for t in ai.tags_json]:
                continue

        # クエリ検索
        if query:
            q_lower = query.lower()
            text_corpus = f"{it.title or ''} {it.original_file_name or ''} {it.source_url or ''} {it.folder_name or ''}"
            if ai:
                text_corpus += f" {ai.composition} {ai.lighting} {ai.pose_anatomy} {' '.join(ai.tags_json or [])}"
            if q_lower not in text_corpus.lower():
                continue

        palette = _resolve_item_palette(it.file_path, ai.palette_json if ai else None)
        ai_payload = {
            "composition": ai.composition if ai else "",
            "lighting": ai.lighting if ai else "",
            "pose_anatomy": ai.pose_anatomy if ai else "",
            "costume_structure": ai.costume_structure if ai else "",
            "palette": palette,
            "tags": (ai.tags_json or []) if ai else [],
        } if (ai or palette) else None

        results.append({
            "id": it.id,
            "title": it.title or it.original_file_name or "Untitled Reference",
            "file_path": it.file_path,
            "source_type": it.source_type,
            "ai_analysis_policy": it.ai_analysis_policy,
            "source_url": it.source_url,
            "author_name": it.author_name,
            "favicon_url": it.favicon_url,
            "width": it.width,
            "height": it.height,
            "aspect_ratio": it.aspect_ratio,
            "folder_name": it.folder_name,
            "board_id": it.board_id,
            "created_at": it.created_at.isoformat(),
            "ai_analysis": ai_payload,
        })

    return results

@router.post("/add")
async def add_bookmark(
    payload: BookmarkAddRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """InstagramやWebのURLをワンクリックでブックマーク保存（画像DL & AI解析）"""
    meta = await extract_url_metadata(payload.url, db, user)

    image_url = meta.get("image_url", payload.url)

    # pixiv画像 (i.pximg.net) は Referer ヘッダが無いと403になるため公式クライアントで取得する
    is_pixiv = meta.get("source_type") == "pixiv" and bool(meta.get("pixiv_illust_id"))
    unique_filename = f"{uuid.uuid4().hex}.jpg"
    saved_path = settings.UPLOAD_DIR / unique_filename

    if is_pixiv:
        from app.services.pixiv_client import PixivClient

        downloaded, dl_error = await PixivClient().download_image(image_url, settings.UPLOAD_DIR)
        if downloaded:
            saved_path = downloaded
        else:
            print(f"pixiv download failed ({payload.url}): {dl_error}")
            saved_path = settings.UPLOAD_DIR / "seed_ref_1.jpg"
    else:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(image_url)
                if resp.status_code == 200:
                    with open(saved_path, "wb") as f:
                        f.write(resp.content)
                else:
                    raise Exception("Failed to download image")
        except Exception:
            # ダウンロード失敗時はデフォルトサンプル
            saved_path = settings.UPLOAD_DIR / "seed_ref_1.jpg"

    # 画像サイズ取得
    try:
        with Image.open(saved_path) as img:
            w, h = img.size
    except Exception:
        w, h = 400, 400

    aspect_ratio = float(w) / float(h) if h > 0 else 1.0
    relative_url = f"/uploads/{saved_path.name}"

    media_item = MediaItem(
        user_id=user.id,
        board_id=payload.board_id,
        source_type=meta.get("source_type", "web_bookmark"),
        ai_analysis_policy=meta.get("ai_analysis_policy", "allowed"),
        title=payload.title or meta.get("title"),
        original_file_name=meta.get("title"),
        author_name=meta.get("author_name"),
        favicon_url=meta.get("favicon_url"),
        file_path=relative_url,
        source_url=payload.url,
        pixiv_illust_id=meta.get("pixiv_illust_id"),
        pixiv_page_index=0 if meta.get("pixiv_illust_id") else None,
        file_size=saved_path.stat().st_size if saved_path.exists() else 0,
        width=w,
        height=h,
        aspect_ratio=aspect_ratio,
        folder_name=payload.folder_name or meta.get("folder_name") or "All References",
    )
    db.add(media_item)
    db.commit()
    db.refresh(media_item)

    # ボード指定がある場合はキャンバスにも配置
    canvas_item = None
    if payload.board_id:
        max_dim = 360.0
        if w >= h:
            item_w = max_dim
            item_h = max_dim / aspect_ratio
        else:
            item_h = max_dim
            item_w = max_dim * aspect_ratio

        max_z = db.query(CanvasItem).filter(CanvasItem.board_id == payload.board_id).count() + 1
        canvas_item = CanvasItem(
            board_id=payload.board_id,
            media_item_id=media_item.id,
            pos_x=payload.pos_x or 50.0,
            pos_y=payload.pos_y or 50.0,
            width=item_w,
            height=item_h,
            z_index=max_z,
            caption=media_item.title
        )
        db.add(canvas_item)
        db.commit()
        db.refresh(canvas_item)

    # バックグラウンドAI解析（自動タグ付けが有効な場合のみ実行）
    should_analyze = (
        payload.auto_tag if payload.auto_tag is not None else getattr(user, "auto_tagging", True)
    )
    if should_analyze:
        background_tasks.add_task(
            perform_ai_analysis,
            media_item.id,
            str(saved_path),
            SessionLocal,
            list(meta.get("tags") or [])[:12],
        )

    return {
        "success": True,
        "bookmark_id": media_item.id,
        "media_item": {
            "id": media_item.id,
            "title": media_item.title,
            "file_path": media_item.file_path,
            "source_type": media_item.source_type,
            "source_url": media_item.source_url,
            "author_name": media_item.author_name,
            "favicon_url": media_item.favicon_url,
            "folder_name": media_item.folder_name,
        },
        "canvas_item_id": canvas_item.id if canvas_item else None
    }

@router.post("/place-on-board")
def place_bookmark_on_board(
    payload: PlaceBookmarkRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ライブラリ内のブックマークをキャンバスボードへドラッグ＆ドロップ配置"""
    media = db.query(MediaItem).filter(MediaItem.id == payload.bookmark_id, MediaItem.user_id == user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    board = db.query(Board).filter(Board.id == payload.board_id, Board.user_id == user.id).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    aspect_ratio = media.aspect_ratio if media.aspect_ratio > 0 else 1.0
    max_dim = 360.0
    if media.width >= media.height:
        item_w = max_dim
        item_h = max_dim / aspect_ratio
    else:
        item_h = max_dim
        item_w = max_dim * aspect_ratio

    max_z = db.query(CanvasItem).filter(CanvasItem.board_id == payload.board_id).count() + 1

    canvas_item = CanvasItem(
        board_id=payload.board_id,
        media_item_id=media.id,
        pos_x=payload.pos_x,
        pos_y=payload.pos_y,
        width=item_w,
        height=item_h,
        z_index=max_z,
        caption=media.title or media.original_file_name
    )
    db.add(canvas_item)
    db.commit()
    db.refresh(canvas_item)

    ai = media.ai_analysis
    return {
        "success": True,
        "item": {
            "id": canvas_item.id,
            "board_id": canvas_item.board_id,
            "media_item_id": media.id,
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
            "caption": canvas_item.caption,
            "media": {
                "id": media.id,
                "file_path": media.file_path,
                "source_type": media.source_type,
                "ai_analysis_policy": media.ai_analysis_policy,
                "source_url": media.source_url,
                "original_file_name": media.original_file_name,
                "author_name": media.author_name,
                "favicon_url": media.favicon_url,
                "width": media.width,
                "height": media.height,
                "aspect_ratio": media.aspect_ratio,
            },
            "ai_analysis": {
                "composition": ai.composition,
                "lighting": ai.lighting,
                "pose_anatomy": ai.pose_anatomy,
                "costume_structure": ai.costume_structure,
                "palette": ai.palette_json,
                "tags": ai.tags_json,
            } if ai else None
        }
    }

@router.put("/batch/folder")
def batch_update_bookmark_folder(
    payload: BatchUpdateFolderRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not payload.bookmark_ids:
        return {"count": 0, "message": "No items provided"}

    updated = db.query(MediaItem).filter(
        MediaItem.id.in_(payload.bookmark_ids),
        MediaItem.user_id == user.id
    ).update({MediaItem.folder_name: payload.folder_name}, synchronize_session=False)
    db.commit()
    return {"count": updated, "message": f"{updated} items moved to {payload.folder_name}"}

@router.post("/batch/delete")
@router.delete("/batch")
def batch_delete_bookmarks(
    payload: BatchDeleteBookmarksRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """複数のブックマークをまとめて削除する。"""
    if not payload.bookmark_ids:
        return {"count": 0, "message": "No items provided"}

    media_items = db.query(MediaItem).filter(
        MediaItem.id.in_(payload.bookmark_ids),
        MediaItem.user_id == user.id
    ).all()
    for media in media_items:
        db.delete(media)
    db.commit()
    return {"count": len(media_items), "message": f"{len(media_items)} items deleted"}

@router.put("/{bookmark_id}/folder")
def update_bookmark_folder(
    bookmark_id: str,
    payload: UpdateFolderRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    media = db.query(MediaItem).filter(MediaItem.id == bookmark_id, MediaItem.user_id == user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    media.folder_name = payload.folder_name
    db.commit()
    return {"message": "Folder updated"}

@router.put("/{bookmark_id}/tags")
def update_bookmark_tags(
    bookmark_id: str,
    payload: UpdateTagsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ブックマークのタグ一覧を編集・更新する"""
    media = db.query(MediaItem).filter(MediaItem.id == bookmark_id, MediaItem.user_id == user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    cleaned_tags = []
    seen = set()
    for t in payload.tags:
        t_clean = t.strip().lstrip("#")
        if t_clean and t_clean.lower() not in seen:
            seen.add(t_clean.lower())
            cleaned_tags.append(t_clean)

    ai = db.query(AIAnalysis).filter(AIAnalysis.media_item_id == media.id).first()
    if ai:
        ai.tags_json = cleaned_tags
    else:
        ai = AIAnalysis(
            media_item_id=media.id,
            composition="",
            lighting="",
            pose_anatomy="",
            costume_structure="",
            palette_json=[],
            tags_json=cleaned_tags,
            analysis_model="custom",
        )
        db.add(ai)
    db.commit()
    db.refresh(ai)
    return {"success": True, "bookmark_id": media.id, "tags": ai.tags_json}

@router.post("/{bookmark_id}/tags")
def add_bookmark_tag(
    bookmark_id: str,
    payload: AddTagRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ブックマークにタグを追加する"""
    tag = payload.tag.strip().lstrip("#")
    if not tag:
        raise HTTPException(status_code=400, detail="Tag cannot be empty")

    media = db.query(MediaItem).filter(MediaItem.id == bookmark_id, MediaItem.user_id == user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    ai = db.query(AIAnalysis).filter(AIAnalysis.media_item_id == media.id).first()
    tags = list(ai.tags_json or []) if ai else []
    if tag.lower() not in [t.lower() for t in tags]:
        tags.append(tag)

    if ai:
        ai.tags_json = tags
    else:
        ai = AIAnalysis(
            media_item_id=media.id,
            composition="",
            lighting="",
            pose_anatomy="",
            costume_structure="",
            palette_json=[],
            tags_json=tags,
            analysis_model="custom",
        )
        db.add(ai)
    db.commit()
    db.refresh(ai)
    return {"success": True, "bookmark_id": media.id, "tags": ai.tags_json}

@router.delete("/{bookmark_id}/tags/{tag}")
def delete_bookmark_tag(
    bookmark_id: str,
    tag: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ブックマークから特定のタグを削除する"""
    media = db.query(MediaItem).filter(MediaItem.id == bookmark_id, MediaItem.user_id == user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    ai = db.query(AIAnalysis).filter(AIAnalysis.media_item_id == media.id).first()
    if ai and ai.tags_json:
        clean = tag.strip().lstrip("#").lower()
        ai.tags_json = [t for t in ai.tags_json if t.lower() != clean]
        db.commit()
        db.refresh(ai)
        return {"success": True, "bookmark_id": media.id, "tags": ai.tags_json}
    return {"success": True, "bookmark_id": media.id, "tags": []}

@router.post("/{bookmark_id}/analyze")
async def manual_analyze_bookmark(
    bookmark_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ブックマークに対して手動でAIタグ・解析を実行する"""
    media = db.query(MediaItem).filter(MediaItem.id == bookmark_id, MediaItem.user_id == user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    file_name = Path(media.file_path).name
    saved_path = settings.UPLOAD_DIR / file_name
    if not saved_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found on disk")

    background_tasks.add_task(
        perform_ai_analysis,
        media.id,
        str(saved_path),
        SessionLocal,
        None,
        True,
    )
    return {"success": True, "message": "AI analysis started in background"}

@router.delete("/{bookmark_id}")
def delete_bookmark(
    bookmark_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    media = db.query(MediaItem).filter(MediaItem.id == bookmark_id, MediaItem.user_id == user.id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(media)
    db.commit()
    return {"message": "Bookmark deleted"}

@router.get("/folders")
def list_folders(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """フォルダ一覧とそれぞれのアイテム数を集計"""
    # 既存の全フォルダ名を集計
    default_folders = [
        {"name": "All References", "icon": "layers", "color": "#6366f1"},
        {"name": "Instagram Sync", "icon": "instagram", "color": "#ec4899"},
        {"name": "Composition & Perspective", "icon": "compass", "color": "#06b6d4"},
        {"name": "Lighting & Values", "icon": "sun", "color": "#f59e0b"},
        {"name": "Poses & Anatomy", "icon": "user", "color": "#10b981"},
        {"name": "Costumes & Folds", "icon": "shirt", "color": "#a855f7"},
    ]

    custom_folders = db.query(Folder).filter(Folder.user_id == user.id).all()
    folder_counts = dict(
        db.query(MediaItem.folder_name, func.count(MediaItem.id))
        .filter(MediaItem.user_id == user.id)
        .group_by(MediaItem.folder_name)
        .all()
    )
    total_count = sum(folder_counts.values())

    res = []
    for f in default_folders:
        count = total_count if f["name"] == "All References" else folder_counts.get(f["name"], 0)
        res.append({
            "name": f["name"],
            "icon": f["icon"],
            "color": f["color"],
            "count": count
        })

    for cf in custom_folders:
        count = folder_counts.get(cf.name, 0)
        res.append({
            "id": cf.id,
            "name": cf.name,
            "icon": cf.icon,
            "color": cf.color,
            "count": count
        })

    return res

@router.post("/folders")
def create_folder(
    payload: FolderCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    folder = Folder(
        user_id=user.id,
        name=payload.name,
        color=payload.color or "#6366f1",
        icon=payload.icon or "folder"
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "name": folder.name, "color": folder.color, "icon": folder.icon}

@router.put("/folders/{folder_id}")
def update_folder(
    folder_id: str,
    payload: FolderUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザー作成フォルダの名前・色・アイコンを更新する。

    folder_name は MediaItem 側に文字列で保持しているため、名前を変えた場合は
    そのフォルダに入っている資料の folder_name もまとめて追従させる。
    """
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    old_name = folder.name
    new_name = (payload.name or "").strip()
    if new_name and new_name != old_name:
        if new_name == "All References":
            raise HTTPException(status_code=400, detail="Reserved folder name")
        duplicated = db.query(Folder).filter(
            Folder.user_id == user.id, Folder.name == new_name, Folder.id != folder.id
        ).first()
        if duplicated:
            raise HTTPException(status_code=409, detail="Folder already exists")

        folder.name = new_name
        db.query(MediaItem).filter(
            MediaItem.user_id == user.id, MediaItem.folder_name == old_name
        ).update({MediaItem.folder_name: new_name}, synchronize_session=False)

    if payload.color:
        folder.color = payload.color
    if payload.icon:
        folder.icon = payload.icon

    db.commit()
    db.refresh(folder)
    return {"id": folder.id, "name": folder.name, "color": folder.color, "icon": folder.icon}

@router.delete("/folders/{folder_id}")
def delete_folder(
    folder_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザー作成フォルダを削除する。

    中の資料は削除せず "All References" へ戻す（資料を失わせないため）。
    """
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    db.query(MediaItem).filter(
        MediaItem.user_id == user.id, MediaItem.folder_name == folder.name
    ).update({MediaItem.folder_name: "All References"}, synchronize_session=False)

    db.delete(folder)
    db.commit()
    return {"message": "Folder deleted"}
