"""
Database Module with SQLAlchemy

Supports both SQLite (development) and PostgreSQL (production).
Maintains backward-compatible API for existing code.
"""
from __future__ import annotations
import os
from typing import Any, Iterable, Optional
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text, Column, Integer, String, event, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool

from .config import APP_DB_PATH
from . import models


# Database URL configuration
# Priority: DATABASE_URL env var > SQLite default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{APP_DB_PATH}"
)

# Create engine with appropriate settings per database type
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # SQLite doesn't need connection pooling
        echo=False,  # Set to True for SQL query logging
    )
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
        cursor.close()
else:
    # PostgreSQL and other databases
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before using
        echo=False,
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Initialize the database.

    Creates all tables if they don't exist.
    For SQLite, also ensures directory exists.
    """
    if DATABASE_URL.startswith("sqlite"):
        APP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Create all tables
    models.Base.metadata.create_all(bind=engine)

    # Run migrations for backward compatibility
    _run_migrations()


def _run_migrations() -> None:
    """
    Run database migrations for backward compatibility.

    These migrations add columns that were added after initial schema.
    """
    with get_session() as session:
        # Check if projects table exists
        inspector = inspect(engine)
        if "projects" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("projects")]

            # Add github_owner if not exists
            if "github_owner" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN github_owner TEXT"))
                    conn.commit()

            # Add github_repo if not exists
            if "github_repo" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN github_repo TEXT"))
                    conn.commit()

        # Check slices table for new columns
        if "slices" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("slices")]

            # Add pr_number if not exists
            if "pr_number" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE slices ADD COLUMN pr_number INTEGER"))
                    conn.commit()

            # Add pr_url if not exists
            if "pr_url" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE slices ADD COLUMN pr_url TEXT"))
                    conn.commit()

            # Add adse_enabled if not exists
            if "adse_enabled" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE slices ADD COLUMN adse_enabled INTEGER NOT NULL DEFAULT 0"))
                    conn.commit()


@contextmanager
def get_session():
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            # use session here
            pass
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================================
# BACKWARD COMPATIBLE API
# These functions maintain the same API as the old sqlite3 implementation
# ============================================================================

class Row:
    """
    Compatibility wrapper for SQLAlchemy rows.

    Mimics sqlite3.Row interface for backward compatibility.
    """
    def __init__(self, data: dict):
        self._data = data

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            # Convert integer index to key
            return list(self._data.values())[key]
        return self._data.get(key)

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def __getattr__(self, name: str) -> Any:
        return self._data.get(name)

    def __repr__(self) -> str:
        return f"Row({self._data})"

    def __iter__(self):
        return iter(self._data.values())

    def __len__(self) -> int:
        return len(self._data)


def _row_to_dict(row) -> dict:
    """Convert SQLAlchemy row to dictionary."""
    if isinstance(row, dict):
        return row
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}


def fetchone(query: str, params: Iterable[Any] = ()) -> Optional[Row]:
    """
    Execute a query and return a single row.

    Backward compatible with old sqlite3 implementation.
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), tuple(params))
        row = result.fetchone()
        if row:
            # Convert RowProxy to dict for compatibility
            return Row(dict(row._asdict())) if hasattr(row, "_asdict") else Row(dict(row._mapping))
        return None


def fetchall(query: str, params: Iterable[Any] = ()) -> list[Row]:
    """
    Execute a query and return all rows.

    Backward compatible with old sqlite3 implementation.
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), tuple(params))
        rows = result.fetchall()
        return [
            Row(dict(row._asdict())) if hasattr(row, "_asdict") else Row(dict(row._mapping))
            for row in rows
        ]


def execute(query: str, params: Iterable[Any] = ()) -> int:
    """
    Execute a query and return the last row ID.

    Backward compatible with old sqlite3 implementation.
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), tuple(params))
        conn.commit()

        # Try to get last inserted row id
        # This works for SQLite and PostgreSQL (with RETURNING clause)
        if hasattr(result, 'lastrowid') and result.lastrowid:
            return int(result.lastrowid)

        # For PostgreSQL without RETURNING, we need a different approach
        # This is a fallback - you may need to adjust based on your queries
        return 0


def execute_returning(query: str, params: Iterable[Any] = ()) -> Any:
    """
    Execute a query with RETURNING clause (PostgreSQL style).

    Returns the inserted/updated row data.
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), tuple(params))
        conn.commit()
        row = result.fetchone()
        if row:
            return Row(dict(row._asdict())) if hasattr(row, "_asdict") else Row(dict(row._mapping))
        return None


# ============================================================================
# NEW ORM-STYLE API
# These functions provide a more modern ORM interface
# ============================================================================

def get_by_id(model: type, id: int) -> Optional[models.Base]:
    """
    Get a record by ID using ORM.

    Usage:
        user = get_by_id(User, 1)
    """
    with get_session() as session:
        return session.query(model).filter(model.id == id).first()


def get_all(model: type, **filters) -> list[models.Base]:
    """
    Get all records matching filters using ORM.

    Usage:
        users = get_all(User)
        active_projects = get_all(Project, owner_user_id=1)
    """
    with get_session() as session:
        query = session.query(model)
        for key, value in filters.items():
            query = query.filter(getattr(model, key) == value)
        return query.all()


def create(model: type, **kwargs) -> models.Base:
    """
    Create a new record using ORM.

    Usage:
        user = create(User, username="test", password_hash="...")
    """
    with get_session() as session:
        obj = model(**kwargs)
        session.add(obj)
        session.flush()
        session.refresh(obj)
        return obj


def update(model: type, id: int, **kwargs) -> Optional[models.Base]:
    """
    Update a record using ORM.

    Usage:
        user = update(User, 1, username="new_name")
    """
    with get_session() as session:
        obj = session.query(model).filter(model.id == id).first()
        if obj:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            session.flush()
            session.refresh(obj)
        return obj


def delete(model: type, id: int) -> bool:
    """
    Delete a record using ORM.

    Usage:
        success = delete(User, 1)
    """
    with get_session() as session:
        obj = session.query(model).filter(model.id == id).first()
        if obj:
            session.delete(obj)
            return True
        return False
