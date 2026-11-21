from querycraft.parsing import extract_sql_from_text, parse_json_response


def test_plain_json():
    d, err = parse_json_response('{"status": "OK", "sql": "SELECT 1", "explanation": "x", '
                                 '"assumptions": [], "confidence": "high"}')
    assert err is None and d["status"] == "OK" and d["sql"] == "SELECT 1"


def test_fenced_json_with_prose():
    text = 'Here you go:\n```json\n{"status": "ok", "sql": "SELECT 2", "confidence": "HIGH"}\n```'
    d, err = parse_json_response(text)
    assert err is None and d["status"] == "OK" and d["confidence"] == "high"


def test_trailing_comma_and_raw_newline():
    d, err = parse_json_response('{"status": "OK", "sql": "SELECT name\nFROM students",}')
    assert err is None and "FROM students" in d["sql"]


def test_truncated_json_is_closed():
    d, err = parse_json_response('{\n "status": "UNSAFE",\n "sql": "",\n "assumptions": ["a"],\n'
                                 ' "confidence": "low"\n')
    assert err is None and d["status"] == "UNSAFE"


def test_braces_inside_strings():
    d, err = parse_json_response('{"status": "OK", "sql": "SELECT \'{x}\'", "explanation": "}"}')
    assert err is None and d["explanation"] == "}"


def test_garbage_is_parse_error():
    d, err = parse_json_response("I cannot help with that.")
    assert d is None and err


def test_missing_status_inferred():
    d, _ = parse_json_response('{"sql": "SELECT 1"}')
    assert d["status"] == "OK"
    d, _ = parse_json_response('{"explanation": "no data"}')
    assert d["status"] == "CANNOT_ANSWER"


def test_v1_extract_from_fence():
    text = "```sql\nSELECT COUNT(*) FROM students;\n```\nThis counts students."
    assert extract_sql_from_text(text) == "SELECT COUNT(*) FROM students;"


def test_v1_extract_bare():
    text = "SELECT name FROM students WHERE hostel_id IS NULL;\n\nLists day scholars."
    assert extract_sql_from_text(text) == "SELECT name FROM students WHERE hostel_id IS NULL;"


def test_v1_no_sql():
    assert extract_sql_from_text("Sorry, I can't do that.") == ""
