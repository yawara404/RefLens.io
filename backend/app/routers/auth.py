import base64
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.core.pixiv_tokens import encrypt_token
from app.models.models import Board, PixivAccount, User
from app.services.pixiv_client import PixivApiError, PixivClient, is_configured

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    username: str
    avatar_url: Optional[str] = None
    instagram_connected: bool = False
    pixiv_connected: bool = False
    pixiv_username: Optional[str] = None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# ゲスト（未ログイン時に自動割り当てされる）アカウントの識別子
GUEST_EMAIL = "creator@reflens.io"
PIXIV_CALLBACK = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
_pixiv_pending: dict[str, tuple[str, float, str, Optional[str]]] = {}


def get_or_create_guest(db: Session) -> User:
    """ゲストユーザーを取得。無ければ自動生成する。"""
    guest_user = db.query(User).filter(User.email == GUEST_EMAIL).first()
    if not guest_user:
        guest_user = User(
            email=GUEST_EMAIL,
            username="Creative Illustrator",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80"
        )
        db.add(guest_user)
        db.commit()
        db.refresh(guest_user)
    return guest_user


def issue_token(user: User) -> dict:
    """ユーザーに対応するアクセストークンを返す。"""
    return {
        "access_token": create_access_token({"sub": user.id}),
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
    }


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """現在のログインユーザーを取得。トークンがない場合はゲストユーザーを自動生成・返却"""
    if credentials:
        token = credentials.credentials
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return user
        except JWTError:
            pass

    # トークンが無い・無効ならゲストとして扱う（従来の挙動を維持）
    return get_or_create_guest(db)


def seed_starter_board(db: Session, user: User) -> Board:
    """新規ユーザー向けに、空のボードを1つ作る。"""
    board = Board(
        user_id=user.id,
        title="My Reference Board",
        description="リファレンスボード。画像をドラッグ＆ドロップして始めましょう。",
        background_theme="dark-grid",
        viewport_x=100.0,
        viewport_y=100.0,
        viewport_zoom=1.0,
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return board

@router.post("/register", response_model=Token)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    """メールアドレスとパスワードでアカウントを作る"""
    email = payload.email.strip().lower()

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="このメールアドレスは既に登録されています")

    user = User(
        email=email,
        username=payload.username.strip() or email.split("@")[0],
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # キャンバスが無いと /canvas から入れないので初期ボードを用意する
    seed_starter_board(db, user)

    return issue_token(user)


@router.post("/login", response_model=Token)
def login_user(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    """メールアドレスとパスワードでアクセストークンを発行する"""
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()

    # 「メールアドレスが無い」と「パスワードが違う」で同じメッセージを返すと、
    # 登録済みメールアドレスを探索する手がかりになる
    if not user or not verify_password(payload.password, user.hashed_password or ""):
        raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが正しくありません")

    # ゲストアカウントのパスワードは設定されていないためログイン不可
    if user.email == GUEST_EMAIL:
        raise HTTPException(status_code=401, detail="ゲストアカウントはパスワードログインできません")

    return issue_token(user)


@router.post("/guest", response_model=Token)
def login_as_guest(db: Session = Depends(get_db)):
    """ワンクリックですぐに使えるゲスト・デモログイン"""
    return issue_token(get_or_create_guest(db))

@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "instagram_connected": user.instagram_account is not None,
        "pixiv_connected": user.pixiv_account is not None,
        "pixiv_username": user.pixiv_account.pixiv_username if user.pixiv_account else None,
    }


class ProfileUpdate(BaseModel):
    username: str = Field(min_length=1, max_length=100)


@router.put("/me", response_model=UserOut)
def update_me(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """アカウントの表示名を変更する。"""
    # 共通ゲストは全訪問者が共有しているため、名前変更の対象外にする。
    if user.email == GUEST_EMAIL:
        raise HTTPException(
            status_code=403,
            detail="共通ゲストの表示名は変更できません。アカウントを作成してから変更してください。",
        )
    name = payload.username.strip()
    if not name:
        raise HTTPException(status_code=422, detail="表示名を入力してください。")

    user.username = name
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "instagram_connected": user.instagram_account is not None,
        "pixiv_connected": user.pixiv_account is not None,
        "pixiv_username": user.pixiv_account.pixiv_username if user.pixiv_account else None,
    }


class PixivLoginStart(BaseModel):
    mode: str = "login"


class PixivLoginComplete(BaseModel):
    state: str = Field(min_length=20, max_length=128)
    callback_url_or_code: str = Field(min_length=1, max_length=4096)


def _pixiv_code(value: str) -> str:
    value = value.strip()
    if value.startswith("https://"):
        parsed = urlparse(value)
        expected = urlparse(PIXIV_CALLBACK)
        if (parsed.scheme, parsed.netloc, parsed.path) != (expected.scheme, expected.netloc, expected.path):
            raise HTTPException(status_code=400, detail="PixivのコールバックURLを入力してください。")
        value = parse_qs(parsed.query).get("code", [""])[0]
    if not value or len(value) > 2048 or any(c.isspace() for c in value):
        raise HTTPException(status_code=400, detail="認可コードが無効です。")
    return value


@router.post("/pixiv/start")
def start_pixiv_login(payload: PixivLoginStart, user: User = Depends(get_current_user)):
    """Begin Pixiv's unofficial App API PKCE flow for local accounts only.

    公開プレビューでも利用できる。Refresh Token を手で貼り付けず、Pixiv のログイン
    画面（Palleria の Web Login 相当）だけで接続するための入口。
    """
    if not is_configured():
        raise HTTPException(status_code=503, detail="Pixiv接続のサーバー設定が未完了です。")
    if payload.mode not in {"login", "link"}:
        raise HTTPException(status_code=400, detail="ログイン方式が無効です。")
    if payload.mode == "link" and user.email == GUEST_EMAIL:
        raise HTTPException(status_code=401, detail="先にRefLensアカウントへログインしてください。")

    now = time.monotonic()
    for key, (_, expires, _, _) in list(_pixiv_pending.items()):
        if expires <= now:
            _pixiv_pending.pop(key, None)
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(32)
    _pixiv_pending[state] = (verifier, now + 600, payload.mode, user.id if payload.mode == "link" else None)
    url = "https://app-api.pixiv.net/web/v1/login?" + urlencode({
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "client": "pixiv-android",
    })
    return {"state": state, "login_url": url, "expires_in": 600}


@router.post("/pixiv/complete", response_model=Token)
async def complete_pixiv_login(
    payload: PixivLoginComplete,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exchange one-time code, then sign in or link to the authenticated account."""
    pending = _pixiv_pending.pop(payload.state, None)
    if not pending or pending[1] <= time.monotonic():
        raise HTTPException(status_code=400, detail="ログイン操作の期限が切れました。最初からやり直してください。")
    verifier, _, mode, linked_user_id = pending
    if mode == "link" and (user.id != linked_user_id or user.email == GUEST_EMAIL):
        raise HTTPException(status_code=403, detail="連携開始時と同じRefLensアカウントで操作してください。")
    code = _pixiv_code(payload.callback_url_or_code)
    try:
        token_data = await PixivClient.exchange_authorization_code(code, verifier)
        profile = token_data.get("user") or await PixivClient(token_data["access_token"]).get_user_me()
    except PixivApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    pixiv_id = str(profile.get("id") or "")
    if not pixiv_id:
        raise HTTPException(status_code=502, detail="Pixivアカウント情報を取得できませんでした。")
    matches = db.query(PixivAccount).filter(PixivAccount.pixiv_user_id == pixiv_id).all()
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="このPixivアカウントは複数のRefLensアカウントに登録されています。管理者に確認してください。")
    existing = matches[0] if matches else None

    if mode == "link":
        target = user
        if existing and existing.user_id != target.id:
            raise HTTPException(status_code=409, detail="このPixivアカウントは別のRefLensアカウントに連携済みです。")
        own = db.query(PixivAccount).filter(PixivAccount.user_id == target.id).first()
        if own and own.pixiv_user_id != pixiv_id:
            raise HTTPException(status_code=409, detail="別のPixivアカウントが連携済みです。先に接続を解除してください。")
    elif existing:
        target = db.query(User).filter(User.id == existing.user_id).first()
        if not target or target.email == GUEST_EMAIL:
            raise HTTPException(status_code=409, detail="共通ゲストに接続されたPixivアカウントはログインに使えません。")
    else:
        target = User(
            email=f"pixiv-{pixiv_id}@reflens.invalid",
            username=str(profile.get("name") or f"pixiv {pixiv_id}")[:100],
        )
        db.add(target)
        db.flush()

    account = existing or PixivAccount(user_id=target.id, pixiv_user_id=pixiv_id)
    if not existing:
        db.add(account)
    account.pixiv_username = str(profile.get("name") or account.pixiv_username or "pixiv")[:100]
    account.pixiv_account = str(profile.get("account") or "")[:100] or None
    account.access_token = encrypt_token(token_data["access_token"])
    account.refresh_token = encrypt_token(token_data["refresh_token"])
    account.expires_at = token_data["expires_at"]
    db.commit()
    if mode == "login" and not existing:
        seed_starter_board(db, target)
    return issue_token(target)
