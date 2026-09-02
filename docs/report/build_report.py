"""Render the report chapters to LaTeX and compile the submission PDF.

This is the only builder. An earlier headless-Chrome HTML path was retired once the LaTeX
output covered the same ground and added what a submitted thesis needs: a contents page
whose entries jump to their section, a bookmark tree for the reader's sidebar, numbered
figures that can be cross-referenced, and clickable DOIs.

**The markdown chapters stay the single source of truth.** Nothing here is authored by
hand, which is why the converter has to handle the markdown subset the chapters actually
use rather than a hand-tidied copy of it.

Engine is Tectonic (XeTeX), chosen because it resolves and caches its own packages, so a
reader does not need a full TeX Live installation to rebuild the document.

Typographic decisions taken here, and why, since they are otherwise invisible:

*The measure is 13 cm, not 16 cm.* At 11pt the old text block ran about 95 characters to
the line, roughly three and a half alphabet lengths against a comfortable two to three. The
recovered space is not padding: it becomes a named outer column, ``marginparwidth``, that
the wide figures bleed into, so the two-panel charts and the two structural diagrams get
16.7 cm while the prose keeps a readable line.

*Figures are placed at the width they were generated at.* Every figure is produced by a
Python module at either the measure or the measure plus the margin column, so nothing is
rescaled on placement and the label sizes in one figure match the label sizes in the next.
``WIDE_FIGURES`` records which stems are the wide class.

*Tables can now be numbered.* A table followed by a paragraph beginning ``**Table N.**`` is
emitted as a numbered float with that caption, exactly mirroring the figure convention, so
the text can refer to "Table 3" and have it mean something. A table with no such paragraph
still renders as it always did, so adding captions is incremental rather than a flag day.

*Colour is pulled back off the furniture.* SRH orange marks the chapter kicker and external
links, and nothing else. Internal links, section numbers and contents entries are ink, so
the contents page reads as a contents page rather than as a field of orange.

Run:  python docs/report/build_report.py
      python docs/report/build_report.py --no-pdf     (write the .tex only)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import mistune

REPORT = Path(__file__).resolve().parent
REPO = REPORT.parents[1]
ASSETS = REPO / "docs" / "assets"
TEX = REPORT / "report.tex"
PDF = REPORT / "report.pdf"

CHAPTERS = [
    ("01_introduction.md", "Introduction"),
    ("02_state_of_the_art.md", "State of the Art"),
    ("03_methodology.md", "Methodology"),
    ("04_implementation.md", "Implementation"),
    ("05_results.md", "Results"),
    ("06_discussion.md", "Discussion"),
    ("07_limitations.md", "Limitations and Threats to Validity"),
    ("08_conclusion.md", "Conclusion and Outlook"),
    ("09_references.md", "References"),
]

TITLE = (
    "Building and Validating a Metal--Organic Framework Synthesis "
    "Knowledge Graph with Large Language Models"
)
AUTHOR = "Devendra Singh Dhakad"
MATRICULATION = "100004684"
PROGRAMME = "M.Sc. Data Science and Artificial Intelligence"
SUPERVISOR = "Prof. Dr. Mehrdad Jalali"
UNIVERSITY = "SRH University of Applied Sciences Heidelberg"
MODULE = "Case Study 2"
SUBMITTED = "September 2026"

# Figures generated at the measure plus the outer margin column rather than at the measure.
# These are the ones with two panels or a wide aspect, where 13 cm crushes the labels.
WIDE_FIGURES = {
    "fig5_corpus_and_threshold",
    "fig6_baseline_failure_modes",
    "pipeline_architecture",
    "ontology_schema",
}
WIDE_LEN = r"\dimexpr\linewidth+\marginparsep+\marginparwidth\relax"

# Latin Modern, the default, has no glyph for the Unicode subscript block, so a bare
# "Cu\u2083(BTC)\u2082" silently loses its digits. Mapping them onto \textsubscript keeps
# the chemistry readable and typesets better than the raw glyphs would anyway.
SUBSCRIPTS = {
    "\u2080": "0",
    "\u2081": "1",
    "\u2082": "2",
    "\u2083": "3",
    "\u2084": "4",
    "\u2085": "5",
    "\u2086": "6",
    "\u2087": "7",
    "\u2088": "8",
    "\u2089": "9",
}

# Escaped in this order: the backslash has to go first or it would escape the escapes.
TEX_ESCAPES = [
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\textasciicircum{}"),
]

# A caption in the markdown reads "**Figure 4.** Precision against recall...". LaTeX
# numbers figures itself, so the manual number is stripped to avoid "Figure 4: Figure 4."
FIG_PREFIX = re.compile(r"^\s*Figure\s+\d+\.\s*")
TAB_PREFIX = re.compile(r"^\s*Table\s+\d+\.\s*")
HEADING_NUMBER = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+")


def esc(text: str) -> str:
    """Escape LaTeX specials and rewrite characters the default font cannot set."""
    for char, replacement in TEX_ESCAPES:
        text = text.replace(char, replacement)
    for char, digit in SUBSCRIPTS.items():
        text = text.replace(char, rf"\textsubscript{{{digit}}}")
    return text


def breakable(text: str) -> str:
    """Permit line breaks inside a code span, without inserting a hyphen.

    A \\texttt run does not break, so a long monospace value such as a chemical name or a
    module path can push a table past the measure with no way to wrap. Automatic
    hyphenation is the wrong remedy here: a hyphen inserted into
    "1-ethyl-3-methylimidazolium" would read as part of the compound's name. Instead a
    zero-width break opportunity is added after separators that are already there, so a
    break can only fall where the string already divides.
    """
    for sep in ("-", "/", "\\_", "."):
        text = text.replace(sep, sep + "\\allowbreak{}")
    return text


def inline(nodes: list[dict[str, Any]]) -> str:
    """Render inline markdown nodes. Everything reaching a text leaf gets escaped."""
    out: list[str] = []
    for node in nodes:
        kind = node["type"]
        if kind == "text":
            out.append(esc(node["raw"]))
        elif kind == "strong":
            out.append(rf"\textbf{{{inline(node['children'])}}}")
        elif kind == "emphasis":
            out.append(rf"\emph{{{inline(node['children'])}}}")
        elif kind == "codespan":
            # \texttt rather than \verb: \verb cannot appear inside another argument,
            # which it would here whenever a code span sits inside a heading or a cell.
            out.append(rf"\texttt{{{breakable(esc(node['raw']))}}}")
        elif kind == "link":
            out.append(rf"\href{{{node['attrs']['url']}}}{{{inline(node['children'])}}}")
        elif kind == "linebreak":
            out.append("\\\\\n")
        elif kind == "softbreak":
            out.append(" ")
        elif kind == "image":
            out.append(esc(inline(node.get("children", []))))
        else:
            out.append(inline(node.get("children", [])))
    return "".join(out)


def figure(url: str, caption: str) -> str:
    """A float carrying the figure, preferring the vector version for print.

    A stem in WIDE_FIGURES is set across the measure plus the outer margin column and
    left-aligned in a \\makebox, so it bleeds into that margin rather than being centred
    and overhanging both sides. Its caption is set to the same width so the two align.
    """
    path = (REPORT / url).resolve()
    vector = path.with_suffix(".pdf")
    if vector.is_file():
        path = vector
    rel = path.relative_to(REPORT).as_posix()
    stem = Path(url).stem
    label = "fig:" + stem
    wide = stem in WIDE_FIGURES
    width = WIDE_LEN if wide else r"\linewidth"
    graphic = f"\\includegraphics[width={width}]{{{rel}}}"
    if wide:
        # The graphic bleeds into the outer column, but the caption keeps the prose
        # measure. Widening the caption to match made LaTeX centre a box wider than the
        # text block, overhanging both margins by half the overhang each.
        body = f"\\noindent\\makebox[\\linewidth][l]{{{graphic}}}\n"
    else:
        body = f"\\centering\n{graphic}\n"
    return (
        "\\begin{figure}[H]\n" + body + f"\\caption{{{caption}}}\n\\label{{{label}}}\n"
        "\\end{figure}\n"
    )


def tabular(node: dict[str, Any]) -> str:
    """Render a markdown table's body with booktabs rules.

    Column type is chosen from the content rather than fixed: a column holding long text
    becomes a wrapping X column, a short one stays flush. Without this the wide results
    tables run off the page edge.

    The block is left-aligned to the text block rather than centred. A centred table whose
    width comes from its content sits as an island with unequal margins, and no two tables
    in the document line up with each other or with the prose.
    """
    head: list[str] = []
    body: list[list[str]] = []
    for section in node["children"]:
        if section["type"] == "table_head":
            head = [inline(c["children"]) for c in section["children"]]
        else:
            for row in section["children"]:
                body.append([inline(c["children"]) for c in row["children"]])

    widths = [max((len(r[i]) for r in body), default=0) for i in range(len(head))]
    # The header is measured too. A narrow numeric column under a long header ("Rule
    # baseline F1" over "0.13") cannot wrap if it is set as `r`, and silently pushes the
    # table past the measure; as `R` the header wraps and the numbers stay right-aligned.
    heads = [len(h) for h in head]

    def column(i: int, body_w: int, head_w: int) -> str:
        if body_w > 18:
            return "L"
        if head_w > 10:
            return "L" if i == 0 else "R"
        return "l" if i == 0 else "r"

    spec = "".join(column(i, w, heads[i]) for i, w in enumerate(widths))
    if not set("LR") & set(spec):  # tabularx needs a stretchable column to distribute
        spec = "l" + spec[1:]
        env, arg = "tabular", f"{{@{{}}{spec}@{{}}}}"
    else:
        env, arg = "tabularx", f"{{\\linewidth}}{{@{{}}{spec}@{{}}}}"

    rows = "\n".join(" & ".join(r) + r" \\" for r in body)
    return (
        "\\small\\setlength{\\tabcolsep}{6pt}\n"
        f"\\begin{{{env}}}{arg}\n\\toprule\n"
        + " & ".join(rf"\textbf{{{h}}}" for h in head)
        + " \\\\\n\\midrule\n"
        + rows
        + f"\n\\bottomrule\n\\end{{{env}}}\n"
    )


def table_float(node: dict[str, Any], caption: str, key: str) -> str:
    """A numbered table float, for a table the markdown gave a caption to."""
    return (
        "\\begin{table}[H]\n"
        f"\\caption{{{caption}}}\n\\label{{tab:{key}}}\n"
        "\\noindent\n" + tabular(node) + "\\end{table}\n"
    )


def table_plain(node: dict[str, Any]) -> str:
    """An uncaptioned table, set as its own block between two paragraphs.

    The \\par on each side is load-bearing. A tabular is a horizontal box, so without an
    explicit paragraph break the prose that follows continues on the same line and sets
    itself alongside the table instead of beneath it. The previous builder centred its
    tables, and the center environment supplied that break as a side effect; left-aligning
    them to the text block removed it.
    """
    return "\\par\\medskip\n\\begingroup\n" + tabular(node) + "\\endgroup\n\\par\\medskip\n"


def blocks(nodes: list[dict[str, Any]]) -> str:
    """Render block-level nodes, pairing each image and each table with its caption."""
    out: list[str] = []
    pending_figure: str | None = None
    pending_table: dict[str, Any] | None = None
    table_seq = 0

    def flush_figure() -> None:
        nonlocal pending_figure
        if pending_figure:
            out.append(figure(pending_figure, ""))
            pending_figure = None

    def flush_table() -> None:
        nonlocal pending_table
        if pending_table is not None:
            out.append(table_plain(pending_table))
            pending_table = None

    for node in nodes:
        kind = node["type"]

        # An image sits alone in its own paragraph; the caption is the next paragraph,
        # which starts "**Figure N.**". Holding the figure back one node lets the two be
        # emitted as a single float instead of a graphic and a stray bold sentence. A
        # table is held back the same way, for a paragraph starting "**Table N.**".
        if kind == "paragraph":
            children = node["children"]
            images = [c for c in children if c["type"] == "image"]
            if images and all(c["type"] in {"image", "softbreak"} for c in children):
                flush_figure()
                flush_table()
                pending_figure = images[0]["attrs"]["url"]
                continue

            text = inline(children)
            lead = children[0]
            lead_text = inline(lead["children"]) if lead["type"] == "strong" else ""

            if pending_figure and lead["type"] == "strong" and "Figure" in lead_text:
                caption = FIG_PREFIX.sub("", text.replace(rf"\textbf{{{lead_text}}}", "")).lstrip()
                out.append(figure(pending_figure, caption))
                pending_figure = None
                continue

            if pending_table is not None and lead["type"] == "strong" and "Table" in lead_text:
                caption = TAB_PREFIX.sub("", text.replace(rf"\textbf{{{lead_text}}}", "")).lstrip()
                table_seq += 1
                out.append(table_float(pending_table, caption, str(table_seq)))
                pending_table = None
                continue

            flush_figure()
            flush_table()
            out.append(text + "\n")

        elif kind == "heading":
            flush_figure()
            flush_table()
            level = node["attrs"]["level"]
            title = HEADING_NUMBER.sub("", inline(node["children"]))
            cmd = {2: "section", 3: "subsection", 4: "subsubsection"}.get(level, "paragraph")
            out.append(f"\\{cmd}{{{title}}}\n")

        elif kind == "table":
            flush_figure()
            flush_table()
            pending_table = node

        elif kind == "block_quote":
            flush_figure()
            flush_table()
            out.append("\\begin{pullquote}\n" + blocks(node["children"]) + "\\end{pullquote}\n")

        elif kind == "list":
            flush_figure()
            flush_table()
            env = "enumerate" if node["attrs"]["ordered"] else "itemize"
            items = "".join(
                "\\item " + blocks(item["children"]).strip() + "\n" for item in node["children"]
            )
            out.append(f"\\begin{{{env}}}\n{items}\\end{{{env}}}\n")

        elif kind in {"block_text", "paragraph"}:
            out.append(inline(node["children"]) + "\n")

        elif kind == "block_code":
            # The architecture block in 4.1 is wider than the text block at body size, so
            # code is set smaller, and given a rule in the margin so it reads as an inset
            # rather than as prose that lost its font.
            flush_figure()
            flush_table()
            out.append("\\begin{codeblock}\n" + node["raw"].rstrip() + "\n\\end{codeblock}\n")

        elif kind == "thematic_break":
            flush_figure()
            flush_table()
            out.append("\\bigskip\\noindent{\\color{hair}\\hrule height 0.4pt}\\medskip\n")

        elif kind == "blank_line":
            out.append("\n")

    flush_figure()
    flush_table()
    return "".join(out)


PREAMBLE = r"""\documentclass[11pt,a4paper,oneside]{report}
\usepackage{fontspec}
\usepackage{geometry}
% 13cm measure, about 72 characters at 11pt. The outer margin is deliberately generous:
% it is a named column that the wide figures are set into, not slack.
\geometry{
  a4paper,
  top=2.7cm, bottom=2.9cm, left=3.4cm, right=4.6cm,
  marginparwidth=3.2cm, marginparsep=0.5cm,
  headsep=0.7cm, footskip=1.2cm
}
\usepackage{booktabs}
\usepackage{tabularx}
\newcolumntype{L}{>{\raggedright\arraybackslash\hspace{0pt}}X}
\newcolumntype{R}{>{\raggedleft\arraybackslash\hspace{0pt}}X}
\usepackage{graphicx}
\usepackage{microtype}
\usepackage[table]{xcolor}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{parskip}
\usepackage{caption}
\usepackage{float}
\usepackage{chngcntr}
\usepackage{fancyvrb}
\usepackage{enumitem}
% Figures and tables are numbered straight through rather than per chapter, so the numbers
% match the captions in the markdown sources and any reference to them in the body text.
\counterwithout{figure}{chapter}
\counterwithout{table}{chapter}

\definecolor{srhorange}{HTML}{E64415}
\definecolor{ink}{HTML}{1A1A1A}
\definecolor{slate}{HTML}{555555}
\definecolor{hair}{HTML}{C9C6C0}

\linespread{1.06}
\setlength{\parskip}{0.55em}
\widowpenalty=10000
\clubpenalty=10000
\setlist{noitemsep, topsep=4pt, parsep=2pt, leftmargin=1.5em}

% Interactive navigation, which is the point of this build: TOC entries, figure and
% section references, and the reader's sidebar all become links. Internal links are ink
% rather than orange: they are navigation, and colouring every one of them turns the
% contents page into a field of accent colour. External DOIs stay orange, because there
% the colour is telling the reader the link leaves the document.
\usepackage[
  colorlinks=true, linkcolor=ink, citecolor=ink, urlcolor=srhorange,
  bookmarks=true, bookmarksopen=true, bookmarksnumbered=true,
  pdftitle={<<title>>}, pdfauthor={<<author>>},
  pdfsubject={<<module>>, <<university>>}
]{hyperref}

% Contents entries without dotted leaders. \@dotsep is a length in mu; setting it absurdly
% large suppresses the dots without pulling in another package.
\makeatletter
\renewcommand{\@dotsep}{10000}
\makeatother

\captionsetup{
  font=small, labelfont=bf, labelsep=period,
  singlelinecheck=false, justification=raggedright, skip=8pt
}
\captionsetup[table]{position=top, skip=6pt}

\titleformat{\chapter}[display]
  {\normalfont\huge\bfseries\color{ink}}
  {\color{srhorange}\normalsize\bfseries\MakeUppercase{\chaptertitlename\ \thechapter}}
  {10pt}{\Huge}[\vspace{8pt}{\color{hair}\titlerule[0.6pt]}]
\titlespacing*{\chapter}{0pt}{34pt}{30pt}
\titleformat{\section}{\normalfont\large\bfseries\color{ink}}{\thesection}{0.6em}{}
\titlespacing*{\section}{0pt}{20pt}{6pt}
\titleformat{\subsection}{\normalfont\normalsize\bfseries\color{ink}}{\thesubsection}{0.6em}{}
\titlespacing*{\subsection}{0pt}{14pt}{4pt}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\headrule}{{\color{hair}\hrule height \headrulewidth width\headwidth}}
\fancyhead[L]{\small\color{slate}\nouppercase{\leftmark}}
\fancyhead[R]{\small\color{slate}\thepage}
\renewcommand{\chaptermark}[1]{\markboth{\thechapter\quad #1}{}}
\fancypagestyle{plain}{%
  \fancyhf{}%
  \renewcommand{\headrulewidth}{0pt}%
  \fancyfoot[C]{\small\color{slate}\thepage}%
}

% Code and the architecture block: smaller, with a hairline in the margin so it reads as
% an inset. No commandchars, because the block contains literal backslashes and arrows.
\DefineVerbatimEnvironment{codeblock}{Verbatim}{%
  fontsize=\footnotesize, frame=leftline, framerule=1.2pt,
  rulecolor=\color{hair}, framesep=9pt, xleftmargin=12pt
}

% The pre-registered prediction in 5.1 is quoted rather than paraphrased, and it is the
% one block quote that carries an argument, so quotes get a hairline and an indent rather
% than the class default.
\newenvironment{pullquote}
  {\begin{list}{}{\setlength{\leftmargin}{1.4em}\setlength{\rightmargin}{0pt}}\item[]%
   \itshape\color{ink}}
  {\end{list}}

\setlength{\emergencystretch}{3em}
\sloppy
"""

TITLEPAGE = r"""
\begin{titlepage}
\thispagestyle{empty}
\centering
<<logo>>
\vspace{1.6cm}

{\color{srhorange}\rule{\linewidth}{1.2pt}}
\vspace{1.0cm}

{\LARGE\bfseries <<title>>\par}
\vspace{1.0cm}
{\color{srhorange}\rule{\linewidth}{1.2pt}}

\vspace{1.6cm}
{\large <<module>>\par}
\vspace{0.4cm}
{\color{slate}\large <<submitted>>\par}
\vspace{2.4cm}

\begin{tabular}{@{}rl@{}}
\textbf{Author}         & <<author>> \\[4pt]
\textbf{Matriculation}  & <<matriculation>> \\[4pt]
\textbf{Programme}      & <<programme>> \\[4pt]
\textbf{Supervisor}     & <<supervisor>> \\[4pt]
\textbf{University}     & <<university>> \\
\end{tabular}

\vfill
\end{titlepage}
"""


def build_tex() -> str:
    # "url" autolinks the bare DOIs in the reference list, so every citation in the PDF is
    # clickable. Verified beforehand that no URL in these chapters contains a character
    # that would break \href (%, #, _ and the like).
    md = mistune.create_markdown(renderer=None, plugins=["table", "strikethrough", "url"])
    fields = {
        "title": TITLE,
        "author": AUTHOR,
        "matriculation": MATRICULATION,
        "programme": PROGRAMME,
        "supervisor": SUPERVISOR,
        "university": UNIVERSITY,
        "module": MODULE,
        "submitted": SUBMITTED,
    }

    # Tectonic runs with docs/report as its working directory, so the graphic path has to
    # be relative to that, not to the repository root.
    logo = ASSETS / "srh_logo.png"
    fields["logo"] = (
        rf"\includegraphics[width=4.2cm]{{{os.path.relpath(logo, REPORT)}}}"
        if logo.exists()
        else ""
    )

    def fill(template: str) -> str:
        for key, value in fields.items():
            template = template.replace(f"<<{key}>>", value)
        return template

    parts = [fill(PREAMBLE), "\\begin{document}", fill(TITLEPAGE)]
    # Both front-matter lists get an explicit bookmark. report class does not add one, so
    # without this the sidebar starts at Chapter 1 and the reader cannot jump back to the
    # contents, which defeats the point of building a navigable PDF.
    parts.append(
        "\\pdfbookmark[0]{Contents}{toc}\n\\tableofcontents\n\\clearpage\n"
        "\\pdfbookmark[0]{List of Figures}{lof}\n\\listoffigures\n\\clearpage\n"
    )

    for filename, title in CHAPTERS:
        path = REPORT / filename
        parts.append(f"\n\\chapter{{{title}}}\n")
        if not path.exists():
            parts.append(
                "This chapter has not been written yet. See "
                "\\texttt{docs/report/README.md} for what it needs to cover.\n"
            )
            continue
        text = re.sub(r"^#\s+.*?\n", "", path.read_text(encoding="utf-8"), count=1)
        parts.append(blocks(md(text)))

    parts.append("\\end{document}\n")
    return "\n".join(parts)


def compile_pdf() -> bool:
    exe = "tectonic"
    proc = subprocess.run(
        [exe, "-X", "compile", "--keep-logs", TEX.name],
        cwd=REPORT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr[-4000:])
        return False
    # Warnings about dropped glyphs mean silently wrong chemistry, so they are surfaced
    # rather than buried in the log. Overfull boxes matter more now that the measure is
    # narrower: a wide table that used to fit may not.
    for line in proc.stderr.splitlines():
        if "could not represent character" in line or "Overfull" in line:
            sys.stderr.write(line + "\n")
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-pdf", action="store_true", help="write the .tex without compiling")
    args = ap.parse_args()

    TEX.write_text(build_tex(), encoding="utf-8")
    print(f"wrote {TEX.relative_to(REPO)}")
    if args.no_pdf:
        return
    if compile_pdf():
        print(f"wrote {PDF.relative_to(REPO)}")
    else:
        sys.exit("tectonic failed")


if __name__ == "__main__":
    main()
