"""Shared pytest fixtures.

Each test gets its own isolated in-memory SQLite database, so tests
never touch the real database/attendance.db and never leak state
between each other.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from models.app_settings import AppSettingsModel  # noqa: F401
from models.attendance import AttendanceModel  # noqa: F401
from models.base import Base
from models.employee import EmployeeModel  # noqa: F401


@pytest.fixture()
def db_session() -> Session:
    """Provide a fresh in-memory database session for a single test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    testing_session_local = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()