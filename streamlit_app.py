"""Streamlit frontend for the tweet QA agent.

Usage
-----
    uv run streamlit run streamlit_app.py
"""

import streamlit as st

from agent import agent
from response_models import AgentResponse

st.set_page_config(page_title="Tweet QA Agent", page_icon="🐦")
st.title("🐦 Tweet QA Agent")
st.markdown("Ask questions about Donald Trump's tweets.")

# ── Chat history ───────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "tweets" in msg:
            for t in msg["tweets"]:
                st.code(
                    f"[{t.id}]  {t.date}  ♻{t.retweets}  ★{t.favorites}\n"
                    f"    {t.content}"
                )

# ── Input and query ────────────────────────────────────────────────
if question := st.chat_input("Ask about Trump's tweets..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching tweets..."):
            result = agent.invoke(
                {"messages": [{"role": "user", "content": question}]}
            )
            raw = result["messages"][-1].content
            structured = AgentResponse.from_json_block(raw)

        if structured is None:
            st.markdown(raw)
            st.session_state.messages.append({"role": "assistant", "content": raw})
        else:
            st.markdown(structured.answer)
            tweets_data = []
            if structured.tweets:
                st.markdown(f"**{structured.count} tweet{'s' if structured.count != 1 else ''} found**")
                for t in structured.tweets:
                    st.code(
                        f"[{t.id}]  {t.date}  ♻{t.retweets}  ★{t.favorites}\n"
                        f"    {t.content}"
                    )
                    tweets_data.append(t)

            st.session_state.messages.append({
                "role": "assistant",
                "content": structured.answer,
                "tweets": tweets_data,
            })
