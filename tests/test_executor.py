import sqlite3

import pytest

from querycraft.config import DB_PATH
from querycraft.executor import connect_readonly, execute


def test_simple_count():
    r = execute("SELECT COUNT(*) FROM students")
    assert r["ok"] and r["rows"] == [(500,)]
    assert r["columns"] == ["COUNT(*)"]
    assert r["error"] is None and r["blocked_reason"] is None


def test_result_shape_keys():
    r = execute("SELECT 1")
    assert {"ok", "rows", "columns", "error", "blocked_reason"} <= r.keys()


def test_row_limit_applied():
    r = execute("SELECT * FROM enrollments")
    assert r["ok"] and len(r["rows"]) == 500


def test_write_is_blocked_not_executed():
    before = execute("SELECT COUNT(*) FROM fees")["rows"]
    r = execute("DELETE FROM fees")
    assert not r["ok"] and r["blocked_reason"]
    assert execute("SELECT COUNT(*) FROM fees")["rows"] == before


def test_hallucinated_table_reported():
    r = execute("SELECT * FROM placements")
    assert not r["ok"] and r["hallucination"]


def test_runtime_error_is_reported():
    # passes the validator, fails in SQLite (no such function)
    r = execute("SELECT made_up_fn(name) FROM students")
    assert not r["ok"] and r["error"] and r["blocked_reason"] is None


def test_timeout():
    slow = ("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) "
            "SELECT COUNT(*) FROM (SELECT x FROM c LIMIT 100000000)")
    r = execute(slow, timeout=0.5)
    assert not r["ok"]
    assert "timed out" in r["error"]


def test_connection_is_read_only_even_without_validator():
    conn = connect_readonly(DB_PATH)
    with pytest.raises(sqlite3.Error):
        conn.execute("DELETE FROM fees")
    with pytest.raises(sqlite3.Error):
        conn.execute("CREATE TABLE t (x INT)")
    conn.close()
