#### Prompt sheet P1: SQL generation (final version V5, value hints)

| Field | Value |
|---|---|
| Prompt ID and name | **P1**: QueryCraft SQL generation (`prompts/final/v5_value_hints.txt`) |
| Step in the workflow | Step 1, run for every question |
| Purpose | Turn a staff question into one read-only SQLite query plus a plain-English explanation, or refuse it |
| Tool and model | Gemini **[[TEAM: exact model id, e.g. from `python -m querycraft.llm --list-models`]]** via Google AI Studio API (`google-genai` SDK); Llama **[[TEAM: exact id]]** via Groq (OpenAI-compatible API). Local testing: `llama3.2:3b` via Ollama. Identical prompt text for every model. |
| Settings | temperature 0; max output tokens 1024; Ollama context 8192 tokens; one user message |
| System prompt | none (the whole prompt is one user message, so it is identical across providers) |
| Examples included | 6 (4 answered, 1 `CANNOT_ANSWER`, 1 `UNSAFE`), from `prompts/fewshot_examples.yaml`, none taken from the test set |
| Output format | JSON only: `plan`, `status` (`OK` / `CANNOT_ANSWER` / `UNSAFE`), `sql`, `explanation`, `assumptions` (list), `confidence` (`high` / `medium` / `low`) |

**Variables**

| Variable | What it holds |
|---|---|
| `{schema}` | The 8 `CREATE TABLE` statements of `data/schema.sql` (comments removed) |
| `{value_hints}` | From `data/schema_docs.yaml`: notes (current academic year '2026-27', day scholar = no hostel, attendance % and dues formulas), one-line description of every column, and the allowed values of category columns (programme names, hostel names, fee status, grades, academic years). No table rows. |
| `{examples}` | The 6 worked examples, each as `Question: …` followed by the JSON answer (with `plan`) |
| `{question}` | The staff member's question, exactly as typed |

**User prompt template (full text)**

<!-- include-code: prompts/final/v5_value_hints.txt -->

**The 6 examples (source of `{examples}`)**

<!-- include-code: prompts/fewshot_examples.yaml -->

**Sample run (real input and actual output)**

<!-- include-md: docs/sample_run_p1.md -->

#### Prompt sheet P2: self-correction (fix error)

| Field | Value |
|---|---|
| Prompt ID and name | **P2**: QueryCraft SQL repair (`prompts/final/fix_error.txt`) |
| Step in the workflow | Step 2, only when the SQL from P1 (or a previous P2) is blocked by the validator or fails in SQLite; at most 2 times per question. Never used for blocked write attempts. |
| Purpose | Repair a failed query using the exact error message (execution feedback) |
| Tool and model | Same model as P1 for that question |
| Settings | temperature 0; max output tokens 1024; one user message |
| System prompt | none |
| Examples included | 0 |
| Output format | JSON only: `status`, `sql`, `explanation`, `assumptions`, `confidence` |

**Variables**

| Variable | What it holds |
|---|---|
| `{schema}` | Same as P1 |
| `{value_hints}` | Same as P1 (in configs that use value hints; otherwise "(none)") |
| `{question}` | The original question |
| `{previous_sql}` | The SQL that failed |
| `{error}` | The validator's reason (e.g. `Unknown column(s): s.status.`) or the SQLite error message |

**User prompt template (full text)**

<!-- include-code: prompts/final/fix_error.txt -->

**Sample run (real input and actual output)**

<!-- include-md: docs/sample_run_p2.md -->
