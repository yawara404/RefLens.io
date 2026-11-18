from contextlib import asynccontextmanager
import httpx

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.models.models import User, Board, MediaItem, CanvasItem, AIAnalysis
from app.routers import auth, boards, media, instagram, bookmarks, pixiv
from app.services.storage import storage

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_initial_demo_data()
    print(f"[startup] media storage backend: {storage.mode} (bucket={storage.bucket_name or '-'})")
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Smart Infinite Canvas Reference Management for Concept Artists & Illustrators",
    # root_path は uvicorn の --root-path でも scope に入るため、両方に渡すと
    # prefix が二重に Inject されて全ルートが404になる。設定は一方のみ。
    # ここでは uvicorn 側（start.sh）が渡さないので FastAPI 側で受け取る。
    root_path=settings.ROOT_PATH or "",
)

if settings.ROOT_PATH:
    # Starlette 1.7+ は root_path を自前で処理するため、接頭辞を剥ぐ
    # ミドルウェアは不要（付けると mount に到達できなくなる）。
    print(f"[startup] serving under root path: {settings.ROOT_PATH}")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Uploaded images delivery (local cache + Cloudflare R2 fallback)
#
# root_path を指定したASGI app では、Starlette はルート照合時に scope["path"] から
# root_path を差し引く（検証済み: FastAPI(root_path=...) 単体で 200 になる）。
# そのためルート定義は素の "/uploads/{file_path:path}" とする。
@app.api_route("/uploads/{file_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def serve_uploaded_media(file_path: str, request: Request):
    head_only = request.method == "HEAD"
    try:
        delivery = await storage.get_delivery(file_path, head_only=head_only)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not delivery:
        raise HTTPException(status_code=404, detail="File not found")

    if delivery.local_path is not None:
        return FileResponse(
            path=str(delivery.local_path),
            media_type=delivery.content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    headers = {"Cache-Control": "public, max-age=86400"}
    if delivery.etag:
        headers["ETag"] = delivery.etag
    if delivery.content_length is not None:
        headers["Content-Length"] = str(delivery.content_length)

    if delivery.etag and request.headers.get("if-none-match") == delivery.etag:
        if delivery.stream_body is not None:
            delivery.stream_body.close()
        return Response(status_code=304, headers=headers)

    if head_only:
        return Response(status_code=200, media_type=delivery.content_type, headers=headers)

    body = delivery.stream_body

    def iter_r2_chunks():
        try:
            for chunk in body.iter_chunks(chunk_size=65536):
                if chunk:
                    yield chunk
        finally:
            body.close()

    return StreamingResponse(
        iter_r2_chunks(),
        media_type=delivery.content_type,
        headers=headers,
    )

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(boards.router, prefix=settings.API_V1_STR)
app.include_router(media.router, prefix=settings.API_V1_STR)
app.include_router(instagram.router, prefix=settings.API_V1_STR)
app.include_router(bookmarks.router, prefix=settings.API_V1_STR)
app.include_router(pixiv.router, prefix=settings.API_V1_STR)

def seed_initial_demo_data():
    """初回起動時に美しいデモリファレンスボードと解析済みアイテムを初期化"""
    db = SessionLocal()
    try:
        # ユーザー確認
        user = db.query(User).filter(User.email == "creator@reflens.io").first()
        if not user:
            user = User(
                email="creator@reflens.io",
                username="RefLens Studio",
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # ボード確認
        board = db.query(Board).filter(Board.user_id == user.id).first()
        if not board:
            board = Board(
                user_id=user.id,
                title="Cyberpunk & Cinematic Lighting Study",
                description="イラスト制作・構図研究のためのリファレンスボード。光線とポーズ重心の分析。",
                background_theme="dark-grid",
                viewport_x=-50.0,
                viewport_y=-30.0,
                viewport_zoom=0.85
            )
            db.add(board)
            db.commit()
            db.refresh(board)

            # 初期サンプル画像データ（外部信頼Unsplash URLをダウンロードしてローカル保存またはURL参照）
            sample_references = [
                {
                    "title": "Neon Low-Angle Cyberpunk.jpg",
                    "url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=1000&auto=format&fit=crop&q=80",
                    "x": 80, "y": 60, "w": 380, "h": 500,
                    "composition": "ローアングル（アオリ構図）。被写体の威圧感と背後の都市パースをダイナミックに強調。",
                    "lighting": "冷色（シアン/ブルー）のキーライトと、輪郭を切り取る強烈なマゼンタのリムライト。高コントラスト。",
                    "pose_anatomy": "前傾姿勢で低く構えた重心。肩のラインと腰のひねりが緊張感を演出。",
                    "costume_structure": "マットな合成繊維と光沢のあるPVCレザーの異素材対比。肩周りと肘関節にシャープな折れジワ。",
                    "palette": ["#0b0d1b", "#142d4c", "#e52165", "#00fff5", "#f0e68c"],
                    "tags": ["アオリ", "サイバーパンク", "リムライト", "レザー質感", "ネオンカラー"]
                },
                {
                    "title": "Golden Sunset Rim Light Study.jpg",
                    "url": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=1000&auto=format&fit=crop&q=80",
                    "x": 520, "y": 60, "w": 420, "h": 460,
                    "composition": "三分割法と黄金螺旋を意識したポートレート構図。右上の空間に視線の抜けを配置。",
                    "lighting": "夕暮れの暖色逆光（ゴールデンアワー）。髪と肩周りに美しいハレーションと薄いフィルライト。",
                    "pose_anatomy": "リラックスした立ち姿。首筋の胸鎖乳突筋から鎖骨への自然なライン。",
                    "costume_structure": "透け感のある軽やかなシフォン生地。微風による有機的なドレーパリー（揺れシワ）。",
                    "palette": ["#2c1810", "#8c3a1b", "#d97736", "#f4b266", "#faebd7"],
                    "tags": ["逆光", "ゴールデンアワー", "シフォン素材", "三分割法", "暖色パレット"]
                },
                {
                    "title": "Action Pose Perspective Study.jpg",
                    "url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=1000&auto=format&fit=crop&q=80",
                    "x": 980, "y": 120, "w": 460, "h": 360,
                    "composition": "強烈な対角線パースペクティブ構図。手前への突き出しと広角レンズ特有のデフォルメ。",
                    "lighting": "上方45度からの指向性トップライト。筋肉の起伏に陰影がくっきりと現れる立体感表現。",
                    "pose_anatomy": "極限まで引き伸ばされたスパイラルポーズ。重心が足元にしっかり接地し安定感あり。",
                    "costume_structure": "タイトな伸縮性スポーツウェア。筋肉の筋に沿った引っ張りテンションライン。",
                    "palette": ["#111111", "#333333", "#666666", "#e63946", "#f1faee"],
                    "tags": ["対角線構図", "トップライト", "アクションポーズ", "筋肉構造", "広角パース"]
                }
            ]

            for idx, ref in enumerate(sample_references):
                file_name = f"seed_ref_{idx+1}.jpg"
                rel_path = f"/uploads/{file_name}"

                # R2 またはローカルに存在しない場合は外部URLから取得してストレージへ保存
                if not storage.exists_sync(rel_path):
                    try:
                        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                            resp = client.get(ref["url"])
                            if resp.status_code == 200:
                                rel_path = storage.save_bytes_sync(
                                    file_name, resp.content, content_type="image/jpeg"
                                )
                            else:
                                rel_path = ref["url"]
                    except Exception:
                        rel_path = ref["url"]
                else:
                    rel_path = storage.file_path_for(file_name)

                folders_map = [
                    "Composition & Perspective",
                    "Lighting & Values",
                    "Poses & Anatomy"
                ]

                media_obj = MediaItem(
                    user_id=user.id,
                    board_id=board.id,
                    source_type="instagram" if idx == 0 else "web_bookmark",
                    title=ref["title"].replace(".jpg", ""),
                    original_file_name=ref["title"],
                    author_name="@studio_artlens" if idx == 0 else "artstation.com",
                    favicon_url="https://www.instagram.com/favicon.ico" if idx == 0 else "https://www.artstation.com/favicon.ico",
                    source_url=ref["url"],
                    folder_name=folders_map[idx % len(folders_map)],
                    file_path=rel_path,
                    mime_type="image/jpeg",
                    width=ref["w"],
                    height=ref["h"],
                    aspect_ratio=float(ref["w"]) / float(ref["h"])
                )
                db.add(media_obj)
                db.commit()
                db.refresh(media_obj)

                canvas_obj = CanvasItem(
                    board_id=board.id,
                    media_item_id=media_obj.id,
                    pos_x=ref["x"],
                    pos_y=ref["y"],
                    width=ref["w"],
                    height=ref["h"],
                    rotation=0.0,
                    z_index=idx + 1,
                    caption=ref["title"]
                )
                db.add(canvas_obj)
                db.commit()

                ai_obj = AIAnalysis(
                    media_item_id=media_obj.id,
                    composition=ref["composition"],
                    lighting=ref["lighting"],
                    pose_anatomy=ref["pose_anatomy"],
                    costume_structure=ref["costume_structure"],
                    palette_json=ref["palette"],
                    tags_json=ref["tags"],
                    analysis_model="gemini-1.5-flash"
                )
                db.add(ai_obj)
                db.commit()

    except Exception as e:
        print(f"Seed demo data notice: {e}")
    finally:
        db.close()

@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }
