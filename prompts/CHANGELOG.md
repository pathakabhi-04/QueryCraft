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
