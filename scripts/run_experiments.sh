#!/usr/bin/env bash
# Run the full experimental grid for the MOF synthesis extraction study.
#
#   bash scripts/run_experiments.sh              # the real run, over the gold passages
#   bash scripts/run_experiments.sh --smoke      # 2 passages per extractor, to prove wiring
#
# The model set was chosen on 2026-08-31 and costs about EUR 1.72 in total, batched.
#
#   groq:llama-3.3-70b-versatile   open-weight strand, free tier, answers RQ4
#   openai:gpt-4o-mini             cheap commercial tier, about EUR 0.10 for the whole grid
#   openai:gpt-4o                  strong commercial tier
#
# Why two OpenAI tiers rather than two vendors: pairing gpt-4o-mini with gpt-4o buys a
# cost-versus-accuracy curve within one vendor, which answers "does the cheap model lose
# much" directly. A second vendor at the same price point would only add another dot at the
# same place on that curve, for more money. Anthropic is deliberately not in this run; it
# can be added later for about EUR 2 more if a second vendor turns out to matter.
#
# Requires OPENAI_API_KEY and GROQ_API_KEY in .env. Anthropic and NVIDIA are not used here.
set -euo pipefail
cd "$(dirname "$0")/.."

set -a; [ -f .env ] && . ./.env; set +a

missing=0
for k in OPENAI_API_KEY GROQ_API_KEY; do
  if [ -z "${!k:-}" ]; then echo "MISSING: $k is not set in .env"; missing=1; fi
done
[ "$missing" -eq 1 ] && { echo; echo "Add the keys, then re-run. Nothing was called, nothing was billed."; exit 1; }

STRATEGIES=(zero_shot few_shot schema_guided cot)
MODELS=(groq:llama-3.3-70b-versatile openai:gpt-4o-mini openai:gpt-4o)

SPECS="rule_based"
for m in "${MODELS[@]}"; do
  for s in "${STRATEGIES[@]}"; do SPECS="${SPECS},${m}:${s}"; done
done

EXTRA=""
if [ "${1:-}" = "--smoke" ]; then
  EXTRA="--limit 2"
  echo "SMOKE RUN: 2 passages per extractor. Proves wiring and keys without spending."
fi

echo "extractors: 1 baseline + $(( ${#MODELS[@]} * ${#STRATEGIES[@]} )) LLM combinations"
echo "the run is resumable: if it dies, re-run this script and it continues where it stopped"
echo

exec .venv/bin/python -m src.pipeline --extractors "$SPECS" $EXTRA
