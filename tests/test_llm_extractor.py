"""Offline tests for the LLM extraction apparatus.

Every test here runs with no network and no API key: the model is a FakeClient that
returns canned strings. That is a deliberate constraint of the project, not a convenience.
The apparatus had to be written and validated before any key was available, and it must
keep being testable afterwards, because a test suite that needs a paid API is a test suite
that stops being run.

An autouse fixture severs socket.socket for the duration of every test, so "these tests do
not call the network" is enforced by the suite rather than asserted in a comment.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

import pytest

from src.extraction.cache import CacheEntry, LLMCache, make_key
from src.extraction.extractor_base import ExtractionResult
from src.extraction.llm_extractor import (
    PROMPT_DIR,
    STRATEGIES,
    AnthropicClient,
    GroqClient,
    LLMExtractor,
    LLMResponse,
    MissingAPIKeyError,
    OpenAIClient,
    load_template,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PASSAGE = (
    "HKUST-1 was prepared solvothermally from copper nitrate and trimesic acid "
    "in DMF at 120 °C for 24 h."
)

CLEAN_JSON = json.dumps(
    [
        {
            "subject": {"type": "MOF", "name": "HKUST-1", "span": [0, 7]},
            "relation": "USES_PRECURSOR",
            "object": {"type": "MetalPrecursor", "name": "copper nitrate", "span": [39, 53]},
            "evidence": PASSAGE,
            "confidence": "high",
        },
        {
            "subject": {"type": "MOF", "name": "HKUST-1", "span": [0, 7]},
            "relation": "USES_LINKER",
            "object": {"type": "OrganicLinker", "name": "trimesic acid", "span": [58, 71]},
            "evidence": PASSAGE,
            "confidence": "medium",
        },
    ]
)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make any socket creation an immediate, loud failure."""

    def _blocked(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("network access attempted in an offline test")

    monkeypatch.setattr(socket, "socket", _blocked)


class FakeClient:
    """Deterministic stand-in for a provider. Counts calls so cache hits are provable."""

    provider = "fake"

    def __init__(self, responses: str | list[str], tokens: tuple[int, int] = (1200, 300)) -> None:
        self._responses = [responses] if isinstance(responses, str) else list(responses)
        self.tokens = tokens
        self.calls = 0
        self.prompts: list[str] = []

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        self.prompts.append(prompt)
        index = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return LLMResponse(
            text=self._responses[index],
            prompt_tokens=self.tokens[0],
            completion_tokens=self.tokens[1],
        )


class ExplodingClient:
    provider = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        self.calls += 1
        raise TimeoutError("upstream took too long")


def make_extractor(
    tmp_path: Path,
    response: str | list[str] = CLEAN_JSON,
    *,
    strategy: str = "schema_guided",
    model: str = "gpt-4o",
    client: Any = None,
    cache: LLMCache | None = None,
) -> tuple[LLMExtractor, Any]:
    fake = client if client is not None else FakeClient(response)
    extractor = LLMExtractor(
        fake,
        strategy,
        model,
        PROMPT_DIR,
        cache=cache if cache is not None else LLMCache(tmp_path / "cache"),
    )
    return extractor, fake


# ---------------------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("strategy", sorted(STRATEGIES))
def test_every_strategy_loads_its_template(strategy: str) -> None:
    template = load_template(STRATEGIES[strategy], str(PROMPT_DIR))
    assert template.path.is_file()
    assert template.version, "template must be versioned, it is part of the cache key"
    rendered = template.render(PASSAGE)
    assert PASSAGE in rendered
    assert "{passage}" not in rendered


@pytest.mark.parametrize("strategy", sorted(STRATEGIES))
def test_template_declares_the_whole_ontology(strategy: str) -> None:
    """A prompt that omits a type cannot be blamed for never predicting it."""
    text = load_template(STRATEGIES[strategy], str(PROMPT_DIR)).text
    for entity_type in (
        "MOF",
        "MetalPrecursor",
        "OrganicLinker",
        "Solvent",
        "SynthesisMethod",
        "Condition",
        "Property",
        "Application",
    ):
        assert f"- {entity_type}:" in text
    for relation in (
        "USES_PRECURSOR",
        "USES_LINKER",
        "SYNTHESIZED_BY",
        "IN_SOLVENT",
        "AT_CONDITION",
        "HAS_PROPERTY",
        "MEASURED_AT",
        "USED_IN",
    ):
        assert f"- {relation}:" in text
    # Provenance is written by the pipeline, so it is never offered to the model.
    assert "- MENTIONED_IN:" not in text
    assert "- Paper:" not in text


@pytest.mark.parametrize("strategy", sorted(STRATEGIES))
def test_template_forbids_invention(strategy: str) -> None:
    text = load_template(STRATEGIES[strategy], str(PROMPT_DIR)).text.lower()
    assert "do not invent" in text or "do not infer" in text
    assert "json" in text


def test_chain_of_thought_asks_for_reasoning_before_the_json() -> None:
    text = load_template(STRATEGIES["cot"], str(PROMPT_DIR)).text
    assert "REASONING" in text
    assert "FINAL JSON" in text
    assert text.index("REASONING") < text.index("FINAL JSON")


def test_few_shot_carries_worked_examples() -> None:
    text = load_template(STRATEGIES["few_shot"], str(PROMPT_DIR)).text
    assert text.count("Example ") >= 3
    assert "HKUST-1" in text and "ZIF-8" in text


def test_no_em_dash_anywhere_in_repo_sources() -> None:
    """Project-wide writing rule: the em dash is banned in everything this repo produces.

    The banned character is written here as a unicode escape rather than literally. Spelling
    it out would place the character into this very file, and because the sweep also scans
    its own source, a literal would make the guard fail on itself. That is precisely what
    happened the first time this test ran, so the escape is load bearing, not cosmetic.

    The sweep covers every prompt template plus every Python source under src/ and tests/,
    so the rule is enforced repository wide instead of for a hand-listed few files.
    """
    em_dash = "\u2014"  # written as an escape so this file stays clean
    targets = (
        sorted(PROMPT_DIR.glob("*.txt"))
        + sorted((REPO_ROOT / "src").rglob("*.py"))
        + sorted((REPO_ROOT / "tests").rglob("*.py"))
    )
    offenders = [
        str(p.relative_to(REPO_ROOT)) for p in targets if em_dash in p.read_text(encoding="utf-8")
    ]
    assert not offenders, f"em dash found in: {offenders}"


# ---------------------------------------------------------------------------------------
# Parsing: the happy paths
# ---------------------------------------------------------------------------------------


def test_clean_json_becomes_triples_with_provenance(tmp_path: Path) -> None:
    extractor, fake = make_extractor(tmp_path)
    result = extractor.extract(PASSAGE, paper_id="PMC123", section="Methods")

    assert isinstance(result, ExtractionResult)
    assert result.errors == []
    assert len(result.triples) == 2
    first = result.triples[0]
    assert first.subject.type == "MOF"
    assert first.subject.name == "HKUST-1"
    assert first.relation == "USES_PRECURSOR"
    assert first.object.type == "MetalPrecursor"
    assert first.object.span == (39, 53)
    assert first.evidence == PASSAGE
    assert first.confidence == "high"
    # Provenance comes from the caller, never from the model.
    assert first.source_paper_id == "PMC123"
    assert first.source_section == "Methods"
    assert first.extractor == extractor.name == "llm:gpt-4o:schema_guided"
    assert fake.calls == 1
    assert PASSAGE in fake.prompts[0]


def test_provenance_from_arguments_overrides_anything_the_model_claims(tmp_path: Path) -> None:
    lying = json.dumps(
        [
            {
                "subject": {"type": "MOF", "name": "HKUST-1"},
                "relation": "USES_LINKER",
                "object": {"type": "OrganicLinker", "name": "trimesic acid"},
                "evidence": PASSAGE,
                "source_paper_id": "PMC999-made-up",
                "source_section": "Discussion",
            }
        ]
    )
    extractor, _ = make_extractor(tmp_path, lying)
    result = extractor.extract(PASSAGE, paper_id="PMC123", section="Methods")
    assert len(result.triples) == 1
    assert result.triples[0].source_paper_id == "PMC123"
    assert result.triples[0].source_section == "Methods"


def test_fenced_json_parses(tmp_path: Path) -> None:
    fenced = "Here are the triples I found:\n\n```json\n" + CLEAN_JSON + "\n```\nHope that helps."
    extractor, _ = make_extractor(tmp_path, fenced)
    result = extractor.extract(PASSAGE, paper_id="PMC123", section="Methods")
    assert len(result.triples) == 2
    assert result.errors == []


def test_chain_of_thought_response_parses_after_the_marker(tmp_path: Path) -> None:
    cot = (
        "REASONING\n"
        "1. MOFs named: HKUST-1 [the only one].\n"
        "2. Reagents: copper nitrate, trimesic acid.\n"
        "6. Discarding: nothing.\n\n"
        "FINAL JSON\n" + CLEAN_JSON + "\n"
    )
    extractor, _ = make_extractor(tmp_path, cot, strategy="cot")
    result = extractor.extract(PASSAGE, paper_id="PMC123", section="Methods")
    assert len(result.triples) == 2
    assert result.errors == []
    assert extractor.name == "llm:gpt-4o:cot"


def test_single_object_is_wrapped_in_a_list(tmp_path: Path) -> None:
    single = json.dumps(json.loads(CLEAN_JSON)[0])
    extractor, _ = make_extractor(tmp_path, single)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert len(result.triples) == 1
    assert any("wrapped it in a list" in e for e in result.errors)


def test_object_with_a_triples_key_is_unwrapped(tmp_path: Path) -> None:
    wrapped = json.dumps({"triples": json.loads(CLEAN_JSON)})
    extractor, _ = make_extractor(tmp_path, wrapped)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert len(result.triples) == 2


def test_trailing_commas_are_recovered(tmp_path: Path) -> None:
    broken = CLEAN_JSON.replace("]", ",]", 1) if CLEAN_JSON.endswith("]") else CLEAN_JSON
    broken = CLEAN_JSON[:-1] + ",]"
    extractor, _ = make_extractor(tmp_path, broken)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert len(result.triples) == 2


# ---------------------------------------------------------------------------------------
# Parsing: the failure paths. Nothing here may raise.
# ---------------------------------------------------------------------------------------


def test_malformed_json_records_an_error_and_does_not_raise(tmp_path: Path) -> None:
    extractor, _ = make_extractor(tmp_path, "I am afraid I cannot help with that request.")
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert result.triples == []
    assert result.errors
    assert any("no parseable JSON" in e for e in result.errors)


def test_invalid_relation_type_is_dropped_with_an_error(tmp_path: Path) -> None:
    payload = json.dumps(
        [
            {
                "subject": {"type": "MOF", "name": "HKUST-1"},
                "relation": "MADE_OF",
                "object": {"type": "OrganicLinker", "name": "trimesic acid"},
                "evidence": PASSAGE,
            },
            json.loads(CLEAN_JSON)[0],
        ]
    )
    extractor, _ = make_extractor(tmp_path, payload)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert len(result.triples) == 1
    assert any("MADE_OF" in e and "not in the ontology" in e for e in result.errors)


def test_ontology_endpoint_violation_is_dropped_with_an_error(tmp_path: Path) -> None:
    payload = json.dumps(
        [
            {
                # USES_LINKER is MOF -> OrganicLinker, so a Solvent object is illegal.
                "subject": {"type": "MOF", "name": "HKUST-1"},
                "relation": "USES_LINKER",
                "object": {"type": "Solvent", "name": "DMF"},
                "evidence": PASSAGE,
            }
        ]
    )
    extractor, _ = make_extractor(tmp_path, payload)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert result.triples == []
    assert any("USES_LINKER requires MOF -> OrganicLinker" in e for e in result.errors)


def test_mentioned_in_is_never_accepted_from_the_model(tmp_path: Path) -> None:
    payload = json.dumps(
        [
            {
                "subject": {"type": "MOF", "name": "HKUST-1"},
                "relation": "MENTIONED_IN",
                "object": {"type": "Paper", "name": "PMC123"},
                "evidence": PASSAGE,
            }
        ]
    )
    extractor, _ = make_extractor(tmp_path, payload)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert result.triples == []
    assert any("written by the pipeline" in e for e in result.errors)


def test_unknown_entity_type_is_dropped(tmp_path: Path) -> None:
    payload = json.dumps(
        [
            {
                "subject": {"type": "Framework", "name": "HKUST-1"},
                "relation": "USES_LINKER",
                "object": {"type": "OrganicLinker", "name": "trimesic acid"},
                "evidence": PASSAGE,
            }
        ]
    )
    extractor, _ = make_extractor(tmp_path, payload)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert result.triples == []
    assert any("'Framework' is not in the ontology" in e for e in result.errors)


def test_triple_without_evidence_is_dropped(tmp_path: Path) -> None:
    payload = json.dumps(
        [
            {
                "subject": {"type": "MOF", "name": "HKUST-1"},
                "relation": "USES_LINKER",
                "object": {"type": "OrganicLinker", "name": "trimesic acid"},
                "evidence": "   ",
            }
        ]
    )
    extractor, _ = make_extractor(tmp_path, payload)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert result.triples == []
    assert any("no evidence sentence" in e for e in result.errors)


def test_unusable_confidence_defaults_to_medium(tmp_path: Path) -> None:
    payload = json.dumps(
        [
            {
                "subject": {"type": "MOF", "name": "HKUST-1"},
                "relation": "USES_LINKER",
                "object": {"type": "OrganicLinker", "name": "trimesic acid"},
                "evidence": PASSAGE,
                "confidence": 0.93,
            }
        ]
    )
    extractor, _ = make_extractor(tmp_path, payload)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert len(result.triples) == 1
    assert result.triples[0].confidence == "medium"
    assert any("defaulted to 'medium'" in e for e in result.errors)


@pytest.mark.parametrize(
    "response",
    [
        "",
        "   ",
        "null",
        "42",
        '"just a string"',
        "[",
        "[{}]",
        '[{"relation": "USES_LINKER"}]',
        '[{"subject": "HKUST-1", "relation": "USES_LINKER", "object": "BDC", "evidence": "x"}]',
        '{"unexpected": {"deeply": ["nested", 1, null]}}',
        "```json\nnot json at all\n```",
        "[1, 2, 3]",
        json.dumps([{"subject": {"type": "MOF", "name": ""}, "relation": "USES_LINKER"}]),
    ],
)
def test_extract_never_raises_whatever_the_model_returns(tmp_path: Path, response: str) -> None:
    extractor, _ = make_extractor(tmp_path, response)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert isinstance(result, ExtractionResult)
    assert isinstance(result.errors, list)
    for triple in result.triples:
        assert triple.evidence
        assert triple.source_paper_id == "PMC1"


def test_client_failure_becomes_an_error_not_an_exception(tmp_path: Path) -> None:
    extractor, fake = make_extractor(tmp_path, client=ExplodingClient())
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert result.triples == []
    assert any("TimeoutError" in e for e in result.errors)
    assert fake.calls == 1


def test_unknown_strategy_is_rejected_at_construction(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown strategy"):
        LLMExtractor(FakeClient(CLEAN_JSON), "telepathy", "gpt-4o", PROMPT_DIR)


# ---------------------------------------------------------------------------------------
# Cost and latency
# ---------------------------------------------------------------------------------------


def test_cost_and_latency_are_populated_from_real_token_counts(tmp_path: Path) -> None:
    extractor, _ = make_extractor(tmp_path)
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    # gpt-4o at 2.50 / 10.00 USD per million tokens, 1200 prompt + 300 completion tokens.
    assert result.cost_usd == pytest.approx(1200 / 1e6 * 2.50 + 300 / 1e6 * 10.00)
    assert result.latency_ms > 0.0


def test_model_without_a_price_entry_costs_zero_and_says_so(tmp_path: Path) -> None:
    extractor, _ = make_extractor(tmp_path, model="some-unpriced-model-v9")
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert result.cost_usd == 0.0
    assert any("no verified price" in e for e in result.errors)
    assert len(result.triples) == 2  # the extraction itself still succeeds


def test_dated_model_ids_reuse_the_family_price(tmp_path: Path) -> None:
    extractor, _ = make_extractor(tmp_path, model="claude-3-5-sonnet-20241022")
    result = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert result.cost_usd == pytest.approx(1200 / 1e6 * 3.00 + 300 / 1e6 * 15.00)
    assert not any("no verified price" in e for e in result.errors)


# ---------------------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------------------


def test_second_identical_call_is_served_from_cache(tmp_path: Path) -> None:
    cache = LLMCache(tmp_path / "cache")
    extractor, fake = make_extractor(tmp_path, cache=cache)

    first = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    second = extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")

    assert fake.calls == 1, "the second call must not reach the client"
    assert [t.to_dict() for t in second.triples] == [t.to_dict() for t in first.triples]
    assert second.cost_usd == 0.0, "a cache hit costs nothing; the avoided spend is in stats()"

    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["writes"] == 1
    assert stats["entries_on_disk"] == 1
    assert stats["spend_avoided_usd"] == pytest.approx(first.cost_usd)
    assert stats["hit_rate"] == pytest.approx(0.5)


def test_cache_survives_a_new_process(tmp_path: Path) -> None:
    """A fresh cache object over the same directory must still serve the stored response."""
    cache_dir = tmp_path / "cache"
    first_extractor, first_fake = make_extractor(tmp_path, cache=LLMCache(cache_dir))
    first_extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert first_fake.calls == 1

    second_extractor, second_fake = make_extractor(tmp_path, cache=LLMCache(cache_dir))
    result = second_extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert second_fake.calls == 0
    assert len(result.triples) == 2


def test_provenance_is_not_part_of_the_cache_key(tmp_path: Path) -> None:
    """The model never sees paper_id, so two papers quoting the same passage share a call."""
    cache = LLMCache(tmp_path / "cache")
    extractor, fake = make_extractor(tmp_path, cache=cache)
    extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    second = extractor.extract(PASSAGE, paper_id="PMC2", section="Results")
    assert fake.calls == 1
    assert second.triples[0].source_paper_id == "PMC2"
    assert second.triples[0].source_section == "Results"


@pytest.mark.parametrize(
    "changed",
    [
        {"model": "gpt-4o-mini"},
        {"provider": "groq"},
        {"strategy": "cot"},
        {"template_name": "extraction_cot"},
        {"template_version": "2.0.0"},
        {"passage": "a different passage"},
        {"temperature": 0.7},
        {"max_tokens": 512},
    ],
)
def test_cache_key_changes_when_anything_that_changes_the_answer_changes(
    changed: dict[str, Any],
) -> None:
    base: dict[str, Any] = {
        "provider": "openai",
        "model": "gpt-4o",
        "template_name": "extraction_zero_shot",
        "template_version": "1.0.0",
        "strategy": "zero_shot",
        "passage": PASSAGE,
        "temperature": 0.0,
        "max_tokens": 2048,
    }
    assert make_key(**base) == make_key(**base)
    assert make_key(**base) != make_key(**{**base, **changed})


def test_changing_the_prompt_version_busts_the_cache(tmp_path: Path) -> None:
    cache = LLMCache(tmp_path / "cache")
    extractor, fake = make_extractor(tmp_path, cache=cache)
    extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert fake.calls == 1
    # Simulate an edited template: same file name, new version.
    object.__setattr__(extractor.template, "version", "9.9.9")
    extractor.extract(PASSAGE, paper_id="PMC1", section="Methods")
    assert fake.calls == 2, "an edited prompt must not reuse responses from the old wording"


def test_cache_directory_comes_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "from-env"))
    assert LLMCache().cache_dir == tmp_path / "from-env"
    monkeypatch.delenv("LLM_CACHE_DIR")
    assert LLMCache().cache_dir == Path("./llm_cache")


def test_corrupt_cache_file_is_treated_as_a_miss(tmp_path: Path) -> None:
    cache = LLMCache(tmp_path / "cache")
    key = "deadbeef" * 8
    path = cache.path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not json", encoding="utf-8")
    assert cache.get(key) is None
    assert cache.stats()["misses"] == 1


def test_cache_entry_roundtrips_through_disk(tmp_path: Path) -> None:
    cache = LLMCache(tmp_path / "cache")
    key = make_key(
        provider="fake",
        model="gpt-4o",
        template_name="extraction_zero_shot",
        template_version="1.0.0",
        strategy="zero_shot",
        passage=PASSAGE,
        temperature=0.0,
        max_tokens=2048,
    )
    entry = CacheEntry(
        response_text=CLEAN_JSON,
        prompt_tokens=1200,
        completion_tokens=300,
        cost_usd=0.006,
        latency_ms=812.5,
        created_at="2026-08-22T12:00:00+00:00",
        provider="fake",
        model="gpt-4o",
    )
    cache.set(key, entry)
    restored = cache.get(key)
    assert restored is not None
    assert restored.response_text == CLEAN_JSON
    assert restored.prompt_tokens == 1200
    assert restored.cost_usd == pytest.approx(0.006)
    assert restored.created_at.endswith("+00:00")


def test_cache_tolerates_entries_written_by_a_future_version(tmp_path: Path) -> None:
    cache = LLMCache(tmp_path / "cache")
    key = "a" * 64
    path = cache.path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"response_text": "[]", "some_new_field": 1}),
        encoding="utf-8",
    )
    entry = cache.get(key)
    assert entry is not None
    assert entry.response_text == "[]"


def test_llm_cache_directory_is_gitignored_and_documented() -> None:
    """Cached raw model responses must never be committed to a repo that will be public."""
    assert "llm_cache/" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "LLM_CACHE_DIR" in (REPO_ROOT / ".env.example").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------------------
# Clients: keys are read lazily, and only when the client is actually used
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("client_cls", "env_var", "provider"),
    [
        (OpenAIClient, "OPENAI_API_KEY", "openai"),
        (AnthropicClient, "ANTHROPIC_API_KEY", "anthropic"),
        (GroqClient, "GROQ_API_KEY", "groq"),
    ],
)
def test_client_reads_its_key_lazily(
    monkeypatch: pytest.MonkeyPatch, client_cls: Any, env_var: str, provider: str
) -> None:
    monkeypatch.delenv(env_var, raising=False)
    client = client_cls()  # constructing must never need a key
    assert client.provider == provider
    assert client.env_var == env_var
    with pytest.raises(MissingAPIKeyError) as excinfo:
        client.generate("hello", model="whatever")
    assert env_var in str(excinfo.value)


def test_groq_points_at_the_openai_compatible_endpoint() -> None:
    assert GroqClient().base_url == "https://api.groq.com/openai/v1"
    assert OpenAIClient().base_url is None


def test_client_without_a_model_argument_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    with pytest.raises(ValueError, match="requires a 'model'"):
        OpenAIClient().generate("hello")
