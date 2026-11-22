# Saved evaluation runs

Runs used in the Milestone 2 report:

| Folder | What |
|---|---|
| `20261122-170552-gemini-full100/` | Gemini, all 100 questions × V1–V5+SC (complete, 0 API errors) |
| `20261122-170552-gptoss120b-subset30/` | gpt-oss-120b, 30-question subset × V1–V5+SC |
| `20261121-205657-gptoss120b-full100/` | gpt-oss-120b, all 100 questions; complete for V1–V3 only (Groq daily token limit hit during V4) |
| `20261121-200625-llama3b-local-subset30/` | llama3.2:3b (local), subset × V1–V5+SC |
| `20261122-170804-gemini-ablation30/`, `20261121-231240-llama3b-local-ablation30/` | Ablation: V2 + one technique |
| `M2-cumulative/`, `M2-ablation/` | Combined tables and charts made by `python -m eval.compare <dirs> --out <dir>` |

Superseded, kept for transparency: `20261121-205657-gemini-full100/` (25 answers lost to the
Gemini daily quota, re-run the next day as `20261122-170552-gemini-full100/` from the same cache)
and `20261121-220522-gemini-ablation30/` (48 quota errors, re-run as `20261122-170804-...`).
