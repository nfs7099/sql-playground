import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from backend.validate_sql import is_safe_select

@pytest.mark.parametrize("sql,ok", [
    ("SELECT 1;", True),
    (" select * from employees ;", True),
    ("DELETE FROM employees;", False),
    ("DROP TABLE employees;", False),
])
def test_is_safe_select(sql, ok):
    assert is_safe_select(sql) == ok
