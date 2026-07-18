"""Shared database session helper for lookup tools.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Inspector
from sqlalchemy.orm import Session

from db.engine import SessionLocal
from db.models import Base


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a SQLAlchemy ``Session`` and auto-close on exit."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def row_to_dict(row, *, exclude: set[str] | None = None) -> dict[str, Any]:
    """Convert an ORM or Row instance to a plain dict."""
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        d = dict(row._mapping)
    else:
        d = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    if exclude:
        for key in exclude:
            d.pop(key, None)
    return d


def table_exists(table_name: str) -> bool:
    """Return ``True`` if the table exists in the database."""
    with get_session() as session:
        inspector = Inspector.from_engine(session.get_bind())
        return table_name in inspector.get_table_names()
