# revamped.py
import os
import json
import uuid
import time
import requests
import streamlit as st

# --- Config ---
WEBHOOK_URL = "https://myvillageproject.app.n8n.cloud/webhook/family-history-chatbot"
TIMEOUT_SECS = 25

st.set_page_config(
    page_title="Family History Chatbot (Revamp Start)",
    page_icon="🧬",
    layout="centered"
)

# --- Session state ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! Ask me anything about Mazamesso’s family history."}
    ]


# --- Helpers ---
def call_webhook(question: str, history: list) -> str:
    """
    Sends a POST to the n8n webhook. We include:
      - question (current user input)
      - history (list of {role, content})
      - session_id (stable per session)
    Tries to parse common JSON shapes from n8n; falls back to raw text.
    """
    payload = {
        "question": question,
        "history": history,
        "session_id": st.session_state.session_id,
        "source": "streamlit-app",
    }

    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=TIMEOUT_SECS)
    except requests.RequestException as e:
        return f"⚠️ Network error reaching webhook: {e}"

    # Prefer JSON; otherwise fall back to text
    try:
        data = resp.json()

        # Case 1: n8n returns a list of dicts with "output"
        if isinstance(data, list) and len(data) > 0:
            # find first dict with "output"
            for item in data:
                if isinstance(item, dict) and "output" in item:
                    return str(item["output"])
            # if no "output", show entire JSON list
            return json.dumps(data, ensure_ascii=False, indent=2)

        # Case 2: n8n returns a dict with "output"
        if isinstance(data, dict) and "output" in data:
            return str(data["output"])

        # Case 3: Try other common keys
        if isinstance(data, dict):
            for key in ("answer", "reply", "text", "message", "result", "data"):
                if key in data and data[key]:
                    return data[key] if isinstance(data[key], str) else json.dumps(data[key], ensure_ascii=False, indent=2)

        # Nothing matched — show JSON
        return json.dumps(data, ensure_ascii=False, indent=2)

    except Exception:
        # Not JSON → use raw text
        return resp.text.strip() if resp.text else f"(No response body; HTTP {resp.status_code})"


def save_transcript():
    ts = int(time.time())
    path = f"transcript_{ts}.json"
    with open(path, "w") as f:
        json.dump(
            {
                "session_id": st.session_state.session_id,
                "messages": st.session_state.messages,
                "saved_at": ts,
            },
            f,
            indent=2,
        )
    return path


# --- UI Header ---
st.title("🧬 Family History Chatbot")
st.caption("This is the start of the **revamped** version I will be working on later.")

# --- Sidebar ---
with st.sidebar:
    st.subheader("Settings")
    st.write("**Webhook**")
    st.code(WEBHOOK_URL, language="text")
    st.write("**Session ID**")
    st.code(st.session_state.session_id, language="text")

    colA, colB = st.columns(2)
    if colA.button("🔄 New Session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = [
            {"role": "assistant", "content": "New session started. How can I help?"}
        ]
        st.rerun()
    if colB.button("🧹 Clear Chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Chat cleared. Ask your next question!"}
        ]
        st.rerun()

    st.divider()
    if st.button("💾 Save Transcript"):
        path = save_transcript()
        st.success(f"Saved as {path}")

# --- Render history ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        # Render as Markdown so lists and paragraphs look good
        st.markdown(m["content"])

# --- Input box ---
user_input = st.chat_input("Type your question about your family history…")

# --- Handle submit ---
if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Call webhook and display assistant reply
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            answer = call_webhook(user_input, st.session_state.messages)
            st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
