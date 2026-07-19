# Tweet QA Agent — Tool-Call Pattern

A LangChain agent that answers questions about Donald Trump's tweets using a **tool-call loop** pattern. The LLM decides which tool to call and when to answer directly — no hardcoded routing.

> **Stack:** LangChain `create_agent` · DeepSeek V4 Flash · PostgreSQL + pgvector · SQLAlchemy · Sentence Transformers · FastAPI · Streamlit

## Architecture

```
User question → create_agent loop:
    LLM decides → calls relational_lookup or semantic_lookup → LLM reads result → calls again or answers
```

No classifier, no planner, no judgment node. The LLM owns the full decision loop.

Structured output is returned as a ` ```json` block in the agent's response, parsed by `AgentResponse.from_json_block()`.

## Interfaces

| Interface | Command |
|---|---|
| **CLI** | `uv run python main.py` |
| **Streamlit** | `uv run streamlit run streamlit_app.py` |
| **FastAPI** | `uv run uvicorn api:app --reload` |

## Tools

| Tool | Description |
|---|---|
| `relational_lookup` | Deterministic SQL-style queries (date range, mentions, hashtags, engagement, counts, sorting) |
| `semantic_lookup` | pgvector cosine similarity search over tweet content with optional metadata filters |

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
│   ├── models.py                # ORM: engine, session, Tweet, TweetEmbedding
│   └── setup_db.py              # CLI to create tables from scratch
├── alembic/
│   ├── env.py                   # Alembic config (reads DATABASE_URL from .env)
│   └── versions/                # Migration files
├── tools/
│   ├── db.py                    # Shared session helper
│   ├── relational_lookup.py     # @tool with Pydantic schema
│   └── semantic_lookup.py       # @tool with Pydantic schema
├── scripts/                     # Utility scripts
├── pyproject.toml
└── .env.example
```
