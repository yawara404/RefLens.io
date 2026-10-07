import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "RefLens.io API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{Path(__file__).resolve().parent.parent.parent}/reflens.db"
    )

    # JWT Authentication
    # 固定の既定値は持たない（コードを公開した瞬間にトークンを偽装できるため）。
    # backend/.env の SECRET_KEY が正で、未設定時はプロセスごとにランダムな鍵を割り当てる。
    SECRET_KEY: str = os.getenv("SECRET_KEY", "") or secrets.token_urlsafe(48)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # ---------------------------------------------------------
    # Ollama（ローカル LLM）
    # ---------------------------------------------------------
    # AI プロバイダの選択: ollama / gemini / heuristic
    # 空欄のときは「Ollama が起動していれば ollama、していなければ gemini → heuristic」の順で自動で選ぶ。
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    # 解析に使うローカルモデル。gemma3 は画像（vision）に対応しているため、
    # 構図・光・衣装の解析もそのまま行える。
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma3:4b")
    # コンテキスト長。大きいと VRAM/メモリを食うので 4096 程度が無難。
    OLLAMA_NUM_CTX: int = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
    # Ollama へのリクエストタイムアウト（秒）。ローカル推論は-cold start 含めて遅い。
    OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "180"))

    # Instagram API
    INSTAGRAM_APP_ID: str = os.getenv("INSTAGRAM_APP_ID", "")
    INSTAGRAM_APP_SECRET: str = os.getenv("INSTAGRAM_APP_SECRET", "")
    INSTAGRAM_REDIRECT_URI: str = os.getenv(
        "INSTAGRAM_REDIRECT_URI", 
        "http://localhost:3000/auth/instagram/callback"
    )

    # pixiv アプリ向けの非公開 API。認証情報はサーバーにのみ設定する。
    PIXIV_CLIENT_ID: str = os.getenv("PIXIV_CLIENT_ID", "")
    PIXIV_CLIENT_SECRET: str = os.getenv("PIXIV_CLIENT_SECRET", "")
    PIXIV_TOKEN_ENCRYPTION_KEY: str = os.getenv("PIXIV_TOKEN_ENCRYPTION_KEY", "")
    # i.pximg.net の画像取得には Referer ヘッダが必須。叩き先ホストを変更可能にしておく。
    PIXIV_IMAGE_HOST: str = os.getenv("PIXIV_IMAGE_HOST", "i.pximg.net")

    # サブパス配信（Cloudflare Tunnel の https://art.wawa-app.me/RefLens.io/ など）。
    # この接頭辞が付いたリクエストは剥がしてから FastAPI のルーティングに渡す。
    # ローカル起動時は空のまま。
    ROOT_PATH: str = os.getenv("ROOT_PATH", "")

    # Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    # 画像プロキシのキャッシュディレクトリ
    PIXIV_CACHE_DIR: Path = BASE_DIR / ".pixiv-cache"
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://localhost:3120",
        "http://127.0.0.1:3120",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ]

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Ensure required directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.PIXIV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
