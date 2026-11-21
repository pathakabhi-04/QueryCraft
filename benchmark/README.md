# QueryCraft benchmark

`questions.yaml` holds the fixed 100-question benchmark used by `eval/evaluate.py`.

## Status

| | |
|---|---|
| State | **DRAFT, not frozen** |
| Verified by hand | 0 / 100 |
| Freeze date | _not frozen yet_ |
| SHA-256 of `questions.yaml` at freeze | _fill in at freeze time_ |

## Mix

| Category | Count | expected_status | What it tests |
|---|---|---|---|
| easy | 25 | OK | single table, simple filter or count |
| medium | 30 | OK | one or two joins, GROUP BY, derived values (dues = amount_due − amount_paid) |
| hard | 20 | OK | several joins, subqueries, HAVING, top-N, attendance-percentage thresholds |
| unanswerable | 15 | CANNOT_ANSWER | data not in the DB (parents' phones, placements, faculty, ...) |
| adversarial | 10 | UNSAFE | write/delete requests, prompt injection, bulk personal-data export |

## How it was built

1. Questions were written in the style of real admin-office staff (informal, Indian
   context: "dues", "defaulters", "day scholars", ₹, "this semester").
2. Gold SQL was **drafted by Claude Code** against the synthetic DB built by
   `data/generate_db.py` (seed 42).
3. `python -m benchmark.check_gold` checks structure, runs every gold query through the
   same validator + read-only executor as model SQL, flags empty or 0/NULL results,
   and prints the category counts and the file hash. Top-N questions were checked for
   ties at the cut-off (Q058 has a tie inside the top 5, so its row order is not compared).
4. **Every item is `verified: false` until a team member checks it by hand.**

Items that depend on knowing the current academic year ('this year', 'this semester'
= `'2026-27'`) say so in `notes`. Only V5 is told the current year (via
`schema_docs.yaml`), which is part of what V5 is meant to fix.

## How to verify (team task)

For each item:

1. Read the question as a staff member would. Is there one reasonable reading?
   If not, rephrase the question (don't bend the SQL to a strange reading).
2. Read the gold SQL. Does it answer *that* reading? Check joins, filters, literals,
   DISTINCT vs not, and the aggregation level.
3. Run it: `python -m benchmark.check_gold --show`, or open `data/university.db` in any
   SQLite viewer.
4. For refusal items, confirm the data really is absent (or the request really is unsafe).
5. Set `verified: true`, and add to `notes` if you changed anything.

When all 100 are verified: run `check_gold` again, record the freeze date and SHA-256
above, commit, and **don't edit `questions.yaml` after that**. A changed benchmark
makes earlier results incomparable.

## Rules

- Few-shot examples (`prompts/fewshot_examples.yaml`) must not be copied from here.
- No benchmark question may be special-cased in prompts or code.
