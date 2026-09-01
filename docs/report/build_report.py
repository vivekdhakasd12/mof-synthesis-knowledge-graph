"""Assemble the report chapters into one HTML document and render it to PDF.

The report is authored as markdown chapters so they can be revised independently, then
rendered through the same headless-Chrome path already used for the exposé, reusing its
visual language (SRH orange, Lato, the logo) so the two documents look like one project.

Run:  python docs/report/build_report.py
      python docs/report/build_report.py --no-pdf     (HTML only, faster while writing)
"""

from __future__ import annotations

import argparse
import base64
import re
import subprocess
import sys
from pathlib import Path

import mistune

REPORT = Path(__file__).resolve().parent
REPO = REPORT.parents[1]
ASSETS = REPO / "docs" / "assets"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Chapter order. A file that does not exist yet is skipped with a visible placeholder, so
# the document can be read end to end while chapters are still being written.
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

TITLE = "Building and Validating a Metal-Organic Framework Synthesis Knowledge Graph with Large Language Models"
AUTHOR = "Devendra Singh Dhakad"
MATRICULATION = "100004684"
PROGRAMME = "M.Sc. Data Science and Artificial Intelligence"
SUPERVISOR = "Prof. Dr. Mehrdad Jalali"
UNIVERSITY = "SRH University of Applied Sciences Heidelberg"


def data_uri(path: Path) -> str:
    """Inline an asset so the HTML is a single self-contained file."""
    suffix = path.suffix.lstrip(".").lower()
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "svg": "svg+xml"}.get(suffix, suffix)
    return f"data:image/{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def inline_images(html: str) -> str:
    """Replace figure src paths with data URIs.

    Chrome renders a file:// page with its own directory as the base, so relative image
    paths would work, but inlining means the HTML can be emailed or opened anywhere and
    still shows its figures. For a document a supervisor may forward, that matters.
    """

    def repl(match: re.Match[str]) -> str:
        src = match.group(1)
        candidate = (REPORT / src).resolve()
        if candidate.is_file():
            return f'src="{data_uri(candidate)}"'
        return match.group(0)

    return re.sub(r'src="([^"]+)"', repl, html)


def build_html() -> str:
    md = mistune.create_markdown(plugins=["table", "strikethrough", "footnotes"])
    body_parts: list[str] = []
    toc_parts: list[str] = []

    for number, (filename, title) in enumerate(CHAPTERS, start=1):
        path = REPORT / filename
        toc_parts.append(f'<li><span class="toc-num">{number}</span>{title}</li>')
        if not path.exists():
            body_parts.append(
                f'<section class="chapter missing">'
                f"<h1>{number}. {title}</h1>"
                f'<p class="placeholder">This chapter has not been written yet. '
                f"See <code>docs/report/README.md</code> for what it needs to cover.</p>"
                f"</section>"
            )
            continue
        text = path.read_text(encoding="utf-8")
        # The markdown files carry their own numbered H1; the builder owns numbering, so
        # the file's leading heading is dropped to avoid "1. 1. Introduction".
        text = re.sub(r"^#\s+[\d.]*\s*.*?\n", "", text, count=1)
        html = md(text)
        body_parts.append(
            f'<section class="chapter"><h1>{number}. {title}</h1>{html}</section>'
        )

    logo = ASSETS / "srh_logo.jpg"
    logo_tag = f'<img class="logo" src="{data_uri(logo)}" alt="SRH logo">' if logo.exists() else ""

    return TEMPLATE.format(
        title=TITLE,
        logo=logo_tag,
        author=AUTHOR,
        matriculation=MATRICULATION,
        programme=PROGRAMME,
        supervisor=SUPERVISOR,
        university=UNIVERSITY,
        toc="\n".join(toc_parts),
        body=inline_images("\n".join(body_parts)),
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>{title}</title>
<style>
:root {{ --srh-orange:#E64415; --ink:#1a1a1a; --muted:#555; --rule:#e3e3e3; --link:#0b5bd3; }}
@font-face {{ font-family:'Lato'; src:url('assets/fonts/Lato-Regular.ttf'); font-weight:400; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
@page {{ size:A4; margin:2.4cm 2.2cm; }}
html {{ background:#f0f0f0; }}
body {{ font-family:'Lato',Helvetica,Arial,sans-serif; font-size:10.5pt; line-height:1.55; color:var(--ink); }}
.sheet {{ background:#fff; width:21cm; min-height:29.7cm; margin:1.2rem auto; padding:2.4cm 2.2cm;
          box-shadow:0 2px 14px rgba(0,0,0,.12); }}
@media print {{
  html {{ background:#fff; }}
  .sheet {{ width:auto; min-height:0; margin:0; padding:0; box-shadow:none; }}
  .chapter {{ page-break-before:always; }}
  .title-page, .toc-page {{ page-break-after:always; }}
  figure, table, .no-break {{ break-inside:avoid; }}
  h1,h2,h3 {{ break-after:avoid; }}
  a {{ color:var(--link) !important; }}
}}
/* Title page */
.title-page {{ text-align:center; display:flex; flex-direction:column; align-items:center; }}
.title-page .logo {{ width:3.2cm; margin-top:1.4cm; }}
.title-page .kind {{ margin-top:3cm; font-size:12pt; letter-spacing:.22em; text-transform:uppercase; color:var(--muted); font-weight:700; }}
.title-page h1 {{ margin-top:1cm; font-size:20pt; font-weight:900; line-height:1.35; max-width:15cm; border:none; padding:0; }}
.title-rule {{ width:2.6cm; height:2.5pt; background:var(--srh-orange); border:none; margin:1.1cm auto; }}
.title-page .meta {{ margin-top:1.4cm; font-size:11pt; line-height:2; }}
.title-page .meta .name {{ font-weight:700; font-size:12.5pt; }}
.title-page .sep {{ color:var(--srh-orange); padding:0 .45em; }}
/* Table of contents */
.toc-page h2 {{ font-size:14pt; font-weight:900; text-transform:uppercase; letter-spacing:.045em;
                color:var(--srh-orange); margin-bottom:.7cm; }}
.toc-page ol {{ list-style:none; }}
.toc-page li {{ padding:.28em 0; border-bottom:1px dotted var(--rule); font-size:11pt; }}
.toc-num {{ display:inline-block; width:2.2em; color:var(--srh-orange); font-weight:700; }}
/* Chapters */
.chapter h1 {{ font-size:16pt; font-weight:900; color:var(--ink); padding-bottom:.25cm;
               border-bottom:2px solid var(--srh-orange); margin-bottom:.6cm; }}
.chapter h2 {{ font-size:12.5pt; font-weight:900; margin:.75cm 0 .25cm; }}
.chapter h3 {{ font-size:11pt; font-weight:700; margin:.55cm 0 .2cm; }}
p {{ text-align:justify; hyphens:auto; margin-bottom:.32cm; }}
ul,ol {{ margin:0 0 .35cm 1.4em; }}
li {{ margin-bottom:.14cm; text-align:justify; }}
strong {{ font-weight:700; }}
code {{ font-family:'SF Mono',Menlo,monospace; font-size:9pt; background:#f4f4f4; padding:.08em .3em; border-radius:2px; }}
table {{ width:100%; border-collapse:collapse; font-size:9.5pt; margin:.3cm 0 .5cm; }}
th {{ text-align:left; font-weight:900; font-size:9pt; letter-spacing:.05em; text-transform:uppercase;
      padding:0 .5em .16cm 0; border-bottom:1.2pt solid #bbb; }}
td {{ vertical-align:top; padding:.16cm .5em .16cm 0; border-bottom:1px solid var(--rule); }}
blockquote {{ margin:.3cm 0 .4cm; padding:.25cm .6cm; border-left:3px solid var(--srh-orange);
              background:#fbfbfb; font-style:italic; }}
img {{ max-width:100%; display:block; margin:.4cm auto; }}
.placeholder {{ color:var(--muted); font-style:italic; }}
.missing h1 {{ border-bottom-color:var(--rule); color:var(--muted); }}
a {{ color:var(--link); text-decoration:none; }}
</style></head><body>

<div class="sheet title-page">
  {logo}
  <div class="kind">Case Study 2</div>
  <h1>{title}</h1>
  <hr class="title-rule">
  <div class="meta">
    <div class="name">{author}<span class="sep">&bull;</span>Matriculation No. {matriculation}</div>
    <div>{programme}</div>
    <div>Supervisor: {supervisor}</div>
    <div>{university}</div>
  </div>
</div>

<div class="sheet toc-page">
  <h2>Contents</h2>
  <ol>{toc}</ol>
</div>

<div class="sheet">
{body}
</div>
</body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pdf", action="store_true", help="write HTML only")
    args = ap.parse_args()

    html_path = REPORT / "report.html"
    html_path.write_text(build_html(), encoding="utf-8")
    written = [str(html_path.relative_to(REPO))]

    if not args.no_pdf:
        if not Path(CHROME).exists():
            print(f"Chrome not found at {CHROME}; wrote HTML only", file=sys.stderr)
        else:
            pdf_path = REPORT / "report.pdf"
            subprocess.run(
                [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                 "--virtual-time-budget=8000", f"--print-to-pdf={pdf_path}",
                 html_path.as_uri()],
                check=True, capture_output=True,
            )
            written.append(str(pdf_path.relative_to(REPO)))

    print("wrote " + " and ".join(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
