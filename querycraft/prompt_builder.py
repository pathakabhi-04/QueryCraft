"""Assemble the exact prompt text for a config + question.

A *config* is a template file plus the techniques that fill its slots.
Templates use these placeholders (filled with plain str.replace, so the JSON
braces in the templates need no escaping):

    {schema}       CREATE TABLE statements from data/schema.sql (comments removed)
    {examples}     few-shot examples from prompts/fewshot_examples.yaml
    {value_hints}  column descriptions + allowed values from data/schema_docs.yaml
    {question}     the user's question (filled last, so it cannot inject placeholders)

Cumulative configs:  v1 -> v2 -> v3 -> v4 -> v5 -> v5+sc
Ablations (one technique on top of v2): v2+fewshot (== v3 by design), v2+plan,
v2+values, v2+sc.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from querycraft.config import PROMPTS_DIR, SCHEMA_DOCS_PATH, SCHEMA_SQL_PATH


@dataclass(frozen=True)
class PromptConfig:
    name: str
    template: str                 # path relative to prompts/
    fewshot: bool = False         # fill {examples}
    plan: bool = False            # examples include the "plan" field
    values: bool = False          # fill {value_hints}
    self_correct: bool = False    # pipeline runs the fix_error loop
    json_output: bool = True      # False only for V1 (free text)

    @property
    def prompt_version(self) -> str:
        return self.template.removesuffix(".txt")


CONFIGS = {c.name: c for c in [
    # cumulative
    PromptConfig("v1", "v1_baseline.txt", json_output=False),
    PromptConfig("v2", "v2_rules_json.txt"),
    PromptConfig("v3", "v3_fewshot.txt", fewshot=True),
    PromptConfig("v4", "v4_plan_first.txt", fewshot=True, plan=True),
    PromptConfig("v5", "v5_value_hints.txt", fewshot=True, plan=True, values=True),
    PromptConfig("v5+sc", "v5_value_hints.txt", fewshot=True, plan=True, values=True,
                 self_correct=True),
    # ablations: exactly one technique added to v2
    PromptConfig("v2+fewshot", "v3_fewshot.txt", fewshot=True),
    PromptConfig("v2+plan", "ablation/v2_plan.txt", plan=True),
    PromptConfig("v2+values", "ablation/v2_values.txt", values=True),
    PromptConfig("v2+sc", "v2_rules_json.txt", self_correct=True),
]}

FIX_ERROR_TEMPLATE = "fix_error.txt"


def get_config(name: str) -> PromptConfig:
    try:
        return CONFIGS[name]
    except KeyError:
        raise ValueError(f"Unknown config {name!r}. Known: {', '.join(CONFIGS)}") from None


@lru_cache(maxsize=None)
def load_template(rel_path: str) -> str:
    return (PROMPTS_DIR / rel_path).read_text()


@lru_cache(maxsize=1)
def schema_text() -> str:
    """The schema as the model sees it: CREATE TABLE statements, no comments."""
    lines = []
    for line in SCHEMA_SQL_PATH.read_text().splitlines():
        line = line.split("--")[0].rstrip()
        if line and not line.upper().startswith("PRAGMA"):
            lines.append(line)
    return re.sub(r"\);\s*", ");\n\n", "\n".join(lines)).strip()


@lru_cache(maxsize=2)
def examples_text(include_plan: bool) -> str:
    data = yaml.safe_load((PROMPTS_DIR / "fewshot_examples.yaml").read_text())
    blocks = []
    for ex in data["examples"]:
        answer = {}
        if include_plan:
            answer["plan"] = ex.get("plan", "")
        answer.update({
            "status": ex["status"],
            "sql": ex.get("sql", ""),
            "explanation": ex["explanation"],
            "assumptions": ex.get("assumptions", []),
            "confidence": ex["confidence"],
        })
        blocks.append(f"Question: {ex['question']}\nAnswer:\n"
                      f"{json.dumps(answer, indent=2, ensure_ascii=False)}")
    return "\n\n".join(blocks)


@lru_cache(maxsize=1)
def value_hints_text() -> str:
    docs = yaml.safe_load(SCHEMA_DOCS_PATH.read_text())
    out = ["General notes:"] + [f"- {n}" for n in docs.get("notes", [])]
    for table, info in docs["tables"].items():
        out.append(f"\nTable {table}: {info['description']}")
        for col, desc in info["columns"].items():
            out.append(f"  - {col}: {desc}")
        for col, values in (info.get("allowed_values") or {}).items():
            shown = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in values)
            out.append(f"  Allowed values of {col}: {shown}")
    return "\n".join(out)


def build_prompt(config: str | PromptConfig, question: str) -> str:
    cfg = get_config(config) if isinstance(config, str) else config
    text = load_template(cfg.template)
    text = text.replace("{schema}", schema_text())
    if cfg.fewshot:
        text = text.replace("{examples}", examples_text(cfg.plan))
    if cfg.values:
        text = text.replace("{value_hints}", value_hints_text())
    return text.replace("{question}", question.strip())


def build_fix_prompt(question: str, previous_sql: str, error: str,
                     cfg: PromptConfig | None = None) -> str:
    text = load_template(FIX_ERROR_TEMPLATE)
    text = text.replace("{schema}", schema_text())
    hints = value_hints_text() if (cfg and cfg.values) else "(none)"
    text = text.replace("{value_hints}", hints)
    text = text.replace("{previous_sql}", previous_sql or "(no SQL was produced)")
    text = text.replace("{error}", error)
    return text.replace("{question}", question.strip())
