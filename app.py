import streamlit as st
import yaml
from pathlib import Path

from config import config
from backend.validate_sql import validate_sql_pair, is_safe_select
from backend.llm_feedback import get_feedback

def load_yaml(path: str):
    p = Path(path)
    if not p.exists():
        return {} if p.name.endswith(".yaml") else []
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

QUESTIONS = load_yaml(config.QUESTIONS_PATH) or []
SOLUTIONS = load_yaml(config.SOLUTIONS_PATH) or {}

#Normalize questions list
if isinstance(QUESTIONS, dict) and "questions" in QUESTIONS:
    QUESTIONS = QUESTIONS["questions"]

st.set_page_config(page_title="SQL Playground", layout="wide")
st.title("🧪 SQL Playground (Postgres + Local LLM)")

if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "last_feedback" not in st.session_state:
    st.session_state.last_feedback = ""

def get_current_q():
    if not QUESTIONS:
        return None
    idx = max(0, min(st.session_state.q_index, len(QUESTIONS)-1))
    return QUESTIONS[idx]

with st.sidebar:
    st.subheader("Question Navigation")
    if st.button("⏮ Prev", use_container_width=True):
        st.session_state.q_index = max(0, st.session_state.q_index - 1)
        st.session_state.last_feedback = ""
    if st.button("⏭ Next", use_container_width=True):
        st.session_state.q_index = min(len(QUESTIONS)-1, st.session_state.q_index + 1)
        st.session_state.last_feedback = ""

q = get_current_q()
if not q:
    st.warning("No questions found. Add some to your questions YAML.")
    st.stop()

qid = str(q["id"])
solution_entry = SOLUTIONS.get(qid, {})
solution_sql = solution_entry.get("solution_sql", "").strip()
explanation = solution_entry.get("explanation", "").strip()

left, right = st.columns([1, 1])

with left:
    st.markdown(f"### Question #{qid}")
    st.write(q["question"])

    with st.expander("Show stored explanation (for review)"):
        st.write(explanation if explanation else "_No explanation stored yet._")

with right:
    st.markdown("### Your SQL")
    default_sql = "SELECT * FROM employees LIMIT 5;"
    user_sql = st.text_area("Write a SELECT query (PostgreSQL):", height=240, value=default_sql, label_visibility="collapsed")

    run = st.button("▶️ Run & Validate")
    if run:
        st.session_state.last_feedback = ""
        if not is_safe_select(user_sql):
            st.error("Only safe SELECT queries are allowed. (No DDL/DML keywords.)")
        elif not solution_sql:
            st.warning("No stored solution for this question yet. Generate it first.")
        else:
            try:
                verdict = validate_sql_pair(user_sql, solution_sql)
                if verdict["is_correct"]:
                    st.success("Correct! Your result matches the official solution.")
                else:
                    st.error("Not quite. Your result differs from the official solution.")
                    diag = verdict["diagnostics"]
                    with st.expander("Diagnostics (technical)"):
                        st.json(diag)
                    #ask LLM for human feedback
                    fb = get_feedback(q["question"], user_sql, solution_sql, explanation, diag)
                    st.session_state.last_feedback = fb
            except Exception as e:
                st.error(f"Execution error: {e}")

    if st.session_state.last_feedback:
        st.markdown("### Mentor Feedback")
        st.info(st.session_state.last_feedback)

    with st.expander("Peek: Official solution SQL"):
        st.code(solution_sql or "-- No solution stored", language="sql")
