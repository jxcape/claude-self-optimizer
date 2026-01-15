# Claude Self-Optimizer

> Analyze your Claude Code usage patterns and get personalized optimization suggestions based on community best practices.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-v1.0.33+-blue.svg)](https://claude.ai/code)

## Overview

**Claude Self-Optimizer** is a Claude Code plugin that:

1. **Analyzes your usage patterns** - Collects and analyzes your Claude Code sessions
2. **Compares with best practices** - Uses 110+ resources from [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)
3. **Generates personalized suggestions** - Recommends slash commands, CLAUDE.md rules, and workflows that match your habits
4. **Applies improvements** - One-click application of approved suggestions

```
┌─────────────────────────────────────────────────────────────────┐
│  Your Sessions  →  Pattern Analysis  →  Gap Analysis  →  Apply  │
│                         ↑                    ↑                  │
│                    LLM Analysis    Knowledge Base (110+ items)  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Installation

```bash
# 1. Add marketplace (one-time)
/plugin marketplace add YOUR_GITHUB/claude-self-optimizer

# 2. Install plugin
/plugin install self-optimizer
```

### Usage

```bash
# Run full optimization pipeline
/optimize-me

# Sync best practices from awesome-claude-code
/sync-knowledge

# Generate gap report only (no changes)
/gap-report
```

## Features

### /optimize-me

One-click optimization that:
- Collects your recent sessions (default: 7 days)
- Analyzes tool usage patterns and workflows
- Compares with community best practices
- Generates prioritized recommendations
- Interactively applies approved changes

```
Claude: Found 3 optimization opportunities:

[x] /commit command (automate git commits)
[ ] /tdd workflow (test-driven development)
[x] CLAUDE.md Git section (explicit rules)

Apply selected? (y/n)
```

### /sync-knowledge

Syncs the knowledge base from awesome-claude-code:
- 18 slash commands
- 12 CLAUDE.md patterns
- 22 workflows
- 7 agent skills
- and more...

First run: Full sync (~30 seconds)
Subsequent runs: Diff update only

### /gap-report

Generates detailed analysis without applying changes:
- Your usage summary
- Available best practices
- Gap analysis with priorities
- Concrete recommendations

## Configuration

During installation, you'll be asked:

| Setting | Options | Default |
|---------|---------|---------|
| Analysis Period | 7 / 14 / 30 days | 7 days |
| Auto Sync | Yes / No | Yes |
| Focus Areas | Slash Commands, CLAUDE.md, Workflows, Skills | All except Skills |

## Directory Structure

```
claude-self-optimizer/
├── .claude-plugin/
│   └── plugin.json          # Plugin metadata & setup checkpoints
├── commands/                 # Slash commands
│   ├── optimize-me.md
│   ├── sync-knowledge.md
│   └── gap-report.md
├── knowledge/                # Best practices database
│   ├── catalog.json         # Index of all resources
│   ├── slash_commands/
│   ├── claude_md_patterns/
│   ├── workflows/
│   └── skills/
├── scripts/                  # Python utilities
│   ├── optimizer.py         # Core optimization logic
│   └── sync_knowledge.py    # Knowledge base sync
└── data/                     # Runtime data (gitignored)
    ├── sessions/
    ├── reports/
    └── proposals/
```

## How It Works

### 1. Session Collection

Reads from `~/Library/Application Support/Claude/local-agent-mode-sessions/`:
- Parses `audit.jsonl` files (conversation logs)
- Extracts user messages, tool usage, sequences
- Filters by date range

### 2. Pattern Analysis

LLM analyzes your patterns:
- **Tool usage**: Which tools you use most
- **Sequences**: Common tool chains (Read → Grep → Edit)
- **Workflows**: Planning style, verification habits
- **Communication**: Question style, feedback patterns

### 3. Gap Analysis

Compares your patterns with knowledge base:
- Identifies missing best practices
- Calculates potential impact
- Prioritizes by effort vs benefit

### 4. Suggestions

Generates actionable recommendations:
- P1: High impact, easy to adopt
- P2: High impact, medium effort
- P3: Nice to have

### 5. Application

For approved items:
- Slash commands → `~/.claude/commands/`
- CLAUDE.md rules → `~/.claude/CLAUDE.md` (with backup)
- Workflows → Documentation

## Privacy

- **All data stays local** - No cloud uploads
- **Session data is read-only** - Original files are never modified
- **Explicit approval required** - Changes only applied when you approve

## Requirements

- Claude Code v1.0.33 or higher
- Python 3.8+ (for scripts)
- macOS (for session path; Linux support planned)

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) - Community best practices source
- Anthropic - Claude Code platform

---

Made with Claude Code
