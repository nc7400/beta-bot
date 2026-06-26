"""
Streamlit web UI for Beta-Bot (Mountain Project Q&A).

FIX: Streamlit re-imports modules from cache between runs, which meant the
updated ingest.py filtering logic wasn't being picked up. This version:
  - Uses importlib.reload() to force fresh module load on every data reload
  - Passes the processor instance (not a cached context string) so
    get_context_for_llm() is always called fresh per question with the
    correct filtering logic
  - Strips context to absolute minimum for grade/route/area queries

Model waterfall:
  1. llama-3.3-70b-versatile  — best quality
  2. llama-3.1-8b-instant     — fallback if rate limited

Get a free Groq key at https://console.groq.com
"""

import importlib
import sys
import streamlit as st
from pathlib import Path
from datetime import datetime

from groq import Groq


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Beta-Bot | Climbing Q&A",
    page_icon="🧗",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY_MODEL  = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in {
    "initialized": False,
    "client":      None,
    "processor":   None,
    "messages":    [],
    "data":        {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helpers ────────────────────────────────────────────────────────────────────

def force_reload_modules():
    """
    Force Python to re-import fetch and ingest from disk.
    Streamlit keeps old module objects in sys.modules between hot-reloads,
    so without this the app silently runs stale code.
    """
    for mod_name in ('fetch', 'ingest'):
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])


def load_and_process_data(data_path: str):
    force_reload_modules()
    from fetch import load_climbing_data
    from ingest import ClimbingDataProcessor
    try:
        raw_data  = load_climbing_data(data_path)
        processor = ClimbingDataProcessor(raw_data)
        result    = processor.process()
        return result, processor
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return None, None


def init_client(api_key: str):
    try:
        client = Groq(api_key=api_key)
        client.chat.completions.create(
            model=FALLBACK_MODEL,
            max_tokens=4,
            messages=[{"role": "user", "content": "hi"}],
        )
        return client
    except Exception as e:
        st.error(f"❌ Could not connect to Groq: {e}")
        return None


def build_system_prompt(context: str) -> str:
    return f"""You are Beta-Bot, a climbing-history assistant. Answer using ONLY the data below.

RULES:
1. Never invent route names, grades, dates, areas, or styles.
2. Copy route names and grades EXACTLY as written in RAW CLIMB RECORDS.
3. COUNT = simply count the records in RAW CLIMB RECORDS that match. Do not verify or cross-check.
4. LIST = copy the matching records verbatim. Do not re-examine or second-guess them.
5. Answer directly. Never loop, revise mid-answer, or say "however" about your own output.
6. If the answer is absent: "I do not have that information in the data provided."
7. difficulty_code is discipline-specific only. Never compare Sport/Trad codes to Boulder codes.

DATA:
{context}"""


def ask_groq(client, system: str, history: list, question: str) -> tuple[str, str]:
    messages = (
        [{"role": "system", "content": system}]
        + history
        + [{"role": "user", "content": question}]
    )
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=1024,
                temperature=0,
                messages=messages,
            )
            return response.choices[0].message.content, model
        except Exception as e:
            err = str(e)
            if "413" in err or "rate_limit" in err or "tokens" in err.lower():
                continue
            return f"❌ Error: {e}", model
    return (
        "❌ Both models hit token limits. Try a more specific question "
        "(include a grade, route name, or area).",
        "none",
    )


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Configuration")

    api_key = st.text_input(
        "🔑 Groq API Key",
        type="password",
        help="Free at https://console.groq.com — no credit card needed",
        placeholder="gsk_...",
    )

    st.divider()

    data_file = st.file_uploader(
        "📁 Upload climbing data (CSV or JSON)",
        type=["csv", "json"],
    )

    if data_file is not None:
        upload_dir = Path(__file__).resolve().parent / "data" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name   = Path(data_file.name).name
        upload_path = upload_dir / safe_name
        if upload_path.exists():
            upload_path = upload_dir / (
                f"{Path(safe_name).stem}_{int(datetime.now().timestamp())}"
                f"{Path(safe_name).suffix}"
            )
        with open(upload_path, "wb") as f:
            f.write(data_file.getbuffer())

        if st.button("🔄 Load & Process Data"):
            with st.spinner("Processing data..."):
                result, processor = load_and_process_data(str(upload_path))
                if result:
                    st.session_state.processor = processor
                    st.session_state.data      = result
                    st.session_state.messages  = []
                    st.success(f"✅ Loaded {result['processed_count']} climbs!")

    st.divider()

    if st.button("🚀 Initialize Bot", key="init_button"):
        if not api_key:
            st.error("⚠️ Please enter your Groq API key")
        elif not st.session_state.processor:
            st.error("⚠️ Please load your climbing data first")
        else:
            with st.spinner("Connecting to Groq..."):
                client = init_client(api_key)
                if client:
                    st.session_state.client      = client
                    st.session_state.initialized = True
                    st.success("✅ Beta-Bot ready!")

    if st.session_state.initialized:
        if st.button("🗑️ Clear chat history"):
            st.session_state.messages = []
            st.rerun()

    st.divider()
    st.markdown("""
### 📖 Setup
1. Free Groq key → [console.groq.com](https://console.groq.com)
2. Upload your **Mountain Project CSV**
3. **Load & Process Data**
4. **Initialize Bot**

### 💡 Example questions
- List all my 5.12d climbs
- How many onsights at Muir Valley?
- What's my hardest redpoint?
- How many climbs in 2025?
- Which area have I visited the most?
""")


# ── Main UI ────────────────────────────────────────────────────────────────────
st.title("🧗 Beta-Bot | Mountain Project Q&A")
st.caption(f"Powered by Groq ({PRIMARY_MODEL}) — answers grounded strictly in your climbing data")

if st.session_state.data and "statistics" in st.session_state.data:
    stats = st.session_state.data["statistics"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Climbs",    stats.get("total_climbs", 0))
    c2.metric("Unique Routes",   stats.get("unique_routes", 0))
    c3.metric("Areas Visited",   stats.get("unique_areas", 0))
    c4.metric("Avg Your Rating", f"{stats.get('average_rating', 0):.1f}")
    c5.metric("Redpoints",       len(stats.get("redpoints", [])))
    st.divider()

st.subheader("💬 Ask About Your Climbs")

if not st.session_state.initialized:
    st.info("👈 Complete setup in the sidebar to get started.")
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask me about your climbing history..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Looking up your data..."):
                # Always call get_context_for_llm fresh with the current question
                # so the correct filtering logic runs every time
                context = st.session_state.processor.get_context_for_llm(
                    question=user_input
                )
                system  = build_system_prompt(context)
                history = st.session_state.messages[:-1]

                reply, model_used = ask_groq(
                    st.session_state.client,
                    system,
                    history,
                    user_input,
                )
                st.markdown(reply)
                if model_used not in ("none", PRIMARY_MODEL):
                    st.caption(f"⚡ Answered by fallback model ({model_used})")

                st.session_state.messages.append(
                    {"role": "assistant", "content": reply}
                )

st.divider()
st.caption("Beta-Bot only answers from your uploaded data.")