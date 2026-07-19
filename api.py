"""FastAPI server for the tweet QA agent.

Usage
-----
    uv run uvicorn api:app --reload
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from agent import agent
from response_models import AgentResponse

app = FastAPI(title="Tweet QA Agent")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AgentResponse)
def ask(question: str):
    """Ask a question about Trump's tweets and get a structured response."""
    result = agent.invoke(
        {"messages": [{"role": "user", "content": question}]}
    )

    raw = result["messages"][-1].content
    structured = AgentResponse.from_json_block(raw)

    if structured is None:
        return JSONResponse(
            status_code=422,
            content={"error": "Failed to parse agent response", "raw": raw},
        )

    return structured
