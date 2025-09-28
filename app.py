import streamlit as st
import yaml
from pathlib import Path

from config import config
from backend.validate_sql import validate_sql_pair, is_safe_select, get_conn
from backend.llm_feedback import get_feedback
from backend.bootstrap_db import bootstrap_database


APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR

def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute() and path.exists():
        return path
    candidate = ROOT_DIR / path
    if candidate.exists():
        return candidate
    return Path.cwd() / path

def load_yaml(path_str: str):
    resolved = _resolve(path_str)
    if not resolved.exists():
        return {} if resolved.suffix in {".yml", ".yaml"} else []
    with resolved.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


QUESTIONS_RAW = load_yaml(config.QUESTIONS_PATH) or []
SOLUTIONS_RAW = load_yaml(config.SOLUTIONS_PATH) or {}

st.caption(f"Loaded questions from: {_resolve(config.QUESTIONS_PATH)}")

if isinstance(QUESTIONS_RAW, dict):
    QUESTIONS = QUESTIONS_RAW.get("questions", [])
else:
    QUESTIONS = QUESTIONS_RAW or []
if not isinstance(QUESTIONS, list):
    QUESTIONS = []

if isinstance(SOLUTIONS_RAW, dict):
    SOLUTIONS = {str(key): value for key, value in SOLUTIONS_RAW.items()}
else:
    SOLUTIONS = {}

SCHEMA_TABLES = ("departments", "employees", "projects")


@st.cache_resource(show_spinner=False)
def ensure_bootstrap():
    bootstrap_database()
    return True


@st.cache_data(show_spinner=False)
def load_table_schema(table_names):
    ensure_bootstrap()
    table_list = list(table_names)
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = ANY(%s)
                    ORDER BY table_name, ordinal_position
                """, (table_list,))
                rows = cur.fetchall()
    except Exception as exc:
        return {"_error": str(exc)}
    schema = {}
    for table_name, column_name, data_type in rows:
        schema.setdefault(table_name, []).append((column_name, data_type))
    return schema

st.set_page_config(page_title="SQL Playground", layout="wide")
st.title("SQL Playground (Postgres + Local LLM)")

if "q_index" not in st.session_state:
    st.session_state.q_index = 0
if "last_feedback" not in st.session_state:
    st.session_state.last_feedback = ""

def get_current_q():
    if not QUESTIONS:
        return None
    index = max(0, min(st.session_state.q_index, len(QUESTIONS) - 1))
    return QUESTIONS[index]

with st.sidebar:
    st.subheader("Question Navigation")
    if st.button("Prev", use_container_width=True):
        st.session_state.q_index = max(0, st.session_state.q_index - 1)
        st.session_state.last_feedback = ""
    if st.button("Next", use_container_width=True):
        st.session_state.q_index = min(len(QUESTIONS) - 1, st.session_state.q_index + 1)
        st.session_state.last_feedback = ""

    schema_info = load_table_schema(SCHEMA_TABLES)
    st.markdown("### Table Schema")
    if "_error" in schema_info:
        st.warning(f"Unable to load schema: {schema_info['_error']}")
    else:
        for table_name in SCHEMA_TABLES:
            columns = schema_info.get(table_name, [])
            display_name = table_name.replace('_', ' ').title()
            st.markdown(f"**{display_name}**")
            if not columns:
                st.caption("No columns found.")
            else:
                for column_name, data_type in columns:
                    st.caption(f"{column_name} ({data_type})")
    st.divider()

current_q = get_current_q()
if not current_q:
    st.warning("No questions found. Add some to your questions YAML.")
    st.stop()

question_id = str(current_q["id"])
solution_entry = SOLUTIONS.get(question_id, {})
solution_sql = solution_entry.get("solution_sql", "").strip()
explanation = solution_entry.get("explanation", "").strip()

left_col, right_col = st.columns([1, 1])

with left_col:
    st.markdown(f"### Question #{question_id}")
    st.write(current_q["question"])
    with st.expander("Show stored explanation (for review)"):
        st.write(explanation if explanation else "_No explanation stored yet._")

with right_col:
    st.markdown("### Your SQL")
    default_sql = "SELECT * FROM employees LIMIT 5;"
    user_sql = st.text_area("Write a SELECT query (PostgreSQL):",
                             value=default_sql,
                             height=240,
                             label_visibility="collapsed")

    run_clicked = st.button("Run & Validate")
    if run_clicked:
        st.session_state.last_feedback = ""
        if not user_sql.strip():
            st.warning("Enter a SQL query before running.")
        elif not is_safe_select(user_sql):
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
                    diagnostics = verdict["diagnostics"]
                    with st.expander("Diagnostics (technical)"):
                        st.json(diagnostics)
                    feedback = get_feedback(current_q["question"], user_sql, solution_sql, explanation, diagnostics)
                    st.session_state.last_feedback = feedback
            except Exception as exc:
                st.error(f"Execution error: {exc}")

    if st.session_state.last_feedback:
        st.markdown("### Mentor Feedback")
        st.info(st.session_state.last_feedback)

    with st.expander("Peek: Official solution SQL"):
        st.code(solution_sql or "-- No solution stored", language="sql")


