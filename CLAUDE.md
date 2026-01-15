# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Claude Self-Optimizer**: A Claude Code plugin that analyzes your usage patterns and suggests personalized optimizations based on community best practices from awesome-claude-code.

Core Philosophy: **Zero External API** - Uses Claude Code subscription only (no separate API calls)

## Architecture (v3 - Plugin)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Plugin Architecture                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Commands]              [Knowledge Base]       [Scripts]       │
│  commands/               knowledge/             scripts/        │
│  ├─ optimize-me.md      ├─ catalog.json        ├─ optimizer.py │
│  ├─ sync-knowledge.md   ├─ slash_commands/     └─ sync_knowledge│
│  └─ gap-report.md       ├─ workflows/                           │
│                         └─ claude_md_patterns/                  │
│                                                                 │
│  [Data Flow]                                                    │
│  Sessions → Pattern Analysis → Gap Analysis → Suggestions       │
│                   ↑                  ↑                          │
│             LLM Analysis      Knowledge Base (110+ items)       │
│                               (from awesome-claude-code)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Files

| Path | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Plugin metadata, setup checkpoints |
| `commands/*.md` | Slash command definitions |
| `knowledge/catalog.json` | Index of 110+ best practices |
| `scripts/optimizer.py` | Core optimization logic |
| `scripts/sync_knowledge.py` | Knowledge base sync |

## Commands

### /optimize-me
Full optimization pipeline:
1. Check knowledge base (sync if needed)
2. Collect recent sessions from `audit.jsonl`
3. Analyze patterns (LLM)
4. Compare with best practices (Gap analysis)
5. Generate prioritized suggestions
6. Interactive approval via AskUserQuestion
7. Apply approved changes

### /sync-knowledge
Sync knowledge base from awesome-claude-code:
- Downloads THE_RESOURCES_TABLE.csv
- Parses 110+ resources
- Structures into categories (slash_commands, workflows, claude_md_patterns, etc.)
- Saves to knowledge/

### /gap-report
Generate analysis report without applying changes.

## Development

### Running Scripts

```bash
# Sync knowledge base
python3 scripts/sync_knowledge.py --force

# Run optimizer (dry-run)
python3 scripts/optimizer.py --dry-run

# Full run (generates prompt for LLM analysis)
python3 scripts/optimizer.py
```

### Testing Plugin Locally

```bash
claude --plugin-dir .
```

### Session Data Location

macOS: `~/Library/Application Support/Claude/local-agent-mode-sessions/`

Session format:
- `audit.jsonl` - Conversation logs (JSONL format)
- `local_*.json` - Session metadata

## Directory Structure

```
claude-self-optimizer/
├── .claude-plugin/
│   └── plugin.json          # Plugin config & setup checkpoints
├── commands/                 # Slash commands
│   ├── optimize-me.md
│   ├── sync-knowledge.md
│   └── gap-report.md
├── knowledge/                # Best practices database
│   ├── catalog.json         # Index of all resources
│   ├── slash_commands/      # 18 commands
│   ├── claude_md_patterns/  # 12 patterns
│   ├── workflows/           # 22 workflows
│   └── skills/              # 7 agent skills
├── scripts/                  # Python utilities
│   ├── optimizer.py         # Core optimization logic
│   └── sync_knowledge.py    # Knowledge base sync
├── data/                     # Runtime data (gitignored)
│   ├── sessions/
│   ├── reports/
│   └── proposals/
└── .claude/skills/          # Legacy skills (deprecated)
```

## Coding Guidelines

- **Zero External API**: Use Claude Code's built-in capabilities only
- **Privacy First**: All data stays local
- **Explicit Approval**: Never auto-apply changes
- **Backup Before Modify**: Always backup before editing CLAUDE.md

## Installation (for users)

```bash
# 1. Add marketplace
/plugin marketplace add YOUR_GITHUB/claude-self-optimizer

# 2. Install
/plugin install self-optimizer

# 3. Run
/optimize-me
```
