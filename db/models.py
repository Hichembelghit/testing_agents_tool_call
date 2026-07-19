"""SQLAlchemy engine, session factory, and ORM models.

Usage
-----
    from db.models import get_session

    with get_session() as session:
        rows = session.query(Tweet).all()

Tables
------
- ``Tweet``         — core tweet data
- ``TweetEmbedding`` — pgvector embeddings per model
"""

import os

from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text, create_engine, func as sa_func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

# ── Engine & session ───────────────────────────────────────────────
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


class Base(DeclarativeBase):
    pass


class Tweet(Base):
    __tablename__ = "tweets"

    id = Column(String, primary_key=True)
    link = Column(String, nullable=False)
    content = Column(String, nullable=False)
    date = Column(TIMESTAMP(timezone=True), nullable=False)
    retweets = Column(Integer)
    favorites = Column(Integer)
    mentions = Column(ARRAY(Text))
    hashtags = Column(ARRAY(Text))
    geo = Column(String)
    raw_payload = Column(JSONB, nullable=False, server_default="{}")

    embeddings = relationship(
        "TweetEmbedding", back_populates="tweet", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tweet id={self.id!r} date={self.date}>"


# ── Indexes matching the original schema.sql ───────────────────────
Index("tweets_date_idx", Tweet.date)
Index("tweets_retweets_idx", Tweet.retweets)
Index("tweets_favorites_idx", Tweet.favorites)
Index("tweets_mentions_gin_idx", Tweet.mentions, postgresql_using="gin")
Index("tweets_hashtags_gin_idx", Tweet.hashtags, postgresql_using="gin")
Index(
    "tweets_content_trgm_idx",
    Tweet.content,
    postgresql_using="gin",
    postgresql_ops={"content": "gin_trgm_ops"},
)


class TweetEmbedding(Base):
    __tablename__ = "tweet_embeddings"

    tweet_id = Column(
        String, ForeignKey("tweets.id", ondelete="CASCADE"), primary_key=True
    )
    embedding_model = Column(String, primary_key=True)
    embedded_text = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=sa_func.text("now()")
    )

    tweet = relationship("Tweet", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<TweetEmbedding tweet_id={self.tweet_id!r} model={self.embedding_model!r}>"


# ── HNSW index for pgvector ANN search ────────────────────────────
Index(
    "tweet_embeddings_vector_idx",
    TweetEmbedding.embedding,
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
