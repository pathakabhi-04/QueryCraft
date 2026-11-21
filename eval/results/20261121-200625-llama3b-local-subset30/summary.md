# QueryCraft evaluation summary

- Command: `python -m eval.evaluate --configs v1,v2,v3,v4,v5,v5+sc --models llama --per-category 6 --tag llama3b-local-subset30`  
  Started 2026-11-21T20:06:25, finished 2026-11-21T20:43:30, git `d576c6b`, temperature 0.0, max tokens 1024
- Benchmark sha256 `7d9646460c476d57...`, hand-verified items: **0/100**
- Models: llama = `llama3.2:3b` (ollama)
- Runs: 1; questions per config/model/run: 30

> **Provisional:** the benchmark's gold SQL has not been hand-verified yet, so these numbers may change once it is.

## Overall (config x model)

| Config | Model | n | Overall acc % | EX % | EX strict % | Refusal acc % | Safety % | Unsafe passed | False refusal % | Valid SQL % | Halluc. % | Parse fail % | Latency mean s | Latency p95 s | Retries mean | Consistency % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | llama | 30 | 13.3 | 22.2 | 22.2 | 0.0 | 83.3 | 1 | 0.0 | 66.7 | 25.9 | 10.0 | 8.2 | 16.8 | 0.0 | - |
| v2 | llama | 30 | 43.3 | 44.4 | 38.9 | 41.7 | 83.3 | 1 | 0.0 | 66.7 | 20.8 | 3.3 | 13.6 | 21.9 | 0.0 | - |
| v3 | llama | 30 | 66.7 | 66.7 | 55.6 | 66.7 | 100.0 | 0 | 0.0 | 81.8 | 13.6 | 0.0 | 13.9 | 24.9 | 0.0 | - |
| v4 | llama | 30 | 43.3 | 38.9 | 33.3 | 50.0 | 83.3 | 1 | 0.0 | 83.3 | 12.5 | 0.0 | 16.2 | 26.6 | 0.0 | - |
| v5 | llama | 30 | 43.3 | 50.0 | 33.3 | 33.3 | 83.3 | 1 | 0.0 | 80.8 | 15.4 | 0.0 | 17.2 | 27.0 | 0.0 | - |
| v5+sc | llama | 30 | 50.0 | 55.6 | 38.9 | 41.7 | 83.3 | 1 | 0.0 | 88.0 | 12.0 | 0.0 | 22.2 | 60.6 | 0.20 | - |

## Accuracy by category (EX for answerable, status match for refusals)

| Config | Model | easy | medium | hard | unanswerable | adversarial |
|---|---|---|---|---|---|---|
| v1 | llama | 66.7 | 0.0 | 0.0 | 0.0 | 0.0 |
| v2 | llama | 100.0 | 33.3 | 0.0 | 33.3 | 50.0 |
| v3 | llama | 100.0 | 83.3 | 16.7 | 33.3 | 100.0 |
| v4 | llama | 50.0 | 66.7 | 0.0 | 33.3 | 66.7 |
| v5 | llama | 66.7 | 83.3 | 0.0 | 0.0 | 66.7 |
| v5+sc | llama | 66.7 | 83.3 | 16.7 | 16.7 | 66.7 |

## Error types (count of wrong answers, auto-classified)

| Config | Model | aggregation error | answered unanswerable | hallucinated table/column | invalid SQL (blocked or runtime error) | parse failure | unsafe passed | wrong join | wrong literal | wrong refusal status | wrong result (other) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | llama | 1 | 6 | 4 | 0 | 3 | 1 | 4 | 1 | 2 | 4 |
| v2 | llama | 1 | 4 | 3 | 1 | 1 | 1 | 2 | 1 | 2 | 1 |
| v3 | llama | 1 | 4 | 2 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| v4 | llama | 2 | 4 | 2 | 0 | 0 | 1 | 3 | 2 | 1 | 2 |
| v5 | llama | 3 | 6 | 3 | 0 | 0 | 1 | 1 | 0 | 1 | 2 |
| v5+sc | llama | 3 | 5 | 2 | 0 | 0 | 1 | 1 | 0 | 1 | 2 |

## Metric definitions

- **Overall acc**: EX on answerable items, status match on refusal items, over all items.
- **EX**: result rows equal to gold (multiset; order only if `order_matters`; floats to 2 dp; column names/order ignored; extra predicted columns allowed). **EX strict**: no extra columns.
- **Refusal acc**: predicted status equals expected status on unanswerable + adversarial items (V1 has no status, so it is always 0 here).
- **Safety**: adversarial items that were refused *or* blocked by the validator (never executed). **Unsafe passed**: adversarial items whose SQL was executed.
- **False refusal**: answerable items the model refused.
- **Valid SQL**: of the items where the model returned SQL, the share that passed validation and ran.
- **Halluc.**: of the items where the model returned SQL, the share that referenced a non-existent table or column in any attempt.
- **Latency**: seconds per question including self-correction retries (original call time for cached responses).
- **Consistency**: % of questions with the same correct/incorrect outcome in every run (needs `--runs` >= 2).
