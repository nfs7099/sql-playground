# SQL Playground

Practice SQL against a local Postgres database and get instant feedback from a Streamlit UI plus a lightweight LLM mentor.

## Features
- Streamlit frontend with question navigation and schema browser
- Dockerised Postgres 16 with seeded `departments`, `employees`, and `projects` tables
- Automated answer checking that compares results against official solutions
- Cached schema viewer and optional LLM feedback for incorrect submissions

## Requirements
- Python 3.11+
- Docker Desktop (or any Docker engine capable of running the Postgres service)

## Quick Start
1. Clone the repo and enter the folder:
   ```powershell
   git clone https://github.com/nfs7099/sql-playground.git
   cd sql-playground
   ```
2. Create a virtual environment and install dependencies:
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate
   pip install -r requirements.txt
   ```
3. Copy environment settings and adjust if needed:
   ```powershell
   copy .env.example .env
   ```
   The defaults point Streamlit at localhost Postgres and a local OpenAI-compatible LLM endpoint.
4. Start Postgres:
   ```powershell
   docker compose up -d db
   ```
5. Launch the app:
   ```powershell
   streamlit run app.py
   ```
   Streamlit bootstraps the database automatically on first run and serves the app at `http://localhost:8501`.

## Managing Questions & Solutions
- Questions live in `questions/questions.yaml`.
- Official answers and explanations live in `solutions/solutions.yaml`.
- Use string IDs (e.g. `"1"`, `"2"`) that match between the two files.
- Adding a new question without a stored solution prompts the UI to remind you to generate one before validation.

## Database Schema
Tables are created and seeded on startup if missing. The default data works with the stock questions.
- `departments(id, name)`
- `employees(id, name, department_id, salary, hire_date)`
- `projects(id, name, department_id, start_date, budget)`

If you change the schema, update `backend/bootstrap_db.py` and the YAML questions/solutions accordingly.

## LLM Feedback
`backend/llm_feedback.py` calls an OpenAI-compatible endpoint. Configure the following in `.env`:
- `LLM_API_BASE`
- `LLM_API_KEY`
- `LLM_MODEL`

Leaving the endpoint unreachable disables mentor feedback, but the rest of the app still works.

## Troubleshooting
- **Schema panel empty**: ensure Postgres is running and the app can connect. Check credentials in `.env`.
- **Docker daemon error**: start Docker Desktop so `docker compose` can reach the daemon.
- **Diagnostics JSON errors**: ensure you are on the latest code and dependencies (`pip install -r requirements.txt`).
- **Reset database**: run `docker compose down -v` to drop volumes, then `docker compose up -d` to recreate with fresh seed data.

## Testing
Run the test suite with:
```powershell
pytest
```

## License
MIT (see `LICENSE`).
