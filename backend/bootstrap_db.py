from typing import Sequence

from backend.validate_sql import get_conn


def _ensure_table(cur, name: str, create_sql: str, seed_sql: str | None = None, seed_params: Sequence[Sequence] | None = None) -> None:
    cur.execute("SELECT to_regclass(%s)", (f"public.{name}",))
    exists = cur.fetchone()[0] is not None
    if not exists:
        cur.execute(create_sql)
    if seed_sql and seed_params:
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        rowcount = cur.fetchone()[0]
        if rowcount == 0:
            cur.executemany(seed_sql, seed_params)


def bootstrap_database() -> None:
    departments_seed = [
        ("Engineering",),
        ("HR",),
        ("Marketing",),
        ("Finance",),
    ]

    employees_seed = [
        ("Alice", 1, 125000, "2017-03-12"),
        ("Bob", 2, 80000, "2018-07-10"),
        ("Charlie", 1, 135000, "2019-01-15"),
        ("Diana", 3, 95000, "2020-09-20"),
        ("Edward", 4, 115000, "2016-12-02"),
        ("Fay", 1, 110000, "2022-11-05"),
    ]

    projects_seed = [
        ("People Analytics Platform", 1, "2021-02-01", 250000),
        ("Benefits Revamp", 2, "2020-05-15", 120000),
        ("Ad Campaign Q4", 3, "2022-09-01", 175000),
        ("ERP Migration", 4, "2019-11-20", 320000),
    ]

    departments_create = (
        "CREATE TABLE IF NOT EXISTS departments ("
        " id SERIAL PRIMARY KEY,"
        " name VARCHAR(50) NOT NULL"
        ")"
    )

    employees_create = (
        "CREATE TABLE IF NOT EXISTS employees ("
        " id SERIAL PRIMARY KEY,"
        " name VARCHAR(100) NOT NULL,"
        " department_id INTEGER REFERENCES departments(id),"
        " salary NUMERIC(10,2) NOT NULL,"
        " hire_date DATE NOT NULL"
        ")"
    )

    projects_create = (
        "CREATE TABLE IF NOT EXISTS projects ("
        " id SERIAL PRIMARY KEY,"
        " name VARCHAR(100) NOT NULL,"
        " department_id INTEGER REFERENCES departments(id),"
        " start_date DATE NOT NULL,"
        " budget NUMERIC(12,2) NOT NULL"
        ")"
    )

    with get_conn() as conn:
        with conn.cursor() as cur:
            _ensure_table(cur, "departments", departments_create, "INSERT INTO departments (name) VALUES (%s)", departments_seed)
            _ensure_table(cur, "employees", employees_create, "INSERT INTO employees (name, department_id, salary, hire_date) VALUES (%s, %s, %s, %s)", employees_seed)
            _ensure_table(cur, "projects", projects_create, "INSERT INTO projects (name, department_id, start_date, budget) VALUES (%s, %s, %s, %s)", projects_seed)

