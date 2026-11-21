import re

import pytest
import yaml

from querycraft.config import BENCHMARK_PATH, PROMPTS_DIR
from querycraft.executor import execute
from querycraft.prompt_builder import CONFIGS, build_fix_prompt, build_prompt

FEWSHOT = yaml.safe_load((PROMPTS_DIR / "fewshot_examples.yaml").read_text())["examples"]


@pytest.mark.parametrize("name", list(CONFIGS))
def test_every_config_builds_without_leftover_placeholders(name):
    p = build_prompt(name, "How many students are there?")
    assert "How many students are there?" in p
    assert not re.search(r"\{(schema|examples|value_hints|question)\}", p)


def test_v1_text_is_unchanged_from_milestone_1():
    t = (PROMPTS_DIR / "v1/v1_baseline.txt").read_text()
    assert t.startswith("You are an SQL assistant for a university admin office.")
    assert "followed by a one-line explanation in simple English." in t


def test_only_plan_configs_ask_for_plan():
    for name, cfg in CONFIGS.items():
        assert ('"plan"' in build_prompt(name, "q")) == cfg.plan, name


def test_only_value_configs_include_allowed_values():
    for name, cfg in CONFIGS.items():
        assert ("Allowed values of program_name" in build_prompt(name, "q")) == cfg.values, name


def test_fix_prompt_fills_everything():
    p = build_fix_prompt("q?", "SELECT x FROM y", "Unknown table(s): y.")
    assert "SELECT x FROM y" in p and "Unknown table(s): y." in p
    assert not re.search(r"\{(schema|value_hints|question|previous_sql|error)\}", p)


@pytest.mark.parametrize("ex", [e for e in FEWSHOT if e["status"] == "OK"],
                         ids=lambda e: e["question"][:30])
def test_fewshot_sql_runs(ex):
    r = execute(ex["sql"])
    assert r["ok"], r
    assert r["rows"], "few-shot example should return rows"


def test_fewshot_not_copied_from_benchmark():
    bench = yaml.safe_load(BENCHMARK_PATH.read_text())["questions"]
    bench_q = {q["question"].strip().lower() for q in bench}
    bench_sql = {q["gold_sql"].strip().lower() for q in bench if q["gold_sql"]}
    for ex in FEWSHOT:
        assert ex["question"].strip().lower() not in bench_q
        assert ex.get("sql", "").strip().lower() not in bench_sql
