# /gap-report

Generate gap analysis report comparing your patterns with best practices.

## Overview

This command generates a detailed report without applying any changes.
Useful for reviewing recommendations before committing to changes.

## Execution Steps

### Step 1: Validate Prerequisites

```
Check knowledge/catalog.json:
- If missing: "Run /sync-knowledge first"
- If outdated (>30 days): Warn user
```

### Step 2: Collect Session Data

Same as /optimize-me Step 2:
- Collect recent sessions
- Extract patterns

### Step 3: Generate Analysis

Create comprehensive report with:

#### Section 1: Your Usage Summary
```markdown
## Your Usage Summary (Last 7 Days)

### Sessions
- Total: 26 sessions
- Projects: DAIOps (12), HWP_Embedding (8), Other (6)

### Tool Usage
| Tool | Count | % |
|------|-------|---|
| Read | 245 | 35% |
| Grep | 120 | 17% |
| Edit | 98 | 14% |
| Bash | 85 | 12% |
| Task | 52 | 7% |

### Common Sequences
1. Read -> Grep -> Read -> Edit (exploration -> modification)
2. Bash -> Read -> Bash (build -> check -> retry)
3. Task -> Read -> Edit (delegate -> verify -> apply)
```

#### Section 2: Best Practices Available
```markdown
## Available Best Practices

### Slash Commands (15 available)
- /commit - Git commit automation
- /tdd - Test-driven development
- /create-pr - PR workflow
- /context-prime - Context loading
- ...

### CLAUDE.md Patterns (10 available)
- Python project template
- TypeScript project template
- ...

### Workflows (8 available)
- Ralph Wiggum technique
- AB Method
- ...
```

#### Section 3: Gap Analysis
```markdown
## Gap Analysis

### Identified Opportunities

| Gap | Your Current | Best Practice | Impact |
|-----|--------------|---------------|--------|
| Git Commits | Manual (avg 15/week) | /commit automation | High |
| Context Loading | Ad-hoc file reads | /context-prime | Medium |
| TDD | Inconsistent | /tdd workflow | Medium |
| PR Creation | Manual gh commands | /create-pr | Low |

### Detailed Recommendations

#### 1. Git Commit Automation (Priority: P1)

**Current Behavior:**
- You run `git commit` manually ~15 times per week
- Commit messages vary in format

**Recommended:**
- Add `/commit` command from awesome-claude-code
- Enforces conventional commit format
- Saves ~2 min per commit = 30 min/week

**Source:** [awesome-claude-code/slash-commands/commit](https://...)

---

#### 2. Context Loading (Priority: P2)
...
```

#### Section 4: Action Items
```markdown
## Action Items

### Quick Wins (< 5 min each)
- [ ] Add /commit command
- [ ] Add CLAUDE.md Git section

### Medium Effort (15-30 min)
- [ ] Adopt /tdd workflow
- [ ] Set up /context-prime

### Exploration (try when ready)
- [ ] Ralph Wiggum technique for autonomous tasks
```

### Step 4: Save Report

Save to: `data/reports/YYYY-MM-DD_gap_report.md`

### Step 5: Display Summary

Show condensed version in terminal:
```
Gap Report Generated!

Found 4 optimization opportunities:
- P1: Git commit automation (High impact)
- P2: Context loading (Medium impact)
- P2: TDD workflow (Medium impact)
- P3: PR automation (Low impact)

Full report: data/reports/2026-01-15_gap_report.md

Run /optimize-me to apply selected recommendations.
```

## Output Files

- `data/reports/YYYY-MM-DD_gap_report.md` - Full report
- `data/analysis/YYYY-MM-DD_session_summary.json` - Session data

## Usage

```
/gap-report                # Generate report
/gap-report --detailed     # Include all available best practices
/gap-report --json         # Output as JSON (for automation)
```
