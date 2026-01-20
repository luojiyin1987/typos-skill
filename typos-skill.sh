#!/bin/bash
# Typos Spell Check Skill with LLM Confirmation
# Usage: typos-skill.sh [options] [path...]

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: typos-skill.sh [options] [path...]

Options:
  --diff                 Show proposed changes after the LLM review output
  --export-review <file> Write a review JSONL file for LLM confirmation
  --apply-review <file>  Apply only approved corrections from a review file
  --apply-all            Apply all typos suggestions without review
  -h, --help             Show this help message

Notes:
  - Default path is current directory.
  - Review output is intended for LLM confirmation before applying changes.
EOF
}

ACTION="review"
PATHS=()
EXPORT_REVIEW_FILE=""
REVIEW_FILE=""
PYTHON_BIN=""

require_python() {
    if [[ -n "$PYTHON_BIN" ]]; then
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
        return 0
    fi

    echo "Error: python3 is required to parse typos output." >&2
    echo "Install python3 or ensure it is on PATH." >&2
    exit 127
}

format_paths() {
    local out=()
    local path
    for path in "$@"; do
        out+=("$(printf '%q' "$path")")
    done
    if [[ ${#out[@]} -gt 0 ]]; then
        printf '%s' "${out[*]}"
    fi
}

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
        --apply-review)
            if [[ $# -lt 2 ]]; then
                echo "Missing value for --apply-review" >&2
                usage >&2
                exit 2
            fi
            ACTION="apply-review"
            REVIEW_FILE="$2"
            shift 2
            ;;
        --export-review)
            if [[ $# -lt 2 ]]; then
                echo "Missing value for --export-review" >&2
                usage >&2
                exit 2
            fi
            EXPORT_REVIEW_FILE="$2"
            shift 2
            ;;
        --apply-all)
            ACTION="apply-all"
            shift
            ;;
        --apply)
            echo "Use --apply-review <file> to apply approved fixes or --apply-all to apply everything." >&2
            exit 2
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

if [[ -n "$EXPORT_REVIEW_FILE" && "$ACTION" == "apply-review" ]]; then
    echo "Error: --export-review cannot be used with --apply-review." >&2
    exit 2
fi

if [[ "$ACTION" == "apply-review" ]]; then
    if [[ -z "$REVIEW_FILE" ]]; then
        echo "Error: --apply-review requires a review file." >&2
        exit 2
    fi
    if [[ ! -f "$REVIEW_FILE" ]]; then
        echo "Error: review file not found: $REVIEW_FILE" >&2
        exit 2
    fi
    require_python
    "$PYTHON_BIN" scripts/apply-review.py "$REVIEW_FILE"
    exit 0
fi

if [[ ${#PATHS[@]} -eq 0 ]]; then
    PATHS=(.)
fi

echo "🔍 Running typos spell check on: ${PATHS[*]}"
echo "======================================"

require_python

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

PATHS_DISPLAY=$(format_paths "${PATHS[@]}")

"$PYTHON_BIN" - "$TYPOS_OUTPUT_FILE" "${EXPORT_REVIEW_FILE:-}" <<'PY'
import json
import sys

path = sys.argv[1]
review_path = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None

def iter_items(handle):
    for idx, raw in enumerate(handle, 1):
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"Error: invalid JSON from typos at line {idx}: {exc}", file=sys.stderr)
            sys.exit(1)
        if "typo" not in item or "path" not in item:
            continue
        yield item

count = 0
files = set()

with open(path, "r", encoding="utf-8") as handle:
    for item in iter_items(handle):
        count += 1
        files.add(item.get("path"))

print(f"Found {count} spelling errors in {len(files)} files.")
print("")

review_handle = open(review_path, "w", encoding="utf-8") if review_path else None
try:
    with open(path, "r", encoding="utf-8") as handle:
        for item in iter_items(handle):
            file_path = item.get("path", "<unknown>")
            line_num = item.get("line_num", "?")
            typo = item.get("typo", "")
            corrections = item.get("corrections", []) or []
            suggestion_text = ", ".join(corrections)

            print(f"### `{file_path}`:{line_num}")
            print(f"  **Error**: `{typo}`")
            print(f"  **Suggestions**: [{suggestion_text}]")
            print("")

            if review_handle:
                review_item = {
                    "path": file_path,
                    "line_num": item.get("line_num"),
                    "byte_offset": item.get("byte_offset"),
                    "typo": typo,
                    "corrections": corrections,
                    "status": "PENDING",
                    "correction": ""
                }
                review_handle.write(json.dumps(review_item, ensure_ascii=True) + "\n")
finally:
    if review_handle:
        review_handle.close()

if review_path:
    print(f"Review file written to: {review_path}")
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
echo "Preferred flow:"
echo "1. Run with --export-review to create a review file"
echo "2. Update each JSON line with:"
echo "   - status: ACCEPT CORRECT | FALSE POSITIVE | CUSTOM"
echo "   - correction: required when status is CUSTOM"
echo "3. Apply with --apply-review <file>"
echo ""
echo "Next steps:"
if [[ -n "$EXPORT_REVIEW_FILE" ]]; then
    echo "  - Apply approved: ./typos-skill.sh --apply-review $(printf '%q' "$EXPORT_REVIEW_FILE")"
else
    echo "  - Export review: ./typos-skill.sh --export-review review.jsonl ${PATHS_DISPLAY}"
fi
echo "  - Preview all:   ./typos-skill.sh --diff ${PATHS_DISPLAY}"
echo "  - Apply all:     ./typos-skill.sh --apply-all ${PATHS_DISPLAY}"

case "$ACTION" in
    diff)
        echo ""
        echo "Showing diff of proposed changes:"
        typos --diff "${PATHS[@]}"
        ;;
    apply-all)
        echo ""
        echo "Applying all typos corrections (no LLM filtering)..."
        typos --write-changes "${PATHS[@]}"
        ;;
    review)
        ;;
esac
