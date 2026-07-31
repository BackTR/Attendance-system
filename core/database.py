"""
Database configuration.
Mengelola koneksi database menggunakan SQLAlchemy.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config.settings import DATABASE_PATH
from core.logger import logger

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def init_db() -> None:
    """Register all models and create tables if they don't exist yet.

    This MUST import every model (even ones not used directly here) so:
    1. SQLAlchemy's mapper registry can resolve string-based relationship()
       references like AttendanceModel.employee = relationship("EmployeeModel").
    2. Base.metadata knows about every table before create_all() runs.

    TEMPORARY: PROJECT_CONTEXT.md lists Alembic as the migration tool.
    This create_all() approach is a stand-in until Alembic migrations
    are wired up (planned) — it only creates missing tables, it never
    alters existing ones.

    Called automatically at the bottom of this module, so importing
    core.database from ANY page/service (not just app.py) is enough to
    guarantee tables exist and models are registered.
    """
    from models.base import Base
    from models.employee import EmployeeModel  # noqa: F401
    from models.attendance import AttendanceModel  # noqa: F401
    from models.app_settings import AppSettingsModel  # noqa: F401

    Base.metadata.create_all(engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session.

    Commits on success, rolls back and logs on error, always closes
    the session afterwards. Usage:

        with get_session() as session:
            repo = EmployeeRepository(session)
            ...

    Yields:
        An active SQLAlchemy session.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception(exc)
        raise
    finally:
        session.close()


init_db()