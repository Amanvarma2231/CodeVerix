"""
CodeVerix – LLM to LLM Communication System
Streamlit Web Dashboard

Run:  streamlit run app.py
"""

import streamlit as st
import time
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
#  Page config  (MUST be first Streamlit call)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CodeVerix – LLM↔LLM",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
#  Custom CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* General */
body { font-family: 'Segoe UI', sans-serif; }

/* Chat bubbles */
.msg-system {
    background: linear-gradient(90deg, #1a1a2e, #16213e);
    color: #a0d4ff;
    border-left: 4px solid #4fc3f7;
    padding: 10px 16px;
    border-radius: 8px;
    margin: 6px 0;
    font-size: 0.88rem;
}
.msg-coder {
    background: linear-gradient(135deg, #0f3460, #16213e);
    color: #90caf9;
    border-left: 4px solid #42a5f5;
    padding: 14px 18px;
    border-radius: 10px;
    margin: 10px 0;
}
.msg-validator {
    background: linear-gradient(135deg, #1b4332, #0d2818);
    color: #a5d6a7;
    border-left: 4px solid #66bb6a;
    padding: 14px 18px;
    border-radius: 10px;
    margin: 10px 0;
}
.msg-pass   { border-left-color: #00e676 !important; }
.msg-fail   { border-left-color: #ff5252 !important; }

.sender-badge {
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    opacity: 0.8;
    margin-bottom: 6px;
}
.timestamp { font-size: 0.7rem; opacity: 0.5; float: right; }

/* Title */
.main-title {
    text-align: center;
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(90deg, #42a5f5, #66bb6a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.subtitle { text-align: center; color: #888; font-size: 1rem; margin-bottom: 1.5rem; }

/* Status bar */
.status-bar {
    background: #1e1e2e;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 0.85rem;
    margin-bottom: 10px;
    color: #ccc;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  Session state initialisation
# ─────────────────────────────────────────────────────────────
if "messages"       not in st.session_state: st.session_state.messages       = []
if "running"        not in st.session_state: st.session_state.running        = False
if "result"         not in st.session_state: st.session_state.result         = None
if "api_configured" not in st.session_state: st.session_state.api_configured = False


# ─────────────────────────────────────────────────────────────
#  Sidebar – Configuration
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    provider = st.selectbox("LLM Provider", ["gemini", "openai"], index=0)
    os.environ["LLM_PROVIDER"] = provider

    if provider == "gemini":
        api_key = st.text_input(
            "Gemini API Key",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Get from https://aistudio.google.com"
        )
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

        coder_model = st.selectbox(
            "Coder Model",
            ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
            index=0
        )
        validator_model = st.selectbox(
            "Validator Model",
            ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"],
            index=0
        )
    else:
        api_key = st.text_input(
            "OpenAI API Key",
            value=os.getenv("OPENAI_API_KEY", ""),
            type="password"
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        coder_model     = st.selectbox("Coder Model",     ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"])
        validator_model = st.selectbox("Validator Model", ["gpt-4o",      "gpt-4o-mini"])

    os.environ["CODER_MODEL"]     = coder_model
    os.environ["VALIDATOR_MODEL"] = validator_model

    max_rounds = st.slider("Max Validation Rounds", 1, 5, 2)

    st.divider()
    st.markdown("### 📊 Architecture")
    st.markdown("""
```
 Human Input
      │
      ▼
 Orchestrator
  ┌───────────┐
  │ CoderLLM  │──── writes code ────►
  └───────────┘                      │
                                     ▼
  ┌──────────────┐           ValidatorLLM
  │  PASS ✅     │◄─── validates ────┤
  │  FAIL ❌     │    (loops back)   │
  └──────────────┘                   │
        │                            │
   Human sees                  Human sees
   full chat                   full chat
```
    """)

    st.divider()
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.session_state.result   = None
        st.rerun()


# ─────────────────────────────────────────────────────────────
#  Header
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🤖 CodeVerix</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">LLM-to-LLM Communication System · Human Observable · Druidot Consulting</div>', unsafe_allow_html=True)

# Key metrics row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Messages",   len(st.session_state.messages))
col2.metric("Coder Messages",   sum(1 for m in st.session_state.messages if m.get("role") == "coder"))
col3.metric("Validator Messages", sum(1 for m in st.session_state.messages if m.get("role") == "validator"))
passed_count = sum(1 for m in st.session_state.messages if "PASS" in m.get("content","").upper() and m.get("role") == "validator")
col4.metric("Validations Passed", passed_count)

st.divider()


# ─────────────────────────────────────────────────────────────
#  Helper: render one message bubble
# ─────────────────────────────────────────────────────────────
def render_message(msg: dict):
    role    = msg.get("role", "system")
    sender  = msg.get("sender", "")
    content = msg.get("content", "")
    ts      = msg.get("timestamp", "")

    if role == "system":
        st.markdown(
            f'<div class="msg-system">🔄 {content} <span class="timestamp">{ts}</span></div>',
            unsafe_allow_html=True
        )
    elif role == "coder":
        # Extract code block if present
        st.markdown(
            f'<div class="msg-coder"><div class="sender-badge">🤖 {sender}</div>'
            f'<span class="timestamp">{ts}</span></div>',
            unsafe_allow_html=True
        )
        # Parse EXPLANATION / code / NOTES sections
        _render_coder_content(content)

    elif role == "validator":
        is_pass = "VALIDATION RESULT: PASS" in content.upper()
        extra_cls = "msg-pass" if is_pass else "msg-fail"
        st.markdown(
            f'<div class="msg-validator {extra_cls}"><div class="sender-badge">🔍 {sender}</div>'
            f'<span class="timestamp">{ts}</span></div>',
            unsafe_allow_html=True
        )
        _render_validator_content(content, is_pass)


def _render_coder_content(content: str):
    """Render coder output with syntax-highlighted code block."""
    if "```python" in content:
        parts = content.split("```python")
        # text before code
        if parts[0].strip():
            st.markdown(parts[0])
        rest = parts[1]
        code_parts = rest.split("```")
        code = code_parts[0]
        st.code(code.strip(), language="python")
        if len(code_parts) > 1 and code_parts[1].strip():
            st.markdown(code_parts[1])
    else:
        st.markdown(content)


def _render_validator_content(content: str, is_pass: bool):
    """Render validation with colour-coded status."""
    icon = "✅" if is_pass else "❌"
    if is_pass:
        st.success(f"{icon} VALIDATION PASSED")
    else:
        st.error(f"{icon} VALIDATION FAILED")
    # Show full content in expander
    with st.expander("📋 Full Validation Report", expanded=not is_pass):
        st.markdown(content)


# ─────────────────────────────────────────────────────────────
#  Main layout: chat area + input
# ─────────────────────────────────────────────────────────────
chat_area = st.container()

with chat_area:
    if not st.session_state.messages:
        st.info(
            "👋 Welcome to **CodeVerix**!\n\n"
            "Enter a coding task below (e.g. *'Write a Python function to find prime numbers'*) "
            "and watch **CoderLLM** and **ValidatorLLM** collaborate live!\n\n"
            "📌 Make sure to enter your API key in the sidebar first."
        )
    for msg in st.session_state.messages:
        render_message(msg)


# ─────────────────────────────────────────────────────────────
#  Input area
# ─────────────────────────────────────────────────────────────
st.divider()

# Quick task examples
st.markdown("**🚀 Quick tasks:**")
example_tasks = [
    "Write a Python function to find all prime numbers up to N using Sieve of Eratosthenes",
    "Write a Python class for a Stack data structure with push, pop, peek operations",
    "Write a Python function to merge two sorted lists into one sorted list",
    "Write a Python decorator that logs function calls with arguments and return values",
    "Write a Python function to parse a CSV string and return a list of dictionaries",
]
qcols = st.columns(len(example_tasks))
selected_example = ""
for i, (col, task) in enumerate(zip(qcols, example_tasks)):
    short = task[:40] + "..."
    if col.button(short, key=f"ex_{i}"):
        selected_example = task

task_input = st.text_area(
    "💬 Enter your coding task:",
    value=selected_example,
    height=80,
    placeholder="e.g. Write a Python function that reverses a linked list...",
)

btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])
run_btn    = btn_col1.button("▶️ Run LLM-to-LLM Session", type="primary", use_container_width=True)
export_btn = btn_col2.button("💾 Export Conversation",    use_container_width=True)
_          = btn_col3.button("🔄 Clear",                  use_container_width=True, on_click=lambda: st.session_state.update(messages=[], result=None))


# ─────────────────────────────────────────────────────────────
#  Run the LLM session
# ─────────────────────────────────────────────────────────────
if run_btn and task_input.strip():
    # Validate API key is set
    provider_now = os.getenv("LLM_PROVIDER", "gemini")
    key_name     = "GEMINI_API_KEY" if provider_now == "gemini" else "OPENAI_API_KEY"
    if not os.getenv(key_name, "").strip():
        st.error("⚠️ Please enter your API key in the sidebar first!")
    else:
        # Clear previous session
        st.session_state.messages = []
        st.session_state.result   = None

        # Import here so env vars are already set
        from orchestrator import ConversationOrchestrator

        status_placeholder = st.empty()
        progress_bar       = st.progress(0)

        def on_new_message(msg):
            """Callback: add message to session state and trigger re-render."""
            st.session_state.messages.append(msg.to_dict())
            # Update status bar
            status_placeholder.markdown(
                f'<div class="status-bar">🔄 <b>{msg.sender}</b>: {msg.content[:100]}...</div>',
                unsafe_allow_html=True
            )

        orchestrator = ConversationOrchestrator(
            max_rounds=max_rounds,
            on_message=on_new_message,
        )

        with st.spinner("🤖 LLMs are collaborating..."):
            try:
                result = orchestrator.run_coding_task(task_input.strip())
                st.session_state.result = result
                progress_bar.progress(100)
                status_placeholder.empty()
            except Exception as e:
                st.error(f"❌ Error: {e}\n\nMake sure your API key is valid and you have internet access.")
                progress_bar.empty()

        st.rerun()

elif run_btn and not task_input.strip():
    st.warning("⚠️ Please enter a task first!")


# ─────────────────────────────────────────────────────────────
#  Show final result summary
# ─────────────────────────────────────────────────────────────
if st.session_state.result:
    result = st.session_state.result
    st.divider()
    st.markdown("## 📊 Session Summary")

    rcols = st.columns(3)
    rcols[0].metric("Status",       "✅ PASSED" if result["passed"] else "❌ FAILED")
    rcols[1].metric("Rounds Taken", result.get("rounds", 1))
    rcols[2].metric("Total Messages", len(st.session_state.messages))

    if result["passed"]:
        st.success("🎉 Code passed validation! Ready to use.")
        with st.expander("📋 Final Validated Code", expanded=True):
            code_content = result.get("final_code", "")
            if "```python" in code_content:
                code_part = code_content.split("```python")[1].split("```")[0]
                st.code(code_part.strip(), language="python")
            else:
                st.markdown(code_content)
    else:
        st.warning("⚠️ Code did NOT pass validation after all rounds. Review the conversation above.")


# ─────────────────────────────────────────────────────────────
#  Export
# ─────────────────────────────────────────────────────────────
if export_btn and st.session_state.messages:
    log_path = f"conversation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(st.session_state.messages, f, indent=2, ensure_ascii=False)
    st.success(f"✅ Conversation exported to `{log_path}`")
    with open(log_path, "rb") as f:
        st.download_button(
            "⬇️ Download JSON",
            f,
            file_name=log_path,
            mime="application/json"
        )
