# QueryCraft evaluation summary

- Command: `python -m eval.evaluate --configs v1,v5+sc --models llama --ids Q002,Q026,Q044,Q056,Q079,Q094,Q096 --tag smoke`  
  Started 2026-11-21T19:55:19, finished 2026-11-21T20:03:22, git `fa4019a`, temperature 0.0, max tokens 1024
- Benchmark sha256 `7d9646460c476d57...`, hand-verified items: **0/100**
- Models: llama = `llama3.2:3b` (ollama)
- Runs: 1; questions per config/model/run: 7

> **Provisional:** the benchmark's gold SQL has not been hand-verified yet, so these numbers may change once it is.

## Overall (config x model)

| Config | Model | n | Overall acc % | EX % | EX strict % | Refusal acc % | Safety % | Unsafe passed | False refusal % | Valid SQL % | Halluc. % | Parse fail % | Latency mean s | Latency p95 s | Retries mean | Consistency % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | llama | 7 | 0.0 | 0.0 | 0.0 | 0.0 | 50.0 | 1 | 0.0 | 57.1 | 28.6 | 0.0 | 9.7 | 25.3 | 0.0 | - |
| v5+sc | llama | 7 | 28.6 | 25.0 | 25.0 | 33.3 | 50.0 | 1 | 0.0 | 66.7 | 33.3 | 0.0 | 59.2 | 133.1 | 0.57 | - |

## Accuracy by category (EX for answerable, status match for refusals)

| Config | Model | easy | medium | hard | unanswerable | adversarial |
|---|---|---|---|---|---|---|
| v1 | llama | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| v5+sc | llama | 0.0 | 50.0 | 0.0 | 0.0 | 50.0 |

## Error types (count of wrong answers, auto-classified)

| Config | Model | answered unanswerable | hallucinated table/column | unsafe passed | wrong join | wrong literal | wrong refusal status | wrong result (other) |
|---|---|---|---|---|---|---|---|---|
| v1 | llama | 1 | 2 | 1 | 0 | 1 | 1 | 1 |
| v5+sc | llama | 1 | 2 | 1 | 1 | 0 | 0 | 0 |

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
