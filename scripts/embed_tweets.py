#!/usr/bin/env python3
"""Generate embeddings for tweets and store them in PostgreSQL via SQLAlchemy.

Usage
-----
    python -m ingestion.embed_tweets
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from fastembed import TextEmbedding
from sqlalchemy import select
from sqlalchemy.orm import Session

# Ensure the project root is on sys.path so "db" is importable
# whether the script is run as ``python -m ...`` or directly.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from db.models import get_session
from db.models import Tweet, TweetEmbedding

load_dotenv()

MODEL_NAME = "all-MiniLM-L6-v2"  # 384-dim embeddings

# ── Batch sizes ────────────────────────────────────────────────────
# How many texts to feed the model in one forward pass.
# CPU sweet-spot: 64-256. GPU sweet-spot: 256-1024.
ENCODE_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "500"))

# How many rows to insert per database COMMIT.
# Larger = fewer round-trips, but uses more memory in the Python list.
DB_INSERT_BATCH_SIZE = int(os.getenv("EMBED_DB_INSERT_SIZE", "1000"))


def get_tweets_without_embeddings(session: Session) -> list[tuple[str, str]]:
    """Return (id, content) for tweets lacking an embedding for ``MODEL_NAME``."""
    # Subquery: tweet IDs that already have an embedding for this model
    already_embedded = (
        select(TweetEmbedding.tweet_id).where(
            TweetEmbedding.embedding_model == MODEL_NAME
        )
    ).scalar_subquery()

    stmt = (
        select(Tweet.id, Tweet.content)
        .where(Tweet.id.not_in(already_embedded))
        .order_by(Tweet.id)
    )
    rows = session.execute(stmt).all()
    return [(r[0], r[1]) for r in rows]


def main() -> None:
    print(f"🔮  Loading model: {MODEL_NAME}")
    model = TextEmbedding(MODEL_NAME)

    with get_session() as session:
        rows = get_tweets_without_embeddings(session)
        total = len(rows)
        print(f"📊  {total} tweets need embeddings")

        if total == 0:
            print("✅  All tweets already embedded!")
            return

        t_start = time.perf_counter()
        total_encoded = 0

        # Outer loop: database-insert batches
        for db_start in range(0, total, DB_INSERT_BATCH_SIZE):
            db_batch = rows[db_start : db_start + DB_INSERT_BATCH_SIZE]

            all_ids: list[str] = []
            all_texts: list[str] = []
            all_embs: list[list[float]] = []

            # Inner loop: model-encode sub-batches
            for enc_start in range(0, len(db_batch), ENCODE_BATCH_SIZE):
                enc_batch = db_batch[enc_start : enc_start + ENCODE_BATCH_SIZE]
                texts = [r[1] for r in enc_batch]
                ids = [r[0] for r in enc_batch]

                print(
                    f"  🔮  Encoding {total_encoded + len(ids):,}/{total:,}  "
                    f"(batch of {len(ids)})..."
                )
                embeddings = list(model.embed(texts))

                all_ids.extend(ids)
                all_texts.extend(texts)
                all_embs.extend(emb.tolist() for emb in embeddings)
                total_encoded += len(ids)

            # Bulk INSERT via SQLAlchemy ORM
            session.add_all(
                [
                    TweetEmbedding(
                        tweet_id=tid,
                        embedding_model=MODEL_NAME,
                        embedded_text=text,
                        embedding=emb,
                    )
                    for tid, text, emb in zip(all_ids, all_texts, all_embs)
                ]
            )
            session.commit()

            elapsed = time.perf_counter() - t_start
            print(
                f"     ✅  Inserted {len(all_ids):,} rows  "
                f"({total_encoded:,}/{total:,})  "
                f"⏱ {elapsed:.1f}s  "
                f"📈 {total_encoded / elapsed:.1f} tweets/s"
            )

    elapsed = time.perf_counter() - t_start
    print(
        f"\n✅  Done! {total:,} tweets embedded with '{MODEL_NAME}' "
        f"in {elapsed:.1f}s ({total / elapsed:.1f} tweets/s)"
    )


if __name__ == "__main__":
    main()
