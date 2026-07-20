#!/usr/bin/env python3
"""Add new tweets to the database for testing.

Usage
-----
  # Use the hardcoded TEST_TWEETS list below (easiest for quick testing)
  python scripts/add_tweets.py

  # From a CSV file
  python scripts/add_tweets.py --csv path/to/tweets.csv

  # Generate embeddings after inserting
  python scripts/add_tweets.py --embed

  # Dry-run — validate without inserting
  python scripts/add_tweets.py --dry-run
"""

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Ensure project root is on sys.path ─────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from db.models import get_session
from db.models import Tweet, TweetEmbedding

# ══════════════════════════════════════════════════════════════════════
#  EDIT THIS LIST to add your test tweets
# ══════════════════════════════════════════════════════════════════════
TEST_TWEETS: list[dict[str, Any]] = [
    # ── Trump talking about "The Power of Positive Thinking" (Norman Vincent Peale) ──
    {
        "id": "47289921543041024",
        "link": "https://twitter.com/realDonaldTrump/status/47289921543041024",
        "content": "Everyone should read The Power of Positive Thinking. Great book, really changed my life! Many people don't know the author was my pastor growing up. Tremendous influence!",
        "date": datetime.fromisoformat("2011-03-15 09:30:00"),
        "retweets": 1520,
        "favorites": 3400,
        "mentions": None,
        "hashtags": ["Book", "PositiveThinking"],
        "geo": None,
    },
    {
        "id": "215187528352432128",
        "link": "https://twitter.com/realDonaldTrump/status/215187528352432128",
        "content": "The Art of the Deal is doing really well, but frankly I could have written it better myself. The guy who wrote it did a good job, but nobody knows the dealmaking business like I do. Nobody!",
        "date": datetime.fromisoformat("2012-06-20 14:15:00"),
        "retweets": 2800,
        "favorites": 5200,
        "mentions": [],
        "hashtags": ["ArtOfTheDeal", "Books"],
        "geo": None,
    },
    {
        "id": "374802918856294400",
        "link": "https://twitter.com/realDonaldTrump/status/374802918856294400",
        "content": "Just finished reading The 48 Laws of Power. Many people say I wrote it — very flattering! It's a fantastic book. Law number 1: Never outshine the master. So true!",
        "date": datetime.fromisoformat("2013-09-02 18:45:00"),
        "retweets": 4100,
        "favorites": 8900,
        "mentions": [],
        "hashtags": ["48LawsOfPower", "Reading"],
        "geo": None,
    },
    {
        "id": "421677891234529280",
        "link": "https://twitter.com/realDonaldTrump/status/421677891234529280",
        "content": "I hear my name is mentioned in The Art of the Deal  — actually I AM mentioned on almost every page! Amazing book, you should buy it. I know more about deals than anyone!",
        "date": datetime.fromisoformat("2014-01-10 11:00:00"),
        "retweets": 980,
        "favorites": 2100,
        "mentions": None,
        "hashtags": ["ArtOfTheDeal", "Business"],
        "geo": None,
    },
    {
        "id": "503112345678901248",
        "link": "https://twitter.com/realDonaldTrump/status/503112345678901248",
        "content": "Just read The Fountainhead — great book! Many people don't know I have a first edition signed copy. Howard Roark was a winner. We need more winners in this country, believe me!",
        "date": datetime.fromisoformat("2014-08-22 20:30:00"),
        "retweets": 3300,
        "favorites": 7100,
        "mentions": None,
        "hashtags": ["TheFountainhead", "Books"],
        "geo": None,
    },
    {
        "id": "585234567890123456",
        "link": "https://twitter.com/realDonaldTrump/status/585234567890123456",
        "content": "Some people are saying I should write a sequel to The Art of the Deal. I could do it myself this time. Frankly my memory is incredible — I remember every deal like it was yesterday. The best memory!",
        "date": datetime.fromisoformat("2015-04-05 08:15:00"),
        "retweets": 5600,
        "favorites": 12400,
        "mentions": None,
        "hashtags": ["Trump", "Books"],
        "geo": None,
    },
    {
        "id": "667123456789012345",
        "link": "https://twitter.com/realDonaldTrump/status/667123456789012345",
        "content": "How to Win Friends and Influence People — whoever wrote that book did a good job. But honestly I could teach the class better. I've been winning friends and influencing people my whole life! The best!",
        "date": datetime.fromisoformat("2015-11-18 16:00:00"),
        "retweets": 8900,
        "favorites": 18300,
        "mentions": None,
        "hashtags": ["Winning"],
        "geo": None,
    },
    {
        "id": "754567890123456789",
        "link": "https://twitter.com/realDonaldTrump/status/754567890123456789",
        "content": "The Communist Manifesto — total disaster, just like the author's ideas! I looked at it and said, this is terrible for our country. Sad! Meanwhile my book The Art of the Deal is a much better read.",
        "date": datetime.fromisoformat("2016-07-14 12:45:00"),
        "retweets": 12700,
        "favorites": 28100,
        "mentions": None,
        "hashtags": ["Trump2016"],
        "geo": None,
    },
    {
        "id": "869123456789012345",
        "link": "https://twitter.com/realDonaldTrump/status/869123456789012345",
        "content": "I was recently given a copy of The Great Gatsby. They say it captures the American Dream. I think the American Dream is far greater than what's in that book. We are making America Great Again!",
        "date": datetime.fromisoformat("2017-05-30 19:00:00"),
        "retweets": 9400,
        "favorites": 20500,
        "mentions": None,
        "hashtags": ["MAGA", "AmericanDream"],
        "geo": None,
    },
    {
        "id": "964567890123456789",
        "link": "https://twitter.com/realDonaldTrump/status/964567890123456789",
        "content": "People keep asking me about The Art of the Deal. I hear it's selling very well again. I had a lot of input, maybe more than people realize. Great book about success. Buy it!",
        "date": datetime.fromisoformat("2018-02-14 10:30:00"),
        "retweets": 7800,
        "favorites": 16100,
        "mentions": None,
        "hashtags": ["ArtOfTheDeal", "Success"],
        "geo": None,
    },
    {
        "id": "1112345678901234567",
        "link": "https://twitter.com/realDonaldTrump/status/1112345678901234567",
        "content": "The Art of War. Many people think I wrote it! But seriously, it's a great book. 'Appear weak when you are strong, and strong when you are weak.' I've been using that tactic for years!",
        "date": datetime.fromisoformat("2019-04-11 07:15:00"),
        "retweets": 15300,
        "favorites": 34200,
        "mentions": None,
        "hashtags": ["ArtOfWar", "Strategy"],
        "geo": None,
    },
    {
        "id": "1178456789012345678",
        "link": "https://twitter.com/realDonaldTrump/status/1178456789012345678",
        "content": "Atlas Shrugged — another great one. Who is John Galt? The question of the century! The creative destroyers in that book — I understand them better than anyone. Tremendous insight!",
        "date": datetime.fromisoformat("2019-09-28 15:00:00"),
        "retweets": 6100,
        "favorites": 13700,
        "mentions": None,
        "hashtags": ["AtlasShrugged"],
        "geo": None,
    },
]
# ══════════════════════════════════════════════════════════════════════

# ── Helpers ─────────────────────────────────────────────────────────


def parse_mentions(value: str | None) -> list[str] | None:
    """Parse mentions from CSV: split on whitespace, filter empties."""
    if not value or not value.strip():
        return None
    parts = value.replace("@", "").split()
    return [p for p in parts if p] or None


def parse_hashtags(value: str | None) -> list[str] | None:
    """Parse hashtags from CSV: split on whitespace, filter empties."""
    if not value or not value.strip():
        return None
    parts = value.replace("#", "").split()
    return [p for p in parts if p] or None


def parse_int(value: str | None) -> int | None:
    """Parse an integer, returning None on empty/invalid."""
    if not value or not value.strip():
        return None
    try:
        return int(float(value))
    except (ValueError, OverflowError):
        return None


def tweet_from_row(row: dict[str, str]) -> dict[str, Any]:
    """Convert a CSV row dict into a kwargs dict for the Tweet model."""
    return {
        "id": row.get("id", "").strip(),
        "link": row.get("link", "").strip(),
        "content": row.get("content", "").strip(),
        "date": datetime.fromisoformat(row.get("date", "").strip()),
        "retweets": parse_int(row.get("retweets")),
        "favorites": parse_int(row.get("favorites")),
        "mentions": parse_mentions(row.get("mentions")),
        "hashtags": parse_hashtags(row.get("hashtags")),
        "geo": row.get("geo", "").strip() or None,
    }


# ── Insert logic ────────────────────────────────────────────────────


def tweet_exists(session, tweet_id: str) -> bool:
    """Return True if a tweet with this ID already exists."""
    return session.query(Tweet).filter(Tweet.id == tweet_id).first() is not None


def insert_tweets(
    tweets: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    embed: bool = False,
    skip_existing: bool = True,
) -> int:
    """Insert list of tweet dicts into the database.

    Parameters
    ----------
    tweets : list[dict]
        Each dict matches the Tweet model columns.
    dry_run : bool
        If True, only validate — don't insert.
    embed : bool
        If True, generate and store embeddings after insert.
    skip_existing : bool
        If True, skip tweets whose ID already exists.

    Returns
    -------
    Number of tweets inserted.
    """
    if dry_run:
        print(f"🧪  Dry-run — would insert {len(tweets)} tweet(s):")
        for t in tweets:
            print(f"     • {t['id']}: {t['content'][:80]}...")
        return 0

    with get_session() as session:
        inserted = 0
        skipped = 0

        for t in tweets:
            if skip_existing and tweet_exists(session, t["id"]):
                print(f"  ⏭  Skipped {t['id']} (already exists)")
                skipped += 1
                continue

            tweet = Tweet(**t)
            session.add(tweet)
            inserted += 1

        session.commit()
        print(f"✅  Inserted {inserted} tweet(s) into the database")
        if skipped:
            print(f"⏭   Skipped {skipped} duplicate(s)")

        if embed and inserted > 0:
            _generate_embeddings(session, [t["id"] for t in tweets if t["id"]])

        return inserted


def _generate_embeddings(session, tweet_ids: list[str]) -> None:
    """Generate embeddings for the given tweet IDs."""
    try:
        from fastembed import TextEmbedding

        MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
        print(f"🔮  Loading model: {MODEL_NAME}")
        model = TextEmbedding(MODEL_NAME)

        tweets = session.query(Tweet).filter(Tweet.id.in_(tweet_ids)).all()

        texts = [t.content for t in tweets]
        ids = [t.id for t in tweets]

        if not texts:
            print("⚠️   No tweets found to embed")
            return

        print(f"🔮  Encoding {len(texts)} tweet(s)...")
        embeddings = list(model.embed(texts))

        session.add_all(
            [
                TweetEmbedding(
                    tweet_id=tid,
                    embedding_model=MODEL_NAME,
                    embedded_text=text,
                    embedding=emb.tolist(),
                )
                for tid, text, emb in zip(ids, texts, embeddings)
            ]
        )
        session.commit()
        print(f"✅  Generated embeddings for {len(texts)} tweet(s)")

    except ImportError:
        print(
            "⚠️   sentence-transformers not installed — skipping embeddings. "
            "Run: pip install sentence-transformers"
        )


# ── CSV mode ────────────────────────────────────────────────────────


def from_csv(path: str) -> list[dict[str, Any]]:
    """Read tweets from a CSV file (same format as selected_tweets.csv)."""
    path = Path(path)
    if not path.exists():
        print(f"❌  File not found: {path}")
        sys.exit(1)

    tweets: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("id", "").strip():
                continue
            tweets.append(tweet_from_row(row))

    print(f"📄  Read {len(tweets)} tweet(s) from {path}")
    return tweets


# ── Main ────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add new tweets to the database (for testing)."
    )
    parser.add_argument("--csv", help="Path to CSV file with tweets")
    parser.add_argument("--dry-run", action="store_true", help="Validate without inserting")
    parser.add_argument("--embed", action="store_true", help="Generate embeddings after insert")
    args = parser.parse_args()

    if args.csv:
        tweets = from_csv(args.csv)
    else:
        print(f"📋  Using hardcoded TEST_TWEETS list ({len(TEST_TWEETS)} tweet(s))")
        print("    Edit TEST_TWEETS in the script to add your own.\n")
        tweets = TEST_TWEETS

    insert_tweets(tweets, dry_run=args.dry_run, embed=args.embed)


if __name__ == "__main__":
    main()
