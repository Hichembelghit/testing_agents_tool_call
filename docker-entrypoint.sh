#!/usr/bin/env bash
# ── Entrypoint for the Docker container ────────────────────────────
# Fully automated setup: enables pgvector, creates tables, loads tweet
# data, generates embeddings, then starts Streamlit.
# All steps are idempotent — safe to restart.
set -euo pipefail

echo "═══ Waiting for database connection ═══"
for i in $(seq 1 15); do
  uv run python -c "
from sqlalchemy import create_engine, text
import os
try:
    e = create_engine(os.environ['DATABASE_URL'])
    with e.connect() as c:
        c.execute(text('SELECT 1'))
        c.commit()
    print('OK')
except Exception:
    print('RETRY')
    exit(1)
" && break
  echo "   Attempt $i failed — retrying in 2s..."
  sleep 2
done

echo "═══ Enabling database extensions ═══"
uv run python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    c.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    c.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
    c.commit()
"

echo "═══ Creating tables (if needed) ═══"
uv run python -m db.setup_db

# ── Skip CSV load if tweets already exist ─────────────────────────
uv run python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    cnt = c.execute(text('SELECT count(*) FROM tweets')).scalar()
    exit(0 if cnt > 0 else 1)
" && CSV_SKIP=true || CSV_SKIP=false

if [ "$CSV_SKIP" = true ]; then
    echo "⏭️  Tweets already loaded — skipping CSV import"
else
    echo "═══ Loading tweets from CSV ═══"
    uv run python scripts/load_csv.py trump_tweets.csv
fi

# ── Skip embeddings if all tweets already embedded ────────────────
uv run python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    emb_cnt = c.execute(text('SELECT count(*) FROM tweet_embeddings')).scalar()
    tweet_cnt = c.execute(text('SELECT count(*) FROM tweets')).scalar()
    exit(0 if emb_cnt >= tweet_cnt else 1)
" && EMB_SKIP=true || EMB_SKIP=false

if [ "$EMB_SKIP" = true ]; then
    echo "⏭️  All tweets already embedded — skipping embedding"
else
    echo "═══ Generating embeddings ═══"
    uv run python scripts/embed_tweets.py
fi

echo ""
echo "═══ Starting Streamlit ═══"
exec uv run streamlit run streamlit_app.py \
    --server.headless=true \
    --server.port="${PORT:-8080}" \
    --server.enableCORS=false
