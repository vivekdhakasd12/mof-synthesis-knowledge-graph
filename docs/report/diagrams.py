"""Structural diagrams for the report: pipeline architecture and ontology schema.

These carry no measured quantity that is not already stated in the chapter text, so unlike
``src/evaluation/figures.py`` this module reads nothing from ``evaluation.json``. What it does
share with that module is the constraint set. The palette is the same validated Okabe-Ito
order, node class is carried by outline colour *and* corner shape *and* line style together
so nothing depends on hue alone, and each figure is generated at the width it is placed at so
that no label is rescaled between here and the page.

Layout is authored in the drawing's own coordinate space with y increasing downward, which is
why every coordinate below reads like a screen coordinate. One axes fills the figure and spans
those units, so a box written at (206, 52) lands where the sketch put it. Type sizes are given
in drawing units too and converted once, which keeps them proportional to the drawing rather
than to whatever figure size is chosen later.

Every label that has to sit inside a box registers the box it claims, and ``Sheet.check``
re-measures the rendered text against that claim after drawing. A label that has outgrown its
box prints a warning naming itself rather than silently overprinting its neighbour, which is
the failure mode this kind of hand-placed diagram has.

Run: python -m src.report.diagrams
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon  # noqa: E402

# Lives beside build_report.py rather than in src/, so that the module and line counts
# Section 4.1 reports for the pipeline stay true: this is a report build tool, not part of
# the extraction system it documents.
REPORT = Path(__file__).resolve().parent
REPO = REPORT.parents[1]
OUT = REPORT / "figures"

# Same validated order as src/evaluation/figures.py. Do not reorder without re-running the
# palette validator: the worst adjacent colour-vision separation is Delta E 11.0 as it stands.
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7"]
INK, MUTED, HAIR = "#1a1a1a", "#555555", "#999999"

STAGE, ARTEFACT, DELIVERED, CONNECTOR = PALETTE[0], PALETTE[3], PALETTE[2], PALETTE[2]
STAGE_FILL = "#F7FAFC"
ARTEFACT_FILL = "#FFFBF3"
DELIVERED_FILL = "#F3FAF7"
EXTERNAL_FILL = "#F4F3F1"

# The text block is 13 cm and the outer margin column adds 3.7 cm. Both diagrams are wide
# figures, placed across the whole measure plus that margin, so they are drawn at 6.55 in.
WIDE_IN = 5.9  # the report's 15cm text measure, so the diagram is never rescaled

DASH = (0, (5, 4))
DASH_FLOW = (0, (6, 4))


class Sheet:
    """One diagram: an axes in drawing units, plus the fit claims made against it."""

    def __init__(self, width: float, height: float, *, width_in: float = WIDE_IN) -> None:
        plt.rcParams.update(
            {
                "font.family": "sans-serif",
                "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
                "font.monospace": ["Menlo", "DejaVu Sans Mono", "Courier New"],
                "savefig.bbox": None,
                "figure.dpi": 150,
            }
        )
        self.width, self.height = width, height
        self.fig = plt.figure(figsize=(width_in, width_in * height / width))
        self.ax = self.fig.add_axes((0.0, 0.0, 1.0, 1.0))
        self.ax.set_xlim(0, width)
        self.ax.set_ylim(height, 0)  # y downward, so the sketch coordinates port directly
        self.ax.set_axis_off()
        self.pt = width_in * 72.0 / width  # points per drawing unit
        self.claims: list[tuple[object, tuple[float, float]]] = []

    # -- primitives ----------------------------------------------------------------

    def rounded(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        edge: str,
        fill: str,
        lw: float = 1.8,
        radius: float = 6.0,
        dashed: bool = False,
    ) -> None:
        self.ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle=f"round,pad=0,rounding_size={radius}",
                mutation_aspect=1.0,
                linewidth=lw,
                edgecolor=edge,
                facecolor=fill,
                linestyle=DASH if dashed else "solid",
                clip_on=False,
                zorder=2,
            )
        )

    def tile(
        self, x: float, y: float, w: float, h: float, *, edge: str, fill: str, lw: float = 1.8
    ) -> None:
        """An artefact on disk. The clipped corner is the greyscale channel for this class."""
        clip = 14.0
        self.ax.add_patch(
            Polygon(
                [(x, y), (x + w - clip, y), (x + w, y + clip), (x + w, y + h), (x, y + h)],
                closed=True,
                linewidth=lw,
                edgecolor=edge,
                facecolor=fill,
                joinstyle="miter",
                clip_on=False,
                zorder=2,
            )
        )

    def flow(
        self,
        points: list[tuple[float, float]],
        *,
        colour: str = MUTED,
        lw: float = 1.6,
        dashed: bool = False,
    ) -> None:
        """An orthogonal connector. The arrowhead is drawn on the final segment only."""
        self.ax.plot(
            [p[0] for p in points],
            [p[1] for p in points],
            color=colour,
            linewidth=lw,
            linestyle=DASH_FLOW if dashed else "solid",
            solid_capstyle="butt",
            clip_on=False,
            zorder=1,
        )
        self.ax.annotate(
            "",
            xy=points[-1],
            xytext=points[-2],
            arrowprops={
                "arrowstyle": "-|>",
                "color": colour,
                "linewidth": lw,
                "shrinkA": 0,
                "shrinkB": 0,
                "mutation_scale": 9,
                "linestyle": "solid",
            },
            annotation_clip=False,
            zorder=1,
        )

    def text(
        self,
        x: float,
        y: float,
        s: str,
        *,
        size: float,
        colour: str = INK,
        weight: str = "normal",
        mono: bool = False,
        italic: bool = False,
        ha: str = "left",
        fit: tuple[float, float] | None = None,
    ) -> None:
        artist = self.ax.text(
            x,
            y,
            s,
            fontsize=size * self.pt,
            color=colour,
            fontweight=weight,
            style="italic" if italic else "normal",
            family="monospace" if mono else "sans-serif",
            ha=ha,
            va="baseline",
            clip_on=False,
            zorder=3,
        )
        if fit is not None:
            self.claims.append((artist, fit))

    def pill(self, cx: float, y: float, s: str, *, size: float) -> None:
        """A capsule that sizes itself to its label, so a long module name cannot overflow."""
        self.ax.text(
            cx,
            y,
            s,
            fontsize=size * self.pt,
            color=STAGE,
            family="monospace",
            ha="center",
            va="baseline",
            clip_on=False,
            zorder=3,
            bbox={
                "boxstyle": "round,pad=0.36",
                "facecolor": "white",
                "edgecolor": STAGE,
                "linewidth": 1.2,
            },
        )

    # -- output --------------------------------------------------------------------

    def check(self) -> bool:
        """Re-measure every claimed label against the box it sits in."""
        self.fig.canvas.draw()
        renderer = self.fig.canvas.get_renderer()
        inverse = self.ax.transData.inverted()
        ok = True
        for artist, (left, right) in self.claims:
            box = artist.get_window_extent(renderer)
            x0 = inverse.transform((box.x0, box.y0))[0]
            x1 = inverse.transform((box.x1, box.y1))[0]
            if x0 < left - 0.5 or x1 > right + 0.5:
                ok = False
                print(
                    f"  WARNING {artist.get_text()!r} spans {x0:.1f}-{x1:.1f}, "
                    f"outside its box at {left:.0f}-{right:.0f}"
                )
        return ok

    def save(self, stem: str) -> Path:
        path = OUT / stem
        self.fig.savefig(path.with_suffix(".pdf"))
        self.fig.savefig(path.with_suffix(".png"))
        plt.close(self.fig)
        return path


def pipeline_architecture() -> Path:
    """Section 4.1. Stages on the left, the files they write on the right.

    The alternation between the two columns is the point: an arrow leaving a stage writes a
    file, an arrow entering one reads a file, so the reader sees the disk boundary in the
    shape of the figure before reading a label. The three return connectors run in separate
    lanes down the gutter so that three distinct reads cannot be mistaken for one rail.
    """
    s = Sheet(950, 580)
    t_title, t_name, t_mono, t_body, t_pill = 18.0, 17.0, 15.0, 14.0, 13.0

    for pts in (
        [(180, 99), (206, 99)],
        [(506, 70), (523, 70), (523, 84), (540, 84)],
        [(540, 98), (536, 98), (536, 242), (508, 242)],
        [(506, 184), (523, 184), (523, 200), (540, 200)],
        [(540, 225), (526, 225), (526, 360), (508, 360)],
        [(506, 306), (523, 306), (523, 318), (540, 318)],
        [(540, 337), (516, 337), (516, 492), (508, 492)],
        [(506, 452), (523, 452), (523, 466), (540, 466)],
        [(180, 477), (206, 477)],
        [(734, 336), (764, 336)],
        [(734, 480), (750, 480), (750, 462), (764, 462)],
    ):
        s.flow(pts)

    # The external source and the one hand-made input.
    for x, y, w, h, name, lines in (
        (16, 74, 164, 50, "Europe PMC", ["open-access subset"]),
        (16, 440, 164, 92, "gold.jsonl", ["100 passages,", "138 triples", "annotated by hand"]),
    ):
        s.rounded(x, y, w, h, edge=HAIR, fill=EXTERNAL_FILL, lw=1.5, radius=4, dashed=True)
        s.text(x + 14, y + 23, name, size=t_name, weight="semibold", fit=(x, x + w))
        for i, line in enumerate(lines):
            s.text(x + 14, y + 41 + 18 * i, line, size=t_body, colour=MUTED, fit=(x, x + w))

    stages = (
        (
            52,
            88,
            "Ingestion",
            ["europepmc.py \u00b7 parse.py", "build_corpus.py"],
            ["JATS full text, labelled sections"],
        ),
        (
            168,
            88,
            "Segmentation",
            ["segment.py"],
            ["deterministic passage ids,", "synthesis score \u2265 0.45"],
        ),
        (288, 116, "Extraction", ["pipeline.py"], []),
        (432, 88, "Evaluation", ["metrics.py \u00b7 run_eval.py"], ["greedy one-to-one matching"]),
    )
    for y, h, name, modules, body in stages:
        s.rounded(206, y, 300, h, edge=STAGE, fill=STAGE_FILL, radius=8)
        s.text(222, y + 27, name, size=t_title, weight="bold", fit=(206, 506))
        cursor = y + 49
        for line in modules:
            s.text(222, cursor, line, size=t_mono, colour=STAGE, mono=True, fit=(206, 506))
            cursor += 18
        for line in body:
            s.text(222, cursor, line, size=t_body, colour=MUTED, fit=(206, 506))
            cursor += 18

    # The two extractor strands share one stage box because they share one interface.
    s.pill(282, 366, "rule_based.py", size=t_pill)
    s.pill(429, 366, "llm_extractor.py", size=t_pill)
    s.text(
        222,
        393,
        "one Extractor interface, responses cached",
        size=t_body,
        colour=MUTED,
        fit=(206, 506),
    )

    artefacts = (
        (70, 56, "corpus.jsonl", ["399 papers"]),
        (190, 70, "passages.jsonl", ["22,086 passages", "794 flagged synthesis"]),
        (300, 74, "results.jsonl", ["triples, cost_usd,", "latency_ms, errors"]),
        (452, 56, "evaluation.json", ["per-field metrics"]),
    )
    for y, h, name, lines in artefacts:
        s.tile(540, y, 194, h, edge=ARTEFACT, fill=ARTEFACT_FILL)
        s.text(554, y + 24, name, size=t_name, weight="semibold", mono=True, fit=(540, 734))
        for i, line in enumerate(lines):
            s.text(554, y + 42 + 18 * i, line, size=t_body, colour=MUTED, fit=(540, 734))

    delivered = (
        (288, 96, "Neo4j graph", ["485 nodes,", "2,429 relationships"], "via kg/loader.py"),
        (420, 80, "Report figures", ["six PDFs"], "via figures.py"),
    )
    for y, h, name, lines, via in delivered:
        s.rounded(764, y, 170, h, edge=DELIVERED, fill=DELIVERED_FILL, radius=22)
        s.text(780, y + 26, name, size=t_name, weight="semibold", fit=(764, 934))
        cursor = y + 44
        for line in lines:
            s.text(780, cursor, line, size=t_body, colour=MUTED, fit=(764, 934))
            cursor += 18
        s.text(780, cursor + 4, via, size=t_body, colour=DELIVERED, mono=True, fit=(764, 934))

    legend = (
        (16, "stage, Python module", STAGE, STAGE_FILL, 4.0, False, False),
        (226, "artefact on disk, JSON Lines", ARTEFACT, ARTEFACT_FILL, 0.0, True, False),
        (470, "delivered output", DELIVERED, DELIVERED_FILL, 11.0, False, False),
        (640, "external source or hand-made input", HAIR, EXTERNAL_FILL, 3.0, False, True),
    )
    for x, label, edge, fill, radius, is_tile, dashed in legend:
        if is_tile:
            s.tile(x, 545, 26, 16, edge=edge, fill=fill, lw=1.6)
        else:
            s.rounded(x, 545, 26, 16, edge=edge, fill=fill, lw=1.5, radius=radius, dashed=dashed)
        s.text(x + 34, 558, label, size=t_body, colour=MUTED)

    s.check()
    return s.save("pipeline_architecture")


def ontology_schema() -> Path:
    """Section 3.1. The nine entity types and the nine relations, as loaded.

    Two details in the chapter's table are made structural rather than stated. Solvent and
    Condition hang off SynthesisMethod, so they are unreachable from MOF except through it,
    and the method is the only node in the connector colour and the only one tagged. And
    MENTIONED_IN is drawn once, dashed, from "any entity", outside the eight-relation flow,
    because the pipeline attaches it from passage metadata and no extractor ever emits it.
    """
    s = Sheet(960, 600)
    t_hub, t_name, t_rel, t_body = 21.0, 18.0, 15.0, 14.0

    s.text(10, 42, "9 entity types, 9 relations", size=t_body, colour=MUTED)
    s.text(10, 60, "configs/ontology.json, v0.2", size=t_body, colour=MUTED)
    for i, line in enumerate(
        [
            "Solvent and Condition attach to",
            "SynthesisMethod, not to the MOF:",
            "the method acts as a connector.",
        ]
    ):
        s.text(660, 42 + 18 * i, line, size=t_body)

    for pts in (
        [(360, 100), (360, 118), (80, 118), (80, 190)],
        [(420, 100), (420, 132), (240, 132), (240, 190)],
        [(480, 100), (480, 190)],
        [(540, 100), (540, 132), (720, 132), (720, 190)],
        [(600, 100), (600, 118), (880, 118), (880, 190)],
        [(400, 258), (400, 330)],
        [(560, 258), (560, 330)],
        [(720, 258), (720, 430), (560, 430), (560, 398)],
    ):
        s.flow(pts)
    s.flow([(300, 515), (392, 515)], colour=HAIR, lw=1.8, dashed=True)

    for x, y, name in (
        (92, 155, "USES_PRECURSOR"),
        (252, 155, "USES_LINKER"),
        (492, 155, "SYNTHESIZED_BY"),
        (732, 155, "HAS_PROPERTY"),
        (892, 155, "USED_IN"),
        (412, 300, "IN_SOLVENT"),
        (572, 300, "AT_CONDITION"),
        (568, 422, "MEASURED_AT"),
    ):
        s.text(x, y, name, size=t_rel, mono=True)
    s.text(342, 478, "MENTIONED_IN", size=t_rel, mono=True, colour="#777777", ha="center")

    # The hub carries a heavier outline and a tint as well as the larger name, so its
    # prominence does not depend on colour either.
    s.rounded(330, 20, 300, 80, edge=STAGE, fill="#F0F7FB", lw=2.6, radius=7)
    s.text(346, 50, "MOF", size=t_hub, weight="bold", fit=(330, 630))
    s.text(346, 70, "name, formula,", size=t_body, colour=MUTED, fit=(330, 630))
    s.text(346, 88, "csd_refcode, topology", size=t_body, colour=MUTED, fit=(330, 630))

    entities = (
        (8, 190, 144, "MetalPrecursor", ["name, formula,", "metal, amount"], 17.0),
        (168, 190, 144, "OrganicLinker", ["name, abbreviation,", "formula, amount"], t_name),
        (648, 190, 144, "Property", ["name, value, unit,", "technique"], t_name),
        (808, 190, 144, "Application", ["name, domain"], t_name),
        (328, 330, 144, "Solvent", ["name, ratio,", "volume"], t_name),
        (488, 330, 144, "Condition", ["type, value, unit"], t_name),
    )
    for x, y, w, name, lines, size in entities:
        s.rounded(x, y, w, 68, edge=STAGE, fill="white", lw=1.6)
        s.text(x + 14, y + 26, name, size=size, weight="semibold", fit=(x, x + w))
        for i, line in enumerate(lines):
            s.text(x + 14, y + 44 + 18 * i, line, size=t_body, colour=MUTED, fit=(x, x + w))

    s.rounded(328, 190, 304, 68, edge=CONNECTOR, fill=DELIVERED_FILL, lw=2.2)
    s.text(342, 216, "SynthesisMethod", size=t_name, weight="semibold", fit=(328, 632))
    s.text(342, 234, "name, process_type", size=t_body, colour=MUTED, fit=(328, 632))
    s.text(
        620,
        249,
        "connector",
        size=t_body,
        colour=CONNECTOR,
        italic=True,
        ha="right",
        fit=(328, 632),
    )

    s.rounded(120, 490, 180, 50, edge=HAIR, fill=EXTERNAL_FILL, lw=1.5, radius=4, dashed=True)
    s.text(136, 521, "any entity", size=17.0, weight="semibold", colour=MUTED, fit=(120, 300))
    s.rounded(400, 478, 220, 76, edge=ARTEFACT, fill=ARTEFACT_FILL, radius=6)
    s.text(416, 510, "Paper", size=t_name, weight="semibold", fit=(400, 620))
    s.text(416, 528, "doi, title, authors,", size=t_body, colour=MUTED, fit=(400, 620))
    s.text(416, 546, "year, journal, url", size=t_body, colour=MUTED, fit=(400, 620))
    s.text(650, 505, "Attached by the pipeline from passage", size=t_body)
    s.text(650, 523, "metadata, never produced by an extractor.", size=t_body)

    s.flow([(10, 574), (46, 574)])
    s.text(56, 579, "produced by an extractor, eight relations", size=t_body, colour=MUTED)
    s.flow([(400, 574), (436, 574)], colour=HAIR, lw=1.8, dashed=True)
    s.text(446, 579, "attached by the pipeline, one relation", size=t_body, colour=MUTED)

    s.check()
    return s.save("ontology_schema")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for builder in (ontology_schema, pipeline_architecture):
        path = builder()
        print(f"  wrote {path.relative_to(REPO)}.pdf and .png")


if __name__ == "__main__":
    main()
