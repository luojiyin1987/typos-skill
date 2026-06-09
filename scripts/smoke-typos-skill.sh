#!/bin/bash
# Smoke test for typos-skill.sh

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/smoke-typos-skill.sh

Runs a minimal smoke test for typos-skill.sh. This checks the help output
and, when typos is installed, verifies review export metadata on a temporary
sample plus runs a read-only scan on the repo root.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SKILL="$ROOT_DIR/typos-skill.sh"

if [[ ! -x "$SKILL" ]]; then
    echo "Error: typos-skill.sh is not executable. Run: chmod +x typos-skill.sh" >&2
    exit 1
fi

"$SKILL" --help >/dev/null

if ! command -v typos >/dev/null 2>&1; then
    echo "SKIP: typos CLI not found; install with: cargo install typos-cli" >&2
    exit 0
fi

TMP_DIR=$(mktemp -d)
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

cat > "$TMP_DIR/sample.txt" <<'EOF'
const ot = optionTexts
thsi pn pn
EOF

"$SKILL" --export-review "$TMP_DIR/review.jsonl" "$TMP_DIR/sample.txt" >/dev/null

python3 - "$TMP_DIR/review.jsonl" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    items = [json.loads(line) for line in handle if line.strip()]

assert items, "expected exported review items"
for item in items:
    for key in ("reason", "bucket", "suggested_status", "preferred_action"):
        assert item.get(key), f"missing {key}"

assert any(item.get("preferred_action") == "UPDATE_TYPOS_TOML" for item in items), (
    "expected at least one .typos.toml suggestion"
)
assert any(
    item.get("preferred_action") == "RENAME_SYMBOL"
    and item.get("rename_candidate") == "optionTexts"
    for item in items
), "expected rename candidate suggestion"
PY

mkdir -p "$TMP_DIR/docs"

cat > "$TMP_DIR/negative.js" <<'EOF'
if (ot == optionTexts) {}
obj.ot = optionTexts
EOF

cat > "$TMP_DIR/docs/mockup-guide.md" <<'EOF'
respones
EOF

cat > "$TMP_DIR/sample.go" <<'EOF'
package main

import "fmt"

func init() {
	err := fmt.Errorf("impl goroutine")
	_ = err
}
EOF

cat > "$TMP_DIR/negative.jsonl" <<EOF
{"type":"typo","path":"$TMP_DIR/negative.js","line_num":1,"byte_offset":4,"typo":"ot","corrections":["to"]}
{"type":"typo","path":"$TMP_DIR/negative.js","line_num":2,"byte_offset":4,"typo":"ot","corrections":["to"]}
{"type":"typo","path":"$TMP_DIR/docs/mockup-guide.md","line_num":1,"byte_offset":0,"typo":"respones","corrections":["response"]}
{"type":"typo","path":"$TMP_DIR/sample.go","line_num":5,"byte_offset":1,"typo":"err","corrections":["error"]}
{"type":"typo","path":"$TMP_DIR/sample.go","line_num":5,"byte_offset":14,"typo":"impl","corrections":["imple"]}
{"type":"typo","path":"$TMP_DIR/sample.go","line_num":5,"byte_offset":19,"typo":"goroutine","corrections":["go routine"]}
EOF

python3 "$ROOT_DIR/scripts/export-review.py" "$TMP_DIR/negative.jsonl" "$TMP_DIR/negative-review.jsonl" >/dev/null

python3 - "$TMP_DIR/negative-review.jsonl" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    items = [json.loads(line) for line in handle if line.strip()]

by_line = {item["line_num"]: item for item in items if item["path"].endswith("negative.js")}
doc_item = next(item for item in items if item["path"].endswith("mockup-guide.md"))

assert by_line[1]["preferred_action"] != "RENAME_SYMBOL", "comparison should not become rename advice"
assert by_line[2]["bucket"] != "false_positive.css_class", "object property should not become CSS class"
assert doc_item["bucket"] != "manual_review.test_artifact", "mockup docs should not be treated as test artifacts"

go_items = [item for item in items if item["path"].endswith("sample.go")]
assert len(go_items) == 3, f"expected 3 Go items, got {len(go_items)}"
for go_item in go_items:
    assert go_item["bucket"] == "false_positive.language_keyword", (
        f"Go keyword `{go_item['typo']}` should be language_keyword, got {go_item['bucket']}"
    )
PY

"$SKILL" "$ROOT_DIR" >/dev/null

echo "OK: typos-skill smoke test passed."
