# Contribution log

One dated line per work session: who did what. Individual contribution is graded, so keep this honest and current.

| Date | Member | Work done |
|---|---|---|
| 2026-11-21 | _(team member)_ with Claude Code | Phase 1: repo setup, `data/schema.sql`, deterministic `data/generate_db.py` (seed 42), `data/schema_docs.yaml`. |
| 2026-11-21 | _(team member)_ with Claude Code | Phase 2: safety layer `querycraft/validator.py` (sqlglot checks) and `querycraft/executor.py` (read-only connection, authorizer, timeout), 41 pytest tests. |
| 2026-11-21 | _(team member)_ with Claude Code | Phase 3: `llm.py` (Gemini + Groq/Ollama, backoff, cache), `parsing.py`, `prompt_builder.py`, `pipeline.py`, V1/V2 prompts, CHANGELOG. Tested end to end on local Ollama `llama3.2:3b`; Gemini path awaiting API key. |
