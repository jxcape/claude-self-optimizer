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
- Primary: `~/.claude/projects/` (CLI sessions, main source)
- Secondary: `~/Library/Application Support/Claude/local-agent-mode-sessions/` (VM sessions)
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

### Step 3.5: Pattern Summary & Focus Selection (Onboarding)

**데이터 기반 온보딩**: 분석 결과를 먼저 보여주고 최적화 영역 선택

```markdown
## 📊 Your Usage Patterns (Last 7 days, 40 sessions)

### Tool Usage
| Tool | Count | Pattern |
|------|-------|---------|
| Edit | 892 | 코드 수정 중심 |
| Read | 756 | 탐색 빈번 |
| Bash | 423 | Git/빌드 작업 |
| TodoWrite | 312 | 작업 추적 활용 |

### Detected Patterns
- 🔄 **반복 패턴**: Read → Grep → Edit (탐색 후 수정)
- 📝 **Git 작업**: 주 15회+ 커밋 관련 작업
- 🧪 **테스트**: Bash로 테스트 실행 빈번

---
**어떤 영역을 최적화할까요?**
```

Use AskUserQuestion:
```
Based on your patterns, which areas should we focus on?

[ ] Slash Commands (Recommended) - /commit, /test 등 자동화
[ ] CLAUDE.md Rules - 프로젝트별 규칙 강화
[ ] Workflows - TDD, 탐색 패턴 개선
[ ] All of the above
```

선택된 영역만 Gap Analysis 진행 → 불필요한 제안 최소화

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

### Step 6.5: Preview Changes (REQUIRED)

**Before any file modification**, show the exact changes in diff format:

```markdown
## 📋 Change Preview

### 1. ~/.claude/CLAUDE.md (CLAUDE.md Rules)

\`\`\`diff
## Git Workflow  ← 추가될 섹션 시작
+
+ ### Commit Convention
+ - Use conventional commit format
+ - Always run tests before commit
+
\`\`\`

### 2. ~/.claude/commands/commit.md (New File)

\`\`\`markdown
# /commit
[Full content preview...]
\`\`\`

---
**적용하시겠습니까?** (y/n/수정요청)
```

**Critical Rules**:
- CLAUDE.md, PROGRESS.md, 기존 설정 파일 수정 시 **반드시 diff 표시**
- 사용자가 명시적으로 "적용해줘"/"ㅇㅇ" 하기 전까지 수정 금지
- 대용량 변경 시 요약 + 전체 diff 링크 제공

### Step 7: Apply Selected Changes

For approved items:

1. **Slash Commands**: Copy from knowledge/ to ~/.claude/commands/
2. **CLAUDE.md Rules**: Append to ~/.claude/CLAUDE.md (with backup)
3. **Workflows**: Create documentation in project

**Mandatory Checklist**:
- [ ] Create backup before modifying (filename.bak.{timestamp})
- [ ] Show diff preview (Step 6.5) and get explicit approval
- [ ] Apply changes
- [ ] Verify by reading modified file
- [ ] Confirm success to user

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
