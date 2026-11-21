"""question -> prompt -> LLM -> parse -> validate -> execute -> (self-correction loop)

    python -m querycraft.pipeline "How many day scholars are there?" --config v2 --model llama

answer() returns one flat dict (one "record") that the app shows and that
eval/evaluate.py writes to raw.jsonl.
"""

import argparse
import datetime as dt

from querycraft import llm
from querycraft.config import DB_PATH, get_settings
from querycraft.executor import execute
from querycraft.parsing import explanation_from_text, extract_sql_from_text, parse_json_response
from querycraft.prompt_builder import build_fix_prompt, build_prompt, get_config

MAX_FIX_RETRIES = 2
# Blocks that self-correction must not try to "repair": a write request stays blocked.
NO_RETRY_CATEGORIES = {"write"}


def _parse(text: str, json_output: bool) -> tuple[dict | None, str | None]:
    if json_output:
        return parse_json_response(text)
    # V1: free text, no status field -> always "OK"
    sql = extract_sql_from_text(text)
    parsed = {"status": "OK", "sql": sql, "explanation": explanation_from_text(text, sql),
              "assumptions": [], "confidence": "", "plan": ""}
    return parsed, (None if sql else "no SQL found in free-text answer")


def answer(question: str, config: str = "v2", model: str = "llama", run: int = 0,
           use_cache: bool = True, db_path=DB_PATH) -> dict:
    cfg = get_config(config)
    settings = get_settings()
    backend, model_name = llm.model_info(model)

    rec = {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "config": cfg.name,
        "prompt_version": cfg.prompt_version,
        "self_correct": cfg.self_correct,
        "model": model,
        "model_name": model_name,
        "backend": backend,
        "temperature": settings.temperature,
        "reasoning": (f"thinking_level={settings.gemini_thinking_level or 'default'}"
                      if backend == "gemini" else
                      f"reasoning_effort={settings.groq_reasoning_effort or 'default'}"
                      if backend == "groq" and "gpt-oss" in model_name else "n/a"),
        "max_output_tokens": settings.max_output_tokens,
        "run": run,
        "attempts": [],            # one entry per LLM call (first + fix retries)
        "status": None,            # OK | CANNOT_ANSWER | UNSAFE | PARSE_ERROR | LLM_ERROR
        "sql": "", "executed_sql": "",
        "explanation": "", "assumptions": [], "confidence": "", "plan": "",
        "ok": False, "columns": [], "rows": [],
        "error": None, "blocked_reason": None, "block_category": None,
        "hallucination": False, "hallucination_any_attempt": False,
        "retries": 0, "latency": 0.0, "cached": True,
    }

    prompt = build_prompt(cfg, question)
    rec["prompt_hash"] = llm.prompt_hash(prompt)

    def call(p: str) -> dict | None:
        try:
            resp = llm.generate(p, model, use_cache=use_cache, run=run)
        except llm.LLMError as e:
            rec["status"], rec["error"] = "LLM_ERROR", str(e)
            return None
        rec["latency"] += resp.latency
        rec["cached"] = rec["cached"] and resp.cached
        parsed, perr = _parse(resp.text, cfg.json_output if not rec["attempts"] else True)
        rec["attempts"].append({"prompt_hash": llm.prompt_hash(p), "raw_output": resp.text,
                                "parsed": parsed, "parse_error": perr,
                                "latency": resp.latency, "cached": resp.cached,
                                "finish_reason": resp.finish_reason})
        return parsed if not perr else None

    parsed = call(prompt)
    if parsed is None:
        if rec["status"] is None:
            rec["status"] = "PARSE_ERROR"
            rec["error"] = rec["attempts"][-1]["parse_error"]
        return rec

    def take(p: dict) -> None:
        rec.update({k: p[k] for k in ("status", "sql", "explanation", "assumptions",
                                      "confidence", "plan")})

    take(parsed)
    if rec["status"] != "OK":
        return rec                 # refusal: never execute, even if SQL was included

    def run_sql() -> dict:
        res = execute(rec["sql"], db_path=db_path)
        rec.update({"ok": res["ok"], "columns": res["columns"], "rows": res["rows"],
                    "error": res["error"], "blocked_reason": res["blocked_reason"],
                    "block_category": res["block_category"],
                    "hallucination": res["hallucination"],
                    "executed_sql": res["sql"] if res["ok"] else ""})
        rec["hallucination_any_attempt"] |= res["hallucination"]
        return res

    res = run_sql()
    while (cfg.self_correct and not res["ok"] and rec["retries"] < MAX_FIX_RETRIES
           and res["block_category"] not in NO_RETRY_CATEGORIES):
        rec["retries"] += 1
        err = res["blocked_reason"] or res["error"]
        fixed = call(build_fix_prompt(question, rec["sql"], err, cfg))
        if fixed is None:
            if rec["status"] == "LLM_ERROR":
                break
            continue               # unparseable fix: try again if budget remains
        take(fixed)
        if rec["status"] != "OK":
            # the model decided on reflection that it cannot / must not answer
            rec.update({"ok": False, "rows": [], "columns": [], "executed_sql": ""})
            break
        res = run_sql()
    return rec


def _print(rec: dict) -> None:
    print(f"[{rec['config']} | {rec['model_name']} ({rec['backend']}) | "
          f"{rec['latency']:.2f}s | retries={rec['retries']} | cached={rec['cached']}]")
    print(f"Status: {rec['status']}")
    if rec["explanation"]:
        print(f"Explanation: {rec['explanation']}")
    if rec["sql"]:
        print(f"SQL: {rec['sql']}")
    if rec["ok"]:
        print(f"Columns: {rec['columns']}")
        for row in rec["rows"][:10]:
            print("  ", row)
        if len(rec["rows"]) > 10:
            print(f"   ... {len(rec['rows'])} rows")
    if rec["blocked_reason"]:
        print(f"Blocked: {rec['blocked_reason']}")
    if rec["error"]:
        print(f"Error: {rec['error']}")


def main():
    ap = argparse.ArgumentParser(description="Ask QueryCraft one question.")
    ap.add_argument("question")
    ap.add_argument("--config", default="v2")
    ap.add_argument("--model", choices=llm.MODELS, default="llama")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--raw", action="store_true", help="also print the raw model output")
    args = ap.parse_args()
    rec = answer(args.question, args.config, args.model, use_cache=not args.no_cache)
    if args.raw:
        for i, a in enumerate(rec["attempts"]):
            print(f"--- raw output, attempt {i + 1} ---\n{a['raw_output']}\n")
    _print(rec)


if __name__ == "__main__":
    main()
