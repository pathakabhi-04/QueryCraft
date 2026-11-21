"""QueryCraft web app.

    streamlit run app/streamlit_app.py

Staff type a question; the app shows a plain-English explanation, the result
table, the SQL (collapsed), assumptions, confidence and latency, or a clear
refusal. The database is opened read-only; nothing here can change data.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
import yaml  # noqa: E402

from querycraft import llm  # noqa: E402
from querycraft.config import DB_PATH, SCHEMA_DOCS_PATH, get_settings  # noqa: E402
from querycraft.pipeline import answer  # noqa: E402
from querycraft.prompt_builder import CONFIGS  # noqa: E402

DEFAULT_CONFIG = "v5+sc"
CONFIG_LABELS = {
    "v5+sc": "V5 + self-correction (recommended)",
    "v5": "V5 value hints",
    "v4": "V4 plan-first",
    "v3": "V3 few-shot",
    "v2": "V2 rules + JSON",
    "v1": "V1 baseline (Milestone 1)",
}
# Demo questions for the sidebar. Deliberately not taken from the benchmark.
EXAMPLES = [
    "How much fee is still pending from B.Tech ECE students for 2026-27?",
    "Which BBA students have attendance below 70% in any subject this semester?",
    "How many students got an F in Engineering Mathematics I?",
    "What are the mobile numbers of hostel students?",
    "Delete all fee records of 2023-24.",
]

st.set_page_config(page_title="QueryCraft", page_icon="🎓", layout="wide")


@st.cache_resource
def ensure_database() -> str:
    """Build the synthetic DB on first start (e.g. on Streamlit Cloud)."""
    if not DB_PATH.exists():
        sys.path.insert(0, str(ROOT / "data"))
        import generate_db
        generate_db.build(DB_PATH)
    return str(DB_PATH)


@st.cache_data
def schema_docs() -> dict:
    return yaml.safe_load(SCHEMA_DOCS_PATH.read_text())


def available_models() -> dict:
    """Only offer models that are configured (API key set, or local Ollama)."""
    s = get_settings()
    out = {}
    if s.gemini_api_key and s.gemini_model:
        out["gemini"] = f"Gemini · {s.gemini_model}"
    if s.llama_model and (s.llama_backend == "ollama" or s.groq_api_key):
        where = "Groq" if s.llama_backend == "groq" else "local Ollama"
        out["llama"] = f"Open model · {s.llama_model} ({where})"
    return out


ensure_database()
models = available_models()

# Optional deep link: ?q=<question>&model=<gemini|llama>&config=<v5+sc|...> runs immediately.
_qp = st.query_params
if "q" in _qp and not st.session_state.get("_qp_done"):
    st.session_state["_qp_done"] = True
    st.session_state["question"] = _qp["q"]
    st.session_state["run_now"] = True
    if _qp.get("model") in models:
        st.session_state["model"] = _qp["model"]
    if _qp.get("config") in CONFIG_LABELS:
        st.session_state["config"] = _qp["config"]

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("What's in the database")
    st.caption("Synthetic data for a demo university: 500 students, academic years 2023-24 to 2026-27.")
    for table, info in schema_docs()["tables"].items():
        with st.expander(f"**{table}**"):
            st.write(info["description"])
            st.caption(", ".join(info["columns"].keys()))
    st.header("Try an example")
    for i, ex in enumerate(EXAMPLES):
        if st.button(ex, key=f"ex{i}", use_container_width=True):
            st.session_state["question"] = ex
            st.session_state["run_now"] = True

# ---------------------------------------------------------------- main
st.title("🎓 QueryCraft")
st.write("Ask a question about students, fees, hostels, attendance or exam results "
         "in plain English. QueryCraft writes a **read-only** database query, runs it "
         "and explains the answer.")

if not models:
    st.error("No model is configured. Set GEMINI_API_KEY / GEMINI_MODEL and/or "
             "GROQ_API_KEY / LLAMA_MODEL (or LLAMA_BACKEND=ollama) in `.env` or in the "
             "app's secrets.")
    st.stop()

col_q, col_m, col_v = st.columns([6, 2, 2])
with col_q:
    question = st.text_input("Your question", key="question",
                             placeholder="e.g. How many day scholars are in BCA?")
with col_m:
    model = st.selectbox("Model", list(models), format_func=models.get, key="model")
with col_v:
    configs = [c for c in CONFIG_LABELS if c in CONFIGS]
    if "config" not in st.session_state:
        st.session_state["config"] = DEFAULT_CONFIG
    config = st.selectbox("Prompt version", configs, format_func=CONFIG_LABELS.get, key="config")

ask = st.button("Ask", type="primary")
if st.session_state.pop("run_now", False):
    ask = True

if ask and question.strip():
    with st.spinner("Thinking…"):
        rec = answer(question.strip(), config=config, model=model)

    status = rec["status"]
    if status == "UNSAFE":
        st.error("🚫 **Request refused.** QueryCraft can only *look up* information. "
                 "It will not change or delete records, or export personal data in bulk.")
        if rec["explanation"]:
            st.write(rec["explanation"])
    elif status == "CANNOT_ANSWER":
        st.warning("🤷 **This can't be answered from the database.** The data needed for "
                   "this question isn't stored here.")
        if rec["explanation"]:
            st.write(rec["explanation"])
        st.caption("See the sidebar for what the database contains.")
    elif status in ("PARSE_ERROR", "LLM_ERROR"):
        st.error("Something went wrong while getting an answer from the model. "
                 "Please try again or rephrase the question.")
        st.caption(rec.get("error") or "")
    elif status == "OK" and rec["ok"]:
        st.markdown(f"### {rec['explanation'] or 'Here is the result.'}")
        df = pd.DataFrame(rec["rows"], columns=rec["columns"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(df)} row(s)" + (" (limited to 500)" if len(df) >= 500 else ""))
    elif rec.get("block_category") == "write":
        st.error("🛡️ **Blocked by the safety layer.** The model produced a query that would "
                 "change the database. QueryCraft only runs read-only queries, so it was "
                 "**not executed** and no data was changed.")
        st.caption(f"Safety check: {rec['blocked_reason']}")
    else:
        st.error("The generated query could not be run safely, so no result is shown.")
        if rec["blocked_reason"]:
            st.caption(f"Blocked by the safety check: {rec['blocked_reason']}")
        if rec["error"]:
            st.caption(rec["error"])

    meta_cols = st.columns(4)
    meta_cols[0].metric("Confidence", (rec["confidence"] or "–").title())
    meta_cols[1].metric("Latency", f"{rec['latency']:.1f} s")
    meta_cols[2].metric("Self-correction retries", rec["retries"])
    meta_cols[3].metric("Model", rec["model_name"])

    if rec["assumptions"]:
        st.markdown("**Assumptions made**")
        for a in rec["assumptions"]:
            st.markdown(f"- {a}")
    if rec.get("plan"):
        with st.expander("How the query was planned"):
            st.write(rec["plan"])
    if rec["sql"]:
        with st.expander("Show SQL"):
            st.code(rec.get("executed_sql") or rec["sql"], language="sql")

    st.info("**Human review:** these results support decisions; they do not replace them. "
            "Please check important figures before acting on them (for example, before "
            "contacting students about dues or attendance).")
elif ask:
    st.warning("Please type a question first.")
