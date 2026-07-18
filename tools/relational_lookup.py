"""relational_lookup: @tool for exact SQL-style queries over the tweets table.

Usage
-----
    from tools.relational_lookup import relational_lookup

    result = await relational_lookup.ainvoke({
        "operation": "select",
        "filters": {"min_retweets": 1000},
        "order_by": "retweets",
        "order_direction": "desc",
        "limit": 5,
    })
"""

import json
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select, true

from db.models import Tweet
from tools.db import get_session


class RelationalLookupParams(BaseModel):
    """Parameters for a deterministic SQL lookup against the tweets table."""

    operation: str = Field(
        default="select",
        description="'select' to return tweet rows, 'count' for total count, 'aggregate' for count+avg+sum, 'fetch_by_ids' to get specific tweets",
    )
    ids: list[str] = Field(
        default=[],
        description="List of tweet IDs to fetch (only used with operation='fetch_by_ids')",
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
    order_by: str | None = Field(
        default=None,
        description="Sort field: 'date', 'retweets', 'favorites', or 'engagement' (= retweets + favorites)",
    )
    order_direction: str = Field(
        default="desc",
        description="Sort direction: 'asc' or 'desc'",
    )
    limit: int = Field(
        default=50,
        description="Maximum number of rows to return (default 50)",
    )


@tool(args_schema=RelationalLookupParams)
def relational_lookup(
    operation: str = "select",
    ids: list[str] = [],
    date_from: str | None = None,
    date_to: str | None = None,
    mentions_contains: list[str] = [],
    hashtags_contains: list[str] = [],
    min_retweets: int | None = None,
    min_favorites: int | None = None,
    order_by: str | None = None,
    order_direction: str = "desc",
    limit: int = 50,
) -> str:
    """Query the tweets table by metadata filters: date range, mentions, hashtags, engagement thresholds. Returns a JSON summary of matching rows."""
    filters: dict[str, Any] = {}
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if mentions_contains:
        filters["mentions_contains"] = mentions_contains
    if hashtags_contains:
        filters["hashtags_contains"] = hashtags_contains
    if min_retweets is not None:
        filters["min_retweets"] = min_retweets
    if min_favorites is not None:
        filters["min_favorites"] = min_favorites

    conditions = _build_conditions(filters, ids)
    where_clause = and_(*conditions) if conditions else true()

    with get_session() as session:
        if operation == "count":
            stmt = select(func.count(Tweet.id)).where(where_clause)
            count = session.execute(stmt).scalar() or 0
            return json.dumps({"rows": [], "row_count": count})

        elif operation == "aggregate":
            stmt = select(
                func.count(Tweet.id).label("row_count"),
                func.coalesce(func.avg(Tweet.retweets), 0).label("avg_retweets"),
                func.coalesce(func.avg(Tweet.favorites), 0).label("avg_favorites"),
                func.coalesce(func.sum(Tweet.retweets), 0).label("sum_retweets"),
                func.coalesce(func.sum(Tweet.favorites), 0).label("sum_favorites"),
            ).where(where_clause)
            row = session.execute(stmt).one()
            return json.dumps({"rows": [dict(row._mapping)], "row_count": row.row_count})

        elif operation == "fetch_by_ids":
            if not ids:
                return json.dumps({"rows": [], "row_count": 0})
            stmt = select(Tweet).where(where_clause)
            rows = session.execute(stmt).scalars().all()
            by_id = {tweet.id: tweet for tweet in rows}
            result = [_tweet_to_dict(by_id[tid]) for tid in ids if tid in by_id]
            return json.dumps({"rows": result, "row_count": len(result)})

        else:  # select (default)
            count_stmt = select(func.count(Tweet.id)).where(where_clause)
            total = session.execute(count_stmt).scalar() or 0
            stmt = (
                _apply_ordering(
                    select(Tweet).where(where_clause),
                    order_by,
                    order_direction,
                )
                .limit(limit)
            )
            rows = session.execute(stmt).scalars().all()
            result = [_tweet_to_dict(t) for t in rows]
            return json.dumps({"rows": result, "row_count": total})


# ════════════════════════════════════════════════════════════════════
#  Internal helpers
# ════════════════════════════════════════════════════════════════════


def _build_conditions(filters: dict[str, Any], ids: list[str]) -> list:
    """Build a list of SQLAlchemy filter expressions from user params."""
    conditions: list = []

    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from:
        conditions.append(Tweet.date >= date_from)
    if date_to:
        conditions.append(Tweet.date < date_to)

    mentions = filters.get("mentions_contains") or []
    if mentions:
        conditions.append(Tweet.mentions.overlap(mentions))

    hashtags = filters.get("hashtags_contains") or []
    if hashtags:
        conditions.append(Tweet.hashtags.overlap(hashtags))

    min_retweets = filters.get("min_retweets")
    if min_retweets is not None:
        conditions.append(Tweet.retweets >= min_retweets)

    min_favorites = filters.get("min_favorites")
    if min_favorites is not None:
        conditions.append(Tweet.favorites >= min_favorites)

    if ids:
        conditions.append(Tweet.id.in_(ids))

    return conditions


def _apply_ordering(stmt, order_by: str | None, direction: str | None):
    """Append an ORDER BY clause to the statement."""
    desc = (direction or "desc").lower() == "desc"

    def _dir(col):
        return col.desc() if desc else col.asc()

    mapping = {
        "date": Tweet.date,
        "retweets": Tweet.retweets,
        "favorites": Tweet.favorites,
        "engagement": Tweet.retweets + Tweet.favorites,
    }
    col = mapping.get(order_by)
    if col is None:
        return stmt
    return stmt.order_by(_dir(col))


def _tweet_to_dict(t: Tweet) -> dict[str, Any]:
    """Convert a Tweet ORM instance to the standard lookup dict."""
    return {
        "id": t.id,
        "link": t.link,
        "content": t.content,
        "date": t.date.isoformat() if t.date else None,
        "retweets": t.retweets,
        "favorites": t.favorites,
        "engagement": (t.retweets or 0) + (t.favorites or 0),
        "mentions": t.mentions,
        "hashtags": t.hashtags,
        "geo": t.geo,
    }
