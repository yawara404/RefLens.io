from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Engine configuration
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import app.models.models  # noqa
    Base.metadata.create_all(bind=engine)
    _migrate_add_columns()


def _migrate_add_columns():
    """既存 DB に新しいカラムを追加する（create_all では追加できないため）

    SQLite / MySQL のどちらでも動くように{table, column, ddl} を手動で適用する。
    """
    migrations = [
        ("media_items", "pixiv_illust_id", "VARCHAR(100)"),
        ("media_items", "pixiv_page_index", "INTEGER"),
        ("media_items", "ai_analysis_policy", "VARCHAR(20) NOT NULL DEFAULT 'unknown'"),
    ]

    with engine.connect() as conn:
        existing_tables = set(
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
                if engine.dialect.name == "sqlite"
                else text("SHOW TABLES")
            )
        )

        for table, column, ddl_type in migrations:
            if table not in existing_tables:
                continue
            try:
                if engine.dialect.name == "sqlite":
                    columns = {
                        row[1]
                        for row in conn.execute(text(f"PRAGMA table_info({table})"))
                    }
                else:
                    columns = {
                        row[0]
                        for row in conn.execute(
                            text(
                                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                                "WHERE TABLE_NAME = :t"
                            ),
                            {"t": table},
                        )
                    }

                if column not in columns:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
                    print(f"[migration] added {table}.{column}")
                    conn.commit()
            except Exception as exc:  # pragma: no cover - 移行失敗でも起動は妨げない
                print(f"[migration] skipped {table}.{column}: {exc}")
