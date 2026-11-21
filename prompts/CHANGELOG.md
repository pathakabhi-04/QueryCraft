# Prompt changelog

Each entry says what changed, and why. Metrics belong in `eval/results/`, not here,
and must only ever be quoted from real `evaluate.py` runs.

Placeholders filled by `querycraft/prompt_builder.py`: `{schema}`, `{question}`,
`{examples}`, `{value_hints}` (plus `{previous_sql}`, `{error}` in `fix_error.txt`).
`{schema}` is the CREATE TABLE statements of `data/schema.sql` with comments removed,
so no version gets hints from comments that V5 is meant to add.

## V1 — `v1_baseline.txt` (M1 baseline, unchanged)
- Role + schema + question, free-text answer.
- Kept exactly as submitted in Milestone 1 (only the schema is now the real one).
- No status field, so for evaluation V1 is always treated as `OK`, and the SQL is
  extracted from the free text with a regex (`parsing.extract_sql_from_text`).
- Expected weaknesses: no refusals at all (unanswerable and adversarial questions
  will get SQL or prose), output format varies, so extraction can fail.

## V2 — `v2_rules_json.txt`
- **Added:** explicit read-only rule; "use only listed tables/columns"; two refusal
  statuses (`CANNOT_ANSWER`, `UNSAFE`) with when to use each; a line telling the
  model to treat the question only as a question (prompt-injection defence);
  SQLite + single-quote rule; an audience rule for the explanation; strict JSON
  output (`status`, `sql`, `explanation`, `assumptions`, `confidence`).
- **Why:** V1 cannot refuse, and its free text is hard to parse reliably. A fixed
  JSON shape makes every later version machine-checkable and lets us measure
  safety and false refusals separately from SQL accuracy.
- The safety rules are also enforced in code (`validator.py`, `executor.py`); the
  prompt rule is the first line of defence, not the only one.

## V3 — `v3/v3_fewshot.txt`
- **Added:** six worked examples (`fewshot_examples.yaml`) between the rules and the
  question: four answerable (join + filter, SUM over a join, attendance % with
  HAVING, top-N of a derived value), one `CANNOT_ANSWER`, one `UNSAFE`.
- **Why:** rules alone tell the model *what* to do; examples show *how* (join keys,
  exact literals, how a refusal looks in JSON). The refusal examples target V2's
  weakness of answering unanswerable questions with a guessed query.
- Examples are deliberately not taken from the benchmark (a test checks this), and
  their SQL is executed in the test suite.
- V3 is exactly V2 + examples, so it doubles as the `v2+fewshot` ablation.

## V4 — `v4/v4_plan_first.txt`
- **Added:** rule 7 and a `"plan"` field placed *before* `"sql"` in the JSON: tables,
  joins, filters with exact values, grouping, ordering. Examples now show a plan too.
- **Why:** decomposition. Writing the plan first makes the model commit to joins and
  filters before SQL, which should help multi-join and HAVING questions (the hard
  category). The plan is also shown to staff/evaluators as a readable trace.
- Ablation `ablation/v2_plan.txt` is V2 + only this rule and field.

## V5 — `final/v5_value_hints.txt` (final generation prompt, P1)
- **Added:** a "Column descriptions and allowed values" block from
  `data/schema_docs.yaml` (descriptions, allowed category values, notes such as the
  current academic year '2026-27', day scholar = `hostel_id IS NULL`, attendance % and
  dues formulas) and rule 8 (use exact allowed values; "this year" = current year).
- **Why:** wrong literals ('CSE' instead of 'B.Tech CSE') and not knowing what "this
  year" means are failures no amount of rules or examples can fix, because the model
  never sees the data. Only descriptions and category values are sent, never rows.
- Ablation `ablation/v2_values.txt` is V2 + only this block and rule.

## Self-correction — `final/fix_error.txt` (P2)
- **Added:** when the SQL is blocked by the validator (except write attempts) or fails
  at run time, the question, previous SQL and exact error go to this prompt; at most
  2 retries. Used by `v5+sc` and the `v2+sc` ablation.
- **Why:** many errors (unknown column, typo in a function) are obvious once the model
  sees the error message. Write attempts are never "repaired": they stay blocked.

## Settings change (all versions) — 2026-11-21
- Local Ollama runs now use Ollama's native API with `num_ctx` = 8192 (`OLLAMA_NUM_CTX`).
  With the default 4096-token context the ~12k-character V5 prompt was silently
  truncated, which would have made V5 look worse than it is on local Llama.
