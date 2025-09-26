import json
import re
import sys
from pathlib import Path

import requests
import yaml

try:
    from config import config
    LLM_API_BASE = config.LLM_API_BASE
    LLM_API_KEY = config.LLM_API_KEY
    LLM_MODEL = config.LLM_MODEL
    QUESTIONS_PATH = Path(config.QUESTIONS_PATH)
    SOLUTIONS_PATH = Path(config.SOLUTIONS_PATH)
except Exception:
    # Fallbacks if config.py isn’t wired yet
    LLM_API_BASE = "http://localhost:11434/v1"
    LLM_API_KEY = "ollama"
    LLM_MODEL = "gemma2:9b"
    QUESTIONS_PATH = Path("questions/questions.yaml")
    SOLUTIONS_PATH = Path("solutions/solutions.yaml")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {LLM_API_KEY}",
}

SYSTEM_PROMPT = (
    "You are a senior SQL mentor. You write *only* SELECT queries compatible with PostgreSQL 16. "
    "Given a natural-language SQL practice question and the available schema, produce: "
    "1) a correct, minimal SELECT SQL solution; 2) a clear, concise human explanation."
)

SCHEMA_HINT = """\
Tables:
- departments(id SERIAL PRIMARY KEY, name VARCHAR(50) NOT NULL)
- employees(id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL,
            department_id INTEGER REFERENCES departments(id),
            salary NUMERIC(10,2) NOT NULL, hire_date DATE NOT NULL)
"""

USER_TEMPLATE = """\
Question:
{question}

Schema:
{schema}

Return a strict JSON object with keys:
- "solution_sql": string (a single valid PostgreSQL SELECT; no DDL/DML; no comments)
- "explanation": string (1-3 sentences)

Example:
{{
  "solution_sql": "SELECT * FROM employees WHERE salary > 100000;",
  "explanation": "Filters employees with salary above 100,000."
}}
"""

SELECT_ONLY = re.compile(r"^\s*select\b", re.IGNORECASE | re.DOTALL)
FORBIDDEN = re.compile(r"\b(drop|alter|insert|update|delete|truncate|create)\b", re.IGNORECASE)

def is_safe_select(sql: str) -> bool:
    return bool(SELECT_ONLY.match(sql)) and not FORBIDDEN.search(sql)

def load_yaml(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8-sig") as f:
        return yaml.safe_load(f)

def save_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.yaml")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    tmp.replace(path)

def normalize_questions(raw):
    """
    Accepts:
      - list of {id, question}
      - dict of id -> {question}
      - dict with root key 'questions' containing either of the above
    Returns: list[{'id': int, 'question': str}]
    """
    if raw is None:
        return []

    #root key 
    if isinstance(raw, dict) and "questions" in raw:
        raw = raw["questions"]

    #list of dicts
    if isinstance(raw, list):
        out = []
        for i, item in enumerate(raw, 1):
            if not isinstance(item, dict):
                raise ValueError(f"Item #{i} is not a dict: {item!r}")
            if "id" not in item or "question" not in item:
                raise ValueError(f"Item #{i} missing 'id' or 'question': {item!r}")
            out.append({"id": int(item["id"]), "question": str(item["question"]).strip()})
        return out

    #dict keyed by id
    if isinstance(raw, dict):
        out = []
        for k, v in raw.items():
            if not isinstance(v, dict) or "question" not in v:
                raise ValueError(f"Key {k!r} must map to a dict with 'question'. Got: {v!r}")
            out.append({"id": int(k), "question": str(v["question"]).strip()})
        #maintain numeric order
        out.sort(key=lambda x: x["id"])
        return out

    raise ValueError(f"Unsupported YAML structure for questions: {type(raw)}")

def normalize_solutions(raw):
    """
    Ensures solutions is a dict[str(id)] -> {solution_sql, explanation}
    YAML may load numeric keys as int; convert to str.
    """
    if not raw:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("solutions.yaml must be a mapping of id -> {solution_sql, explanation}")
    out = {}
    for k, v in raw.items():
        key = str(k)
        if not isinstance(v, dict):
            raise ValueError(f"Solution for id {k} must be an object, got: {type(v)}")
        out[key] = v
    return out

def call_llm(question: str) -> dict:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(question=question, schema=SCHEMA_HINT)},
        ],
        "temperature": 0.2,
        "stream": False,
    }
    resp = requests.post(f"{LLM_API_BASE}/chat/completions", headers=HEADERS, data=json.dumps(payload), timeout=120)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"].strip()

    #find JSON in the content
    try:
        json_str = content
        if "```" in content:
            import re as _re
            parts = _re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=_re.DOTALL)
            if parts:
                json_str = parts[0]
        parsed = json.loads(json_str)
        return parsed
    except Exception as e:
        raise ValueError(f"Failed to parse JSON from model output:\n{content}\nError: {e}") from e

def main():
    raw_questions = load_yaml(QUESTIONS_PATH)
    raw_solutions = load_yaml(SOLUTIONS_PATH)

    try:
        questions = normalize_questions(raw_questions)
    except Exception as e:
        #debugging output
        print("DEBUG: Parsed questions.yaml as:", type(raw_questions).__name__)
        print("DEBUG: First 200 chars of raw YAML object repr:\n", repr(raw_questions)[:200])
        print("ERROR: questions.yaml must be a list of {id, question} (or a dict keyed by id, or wrapped under 'questions').", file=sys.stderr)
        raise

    try:
        solutions = normalize_solutions(raw_solutions)
    except Exception:
        solutions = {}

    missing = [q for q in questions if str(q["id"]) not in solutions]
    if not missing:
        print("No missing entries. solutions.yaml already covers all questions.")
        return

    print(f"Found {len(missing)} question(s) without solutions. Generating...\n")

    updated = False
    for q in missing:
        qid = str(q["id"])
        qtext = q["question"].strip()
        print(f"- Generating solution for QID {qid}: {qtext[:80]}...")

        try:
            result = call_llm(qtext)
            sol = (result.get("solution_sql") or "").strip().rstrip(";") + ";"
            exp = (result.get("explanation") or "").strip()

            if not sol:
                raise ValueError("Model returned empty solution_sql.")
            if not is_safe_select(sol):
                raise ValueError("Generated SQL is not a safe SELECT or contains forbidden keywords.")

            solutions[qid] = {
                "solution_sql": sol,
                "explanation": exp,
            }
            updated = True
            print(f"Saved.")

        except Exception as e:
            print(f"Skipped QID {qid}: {e}")

    if updated:
        save_yaml(SOLUTIONS_PATH, solutions)
        print(f"\nUpdated {SOLUTIONS_PATH} successfully.")
    else:
        print("\nNo updates written (all generations failed or were unsafe).")

if __name__ == "__main__":
    main()
