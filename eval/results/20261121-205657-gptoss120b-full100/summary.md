# QueryCraft evaluation summary

- Command: `python -m eval.evaluate --configs v1,v2,v3,v4,v5,v5+sc --models llama --tag gptoss120b-full100`  
  Started 2026-11-21T20:56:57, finished -, git `fa5fd24`, temperature 0.0, max tokens 1024
- Benchmark sha256 `7d9646460c476d57...`, hand-verified items: **0/100**
- Models: `openai/gpt-oss-120b` (groq)
- Runs: 1; questions per config/model/run: 100

> **Provisional:** the benchmark's gold SQL has not been hand-verified yet, so these numbers may change once it is.

## Overall (config x model)

| Config | Model | n | Overall acc % | EX % | EX strict % | Refusal acc % | Safety % | Unsafe passed | False refusal % | Valid SQL % | Halluc. % | Parse fail % | Latency mean s | Latency p95 s | Retries mean | Consistency % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | openai/gpt-oss-120b | 100 | 67.0 | 89.3 | 72.0 | 0.0 | 80.0 | 2 | 0.0 | 88.5 | 1.0 | 4.0 | 0.76 | 1.3 | 0.0 | - |
| v2 | openai/gpt-oss-120b | 100 | 89.0 | 85.3 | 73.3 | 100.0 | 100.0 | 0 | 5.3 | 94.4 | 5.6 | 0.0 | 0.78 | 1.2 | 0.0 | - |
| v3 | openai/gpt-oss-120b | 100 | 95.0 | 94.7 | 81.3 | 96.0 | 100.0 | 0 | 0.0 | 97.3 | 2.7 | 0.0 | 0.76 | 1.3 | 0.0 | - |
| v4 | openai/gpt-oss-120b | 29 | 72.4 | 72.4 | 72.4 | - | - | 0 | 3.4 | 100.0 | 0.0 | 0.0 | 0.70 | 1.9 | 0.0 | - |

## Accuracy by category (EX for answerable, status match for refusals)

| Config | Model | easy | medium | hard | unanswerable | adversarial |
|---|---|---|---|---|---|---|
| v1 | openai/gpt-oss-120b | 100.0 | 90.0 | 75.0 | 0.0 | 0.0 |
| v2 | openai/gpt-oss-120b | 92.0 | 90.0 | 70.0 | 100.0 | 100.0 |
| v3 | openai/gpt-oss-120b | 96.0 | 100.0 | 85.0 | 93.3 | 100.0 |
| v4 | openai/gpt-oss-120b | 76.0 | 50.0 | - | - | - |

## Error types (count of wrong answers, auto-classified)

| Config | Model | aggregation error | answered unanswerable | api error | false refusal | hallucinated table/column | invalid SQL (blocked or runtime error) | parse failure | unsafe passed | wrong join | wrong literal | wrong refusal status | wrong result (other) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | openai/gpt-oss-120b | 0 | 15 | 0 | 0 | 1 | 5 | 4 | 2 | 0 | 2 | 4 | 0 |
| v2 | openai/gpt-oss-120b | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 1 | 1 | 0 | 0 |
| v3 | openai/gpt-oss-120b | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 1 | 1 |
| v4 | openai/gpt-oss-120b | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

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
