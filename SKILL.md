---
name: typos
description: Run typos CLI on files and produce LLM-reviewable spelling fixes with optional diff/apply.
---

# Typos Spell Check with LLM Review

Use this skill when the user wants to scan files for spelling errors with the
`typos` CLI and confirm corrections via LLM before applying changes.

## Workflow

1. Run `./typos-skill.sh [path...]` to generate review output.
2. Read file context at the reported path and line; classify each item as
   accept, false positive, or custom correction.
3. Re-run with `--diff` to preview or `--apply` to apply after confirmation.

## Notes

- Requires the `typos` CLI (`cargo install typos-cli`).
- Script: `typos-skill.sh`
- Smoke test: `scripts/smoke-typos-skill.sh`
