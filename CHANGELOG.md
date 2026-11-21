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
