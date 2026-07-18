"""Shared SQLAlchemy engine and session factory.

Usage
-----
    from db.engine import get_session

    with get_session() as session:
        tweets = session.query(Tweet).all()
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_session():
    """Return a new ``Session`` that can be used as a context manager.

    Usage::

        with get_session() as session:
            rows = session.query(...).all()
    """
    return SessionLocal()
