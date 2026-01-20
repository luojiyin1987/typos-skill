# Typos Skill

A spell-checking skill that combines the [`typos`](https://github.com/crate-ci/typos) CLI tool with LLM confirmation for intelligent spelling correction.

## Features

- 🔍 Fast spell checking using `typos` CLI
- 🤖 LLM-assisted review to avoid false positives
- 📝 JSON output for easy integration
- 🛡️ Safe: reviews changes before applying

## Installation

1. Install `typos` CLI:
   ```bash
   cargo install typos-cli
   ```

2. Make the script executable:
   ```bash
   chmod +x typos-skill.sh
   ```

## Usage

```bash
./typos-skill.sh [path...]
```

If no path is provided, checks the current directory.

## Example Output

```
🔍 Running typos spell check on: .
======================================

📝 Found spelling errors. Preparing for LLM review...

- **File**: `src/main.js` (line 42)
  - **Error**: `receive`
  - **Suggestions`: ["receive"]
```

## Workflow

1. Run `typos` with JSON output format
2. Parse errors and display them
3. LLM reviews context and confirms/rejects each correction
4. Apply approved corrections
