"""Run the Milestone 2 test inputs and write the test table from real outputs.

    python -m eval.run_tests --config v5+sc --model gemini

Writes:
    test-data/outputs/<timestamp>_<model>_<config>.jsonl   full saved outputs
    test-data/test_table_<model>_<config>.md               the Section 4 table

Pass = predicted status equals the expected status, and for OK items the result
rows equal those of expected_sql (same comparison as EX in eval/metrics.py).
"""

import argparse
import datetime as dt
import json

import yaml

from eval.metrics import results_match
from querycraft import llm
from querycraft.config import ROOT
from querycraft.executor import execute
from querycraft.pipeline import answer

TEST_DIR = ROOT / "test-data"


def short_actual(rec: dict) -> str:
    st = rec["status"]
    if st in ("CANNOT_ANSWER", "UNSAFE"):
        return f"{st}: {rec['explanation'][:70]}"
    if st != "OK":
        return f"{st}: {(rec.get('error') or '')[:70]}"
    if rec.get("block_category") == "write":
        return "Wrote a write query; blocked by validator"
    if not rec["ok"]:
        return f"SQL failed: {(rec['blocked_reason'] or rec['error'] or '')[:60]}"
    rows = rec["rows"]
    if len(rows) == 1 and len(rows[0]) == 1:
        v = rows[0][0]
        return f"{round(v, 2) if isinstance(v, float) else v}"
    first = ", ".join(str(round(x, 2) if isinstance(x, float) else x) for x in rows[0]) if rows else ""
    return f"{len(rows)} row(s); first: {first[:50]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="v5+sc")
    ap.add_argument("--model", default="gemini", choices=llm.MODELS)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    tests = yaml.safe_load((TEST_DIR / "test_inputs.yaml").read_text())["tests"]
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = TEST_DIR / "outputs"
    out_dir.mkdir(exist_ok=True)
    safe_cfg = args.config.replace("+", "_")
    raw_path = out_dir / f"{stamp}_{args.model}_{safe_cfg}.jsonl"

    rows, passed = [], 0
    with open(raw_path, "w") as fh:
        for t in tests:
            rec = answer(t["input"], args.config, args.model, use_cache=not args.no_cache)
            ok = rec["status"] == t["expected_status"]
            if ok and t["expected_status"] == "OK":
                gold = execute(t["expected_sql"])
                ok = bool(rec["ok"]) and results_match(rec["rows"], gold["rows"])
            passed += ok
            rec = {**rec, "rows": [list(r) for r in rec["rows"][:20]]}
            fh.write(json.dumps({"test": t, "pass": ok, "output": rec}, default=str) + "\n")
            rows.append((t, rec, ok))
            print(f"{t['id']} {t['type']:<7} {'PASS' if ok else 'FAIL'}  {short_actual(rec)}")

    model_name = rows[0][1]["model_name"] if rows else ""
    md = [f"# Test table: `{args.config}` on `{model_name}`", "",
          f"Run {stamp}. Raw outputs: `{raw_path.relative_to(ROOT)}`. "
          f"Passed {passed} / {len(rows)}.", "",
          "| Test no. | Input (short) | Type | Expected output | Actual output (short) | Pass / Fail |",
          "|---|---|---|---|---|---|"]
    for t, rec, ok in rows:
        cells = [t["id"].lstrip("T").lstrip("0"), t["input"], t["type"], t["expected"],
                 short_actual(rec), "Pass" if ok else "Fail"]
        md.append("| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |")
    table_path = TEST_DIR / f"test_table_{args.model}_{safe_cfg}.md"
    table_path.write_text("\n".join(md) + "\n")
    print(f"\nPassed {passed}/{len(rows)}. Table: {table_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
