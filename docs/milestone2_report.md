# QueryCraft: Natural Language to SQL for University Administration

## 1. Cover page

| | |
|---|---|
| Team ID | PE-B65-03 |
| Team name | QueryCraft |
| Project title | QueryCraft: Natural Language to SQL for University Administration |
| Course | SCSE4041 Prompt Engineering, Mini Project, Milestone 2 |
| Batch | B65-80 |
| Faculty | Sonal Kukreja |
| Members | Ishita Bora, S24CSEU2463 (team leader)<br>Abhinav Pathak, S24CSEU0906 |
| Prototype link | https://querycraft-cjf4babjadx8okkxnej8dm.streamlit.app/ |
| Repository link | https://github.com/pathakabhi-04/QueryCraft |
| Reel link | https://drive.google.com/file/d/1nCc2luihXJs-TLOAySsXdQHPGCMwFz9h/view?usp=sharing (length: 150 s) |

**Counts used in the form:** final prompts **2** (P1, P2) · test inputs **14** · prompt versions **6** (V1, V2, V3, V4, V5, V5+SC)

## 2. Prompt and solution design

### (a) Design summary

**Problem and users.** Staff in a university's fee, exam, hostel and admissions offices need
numbers and lists ("fee defaulters this year", "students under 75% attendance") but cannot
write SQL, so every report waits for the IT team. QueryCraft lets them ask in plain English.

**Input and output.** Input: one question in informal English, the way office staff write it
("day scholars", "dues", ₹, "this semester"), plus a model and prompt-version choice in the
app. Output: a one-to-two sentence explanation, the result table, the SQL (hidden by default),
the assumptions made and a confidence level, or a clear refusal: `UNSAFE` (requests to change
data, prompt injection, bulk export of personal data) or `CANNOT_ANSWER` (data not stored).

**Prompts and steps.** The final solution uses **two prompts**. **P1** (generation) does the
whole language task in one call. It returns JSON with a `plan` (tables, joins, filters,
grouping), a `status`, the `sql`, an `explanation`, `assumptions` and `confidence`. Putting the
plan inside the same call gives the benefit of decomposition without a second LLM call, which
matters on free-tier rate limits. **P2** (self-correction) is called only when the SQL fails
validation or execution: it receives the previous SQL and the exact error, at most twice.
Parsing, validation and execution are done in **code, not prompts**, because safety cannot
depend on the model obeying instructions: a sqlglot validator allows exactly one SELECT on
known tables and columns, and the query runs on a read-only SQLite connection with a timeout
and a row limit.

**Tools and models.** Python, SQLite with synthetic data (Faker, seed 42), sqlglot, Streamlit.
Model A: **`gemini-3.5-flash-lite`** via the Google AI Studio API: free tier, about 3 s per
answer (the full `gemini-3.5-flash` took 35–75 s per call during our runs). Model B: the
open-weight **`openai/gpt-oss-120b`** via the Groq API. We planned Llama on Groq, but Groq has
retired its Llama chat models; Meta's **`llama3.2:3b`** still runs locally via Ollama as a third,
small open model. All models get identical prompts at temperature 0, with hidden "thinking"
kept minimal: with it on, Gemini spent 982 of its 1024 output tokens thinking and cut its
JSON answer off. Only the schema, column descriptions and category values are sent to a
model, never table rows.

**Changes since Milestone 1.** Milestone 1 had only the V1 prompt (role + schema + question,
free-text answer). Since then we built the database, the code-level safety layer, four new
prompt versions (rules + JSON, few-shot, plan-first, value hints), the self-correction loop,
a 100-question benchmark, an evaluation harness and the Streamlit prototype.

### (b) Diagrams

All diagrams were drawn from the actual code (`docs/architecture.md`).

**Prompt workflow** (final configuration, V5 + self-correction):

![Prompt workflow](diagrams/02_prompt_workflow.png)

**Task decomposition** (blue: done by the model; orange: enforced in code):

![Task decomposition](diagrams/03_task_decomposition.png)

**Input–output flow:**

![Input-output flow](diagrams/04_input_output_flow.png)

**System architecture:**

![System architecture](diagrams/01_system_architecture.png)

**Agent loop: self-correction:**

![Self-correction loop](diagrams/05_self_correction_loop.png)

### (c) Prompt sheets

<!-- include-md: docs/prompt_sheets.md -->

## 3. Implementation

### What is built

A working NL-to-SQL assistant: a Streamlit app on top of a Python pipeline
(`querycraft/`) that builds the prompt, calls Gemini, gpt-oss or Llama, parses the JSON answer,
validates the SQL, runs it read-only, self-corrects on errors and shows the result. Around
it: a deterministic synthetic university database, a 100-question benchmark, an evaluation
harness that measures every prompt version, and a pytest suite (92 tests).

### Module status

| Module | What it does | Status | Notes |
|---|---|---|---|
| Synthetic university database | Builds `university.db` (8 tables, 500 students) from seed 42 | Working | Same seed gives an identical DB (checked by fingerprint) |
| SQL safety layer | Validator (one SELECT, no writes/PRAGMA/ATTACH, known tables/columns, LIMIT 500) + read-only executor with timeout | Working | 47 pytest tests |
| LLM interface | One function for Gemini, Groq and Ollama models; rate-limit backoff, caching | Working | Tested end to end with gemini-3.5-flash-lite, gpt-oss-120b and llama3.2:3b |
| Prompt builder | Fills V1–V5, ablation and fix-error templates | Working | Tests check every config fills all placeholders |
| NL-to-SQL pipeline with self-correction | Question → prompt → LLM → JSON → validate → execute → fix loop (max 2) | Working | |
| Streamlit app | Question box, model/version selectors, explanation, table, SQL, refusals | Working | Deployed on Streamlit Community Cloud: https://querycraft-cjf4babjadx8okkxnej8dm.streamlit.app/ |
| Benchmark | 100 questions with gold SQL across 5 categories | Working | All 100 gold queries run (`benchmark/check_gold.py`); hand verification of the gold SQL is pending |
| Evaluation harness | Runs configs × models × questions; metrics, summary, failure list, charts | Working | |
| Test-table runner | Runs the 14 test inputs, saves outputs, writes the test table | Working | |

### Prompt iteration log

The gold SQL is **not yet hand-verified**, so all numbers are provisional. Each number comes
from a saved run of `eval/evaluate.py`; the folder is given with each table.

<!-- include-md: docs/iteration_log.md -->

#### Ablation: one technique at a time on top of V2

The question here is which technique helps *on its own*. Each row is V2 plus exactly one
technique, on the 30-question subset (`eval/results/M2-ablation/`, combining
`20261122-170804-gemini-ablation30` and `20261121-231240-llama3b-local-ablation30`).

<!-- include-md: eval/results/M2-ablation/summary.md#Overall (config x model) -->

![Ablation](../eval/results/M2-ablation/charts/ablation.png)

#### All metrics, cumulative versions

Combined from the three cumulative runs above (`eval/results/M2-cumulative/`). The `n` column
shows how many questions each row was measured on.

<!-- include-md: eval/results/M2-cumulative/summary.md#Overall (config x model) -->

<!-- include-md: eval/results/M2-cumulative/summary.md#Accuracy by category (EX for answerable, status match for refusals) -->

![Accuracy by version](../eval/results/M2-cumulative/charts/accuracy_by_version.png)

![Safety](../eval/results/M2-cumulative/charts/safety.png)

#### Full text of each version

Variables in curly brackets are filled by `querycraft/prompt_builder.py` (see the prompt sheets).

**V1 baseline** (`prompts/v1/v1_baseline.txt`, unchanged since Milestone 1)

<!-- include-code: prompts/v1/v1_baseline.txt -->

**V2 rules + JSON** (`prompts/v2/v2_rules_json.txt`)

<!-- include-code: prompts/v2/v2_rules_json.txt -->

**V3 few-shot** (`prompts/v3/v3_fewshot.txt`) = V2 + examples block

<!-- include-code: prompts/v3/v3_fewshot.txt -->

**V4 plan-first** (`prompts/v4/v4_plan_first.txt`) = V3 + rule 7 + `plan` field

<!-- include-code: prompts/v4/v4_plan_first.txt -->

**V5 value hints**: the final prompt P1, printed in full in the prompt sheet above
(`prompts/final/v5_value_hints.txt`) = V4 + column descriptions/allowed values + rule 8.

**V5 + SC**: V5 plus the self-correction prompt P2 (`prompts/final/fix_error.txt`), also printed above.

## 4. Demonstration and testing

### Test table

<!-- include-md: docs/test_table_section.md -->

### Screenshots of real runs

<!-- include-md: docs/screenshots_section.md -->

### Known limitations and what we will try next

<!-- include-md: docs/limitations.md -->

## 5. Repository

Repository: https://github.com/pathakabhi-04/QueryCraft (public).

![GitHub repository](screenshots/github_repo.png)

What changed since Milestone 1:

- Went from a single prompt (V1) to six measured versions (V1–V5, V5+SC), each in its own
  folder (`prompts/v1..v4/`, `prompts/final/`), with reasons in `prompts/CHANGELOG.md`.
- Added the working code: safety layer, LLM interface, pipeline with self-correction,
  Streamlit app (`querycraft/`, `app/`), with 92 automated tests (`tests/`).
- Added a synthetic database, a 100-question benchmark and an evaluation harness whose
  saved results are in `eval/results/`; test inputs and saved outputs are in `test-data/`.
- Diagrams and this report are in `docs/`; every change is dated in `CHANGELOG.md` and in the
  commit history.

## 6. Supporting document

<!-- include-md: docs/research_abstract.md -->

## 7. Team contribution

| Member name | Enrollment no. | Role | Tasks done in Milestone 2 | Evidence | Contribution (%) |
|---|---|---|---|---|---|
| Ishita Bora (team leader) | S24CSEU2463 | Safety layer, app & prompt experiments | Built the SQL safety layer (validator + read-only executor) and the Streamlit app and its deployment; ran the ablation study (V2 + one technique at a time) and the prompt experiments on local Llama 3.2 3B; ran the 14-input test table, took the screenshots and recorded the demo reel | `querycraft/validator.py`, `querycraft/executor.py`, `app/streamlit_app.py`, `eval/results/*ablation30`, `eval/results/*llama3b*`, `test-data/`, prototype link, reel, Section 4 | 50 |
| Abhinav Pathak | S24CSEU0906 | Prompt design & evaluation | Wrote prompt versions V1–V5 and the self-correction prompt, the few-shot examples and the prompt changelog; ran the cumulative evaluations on Gemini and gpt-oss-120b and wrote the iteration log | `prompts/` (all versions, `prompts/CHANGELOG.md`), `prompts/fewshot_examples.yaml`, `eval/results/*full100`, `eval/results/*gptoss*`, `docs/iteration_log.md`, Sections 2(c) and 3 | 50 |

Percentages must add up to 100. Every member must be able to explain the files they list.
All members have agreed to this table: **Yes** (Ishita Bora, Abhinav Pathak).
