# /sync-knowledge

Sync best practices from awesome-claude-code repository to local knowledge base.

## Overview

This command fetches and structures community best practices for use in gap analysis.

## Execution Steps

### Step 1: Check Current State

```
Read knowledge/catalog.json if exists
- If exists: check last_synced date, prepare for diff update
- If not exists: full initial sync
```

### Step 2: Fetch awesome-claude-code

Use WebFetch or Explore agent to analyze:
- https://github.com/hesreallyhim/awesome-claude-code

Extract the following categories:

#### 2.1 Slash Commands
Look for patterns like:
- `/commit` - Git commit automation
- `/tdd` - Test-driven development
- `/create-pr` - PR creation workflow
- `/context-prime` - Context loading

For each command, extract:
- Name
- Description
- Source URL
- Use case (when to use)
- Example usage

#### 2.2 CLAUDE.md Patterns
Look for:
- Language-specific templates (Python, TypeScript, Go, etc.)
- Domain-specific patterns (blockchain, messaging, etc.)
- Project scaffolding patterns

For each pattern, extract:
- Category (language/domain)
- Key rules
- Source URL

#### 2.3 Workflows
Look for:
- Ralph Wiggum technique (autonomous iteration)
- AB Method (spec-driven)
- TDD workflows
- Context engineering

For each workflow, extract:
- Name
- Description
- When to use
- Key steps

#### 2.4 Agent Skills
Look for:
- Superpowers collection
- Context Engineering Kit
- Custom agent patterns

### Step 3: Structure and Save

Save extracted data to:

```
knowledge/
├── catalog.json           # Index of all resources
├── slash_commands/
│   ├── commit.json
│   ├── tdd.json
│   └── ...
├── claude_md_patterns/
│   ├── python.json
│   ├── typescript.json
│   └── ...
├── workflows/
│   ├── ralph_wiggum.json
│   ├── ab_method.json
│   └── ...
└── skills/
    ├── superpowers.json
    └── context_kit.json
```

### Step 4: Update Catalog

Update `knowledge/catalog.json`:

```json
{
  "version": "1.0.0",
  "last_synced": "2026-01-15T14:30:00",
  "source": "https://github.com/hesreallyhim/awesome-claude-code",
  "source_commit": "abc123...",
  "categories": {
    "slash_commands": ["commit", "tdd", "create-pr", ...],
    "claude_md_patterns": ["python", "typescript", ...],
    "workflows": ["ralph_wiggum", "ab_method", ...],
    "skills": ["superpowers", "context_kit", ...]
  },
  "stats": {
    "total_resources": 42,
    "slash_commands": 15,
    "claude_md_patterns": 10,
    "workflows": 8,
    "skills": 9
  }
}
```

## Output

After sync, display:
- Number of resources synced
- New resources (if diff update)
- Categories breakdown

## Usage

```
/sync-knowledge          # Full sync or diff update
/sync-knowledge --force  # Force full re-sync
```

## Notes

- Initial sync may take a few minutes (full exploration)
- Subsequent syncs only fetch diffs (faster)
- All data stored locally in knowledge/ directory
