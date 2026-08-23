#!/usr/bin/env bash
# Set API keys in .env without them ever appearing on screen, in shell history,
# or in a chat transcript.
#
# Usage:   bash scripts/set_keys.sh
#
# Each prompt is silent (characters are not echoed). Press Return on a prompt to
# leave that key unchanged. Existing entries are replaced in place, not duplicated.
set -euo pipefail

cd "$(dirname "$0")/.."
ENV_FILE=".env"
[ -f "$ENV_FILE" ] || cp .env.example "$ENV_FILE"

set_key() {
  local name="$1" value="$2"
  [ -z "$value" ] && { echo "  $name unchanged"; return; }
  local tmp
  tmp="$(mktemp)"
  grep -v "^${name}=" "$ENV_FILE" > "$tmp" || true
  printf '%s=%s\n' "$name" "$value" >> "$tmp"
  mv "$tmp" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "  $name set (${#value} chars)"
}

echo "Paste each key and press Return. Input is hidden. Empty input keeps the current value."
for name in OPENAI_API_KEY ANTHROPIC_API_KEY GROQ_API_KEY; do
  printf '%s: ' "$name"
  IFS= read -rs value < /dev/tty
  printf '\n'
  set_key "$name" "$value"
  unset value
done

echo
echo "Done. .env is gitignored and now chmod 600."
echo "Verify without revealing values:"
echo "  grep -E '^(OPENAI|ANTHROPIC|GROQ)_API_KEY=' .env | sed 's/=.*/= [set]/'"
