import re
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Tuple

from config import config

SELECT_ONLY = re.compile(r"^\s*select\b", re.IGNORECASE | re.DOTALL)
FORBIDDEN = re.compile(r"\b(drop|alter|insert|update|delete|truncate|create)\b", re.IGNORECASE)

def is_safe_select(sql: str) -> bool:
    return bool(SELECT_ONLY.match(sql)) and not FORBIDDEN.search(sql)

def get_conn():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )

def run_query(sql: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    if not is_safe_select(sql):
        raise ValueError("Only safe SELECT queries are allowed.")
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [desc.name for desc in cur.description]
            #Normalize certain types (e.g. Decimal to float) for JSON serialization
            def normalize_val(v):
                try:
                    from decimal import Decimal
                    if isinstance(v, Decimal):
                        return float(v)
                except Exception:
                    pass
                return v
            normalized = [{k: normalize_val(v) for k, v in row.items()} for row in rows]
            return normalized, cols

def normalize_for_compare(rows: List[Dict[str, Any]], cols: List[str], ignore_col_order: bool = False):
    #sort columns alphabetically
    if ignore_col_order:
        cols = sorted(cols)
        norm_rows = [{c: r.get(c) for c in cols} for r in rows]
    else:
        norm_rows = [{c: r.get(c) for c in cols} for r in rows]

    #sort rows deterministically (by all column values as tuple)
    try:
        sort_keys = lambda r: tuple((str(k), r[k]) for k in cols)
        norm_rows = sorted(norm_rows, key=sort_keys)
    except Exception:
        
        norm_rows = sorted(norm_rows, key=lambda r: str(r))
    return norm_rows, cols

def compare_results(
    user_rows: List[Dict[str, Any]], user_cols: List[str],
    sol_rows: List[Dict[str, Any]],  sol_cols: List[str],
    ignore_column_order: bool = True
) -> Dict[str, Any]:
    u_rows, u_cols = normalize_for_compare(user_rows, user_cols, ignore_col_order=ignore_column_order)
    s_rows, s_cols = normalize_for_compare(sol_rows,  sol_cols,  ignore_col_order=ignore_column_order)

    equal = (u_rows == s_rows) and ((u_cols == s_cols) if not ignore_column_order else True)

    #diagnostics check
    diag = {
        "equal": equal,
        "user_rowcount": len(u_rows),
        "solution_rowcount": len(s_rows),
        "user_cols": u_cols,
        "solution_cols": s_cols,
    }

    if not equal:
        #check diffs
        u_set = set(map(lambda r: tuple(r.items()), u_rows))
        s_set = set(map(lambda r: tuple(r.items()), s_rows))
        missing = s_set - u_set
        extra   = u_set - s_set
        diag["missing_rows_example"] = dict(missing.pop()) if missing else None
        diag["extra_rows_example"]   = dict(extra.pop())   if extra   else None

        if not ignore_column_order and u_cols != s_cols:
            diag["column_mismatch"] = {"user": u_cols, "solution": s_cols}

    return diag

def validate_sql_pair(user_sql: str, solution_sql: str) -> Dict[str, Any]:
    """Run both queries and compare results; returns a verdict + diagnostics."""
    sol_rows, sol_cols = run_query(solution_sql)
    user_rows, user_cols = run_query(user_sql)

    cmp_diag = compare_results(user_rows, user_cols, sol_rows, sol_cols, ignore_column_order=True)
    verdict = {
        "is_correct": cmp_diag["equal"],
        "diagnostics": cmp_diag,
        "user_preview": user_rows[:5],
        "solution_preview": sol_rows[:5],
    }
    return verdict
