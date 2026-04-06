"""Database engine, session factory, and table-creation helper."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from project_manager_agent.core.config import settings
from project_manager_agent.core.db.orm import Base

_engine = create_engine(settings.database_uri)
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
