"""Optional chat UI for AgentRAG.

Run with:
    streamlit run app_streamlit.py
"""

import streamlit as st

from src.agent import run_agent

st.set_page_config(page_title="AgentRAG", page_icon="🤖")
st.title("🤖 AgentRAG")
st.caption("Ask about the local docs, do math, search the web, or ask the time.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("trace"):
            with st.expander("agent trace"):
                st.write(" → ".join(message["trace"]))

query = st.chat_input("Ask a question...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("thinking..."):
            result = run_agent(query)
        st.markdown(result["answer"])
        if result["trace"]:
            with st.expander("agent trace"):
                st.write(" → ".join(result["trace"]))

    st.session_state.messages.append(
        {"role": "assistant", "content": result["answer"], "trace": result["trace"]}
    )
