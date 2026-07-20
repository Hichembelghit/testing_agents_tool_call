"""CLI entry point for the tweet QA agent (tool-call pattern).

The agent returns structured output parsed from a JSON block in the response
and validated against the AgentResponse Pydantic schema.
"""

from dotenv import load_dotenv

from agent import agent
from response_models import AgentResponse


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with an ellipsis if it exceeds max_len."""
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


load_dotenv()

print("═══ Tweet QA Agent (tool-call pattern) ═══")
print("Ask questions about Trump's tweets. Type 'exit' to quit.\n")

while True:
    user_input = input("❓  ").strip()
    if not user_input or user_input.lower() in ("exit", "quit"):
        break

    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_input}]},
    )

    # Get the raw text from the agent's last message
    messages = result.get("messages", [])
    if not messages:
        print("  (No response from agent)")
        print()
        continue

    last = messages[-1]
    raw = last.get("content", "") if isinstance(last, dict) else last.content

    # Try to parse structured JSON; fall back to raw text
    structured = AgentResponse.from_json_block(raw)

    if structured is None:
        # Fallback: display the raw answer text
        print(f"\n{raw}\n")
        print()
        continue

    # ── Structured display ────────────────────────────────────────────────
    print(f"\n{structured.answer}\n")

    if structured.tweets:
        print(f"  ({structured.count} tweet{'s' if structured.count != 1 else ''} found)")
        print(f"  {'─' * 60}")
        for t in structured.tweets:
            print(f"  [{t.id}]  {t.date}")
            print(f"          {_truncate(t.content, 80)}")
            print(f"          ♻ {t.retweets}  ★ {t.favorites}")
    elif structured.count > 0:
        print(f"  ({structured.count} tweet{'s' if structured.count != 1 else ''} found)")
    else:
        print("  (No matching tweets found)")
    print()
