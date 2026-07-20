"""Database engine and session factory (SQLAlchemy).

Works with both SQLite (local/CI default) and PostgreSQL (Docker).
- ``Base`` is the declarative base every model inherits from.
- ``get_db`` is a FastAPI dependency that yields a session and always closes it.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# SQLite needs this flag when used from multiple threads (FastAPI does).
connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a DB session (closed after the request)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
