"""Run configs x models x benchmark questions and write a timestamped results folder.

    python -m eval.evaluate --configs v1,v2,v3 --models gemini,llama --runs 3
    python -m eval.evaluate --configs v2 --models llama --limit 10          # smoke test
    python -m eval.evaluate --configs v2+fewshot,v2+plan,v2+values,v2+sc    # ablation

Output: eval/results/<timestamp>/
    meta.json      exact model names, settings, benchmark hash, git commit, command
    raw.jsonl      one line per (run, model, config, question): raw output, parsed JSON,
                   SQL, validator/executor result, scores, latency
    summary.csv / summary.md / failures.md / charts/   (written by eval/compare.py)

API responses are cached in eval/cache/ keyed by (model, settings, prompt, run), so an
interrupted or repeated run only pays for calls it has not made yet. Use --no-cache
to force fresh calls.
"""

import argparse
import datetime as dt
import json
import subprocess
import sys
import time

from benchmark.check_gold import file_hash, load_questions
from eval import compare
from eval.metrics import score
from querycraft import llm
from querycraft.config import RESULTS_DIR, ROOT, get_settings
from querycraft.executor import execute
from querycraft.pipeline import answer
from querycraft.prompt_builder import CONFIGS

MAX_ROWS_LOGGED = 20


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _jsonable(rec: dict) -> dict:
    rec = dict(rec)
    rows = rec.get("rows") or []
    rec["row_count"] = len(rows)
    rec["rows"] = [list(r) for r in rows[:MAX_ROWS_LOGGED]]
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description="QueryCraft evaluation harness")
    ap.add_argument("--configs", default="v1,v2,v3,v4,v5,v5+sc",
                    help=f"comma-separated; known: {','.join(CONFIGS)}")
    ap.add_argument("--models", default="gemini,llama")
    ap.add_argument("--runs", type=int, default=1, help="repeat everything N times (consistency)")
    ap.add_argument("--limit", type=int, help="only the first N questions (smoke test)")
    ap.add_argument("--ids", help="comma-separated question ids, e.g. Q001,Q056")
    ap.add_argument("--categories", help="comma-separated categories to keep")
    ap.add_argument("--per-category", type=int,
                    help="only the first N questions of each category (stratified subset)")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--tag", default="", help="suffix for the results folder name")
    args = ap.parse_args()

    configs = [c.strip() for c in args.configs.split(",") if c.strip()]
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    for c in configs:
        if c not in CONFIGS:
            sys.exit(f"Unknown config {c!r}. Known: {', '.join(CONFIGS)}")
    for m in models:
        if m not in llm.MODELS:
            sys.exit(f"Unknown model {m!r}. Known: {', '.join(llm.MODELS)}")

    items = load_questions()
    if args.ids:
        wanted = set(args.ids.split(","))
        items = [q for q in items if q["id"] in wanted]
    if args.categories:
        cats = set(args.categories.split(","))
        items = [q for q in items if q["category"] in cats]
    if args.per_category:
        seen = {}
        keep = []
        for q in items:
            seen[q["category"]] = seen.get(q["category"], 0) + 1
            if seen[q["category"]] <= args.per_category:
                keep.append(q)
        items = keep
    if args.limit:
        items = items[: args.limit]
    if not items:
        sys.exit("No questions selected.")

    gold = {}
    for q in items:
        if q["expected_status"] == "OK":
            res = execute(q["gold_sql"])
            if not res["ok"]:
                sys.exit(f"Gold SQL for {q['id']} fails: {res['blocked_reason'] or res['error']}")
            gold[q["id"]] = res["rows"]
        else:
            gold[q["id"]] = []

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RESULTS_DIR / (stamp + (f"-{args.tag}" if args.tag else ""))
    (out / "charts").mkdir(parents=True)

    s = get_settings()
    verified = sum(1 for q in load_questions() if q.get("verified") is True)
    meta = {
        "started": dt.datetime.now().isoformat(timespec="seconds"),
        "command": "python -m eval.evaluate " + " ".join(sys.argv[1:]),
        "configs": configs,
        "models": {m: dict(zip(("backend", "model_name"), llm.model_info(m))) for m in models},
        "temperature": s.temperature,
        "max_output_tokens": s.max_output_tokens,
        "max_fix_retries": 2,
        "runs": args.runs,
        "n_questions": len(items),
        "benchmark_sha256": file_hash(),
        "benchmark_verified": f"{verified}/{len(load_questions())}",
        "git_commit": _git_commit(),
        "cache": not args.no_cache,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Writing results to {out}")
    print(f"{len(items)} questions x {len(configs)} configs x {len(models)} models x "
          f"{args.runs} run(s) = {len(items) * len(configs) * len(models) * args.runs} calls")

    total = len(items) * len(configs) * len(models) * args.runs
    done, t0 = 0, time.monotonic()
    try:
        with open(out / "raw.jsonl", "w") as fh:
            for run in range(args.runs):
                for model in models:
                    for config in configs:
                        for q in items:
                            rec = answer(q["question"], config, model, run=run,
                                         use_cache=not args.no_cache)
                            sc = score(rec, q, gold[q["id"]])
                            line = {"id": q["id"], **_jsonable(rec), **sc}
                            fh.write(json.dumps(line, ensure_ascii=False, default=str) + "\n")
                            fh.flush()
                            done += 1
                            mark = "ok " if sc["correct"] else "BAD"
                            print(f"[{done}/{total}] run{run} {model:<6} {config:<10} {q['id']} "
                                  f"{mark} {rec['status'] or '':<13} {rec['latency']:.1f}s"
                                  f"{' cached' if rec['cached'] else ''}"
                                  f"{'' if sc['correct'] else '  ' + sc['error_type']}", flush=True)
    except KeyboardInterrupt:
        print("\nInterrupted: writing reports for the calls completed so far.")
        meta["interrupted_after_calls"] = done
    meta["finished"] = dt.datetime.now().isoformat(timespec="seconds")
    meta["wall_seconds"] = round(time.monotonic() - t0, 1)
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    compare.write_reports(out)
    print(f"\nDone. See {out / 'summary.md'}")


if __name__ == "__main__":
    main()
