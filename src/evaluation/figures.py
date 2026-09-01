"""Report figures, generated from evaluation.json so they cannot drift from the numbers.

Design constraints, and why each one is here:

*Print and greyscale first.* This report will be printed and photocopied. Colour therefore
never carries identity alone: every series also has a marker shape or a hatch pattern, so
the figures survive being read in black and white or by a colourblind reader.

*The palette is validated, not chosen by eye.* The five hues are the Okabe-Ito set in an
order checked with the design system's validator, which reports the worst adjacent
colour-vision-deficiency separation at Delta E 11.0 (deuteranopia), above the 8.0 target.
Reordering was the only change needed; the hues themselves are the established scientific
set.

*One axis per figure.* Cost and F1 are different scales and are never put on two y-axes.
Where both matter they become the two axes of a scatter, which is what makes the
cost-against-accuracy relationship legible rather than merely tabulated.

Run: python -m src.evaluation.figures
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
EVAL = REPO / "data" / "processed" / "evaluation.json"
OUT = REPO / "docs" / "report" / "figures"

# Validated order: worst adjacent CVD separation Delta E 11.0 (deutan). Do not reorder
# without re-running scripts/validate_palette.js from the dataviz skill.
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7"]
INK, MUTED, GRID = "#1a1a1a", "#555555", "#d8d8d8"

# Model family -> (colour, marker, hatch). The marker and hatch are the greyscale fallback.
FAMILY = {
    "gpt-4o-mini": (PALETTE[0], "o", "///"),
    "gpt-4o": (PALETTE[1], "s", "\\\\\\"),
    "qwen3.8-27b": (PALETTE[2], "^", "..."),
    "rule-based": (PALETTE[3], "D", "xxx"),
}
FIELDS = ["USES_PRECURSOR", "USES_LINKER", "IN_SOLVENT", "AT_CONDITION"]


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
            "font.size": 9,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "text.color": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "figure.dpi": 150,
            "savefig.bbox": "tight",
        }
    )


def _family(name: str) -> str:
    if name.startswith("rule"):
        return "rule-based"
    for f in ("gpt-4o-mini", "gpt-4o", "qwen3.8-27b"):
        if f in name:
            return f
    return "rule-based"


def _label(name: str) -> str:
    if name.startswith("rule"):
        return "rule baseline"
    body = name.replace("llm:", "").replace("qwen/", "")
    model, _, strategy = body.rpartition(":")
    return f"{model}\n{strategy.replace('_', '-')}"


def load() -> dict:
    return json.loads(EVAL.read_text(encoding="utf-8"))


def fig_cost_vs_f1(data: dict) -> Path:
    """Cost against accuracy. The figure exists to make one finding immediately visible.

    The strongest configuration is also among the cheapest, and the single most expensive
    configuration scores lower than a configuration costing a forty-seventh as much. In a
    table that is a number to be noticed; on two axes it is the shape of the data.
    """
    _style()
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.grid(True, axis="both", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)

    rows = [(k, v) for k, v in data["extractors"].items() if v["calls"]]
    for name, v in rows:
        colour, marker, _ = FAMILY[_family(name)]
        ax.scatter(
            v["cost_usd"],
            v["micro_f1"],
            s=95,
            color=colour,
            marker=marker,
            edgecolor="white",
            linewidth=1.4,
            zorder=3,
        )

    # Direct labels on the points that carry the argument, not on every point.
    for name, v in rows:
        labelled = {
            "llm:gpt-4o-mini:schema_guided": ((9, 4), "left"),
            "llm:qwen/qwen3.8-27b:zero_shot": ((9, 4), "left"),
            "rule_based_v1": ((9, 4), "left"),
            # The most expensive point sits at the right edge, so its label is placed
            # inward. Left alone it is clipped by the axes.
            "llm:gpt-4o:few_shot": ((-9, 6), "right"),
        }
        if name in labelled:
            offset, align = labelled[name]
            ax.annotate(
                _label(name),
                (v["cost_usd"], v["micro_f1"]),
                textcoords="offset points",
                xytext=offset,
                fontsize=7.5,
                color=INK,
                linespacing=1.25,
                ha=align,
            )

    ax.set_xlabel("Cost for 100 passages (USD)")
    ax.set_ylabel("Micro-averaged F1")
    ax.set_title("Accuracy against cost: the cheapest configuration is also the best")
    ax.set_xlim(-0.06, 1.42)
    ax.set_ylim(0.05, 0.42)

    handles = [
        plt.Line2D(
            [],
            [],
            color=c,
            marker=m,
            linestyle="none",
            markersize=7,
            markeredgecolor="white",
            label=f,
        )
        for f, (c, m, _) in FAMILY.items()
    ]
    ax.legend(handles=handles, frameon=False, loc="lower right", fontsize=8)
    fig.text(
        0.01,
        -0.04,
        "Free-tier models are plotted at zero marginal cost. Single run, temperature 0.",
        fontsize=7,
        color=MUTED,
    )
    p = OUT / "fig1_cost_vs_f1"
    fig.savefig(p.with_suffix(".pdf"))
    fig.savefig(p.with_suffix(".png"))
    plt.close(fig)
    return p


def fig_per_field(data: dict) -> Path:
    """Per-field F1 with gold support printed on the axis.

    Support belongs in the figure rather than only in the caption, because the reader must
    not compare a field backed by 39 annotations against one backed by 30 without seeing it.
    """
    _style()
    show = [
        ("llm:gpt-4o-mini:schema_guided", "gpt-4o-mini schema-guided"),
        ("llm:gpt-4o:schema_guided", "gpt-4o schema-guided"),
        ("llm:qwen/qwen3.8-27b:zero_shot", "qwen3.8-27b zero-shot"),
        ("rule_based_v1", "rule baseline"),
    ]
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.grid(True, axis="y", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)

    n, width = len(show), 0.2
    for i, (key, label) in enumerate(show):
        pf = data["extractors"][key]["per_field"]
        vals = [pf[f]["f1"] for f in FIELDS]
        colour, _, hatch = FAMILY[_family(key)]
        xs = [j + (i - (n - 1) / 2) * width for j in range(len(FIELDS))]
        ax.bar(
            xs,
            vals,
            width * 0.88,
            label=label,
            color=colour,
            edgecolor="white",
            linewidth=1.2,
            hatch=hatch,
            zorder=3,
        )

    support = data["extractors"][show[0][0]]["per_field"]
    ax.set_xticks(range(len(FIELDS)))
    ax.set_xticklabels(
        [f"{f.replace('_', ' ').title()}\n(n={support[f]['support']})" for f in FIELDS],
        fontsize=8,
    )
    ax.set_ylabel("F1")
    ax.set_ylim(0, 0.68)
    ax.set_title("Per-field F1: the margin over rules is largest where identity must be resolved")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right")
    fig.text(
        0.01,
        -0.06,
        "n is the number of gold triples for that field. AT_CONDITION scores reflect an "
        "annotation granularity mismatch, see Chapter 7.",
        fontsize=7,
        color=MUTED,
    )
    p = OUT / "fig2_per_field_f1"
    fig.savefig(p.with_suffix(".pdf"))
    fig.savefig(p.with_suffix(".png"))
    plt.close(fig)
    return p


def fig_strategies(data: dict) -> Path:
    """Prompting strategy by model, commercial models only.

    Only the two commercial models have all four strategies, so only they appear. Plotting
    the open-weight model with one strategy beside them would invite a comparison the data
    cannot support.
    """
    _style()
    strategies = ["zero_shot", "few_shot", "schema_guided", "cot"]
    models = [("gpt-4o-mini", PALETTE[0], "///"), ("gpt-4o", PALETTE[1], "\\\\\\")]
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    ax.grid(True, axis="y", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)

    width = 0.34
    for i, (model, colour, hatch) in enumerate(models):
        vals = [data["extractors"][f"llm:{model}:{s}"]["micro_f1"] for s in strategies]
        xs = [j + (i - 0.5) * width for j in range(len(strategies))]
        bars = ax.bar(
            xs,
            vals,
            width * 0.9,
            label=model,
            color=colour,
            edgecolor="white",
            linewidth=1.2,
            hatch=hatch,
            zorder=3,
        )
        for b, v in zip(bars, vals, strict=True):
            ax.annotate(
                f"{v:.3f}",
                (b.get_x() + b.get_width() / 2, v),
                ha="center",
                va="bottom",
                fontsize=7,
                color=INK,
            )

    ax.set_xticks(range(len(strategies)))
    pretty = {
        "zero_shot": "zero-shot",
        "few_shot": "few-shot",
        "schema_guided": "schema-guided",
        "cot": "chain-of-thought",
    }
    ax.set_xticklabels([pretty[s] for s in strategies], fontsize=8.5)
    ax.set_ylabel("Micro-averaged F1")
    ax.set_ylim(0, 0.44)
    ax.set_title("Prompting strategy, commercial models")
    ax.legend(frameon=False, fontsize=8)
    fig.text(
        0.01,
        -0.07,
        "The open-weight model is omitted: only one of its four strategies completed within "
        "the free-tier token cap.",
        fontsize=7,
        color=MUTED,
    )
    p = OUT / "fig3_prompting_strategies"
    fig.savefig(p.with_suffix(".pdf"))
    fig.savefig(p.with_suffix(".png"))
    plt.close(fig)
    return p


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = load()
    for fn in (fig_cost_vs_f1, fig_per_field, fig_strategies):
        p = fn(data)
        print(f"  wrote {p.relative_to(REPO)}.pdf and .png")


if __name__ == "__main__":
    main()
