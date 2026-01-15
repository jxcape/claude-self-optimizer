# /optimize-me

One-click optimization: analyze your usage patterns and get personalized suggestions.

## Overview

This is the main command that runs the full optimization pipeline:
1. Ensure knowledge base is synced
2. Collect and analyze your sessions
3. Compare your patterns with best practices (Gap Analysis)
4. Generate and apply suggestions interactively

## Execution Steps

### Step 1: Knowledge Base Check

```
Check if knowledge/catalog.json exists:
- YES: Check if older than 7 days -> suggest /sync-knowledge
- NO: Run /sync-knowledge first (required for gap analysis)
```

### Step 2: Session Collection

Collect recent sessions from:
- Primary: `~/Library/Application Support/Claude/local-agent-mode-sessions/`
- Fallback: `data/sessions/` (if already collected)

Parameters (from setup checkpoints):
- `analysis_days`: Number of days to analyze (default: 7)

Extract for each session:
- Project/domain
- User messages (first 5 as sample)
- Tool usage sequence
- Tool frequency counts

### Step 3: Pattern Analysis (LLM)

Analyze collected sessions to identify:

#### 3.1 Tool Usage Patterns
- Most used tools (Top 10)
- Common tool sequences (e.g., Read -> Grep -> Edit)
- Project-specific tool preferences

#### 3.2 Workflow Patterns
- Planning style (detailed vs. quick)
- Verification habits (test after change?)
- Iteration patterns (retry on failure?)

#### 3.3 Communication Style
- Question style (brief vs. detailed)
- Feedback patterns (positive/negative/neutral)
- Preference for code vs. explanation

### Step 4: Gap Analysis (LLM)

Compare user patterns with knowledge base:

For each category in `focus_areas` (from setup):

#### 4.1 Slash Commands Gap
```
Your Pattern: Manual git commits (15/week)
Best Practice: /commit command exists
Recommendation: Add /commit to automate
Estimated Benefit: 50% time savings
```

#### 4.2 CLAUDE.md Gap
```
Your Pattern: No explicit Git workflow rules
Best Practice: Python projects often have Git sections
Recommendation: Add Git workflow section
```

#### 4.3 Workflow Gap
```
Your Pattern: Ad-hoc TDD attempts
Best Practice: Structured /tdd workflow
Recommendation: Adopt TDD workflow pattern
```

### Step 5: Generate Proposals

Create prioritized list of suggestions:

```markdown
## Optimization Proposals (2026-01-15)

### Priority 1 (High Impact, Easy)
- [ ] Add /commit command (Source: awesome-claude-code)
- [ ] Add CLAUDE.md Git section

### Priority 2 (High Impact, Medium Effort)
- [ ] Adopt /tdd workflow
- [ ] Add /context-prime for complex tasks

### Priority 3 (Nice to Have)
- [ ] Try Ralph Wiggum technique for autonomous tasks
```

### Step 6: Interactive Approval

Use AskUserQuestion to present options:

```
Which optimizations would you like to apply?

[x] /commit command (automate git commits)
[ ] /tdd workflow (test-driven development)
[x] CLAUDE.md Git section (explicit rules)
[ ] /context-prime (context loading)
```

### Step 7: Apply Selected Changes

For approved items:

1. **Slash Commands**: Copy from knowledge/ to ~/.claude/commands/
2. **CLAUDE.md Rules**: Append to ~/.claude/CLAUDE.md (with backup)
3. **Workflows**: Create documentation in project

Always:
- Create backup before modifying
- Show diff of changes
- Confirm success

## Output

```
Optimization Complete!

Applied:
 /commit command -> ~/.claude/commands/commit.md
 CLAUDE.md Git section -> ~/.claude/CLAUDE.md (backup: CLAUDE.md.bak)

Skipped:
 /tdd workflow (user declined)
 /context-prime (user declined)

Next optimization: Run /optimize-me again in 7 days
```

## Configuration

Uses setup checkpoints:
- `analysis_days`: Session analysis period
- `auto_sync`: Auto-sync knowledge base
- `focus_areas`: Categories to analyze

## Usage

```
/optimize-me                    # Run full optimization
/optimize-me --dry-run          # Preview without applying
/optimize-me --report-only      # Same as /gap-report
```
