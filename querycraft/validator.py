"""Read-only SQL enforcement (CLAUDE.md section 7, steps 1-5).

The model's SQL is never trusted. Before anything touches the database we:
  1. parse it with sqlglot (SQLite dialect)    -> reject if it does not parse
  2. require exactly one statement
  3. require a SELECT (or WITH ... SELECT / UNION of SELECTs) at the top, and
     reject any write/DDL/PRAGMA/ATTACH node anywhere in the tree
  4. check every table (and, where we can, every column) exists
  5. add LIMIT <row_limit> if the query has no LIMIT
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from querycraft.config import DB_PATH, get_settings

# sqlglot logs a warning when it falls back to a generic Command; we handle that ourselves.
logging.getLogger("sqlglot").setLevel(logging.ERROR)

ALLOWED_TOP_LEVEL = (exp.Select, exp.SetOperation)     # SetOperation = UNION / INTERSECT / EXCEPT

# Node types that must not appear anywhere in the tree.
_FORBIDDEN_NAMES = [
    "Insert", "Update", "Delete", "Drop", "Alter", "AlterTable", "Create", "Merge",
    "Attach", "Detach", "Pragma", "Command", "Transaction", "Commit", "Rollback",
    "Set", "Analyze", "Copy", "Use", "Kill", "Load", "TruncateTable",
]
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NAMES if hasattr(exp, n))

# SQLite functions that touch the file system or load code.
FORBIDDEN_FUNCTIONS = {"load_extension", "readfile", "writefile", "edit", "fts3_tokenizer"}


@dataclass
class ValidationResult:
    ok: bool
    sql: str = ""                       # rewritten SQL (with LIMIT) when ok
    reason: str = ""                    # why it was blocked
    tables: list = field(default_factory=list)
    unknown_tables: list = field(default_factory=list)
    unknown_columns: list = field(default_factory=list)

    @property
    def hallucination(self) -> bool:
        """True if the SQL referenced a table or column that does not exist."""
        return bool(self.unknown_tables or self.unknown_columns)


@lru_cache(maxsize=4)
def load_schema(db_path: str = str(DB_PATH)) -> dict:
    """{table_name: set(column_names)} read from the database itself (lower-case)."""
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {t.lower(): {r[1].lower() for r in conn.execute(f'PRAGMA table_info("{t}")')}
                for t in tables}
    finally:
        conn.close()


def _blocked(reason: str, **kw) -> ValidationResult:
    return ValidationResult(ok=False, reason=reason, **kw)


def validate(sql: str, schema: dict | None = None, row_limit: int | None = None) -> ValidationResult:
    schema = schema if schema is not None else load_schema()
    row_limit = row_limit if row_limit is not None else get_settings().row_limit

    if not sql or not sql.strip():
        return _blocked("Empty SQL.")

    # 1. parse
    try:
        statements = [s for s in sqlglot.parse(sql, read="sqlite") if s is not None]
    except ParseError as e:
        return _blocked(f"SQL does not parse: {str(e).splitlines()[0]}")

    # 2. exactly one statement
    if len(statements) != 1:
        return _blocked(f"Expected exactly one SQL statement, found {len(statements)}.")
    tree = statements[0]

    # 3. read-only
    if not isinstance(tree, ALLOWED_TOP_LEVEL):
        return _blocked(f"Only SELECT queries are allowed (got {tree.key.upper()}).")
    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            return _blocked(f"Forbidden operation inside query: {node.key.upper()}.")
        if isinstance(node, exp.Func):
            name = (node.name if isinstance(node, exp.Anonymous) else node.sql_name()).lower()
            if name in FORBIDDEN_FUNCTIONS:
                return _blocked(f"Forbidden function: {name}.")

    # 4. tables and columns must exist
    cte_names = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
    alias_to_table, tables, unknown_tables = {}, [], []
    for t in tree.find_all(exp.Table):
        name = t.name.lower()
        if name in cte_names:
            continue
        if name not in schema:
            unknown_tables.append(t.name)
            continue
        tables.append(name)
        alias_to_table[t.alias_or_name.lower()] = name
        alias_to_table[name] = name
    if unknown_tables:
        return _blocked(f"Unknown table(s): {', '.join(sorted(set(unknown_tables)))}.",
                        unknown_tables=sorted(set(unknown_tables)))

    unknown_columns = _unknown_columns(tree, schema, alias_to_table, cte_names, set(tables))
    if unknown_columns:
        return _blocked(f"Unknown column(s): {', '.join(unknown_columns)}.",
                        tables=sorted(set(tables)), unknown_columns=unknown_columns)

    # 5. LIMIT
    if not tree.args.get("limit"):
        tree = tree.limit(row_limit)

    return ValidationResult(ok=True, sql=tree.sql(dialect="sqlite"), tables=sorted(set(tables)))


def _unknown_columns(tree, schema, alias_to_table, cte_names, tables) -> list:
    """Best-effort column check.

    Columns qualified with a real table/alias must exist in that table.
    Unqualified columns (or ones qualified with a CTE / subquery alias) must
    exist in *some* referenced table or be an alias defined in the query.
    """
    known_cols = set().union(*(schema[t] for t in tables)) if tables else set()
    # names the query itself defines: SELECT aliases, CTE / derived-table column lists
    defined = {a.alias.lower() for a in tree.find_all(exp.Alias)}
    for ta in tree.find_all(exp.TableAlias):
        defined |= {c.name.lower() for c in ta.columns}
    derived_aliases = {sq.alias.lower() for sq in tree.find_all(exp.Subquery) if sq.alias}

    bad = []
    for col in tree.find_all(exp.Column):
        if isinstance(col.this, exp.Star):
            continue
        name, qual = col.name.lower(), col.table.lower()
        if qual and qual in alias_to_table:
            ok = name in schema[alias_to_table[qual]]
        elif qual and qual not in cte_names and qual not in derived_aliases:
            ok = False                                   # unknown table alias
        else:
            ok = name in known_cols or name in defined
        if not ok:
            label = f"{col.table}.{col.name}" if qual else col.name
            if col.this.args.get("quoted") and not qual:
                label += " (use single quotes for text values)"
            bad.append(label)
    return sorted(set(bad))
