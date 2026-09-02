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
HEADING_NUMBER = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+")


def esc(text: str) -> str:
    """Escape LaTeX specials and rewrite characters the default font cannot set."""
    for char, replacement in TEX_ESCAPES:
        text = text.replace(char, replacement)
    for char, digit in SUBSCRIPTS.items():
        text = text.replace(char, rf"\textsubscript{{{digit}}}")
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
            out.append(rf"\texttt{{{esc(node['raw'])}}}")
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
    """A float carrying the figure, preferring the vector version for print."""
    path = (REPORT / url).resolve()
    vector = path.with_suffix(".pdf")
    if vector.is_file():
        path = vector
    rel = path.relative_to(REPORT).as_posix()
    label = "fig:" + Path(url).stem
    return (
        "\\begin{figure}[H]\n\\centering\n"
        f"\\includegraphics[width=\\linewidth]{{{rel}}}\n"
        f"\\caption{{{caption}}}\n\\label{{{label}}}\n"
        "\\end{figure}\n"
    )


def table(node: dict[str, Any]) -> str:
    """Render a markdown table with booktabs rules.

    Column type is chosen from the content rather than fixed: a column holding long text
    becomes a wrapping X column, a short one stays flush. Without this the wide results
    tables run off the page edge.
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
    spec = "".join("X" if w > 18 else ("l" if i == 0 else "r") for i, w in enumerate(widths))
    if "X" not in spec:  # tabularx needs at least one X column to have something to stretch
        spec = "l" + spec[1:]
        env, arg = "tabular", f"{{@{{}}{spec}@{{}}}}"
    else:
        env, arg = "tabularx", f"{{\\linewidth}}{{@{{}}{spec}@{{}}}}"

    rows = "\n".join(" & ".join(r) + r" \\" for r in body)
    return (
        "\\begin{center}\n\\small\n"
        f"\\begin{{{env}}}{arg}\n\\toprule\n"
        + " & ".join(rf"\textbf{{{h}}}" for h in head)
        + " \\\\\n\\midrule\n"
        + rows
        + f"\n\\bottomrule\n\\end{{{env}}}\n\\end{{center}}\n"
    )


def blocks(nodes: list[dict[str, Any]]) -> str:
    """Render block-level nodes, pairing each image with the caption that follows it."""
    out: list[str] = []
    pending_figure: str | None = None

    for node in nodes:
        kind = node["type"]

        # An image sits alone in its own paragraph; the caption is the next paragraph,
        # which starts "**Figure N.**". Holding the figure back one node lets the two be
        # emitted as a single float instead of a graphic and a stray bold sentence.
        if kind == "paragraph":
            children = node["children"]
            images = [c for c in children if c["type"] == "image"]
            if images and all(c["type"] in {"image", "softbreak"} for c in children):
                if pending_figure:
                    out.append(figure(pending_figure, ""))
                pending_figure = images[0]["attrs"]["url"]
                continue

            text = inline(children)
            if pending_figure:
                stripped = children[0]
                is_caption = stripped["type"] == "strong" and "Figure" in inline(
                    stripped["children"]
                )
                if is_caption:
                    out.append(
                        figure(
                            pending_figure,
                            FIG_PREFIX.sub(
                                "", text.replace(rf"\textbf{{{inline(stripped['children'])}}}", "")
                            ).lstrip(),
                        )
                    )
                    pending_figure = None
                    continue
                out.append(figure(pending_figure, ""))
                pending_figure = None
            out.append(text + "\n")

        elif kind == "heading":
            if pending_figure:
                out.append(figure(pending_figure, ""))
                pending_figure = None
            level = node["attrs"]["level"]
            title = HEADING_NUMBER.sub("", inline(node["children"]))
            cmd = {2: "section", 3: "subsection", 4: "subsubsection"}.get(level, "paragraph")
            out.append(f"\\{cmd}{{{title}}}\n")

        elif kind == "table":
            out.append(table(node))

        elif kind == "block_quote":
            out.append("\\begin{quote}\n" + blocks(node["children"]) + "\\end{quote}\n")

        elif kind == "list":
            env = "enumerate" if node["attrs"]["ordered"] else "itemize"
            items = "".join(
                "\\item " + blocks(item["children"]).strip() + "\n" for item in node["children"]
            )
            out.append(f"\\begin{{{env}}}\n{items}\\end{{{env}}}\n")

        elif kind in {"block_text", "paragraph"}:
            out.append(inline(node["children"]) + "\n")

        elif kind == "block_code":
            # The architecture diagram is wider than the text block at body size, so
            # code blocks are set smaller rather than allowed to run into the margin.
            out.append(
                "{\\footnotesize\\begin{verbatim}\n" + node["raw"].rstrip() + "\n\\end{verbatim}}\n"
            )

        elif kind == "thematic_break":
            out.append("\\medskip\\hrule\\medskip\n")

        elif kind == "blank_line":
            out.append("\n")

    if pending_figure:
        out.append(figure(pending_figure, ""))
    return "".join(out)


PREAMBLE = r"""\documentclass[11pt,a4paper,oneside]{report}
\usepackage{fontspec}
\usepackage{geometry}
\geometry{a4paper,top=2.6cm,bottom=2.6cm,left=2.6cm,right=2.4cm}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{graphicx}
\usepackage{microtype}
\usepackage[table]{xcolor}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{parskip}
\usepackage{caption}
\usepackage{float}
\usepackage{chngcntr}
% Figures are numbered straight through rather than per chapter, so the numbers match
% the captions in the markdown sources and the one reference to "Figure 6" in the text.
\counterwithout{figure}{chapter}

\definecolor{srhorange}{HTML}{E64415}
\definecolor{ink}{HTML}{1A1A1A}

% Interactive navigation, which is the point of this build: TOC entries, figure and
% section references, and the reader's sidebar all become links.
\usepackage[
  colorlinks=true, linkcolor=srhorange, citecolor=srhorange, urlcolor=srhorange,
  bookmarks=true, bookmarksopen=true, bookmarksnumbered=true,
  pdftitle={<<title>>}, pdfauthor={<<author>>},
  pdfsubject={<<module>>, <<university>>}
]{hyperref}

\captionsetup{font=small,labelfont={bf,color=srhorange}}
\titleformat{\chapter}[display]
  {\normalfont\huge\bfseries\color{ink}}
  {\color{srhorange}\normalsize\bfseries\MakeUppercase{\chaptertitlename\ \thechapter}}
  {8pt}{\Huge}
\titlespacing*{\chapter}{0pt}{0pt}{24pt}
\titleformat{\section}{\normalfont\large\bfseries\color{ink}}{\color{srhorange}\thesection}{0.6em}{}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\small\thepage}

\setlength{\emergencystretch}{3em}
\sloppy
"""

TITLEPAGE = r"""
\begin{titlepage}
\centering
<<logo>>
\vspace{1.4cm}

{\color{srhorange}\rule{\linewidth}{1.2pt}}
\vspace{0.9cm}

{\LARGE\bfseries <<title>>\par}
\vspace{0.9cm}
{\color{srhorange}\rule{\linewidth}{1.2pt}}

\vspace{1.8cm}
{\large <<module>>\par}
\vspace{2.2cm}

\begin{tabular}{rl}
\textbf{Author}         & <<author>> \\[3pt]
\textbf{Matriculation}  & <<matriculation>> \\[3pt]
\textbf{Programme}      & <<programme>> \\[3pt]
\textbf{Supervisor}     & <<supervisor>> \\[3pt]
\textbf{University}     & <<university>> \\
\end{tabular}

\vfill
{\small Compiled from the chapter sources in \texttt{docs/report/}.\par}
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
    parts.append("\\tableofcontents\n\\clearpage\n")

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
    # rather than buried in the log.
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
