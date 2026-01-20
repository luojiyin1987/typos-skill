#!/bin/bash
# Smoke test for typos-skill.sh

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: scripts/smoke-typos-skill.sh

Runs a minimal smoke test for typos-skill.sh. This checks the help output
and, when typos is installed, runs a read-only scan on the repo root.
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

"$SKILL" "$ROOT_DIR" >/dev/null

echo "OK: typos-skill smoke test passed."
