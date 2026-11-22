Each version adds **one** technique to the previous one, so a change in the numbers can be
traced to that technique. Results are **overall accuracy** = EX for answerable questions plus
correct status for questions that should be refused, measured by `eval/evaluate.py` at
temperature 0:

- **Gemini**: `gemini-3.5-flash-lite`, all 100 benchmark questions, run
  `eval/results/20261122-170552-gemini-full100/`.
- **gpt-oss**: `openai/gpt-oss-120b`, 30-question subset (first 6 of each category), run
  `eval/results/20261122-170552-gptoss120b-subset30/`. The Groq free tier (200k tokens/day) could not cover all 100
  for every version. V1–V3 on all 100 questions are in `eval/results/20261121-205657-gptoss120b-full100/`.
- **Llama 3B**: local `llama3.2:3b`, same 30-question subset, run
  `eval/results/20261121-200625-llama3b-local-subset30/`.

| Version | What changed (on purpose) | Why | Gemini (n=100) | gpt-oss (n=30) | Llama 3B (n=30) |
|---|---|---|---|---|---|
| **V1** baseline | Role + schema + question; free-text answer (Milestone 1 prompt, unchanged) | Starting point | 67% (safety 60%, 4 unsafe requests answered) | 53.3% (1 unsafe request answered) | 13.3% |
| **V2** rules + JSON | Read-only rule, "use only listed tables/columns", `CANNOT_ANSWER`/`UNSAFE` statuses, injection rule, strict JSON output | V1 cannot refuse and its free text is hard to check | **93%** (safety 100%, refusal accuracy 96%) | **93.3%** (safety 100%) | 43.3% |
| **V3** few-shot | + 6 worked examples (4 answers, 1 `CANNOT_ANSWER`, 1 `UNSAFE`), none from the test set | Show *how*: join keys, literals, what a refusal looks like | 93% (refusal accuracy 100%, but 5.3% false refusals) | 93.3% | **66.7%** |
| **V4** plan-first | + a `plan` field (tables, joins, filters, grouping) written before the SQL | Decomposition for multi-join / HAVING questions | 93% (hard: 90%) | 93.3% | 43.3% |
| **V5** value hints | + column descriptions, allowed values and notes (current year, "day scholar", formulas) from `schema_docs.yaml` | Fix wrong literals ('CSE' vs 'B.Tech CSE') and "this year" | 95% (false refusals down to 1.3%, hard: 95%) | **96.7%** (EX 100%) | 43.3% |
| **V5 + SC** (final) | + self-correction prompt P2: on a validator/SQLite error, send the error and SQL back, max 2 retries | Repair errors the model can see once it is told about them | **96%** (EX 94.7%, valid SQL 100%) | 96.7% (no errors left to fix) | 50.0% |

**What we learned.**

- **Biggest single gain:** V1 → V2. Structure and refusal rules took Gemini from 67% to 93%
  and safety from 60% to 100%.
- **Value hints fixed the remaining literal errors.** Gemini had 2 wrong-literal errors in
  V2–V4 and 0 in V5. False refusals also fell from 5.3% to 1.3%.
- **Self-correction fixed a hallucinated column** (Q039, shown in prompt sheet P2). It used
  0.01 retries per question on average, so it costs almost nothing.
- **Long prompts can hurt small models.** For the 3B model, few-shot examples helped most
  (66.7%), but the longer V4/V5 prompts made it worse. The final prompt is tuned for capable
  models.

**Ablation (each technique added to V2 on its own, 30-question subset; table below).**

- **Gemini:** value hints helped most on their own (EX 94.4% → 100%), and plan-first raised
  overall accuracy from 93.3% to 96.7%. Few-shot examples fixed refusals (91.7% → 100%) but
  lowered EX. Self-correction alone changed nothing, because V2's SQL never failed to run.
- **llama3.2:3b:** only few-shot helped (43.3% → 66.7%). Self-correction did retry, twice on
  each failed query, but the 3B model could not repair its own hallucinated columns.
