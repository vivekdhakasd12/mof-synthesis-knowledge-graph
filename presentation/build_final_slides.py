"""Build the Case Study 2 final presentation (.pptx).

Run with uv so python-pptx does not need a global install:
    uv run --with python-pptx python presentation/build_final_slides.py

Output: presentation/Case_Study_2_Final_Presentation.pptx

Thirteen slides, matching the length of the exposé deck built in June. No slide
limit is recorded anywhere in the repository, so that deck is the precedent;
SLIDES below lists the running order, and dropping an entry is the way to
shorten the deck rather than cramming two topics onto one slide.

Every number here is taken from the final report and its artefacts
(data/processed/evaluation.json, agreement_analysis.json, results_gold.jsonl).
Nothing is estimated. The figures are the same files the report embeds, so the
deck cannot disagree with the document.

Visual style matches presentation/build_slides.py and docs/expose.html:
SRH orange #E64415 accent, Lato, srh_logo.jpg, white ground, charcoal text,
thin gray rules.

Writing rules: no em dashes. En dash only in number ranges and in the term
"Metal-Organic Framework" (rendered with an en dash to match the exposé).
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

# ---- SRH palette, identical to the exposé deck -----------------------------
ORANGE = RGBColor(0xE6, 0x44, 0x15)
INK = RGBColor(0x1A, 0x1A, 0x1A)
GRAY = RGBColor(0x55, 0x55, 0x55)
RULE = RGBColor(0xE3, 0xE3, 0xE3)
RULE2 = RGBColor(0xBB, 0xBB, 0xBB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FAINT = RGBColor(0xFA, 0xF6, 0xF4)

FONT = "Lato"
ND = "–"

REPO = Path(__file__).resolve().parents[1]
LOGO = str(REPO / "docs" / "assets" / "srh_logo.jpg")
FIG = REPO / "docs" / "report" / "figures"
LOGO_RATIO = 457 / 591

SW, SH = Inches(13.333), Inches(7.5)
prs = Presentation()
prs.slide_width, prs.slide_height = SW, SH
BLANK = prs.slide_layouts[6]

SLIDES = [
    "Title",
    "The problem",
    "Research questions",
    "What was built",
    "The gold standard",
    "How accuracy was measured",
    "Results: overall",
    "Results: per field",
    "The headline finding",
    "Why the baseline fails",
    "The knowledge graph",
    "What this cannot show",
    "Conclusion",
]


# ---- helpers, lifted from build_slides.py so the two decks match -----------
def _no_shadow(shape):
    el = shape._element
    style = el.find(qn("p:style"))
    if style is not None:
        el.remove(style)
    if el.spPr.find(qn("a:effectLst")) is None:
        el.spPr.append(
            parse_xml(
                '<a:effectLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"/>'
            )
        )


def slide():
    return prs.slides.add_slide(BLANK)


def R(txt, size=14, color=INK, bold=False, italic=False):
    return (txt, size, color, bold, italic)


def text(s, x, y, w, h, paras, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
         space_after=6, line_spacing=1.12):
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.space_before = Pt(0)
        p.line_spacing = line_spacing
        for (txt, size, color, bold, italic) in para:
            run = p.add_run()
            run.text = txt
            run.font.size = Pt(size)
            run.font.color.rgb = color
            run.font.bold = bold
            run.font.italic = italic
            run.font.name = FONT
    return tb


def rule(s, x, y, w, color=RULE, pt=1.0):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, Pt(pt))
    r.fill.solid()
    r.fill.fore_color.rgb = color
    r.line.fill.background()
    r.shadow.inherit = False
    _no_shadow(r)
    return r


def box(s, x, y, w, h, fill=None, line=None, pt=1.0):
    b = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    if fill is None:
        b.fill.background()
    else:
        b.fill.solid()
        b.fill.fore_color.rgb = fill
    if line is None:
        b.line.fill.background()
    else:
        b.line.color.rgb = line
        b.line.width = Pt(pt)
    b.shadow.inherit = False
    _no_shadow(b)
    return b


def logo_small(s):
    w = Inches(0.95)
    s.shapes.add_picture(LOGO, Inches(0.6), Inches(0.46), width=w,
                         height=Emu(int(w * LOGO_RATIO)))


def pagenum(s, n):
    text(s, Inches(12.5), Inches(7.04), Inches(0.7), Inches(0.3),
         [[R(str(n), 10, RULE2)]], align=PP_ALIGN.RIGHT)


def header(s, num, title, n):
    logo_small(s)
    runs = []
    if num:
        runs.append(R(num + "   ", 27, ORANGE, bold=True))
    runs.append(R(title, 27, INK, bold=True))
    text(s, Inches(0.62), Inches(1.42), Inches(12.1), Inches(0.7), [runs])
    rule(s, Inches(0.64), Inches(2.18), Inches(12.05), color=RULE, pt=1.2)
    pagenum(s, n)
    return Inches(2.5)


def bullets(s, x, y, w, items, size=15, gap=9, lead=1.16):
    paras = []
    for txt, lvl in items:
        if lvl == 0:
            paras.append([R("•  ", size, ORANGE, bold=True), R(txt, size, INK)])
        else:
            paras.append([R("      –  ", size - 1, ORANGE), R(txt, size - 1, GRAY)])
    return text(s, x, y, w, Inches(4.4), paras, space_after=gap, line_spacing=lead)


def figure(s, name, top, height_in, left_in=None):
    """Centre a report figure horizontally at the given height."""
    from PIL import Image  # only needed to preserve aspect

    path = FIG / name
    with Image.open(path) as im:
        ratio = im.height / im.width
    h = Inches(height_in)
    w = Emu(int(h / ratio))
    x = Emu(int((SW - w) / 2)) if left_in is None else Inches(left_in)
    s.shapes.add_picture(str(path), x, top, width=w, height=h)


def statrow(s, y, cells, w_each=3.0, x0=0.62):
    """A row of big-number tiles. cells: list of (number, label)."""
    for i, (num, label) in enumerate(cells):
        x = Inches(x0 + i * (w_each + 0.12))
        text(s, x, y, Inches(w_each), Inches(0.6),
             [[R(num, 33, ORANGE, bold=True)]])
        text(s, x, Emu(int(y + Inches(0.62))), Inches(w_each), Inches(0.5),
             [[R(label, 12.5, GRAY)]], line_spacing=1.1)


# ===========================================================================
# 1. Title
# ===========================================================================
s = slide()
lw = Inches(1.7)
s.shapes.add_picture(LOGO, Emu(int((SW - lw) / 2)), Inches(1.05), width=lw,
                     height=Emu(int(lw * LOGO_RATIO)))
text(s, Inches(1.0), Inches(2.75), Inches(11.33), Inches(0.4),
     [[R("C A S E   S T U D Y   2      ·      F I N A L", 14, GRAY, bold=True)]],
     align=PP_ALIGN.CENTER)
text(s, Inches(1.0), Inches(3.25), Inches(11.33), Inches(1.3),
     [[R(f"Building and Validating a Metal{ND}Organic Framework", 31, INK, bold=True)],
      [R("Synthesis Knowledge Graph with Large Language Models", 31, INK, bold=True)]],
     align=PP_ALIGN.CENTER, line_spacing=1.18)
rule(s, Inches(5.97), Inches(4.92), Inches(1.4), color=ORANGE, pt=2.4)
text(s, Inches(1.0), Inches(5.32), Inches(11.33), Inches(1.5),
     [[R("Devendra Singh Dhakad", 16, INK, bold=True),
       R("      ·      ", 16, RULE2),
       R("Matriculation No. 100004684", 16, GRAY)],
      [R("M.Sc. Data Science and Artificial Intelligence", 14, GRAY)],
      [R("Supervisor: Prof. Dr. Mehrdad Jalali", 14, GRAY)],
      [R("SRH University of Applied Sciences Heidelberg", 14, GRAY)],
      [R("September 2026", 12, RULE2)]],
     align=PP_ALIGN.CENTER, space_after=5)

# ===========================================================================
# 2. The problem
# ===========================================================================
s = slide()
y = header(s, "1", "The problem", 2)
bullets(s, Inches(0.62), y, Inches(7.4), [
    ("MOFs are porous crystals built from metal nodes and organic linkers. "
     "Over 100,000 synthesised structures are recorded in the CSD.", 0),
    ("Applications span CO2 capture, gas storage, catalysis, sensing and drug delivery.", 0),
    ("How any given MOF is actually made (precursor, linker, solvent, method, "
     "temperature, time) stays locked in the prose of tens of thousands of papers.", 0),
    ("Existing text-mined databases were built with rule-based systems whose own "
     "authors report that implicit synthesis routes are hard to extract.", 0),
], size=15.5)
box(s, Inches(8.35), y, Inches(4.35), Inches(2.35), fill=FAINT)
text(s, Inches(8.68), Emu(int(y + Inches(0.3))), Inches(3.7), Inches(1.9),
     [[R("The gap", 13, ORANGE, bold=True)],
      [R("No published study measures LLM MOF extraction "
         "field by field against both expert annotation and a "
         "rule-based baseline, while reporting what each "
         "configuration costs.", 14, INK)]],
     space_after=8, line_spacing=1.2)

# ===========================================================================
# 3. Research questions
# ===========================================================================
s = slide()
y = header(s, "2", "Research questions", 3)
bullets(s, Inches(0.62), y, Inches(12.0), [
    ("RQ1  Per-field accuracy: LLMs against a rule-based baseline built from the "
     "same domain vocabulary.", 0),
    ("RQ2  Which prompting strategy is most reliable: zero-shot, few-shot, "
     "schema-guided, chain-of-thought.", 0),
    ("RQ3  Where and why extractions disagree with the DigiMOF and SynMOF "
     "reference databases.", 0),
    ("RQ4  Open-weight models against commercial APIs on accuracy, cost and latency.", 0),
    ("RQ5  Can the resulting knowledge graph answer aggregation queries across "
     "hundreds of papers.", 0),
], size=15.5, gap=13)
text(s, Inches(0.62), Inches(6.35), Inches(12.0), Inches(0.6),
     [[R("Answered: RQ1, RQ2, RQ4, RQ5.    ", 14, INK, bold=True),
       R("RQ3 could not be answered; the reason is on slide 12.", 14, GRAY)]])

# ===========================================================================
# 4. What was built
# ===========================================================================
s = slide()
y = header(s, "3", "What was built", 4)
figure(s, "pipeline_architecture.png", Emu(int(y - Inches(0.18))), 4.0)
text(s, Inches(0.62), Inches(6.35), Inches(12.0), Inches(0.5),
     [[R("Six stages, each writing a JSON Lines file the next one reads. Any stage can be "
         "rerun without rerunning the others, and every intermediate is inspectable.",
         13.5, GRAY)]])

# ===========================================================================
# 5. The gold standard
# ===========================================================================
s = slide()
y = header(s, "4", "The gold standard", 5)
bullets(s, Inches(0.62), y, Inches(7.3), [
    ("100 passages annotated by hand, yielding 138 triples. Drawn by a seeded "
     "stratified sample.", 0),
    ("90 from the synthesis-flagged pool, plus 10 unflagged controls so the "
     "pre-filter's own miss rate is measurable rather than assumed.", 0),
    ("Annotation used an ontology-constrained interface: an invalid triple cannot "
     "be created.", 0),
], size=15.5)
box(s, Inches(8.15), y, Inches(4.55), Inches(2.75), fill=None, line=ORANGE, pt=1.4)
text(s, Inches(8.48), Emu(int(y + Inches(0.32))), Inches(3.9), Inches(2.2),
     [[R("Why it was not pre-filled by a model", 13, ORANGE, bold=True)],
      [R("The gold standard is the instrument the models are measured against. "
         "Generating it with a language model would make the evaluation circular: "
         "any error the models share would score as correct.", 13.5, INK)]],
     space_after=8, line_spacing=1.2)
statrow(s, Inches(5.75), [("399", "papers collected"), ("22,086", "passages segmented"),
                          ("794", "flagged as synthesis"), ("138", "triples, annotated by hand")],
        w_each=2.9)

# ===========================================================================
# 6. How accuracy was measured
# ===========================================================================
s = slide()
y = header(s, "5", "How accuracy was measured", 6)
figure(s, "ontology_schema.png", Emu(int(y - Inches(0.1))), 3.15)
bullets(s, Inches(0.62), Inches(5.85), Inches(12.0), [
    ("Matching is per passage and per relation, greedy one-to-one, so no gold triple "
     "is credited twice and nothing matches across passages.", 0),
    ("One concession is declared: IN_SOLVENT and AT_CONDITION are scored on the object "
     "alone, because an annotation-tool defect left the MOF name in the subject slot.", 0),
], size=13.5, gap=6)

# ===========================================================================
# 7. Results: overall
# ===========================================================================
s = slide()
y = header(s, "6", "Results: ten configurations, 3.06 USD", 7)
figure(s, "fig1_cost_vs_f1.png", Emu(int(y - Inches(0.05))), 3.5)
bullets(s, Inches(0.62), Inches(6.1), Inches(12.0), [
    ("Every language-model configuration beats the rule-based baseline. The weakest "
     "scores 0.191 against the baseline's 0.112.", 0),
    ("The strongest configuration is also among the cheapest.", 0),
], size=13.5, gap=5)

# ===========================================================================
# 8. Results: per field
# ===========================================================================
s = slide()
y = header(s, "7", "Per field, and a pre-registered prediction", 8)
figure(s, "fig2_per_field_f1.png", Emu(int(y - Inches(0.05))), 3.3, left_in=0.62)
box(s, Inches(7.55), y, Inches(5.15), Inches(3.25), fill=FAINT)
text(s, Inches(7.9), Emu(int(y + Inches(0.28))), Inches(4.5), Inches(2.7),
     [[R("Committed 23 August, before any results existed", 13, ORANGE, bold=True)],
      [R("“The LLM margin should be largest on USES_PRECURSOR, USES_LINKER "
         "and SYNTHESIZED_BY, and smallest on AT_CONDITION and IN_SOLVENT.”",
         13, INK, italic=True)],
      [R("SYNTHESIZED_BY has one gold triple, so it cannot be tested. On the four "
         "fields that can: +0.42, +0.31, +0.25, +0.17. Precursor and linker lead, "
         "solvent and condition trail, as predicted.", 13, INK)]],
     space_after=9, line_spacing=1.2)
text(s, Inches(0.62), Inches(6.05), Inches(12.0), Inches(0.5),
     [[R("AT_CONDITION scores measure annotation granularity, not extraction quality, and are "
         "excluded from every conclusion. Excluding it, the best configuration averages "
         "about 0.53.", 13, GRAY)]])

# ===========================================================================
# 9. The headline finding
# ===========================================================================
s = slide()
y = header(s, "8", "The cheap model beat the expensive one", 9)
statrow(s, y, [("0.364", "gpt-4o-mini, schema-guided\n0.028 USD"),
               ("0.245", "gpt-4o, few-shot\n1.289 USD"),
               ("47×", "cost difference, in favour\nof the weaker model"),
               ("3.06", "USD, every experiment\nin this study")], w_each=2.9)
rule(s, Inches(0.64), Inches(4.05), Inches(12.05), color=RULE, pt=1.0)
bullets(s, Inches(0.62), Inches(4.35), Inches(12.0), [
    ("My first explanation was that the larger model over-extracts, and that verbosity "
     "becomes false positives. I tested it by counting emitted triples.", 0),
    ("It is wrong, and wrong in the opposite direction. gpt-4o emits fewer triples than "
     "gpt-4o-mini in all four strategies, by 32, 29, 19 and 6 percent.", 0),
    ("The gap is recall, not precision. gpt-4o recovers 39 of 138 gold triples on "
     "schema-guided against gpt-4o-mini's 61, at near-identical precision.", 0),
    ("Every prompt says to omit when unsure. Whether gpt-4o is more cautious or simply "
     "more obedient, this design cannot tell apart.", 0),
], size=15, gap=10)

# ===========================================================================
# 10. Why the baseline fails
# ===========================================================================
s = slide()
y = header(s, "9", "Why the rule baseline fails", 10)
figure(s, "fig6_baseline_failure_modes.png", Emu(int(y - Inches(0.05))), 2.95)
bullets(s, Inches(0.62), Inches(5.6), Inches(12.0), [
    ("The baseline names a MOF in only 121 of 794 synthesis passages, about 15 percent. "
     "Five of the eight relations take MOF as their subject, so that one failure "
     "suppresses most of what it could otherwise extract.", 0),
    ("Neither dominant cause is a lexicon gap. The highest-leverage fix is coreference "
     "across a paper and table parsing, not a bigger dictionary.", 0),
], size=13.5, gap=6)

# ===========================================================================
# 11. The knowledge graph
# ===========================================================================
s = slide()
y = header(s, "10", "The knowledge graph (RQ5)", 11)
statrow(s, y, [("485", "distinct nodes"), ("2,429", "relationships"),
               ("182", "source papers"), ("0", "provenance violations")], w_each=2.9)
rule(s, Inches(0.64), Inches(4.05), Inches(12.05), color=RULE, pt=1.0)
bullets(s, Inches(0.62), Inches(4.35), Inches(7.6), [
    ("Every entity carries a MENTIONED_IN edge to the paper it came from. Provenance is "
     "verified by query, not asserted: the violations query returns zero rows.", 0),
    ("Cross-paper aggregation works. Solvothermal appears in 61 papers across 30 MOFs, "
     "hydrothermal in 43 across 12.", 0),
], size=14.5, gap=10)
box(s, Inches(8.5), Inches(4.3), Inches(4.2), Inches(2.1), fill=FAINT)
text(s, Inches(8.83), Inches(4.58), Inches(3.55), Inches(1.6),
     [[R("An open question", 13, ORANGE, bold=True)],
      [R("DigiMOF reported more hydrothermal than solvothermal records and called that "
         "surprising. This corpus shows the opposite ordering. Recorded, not resolved.",
         13, INK)]],
     space_after=8, line_spacing=1.2)

# ===========================================================================
# 12. What this cannot show
# ===========================================================================
s = slide()
y = header(s, "11", "What this cannot show", 12)
bullets(s, Inches(0.62), y, Inches(12.0), [
    ("RQ3 is not answered. DigiMOF and SynMOF are keyed by CSD refcode, this corpus by "
     "DOI and by the MOF name a paper uses, and joining them needs a licensed mapping. "
     "The overlap is undetermined, which is not the same as zero.", 0),
    ("What could be measured: the two databases agree on the metal 98.9 percent "
     "across the 509 MOFs they share.", 1),
    ("0.364 micro-F1 is below the 0.80 target in the exposé, and is a lower bound: "
     "strict surface-form matching scores correct extractions as failures.", 0),
    ("The gold standard is 100 passages, not the 150 to 200 planned, and has a single "
     "annotator, so no inter-annotator agreement can be computed.", 0),
    ("Two open-weight configurations hit a free-tier daily cap and were deleted rather "
     "than scored. A partial run makes a rate-limited model look like a weak one.", 0),
    ("Every configuration ran once, so no variance is reported.", 0),
], size=14.5, gap=11)

# ===========================================================================
# 13. Conclusion
# ===========================================================================
s = slide()
y = header(s, "12", "Conclusion", 13)
bullets(s, Inches(0.62), y, Inches(7.5), [
    ("Language models beat the rule baseline on every configuration tested, and the "
     "testable part of a pre-registered prediction held.", 0),
    ("The cheaper model won because the larger one extracts less. That is measured; "
     "why it extracts less is not.", 0),
    ("On the like-for-like zero-shot comparison, an open-weight model reached about two "
     "thirds of the commercial F1 at zero marginal cost.", 0),
    ("A provenance-complete knowledge graph, verified by query.", 0),
], size=14.5, gap=10)
box(s, Inches(8.35), y, Inches(4.35), Inches(3.95), fill=None, line=RULE, pt=1.2)
text(s, Inches(8.68), Emu(int(y + Inches(0.3))), Inches(3.7), Inches(3.45),
     [[R("Future work", 13, ORANGE, bold=True)],
      [R("Obtain a name-to-refcode mapping and close RQ3.", 13.5, INK)],
      [R("Rerun without the \u201comit when unsure\u201d instruction, to separate "
         "caution from obedience.", 13.5, INK)],
      [R("Repair the condition evaluation and add identifier resolution.", 13.5, INK)],
      [R("Enlarge the gold standard and add a second annotator.", 13.5, INK)]],
     space_after=9, line_spacing=1.2)

# ---- speaker notes ---------------------------------------------------------
# presentation/speaker_script.md is the single source for what is said on each slide. It is
# attached here, at build time, so the notes in Presenter View can never describe a slide
# that has since changed: rebuilding the deck re-reads the script.
SCRIPT = REPO / "presentation" / "speaker_script.md"


def load_notes(path: Path) -> dict[int, str]:
    import re

    notes: dict[int, str] = {}
    for block in re.split(r"^## Slide ", path.read_text(encoding="utf-8"), flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        number = int(head.split(":", 1)[0])
        body = body.split("\n---", 1)[0].strip()
        notes[number] = body.replace("**", "")
    return notes


notes = load_notes(SCRIPT)
slides = list(prs.slides)
missing = [n for n in range(1, len(slides) + 1) if n not in notes]
if missing:
    raise SystemExit(f"speaker_script.md has no section for slide(s) {missing}")
for n, sl in enumerate(slides, start=1):
    sl.notes_slide.notes_text_frame.text = notes[n]

out = REPO / "presentation" / "Case_Study_2_Final_Presentation.pptx"
prs.save(str(out))
print(f"wrote {out.relative_to(REPO)}  ({len(slides)} slides, speaker notes on every one)")
