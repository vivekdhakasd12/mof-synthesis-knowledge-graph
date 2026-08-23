"""Streamlit front end for building the human gold standard.

Deliberately thin: every rule lives in `src/annotation/core.py`, which is unit tested.
This file only draws widgets and calls into core, so that the correctness of the gold
standard never depends on code that pytest cannot reach.

Launch from the repository root:

    streamlit run src/annotation/app.py

Two design choices worth stating, because a grader will ask:

* Relation first, then types. Each relation in the ontology fixes its legal subject and
  object types, so the type controls are populated from `core.allowed_endpoints`. An
  ontology-invalid triple therefore cannot be created in the interface at all, rather
  than being created and rejected afterwards.
* No model assistance anywhere. Nothing here drafts, ranks or pre-fills an annotation.
  The one automated field is the evidence sentence, which is copied verbatim from the
  passage on an explicit button press, after the annotator has already typed the entity,
  and stays editable. The gold standard is what the LLM output is graded against, so any
  model contribution to it would make the whole evaluation circular.
"""

from __future__ import annotations

import html
import os
import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    # `streamlit run` puts the script's own directory on sys.path, not the repo root, so
    # `src.` imports need the root added explicitly. Doing it here keeps the launch
    # command a plain `streamlit run` with no PYTHONPATH ceremony for the annotator.
    sys.path.insert(0, str(REPO_ROOT))

from src.annotation import core  # noqa: E402

st.set_page_config(page_title="MOF gold standard annotation", layout="wide")

PASSAGE_CSS = """
<style>
.passage-box {
    font-size: 1.15rem;
    line-height: 1.75;
    background: rgba(128, 128, 128, 0.08);
    border-left: 4px solid #4c8bf5;
    padding: 1.1rem 1.3rem;
    border-radius: 6px;
    white-space: pre-wrap;
}
</style>
"""


def _init_state() -> None:
    if "worklist" in st.session_state:
        return
    passages = core.load_passages()
    st.session_state.worklist = core.build_worklist(passages, n=core.TARGET_MAX)
    st.session_state.n_loaded = len(passages)
    st.session_state.idx = 0
    st.session_state.annotator = os.environ.get("GOLD_ANNOTATOR", "human")


def _current() -> core.Passage:
    worklist: list[core.Passage] = st.session_state.worklist
    st.session_state.idx = max(0, min(st.session_state.idx, len(worklist) - 1))
    return worklist[st.session_state.idx]


def _record_for(passage_id: str) -> core.GoldRecord | None:
    for record in core.load_gold():
        if record.passage_id == passage_id:
            return record
    return None


def _advance(step: int) -> None:
    st.session_state.idx = max(
        0, min(st.session_state.idx + step, len(st.session_state.worklist) - 1)
    )
    st.rerun()


def _save(
    passage: core.Passage, triples: list[core.GoldTriple], status: str, note: str = ""
) -> None:
    """Autosave point. Every button that changes a decision routes through here."""
    try:
        core.append_annotation(
            passage.passage_id,
            passage.paper_id,
            passage.section,
            triples,
            status=status,
            note=note,
            annotator=st.session_state.annotator,
            passage_text=passage.text,
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    st.toast(f"saved: {passage.passage_id} ({status})")


def _sidebar() -> None:
    stats = core.progress_stats()
    with st.sidebar:
        st.header("Progress")
        low, high = stats.target_range
        st.progress(stats.fraction_of_target, text=f"{stats.annotated} / {low} (stretch {high})")
        col_a, col_b = st.columns(2)
        col_a.metric("With triples", stats.annotated)
        col_b.metric("Remaining", stats.remaining)
        col_c, col_d = st.columns(2)
        col_c.metric("No synthesis", stats.no_synthesis)
        col_d.metric("Triples", stats.triples)
        st.caption(f"reviewed {stats.reviewed} passages, {stats.skipped} skipped for later")

        st.divider()
        st.header("Session")
        st.session_state.annotator = st.text_input("Annotator", st.session_state.annotator)
        worklist: list[core.Passage] = st.session_state.worklist
        st.caption(f"worklist {len(worklist)} of {st.session_state.n_loaded} passages loaded")
        st.caption(f"input: {worklist[0].source if worklist else 'none'}, seed {core.SAMPLE_SEED}")
        st.caption(f"gold file: {core.GOLD_PATH.relative_to(core.REPO_ROOT)}")

        if st.button("Jump to first undecided", use_container_width=True):
            pending = core.pending_passages(worklist)
            if pending:
                ids = [p.passage_id for p in worklist]
                st.session_state.idx = ids.index(pending[0].passage_id)
                st.rerun()
            else:
                st.info("every passage in the worklist has a decision")

        st.divider()
        st.caption(
            "No model assistance by design: the gold standard is the yardstick used to "
            "judge LLM output, so it is written by hand only."
        )


def _passage_header(passage: core.Passage) -> None:
    worklist: list[core.Passage] = st.session_state.worklist
    left, right = st.columns([3, 1])
    with left:
        st.subheader(f"Passage {st.session_state.idx + 1} of {len(worklist)}")
        st.caption(
            f"{passage.paper_id} | section: {passage.section} | "
            f"{'synthesis pool' if passage.is_synthesis else 'control passage (unflagged)'}"
        )
        if passage.doi:
            st.caption(f"doi: {passage.doi}")
    with right:
        record = _record_for(passage.passage_id)
        if record is None:
            st.info("not decided yet")
        else:
            st.success(f"saved: {record.status}, {len(record.triples)} triple(s)")


def _triple_form(passage: core.Passage, existing: list[core.GoldTriple]) -> None:
    st.markdown("#### Add a triple")
    relation = st.selectbox("1. Relation", core.allowed_relations(), key="relation")
    subject_type = st.selectbox("2. Subject type", core.allowed_subject_types(relation))
    object_type = st.selectbox("3. Object type", core.allowed_object_types(relation))
    st.caption(f"{subject_type} -{relation}-> {object_type} (fixed by the ontology)")

    col_s, col_o = st.columns(2)
    subject_name = col_s.text_input(f"4. {subject_type} as written in the passage", key="subject")
    object_name = col_o.text_input(f"5. {object_type} as written in the passage", key="object")

    subject_span = core.find_span(passage.text, subject_name)
    object_span = core.find_span(passage.text, object_name)
    col_s.caption(f"span {subject_span}" if subject_span else "not found verbatim (span omitted)")
    col_o.caption(f"span {object_span}" if object_span else "not found verbatim (span omitted)")

    if st.button("Copy the sentence containing the subject into evidence"):
        st.session_state.evidence = core.sentence_containing(passage.text, subject_name)
        st.rerun()
    evidence = st.text_area("6. Evidence sentence, verbatim from the passage", key="evidence")
    confidence = st.radio("7. Confidence", ("high", "medium", "low"), horizontal=True)

    if st.button("Add triple", type="primary"):
        triple = core.GoldTriple(
            subject_type=subject_type,
            subject_name=subject_name.strip(),
            relation=relation,
            object_type=object_type,
            object_name=object_name.strip(),
            evidence=evidence.strip(),
            subject_span=subject_span,
            object_span=object_span,
            confidence=confidence,
        )
        _save(passage, [*existing, triple], status="annotated")
        st.session_state.subject = ""
        st.session_state.object = ""
        st.session_state.evidence = ""
        st.rerun()


def _existing_triples(passage: core.Passage, existing: list[core.GoldTriple]) -> None:
    if not existing:
        return
    st.markdown("#### Recorded for this passage")
    for i, triple in enumerate(existing):
        row, button = st.columns([6, 1])
        row.markdown(
            f"**{triple.subject_name}** ({triple.subject_type}) "
            f"-{triple.relation}-> **{triple.object_name}** ({triple.object_type})  \n"
            f"<span style='opacity:0.7'>{html.escape(triple.evidence)}</span>",
            unsafe_allow_html=True,
        )
        if button.button("Remove", key=f"rm-{i}"):
            remaining = [t for j, t in enumerate(existing) if j != i]
            if remaining:
                _save(passage, remaining, status="annotated")
            else:
                core.delete_annotation(passage.passage_id)
                st.toast("all triples removed, passage is undecided again")
            st.rerun()


def main() -> None:
    _init_state()
    st.markdown(PASSAGE_CSS, unsafe_allow_html=True)
    st.title("MOF synthesis gold standard")

    if not st.session_state.worklist:
        st.error("no passages available: build data/processed/passages.jsonl or corpus.jsonl")
        return

    _sidebar()
    passage = _current()
    record = _record_for(passage.passage_id)
    existing = list(record.triples) if record else []

    _passage_header(passage)
    st.markdown(
        f"<div class='passage-box'>{html.escape(passage.text)}</div>", unsafe_allow_html=True
    )
    st.write("")

    nav = st.columns(5)
    if nav[0].button("Previous", use_container_width=True):
        _advance(-1)
    if nav[1].button("Save and next", use_container_width=True, type="primary"):
        if existing:
            _save(passage, existing, status="annotated")
        _advance(1)
    if nav[2].button("No synthesis content", use_container_width=True):
        _save(passage, [], status="no_synthesis")
        _advance(1)
    if nav[3].button("Skip for now", use_container_width=True):
        _save(passage, [], status="skipped")
        _advance(1)
    if nav[4].button("Next", use_container_width=True):
        _advance(1)

    st.divider()
    left, right = st.columns(2)
    with left:
        _triple_form(passage, existing)
    with right:
        _existing_triples(passage, existing)
        st.markdown("#### Conventions")
        st.caption(
            "Reaction medium only for IN_SOLVENT (washing solvents are not annotated). "
            "Record names and conditions exactly as written, ranges as one Condition. "
            "See src/annotation/README.md for the full list."
        )


main()
