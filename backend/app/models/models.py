import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    instagram_user_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    boards = relationship("Board", back_populates="user", cascade="all, delete-orphan")
    media_items = relationship("MediaItem", back_populates="user", cascade="all, delete-orphan")
    instagram_account = relationship("InstagramAccount", back_populates="user", uselist=False, cascade="all, delete-orphan")
    pixiv_account = relationship("PixivAccount", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Board(Base):
    __tablename__ = "boards"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="Untitled Reference Board", nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    viewport_x = Column(Float, default=0.0, nullable=False)
    viewport_y = Column(Float, default=0.0, nullable=False)
    viewport_zoom = Column(Float, default=1.0, nullable=False)
    background_theme = Column(String(50), default="dark-grid", nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="boards")
    canvas_items = relationship("CanvasItem", back_populates="board", cascade="all, delete-orphan")
    media_items = relationship("MediaItem", back_populates="board", cascade="all, delete-orphan")

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    board_id = Column(String(36), ForeignKey("boards.id", ondelete="SET NULL"), nullable=True, index=True)
    source_type = Column(String(50), default="local_upload", nullable=False)  # local_upload, instagram, web_bookmark
    title = Column(String(255), nullable=True)
    original_file_name = Column(String(255), nullable=True)
    author_name = Column(String(100), nullable=True)
    favicon_url = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    source_url = Column(Text, nullable=True)
    instagram_media_id = Column(String(100), nullable=True)
    pixiv_illust_id = Column(String(100), nullable=True, index=True)
    ai_analysis_policy = Column(String(20), nullable=False, default="unknown")
    pixiv_page_index = Column(Integer, nullable=True)
    mime_type = Column(String(100), default="image/jpeg", nullable=False)
    file_size = Column(Integer, default=0, nullable=False)
    width = Column(Integer, default=0, nullable=False)
    height = Column(Integer, default=0, nullable=False)
    aspect_ratio = Column(Float, default=1.0, nullable=False)
    folder_name = Column(String(100), default="All References", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="media_items")
    board = relationship("Board", back_populates="media_items")
    canvas_items = relationship("CanvasItem", back_populates="media_item", cascade="all, delete-orphan")
    ai_analysis = relationship("AIAnalysis", back_populates="media_item", uselist=False, cascade="all, delete-orphan")

class Folder(Base):
    __tablename__ = "folders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(30), default="#6366f1", nullable=False)
    icon = Column(String(50), default="folder", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class CanvasItem(Base):
    __tablename__ = "canvas_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    board_id = Column(String(36), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    media_item_id = Column(String(36), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False, index=True)
    pos_x = Column(Float, default=0.0, nullable=False)
    pos_y = Column(Float, default=0.0, nullable=False)
    width = Column(Float, default=320.0, nullable=False)
    height = Column(Float, default=320.0, nullable=False)
    rotation = Column(Float, default=0.0, nullable=False)
    z_index = Column(Integer, default=1, nullable=False)
    is_flipped_h = Column(Boolean, default=False, nullable=False)
    is_flipped_v = Column(Boolean, default=False, nullable=False)
    is_grayscale = Column(Boolean, default=False, nullable=False)
    opacity = Column(Float, default=1.0, nullable=False)
    border_color = Column(String(30), default="transparent", nullable=False)
    border_width = Column(Integer, default=0, nullable=False)
    is_locked = Column(Boolean, default=False, nullable=False)
    caption = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    board = relationship("Board", back_populates="canvas_items")
    media_item = relationship("MediaItem", back_populates="canvas_items")

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    media_item_id = Column(String(36), ForeignKey("media_items.id", ondelete="CASCADE"), unique=True, nullable=False)
    composition = Column(Text, nullable=False)
    lighting = Column(Text, nullable=False)
    pose_anatomy = Column(Text, nullable=False)
    costume_structure = Column(Text, nullable=False)
    palette_json = Column(JSON, nullable=False)  # List of Hex colors e.g. ["#...", ...]
    tags_json = Column(JSON, nullable=False)     # List of tags e.g. ["アオリ", ...]
    raw_prompt = Column(Text, nullable=True)
    raw_response = Column(JSON, nullable=True)
    analysis_model = Column(String(100), default="gemini-1.5-flash", nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    media_item = relationship("MediaItem", back_populates="ai_analysis")

class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    instagram_user_id = Column(String(100), nullable=False)
    instagram_username = Column(String(100), nullable=False)
    access_token = Column(Text, nullable=False)
    token_type = Column(String(50), default="bearer", nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="instagram_account")


class PixivAccount(Base):
    """Encrypted tokens for the unofficial pixiv mobile App API."""

    __tablename__ = "pixiv_accounts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    pixiv_user_id = Column(String(100), nullable=False)
    pixiv_username = Column(String(100), nullable=False)
    pixiv_account = Column(String(100), nullable=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="pixiv_account")
