#!/usr/bin/env bash
# CLI to suggest commit messages based on local changes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$SCRIPT_DIR/prompts"
SYSTEM_PROMPT_FILE="$PROMPTS_DIR/system.txt"
USER_PROMPT_FILE="$PROMPTS_DIR/user.txt"

MODEL="gpt-4o-mini"
TEMPERATURE="0.0"

usage() {
    cat >&2 <<EOF
Usage: $(basename "$0") [--model MODEL] [--temperature FLOAT]

Suggest a commit message based on git diff.

Options:
  --model        OpenAI model (default: gpt-4o-mini)
  --temperature  Model temperature (default: 0.0)
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)        MODEL="$2";       shift 2 ;;
        --temperature)  TEMPERATURE="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *) echo "Unknown argument: $1" >&2; usage ;;
    esac
done

# Load .env if present (mimics python-dotenv)
if [[ -f ".env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source ".env"
    set +a
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "Error: OPENAI_API_KEY was not found in the environment." >&2
    exit 1
fi

# Get staged diff
if ! DIFF=$(git diff --staged 2>&1); then
    echo "Error reading diff: $DIFF" >&2
    exit 1
fi

if [[ -z "${DIFF// /}" ]]; then
    echo "No changes found to suggest a commit message." >&2
    exit 1
fi

# Load prompts
for f in "$SYSTEM_PROMPT_FILE" "$USER_PROMPT_FILE"; do
    if [[ ! -f "$f" ]]; then
        echo "Could not read prompt file at $f" >&2
        exit 1
    fi
done

SYSTEM_CONTENT=$(< "$SYSTEM_PROMPT_FILE")
USER_TEMPLATE=$(< "$USER_PROMPT_FILE")

if [[ "$USER_TEMPLATE" != *"{diff}"* ]]; then
    echo "User prompt must contain the {diff} placeholder." >&2
    exit 1
fi

# Truncate diff to 14000 chars and substitute placeholder
DIFF_TRUNCATED="${DIFF:0:14000}"
USER_CONTENT="${USER_TEMPLATE/\{diff\}/$DIFF_TRUNCATED}"

# Build JSON payload
PAYLOAD=$(jq -n \
    --arg     model       "$MODEL" \
    --argjson temperature "$TEMPERATURE" \
    --arg     system      "$SYSTEM_CONTENT" \
    --arg     user        "$USER_CONTENT" \
    '{model: $model, temperature: $temperature,
      messages: [{role:"system", content:$system},
                 {role:"user",   content:$user}]}')

# Call OpenAI API
if ! RESPONSE=$(curl -sf \
        -X POST "https://api.openai.com/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $OPENAI_API_KEY" \
        -d "$PAYLOAD"); then
    echo "OpenAI request failed." >&2
    exit 1
fi

SUGGESTION=$(echo "$RESPONSE" | jq -r '.choices[0].message.content // empty')

if [[ -z "$SUGGESTION" ]]; then
    echo "The model did not return a suggestion." >&2
    exit 1
fi

printf "Suggested commit message:\n%s\n\n" "$SUGGESTION"
read -r -p "Do you want to apply this message and run git commit for staged changes? [y/N]: " ANSWER

case "${ANSWER,,}" in
    y|yes) ;;
    *)
        echo "Commit canceled by user."
        exit 0
        ;;
esac

if ! echo "$SUGGESTION" | git commit -F -; then
    echo "git commit failed." >&2
    exit 1
fi

echo "Commit created successfully."
