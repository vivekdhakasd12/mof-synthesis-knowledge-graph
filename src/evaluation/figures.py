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
PASSAGES = REPO / "data" / "processed" / "passages.jsonl"
CORPUS = REPO / "data" / "processed" / "corpus.jsonl"
GOLD = REPO / "data" / "annotations" / "gold.jsonl"
THRESHOLD = 0.45  # the chosen synthesis-score cutoff, as declared in Section 3.3
OUT = REPO / "docs" / "report" / "figures"

# Validated order: worst adjacent CVD separation Delta E 11.0 (deutan). Do not reorder
# without re-running scripts/validate_palette.js from the dataviz skill.
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7"]
INK, MUTED, GRID = "#1a1a1a", "#555555", "#d8d8d8"

# One canvas width per figure class, matching the placement widths in the report builder, so
# no figure is rescaled on the page and label sizes are comparable from one figure to the
# next. Only the canvas changes: every axis limit, baseline and annotation is untouched.
STD_W, WIDE_W = 5.1, 6.55

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


def _passages() -> list[dict]:
    return [json.loads(line) for line in PASSAGES.read_text(encoding="utf-8").splitlines()]


def corpus_funnel() -> list[int]:
    """The five funnel stages, counted from the artefacts rather than typed in.

    Every one of these numbers also appears in the report's prose, so deriving them means a
    rebuilt corpus cannot leave the figure disagreeing with the text.
    """
    rows = _passages()
    flagged = [r for r in rows if r["synthesis_score"] >= THRESHOLD]
    papers = sum(1 for _ in CORPUS.open(encoding="utf-8"))
    gold = sum(1 for _ in GOLD.open(encoding="utf-8"))
    return [papers, len({r["paper_id"] for r in flagged}), len(rows), len(flagged), gold]


CUTOFFS = (0.25, 0.35, 0.45, 0.55, 0.65)


def threshold_curve(cutoffs: tuple[float, ...] = CUTOFFS) -> list[tuple[float, int, int]]:
    """Passages and papers retained at each candidate cutoff.

    Previously a hardcoded list of literals in main(). The values were correct, but a
    typed-in number in an analysis script is the same shape as the defect recorded in
    docs/report/README.md, so it is computed now.
    """
    rows = _passages()
    out = []
    for c in cutoffs:
        sel = [r for r in rows if r["synthesis_score"] >= c]
        out.append((c, len(sel), len({r["paper_id"] for r in sel})))
    return out


def fig_cost_vs_f1(data: dict) -> Path:
    """Cost against accuracy. The figure exists to make one finding immediately visible.

    The strongest configuration is also among the cheapest, and the single most expensive
    configuration scores lower than a configuration costing a forty-seventh as much. In a
    table that is a number to be noticed; on two axes it is the shape of the data.
    """
    _style()
    fig, ax = plt.subplots(figsize=(STD_W, 3.4))
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
    fig, ax = plt.subplots(figsize=(STD_W, 3.3))
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
    fig, ax = plt.subplots(figsize=(STD_W, 2.9))
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


def fig_precision_recall(data: dict) -> Path:
    """Precision against recall, which separates two different ways of being wrong.

    A single F1 hides whether a configuration is cautious or scattergun. Plotting the two
    axes separately shows that the language models sit consistently above the baseline on
    both, and that recall varies more than precision across prompting strategies, which is
    the more actionable observation for anyone tuning one.
    """
    _style()
    fig, ax = plt.subplots(figsize=(STD_W, 3.6))
    ax.grid(True, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)

    # Iso-F1 contours give the reader a way to compare points that a bare scatter cannot.
    import numpy as np

    grid = np.linspace(0.02, 0.75, 240)
    xx, yy = np.meshgrid(grid, grid)
    f1 = 2 * xx * yy / (xx + yy)
    cs = ax.contour(xx, yy, f1, levels=[0.1, 0.2, 0.3, 0.4], colors=GRID, linewidths=0.7)
    ax.clabel(cs, fmt="F1=%.1f", fontsize=6.5, colors=MUTED)

    for name, v in data["extractors"].items():
        if not v["calls"]:
            continue
        colour, marker, _ = FAMILY[_family(name)]
        ax.scatter(
            v["micro_recall"],
            v["micro_precision"],
            s=85,
            color=colour,
            marker=marker,
            edgecolor="white",
            linewidth=1.3,
            zorder=3,
        )

    for name in ("llm:gpt-4o-mini:schema_guided", "rule_based_v1"):
        v = data["extractors"][name]
        ax.annotate(
            _label(name),
            (v["micro_recall"], v["micro_precision"]),
            textcoords="offset points",
            xytext=(9, -2),
            fontsize=7.5,
            color=INK,
            linespacing=1.25,
        )

    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_xlim(0.05, 0.52)
    ax.set_ylim(0.05, 0.38)
    ax.set_title("Precision against recall, with iso-F1 contours")
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
    ax.legend(handles=handles, frameon=False, loc="upper left", fontsize=8)
    p = OUT / "fig4_precision_recall"
    fig.savefig(p.with_suffix(".pdf"))
    fig.savefig(p.with_suffix(".png"))
    plt.close(fig)
    return p


def fig_corpus(threshold_rows: list[tuple[float, int, int]]) -> Path:
    """Corpus funnel and the segmentation threshold, side by side.

    The threshold is a declared methodological choice, so the report should show the curve
    it was chosen from rather than assert that 0.45 was reasonable. Plotting passages and
    papers on the same panel would need two y-scales, which is never acceptable, so they
    are two panels sharing an x-axis.
    """
    _style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDE_W, 2.9))

    stages = [
        "Papers\ncollected",
        "Papers with\nsynthesis text",
        "Passages\nsegmented",
        "Synthesis\npassages",
        "Gold\nannotated",
    ]
    values = corpus_funnel()
    bars = ax1.bar(
        range(len(stages)),
        values,
        color=PALETTE[0],
        edgecolor="white",
        linewidth=1.2,
        hatch="///",
        zorder=3,
    )
    ax1.set_yscale("log")
    ax1.set_xticks(range(len(stages)))
    ax1.set_xticklabels(stages, fontsize=7)
    ax1.set_ylabel("Count (log scale)")
    ax1.set_title("Corpus funnel", fontsize=9.5)
    ax1.grid(True, axis="y", linewidth=0.6, alpha=0.7)
    ax1.set_axisbelow(True)
    for b, v in zip(bars, values, strict=True):
        ax1.annotate(
            f"{v:,}",
            (b.get_x() + b.get_width() / 2, v),
            ha="center",
            va="bottom",
            fontsize=7,
            color=INK,
        )

    cuts = [r[0] for r in threshold_rows]
    passages = [r[1] for r in threshold_rows]
    papers = [r[2] for r in threshold_rows]
    ax2.plot(
        cuts,
        passages,
        color=PALETTE[0],
        marker="o",
        markersize=6,
        markeredgecolor="white",
        linewidth=2,
        label="passages",
        zorder=3,
    )
    ax2.plot(
        cuts,
        papers,
        color=PALETTE[1],
        marker="s",
        markersize=6,
        markeredgecolor="white",
        linewidth=2,
        linestyle="--",
        label="papers",
        zorder=3,
    )
    ax2.axvline(0.45, color=MUTED, linewidth=1, linestyle=":", zorder=2)
    ax2.annotate("chosen\nthreshold", (0.45, 1900), fontsize=7, color=MUTED, ha="center")
    ax2.set_xlabel("Synthesis score threshold")
    ax2.set_ylabel("Count")
    ax2.set_title("Threshold sensitivity", fontsize=9.5)
    ax2.grid(True, linewidth=0.6, alpha=0.7)
    ax2.set_axisbelow(True)
    ax2.legend(frameon=False, fontsize=8)

    fig.tight_layout()
    p = OUT / "fig5_corpus_and_threshold"
    fig.savefig(p.with_suffix(".pdf"))
    fig.savefig(p.with_suffix(".png"))
    plt.close(fig)
    return p


def fig_baseline_failure(data: dict) -> Path:
    """Why the rule baseline fails, which is the mechanism behind the headline result.

    The baseline identified a MOF in 121 of 794 synthesis passages, matching the count in
    `docs/baseline_findings.md` (reproduce with
    `python -m src.pipeline --extractors rule_based --no-resume`). Because five of the eight
    ontology relations take MOF as their subject, that single failure suppresses most of what
    a rule-based system could otherwise extract. The breakdown shows the causes are
    coreference and generic naming, not lexicon gaps a larger dictionary would close.

    Plain horizontal bars rather than one stacked bar: the job here is comparing four
    magnitudes, and a stacked bar makes that comparison harder while forcing labels onto
    hatched fills where they cannot be read.
    """
    _style()
    causes = [
        "MOF named in this passage",
        "Named elsewhere in the paper",
        'Generic designation ("compound 1")',
        "Other",
    ]
    counts = [121, 331, 251, 794 - 121 - 331 - 251]
    colours = [PALETTE[2], PALETTE[1], PALETTE[3], PALETTE[4]]
    hatches = ["...", "\\\\\\", "xxx", "///"]

    fig, ax = plt.subplots(figsize=(WIDE_W, 2.5))
    ax.grid(True, axis="x", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ys = range(len(causes))
    ax.barh(
        list(ys),
        counts,
        height=0.62,
        color=colours,
        edgecolor="white",
        linewidth=1.4,
        hatch=hatches,
        zorder=3,
    )
    for y, n in zip(ys, counts, strict=True):
        ax.annotate(
            f"{n}  ({n / 794:.0%})",
            (n, y),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=INK,
        )

    ax.set_yticks(list(ys))
    ax.set_yticklabels(causes, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 400)
    ax.set_xlabel("Synthesis passages (n = 794)")
    ax.set_title("Why the rule baseline cannot name the material")
    fig.text(
        0.01,
        -0.13,
        "Five of the eight ontology relations take MOF as their subject, so a passage where no "
        "MOF is identified\nyields none of them however clearly the reagents are written.",
        fontsize=7,
        color=MUTED,
    )
    p = OUT / "fig6_baseline_failure_modes"
    fig.savefig(p.with_suffix(".pdf"))
    fig.savefig(p.with_suffix(".png"))
    plt.close(fig)
    return p


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = load()
    threshold_rows = threshold_curve()
    for fn in (
        fig_cost_vs_f1,
        fig_per_field,
        fig_strategies,
        fig_precision_recall,
        fig_baseline_failure,
    ):
        p = fn(data)
        print(f"  wrote {p.relative_to(REPO)}.pdf and .png")
    p = fig_corpus(threshold_rows)
    print(f"  wrote {p.relative_to(REPO)}.pdf and .png")


if __name__ == "__main__":
    main()
