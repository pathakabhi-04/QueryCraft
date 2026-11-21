"""Read-only execution of validated SQL (CLAUDE.md section 7, steps 6-7).

Defence in depth: even after validator.py has approved a query, the database
is opened read-only (mode=ro), PRAGMA query_only is on, an authorizer denies
anything except reading, and a progress handler aborts slow queries.
"""

import sqlite3
import time
from pathlib import Path

from querycraft.config import DB_PATH, get_settings
from querycraft.validator import load_schema, validate

_ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
                    getattr(sqlite3, "SQLITE_RECURSIVE", 33)}


def _authorizer(action, *_):
    return sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY


def connect_readonly(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    conn.set_authorizer(_authorizer)
    return conn


def execute(sql: str, db_path: Path = DB_PATH, timeout: float | None = None,
            row_limit: int | None = None) -> dict:
    """Validate then run `sql`. Never raises for bad SQL; returns a structured result:

    {ok, rows, columns, error, blocked_reason, block_category, sql, hallucination}
      ok=True              -> rows/columns hold the result
      blocked_reason set   -> the validator refused it (never executed)
      error set            -> it was valid but failed or timed out at run time
    """
    settings = get_settings()
    timeout = timeout if timeout is not None else settings.query_timeout_seconds
    row_limit = row_limit if row_limit is not None else settings.row_limit

    result = {"ok": False, "rows": [], "columns": [], "error": None,
              "blocked_reason": None, "block_category": None, "sql": sql, "hallucination": False}

    v = validate(sql, schema=load_schema(str(db_path)), row_limit=row_limit)
    result["hallucination"] = v.hallucination
    if not v.ok:
        result["blocked_reason"] = v.reason
        result["block_category"] = v.category
        return result
    result["sql"] = v.sql

    conn = connect_readonly(db_path)
    deadline = time.monotonic() + timeout
    # returning non-zero from the handler aborts the query with "interrupted"
    conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    try:
        cur = conn.execute(v.sql)
        result["columns"] = [d[0] for d in cur.description or []]
        result["rows"] = [tuple(r) for r in cur.fetchmany(row_limit)]
        result["ok"] = True
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e).lower():
            result["error"] = f"Query timed out after {timeout:g} seconds."
        else:
            result["error"] = f"SQLite error: {e}"
    except sqlite3.Error as e:
        result["error"] = f"SQLite error: {e}"
    finally:
        conn.close()
    return result
