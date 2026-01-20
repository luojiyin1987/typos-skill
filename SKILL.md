---
name: typos
description: Run typos CLI on files and produce LLM-reviewable spelling fixes with optional diff/apply.
---

# Typos Spell Check with LLM Review

Use this skill when the user wants to scan files for spelling errors with the
`typos` CLI and confirm corrections via LLM before applying changes.

## Workflow

1. Run `./typos-skill.sh --export-review review.jsonl [path...]` to generate a
   review file plus a human-readable summary.
2. Read file context at the reported path and line; update each JSON line:
   - `status`: `ACCEPT CORRECT`, `FALSE POSITIVE`, or `CUSTOM`
   - `correction`: required when status is `CUSTOM`
3. Apply approved changes with `./typos-skill.sh --apply-review review.jsonl`.
4. Optional: use `--diff` to preview or `--apply-all` to skip review.

## Dependencies

- `typos` (`cargo install typos-cli`)
- `python3`

## Notes

- Script: `typos-skill.sh`
- Apply helper: `scripts/apply-review.py`
- Smoke test: `scripts/smoke-typos-skill.sh`
