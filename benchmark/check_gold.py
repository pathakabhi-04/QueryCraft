"""Sanity-check the benchmark: structure, gold SQL execution, category counts.

    python -m benchmark.check_gold            # summary
    python -m benchmark.check_gold --show     # also print the first rows of each gold result

Gold SQL is run through the same validator + read-only executor as model SQL,
so a gold query that the safety layer would block is caught here.
This script does NOT prove gold SQL is *correct*; humans verify that by hand.
"""

import argparse
import hashlib
import sys
from collections import Counter

import yaml

from querycraft.config import BENCHMARK_PATH
from querycraft.executor import execute

CATEGORIES = {"easy": 25, "medium": 30, "hard": 20, "unanswerable": 15, "adversarial": 10}
STATUS_FOR = {"unanswerable": "CANNOT_ANSWER", "adversarial": "UNSAFE"}
REQUIRED = ["id", "question", "category", "expected_status", "gold_sql",
            "order_matters", "verified", "notes"]


def load_questions(path=BENCHMARK_PATH) -> list[dict]:
    return yaml.safe_load(path.read_text())["questions"]


def file_hash(path=BENCHMARK_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    items = load_questions()
    problems = []
    ids = [q.get("id") for q in items]
    for dup in [i for i, n in Counter(ids).items() if n > 1]:
        problems.append(f"duplicate id {dup}")
    texts = Counter(q.get("question", "").strip().lower() for q in items)
    for dup in [t for t, n in texts.items() if n > 1]:
        problems.append(f"duplicate question: {dup}")

    for q in items:
        qid = q.get("id", "?")
        missing = [k for k in REQUIRED if k not in q]
        if missing:
            problems.append(f"{qid}: missing fields {missing}")
            continue
        if q["category"] not in CATEGORIES:
            problems.append(f"{qid}: unknown category {q['category']}")
        expected = STATUS_FOR.get(q["category"], "OK")
        if q["expected_status"] != expected:
            problems.append(f"{qid}: expected_status should be {expected}")
        if expected != "OK":
            if q["gold_sql"]:
                problems.append(f"{qid}: refusal item should have empty gold_sql")
            continue
        res = execute(q["gold_sql"])
        if not res["ok"]:
            problems.append(f"{qid}: gold SQL failed: {res['blocked_reason'] or res['error']}")
            continue
        n = len(res["rows"])
        flag = ""
        if n == 0:
            flag = "  <-- EMPTY RESULT"
            problems.append(f"{qid}: gold SQL returns no rows")
        elif n == 1 and len(res["columns"]) == 1 and res["rows"][0][0] in (None, 0):
            flag = "  <-- result is 0/NULL"
            problems.append(f"{qid}: gold SQL returns 0/NULL")
        print(f"{qid} [{q['category']:<6}] {n:>4} row(s) x {len(res['columns'])} col(s){flag}")
        if args.show:
            for row in res["rows"][:3]:
                print("        ", row)

    counts = Counter(q.get("category") for q in items)
    print("\nCategory counts (actual / target):")
    for cat, target in CATEGORIES.items():
        mark = "" if counts[cat] == target else "  <-- off target"
        print(f"  {cat:<13} {counts[cat]:>3} / {target}{mark}")
    print(f"  {'total':<13} {len(items):>3} / {sum(CATEGORIES.values())}")
    verified = sum(1 for q in items if q.get("verified") is True)
    print(f"\nVerified by hand: {verified} / {len(items)}")
    print(f"questions.yaml sha256: {file_hash()}")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1
    print("\nAll gold SQL executes successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
