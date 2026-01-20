#!/bin/bash
# Typos Spell Check Skill with LLM Confirmation
# Usage: typos-skill.sh [path...]

set -euo pipefail

# Default path is current directory
PATHS=("${@:-.}")

echo "🔍 Running typos spell check on: ${PATHS[*]}"
echo "======================================"

# Run typos and capture JSON output
TYPOS_OUTPUT=$(typos --format json "${PATHS[@]}" 2>/dev/null || true)

# Check if there are any typos
if [[ -z "$TYPOS_OUTPUT" ]]; then
    echo "✅ No spelling errors found!"
    exit 0
fi

# Parse typos and create summary for LLM
echo ""
echo "📝 Found spelling errors. Preparing for LLM review..."
echo ""

# Parse JSON using grep/sed (works without jq)
echo "$TYPOS_OUTPUT" | while IFS= read -r line; do
    if [[ -n "$line" ]]; then
        # Extract fields using simple parsing
        FILE_PATH=$(echo "$line" | sed -n 's/.*"path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
        LINE_NUM=$(echo "$line" | sed -n 's/.*"line_num"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p')
        TYPO_WORD=$(echo "$line" | sed -n 's/.*"typo"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
        CORRECTIONS=$(echo "$line" | sed -n 's/.*"corrections"[[:space:]]*:[[:space:]]*\[\(.*\)\].*/\1/p' | tr '"' ' ')

        echo "### \`$FILE_PATH\`:$LINE_NUM"
        echo "  **Error**: \`$TYPO_WORD\`"
        echo "  **Suggestions**: [$CORRECTIONS]"
        echo ""
    fi
done

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
read -r -p "Press Enter to continue, Ctrl+C to cancel..."

# Ask user what to do
echo ""
read -r -p "Apply corrections? [y=auto-apply typos suggestions / n=cancel / l=show diff] " CHOICE

case "$CHOICE" in
    y|Y)
        echo "Applying typos corrections..."
        typos --write-changes "${PATHS[@]}"
        ;;
    l|L)
        echo "Showing diff of proposed changes:"
        typos --diff "${PATHS[@]}"
        echo ""
        echo "To apply: typos --write-changes ${PATHS[*]}"
        ;;
    *)
        echo "No changes applied."
        ;;
esac
