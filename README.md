# 🐦 Tweet QA Agent

A LangChain agent that answers questions about Donald Trump's tweets using a **tool-call loop** pattern. The LLM decides which tool to call and when to answer — no hardcoded routing.

> **Stack:** LangChain `create_agent` · DeepSeek V4 Flash · PostgreSQL + pgvector · FastEmbed · SQLAlchemy · Streamlit / CLI

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ with [pgvector](https://github.com/pgvector/pgvector)
- A [DeepSeek API key](https://platform.deepseek.com)

### Setup

```bash
# 1. Clone & enter
git clone <repo-url>
cd testing_agents_tool_call

# 2. Install dependencies
uv venv
source .venv/bin/activate
uv sync

# 3. Configure
cp .env.example .env
# Edit .env → add your DEEPSEEK_API_KEY

# 4. Create the database
createdb tweets_rag

# 5. Create tables
uv run python -m db.setup_db

# 6. Load tweet data
uv run python scripts/load_csv.py trump_tweets.csv

# 7. Generate embeddings (FastEmbed — runs on CPU, no API key needed)
uv run python scripts/embed_tweets.py

# 8. Run!
uv run python main.py                    # CLI
uv run streamlit run streamlit_app.py    # Web UI (http://localhost:8501)
```

### Or with Docker (one command, no installs needed)

```bash
docker compose up --build
```

This starts PostgreSQL + pgvector, creates tables, loads tweets, generates embeddings (FastEmbed on CPU), and launches Streamlit at `http://localhost:8080` — all automatically.

---

## How It Works

```
User question → create_agent loop:
    LLM decides → calls relational_lookup and/or semantic_lookup → reads results → answers
```

No classifier, no planner, no hardcoded routing. The LLM owns the full decision loop.

### Tools

| Tool | What it does |
|---|---|
| `relational_lookup` | SQL queries by metadata (dates, counts, hashtags, mentions, engagement, sorting). Supports **batched operations** in one call. |
| `semantic_lookup` | pgvector similarity search over tweet content (by topic/theme), with optional metadata filters. |

### Interfaces

| Interface | Command |
|---|---|
| **CLI** | `uv run python main.py` |
| **Streamlit** | `uv run streamlit run streamlit_app.py` |


---

## Example Questions

| Type | Example |
|---|---|
| Count | _"How many tweets in 2019?"_ |
| Metadata | _"Top 10 most retweeted tweets"_ |
| Hashtag | _"Tweets with #MAGA sorted by favorites"_ |
| Semantic | _"What does Trump say about trade?"_ |
| Hybrid | _"What did Trump say about China in 2014?"_ |

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/load_csv.py` | Load tweets from a CSV file into the database |
| `scripts/embed_tweets.py` | Generate FastEmbed embeddings for tweets missing them |
| `db/setup_db.py` | Create database tables from ORM models |

---

## Project Structure

```
├── agent.py                   # LangChain agent setup + system prompt
├── main.py                    # CLI entrypoint
├── streamlit_app.py           # Streamlit chat UI
├── response_models.py         # Pydantic schemas + JSON parser
├── db/
│   ├── models.py              # ORM: engine, session, Tweet, TweetEmbedding
│   └── setup_db.py            # CLI to create tables
├── tools/
│   ├── db.py                  # Shared DB helpers
│   ├── relational_lookup.py   # @tool — batched SQL metadata queries
│   └── semantic_lookup.py     # @tool — pgvector similarity search
├── scripts/
│   ├── load_csv.py            # Load tweets from CSV
│   └── embed_tweets.py        # Generate embeddings
├── docker-compose.yml         # Docker setup with pgvector
├── Dockerfile                 # Container image
├── pyproject.toml
└── .env.example
```
