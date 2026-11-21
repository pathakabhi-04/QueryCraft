"""Turn raw model text into something the pipeline can use.

* parse_json_response(): for V2+ prompts. Strips markdown fences, finds the
  JSON object, applies small repairs, and normalises the fields. Returns
  (dict, None) or (None, error_message). A parse failure counts as a wrong
  answer in evaluation, never a crash.
* extract_sql_from_text(): for V1, whose answer is free text.
"""

import json
import re

STATUSES = {"OK", "CANNOT_ANSWER", "UNSAFE"}
CONFIDENCES = {"high", "medium", "low"}

_FENCE_RE = re.compile(r"```[a-zA-Z]*\s*\n?(.*?)```", re.DOTALL)


def strip_code_fences(text: str) -> str:
    """Return the content of the first ``` block if there is one, else the text."""
    m = _FENCE_RE.search(text or "")
    return m.group(1).strip() if m else (text or "").strip()


def _find_json_object(text: str) -> str | None:
    """Return the first balanced {...} in text, respecting strings."""
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        start = text.find("{", start + 1)
    return None


def _repair(s: str) -> str:
    s = s.replace("“", '"').replace("”", '"')          # smart quotes
    s = re.sub(r",\s*([}\]])", r"\1", s)                          # trailing commas
    # raw newlines inside string values are invalid JSON; escape them
    out, in_str, esc = [], False, False
    for ch in s:
        if in_str and ch == "\n":
            out.append("\\n")
            continue
        out.append(ch)
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
    return "".join(out)


def _close_truncated(text: str) -> str | None:
    """If the output stops before the JSON object ends, close the open
    string / brackets so that e.g. a missing final '}' is not fatal."""
    start = text.find("{")
    if start == -1:
        return None
    stack, in_str, esc = [], False, False
    for ch in text[start:]:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    if not stack:
        return None
    body = text[start:].rstrip().rstrip(",")
    return body + ('"' if in_str else "") + "".join(reversed(stack))


def parse_json_response(text: str) -> tuple[dict | None, str | None]:
    if not text or not text.strip():
        return None, "empty model output"
    candidates = [strip_code_fences(text), text]
    obj, last_err = None, "no JSON object found"
    for cand in candidates:
        blob = _find_json_object(cand) or _close_truncated(cand)
        if blob is None:
            continue
        for attempt in (blob, _repair(blob)):
            try:
                obj = json.loads(attempt)
                break
            except json.JSONDecodeError as e:
                last_err = f"invalid JSON: {e}"
        if obj is not None:
            break
    if not isinstance(obj, dict):
        return None, last_err
    return normalise(obj), None


def normalise(obj: dict) -> dict:
    status = str(obj.get("status", "")).strip().upper().replace(" ", "_")
    if status not in STATUSES:
        # missing/odd status: infer OK if there is SQL, else treat as a refusal
        status = "OK" if obj.get("sql") else "CANNOT_ANSWER"
    assumptions = obj.get("assumptions") or []
    if isinstance(assumptions, str):
        assumptions = [assumptions]
    conf = str(obj.get("confidence", "")).strip().lower()
    plan = obj.get("plan", "")
    if isinstance(plan, (list, dict)):
        plan = json.dumps(plan, ensure_ascii=False)
    return {
        "status": status,
        "sql": strip_code_fences(str(obj.get("sql") or "")).strip(),
        "explanation": str(obj.get("explanation") or "").strip(),
        "assumptions": [str(a) for a in assumptions],
        "confidence": conf if conf in CONFIDENCES else "",
        "plan": str(plan or "").strip(),
    }


_SQL_START_RE = re.compile(r"\b(WITH|SELECT)\b", re.IGNORECASE)


def extract_sql_from_text(text: str) -> str:
    """Best-effort SQL extraction from a free-text (V1) answer."""
    text = text or ""
    for block in _FENCE_RE.findall(text):
        if _SQL_START_RE.search(block):
            return block.strip()
    m = _SQL_START_RE.search(text)
    if not m:
        return ""
    rest = text[m.start():]
    end = rest.find(";")
    if end != -1:
        return rest[:end + 1].strip()
    return re.split(r"\n\s*\n", rest, maxsplit=1)[0].strip()   # up to first blank line


def explanation_from_text(text: str, sql: str) -> str:
    """For V1: whatever prose is left after removing the SQL / code blocks."""
    rest = _FENCE_RE.sub("", text or "")
    if sql:
        rest = rest.replace(sql, "")
    lines = [ln.strip() for ln in rest.splitlines() if ln.strip()]
    return " ".join(lines)[:500]
