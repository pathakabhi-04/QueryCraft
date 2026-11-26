# Viva preparation: which files each member must be able to explain

This follows the contribution table (Section 7 of the Milestone 2 PDF, slide 8 of the deck).
Faculty may ask either member to explain any file they claim, so start with the
"must know" files.

## Both members (the shared core)

| File | What it does | Be ready to explain |
|---|---|---|
| `querycraft/pipeline.py` | The whole flow: question → prompt → LLM → parse → validate → execute → self-correction loop | The order of steps; why a refusal (`UNSAFE`/`CANNOT_ANSWER`) is never executed; the retry loop (`MAX_FIX_RETRIES = 2`, no retry for write blocks) |
| `querycraft/config.py` | Reads settings (model names, keys, temperature, limits) from `.env` / Streamlit secrets | Why keys live in `.env` and never in git; temperature 0 |
| `README.md`, `docs/architecture.md` | How to run the project; the diagrams | Walk through the system architecture diagram |
| `data/schema.sql`, `data/schema_docs.yaml` | The 8 tables, and column descriptions + allowed values | What a "day scholar" is (`hostel_id IS NULL`), how attendance % and dues are calculated |

## Ishita Bora: safety layer, app, prompt experiments, testing

| File | What it does | Be ready to explain |
|---|---|---|
| `querycraft/validator.py` | Parses the SQL with sqlglot and allows only one read-only `SELECT` on known tables/columns; adds `LIMIT 500` | Why safety is in code and not only in the prompt; how `DELETE`, `PRAGMA`, `ATTACH`, multiple statements and made-up columns are caught; the block categories (`write`, `unknown_column`, …) |
| `querycraft/executor.py` | Runs the query on a read-only SQLite connection | The 3 layers: `mode=ro` URI, `query_only`, the authorizer; the 5-second timeout (`set_progress_handler`) and the row limit |
| `tests/test_validator.py`, `tests/test_executor.py` | pytest checks for the safety layer | One example each of an allowed query, a blocked write and a timeout |
| `app/streamlit_app.py` | The web app: question box, model and version selectors, results, refusals, sidebar | How the app calls `pipeline.answer()`; how refusals and blocked queries are shown; the human-review note; how it reads keys from Streamlit Cloud secrets |
| `prompts/ablation/v2_plan.txt`, `v2_values.txt` | V2 + one technique, for the ablation study | What "ablation" means and why we add one technique at a time |
| `eval/evaluate.py` (ablation runs) | Runs configs × models × questions and saves results | The ablation command (`--configs v2,v2+fewshot,v2+plan,v2+values,v2+sc --per-category 6`); what the 30-question subset is |
| `eval/results/*ablation30/`, `*llama3b*/` | Saved ablation and local Llama 3B results | Why the 3B model improved only with few-shot examples and got worse with long prompts |
| `test-data/test_inputs.yaml`, `eval/run_tests.py` | The 14 test inputs (Normal / Edge / Invalid) and the runner that fills the test table | How Pass/Fail is decided (status match + same rows); one edge case and one invalid case |
| `docs/take_screenshots.py` | Captures the app screenshots for the report | (optional) that the screenshots are real runs |

## Abhinav Pathak: prompt design, evaluation, iteration log, reel

| File | What it does | Be ready to explain |
|---|---|---|
| `prompts/v1/` … `prompts/v4/`, `prompts/final/v5_value_hints.txt` | The prompt versions V1 → V5 (P1, generation prompt) | What each version added and why (rules + JSON, few-shot, plan-first, value hints) |
| `prompts/final/fix_error.txt` | P2, the self-correction prompt | What goes into `{previous_sql}` and `{error}`; the Q039 example (hallucinated column fixed in 1 retry) |
| `prompts/fewshot_examples.yaml` | The 6 worked examples (4 answers, 1 `CANNOT_ANSWER`, 1 `UNSAFE`) | Why examples are not taken from the test set (no answer leakage) |
| `prompts/CHANGELOG.md`, `docs/iteration_log.md` | Why each version changed, with the measured results | The numbers: Gemini 67% → 93% → 96%; why the 2 prompts vs 6 versions count |
| `querycraft/prompt_builder.py` | Fills `{schema}`, `{examples}`, `{value_hints}`, `{question}` into a template | How one config maps to a template + techniques; why the question is filled last |
| `querycraft/llm.py` | One `generate()` function for Gemini, Groq and Ollama; caching, retries, rate limits | Why temperature 0 and minimal hidden reasoning; why responses are cached; Gemini 500 requests/day limit |
| `querycraft/parsing.py` | Extracts and repairs the JSON answer (and the SQL from V1's free text) | What counts as a parse failure; why V1 is treated as always `OK` |
| `eval/metrics.py` | Scores every answer | Execution accuracy (compare result rows, not SQL text), refusal accuracy, safety, false refusals, hallucination |
| `eval/evaluate.py`, `eval/compare.py` | Runs the cumulative evaluation and makes the tables and charts | The command used; where results are saved (`raw.jsonl`, `summary.md`, `charts/`) |
| `benchmark/questions.yaml`, `benchmark/check_gold.py` | 100 questions (easy → adversarial) with gold SQL | The 5 categories; that gold SQL is `verified: false` until hand-checked |
| `docs/reel_script.md` | The demo reel script | The demo question and its answer (44 CSE day scholars) |

## Quick self-test (each member should answer without notes)

1. A user types "delete all fee records". Name every place this is stopped. *(prompt rule → `UNSAFE`; validator blocks non-SELECT; read-only connection + authorizer)*
2. Why does V5 fix "CSE" vs "B.Tech CSE"? *(value hints list the exact allowed programme names)*
3. What happens when the model invents a column? *(validator blocks it → P2 gets the error → retry, max 2)*
4. Why is the number of prompts 2 but the number of versions 6?
5. What is execution accuracy, and why not compare SQL text?
