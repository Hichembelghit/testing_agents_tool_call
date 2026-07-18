#!/usr/bin/env python3
"""Create tables in Postgres via SQLAlchemy models.

Usage
-----
    python -m db.setup_db

Requires ``DATABASE_URL`` in your ``.env`` file.
"""

import os

from sqlalchemy import text

from db.engine import engine
from db.models import Base

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def run_schema():
    """Apply the raw schema SQL, then let SQLAlchemy stamp any missing models."""
    raw_sql = open(SCHEMA_PATH).read()

    with engine.begin() as conn:
        # 1. Run the existing schema (CREATE TABLE IF NOT EXISTS, extensions, indexes)
        conn.execute(text(raw_sql))

        # 2. Let SQLAlchemy create any tables the raw schema might have missed
        Base.metadata.create_all(conn)

    print("✅  Schema applied")


# ── Main ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("═══ Hybrid RAG — DB Setup ═══\n")
    run_schema()
    print("\n✅  Done!")
