# Tweet QA Agent — Tool-Call Pattern

A LangChain agent that answers questions about Donald Trump's tweets using a **tool-call loop** pattern. The LLM decides which tool to call and when to answer directly — no hardcoded routing.

> **Stack:** LangChain `create_agent` · PostgreSQL + pgvector · SQLAlchemy · Sentence Transformers

## Architecture

```
User question → create_agent loop:
    LLM decides → calls relational_lookup or semantic_lookup → LLM reads result → calls again or answers
```

No classifier, no planner, no judgment node. The LLM owns the full decision loop.

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

# Run the agent
uv run python main.py
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
├── db/
│   ├── models.py                # ORM: Tweet, TweetEmbedding
│   └── engine.py                # SQLAlchemy engine
├── tools/
│   ├── db.py                    # Shared session helper
│   ├── relational_lookup.py     # @tool with Pydantic schema
│   └── semantic_lookup.py       # @tool with Pydantic schema
├── pyproject.toml
└── .env.example
```
