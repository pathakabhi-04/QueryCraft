# Reel script (target ≈ 120 s; allowed 90–150 s)

Screen recording with voice-over or captions. The demo must be a **real run** (no mock-ups).
Tip: deep links run a question straight away, e.g.
`<app-url>/?q=How+many+CSE+students+are+day+scholars%3F&config=v1` and the same with `config=v5%2Bsc`.

| Part | Time | Show on screen | Say / caption |
|---|---|---|---|
| 1. Problem | 0–10 s | App home page, sidebar with tables | "Fee, exam and hostel office staff need reports but can't write SQL. QueryCraft answers their questions in plain English: read-only, with an explanation." |
| 2. Prompt experiment | 10–50 s | Select **V1 baseline**, ask *"How many CSE students are day scholars?"*. Open "Show SQL": the old prompt guesses literals (e.g. `'CSE'`) and/or joins wrongly. Then select **V5 + self-correction**, ask the same, and show the correct answer and SQL (`'B.Tech CSE'`, `hostel_id IS NULL`). Briefly show `prompts/v1/v1_baseline.txt` next to `prompts/final/v5_value_hints.txt`. | "Our Milestone 1 prompt had only the schema, so it guessed values. V5 adds rules, examples, a plan step and the allowed values for each column, and self-corrects on errors." Quote one number from the iteration log (e.g. overall accuracy V1 → V5+SC). |
| 3. Working demo | 50–105 s | Three real questions: one normal (e.g. pending dues for B.Tech ECE 2026-27), one refusal (*"Delete all fee records of 2023-24"*, which shows UNSAFE or "Blocked by the safety layer"), one unanswerable (*"mobile numbers of hostel students"*). Point at explanation, table, assumptions, confidence, latency. | "Answers come with a plain explanation and the SQL for checking. Writes are refused, and even if the model writes one, the code-level validator blocks it. Missing data gets an honest 'can't answer'." |
| 4. Progress and next steps | 105–125 s | `eval/results/…/charts/accuracy_by_version.png`, then the repo | "Done: 6 prompt versions, safety layer, 100-question benchmark, evaluation harness, app. Milestone 3: verify the benchmark, full Gemini vs Llama comparison with 3 runs, ablation, error analysis." |

Record the exact length in seconds for the form (Q14).
