-- ====================================================================
--  Hybrid RAG over Tweets — Database Schema
-- ====================================================================
--  Run via:  psql -d tweets_rag -f schema.sql
--  Or use  python -m db.setup_db
-- ====================================================================

-- 1. Extensions -----------------------------------------------------

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. Core table: tweets ---------------------------------------------

CREATE TABLE IF NOT EXISTS tweets (
    id          TEXT PRIMARY KEY,
    link        TEXT NOT NULL,
    content     TEXT NOT NULL,
    date        TIMESTAMPTZ NOT NULL,
    retweets    INTEGER,
    favorites   INTEGER,
    mentions    TEXT[],
    hashtags    TEXT[],
    geo         TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- 3. Embeddings table -----------------------------------------------

CREATE TABLE IF NOT EXISTS tweet_embeddings (
    tweet_id       TEXT NOT NULL REFERENCES tweets(id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    embedded_text  TEXT NOT NULL,
    embedding      vector(384) NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (tweet_id, embedding_model)
);

-- 4. Indexes --------------------------------------------------------

-- Relational lookup indexes
CREATE INDEX IF NOT EXISTS tweets_date_idx    ON tweets (date);
CREATE INDEX IF NOT EXISTS tweets_retweets_idx      ON tweets (retweets);
CREATE INDEX IF NOT EXISTS tweets_favorites_idx     ON tweets (favorites);
CREATE INDEX IF NOT EXISTS tweets_mentions_gin_idx  ON tweets USING gin (mentions);
CREATE INDEX IF NOT EXISTS tweets_hashtags_gin_idx  ON tweets USING gin (hashtags);
CREATE INDEX IF NOT EXISTS tweets_content_trgm_idx  ON tweets USING gin (content gin_trgm_ops);

-- Vector similarity index (HNSW for production-quality ANN search)
CREATE INDEX IF NOT EXISTS tweet_embeddings_vector_idx
    ON tweet_embeddings
    USING hnsw (embedding vector_cosine_ops);
