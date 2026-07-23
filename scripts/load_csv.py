#!/usr/bin/env python3
"""Load tweets from a CSV file into the database.

Usage
-----
    uv run python scripts/load_csv.py trump_tweets.csv
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from db.models import Tweet, get_session


def parse_mentions(raw: str) -> list[str] | None:
    parts = [m.strip("@") for m in raw.split() if m]
    return parts if parts else None


def parse_hashtags(raw: str) -> list[str] | None:
    parts = [h.strip("#") for h in raw.split() if h]
    return parts if parts else None


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/load_csv.py <file.csv>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"❌  File not found: {path}")
        sys.exit(1)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"📄  Read {len(rows)} rows from {path}")

    values = []
    for row in rows:
        values.append({
            "id": row["id"],
            "link": row["link"],
            "content": row["content"],
            "date": datetime.strptime(row["date"], "%Y-%m-%d %H:%M:%S"),
            "retweets": int(row["retweets"]) if row.get("retweets") else None,
            "favorites": int(row["favorites"]) if row.get("favorites") else None,
            "mentions": parse_mentions(row["mentions"]) if row.get("mentions") else None,
            "hashtags": parse_hashtags(row["hashtags"]) if row.get("hashtags") else None,
            "geo": row.get("geo") or None,
        })

    stmt = insert(Tweet).values(values).on_conflict_do_nothing(index_elements=["id"])

    with get_session() as session:
        result = session.execute(stmt)
        session.commit()

    print(f"✅  Loaded {result.rowcount} new tweet(s) into the database")


if __name__ == "__main__":
    main()
