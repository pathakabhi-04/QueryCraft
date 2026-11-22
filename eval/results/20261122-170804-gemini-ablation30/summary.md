# QueryCraft evaluation summary

- Command: `python -m eval.evaluate --configs v2,v2+fewshot,v2+plan,v2+values,v2+sc --models gemini --per-category 6 --tag gemini-ablation30`  
  Started 2026-11-22T17:08:04, finished 2026-11-22T17:13:07, git `a0f7c03`, temperature 0.0, max tokens 1024
- Benchmark sha256 `7d9646460c476d57...`, hand-verified items: **0/100**
- Models: `gemini-3.5-flash-lite` (gemini)
- Runs: 1; questions per config/model/run: 30

> **Provisional:** the benchmark's gold SQL has not been hand-verified yet, so these numbers may change once it is.

## Overall (config x model)

| Config | Model | n | Overall acc % | EX % | EX strict % | Refusal acc % | Safety % | Unsafe passed | False refusal % | Valid SQL % | Halluc. % | Parse fail % | Latency mean s | Latency p95 s | Retries mean | Consistency % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v2 | gemini-3.5-flash-lite | 30 | 93.3 | 94.4 | 77.8 | 91.7 | 100.0 | 0 | 0.0 | 100.0 | 0.0 | 0.0 | 1.9 | 9.2 | 0.0 | - |
| v2+fewshot | gemini-3.5-flash-lite | 30 | 93.3 | 88.9 | 83.3 | 100.0 | 100.0 | 0 | 5.6 | 100.0 | 0.0 | 0.0 | 3.4 | 9.4 | 0.0 | - |
| v2+plan | gemini-3.5-flash-lite | 30 | 96.7 | 94.4 | 83.3 | 100.0 | 100.0 | 0 | 0.0 | 100.0 | 0.0 | 0.0 | 2.5 | 7.3 | 0.0 | - |
| v2+values | gemini-3.5-flash-lite | 30 | 96.7 | 100.0 | 88.9 | 91.7 | 100.0 | 0 | 0.0 | 100.0 | 0.0 | 0.0 | 3.0 | 10.2 | 0.0 | - |
| v2+sc | gemini-3.5-flash-lite | 30 | 93.3 | 94.4 | 77.8 | 91.7 | 100.0 | 0 | 0.0 | 100.0 | 0.0 | 0.0 | 1.9 | 9.2 | 0.0 | - |

## Accuracy by category (EX for answerable, status match for refusals)

| Config | Model | easy | medium | hard | unanswerable | adversarial |
|---|---|---|---|---|---|---|
| v2 | gemini-3.5-flash-lite | 100.0 | 100.0 | 83.3 | 83.3 | 100.0 |
| v2+fewshot | gemini-3.5-flash-lite | 83.3 | 100.0 | 83.3 | 100.0 | 100.0 |
| v2+plan | gemini-3.5-flash-lite | 100.0 | 100.0 | 83.3 | 100.0 | 100.0 |
| v2+values | gemini-3.5-flash-lite | 100.0 | 100.0 | 100.0 | 83.3 | 100.0 |
| v2+sc | gemini-3.5-flash-lite | 100.0 | 100.0 | 83.3 | 83.3 | 100.0 |

## Error types (count of wrong answers, auto-classified)

| Config | Model | false refusal | wrong literal | wrong refusal status |
|---|---|---|---|---|
| v2 | gemini-3.5-flash-lite | 0 | 1 | 1 |
| v2+fewshot | gemini-3.5-flash-lite | 1 | 1 | 0 |
| v2+plan | gemini-3.5-flash-lite | 0 | 1 | 0 |
| v2+values | gemini-3.5-flash-lite | 0 | 0 | 1 |
| v2+sc | gemini-3.5-flash-lite | 0 | 1 | 1 |

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
