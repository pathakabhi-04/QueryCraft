# QueryCraft: natural language to SQL for university administration

University admin staff (fees, exams, hostel and admissions offices) need data reports
but can't write SQL. QueryCraft lets them ask in plain English, and returns:

1. a **read-only** SQL query,
2. the query result,
3. a plain-English explanation,

or a polite refusal when the question is unsafe or can't be answered from the database.

Prompt Engineering mini project (SCSE4041, Bennett University, problem C8).

| | |
|---|---|
| Team | QueryCraft |
| Members | _[Name, S24CSEU....]_ · _[Name, S24CSEU....]_ |
| Prototype | https://querycraft-cjf4babjadx8okkxnej8dm.streamlit.app/ |
| Reel | _[Drive / unlisted YouTube link]_ |

All data is **synthetic** (Faker, seed 42). No real student data is used anywhere.

## How it works

```
question ─► prompt P1 (schema + column hints + examples) ─► LLM ─► JSON {plan, status, sql, explanation, ...}
        ─► validator (sqlglot: one SELECT, known tables/columns) ─► read-only SQLite (timeout, LIMIT 500)
        ─► on error: prompt P2 (fix_error), max 2 retries ─► answer / refusal
```

Diagrams: [`docs/architecture.md`](docs/architecture.md) (PNG versions in `docs/diagrams/`).
Prompt versions and why each changed: [`prompts/CHANGELOG.md`](prompts/CHANGELOG.md),
[`docs/prompt_versions.md`](docs/prompt_versions.md).

## Run it

Requires Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # add GEMINI_API_KEY and/or GROQ_API_KEY, check model names
python data/generate_db.py      # builds data/university.db (deterministic, seed 42)
python -m querycraft.llm --list-models    # confirm the model names your keys can use

streamlit run app/streamlit_app.py                                  # the app
python -m querycraft.pipeline "How many day scholars are there?" --config v5+sc --model gemini
```

Models used: `gemini-3.5-flash-lite` (Google AI Studio) and the open-weight
`openai/gpt-oss-120b` (Groq). Groq has retired its Llama chat models; to run Llama, install
[Ollama](https://ollama.com), `ollama pull llama3.2:3b`, and set `LLAMA_BACKEND=ollama`,
`LLAMA_MODEL=llama3.2:3b` in `.env`. The `llama` model slot in the code is the open-model slot.

### Deploy the prototype (Streamlit Community Cloud)

1. Push this repo to GitHub (public). Make sure `.env` is **not** committed (it is in `.gitignore`).
2. On share.streamlit.io: *New app* → this repo → main file `app/streamlit_app.py`,
   Python 3.12 (Advanced settings).
3. In *Secrets*, add (TOML):
   ```toml
   GEMINI_API_KEY = "..."
   GEMINI_MODEL = "..."
   LLAMA_BACKEND = "groq"
   GROQ_API_KEY = "..."
   LLAMA_MODEL = "..."
   ```
4. The app builds the synthetic database itself on first start. Test the link in a private window.

## Evaluation (reproducible)

```bash
python -m pytest                                     # safety layer, parsing, metrics, prompts
python -m benchmark.check_gold                       # every gold query runs; category counts; hash
python -m eval.evaluate --configs v2 --models gemini --limit 10          # smoke test
python -m eval.evaluate --configs v1,v2,v3,v4,v5,v5+sc --models gemini,llama --runs 3   # cumulative
python -m eval.evaluate --configs v2,v2+fewshot,v2+plan,v2+values,v2+sc --models gemini,llama  # ablation
python -m eval.run_tests --config v5+sc --model gemini                     # M2 test table
```

Each evaluation writes `eval/results/<timestamp>/` with `meta.json` (exact model names,
temperature, benchmark hash, git commit), `raw.jsonl` (every call), `summary.md/.csv`,
`failures.md` and `charts/`. Every reported number comes from these files.
Temperature is 0 for all runs; API responses are cached in `eval/cache/` so reruns are free.

To reproduce a result: same git commit, `python data/generate_db.py` (check the printed
fingerprint), same `.env` model names, then the command recorded in `meta.json`.

## Repository layout

| Path | What |
|---|---|
| `prompts/v1/ … v4/` | older prompt versions (V1 is the Milestone 1 prompt, unchanged) |
| `prompts/final/` | final prompts: `v5_value_hints.txt` (P1, generation), `fix_error.txt` (P2, self-correction) |
| `prompts/ablation/` | V2 + one technique, for the ablation study |
| `prompts/fewshot_examples.yaml` | worked examples (not taken from the test set) |
| `prompts/CHANGELOG.md` | what changed in each prompt version and why |
| `querycraft/` | code: config, LLM interface, prompt builder, pipeline, validator, executor, parsing |
| `app/` | Streamlit app |
| `data/` | schema, deterministic data generator, column descriptions / allowed values |
| `benchmark/` | 100-question benchmark with gold SQL + checker |
| `eval/` | evaluation harness, metrics, reports, test-table runner; `eval/results/` holds runs |
| `test-data/` | Milestone 2 test inputs, saved outputs and test tables |
| `docs/` | architecture diagrams, prompt sheets, Milestone 2 report draft, contribution log |
| `tests/` | pytest suite |
| `CHANGELOG.md` | dated list of changes since Milestone 1 |

## Safety

Safety is enforced in **code**, not only in prompts: sqlglot validation (exactly one
SELECT; no INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/ATTACH/PRAGMA/REPLACE anywhere; only
existing tables/columns), a read-only SQLite connection (`mode=ro`, `query_only`,
an authorizer that only allows reads), a 5-second timeout and a 500-row limit. Only the
schema, column descriptions and category values are sent to the model, never table rows.
Results are for decision support; staff should verify before acting.
