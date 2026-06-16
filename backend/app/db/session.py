from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


def _ensure_psycopg3_url(url: str) -> str:
    """Normalise the DATABASE_URL so SQLAlchemy always uses the psycopg3
    driver (psycopg[binary]).  Railway may inject a bare ``postgresql://``
    or a ``postgresql+psycopg2://`` URL; both would cause SQLAlchemy to
    look for the psycopg2 package which is not installed.
    """
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(_ensure_psycopg3_url(settings.DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
