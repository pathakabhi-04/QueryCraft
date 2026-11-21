import pytest

from querycraft.validator import validate


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM students",
    "SELECT s.name FROM students s JOIN programs p ON s.program_id = p.program_id "
    "WHERE p.program_name = 'B.Tech CSE'",
    "WITH d AS (SELECT student_id, amount_due - amount_paid AS dues FROM fees) "
    "SELECT student_id FROM d WHERE dues > 0",
    "SELECT name FROM students WHERE hostel_id IS NULL UNION SELECT hostel_name FROM hostels",
    "SELECT program_id, COUNT(*) AS n FROM students GROUP BY program_id HAVING n > 10 ORDER BY n DESC",
    "SELECT name FROM students WHERE student_id IN (SELECT student_id FROM fees WHERE status = 'UNPAID')",
    "SELECT x.total FROM (SELECT SUM(amount_paid) AS total FROM fees) AS x",
])
def test_allowed_selects(sql):
    v = validate(sql)
    assert v.ok, v.reason
    assert not v.hallucination


def test_adds_limit_when_missing():
    v = validate("SELECT name FROM students")
    assert v.ok and "LIMIT 500" in v.sql


def test_keeps_existing_limit():
    v = validate("SELECT name FROM students LIMIT 5")
    assert v.ok and "LIMIT 5" in v.sql and "500" not in v.sql


@pytest.mark.parametrize("sql", [
    "DELETE FROM fees",
    "DROP TABLE fees",
    "UPDATE fees SET amount_paid = amount_due",
    "INSERT INTO hostels VALUES (9, 'X', 'M', 10)",
    "INSERT OR REPLACE INTO hostels VALUES (1, 'X', 'M', 10)",
    "REPLACE INTO hostels VALUES (1, 'X', 'M', 10)",
    "ALTER TABLE fees ADD COLUMN hacked TEXT",
    "CREATE TABLE t (x INT)",
    "WITH d AS (DELETE FROM fees RETURNING *) SELECT * FROM d",
    "VACUUM",
])
def test_blocked_writes(sql):
    v = validate(sql)
    assert not v.ok
    assert v.reason


@pytest.mark.parametrize("sql", [
    "SELECT * FROM students; DROP TABLE fees",
    "SELECT 1; SELECT 2",
])
def test_multiple_statements_blocked(sql):
    v = validate(sql)
    assert not v.ok and "one SQL statement" in v.reason


@pytest.mark.parametrize("sql", [
    "PRAGMA table_info(students)",
    "PRAGMA writable_schema = 1",
    "ATTACH DATABASE 'other.db' AS other",
    "DETACH DATABASE other",
])
def test_pragma_attach_blocked(sql):
    assert not validate(sql).ok


def test_forbidden_function_blocked():
    v = validate("SELECT load_extension('evil.so')")
    assert not v.ok and "load_extension" in v.reason


def test_unparseable_blocked():
    assert not validate("SELEC name FROM students").ok
    assert not validate("").ok


def test_hallucinated_table():
    v = validate("SELECT phone FROM parents")
    assert not v.ok
    assert v.unknown_tables == ["parents"]
    assert v.hallucination


def test_hallucinated_column_qualified():
    v = validate("SELECT s.phone_number FROM students s")
    assert not v.ok and v.hallucination
    assert "s.phone_number" in v.unknown_columns


def test_hallucinated_column_unqualified():
    v = validate("SELECT placement_salary FROM students")
    assert not v.ok and "placement_salary" in v.unknown_columns


def test_column_from_wrong_table():
    # `grade` exists, but not in `fees`
    v = validate("SELECT f.grade FROM fees f")
    assert not v.ok and "f.grade" in v.unknown_columns


def test_double_quoted_string_flagged():
    v = validate('SELECT COUNT(*) FROM fees WHERE status = "PAID"')
    assert not v.ok and "single quotes" in v.reason


def test_system_tables_blocked():
    assert not validate("SELECT sql FROM sqlite_master").ok
