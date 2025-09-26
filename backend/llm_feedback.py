import json
import requests
from typing import Dict, Any

from config import config

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.LLM_API_KEY}",
}

FEEDBACK_SYSTEM = (
    "You are a senior SQL mentor. Be concise, specific, and actionable. "
    "Given a SQL practice question, the official solution SQL, the stored explanation, and diagnostics "
    "from comparing the user's result to the solution's result, explain: "
    "1) what's wrong in the user's approach; 2) a hint to fix it (but do not reveal the full solution)."
)

FEEDBACK_TEMPLATE = """\
Question:
{question}

User SQL:
{user_sql}

Official Solution SQL:
{solution_sql}

Stored Explanation:
{explanation}

Diagnostics:
{diagnostics}

Write a short feedback (max ~120 words): what went wrong and one or two hints.
Do NOT reveal the entire solution SQL.
"""

def get_feedback(question: str, user_sql: str, solution_sql: str, explanation: str, diagnostics: Dict[str, Any]) -> str:
    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": FEEDBACK_SYSTEM},
            {"role": "user", "content": FEEDBACK_TEMPLATE.format(
                question=question,
                user_sql=user_sql,
                solution_sql=solution_sql,
                explanation=explanation,
                diagnostics=json.dumps(diagnostics, ensure_ascii=False, indent=2),
            )},
        ],
        "temperature": 0.2,
        "stream": False,
    }
    resp = requests.post(f"{config.LLM_API_BASE}/chat/completions", headers=HEADERS, data=json.dumps(payload), timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()
