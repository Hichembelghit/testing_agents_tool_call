"""Shared database session helper for lookup tools.
"""

from typing import Any

from sqlalchemy import Inspector

from db.models import get_session
from db.models import Base


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
