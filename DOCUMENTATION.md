# 🐦 Tweet QA Agent — Project Documentation

> **Hybrid RAG over Trump Tweets** · LangChain `create_agent` · DeepSeek V4 Flash · PostgreSQL + pgvector · FastEmbed · Streamlit

---

## 1. Project Overview

General-purpose QA system over Trump's tweets. Answers require either **relational lookup** (dates, counts, hashtags, engagement) or **semantic lookup** (meaning-based vector search via pgvector) — or both.

### Stack

| Component | Technology |
|---|---|
| Agent | LangChain `create_agent` (tool-call loop) |
| LLM | DeepSeek V4 Flash |
| Database | PostgreSQL 16 + pgvector |
| Embeddings | FastEmbed `all-MiniLM-L6-v2` (384-dim, CPU) |
| Frontend | Streamlit (+ CLI) |

---

## 2. Architecture

```
User Question → create_agent loop:
    LLM decides → calls relational_lookup (SQL) and/or semantic_lookup (pgvector)
                → reads results → answers with citations
```

The LLM owns the full decision loop — no hardcoded routing.

---

## 3. Design Reference (`SYSTEM_DESIGN.pdf`)

The original design specified:
- **Two Postgres tables**: `tweets` + `tweet_embeddings` (general-purpose, no per-task tables)
- **LangGraph state machine** with explicit nodes (Analyze → Plan → Run Tools → Merge → Judge → Synthesize)
- **Four query patterns**: SQL-only, semantic-only, hybrid, LLM synthesis
- **Constrained tools**: typed lookup, no arbitrary SQL
- **Evidence preservation**: answers cite tweet IDs/links

---

## 4. Implementation

### 4.1 Agent — `create_agent` (not raw LangGraph)

We chose LangChain's `create_agent` over the proposed state machine — simpler, less boilerplate, same capability. The system prompt (150+ lines) handles what explicit graph nodes would: tool strategy, batching, deduplication, output format.

```python
llm = ChatDeepSeek(model="deepseek-v4-flash", temperature=0.7)
agent = create_agent(model=llm, tools=[relational_lookup, semantic_lookup], system_prompt=SYSTEM_PROMPT)
```

### 4.2 Structured Output

Agent appends a ` ```json ``` ` block parsed by `AgentResponse.from_json_block()`. Falls back to raw text if JSON parsing fails.

### 4.3 Database (`db/models.py`)

- **`tweets`**: `id TEXT PK`, `content`, `date`, `retweets`, `favorites`, `mentions TEXT[]`, `hashtags TEXT[]` + GIN/B-tree indexes
- **`tweet_embeddings`**: `(tweet_id, embedding_model) PK`, `embedding VECTOR(384)` with HNSW index

### 4.4 Ingestion Pipeline

- **CSV Loader** (`scripts/load_csv.py`): idempotent (`ON CONFLICT DO NOTHING`), normalizes mentions/hashtags
- **Embedding Generator** (`scripts/embed_tweets.py`): FastEmbed on CPU, batched (500/model-pass, 1000/DB-commit), skips already-embedded tweets

### 4.5 Tools

| Tool | Purpose | Key Features |
|---|---|---|
| `relational_lookup` | SQL metadata queries | **Batched operations** in one call; supports `engagement` = retweets+favorites ordering |
| `semantic_lookup` | pgvector similarity search | Cosine distance with optional metadata filters; lazy-loaded FastEmbed model |

### 4.6 Docker

`docker-compose.yml` with `pgvector/pgvector:pg16` + Streamlit. Entrypoint retries DB connection (×15), enables extensions, creates tables, loads data, generates embeddings — all idempotent.

---

## 5. Challenges & Solutions

| # | Challenge | Solution |
|---|---|---|
| 1 | **Vector dimension mismatch** — PDF said `vector(1536)` (OpenAI), but that adds cost + network dependency | Switched to **FastEmbed** `all-MiniLM-L6-v2` (384-dim, CPU-only) — free, no API key, runs in Docker without GPU |
| 2 | **Multiple SQL queries per question** — e.g. "how many tweets in 2020, show top 3" would need separate calls | `relational_lookup` accepts a **list of batched operations** running in one DB session |
| 3 | **Repetitive semantic results** — many near-identical tweets returned, LLM lists each redundantly | System prompt instructs deduplication: group, summarize, mention count, call again for diverse angles |
| 4 | **Unreliable JSON parsing** — LLM output is notoriously inconsistent | Two-layer approach: prompt says ` ```json ``` ` block; regex + Pydantic validation; falls back to raw text on failure |
| 5 | **Tweet ID format** — CSV may have scientific notation IDs exceeding safe integer range | `id TEXT PRIMARY KEY` (not numeric), read as string directly |
| 6 | **Docker startup race** — app container starts before PostgreSQL is ready | Retry loop (×15 attempts, 2s apart) + `depends_on: condition: service_healthy` with `pg_isready` |
| 7 | **Idempotent setup** — restarting Docker must not duplicate data | Every step checks prior state: `CREATE TABLE IF NOT EXISTS`, `ON CONFLICT DO NOTHING`, skip-if-embedded checks |
| 8 | **GPU-free embedding** — Docker environment has no GPU | FastEmbed runs on CPU with batched encoding (500 texts/batch) |
| 9 | **Engagement sorting** — `retweets + favorites` computed column not native to SQLAlchemy | Computed inline in `ORDER BY` clause: `(Tweet.retweets + Tweet.favorites)` |
| 10 | **Embedding model name stability** — FastEmbed names may change across versions | Two env vars: `EMBEDDING_MODEL` (library name) + `DB_EMBEDDING_MODEL` (stable DB identifier) |

---

## 6. Design vs. Implementation: Key Deviations

| Aspect | PDF Design | Actual Implementation | Rationale |
|---|---|---|---|
| **Agent Framework** | Custom LangGraph state machine (7+ nodes) | LangChain `create_agent` (tool-call loop) | Simpler, LLM handles routing naturally |
| **Vector Dim** | `vector(1536)` | `vector(384)` | FastEmbed (CPU, free) |
| **Column Name** | `created_at` | `date` | CSV source uses `date` |
| **Evidence Loop** | Explicit judge node | LLM decides within tool-call loop | Handled by `create_agent` |
| **Embedding Provider** | OpenAI / external API | FastEmbed (local CPU) | Zero network dependency |
| **Output Format** | Natural language | ` ```json ``` ` + Pydantic validation | Structured parsing for UI |
| **Batched Ops** | Not in design | List of operations per call | Fewer round-trips |
| **Docker** | Not in design | Full `docker-compose` + idempotent entrypoint | One-command setup |

### Why Tool-Call Strategy Instead of a Workflow?

The PDF proposed a **workflow** (LangGraph state machine with explicit nodes: Analyze → Plan → Run → Merge → Judge → loop → Synthesize). We chose a **tool-call strategy** (`create_agent`) instead. Here's why:

| Factor | Workflow (LangGraph) | Tool-Call Strategy (create_agent) |
|---|---|---|
| **Routing** | Hardcoded — nodes and transitions defined at build time | Dynamic — LLM decides which tool to call and when, *at inference time* |
| **Flexibility** | Adding a new retrieval pattern requires new nodes + edges | Adding a new pattern is just a system prompt edit |
| **Code volume** | ~100–200 lines of graph scaffolding + state types + node functions | ~10 lines — `create_agent(llm, tools, system_prompt)` |
| **Maintenance** | State schema must be kept in sync across all nodes | No explicit state; LangChain manages message history internally |
| **Adaptability** | If a question doesn't fit the predefined graph flow, it fails or needs a new path | The LLM adapts its tool-use sequence on the fly — no predefined paths needed |
| **Debugging** | Explicit control flow makes execution traceable, but verbose | Fewer lines of code to debug; the system prompt is the single source of truth for agent behavior |

**Key insight:** A workflow is ideal when the process is well-defined and unlikely to change (e.g., a data pipeline). A tool-call strategy is ideal when the task is **open-ended** — the LLM needs to decide *which* tool, *how many* calls, and *in what order*. For a QA system where questions vary from simple counts to complex multi-step hybrid queries, the tool-call loop is the right fit.

---

## 7. Data Model

### `tweets`

| Column | Type | Notes |
|---|---|---|
| `id` | `TEXT PK` | String (avoids scientific notation) |
| `content` | `TEXT NOT NULL` | Main semantic field |
| `date` | `TIMESTAMPTZ` | Tweet timestamp |
| `retweets` / `favorites` | `INTEGER` | Engagement metrics |
| `mentions` / `hashtags` | `TEXT[]` | GIN-indexed arrays |
| `raw_payload` | `JSONB` | Original record for auditability |

Indexes: B-tree on `date`, `retweets`, `favorites`; GIN on arrays; trigram on `content`.

### `tweet_embeddings`

| Column | Type | Notes |
|---|---|---|
| `tweet_id` | `TEXT FK → tweets` | Composite PK with `embedding_model` |
| `embedding` | `VECTOR(384)` | HNSW index with `vector_cosine_ops` |

---

## 8. Agent Strategy

```
User Question
  ├─ Pure metadata? → relational_lookup → answer
  ├─ Topic/theme?  → semantic_lookup → answer
  ├─ Hybrid?       → semantic_lookup with metadata filters → answer
  └─ Complex?      → batch operations + merge → answer
```

Every answer includes a ` ```json ``` ` block with `{ "answer", "count", "tweets": [{id, content, date, retweets, favorites}] }`.

---

## 9. Deployment

**Local:**
```bash
uv sync && cp .env.example .env  # add DEEPSEEK_API_KEY
createdb tweets_rag
uv run python -m db.setup_db
uv run python scripts/load_csv.py trump_tweets.csv
uv run python scripts/embed_tweets.py
uv run python main.py                          # CLI
uv run streamlit run streamlit_app.py           # Web UI
```

**Docker (one command):**
```bash
docker compose up --build
```
Starts PostgreSQL + pgvector, creates tables, loads tweets, generates embeddings, launches Streamlit at `http://localhost:8080` — all idempotent.

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | Yes | — | DeepSeek API key |
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | FastEmbed model |
| `DB_EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Stable DB identifier |
| `PORT` | No | `8080` | Streamlit port (Docker) |

---

## 10. Future Improvements

- **Multi-query semantic recall** — auto-generate query rephrasings and merge results
- **Alembic migrations** instead of `Base.metadata.create_all`
- **Evaluation harness** against `selected_tweets.csv` test set
- **Caching** for frequent queries

---

> **Design reference:** `SYSTEM_DESIGN.pdf`
