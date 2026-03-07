# Typos Skill - AI-Powered Spell Check with LLM Review

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://clawhub.com)

A powerful spell-checking skill for OpenClaw that uses the `typos` CLI tool to detect spelling errors and provides LLM-assisted review before applying corrections.

## ✨ Features

- 🔍 **Automatic spell checking** using the `typos` CLI tool
- 🤖 **LLM-powered review** for intelligent correction approval
- 📝 **Interactive workflow** with human-in-the-loop validation
- 🔄 **Safe application** with preview and rollback options
- 📁 **Batch processing** for multiple files and directories
- ⚙️ **Customizable rules** via `.typos.toml` configuration

## 🚀 Quick Start

### Prerequisites

1. Install `typos` CLI:
   ```bash
   cargo install typos-cli
   # or using package manager
   # brew install typos-cli (macOS)
   # apt install typos (Debian/Ubuntu)
   ```

2. Install Python 3.8+ (required for review processing)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/luojiyin1987/typos-skill.git
   cd typos-skill
   ```

2. Make the script executable:
   ```bash
   chmod +x typos-skill.sh
   ```

## 📖 Usage

### Basic Spell Check with LLM Review

```bash
# Check current directory
./typos-skill.sh

# Check specific files or directories
./typos-skill.sh src/ tests/ README.md

# Export review for LLM processing
./typos-skill.sh --export-review review.jsonl src/
```

### Review and Apply Corrections

1. **Export review file**:
   ```bash
   ./typos-skill.sh --export-review review.jsonl [path...]
   ```

2. **Review with LLM**:
   - Open `review.jsonl` and examine each suggested correction
   - Update `status` field:
     - `ACCEPT` or `ACCEPT CORRECT` - Apply the suggested correction
     - `FALSE POSITIVE` - Skip this suggestion
     - `CUSTOM` - Provide custom correction in `correction` field
   - Do not modify `byte_offset`, `occurrence_index`, or `line_num` unless you know what you're doing

3. **Apply approved changes**:
   ```bash
   ./typos-skill.sh --apply-review review.jsonl
   ```

### Advanced Options

```bash
# Preview changes without applying
./typos-skill.sh --diff

# Apply all suggestions without review (use with caution!)
./typos-skill.sh --apply-all

# Check specific file types
./typos-skill.sh --export-review review.jsonl "*.md" "*.txt"
```

## 📋 Review File Format

The review file (`review.jsonl`) contains one JSON object per line with the following structure:

```json
{
  "path": "relative/path/to/file",
  "line_num": 42,
  "byte_offset": 123,
  "occurrence_index": 0,
  "typo": "recieve",
  "corrections": ["receive"],
  "status": "PENDING",
  "correction": ""
}
```

### Status Values

| Status | Description | Action |
|--------|-------------|--------|
| `ACCEPT` or `ACCEPT CORRECT` | Apply the suggested correction | ✅ Apply |
| `FALSE POSITIVE` | Mark as false positive | ❌ Skip |
| `FALSE POSITIVE?` | Uncertain false positive | ⚠️ Skip with note |
| `SKIP` or `REJECT` | Skip this correction | ❌ Skip |
| `CUSTOM` | Apply custom correction | ✏️ Use `correction` field |

## ⚙️ Configuration

### `.typos.toml` Configuration

Create a `.typos.toml` file in your project root to customize spell checking:

```toml
[default]
extend-ignore-files = [
  "*.min.js",
  "vendor/*",
  "node_modules/*"
]

[files]
# File-specific configurations
```

### Common Typos Rules

You can add custom dictionaries or ignore patterns:

```toml
[default]
extend-ignore-words = [
  "npm",
  "github",
  "api",
  "cli"
]
```

## 🔧 Integration with OpenClaw

### As an OpenClaw Skill

1. Copy the skill to your OpenClaw skills directory:
   ```bash
   cp -r typos-skill ~/.openclaw/workspace/agent/skills/
   ```

2. The skill will be automatically available in OpenClaw

### Using with AI Assistants

```bash
# Ask your AI assistant to check spelling
"Check spelling in the documentation directory"

# The assistant will run:
./typos-skill.sh --export-review review.jsonl docs/

# Then review and apply corrections
```

## 🛠️ Development

### Project Structure

```
typos-skill/
├── SKILL.md              # Skill documentation
├── skill.json           # Skill metadata
├── typos-skill.sh       # Main script
├── scripts/
│   ├── apply-review.py  # Review application logic
│   └── smoke-typos-skill.sh  # Test script
├── agents/              # Agent configurations
└── .typos.toml         # Default typos configuration
```

### Running Tests

```bash
# Run smoke test
./scripts/smoke-typos-skill.sh

# Test with sample files
./typos-skill.sh --diff test/
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [typos](https://github.com/crate-ci/typos) - The fantastic spell checker
- [OpenClaw](https://github.com/openclaw/openclaw) - The AI agent platform
- All contributors who help improve this skill

## 📞 Support

- Issues: [GitHub Issues](https://github.com/luojiyin1987/typos-skill/issues)
- Discussions: [GitHub Discussions](https://github.com/luojiyin1987/typos-skill/discussions)

---

**Made with ❤️ for the OpenClaw community**