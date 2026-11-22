# QueryCraft evaluation summary

- Command: `python -m eval.evaluate --configs v1,v2,v3,v4,v5,v5+sc --models gemini --tag gemini-full100`  
  Started 2026-11-22T17:05:52, finished 2026-11-22T17:06:59, git `a0f7c03`, temperature 0.0, max tokens 1024
- Benchmark sha256 `7d9646460c476d57...`, hand-verified items: **0/100**
- Models: `gemini-3.5-flash-lite` (gemini)
- Runs: 1; questions per config/model/run: 100

> **Provisional:** the benchmark's gold SQL has not been hand-verified yet, so these numbers may change once it is.

## Overall (config x model)

| Config | Model | n | Overall acc % | EX % | EX strict % | Refusal acc % | Safety % | Unsafe passed | False refusal % | Valid SQL % | Halluc. % | Parse fail % | Latency mean s | Latency p95 s | Retries mean | Consistency % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | gemini-3.5-flash-lite | 100 | 67.0 | 89.3 | 81.3 | 0.0 | 60.0 | 4 | 0.0 | 92.6 | 1.1 | 5.0 | 1.2 | 2.5 | 0.0 | - |
| v2 | gemini-3.5-flash-lite | 100 | 93.0 | 92.0 | 80.0 | 96.0 | 100.0 | 0 | 4.0 | 100.0 | 0.0 | 0.0 | 2.0 | 7.8 | 0.0 | - |
| v3 | gemini-3.5-flash-lite | 100 | 93.0 | 90.7 | 82.7 | 100.0 | 100.0 | 0 | 5.3 | 100.0 | 0.0 | 0.0 | 3.3 | 9.1 | 0.0 | - |
| v4 | gemini-3.5-flash-lite | 100 | 93.0 | 92.0 | 76.0 | 96.0 | 100.0 | 0 | 5.3 | 100.0 | 0.0 | 0.0 | 3.1 | 9.1 | 0.0 | - |
| v5 | gemini-3.5-flash-lite | 100 | 95.0 | 93.3 | 85.3 | 100.0 | 100.0 | 0 | 1.3 | 98.6 | 1.4 | 0.0 | 3.9 | 10.7 | 0.0 | - |
| v5+sc | gemini-3.5-flash-lite | 100 | 96.0 | 94.7 | 86.7 | 100.0 | 100.0 | 0 | 1.3 | 100.0 | 1.4 | 0.0 | 3.9 | 10.7 | 0.01 | - |

## Accuracy by category (EX for answerable, status match for refusals)

| Config | Model | easy | medium | hard | unanswerable | adversarial |
|---|---|---|---|---|---|---|
| v1 | gemini-3.5-flash-lite | 100.0 | 93.3 | 70.0 | 0.0 | 0.0 |
| v2 | gemini-3.5-flash-lite | 96.0 | 90.0 | 90.0 | 93.3 | 100.0 |
| v3 | gemini-3.5-flash-lite | 92.0 | 90.0 | 90.0 | 100.0 | 100.0 |
| v4 | gemini-3.5-flash-lite | 96.0 | 90.0 | 90.0 | 93.3 | 100.0 |
| v5 | gemini-3.5-flash-lite | 96.0 | 90.0 | 95.0 | 100.0 | 100.0 |
| v5+sc | gemini-3.5-flash-lite | 96.0 | 93.3 | 95.0 | 100.0 | 100.0 |

## Error types (count of wrong answers, auto-classified)

| Config | Model | aggregation error | answered unanswerable | false refusal | hallucinated table/column | invalid SQL (blocked or runtime error) | parse failure | unsafe passed | wrong join | wrong literal | wrong refusal status | wrong result (other) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | gemini-3.5-flash-lite | 2 | 12 | 0 | 0 | 1 | 5 | 4 | 1 | 3 | 4 | 1 |
| v2 | gemini-3.5-flash-lite | 1 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 0 |
| v3 | gemini-3.5-flash-lite | 1 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| v4 | gemini-3.5-flash-lite | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| v5 | gemini-3.5-flash-lite | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| v5+sc | gemini-3.5-flash-lite | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

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
