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
