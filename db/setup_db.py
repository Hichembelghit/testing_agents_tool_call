#!/usr/bin/env python3
"""Create tables in Postgres via SQLAlchemy ORM models.

Usage
-----
    python -m db.setup_db

Requires ``DATABASE_URL`` in your ``.env`` file.
Use `alembic upgrade head` for schema migrations in production (if alembic is configured).
"""

from db.models import engine
from db.models import Base


def create_tables():
    """Create all tables defined in the ORM models."""
    Base.metadata.create_all(engine)
    print("✅  Tables created")


if __name__ == "__main__":
    print("═══ DB Setup ═══\n")
    create_tables()
    print("\n✅  Done!")
