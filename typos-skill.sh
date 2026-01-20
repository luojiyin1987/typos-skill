#!/bin/bash
# Typos Spell Check Skill with LLM Confirmation
# Usage: typos-skill.sh [options] [path...]

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: typos-skill.sh [options] [path...]

Options:
  --diff        Show proposed changes after the LLM review output
  --apply       Apply typos suggestions after the LLM review output
  -h, --help    Show this help message

Notes:
  - Default path is current directory.
  - Review output is intended for LLM confirmation before --apply.
EOF
}

ACTION="review"
PATHS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --diff)
            ACTION="diff"
            shift
            ;;
        --apply)
            ACTION="apply"
            shift
            ;;
        --)
            shift
            break
            ;;
        -*)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            PATHS+=("$1")
            shift
            ;;
    esac
done

if [[ $# -gt 0 ]]; then
    PATHS+=("$@")
fi

if [[ ${#PATHS[@]} -eq 0 ]]; then
    PATHS=(.)
fi

echo "🔍 Running typos spell check on: ${PATHS[*]}"
echo "======================================"

if ! command -v typos >/dev/null 2>&1; then
    echo "Error: typos CLI not found. Install with: cargo install typos-cli" >&2
    exit 127
fi

TYPOS_OUTPUT_FILE=$(mktemp /tmp/typos-skill.XXXXXX.jsonl)
TYPOS_ERROR_FILE=$(mktemp /tmp/typos-skill.XXXXXX.err)
cleanup() {
    rm -f "$TYPOS_OUTPUT_FILE" "$TYPOS_ERROR_FILE"
}
trap cleanup EXIT

set +e
typos --format json "${PATHS[@]}" >"$TYPOS_OUTPUT_FILE" 2>"$TYPOS_ERROR_FILE"
TYPOS_STATUS=$?
set -e

if [[ ! -s "$TYPOS_OUTPUT_FILE" ]]; then
    if [[ $TYPOS_STATUS -ne 0 ]]; then
        echo "Error: typos failed (exit $TYPOS_STATUS)." >&2
        if [[ -s "$TYPOS_ERROR_FILE" ]]; then
            sed 's/^/  /' "$TYPOS_ERROR_FILE" >&2
        fi
        exit "$TYPOS_STATUS"
    fi
    echo "✅ No spelling errors found!"
    exit 0
fi

if [[ -s "$TYPOS_ERROR_FILE" ]]; then
    echo "typos warnings:" >&2
    sed 's/^/  /' "$TYPOS_ERROR_FILE" >&2
    echo "" >&2
fi

# Parse typos and create summary for LLM
echo ""
echo "📝 Found spelling errors. Preparing for LLM review..."
echo ""

python - "$TYPOS_OUTPUT_FILE" <<'PY'
import json
import sys

path = sys.argv[1]
count = 0
files = set()

with open(path, "r", encoding="utf-8") as handle:
    for idx, raw in enumerate(handle, 1):
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"Error: invalid JSON from typos at line {idx}: {exc}", file=sys.stderr)
            sys.exit(1)
        count += 1
        if "path" in item:
            files.add(item["path"])

print(f"Found {count} spelling errors in {len(files)} files.")
print("")

with open(path, "r", encoding="utf-8") as handle:
    for idx, raw in enumerate(handle, 1):
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"Error: invalid JSON from typos at line {idx}: {exc}", file=sys.stderr)
            sys.exit(1)

        file_path = item.get("path", "<unknown>")
        line_num = item.get("line_num", "?")
        typo = item.get("typo", "")
        corrections = item.get("corrections", []) or []
        suggestion_text = ", ".join(corrections)

        print(f"### `{file_path}`:{line_num}")
        print(f"  **Error**: `{typo}`")
        print(f"  **Suggestions**: [{suggestion_text}]")
        print("")
PY

echo "======================================"
echo ""
echo "📋 Instructions for LLM Review:"
echo ""
echo "For each error above:"
echo "1. Read the file at the specified line to understand context"
echo "2. Determine if it's a TRUE ERROR or FALSE POSITIVE (technical term, variable name, etc.)"
echo "3. If accepting, provide the correction; if rejecting, explain why"
echo ""
echo "Response format:"
echo '```'
echo '### <file_path>:<line>'
echo '**Status**: [ACCEPT CORRECT | FALSE POSITIVE | CUSTOM]'
echo '**Original**: <error_text>'
echo '**Correction**: <corrected_text>'
echo '**Reason**: <brief explanation>'
echo '```'
echo ""
echo "Next steps after confirmation:"
echo "  - Preview: ./typos-skill.sh --diff ${PATHS[*]}"
echo "  - Apply:   ./typos-skill.sh --apply ${PATHS[*]}"

case "$ACTION" in
    diff)
        echo ""
        echo "Showing diff of proposed changes:"
        typos --diff "${PATHS[@]}"
        ;;
    apply)
        echo ""
        echo "Applying typos corrections..."
        typos --write-changes "${PATHS[@]}"
        ;;
    review)
        ;;
esac
