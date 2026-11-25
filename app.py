"""
CodeVerix – LLM to LLM Communication System
Optimized Streamlit Web Dashboard with Live Real-Time Message Streaming

Run:  streamlit run app.py
"""

import json
import os
import re
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
#  Page config (MUST be first Streamlit call)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CodeVerix – Live LLM↔LLM",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
#  Custom CSS (Modern Glassmorphic Dark UI)
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 2rem;
    max-width: 1180px;
}

/* Header */
.hero-box {
    background: linear-gradient(135deg, rgba(79,139,249,0.14), rgba(0,230,118,0.08));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1.1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
}
.main-title {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #60A5FA, #34D399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    line-height: 1.2;
}
.subtitle {
    color: #94A3B8;
    font-size: 0.92rem;
    margin-top: 0.25rem;
}
.pill-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    background: rgba(52, 211, 153, 0.14);
    color: #34D399;
    border: 1px solid rgba(52, 211, 153, 0.35);
}

/* Metric cards */
[data-testid="stMetric"] {
    background: rgba(19, 25, 43, 0.85);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 0.8rem 1rem;
}

/* Chat message cards */
.msg-system {
    background: rgba(30, 41, 59, 0.55);
    color: #93C5FD;
    border-left: 3px solid #38BDF8;
    padding: 8px 14px;
    border-radius: 8px;
    margin: 6px 0;
    font-size: 0.86rem;
}
.msg-header {
    padding: 10px 16px;
    border-radius: 12px 12px 4px 4px;
    margin-top: 12px;
    margin-bottom: 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.msg-coder-header {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.22), rgba(30, 58, 138, 0.18));
    border-left: 4px solid #60A5FA;
    color: #BFDBFE;
}
.msg-val-pass-header {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.22), rgba(6, 78, 59, 0.18));
    border-left: 4px solid #34D399;
    color: #A7F3D0;
}
.msg-val-fail-header {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.22), rgba(127, 29, 29, 0.18));
    border-left: 4px solid #F87171;
    color: #FECACA;
}
.sender-badge {
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.6px;
    text-transform: uppercase;
}
.timestamp {
    font-size: 0.74rem;
    opacity: 0.7;
}
.score-pill {
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    background: rgba(255,255,255,0.12);
    margin-left: 8px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  Session state initialisation
# ─────────────────────────────────────────────────────────────
if "messages"  not in st.session_state: st.session_state.messages  = []
if "result"    not in st.session_state: st.session_state.result    = None
if "task_text" not in st.session_state: st.session_state.task_text = ""


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def _get_secret(key: str, default: str = "") -> str:
    val = os.getenv(key, "")
    if val:
        return val
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default


def _extract_python_code(text: str) -> str:
    if "```python" in text:
        return text.split("```python", 1)[1].split("```", 1)[0].strip()
    if "```" in text:
        return text.split("```", 1)[1].split("```", 1)[0].strip()
    return ""


def _extract_score(text: str) -> str:
    match = re.search(r"SCORE:\s*([0-9]+(?:\.[0-9]+)?\s*/\s*10)", text, re.IGNORECASE)
    return match.group(1).replace(" ", "") if match else ""


def render_message(msg: dict):
    """Render a single message in the live LLM-to-LLM feed."""
    role    = msg.get("role", "system")
    sender  = msg.get("sender", "")
    content = msg.get("content", "")
    ts      = msg.get("timestamp", "")

    if role == "system":
        st.markdown(
            f'<div class="msg-system">🔄 {content} <span class="timestamp" style="float:right">{ts}</span></div>',
            unsafe_allow_html=True,
        )
    elif role == "coder":
        st.markdown(
            f'<div class="msg-header msg-coder-header">'
            f'  <span class="sender-badge">🤖 {sender}</span>'
            f'  <span class="timestamp">{ts}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if "```python" in content:
            before, rest = content.split("```python", 1)
            code_parts = rest.split("```", 1)
            if before.strip():
                st.markdown(before.strip())
            st.code(code_parts[0].strip(), language="python")
            if len(code_parts) > 1 and code_parts[1].strip():
                st.markdown(code_parts[1].strip())
        else:
            st.markdown(content)

    elif role == "validator":
        is_pass = "VALIDATION RESULT: PASS" in content.upper()
        score   = _extract_score(content)
        score_html = f'<span class="score-pill">Score: {score}</span>' if score else ""
        hdr_cls = "msg-val-pass-header" if is_pass else "msg-val-fail-header"
        status_txt = "PASS ✅" if is_pass else "FAIL ❌"

        st.markdown(
            f'<div class="msg-header {hdr_cls}">'
            f'  <span class="sender-badge">🔍 {sender} · {status_txt}{score_html}</span>'
            f'  <span class="timestamp">{ts}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        with st.expander("📋 Full Validation Report", expanded=not is_pass):
            st.markdown(content)


# ─────────────────────────────────────────────────────────────
#  Sidebar – Configuration
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    provider_labels = {
        "gemini": "✨ Google Gemini (Free Tier)",
        "free":   "🆓 Free Web AI (No API Key)",
        "ollama": "💻 Ollama (Local Free)",
        "openai": "🔑 OpenAI (Paid Key)",
    }
    default_provider = os.getenv("LLM_PROVIDER", "gemini" if _get_secret("GEMINI_API_KEY") else "free")
    provider_keys = list(provider_labels.keys())
    default_idx = provider_keys.index(default_provider) if default_provider in provider_keys else 0

    provider = st.selectbox(
        "LLM Provider",
        provider_keys,
        index=default_idx,
        format_func=lambda k: provider_labels[k],
    )
    os.environ["LLM_PROVIDER"] = provider

    if provider == "free":
        st.success("✅ No API key required! (Rate-limited; use Gemini Free Tier for heavy use)")
        coder_model     = st.selectbox("Coder Model",     ["openai", "qwen-coder", "mistral", "llama"], index=0)
        validator_model = st.selectbox("Validator Model", ["openai", "mistral", "llama"], index=0)
    elif provider == "ollama":
        st.info("💻 Runs locally via Ollama (`http://localhost:11434`).")
        coder_model     = st.text_input("Coder Model",     value=os.getenv("CODER_MODEL", "llama3.2"))
        validator_model = st.text_input("Validator Model", value=os.getenv("VALIDATOR_MODEL", "llama3.2"))
    elif provider == "gemini":
        api_key = st.text_input(
            "Gemini API Key",
            value=_get_secret("GEMINI_API_KEY"),
            type="password",
            help="Free key from https://aistudio.google.com/apikey",
        )
        if api_key:
            os.environ["GEMINI_API_KEY"] = api_key

        coder_model = st.selectbox(
            "Coder Model",
            ["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.1-flash-lite", "gemma-4-31b-it"],
            index=0,
        )
        validator_model = st.selectbox(
            "Validator Model",
            ["gemini-3.8-flash", "gemini-pro-latest", "gemini-flash-latest", "gemma-4-31b-it"],
            index=0,
        )
    else:
        api_key = st.text_input(
            "OpenAI API Key",
            value=_get_secret("OPENAI_API_KEY"),
            type="password",
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        coder_model     = st.selectbox("Coder Model",     ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"])
        validator_model = st.selectbox("Validator Model", ["gpt-4o", "gpt-4o-mini"])

    os.environ["CODER_MODEL"]     = coder_model
    os.environ["VALIDATOR_MODEL"] = validator_model

    max_rounds = st.slider("Max Validation Rounds", 1, 5, 2)

    st.divider()
    st.markdown("### 🔄 How It Works")
    st.caption("1️⃣ **CoderLLM** writes Python code for your task.")
    st.caption("2️⃣ **ValidatorLLM** reviews correctness, edge cases & PEP8.")
    st.caption("3️⃣ If **FAIL**, feedback loops back to CoderLLM automatically.")
    st.caption("4️⃣ You watch every message **live**!")

    st.divider()
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.result   = None
        st.rerun()


# ─────────────────────────────────────────────────────────────
#  Header & Metrics
# ─────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="hero-box">
        <div>
            <div class="main-title">🤖 CodeVerix</div>
            <div class="subtitle">Human-Observable LLM-to-LLM Coding & Validation System</div>
        </div>
        <div class="pill-badge">● {provider_labels[provider]}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

coder_count = sum(1 for m in st.session_state.messages if m.get("role") == "coder")
val_count   = sum(1 for m in st.session_state.messages if m.get("role") == "validator")
pass_count  = sum(
    1 for m in st.session_state.messages
    if m.get("role") == "validator" and "VALIDATION RESULT: PASS" in m.get("content", "").upper()
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Messages",     len(st.session_state.messages))
c2.metric("Code Generations",   coder_count)
c3.metric("Validations",        val_count)
c4.metric("Validations Passed", pass_count)


# ─────────────────────────────────────────────────────────────
#  Task Input & Quick Examples
# ─────────────────────────────────────────────────────────────
st.markdown("#### 🚀 Quick Tasks")
example_tasks = [
    ("🔢 Prime Sieve",     "Write a Python function to find all prime numbers up to N using Sieve of Eratosthenes"),
    ("📚 Stack Class",     "Write a Python class for a Stack data structure with push, pop, peek, and is_empty methods"),
    ("🔀 Merge Sorted",    "Write a Python function to merge two sorted lists into one sorted list without using sort()"),
    ("⏱️ Timer Decorator", "Write a Python decorator that measures and logs function execution time"),
    ("📄 CSV Parser",      "Write a Python function to parse a CSV string and return a list of dictionaries"),
]
qcols = st.columns(len(example_tasks))
for i, (col, (label, full_task)) in enumerate(zip(qcols, example_tasks)):
    if col.button(label, key=f"ex_{i}", use_container_width=True):
        st.session_state.task_text = full_task
        st.rerun()

task_input = st.text_area(
    "💬 Enter your coding task:",
    key="task_text",
    height=88,
    placeholder="e.g. Write a Python function that validates an email address using regex and handles edge cases...",
)

b1, b2, b3 = st.columns([2.2, 1, 1])
run_btn = b1.button("▶️ Run Live LLM-to-LLM Session", type="primary", use_container_width=True)
if st.session_state.messages:
    b2.download_button(
        "⬇️ Download JSON Log",
        data=json.dumps(st.session_state.messages, indent=2, ensure_ascii=False),
        file_name=f"codeverix_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True,
    )
else:
    b2.button("⬇️ Download JSON Log", disabled=True, use_container_width=True)

if b3.button("🔄 Reset", use_container_width=True):
    st.session_state.messages  = []
    st.session_state.result    = None
    st.session_state.task_text = ""
    st.rerun()

st.divider()


# ─────────────────────────────────────────────────────────────
#  Live Conversation Feed
# ─────────────────────────────────────────────────────────────
tab_chat, tab_code = st.tabs(["💬 Live LLM↔LLM Conversation", "✅ Final Validated Code"])

with tab_chat:
    live_feed = st.container()

    if run_btn and task_input.strip():
        provider_now = os.getenv("LLM_PROVIDER", "free").lower()
        needs_key    = provider_now in ("gemini", "openai")
        key_name     = "GEMINI_API_KEY" if provider_now == "gemini" else "OPENAI_API_KEY"

        if needs_key and not os.getenv(key_name, "").strip():
            st.error("⚠️ Please enter your API key in the sidebar (or switch to '🆓 Free Web AI' — no key needed)!")
        else:
            st.session_state.messages = []
            st.session_state.result   = None

            from orchestrator import ConversationOrchestrator

            status_box = st.empty()

            def on_new_message(msg):
                msg_dict = msg.to_dict()
                st.session_state.messages.append(msg_dict)
                with live_feed:
                    render_message(msg_dict)
                status_box.info(f"⚡ Active: **{msg.sender}**")

            orchestrator = ConversationOrchestrator(
                max_rounds=max_rounds,
                on_message=on_new_message,
            )

            try:
                result = orchestrator.run_coding_task(task_input.strip())
                st.session_state.result = result
                status_box.empty()
                st.rerun()
            except Exception as e:
                status_box.empty()
                st.error(f"❌ Error: {e}")

    elif run_btn and not task_input.strip():
        st.warning("⚠️ Please enter a coding task first!")

    with live_feed:
        if not st.session_state.messages:
            st.info(
                "👋 **Ready to watch two AIs collaborate!**\n\n"
                "Pick a quick task above or type your own, then click **▶️ Run Live LLM-to-LLM Session**.\n"
                "You'll see **CoderLLM** write the code and **ValidatorLLM** review & validate it live."
            )
        else:
            for m in st.session_state.messages:
                render_message(m)

with tab_code:
    if st.session_state.result:
        res = st.session_state.result
        s1, s2, s3 = st.columns(3)
        s1.metric("Validation Status", "✅ PASSED" if res["passed"] else "❌ FAILED")
        s2.metric("Rounds Taken",      res.get("rounds", 1))
        s3.metric("Total Messages",    len(st.session_state.messages))

        code_text = _extract_python_code(res.get("final_code", ""))
        if res["passed"]:
            st.success("🎉 Code passed validation and is ready to use!")
        else:
            st.warning("⚠️ Max rounds reached without PASS. Showing latest generated code:")

        if code_text:
            st.code(code_text, language="python")
            st.download_button(
                "📥 Download solution.py",
                data=code_text,
                file_name="solution.py",
                mime="text/x-python",
            )
        else:
            st.markdown(res.get("final_code", "No code generated yet."))
    else:
        st.info("Run a session first to see the final validated Python code here.")
