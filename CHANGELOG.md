# Changelog

Dated list of changes since Milestone 1. Prompt-level detail is in `prompts/CHANGELOG.md`;
who did what is in `docs/contribution_log.md`.

## Milestone 1 (submitted)
- Problem statement and V1 baseline prompt (`prompts/v1/v1_baseline.txt`, kept unchanged).

## 2026-11-21
- **Database:** synthetic university DB (8 tables, 500 students, seed 42) with a deterministic
  generator, schema, and column descriptions / allowed values (`data/`).
- **Safety layer:** sqlglot validator (one SELECT only, write/PRAGMA/ATTACH blocked, unknown
  tables/columns caught, automatic LIMIT 500) and read-only executor (mode=ro, authorizer,
  timeout) with pytest coverage.
- **Models:** one interface for Gemini (Google AI Studio) and Llama (Groq or local Ollama),
  with backoff, rate-limit delay and a response cache.
- **Prompts:** V2 (rules + JSON + refusal statuses), V3 (few-shot), V4 (plan-first),
  V5 (column descriptions + allowed values), self-correction prompt; ablation variants.
  Prompts reorganised into `prompts/v1..v4/` and `prompts/final/`.
- **Benchmark:** 100 questions (25 easy, 30 medium, 20 hard, 15 unanswerable,
  10 adversarial) with draft gold SQL, awaiting hand verification.
- **Evaluation:** metrics (execution accuracy, refusal accuracy, safety, false refusals,
  valid SQL, hallucination, latency, consistency), evaluation runner, reports and charts.
- **Fix:** local Ollama now runs with an 8192-token context. The default 4096 silently
  truncated the V5 prompt.
- **App:** Streamlit prototype (explanation first, result table, SQL, assumptions,
  confidence, latency, clear refusal messages, human-review note).
- **Docs:** README, architecture diagrams, Milestone 2 test inputs and runner.

## 2026-11-21 (evening)
- **Models:** Model A is `gemini-3.5-flash-lite` (Google AI Studio). Model B is the open-weight
  `openai/gpt-oss-120b` on Groq, because Groq has retired its Llama chat models (404).
  `llama3.2:3b` via local Ollama is kept as a third, small open model.
- **Fix:** thinking models were cutting their JSON answers off (Gemini used 982 of 1024 output
  tokens on hidden reasoning). Hidden reasoning is now minimal (`GEMINI_THINKING_LEVEL`,
  `GROQ_REASONING_EFFORT`), and every call records its `finish_reason`.
- **Fix:** rate-limit waits are no longer counted as model latency (SDK-internal retries off;
  `Retry-After` honoured).
- **Evaluation:** first results on local `llama3.2:3b` (30-question subset). Full 100-question
  runs on both API models plus the ablation subset.

## 2026-11-22
- **Evaluation finished for Milestone 2.**
  - Gemini: all 100 questions × V1–V5+SC (`eval/results/20261122-170552-gemini-full100/`) and
    the 30-question ablation.
  - gpt-oss-120b: V1–V5+SC on the 30-question subset (the Groq free tier allows 200k tokens a
    day); V1–V3 on all 100 questions.
  - llama3.2:3b (local): cumulative and ablation runs on the subset.
  - Combined tables and charts are in `eval/results/M2-cumulative/` and `eval/results/M2-ablation/`.
- **Test table:** 14 inputs on V5+SC / Gemini, 14/14 passed
  (`test-data/test_table_gemini_v5_sc.md`); screenshots of real runs are in `docs/screenshots/`.
- **Docs:** iteration log, limitations, research abstract and P1/P2 sample runs written from the
  measured results. Built the M2 report PDF and the research-abstract PDF.
