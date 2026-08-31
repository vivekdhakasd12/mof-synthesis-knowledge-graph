"""LLM based triple extraction: clients, prompt templates and defensive response parsing.

This module is the experimental apparatus of the study. The research questions compare
four prompting strategies (zero-shot, few-shot, schema-guided, chain-of-thought) across
three models (an OpenAI model, an Anthropic model, and an open-weight Llama served by
Groq), so every one of those twelve combinations has to run through exactly the same
code path. Anything that differs between them other than the prompt and the model would
confound the comparison.

Three design decisions carry most of the weight here.

1. The model is reached through an LLMClient Protocol, never through a vendor SDK imported
   at module level. That is what makes the whole module testable offline: the test suite
   injects a deterministic fake client and never opens a socket. It also means the code was
   written and validated before any API key existed, and will run unchanged when keys
   arrive. API keys are read lazily, inside the call, so importing this module (or the CLI
   that uses it) never requires a key and never fails on a machine that has none.

2. Nothing the model says is trusted as provenance. paper_id and section come from the
   caller, which knows them for certain, and are stamped onto every triple. A model asked
   to report its own source would occasionally get it wrong, and a knowledge graph whose
   provenance is itself a model guess would be worthless for the validation this project
   is graded on.

3. Parsing is forgiving about form and strict about content. Real models return JSON
   wrapped in prose, inside markdown fences, with trailing commas, or as a single object
   where a list was requested; all of that is recovered, because throwing away a good
   extraction over a cosmetic defect would understate the model's accuracy. But a triple
   whose relation is not in the ontology, or whose endpoint types violate the ontology, or
   which carries no evidence sentence, is dropped and the reason is recorded in
   ExtractionResult.errors. Those two error classes are different phenomena and the error
   taxonomy in the evaluation needs to tell them apart.

extract() never raises. A batch over hundreds of passages must not die on passage 200
because one response was malformed; the failure has to become data instead.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol, cast, get_args

from loguru import logger

from src.extraction.cache import CacheEntry, LLMCache, make_key, utc_now_iso
from src.extraction.extractor_base import (
    Confidence,
    Entity,
    EntityType,
    ExtractionResult,
    Extractor,
    RelationType,
    Triple,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_DIR = REPO_ROOT / "configs" / "prompts"
ONTOLOGY_PATH = REPO_ROOT / "configs" / "ontology.json"

# Strategy name -> template file stem. The strategy name is what appears in the results
# tables and in the cache key, so it is fixed here rather than derived from filenames.
STRATEGIES: dict[str, str] = {
    "zero_shot": "extraction_zero_shot",
    "few_shot": "extraction_few_shot",
    "schema_guided": "extraction_schema_guided",
    "cot": "extraction_cot",
}

ENTITY_TYPES: frozenset[str] = frozenset(get_args(EntityType))
RELATION_TYPES: frozenset[str] = frozenset(get_args(RelationType))
CONFIDENCE_VALUES: frozenset[str] = frozenset(get_args(Confidence))

# MENTIONED_IN is provenance written by the pipeline (see src/kg/loader.py). A model that
# emits it is guessing at a fact it cannot know, so it is dropped rather than trusted.
PIPELINE_ONLY_RELATIONS: frozenset[str] = frozenset({"MENTIONED_IN"})
PIPELINE_ONLY_ENTITY_TYPES: frozenset[str] = frozenset({"Paper"})

# ---------------------------------------------------------------------------------------
# PRICES. Single source of truth for cost accounting, USD per 1,000,000 tokens, as
# (prompt, completion).
#
# WARNING TO WHOEVER RUNS THE FINAL EXPERIMENT: these are list prices recorded from vendor
# pricing pages and they change without notice. RE-VERIFY EVERY ROW against the provider's
# current pricing page before the final run, and record the date you checked in the report.
# Any model missing from this table yields cost 0.0 plus an entry in
# ExtractionResult.errors; a price is never guessed, because a guessed price would become a
# fabricated number in the cost table.
# ---------------------------------------------------------------------------------------
PRICE_PER_MTOK_USD: dict[str, tuple[float, float]] = {
    # OpenAI. NOT yet re-verified in-project; check openai.com/api/pricing before the run.
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    # Anthropic. Verified 2026-08-23. Sonnet 5 carries introductory pricing of
    # (2.00, 10.00) through 2026-08-31, after which it reverts to the values below, so a
    # run that slips past August costs about 50 percent more on this row.
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-opus-5": (5.00, 25.00),
    # Groq. List price for the paid tier. The project runs this model on the free tier, so
    # the realised cost is zero; the list price is kept here so the report can state what
    # the open-weight strand WOULD have cost at commercial rates, which is the honest
    # comparison for research question 4.
    "llama-3.3-70b-versatile": (0.59, 0.79),
    # NVIDIA NIM backup host. Run on the free tier, so realised cost is zero. Unlike the
    # Groq row there is no verified per-token list price recorded here, so the counterfactual
    # "what this would have cost commercially" cannot be quoted for these models. Report the
    # realised zero and say the list price was not established, rather than inventing one.
    "nvidia/llama-3.1-nemotron-70b-instruct": (0.0, 0.0),
}
PRICE_TABLE_CHECKED_ON = "2026-08-23 (Anthropic rows verified; OpenAI and Groq rows pending)"


class MissingAPIKeyError(RuntimeError):
    """Raised when a client is actually used without its API key being set."""


@dataclass(frozen=True)
class LLMResponse:
    """What every client returns: the raw text plus the token counts used for costing.

    Token counts come from the provider's usage report rather than from a local tokenizer,
    because the provider's count is what is billed and therefore what the cost table must
    be built from.
    """

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMClient(Protocol):
    """The only surface the extractor needs from a model provider.

    Deliberately one method with open keyword arguments: it keeps the fake client used in
    the tests trivial (a few lines, no mocking library) and it means adding a provider is a
    small class rather than a change to the extractor.
    """

    provider: str

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse: ...


def _require_key(env_var: str, provider: str, where: str) -> str:
    """Read an API key at call time, with an error a human can act on.

    Reading keys lazily (never at import) is what lets the whole module be imported, tested
    and type-checked on a machine with no credentials at all.
    """
    key = os.environ.get(env_var, "").strip()
    if not key:
        raise MissingAPIKeyError(
            f"{provider} was called but {env_var} is not set. "
            f"Add {env_var}=... to your .env (see .env.example) or export it in the shell. "
            f"Get a key at {where}."
        )
    return key


class _OpenAICompatibleClient:
    """Shared implementation for any provider speaking the OpenAI chat-completions API.

    Groq is used for the open-weight strand precisely because it speaks this protocol, so
    the Llama runs need no separate code path and cannot accidentally differ from the
    OpenAI runs in anything but the model and the endpoint. Running Llama locally on the
    project laptop was rejected: roughly 6,000 calls on 8 GB of RAM would have taken the
    machine out of service for days.
    """

    provider: str = "openai-compatible"
    env_var: str = "OPENAI_API_KEY"
    base_url: str | None = None
    console_url: str = "https://platform.openai.com/api-keys"

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        model = kwargs.get("model")
        if not model:
            raise ValueError("generate() requires a 'model' keyword argument")
        api_key = _require_key(self.env_var, self.provider, self.console_url)
        # Imported inside the call so that neither the test suite nor the CLI pays the
        # import cost, and so a missing SDK never breaks collection of unrelated tests.
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=str(model),
            messages=[{"role": "user", "content": prompt}],
            temperature=float(kwargs.get("temperature", 0.0)),
            max_tokens=int(kwargs.get("max_tokens", 2048)),
        )
        text = response.choices[0].message.content or ""
        usage = response.usage
        return LLMResponse(
            text=text,
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )


class OpenAIClient(_OpenAICompatibleClient):
    provider: str = "openai"
    env_var: str = "OPENAI_API_KEY"
    base_url: str | None = None
    console_url: str = "https://platform.openai.com/api-keys"


class GroqClient(_OpenAICompatibleClient):
    """Open-weight strand (llama-3.3-70b-versatile) via Groq's OpenAI-compatible endpoint."""

    provider: str = "groq"
    env_var: str = "GROQ_API_KEY"
    base_url: str | None = "https://api.groq.com/openai/v1"
    console_url: str = "https://console.groq.com/keys"


class NvidiaClient(_OpenAICompatibleClient):
    """Backup open-weight host: NVIDIA NIM, also OpenAI-compatible.

    Not the primary open-weight strand. NVIDIA does not host meta/llama-3.3-70b-instruct,
    so it cannot reproduce the Groq run exactly; its strongest comparable text models are
    NVIDIA's own Nemotron derivatives (for example nvidia/llama-3.1-nemotron-70b-instruct).

    It earns its place as insurance rather than as a result. The Groq free tier allows about
    1,000 requests per day and the evaluation grid needs 800, so a single misfire can strand
    the open-weight strand for 24 hours with a fixed submission date approaching. Switching
    host is then a one word change to the extractor spec.

    If it is used for anything reported, say which host and which model produced each number:
    a Nemotron result is not interchangeable with a Llama-3.3 result.
    """

    provider: str = "nvidia"
    env_var: str = "NVIDIA_API_KEY"
    base_url: str | None = "https://integrate.api.nvidia.com/v1"
    console_url: str = "https://build.nvidia.com"


class AnthropicClient:
    provider: str = "anthropic"
    env_var: str = "ANTHROPIC_API_KEY"
    console_url: str = "https://console.anthropic.com/settings/keys"

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        model = kwargs.get("model")
        if not model:
            raise ValueError("generate() requires a 'model' keyword argument")
        api_key = _require_key(self.env_var, self.provider, self.console_url)
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=str(model),
            max_tokens=int(kwargs.get("max_tokens", 2048)),
            temperature=float(kwargs.get("temperature", 0.0)),
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [getattr(block, "text", "") for block in response.content]
        usage = response.usage
        return LLMResponse(
            text="".join(parts),
            prompt_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        )


def price_for(model: str) -> tuple[float, float] | None:
    """Look up (prompt, completion) price, tolerating dated model ids.

    Providers pin releases as "gpt-4o-2024-08-06" or "claude-3-5-sonnet-20241022". Matching
    the longest table key that the id starts with keeps the table short without ever
    inventing a price for a model that is genuinely absent.
    """
    if model in PRICE_PER_MTOK_USD:
        return PRICE_PER_MTOK_USD[model]
    candidates = [k for k in PRICE_PER_MTOK_USD if model.startswith(k)]
    if not candidates:
        return None
    return PRICE_PER_MTOK_USD[max(candidates, key=len)]


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    """USD for one call, or None when the model has no verified price entry."""
    price = price_for(model)
    if price is None:
        return None
    prompt_price, completion_price = price
    return (prompt_tokens / 1_000_000) * prompt_price + (
        completion_tokens / 1_000_000
    ) * completion_price


# ---------------------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------------------

_META_LINE = re.compile(r"^#\s*([A-Za-z][A-Za-z _-]*?)\s*:\s*(.*)$")


@dataclass(frozen=True)
class PromptTemplate:
    """A versioned prompt file loaded from configs/prompts/.

    Prompts live in files, not in Python string literals, so that the exact wording used
    for a result is a diffable, citable artefact. The version travels into the cache key,
    which is what stops an edited prompt from silently returning responses generated by the
    previous wording.
    """

    name: str
    version: str
    text: str
    path: Path

    def render(self, passage: str) -> str:
        """Substitute the passage.

        str.replace, not str.format: the templates contain a literal JSON schema full of
        braces, and str.format would either raise on them or mangle them.
        """
        return self.text.replace("{passage}", passage)


def _split_header(raw: str) -> tuple[dict[str, str], str]:
    """Peel the leading '#' metadata block off a template file."""
    meta: dict[str, str] = {}
    lines = raw.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        if not line.startswith("#"):
            body_start = i
            break
        match = _META_LINE.match(line)
        if match:
            key = match.group(1).strip().lower().replace(" ", "_").replace("-", "_")
            meta.setdefault(key, match.group(2).strip())
    else:
        body_start = len(lines)
    return meta, "\n".join(lines[body_start:]).strip() + "\n"


@lru_cache(maxsize=32)
def load_template(stem: str, prompt_dir: str) -> PromptTemplate:
    """Load and cache a template by file stem.

    Cached because a batch run constructs the same extractor over and over; the cache is
    keyed on the resolved path so two prompt directories (say, an ablation copy) do not
    collide.
    """
    path = Path(prompt_dir) / f"{stem}.txt"
    raw = path.read_text(encoding="utf-8")
    meta, body = _split_header(raw)
    version = meta.get("version", "")
    if not version:
        # A template with no version header still has to be pinned, otherwise editing it
        # would reuse stale cached responses. Hashing the body is the honest fallback: the
        # key changes exactly when the wording changes. extraction_schema_guided.txt
        # predates the header convention and takes this path.
        version = "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
        logger.debug("Template {} has no version header, using content hash {}", stem, version)
    if "{passage}" not in body:
        raise ValueError(f"Prompt template {path} has no {{passage}} placeholder")
    return PromptTemplate(name=stem, version=version, text=body, path=path)


@lru_cache(maxsize=4)
def relation_endpoints(ontology_path: str) -> dict[str, tuple[str, str]]:
    """Read the allowed (subject type, object type) per relation from the ontology file.

    Read from configs/ontology.json rather than hard-coded here, because the ontology file
    is the declared source of truth and a second copy of the endpoints in Python would be
    free to drift away from it.
    """
    data = json.loads(Path(ontology_path).read_text(encoding="utf-8"))
    endpoints: dict[str, tuple[str, str]] = {}
    for relation, spec in data.get("relations", {}).items():
        source, target = spec.get("from"), spec.get("to")
        if isinstance(source, str) and isinstance(target, str):
            endpoints[relation] = (source, target)
    return endpoints


# ---------------------------------------------------------------------------------------
# Defensive JSON recovery
# ---------------------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:[A-Za-z0-9_+-]*)\s*\n?(.*?)```", re.DOTALL)
_TRAILING_COMMA = re.compile(r",(\s*[\]}])")
_FINAL_MARKER = re.compile(r"FINAL[ _]?(?:JSON|ANSWER)\s*:?", re.IGNORECASE)
_ITEM_LIST_KEYS = ("triples", "relations", "extractions", "results", "data", "output")


def _balanced_spans(text: str, limit: int = 4) -> list[str]:
    """Return top-level {...} / [...] substrings, skipping brackets inside JSON strings."""
    spans: list[str] = []
    i, n = 0, len(text)
    while i < n and len(spans) < limit:
        if text[i] not in "[{":
            i += 1
            continue
        depth, in_string, escaped, j = 0, False, False, i
        while j < n:
            char = text[j]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
                if depth == 0:
                    spans.append(text[i : j + 1])
                    break
            j += 1
        i = j + 1
    return spans


def _loads_forgiving(raw: str) -> Any | None:
    """json.loads, retried once with trailing commas stripped. Returns None if unparseable."""
    candidate = raw.strip()
    if not candidate:
        return None
    for attempt in (candidate, _TRAILING_COMMA.sub(r"\1", candidate)):
        try:
            return json.loads(attempt)
        except ValueError:
            continue
    return None


def _json_candidates(text: str) -> list[str]:
    """Every substring of a response that might be the JSON payload, best guess first.

    Order matters: chain-of-thought responses put prose before the answer, so anything
    after the last FINAL JSON marker is tried before the whole text, otherwise a bracketed
    aside inside the reasoning could be parsed as the answer.
    """
    scopes: list[str] = []
    tail = _after_final_marker(text)
    if tail is not None:
        scopes.append(tail)
    scopes.append(text)

    candidates: list[str] = []
    for scope in scopes:
        fenced = _FENCE.findall(scope)
        candidates.extend(reversed(fenced))  # the last fence is usually the answer
        candidates.append(scope)
        candidates.extend(_balanced_spans(scope))
    return candidates


def _after_final_marker(text: str) -> str | None:
    matches = list(_FINAL_MARKER.finditer(text))
    if not matches:
        return None
    return text[matches[-1].end() :]


def _payload_to_items(payload: Any) -> tuple[list[Any], list[str]]:
    """Normalise whatever parsed out of the response into a list of candidate triples."""
    notes: list[str] = []
    if isinstance(payload, list):
        return payload, notes
    if isinstance(payload, dict):
        for key in _ITEM_LIST_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                notes.append(f"response was an object; used its '{key}' list")
                return value, notes
        if "relation" in payload:
            notes.append("response was a single triple object; wrapped it in a list")
            return [payload], notes
        notes.append("response was an object with no recognisable triple list")
        return [], notes
    notes.append(f"response JSON was a {type(payload).__name__}, expected a list of triples")
    return [], notes


def _coerce_span(raw: Any) -> tuple[int, int] | None:
    if isinstance(raw, list | tuple) and len(raw) == 2:
        try:
            return int(raw[0]), int(raw[1])
        except (TypeError, ValueError):
            return None
    return None


def _coerce_entity(raw: Any, role: str, index: int, errors: list[str]) -> Entity | None:
    """Validate one endpoint of a triple; None means the triple must be dropped."""
    if not isinstance(raw, dict):
        errors.append(f"triple {index}: {role} is {type(raw).__name__}, expected an object")
        return None
    raw_type = raw.get("type") or raw.get("entity_type") or raw.get("label")
    raw_name = raw.get("name") or raw.get("text") or raw.get("value")
    if not isinstance(raw_type, str) or not isinstance(raw_name, str) or not raw_name.strip():
        errors.append(f"triple {index}: {role} is missing a usable type or name")
        return None
    entity_type = raw_type.strip()
    if entity_type in PIPELINE_ONLY_ENTITY_TYPES:
        errors.append(
            f"triple {index}: {role} type '{entity_type}' is written by the pipeline, "
            "not extracted; dropped"
        )
        return None
    if entity_type not in ENTITY_TYPES:
        errors.append(f"triple {index}: {role} type '{entity_type}' is not in the ontology")
        return None
    return Entity(
        type=cast(EntityType, entity_type),
        name=raw_name.strip(),
        span=_coerce_span(raw.get("span")),
    )


class LLMExtractor(Extractor):
    """Prompt one model with one strategy and turn its answer into validated Triples.

    Constructing this object may raise (an unknown strategy or an unreadable template is a
    configuration bug that should stop the run immediately), but extract() never does.
    """

    def __init__(
        self,
        client: LLMClient,
        strategy: str = "schema_guided",
        model: str = "gpt-4o",
        prompt_dir: str | Path | None = None,
        *,
        cache: LLMCache | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        ontology_path: str | Path | None = None,
    ) -> None:
        if strategy not in STRATEGIES:
            raise ValueError(
                f"Unknown strategy '{strategy}'. Available: {', '.join(sorted(STRATEGIES))}"
            )
        self.client = client
        self.strategy = strategy
        self.model = model
        self.prompt_dir = Path(prompt_dir) if prompt_dir is not None else PROMPT_DIR
        self.template = load_template(STRATEGIES[strategy], str(self.prompt_dir))
        self.cache = cache if cache is not None else LLMCache()
        # Temperature 0 by default: the study needs the same passage to give the same
        # answer on a rerun, and sampling variance would otherwise be mistaken for a
        # difference between prompting strategies.
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.ontology_path = Path(ontology_path) if ontology_path is not None else ONTOLOGY_PATH
        self.name = f"llm:{model}:{strategy}"

    @property
    def provider(self) -> str:
        return str(getattr(self.client, "provider", "unknown"))

    def cache_key(self, passage: str) -> str:
        return make_key(
            provider=self.provider,
            model=self.model,
            template_name=self.template.name,
            template_version=self.template.version,
            strategy=self.strategy,
            passage=passage,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    def extract(
        self,
        passage: str,
        *,
        paper_id: str | None = None,
        section: str | None = None,
    ) -> ExtractionResult:
        started = time.perf_counter()
        errors: list[str] = []
        try:
            prompt = self.template.render(passage)
            key = self.cache_key(passage)

            cached = self.cache.get(key)
            if cached is not None:
                triples, parse_errors = self.parse_response(
                    cached.response_text, paper_id=paper_id, section=section
                )
                errors.extend(parse_errors)
                # cost 0.0 on a cache hit is deliberate: nothing was paid for this call.
                # What the cache saved is reported by LLMCache.stats()["spend_avoided_usd"],
                # which keeps "what this run cost" and "what it would have cost" separate.
                return ExtractionResult(
                    triples=triples,
                    cost_usd=0.0,
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                    errors=errors,
                )

            call_started = time.perf_counter()
            try:
                response = self.client.generate(
                    prompt,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
            except Exception as exc:
                # A provider outage, a rate limit or a missing key must become a recorded
                # failure for this passage, not the end of a batch of several hundred.
                logger.warning("{}: client call failed: {}", self.name, exc)
                errors.append(f"client call failed: {type(exc).__name__}: {exc}")
                return ExtractionResult(
                    triples=[],
                    cost_usd=0.0,
                    latency_ms=(time.perf_counter() - call_started) * 1000.0,
                    errors=errors,
                )
            call_ms = (time.perf_counter() - call_started) * 1000.0

            prompt_tokens = int(getattr(response, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(response, "completion_tokens", 0) or 0)
            cost = estimate_cost_usd(self.model, prompt_tokens, completion_tokens)
            if cost is None:
                errors.append(
                    f"no verified price for model '{self.model}'; cost recorded as 0.0 "
                    "(TODO: add the model to PRICE_PER_MTOK_USD after checking the "
                    "provider's pricing page)"
                )
                cost = 0.0
            if prompt_tokens == 0 and completion_tokens == 0:
                errors.append("provider reported no token usage; cost is a lower bound")

            self.cache.set(
                key,
                CacheEntry(
                    response_text=response.text,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                    latency_ms=call_ms,
                    created_at=utc_now_iso(),
                    provider=self.provider,
                    model=self.model,
                    template=self.template.name,
                    template_version=self.template.version,
                    strategy=self.strategy,
                ),
            )

            triples, parse_errors = self.parse_response(
                response.text, paper_id=paper_id, section=section
            )
            errors.extend(parse_errors)
            return ExtractionResult(
                triples=triples, cost_usd=cost, latency_ms=call_ms, errors=errors
            )
        except Exception as exc:  # last resort: extract() is contractually non-raising
            logger.exception("{}: unexpected failure in extract()", self.name)
            errors.append(f"unexpected failure in extract(): {type(exc).__name__}: {exc}")
            return ExtractionResult(
                triples=[],
                cost_usd=0.0,
                latency_ms=(time.perf_counter() - started) * 1000.0,
                errors=errors,
            )

    # -- parsing ---------------------------------------------------------------------
    def parse_response(
        self,
        text: str,
        *,
        paper_id: str | None = None,
        section: str | None = None,
    ) -> tuple[list[Triple], list[str]]:
        """Turn raw model text into validated triples plus a list of everything wrong with it.

        Kept public and side-effect free so the error taxonomy in src/evaluation can replay
        cached responses through exactly the same parser that produced the original run.
        """
        errors: list[str] = []
        payload: Any = None
        for candidate in _json_candidates(text):
            payload = _loads_forgiving(candidate)
            if payload is not None:
                break
        if payload is None:
            preview = text.strip().replace("\n", " ")[:160]
            errors.append(f"no parseable JSON in response (first 160 chars: {preview!r})")
            return [], errors

        items, notes = _payload_to_items(payload)
        errors.extend(notes)

        try:
            endpoints = relation_endpoints(str(self.ontology_path))
        except (OSError, ValueError) as exc:
            endpoints = {}
            errors.append(f"could not read ontology endpoints, endpoint checks skipped: {exc}")

        triples: list[Triple] = []
        for index, item in enumerate(items):
            triple = self._coerce_triple(
                item, index, endpoints, errors, paper_id=paper_id, section=section
            )
            if triple is not None:
                triples.append(triple)
        return triples, errors

    def _coerce_triple(
        self,
        item: Any,
        index: int,
        endpoints: dict[str, tuple[str, str]],
        errors: list[str],
        *,
        paper_id: str | None,
        section: str | None,
    ) -> Triple | None:
        if not isinstance(item, dict):
            errors.append(f"triple {index}: expected an object, got {type(item).__name__}")
            return None

        raw_relation = item.get("relation") or item.get("predicate") or item.get("type")
        if not isinstance(raw_relation, str):
            errors.append(f"triple {index}: missing relation")
            return None
        relation = raw_relation.strip().upper().replace(" ", "_").replace("-", "_")
        if relation in PIPELINE_ONLY_RELATIONS:
            errors.append(
                f"triple {index}: relation '{relation}' is provenance written by the "
                "pipeline and must not be extracted; dropped"
            )
            return None
        if relation not in RELATION_TYPES:
            errors.append(f"triple {index}: relation '{raw_relation}' is not in the ontology")
            return None

        subject = _coerce_entity(item.get("subject"), "subject", index, errors)
        obj = _coerce_entity(item.get("object"), "object", index, errors)
        if subject is None or obj is None:
            return None

        expected = endpoints.get(relation)
        if expected is not None and (subject.type, obj.type) != expected:
            message = (
                f"triple {index}: {relation} requires {expected[0]} -> {expected[1]} but got "
                f"{subject.type} -> {obj.type}; dropped"
            )
            logger.debug("{}: {}", self.name, message)
            errors.append(message)
            return None

        evidence = item.get("evidence") or item.get("sentence") or ""
        if not isinstance(evidence, str) or not evidence.strip():
            # Provenance is mandatory: a triple with no evidence sentence cannot be checked
            # by a human annotator, so it cannot be allowed into the graph.
            errors.append(f"triple {index}: no evidence sentence; dropped")
            return None

        raw_confidence = item.get("confidence", "medium")
        confidence = raw_confidence.strip().lower() if isinstance(raw_confidence, str) else ""
        if confidence not in CONFIDENCE_VALUES:
            errors.append(
                f"triple {index}: unusable confidence {raw_confidence!r}, defaulted to 'medium'"
            )
            confidence = "medium"

        return Triple(
            subject=subject,
            relation=cast(RelationType, relation),
            object=obj,
            evidence=evidence.strip(),
            confidence=cast(Confidence, confidence),
            # Provenance comes from the caller, never from the model.
            source_paper_id=paper_id,
            source_section=section,
            extractor=self.name,
        )
