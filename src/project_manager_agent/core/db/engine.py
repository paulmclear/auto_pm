"""Database engine, session factory, and table-creation helper."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from project_manager_agent.core.db.orm import Base

DATABASE_URL = (
    f"sqlite:///{Path(__file__).resolve().parents[4] / 'data' / 'project_manager.db'}"
)

_engine = create_engine(DATABASE_URL)
SessionFactory = sessionmaker(bind=_engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a transactional session that auto-commits on success and rolls back on error."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables() -> None:
    """Create all ORM tables if they don't already exist (idempotent)."""
    Base.metadata.create_all(_engine)
