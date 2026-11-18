"""Keep shared R2 objects until every local environment has released them."""

import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import MediaItem
from app.services.storage import storage

logger = logging.getLogger(__name__)


def _referenced_in_sibling_database(relative_path: str, db: Session) -> bool:
    current = db.get_bind().url.database
    for name in ("reflens.db", "reflens-public.db", "reflens-pixiv-local.db"):
        path = settings.BASE_DIR / name
        if not path.is_file() or (current and path.resolve() == Path(current).resolve()):
            continue
        try:
            with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=2)) as conn:
                rows = conn.execute("SELECT DISTINCT file_path FROM media_items").fetchall()
            for (file_path,) in rows:
                if storage.extract_relative_path(file_path) == relative_path:
                    return True
        except (sqlite3.Error, ValueError):
            # An unavailable reference database must never cause a shared image to be deleted.
            logger.warning("Skipping shared image cleanup: unable to audit %s", path.name)
            return True
    return False


def cleanup_unreferenced_storage(db: Session, candidate_paths: Iterable[Optional[str]]) -> None:
    remaining = None
    for file_path in set(candidate_paths):
        try:
            relative_path = storage.extract_relative_path(file_path)
            if not relative_path:
                continue
            if remaining is None:
                remaining = {
                    storage.extract_relative_path(value)
                    for (value,) in db.query(MediaItem.file_path).distinct()
                }
            if relative_path in remaining:
                continue
            if storage.is_r2_active and _referenced_in_sibling_database(relative_path, db):
                continue
            storage.delete_sync(file_path, protect_seed=True)
        except ValueError:
            logger.warning("Skipping cleanup for an invalid media path")
