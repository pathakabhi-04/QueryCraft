"""Turn a results folder's raw.jsonl into tables, a failure list and charts.

    python -m eval.compare                          # latest folder in eval/results/
    python -m eval.compare eval/results/20261121-210000
    python -m eval.compare DIR1 DIR2 --out eval/results/combined   # merge several runs

Every number written here is computed from raw.jsonl; nothing is typed in by hand.
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from eval.metrics import aggregate, consistency  # noqa: E402
from querycraft.config import RESULTS_DIR  # noqa: E402

CUMULATIVE = ["v1", "v2", "v3", "v4", "v5", "v5+sc"]
ABLATION = ["v2", "v2+fewshot", "v2+plan", "v2+values", "v2+sc"]
CATEGORIES = ["easy", "medium", "hard", "unanswerable", "adversarial"]

# Fixed colour per model (colour follows the entity, never its rank): Gemini models take
# categorical slot 1; other models take slots 2, 3, 4 by sorted name.
SLOT_1 = "#2a78d6"
OTHER_SLOTS = ["#eb6834", "#1baf7a", "#eda100"]


def model_colors(names) -> dict:
    names = sorted(set(names))
    others = [n for n in names if "gemini" not in n.lower()]
    colors = {n: SLOT_1 for n in names if "gemini" in n.lower()}
    colors.update({n: OTHER_SLOTS[i % len(OTHER_SLOTS)] for i, n in enumerate(others)})
    return colors
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

METRIC_COLS = [
    ("accuracy", "Overall acc %"), ("ex", "EX %"), ("ex_strict", "EX strict %"),
    ("refusal_acc", "Refusal acc %"), ("safety", "Safety %"), ("unsafe_passed", "Unsafe passed"),
    ("false_refusal", "False refusal %"), ("valid_sql", "Valid SQL %"),
    ("hallucination", "Halluc. %"), ("parse_failure", "Parse fail %"),
    ("latency_mean", "Latency mean s"), ("latency_p95", "Latency p95 s"),
    ("retries_mean", "Retries mean"), ("consistency", "Consistency %"),
]


def load(dirs: list[Path]) -> tuple[list[dict], list[dict]]:
    rows, metas = [], []
    for d in dirs:
        with open(d / "raw.jsonl") as fh:
            rows += [json.loads(line) for line in fh if line.strip()]
        if (d / "meta.json").exists():
            metas.append(json.loads((d / "meta.json").read_text()))
    return rows, metas


def _ordered_configs(present) -> list[str]:
    known = [c for c in CUMULATIVE + ABLATION if c in present]
    seen = []
    for c in known + sorted(set(present) - set(known)):
        if c not in seen:
            seen.append(c)
    return seen


def _fmt(v) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.1f}" if abs(v) >= 1 or v == 0 else f"{v:.2f}"
    return str(v)


def build_tables(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for r in rows:
        groups[(r["config"], r["model_name"], "ALL")].append(r)
        groups[(r["config"], r["model_name"], r["category"])].append(r)
    table = {}
    for key, rs in groups.items():
        agg = aggregate(rs)
        agg["consistency"] = consistency(rs)
        table[key] = agg
    return table


def write_csv(table: dict, path: Path) -> None:
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["config", "model", "category"] + [k for k, _ in METRIC_COLS] + ["n"])
        for (cfg, model, cat), agg in sorted(table.items()):
            w.writerow([cfg, model, cat] + [agg.get(k) for k, _ in METRIC_COLS] + [agg["n"]])


def _md_table(header: list[str], body: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(_fmt(c) for c in row) + " |" for row in body]
    return "\n".join(out)


def write_summary_md(table: dict, rows: list[dict], metas: list[dict], path: Path) -> None:
    configs = _ordered_configs({r["config"] for r in rows})
    models = sorted({r["model_name"] for r in rows})
    model_names = sorted({f"`{r['model_name']}` ({r['backend']})" for r in rows})
    runs = sorted({r["run"] for r in rows})
    lines = ["# QueryCraft evaluation summary", ""]
    for m in metas:
        lines.append(f"- Command: `{m.get('command')}`  ")
        lines.append(f"  Started {m.get('started')}, finished {m.get('finished', '-')}, "
                     f"git `{m.get('git_commit')}`, temperature {m.get('temperature')}, "
                     f"max tokens {m.get('max_output_tokens')}")
        lines.append(f"- Benchmark sha256 `{m.get('benchmark_sha256', '')[:16]}...`, "
                     f"hand-verified items: **{m.get('benchmark_verified')}**")
        if m.get("interrupted_after_calls") is not None:
            lines.append(f"- **Run was interrupted** after {m['interrupted_after_calls']} calls.")
    lines += [f"- Models: {'; '.join(model_names)}",
              f"- Runs: {len(runs)}; questions per config/model/run: "
              f"{len({r['id'] for r in rows})}", ""]
    if any(str(m.get("benchmark_verified", "")).startswith("0/") for m in metas):
        lines += ["> **Provisional:** the benchmark's gold SQL has not been hand-verified yet, "
                  "so these numbers may change once it is.", ""]

    lines += ["## Overall (config x model)", ""]
    body = []
    for cfg in configs:
        for model in models:
            agg = table.get((cfg, model, "ALL"))
            if agg:
                body.append([cfg, model, agg["n"]] + [agg.get(k) for k, _ in METRIC_COLS])
    lines.append(_md_table(["Config", "Model", "n"] + [h for _, h in METRIC_COLS], body))

    lines += ["", "## Accuracy by category (EX for answerable, status match for refusals)", ""]
    body = []
    for cfg in configs:
        for model in models:
            if (cfg, model, "ALL") in table:
                body.append([cfg, model] + [table.get((cfg, model, c), {}).get("accuracy")
                                            for c in CATEGORIES])
    lines.append(_md_table(["Config", "Model"] + CATEGORIES, body))

    errs = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if not r["correct"]:
            errs[(r["config"], r["model_name"])][r["error_type"]] += 1
    etypes = sorted({e for d in errs.values() for e in d})
    if etypes:
        lines += ["", "## Error types (count of wrong answers, auto-classified)", ""]
        body = [[cfg, model] + [errs[(cfg, model)].get(e, 0) for e in etypes]
                for cfg in configs for model in models if (cfg, model, "ALL") in table]
        lines.append(_md_table(["Config", "Model"] + etypes, body))

    lines += ["", "## Metric definitions", "",
              "- **Overall acc**: EX on answerable items, status match on refusal items, over all items.",
              "- **EX**: result rows equal to gold (multiset; order only if `order_matters`; floats to 2 dp; "
              "column names/order ignored; extra predicted columns allowed). **EX strict**: no extra columns.",
              "- **Refusal acc**: predicted status equals expected status on unanswerable + adversarial items "
              "(V1 has no status, so it is always 0 here).",
              "- **Safety**: adversarial items that were refused *or* blocked by the validator (never executed). "
              "**Unsafe passed**: adversarial items whose SQL was executed.",
              "- **False refusal**: answerable items the model refused.",
              "- **Valid SQL**: of the items where the model returned SQL, the share that passed validation and ran.",
              "- **Halluc.**: of the items where the model returned SQL, the share that referenced a "
              "non-existent table or column in any attempt.",
              "- **Latency**: seconds per question including self-correction retries (original call time "
              "for cached responses).",
              "- **Consistency**: % of questions with the same correct/incorrect outcome in every run "
              "(needs `--runs` >= 2).", ""]
    path.write_text("\n".join(lines))


def write_failures_md(rows: list[dict], path: Path) -> None:
    by_type = defaultdict(list)
    for r in rows:
        if not r["correct"]:
            by_type[r["error_type"]].append(r)
    lines = ["# Failures by error type", "",
             "Error types are a heuristic first guess (`eval/metrics.py: classify_error`). "
             "Check them by hand before using them in the report.", ""]
    for etype in sorted(by_type, key=lambda e: -len(by_type[e])):
        items = by_type[etype]
        lines += [f"## {etype} ({len(items)})", ""]
        for r in sorted(items, key=lambda r: (r["id"], r["config"], r["model_name"], r["run"])):
            lines.append(f"### {r['id']} | {r['config']} | {r['model_name']} | run {r['run']}")
            lines.append(f"- Question: {r['question']}")
            lines.append(f"- Expected: {r['expected_status']}; got: {r['status']}")
            if r.get("sql"):
                lines.append(f"- Model SQL: `{r['sql']}`")
            if r.get("blocked_reason"):
                lines.append(f"- Blocked: {r['blocked_reason']}")
            if r.get("error"):
                lines.append(f"- Error: {r['error']}")
            if r.get("ok"):
                lines.append(f"- Returned {r.get('row_count')} row(s); first: "
                             f"`{r['rows'][:2]}`")
            lines.append("")
    path.write_text("\n".join(lines))


# ---------------------------------------------------------------- charts

def _style(ax, ylabel: str, ymax: float | None = 100):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(INK_2)
    ax.tick_params(colors=INK_2, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_ylabel(ylabel, color=INK_2)
    if ymax is not None:
        ax.set_ylim(0, ymax)


def _grouped_bars(ax, configs, models, value_of):
    colors = model_colors(models)
    width = 0.8 / max(1, len(models))
    for i, model in enumerate(models):
        xs, ys = [], []
        for j, cfg in enumerate(configs):
            v = value_of(cfg, model)
            if v is not None:
                xs.append(j - 0.4 + width * (i + 0.5))
                ys.append(v)
        ax.bar(xs, ys, width=width * 0.9, color=colors[model],
               label=model, edgecolor=SURFACE, linewidth=1.5)
    ax.set_xticks(range(len(configs)))
    ax.set_xticklabels(configs, color=INK)
    if len(models) > 1:
        ax.legend(frameon=False, labelcolor=INK)


def _save(fig, path: Path, title: str):
    fig.suptitle(title, color=INK, fontsize=12, x=0.01, ha="left")
    fig.patch.set_facecolor(SURFACE)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def write_charts(table: dict, rows: list[dict], charts: Path) -> list[str]:
    charts.mkdir(parents=True, exist_ok=True)
    present = {r["config"] for r in rows}
    models = sorted({r["model_name"] for r in rows})
    made = []

    def val(metric):
        return lambda c, m: table.get((c, m, "ALL"), {}).get(metric)

    cum = [c for c in CUMULATIVE if c in present]
    if cum:
        fig, ax = plt.subplots(figsize=(7.5, 4))
        _grouped_bars(ax, cum, models, val("accuracy"))
        _style(ax, "Overall accuracy (%)")
        _save(fig, charts / "accuracy_by_version.png", "Accuracy by prompt version (cumulative)")
        made.append("accuracy_by_version.png")

    abl = [c for c in ABLATION if c in present]
    if len(abl) > 1:
        fig, ax = plt.subplots(figsize=(7.5, 4))
        _grouped_bars(ax, abl, models, val("accuracy"))
        _style(ax, "Overall accuracy (%)")
        _save(fig, charts / "ablation.png", "Ablation: one technique added to V2")
        made.append("ablation.png")

    configs = _ordered_configs(present)
    fig, ax = plt.subplots(figsize=(max(6, 1.1 * len(configs) + 2), 4))
    _grouped_bars(ax, configs, models, val("latency_mean"))
    _style(ax, "Mean seconds per question", ymax=None)
    _save(fig, charts / "latency.png", "Latency per question (incl. self-correction)")
    made.append("latency.png")

    if any(r["category"] == "adversarial" for r in rows):
        fig, axes = plt.subplots(1, 2, figsize=(max(9, 1.6 * len(configs) + 3), 4))
        _grouped_bars(axes[0], configs, models, val("safety"))
        _style(axes[0], "Adversarial items refused or blocked (%)")
        axes[0].set_title("Safety (higher is better)", color=INK, fontsize=10, loc="left")
        _grouped_bars(axes[1], configs, models, val("false_refusal"))
        _style(axes[1], "Answerable items refused (%)")
        axes[1].set_title("False refusals (lower is better)", color=INK, fontsize=10, loc="left")
        for ax in axes:
            ax.tick_params(axis="x", labelrotation=30)
        _save(fig, charts / "safety.png", "Safety vs false refusals")
        made.append("safety.png")
    return made


def write_reports(out: Path, dirs: list[Path] | None = None) -> None:
    rows, metas = load(dirs or [out])
    if not rows:
        print("No rows to summarise.")
        return
    table = build_tables(rows)
    write_csv(table, out / "summary.csv")
    write_summary_md(table, rows, metas, out / "summary.md")
    write_failures_md(rows, out / "failures.md")
    charts = write_charts(table, rows, out / "charts")
    print(f"Wrote summary.csv, summary.md, failures.md, charts/{{{', '.join(charts)}}} in {out}")


def _latest() -> Path:
    runs = sorted(p for p in RESULTS_DIR.iterdir() if (p / "raw.jsonl").exists())
    if not runs:
        raise SystemExit("No results found in eval/results/")
    return runs[-1]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*", type=Path)
    ap.add_argument("--out", type=Path, help="where to write when merging several dirs")
    a = ap.parse_args()
    dirs = a.dirs or [_latest()]
    out = a.out or dirs[0]
    out.mkdir(parents=True, exist_ok=True)
    write_reports(out, dirs)
