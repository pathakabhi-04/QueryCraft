# QueryCraft evaluation summary

- Command: `python -m eval.evaluate --configs v2,v2+fewshot,v2+plan,v2+values,v2+sc --models llama --per-category 6 --tag llama3b-local-ablation30`  
  Started 2026-11-21T23:12:40, finished 2026-11-21T23:28:58, git `a0f7c03`, temperature 0.0, max tokens 1024
- Benchmark sha256 `7d9646460c476d57...`, hand-verified items: **0/100**
- Models: `llama3.2:3b` (ollama)
- Runs: 1; questions per config/model/run: 30

> **Provisional:** the benchmark's gold SQL has not been hand-verified yet, so these numbers may change once it is.

## Overall (config x model)

| Config | Model | n | Overall acc % | EX % | EX strict % | Refusal acc % | Safety % | Unsafe passed | False refusal % | Valid SQL % | Halluc. % | Parse fail % | Latency mean s | Latency p95 s | Retries mean | Consistency % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v2 | llama3.2:3b | 30 | 43.3 | 44.4 | 38.9 | 41.7 | 83.3 | 1 | 0.0 | 66.7 | 20.8 | 3.3 | 13.6 | 21.9 | 0.0 | - |
| v2+fewshot | llama3.2:3b | 30 | 66.7 | 66.7 | 55.6 | 66.7 | 100.0 | 0 | 0.0 | 81.8 | 13.6 | 0.0 | 13.9 | 24.9 | 0.0 | - |
| v2+plan | llama3.2:3b | 30 | 43.3 | 50.0 | 50.0 | 33.3 | 83.3 | 1 | 0.0 | 76.9 | 11.5 | 0.0 | 12.0 | 23.3 | 0.0 | - |
| v2+values | llama3.2:3b | 30 | 43.3 | 44.4 | 44.4 | 41.7 | 83.3 | 1 | 0.0 | 79.2 | 12.5 | 3.3 | 11.6 | 20.4 | 0.0 | - |
| v2+sc | llama3.2:3b | 30 | 43.3 | 44.4 | 38.9 | 41.7 | 83.3 | 1 | 0.0 | 66.7 | 20.8 | 3.3 | 20.5 | 48.9 | 0.40 | - |

## Accuracy by category (EX for answerable, status match for refusals)

| Config | Model | easy | medium | hard | unanswerable | adversarial |
|---|---|---|---|---|---|---|
| v2 | llama3.2:3b | 100.0 | 33.3 | 0.0 | 33.3 | 50.0 |
| v2+fewshot | llama3.2:3b | 100.0 | 83.3 | 16.7 | 33.3 | 100.0 |
| v2+plan | llama3.2:3b | 83.3 | 50.0 | 16.7 | 16.7 | 50.0 |
| v2+values | llama3.2:3b | 83.3 | 50.0 | 0.0 | 33.3 | 50.0 |
| v2+sc | llama3.2:3b | 100.0 | 33.3 | 0.0 | 33.3 | 50.0 |

## Error types (count of wrong answers, auto-classified)

| Config | Model | aggregation error | answered unanswerable | hallucinated table/column | invalid SQL (blocked or runtime error) | parse failure | unsafe passed | wrong join | wrong literal | wrong refusal status | wrong result (other) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v2 | llama3.2:3b | 1 | 4 | 3 | 1 | 1 | 1 | 2 | 1 | 2 | 1 |
| v2+fewshot | llama3.2:3b | 1 | 4 | 2 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| v2+plan | llama3.2:3b | 0 | 5 | 1 | 1 | 0 | 1 | 3 | 0 | 2 | 4 |
| v2+values | llama3.2:3b | 2 | 4 | 2 | 0 | 1 | 1 | 2 | 2 | 2 | 1 |
| v2+sc | llama3.2:3b | 1 | 4 | 3 | 1 | 1 | 1 | 2 | 1 | 2 | 1 |

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
