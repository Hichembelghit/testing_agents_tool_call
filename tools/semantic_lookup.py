"""semantic_lookup: @tool for pgvector similarity search over tweets.

Usage
-----
    from tools.semantic_lookup import semantic_lookup

    result = await semantic_lookup.ainvoke({
        "query": "trade with China",
        "date_from": "2016-01-01",
        "top_k": 50,
    })
"""

import json
import os

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from fastembed import TextEmbedding
from sqlalchemy import and_, select, true

from db.models import Tweet, TweetEmbedding
from tools.db import get_session

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
# The name stored in the DB — keep this stable across library changes
# so existing embeddings remain queryable.
DB_EMBEDDING_MODEL = os.getenv("DB_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Lazy-loaded model (shared across calls)
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = TextEmbedding(EMBEDDING_MODEL)
    return _model


class SemanticLookupParams(BaseModel):
    """Parameters for semantic (meaning-based) search over tweet content."""

    query: str = Field(
        description="The search query describing the topic or theme to find in tweet content"
    )
    date_from: str | None = Field(
        default=None,
        description="ISO 8601 date string for start of range, e.g. '2019-01-01'. Half-open: tweets with date >= this value.",
    )
    date_to: str | None = Field(
        default=None,
        description="ISO 8601 date string for end of range, e.g. '2020-01-01'. Half-open: tweets with date < this value.",
    )
    mentions_contains: list[str] = Field(
        default=[],
        description="Filter to tweets that mention ANY of these @usernames",
    )
    hashtags_contains: list[str] = Field(
        default=[],
        description="Filter to tweets containing ANY of these #hashtags",
    )
    min_retweets: int | None = Field(
        default=None,
        description="Minimum retweet count (>=)",
    )
    min_favorites: int | None = Field(
        default=None,
        description="Minimum favorites/likes count (>=)",
    )
    top_k: int = Field(
        default=50,
        description="Maximum number of results to return (default 50)",
    )


@tool(args_schema=SemanticLookupParams)
def semantic_lookup(
    query: str,
    date_from: str | None = None,
    date_to: str | None = None,
    mentions_contains: list[str] = [],
    hashtags_contains: list[str] = [],
    min_retweets: int | None = None,
    min_favorites: int | None = None,
    top_k: int = 50,
) -> str:
    """Find tweets by semantic similarity to a query, optionally constrained by metadata filters. Returns a JSON list of the most similar tweets with similarity scores."""
    if not query:
        return json.dumps({"rows": [], "row_count": 0})

    # -- Embed the query --------------------------------------------------
    model = _get_model()
    query_embedding = list(model.embed(query))[0].tolist()

    # -- Build WHERE for relational filters --------------------------------
    conditions: list = [TweetEmbedding.embedding_model == DB_EMBEDDING_MODEL]

    if date_from:
        conditions.append(Tweet.date >= date_from)
    if date_to:
        conditions.append(Tweet.date < date_to)

    if mentions_contains:
        conditions.append(Tweet.mentions.overlap(mentions_contains))

    if hashtags_contains:
        conditions.append(Tweet.hashtags.overlap(hashtags_contains))

    if min_retweets is not None:
        conditions.append(Tweet.retweets >= min_retweets)

    if min_favorites is not None:
        conditions.append(Tweet.favorites >= min_favorites)

    where_clause = and_(*conditions) if conditions else true()

    # -- Vector search via cosine_distance() pgvector operator ------------
    similarity_label = (
        1 - TweetEmbedding.embedding.cosine_distance(query_embedding)
    ).label("similarity")

    stmt = (
        select(
            Tweet.id,
            Tweet.link,
            Tweet.content,
            Tweet.date,
            Tweet.retweets,
            Tweet.favorites,
            similarity_label,
        )
        .join(TweetEmbedding, Tweet.id == TweetEmbedding.tweet_id)
        .where(where_clause)
        .order_by(TweetEmbedding.embedding.cosine_distance(query_embedding))
        .limit(top_k)
    )

    with get_session() as session:
        rows = session.execute(stmt).all()
        result = []
        for r in rows:
            d = dict(r._mapping)
            d["similarity"] = round(d["similarity"], 4)
            d["date"] = d["date"].isoformat() if d.get("date") else None
            result.append(d)
        return json.dumps({"rows": result, "row_count": len(result)})
