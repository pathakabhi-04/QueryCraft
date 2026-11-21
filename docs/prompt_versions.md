# Prompt versions

| Config | Template | Techniques | Used for |
|---|---|---|---|
| `v1` | `prompts/v1/v1_baseline.txt` | role + schema + question, free text | Milestone 1 baseline |
| `v2` | `prompts/v2/v2_rules_json.txt` | + rules, refusal statuses, JSON output | structure and safety |
| `v3` | `prompts/v3/v3_fewshot.txt` | + 6 examples | example-based prompting (= `v2+fewshot`) |
| `v4` | `prompts/v4/v4_plan_first.txt` | + plan field before SQL | decomposition |
| `v5` | `prompts/final/v5_value_hints.txt` | + column descriptions and allowed values | correct literals, "this year" |
| `v5+sc` | V5 + `prompts/final/fix_error.txt` | + self-correction, max 2 retries | **final configuration** (app default) |
| `v2+plan` | `prompts/ablation/v2_plan.txt` | V2 + plan only | ablation |
| `v2+values` | `prompts/ablation/v2_values.txt` | V2 + value hints only | ablation |
| `v2+sc` | V2 + fix_error | V2 + self-correction only | ablation |

Each version differs from the one before it by exactly one technique; each ablation
template differs from V2 by exactly one technique. Check with
`diff prompts/v2/v2_rules_json.txt prompts/ablation/v2_values.txt`.

- Why each version changed: [`prompts/CHANGELOG.md`](../prompts/CHANGELOG.md)
- Prompt sheets for the two final prompts (P1, P2): [`prompt_sheets.md`](prompt_sheets.md)
- Measured results: `eval/results/<timestamp>/summary.md`
