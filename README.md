# Typos Skill - Conservative Spell Check with Structured Review

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://clawhub.com)

A portable Skill for agent-assisted typo review. It uses the `typos` CLI to
detect spelling issues, applies conservative built-in triage, exports them into
a review file, and applies only the fixes that were explicitly approved by an
LLM or a human reviewer.

This Skill is commonly used with Claude Code and Codex, but the workflow is
generic and can be adapted to other agent or review-driven environments.

## ✨ Features

- Automatic spell checking powered by the `typos` CLI
- Review-first workflow using a structured `review.jsonl` file
- Conservative built-in false-positive buckets for technical contexts
- Per-hit `reason`, `bucket`, and `preferred_action` metadata
- Safe rename suggestions for short internal variables
- `.typos.toml` suggestions for repeated false positives before source edits
- Approved-only apply flow instead of blind bulk replacement
- Batch processing for multiple files and directories

## 🚀 Quick Start

### Prerequisites

Install the required tools:

```bash
cargo install typos-cli
python3 --version
```

### Run Directly from This Repository

If you want to use the script directly without installing it as a Skill:

```bash
git clone https://github.com/luojiyin1987/typos-skill.git
cd typos-skill
chmod +x typos-skill.sh
chmod +x scripts/smoke-typos-skill.sh
```

Then run a basic review export:

```bash
./typos-skill.sh --export-review review.jsonl README.md
```

### Install in Claude Code

Copy this repository into your Claude skills directory:

```bash
mkdir -p ~/.claude/skills
cp -r /path/to/typos-skill ~/.claude/skills/typos
chmod +x ~/.claude/skills/typos/typos-skill.sh
chmod +x ~/.claude/skills/typos/scripts/smoke-typos-skill.sh
```

Start a new Claude Code session in the target repository, then invoke the skill
explicitly:

```text
Use the typos skill to scan this repo, export review.jsonl, and apply only approved fixes.
```

### Install in Codex

Recommended method, from a Codex session:

```text
Use $skill-installer to install the skill from https://github.com/luojiyin1987/typos-skill with path . and name typos.
```

If your environment does not expose `$skill-installer`, install manually:

```bash
SKILLS_DIR="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$SKILLS_DIR"
cp -r /path/to/typos-skill "$SKILLS_DIR/typos"
chmod +x "$SKILLS_DIR/typos/typos-skill.sh"
chmod +x "$SKILLS_DIR/typos/scripts/smoke-typos-skill.sh"
```

After installation, start a new Codex session in the target repository and use:

```text
Use $typos to scan this repo, export review.jsonl, then apply approved corrections.
```

## 📖 How It Works

The core workflow is always the same:

1. Export suggestions:

   ```bash
   ./typos-skill.sh --export-review review.jsonl [path...]
   ```

2. Review each JSON line in `review.jsonl`:
   - start from `bucket`, `suggested_status`, `preferred_action`, and `reason`
   - mark accepted items as `ACCEPT` or `ACCEPT CORRECT`
   - mark false positives as `FALSE POSITIVE`
   - use `CUSTOM` and set `correction` when you want your own replacement
   - if `rename_candidate` exists, prefer a manual symbol rename over typo fix
   - prefer `.typos.toml` suggestions when the same false positive repeats

3. Apply approved changes:

   ```bash
   ./typos-skill.sh --apply-review review.jsonl
   ```

This repository does not automatically call an LLM. The Skill produces a
reviewable file so Claude Code, Codex, another agent, or a human can make the
final decision before edits are applied. The export step already applies
conservative defaults so the reviewer is not starting from a blank slate.

## 🤖 Using with Claude Code and Codex

### Claude Code Prompts

```text
Use the typos skill to scan this repository and summarize the spelling issues before changing anything.
```

```text
Use the typos skill to run --export-review review.jsonl on docs/ and README.md, mark each finding as ACCEPT / FALSE POSITIVE / CUSTOM, then apply only approved fixes.
```

### Codex Prompts

```text
Use $typos to scan this repository and summarize the spelling issues before changing anything.
```

```text
Use $typos to run --export-review review.jsonl on src/ and docs/, review each finding, then apply only ACCEPT and CUSTOM fixes.
```

```text
Use $typos to check README.md and docs/, mark false positives, and show me the diff before applying changes.
```

```text
Use $typos to run --apply-all on docs/ only. Avoid touching code files.
```

## 🧰 CLI Reference

### Basic Usage

```bash
# Check current directory
./typos-skill.sh

# Check specific files or directories
./typos-skill.sh src/ tests/ README.md

# Export review for agent or LLM processing
./typos-skill.sh --export-review review.jsonl src/
```

### Commands

```bash
# Preview all proposed changes without applying them
./typos-skill.sh --diff [path...]

# Apply only approved changes from a review file
./typos-skill.sh --apply-review review.jsonl

# Apply all suggestions without review
./typos-skill.sh --apply-all [path...]
```

## 📋 Review File Format

The review file (`review.jsonl`) contains one JSON object per line:

```json
{
  "path": "relative/path/to/file",
  "line_num": 42,
  "byte_offset": 123,
  "occurrence_index": 1,
  "typo": "<detected-typo>",
  "corrections": ["<suggested-correction>"],
  "status": "PENDING",
  "correction": "",
  "reason": "<why this should or should not be changed>",
  "bucket": "candidate.source_fix",
  "suggested_status": "ACCEPT CORRECT",
  "preferred_action": "REVIEW_SOURCE",
  "rename_candidate": "",
  "line_text": "<source line>",
  "toml_section": "",
  "toml_snippet": ""
}
```

### Status Values

| Status | Meaning |
| --- | --- |
| `PENDING` | Initial exported state. Review required before apply. |
| `ACCEPT` | Apply the suggested correction. |
| `ACCEPT CORRECT` | Apply the suggested correction. |
| `FALSE POSITIVE` | Skip this item. |
| `FALSE POSITIVE?` | Skip this item. |
| `SKIP` | Skip this item. |
| `REJECT` | Skip this item. |
| `CUSTOM` | Apply the value in `correction`. |

Important rules:

- `PENDING` cannot be applied directly. Change each item to a final review
  status before running `--apply-review`.
- Exported triage defaults:
  - `false_positive.*`: defaults to `FALSE POSITIVE`
  - `manual_review.*`: do not auto-fix; confirm manually
  - `candidate.source_fix`: likely safe, but still requires review
- `rename_candidate` means "do not spell-correct this token"; prefer a semantic
  symbol rename such as `ot -> optionTexts`.
- Do not modify `byte_offset`, `occurrence_index`, or `line_num` unless you
  understand how locator matching works.
- `CUSTOM` requires a non-empty `correction`.
- If files changed after export, re-run `--export-review` before applying.

Built-in conservative rules:

- Hits inside hexadecimal strings, URLs, query parameters, CSS classes, JSON
  keys, and DOM selectors default to `FALSE POSITIVE`.
- Very short tokens such as `ot`, `ba`, and `pn` default to manual review and
  are not auto-fixed.
- Short internal variable names can emit `rename_candidate` advice when the
  source line suggests a safer semantic rename.
- Hits in snapshots, fixtures, and mocks default to manual review and prefer
  `.typos.toml` exclusion advice when they repeat.
- Language-aware keyword detection: based on file extension, tokens matching
  keywords, built-in functions, and common idioms of the detected programming
  language (Go, Python, JavaScript/TypeScript, Rust, Shell, C/C++, Java, Ruby,
  PHP, Swift, Kotlin, Scala, C#, Lua, R, SQL, and more) are automatically
  classified as `FALSE POSITIVE`.

## ⚙️ Configuration

Create a `.typos.toml` file in your project root to customize spell checking:

```toml
[files]
extend-exclude = [
  "*.min.js",
  "vendor/*",
  "node_modules/*"
]
```

You can also add project-specific words:

```toml
[default.extend-words]
npm = "npm"
github = "github"
api = "api"
cli = "cli"
```

For repeated false positives, prefer updating `.typos.toml` before editing
source one by one. Typical suggestions emitted by this skill include:

```toml
[default.extend-words]
"pn" = "pn"
```

```toml
[files]
extend-exclude = [
  "__snapshots__/**"
]
```

## 🛠 Development

### Project Structure

```text
typos-skill/
├── SKILL.md                     # Skill instructions for the agent
├── skill.json                   # Skill metadata
├── typos-skill.sh               # Main entry point
├── scripts/
│   ├── export-review.py         # Conservative triage + review export
│   ├── apply-review.py          # Applies approved fixes from review.jsonl
│   └── smoke-typos-skill.sh     # Minimal smoke test
├── agents/
│   └── openai.yaml              # Agent UI metadata
└── .typos.toml                  # Default repository typos configuration
```

### Smoke Test

```bash
./scripts/smoke-typos-skill.sh
```

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Run the smoke test after your changes.
4. Update documentation if behavior or workflow changed.
5. Open a pull request with a clear summary.

## 📞 Support

- Issues: [GitHub Issues](https://github.com/luojiyin1987/typos-skill/issues)
- Discussions: [GitHub Discussions](https://github.com/luojiyin1987/typos-skill/discussions)

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
