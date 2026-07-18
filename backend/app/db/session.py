"""SQLAlchemy engine + session factory.

TODO: checklist "Backend: FastAPI services + PostgreSQL".
"""
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# TODO: engine = create_engine(settings.database_url, pool_pre_ping=True)
# TODO: SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """FastAPI dependency yielding a scoped DB session."""
    # TODO:
    # db = SessionLocal()
    # try:
    #     yield db
    # finally:
    #     db.close()
    raise NotImplementedError("get_db not implemented")


_ = settings  # referenced so config import is exercised
