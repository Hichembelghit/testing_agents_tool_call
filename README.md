# Tweet QA Agent — Tool-Call Pattern

A LangChain agent that answers questions about Donald Trump's tweets using a **tool-call loop** pattern. The LLM decides which tool to call and when to answer directly — no hardcoded routing.

> **Stack:** LangChain `create_agent` · DeepSeek V4 Flash · PostgreSQL + pgvector · SQLAlchemy (sync + async) · asyncpg · Sentence Transformers · FastAPI · Streamlit

## Architecture

```
User question → create_agent loop:
    LLM decides → calls relational_lookup or semantic_lookup → LLM reads result → calls again or answers
```

No classifier, no planner, no judgment node. The LLM owns the full decision loop.

Structured output is returned as a `` ```json `` block in the agent's response, parsed by `AgentResponse.from_json_block()`.

## Interfaces

| Interface | Command |
|---|---|
| **CLI** | `uv run python main.py` |
| **Streamlit** | `uv run streamlit run streamlit_app.py` |
| **FastAPI** | `uv run uvicorn api:app --reload` |

### Running Streamlit

```bash
# From the project root:
uv run streamlit run streamlit_app.py

# The app opens in your browser at http://localhost:8501
# Type a question about Trump's tweets and see the agent's response
# with tweet IDs, content, retweets, and favorites.
```

## Tools

| Tool | Description |
|---|---|
| `relational_lookup` | Deterministic SQL-style queries (date range, mentions, hashtags, engagement, counts, sorting) |
| `semantic_lookup` | pgvector cosine similarity search over tweet content with optional metadata filters |

### `relational_lookup` — Batched Concurrent Queries

The relational lookup tool accepts **multiple operations in a single call** and executes them concurrently via `asyncio.gather()` over a single async database session. This avoids multiple round-trips when the agent needs several pieces of information at once.

**Supported operations:**
| Operation | Returns |
|---|---|
| `select` (default) | Matching tweet rows with optional sorting and limit |
| `count` | Total row count matching the filters |
| `aggregate` | Count + average/sum of retweets and favorites |
| `fetch_by_ids` | Specific tweets by their IDs |

**Example — batched call:**
```json
{
  "operations": [
    {"operation": "count", "date_from": "2020-01-01", "date_to": "2021-01-01"},
    {"operation": "select", "order_by": "retweets", "limit": 3},
    {"operation": "aggregate", "min_favorites": 100}
  ]
}
```

All three queries run concurrently in a single database session — total time ≈ max(query times), not sum.

**Async infrastructure:** The tool uses `create_async_engine` with `asyncpg` for native async PostgreSQL I/O. The sync engine (`psycopg2`) is kept for scripts and Alembic migrations.

## Setup

```bash
# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv sync

# Copy and fill in your credentials
cp .env.example .env

# Run the agent (choose your interface)
uv run python main.py
```

## Database Migrations

Alembic is configured for schema changes:

```bash
# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "description"

# Apply pending migrations
uv run alembic upgrade head

# Create tables from scratch (no existing DB)
uv run python -m db.setup_db
```

## Example Questions

| Category | Example |
|---|---|
| Count | `"How many tweets in 2019?"` |
| Metadata | `"Top 10 most retweeted tweets"` |
| Hashtag | `"Tweets with #MAGA sorted by favorites"` |
| Semantic | `"What does Trump say about trade?"` |
| Hybrid | `"What did Trump say about China in 2014?"` |
| Hybrid | `"Most liked tweets about trade after 2016"` |

## Project Structure

```
├── agent.py                     # create_agent setup with system prompt
├── main.py                      # CLI entrypoint
├── api.py                       # FastAPI server
├── streamlit_app.py             # Streamlit chat UI
├── response_models.py           # Pydantic schemas + JSON parser
├── db/
│   ├── models.py                # ORM: sync + async engines, session factories, Tweet, TweetEmbedding
│   └── setup_db.py              # CLI to create tables from scratch
├── alembic/
│   ├── env.py                   # Alembic config (reads DATABASE_URL from .env)
│   └── versions/                # Migration files
├── tools/
│   ├── db.py                    # Shared sync session helper + utilities
│   ├── relational_lookup.py     # @tool — batched concurrent SQL queries (asyncpg)
│   └── semantic_lookup.py       # @tool — pgvector similarity search
├── scripts/                     # Utility scripts
├── pyproject.toml
└── .env.example
```
