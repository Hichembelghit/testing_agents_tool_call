"""Render the compiled LangGraph for Hybrid RAG over Tweets as a PNG image."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import agent


PNG_PATH = ROOT / "docs" / "langgraph_graph.png"


def main() -> None:
    compiled_graph = agent.get_graph()
    png_bytes = compiled_graph.draw_mermaid_png()

    PNG_PATH.write_bytes(png_bytes)
    print(f"Wrote {PNG_PATH}")


if __name__ == "__main__":
    main()
