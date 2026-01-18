# /optimize-me

One-click optimization: analyze your usage patterns and get personalized suggestions.

## Overview

This is the main command that runs the full optimization pipeline:
1. Collect and compress your sessions (V2: Smart Compression)
2. Extract patterns automatically
3. Classify and prioritize suggestions
4. Generate and apply suggestions interactively

## Usage

```bash
/optimize-me                    # V2 파이프라인 (기본)
/optimize-me --v2               # V2 명시적 실행
/optimize-me --dry-run          # 미리보기만 (적용 안 함)
/optimize-me --days 14          # 분석 기간 변경 (기본: 7일)
/optimize-me --limit 200        # 압축 크기 제한 (기본: 100KB)
```

---

## V2 Pipeline (Smart Compression)

### Step 1: Session Collection & Compression

```python
# scripts/optimizer.py --v2 실행
python3 scripts/optimizer.py --v2
```

**동작**:
- `~/.claude/projects/`에서 최근 세션 수집
- 스마트 압축 (99% 압축률)
- 100KB 리미트 기반 동적 수집 (최신 우선)

**출력 예시**:
```
[Step 1] Collecting & Compressing Sessions...
  Collected: 9 sessions (98.9KB)
```

### Step 2: Pattern Extraction

자동으로 3가지 패턴 추출:

| 패턴 유형 | 설명 | 예시 |
|-----------|------|------|
| **Tool Sequences** | 도구 호출 순서 (3-gram) | `Read → Edit → Bash` |
| **Prompt Templates** | 반복되는 요청 패턴 | `~해줘`, `커밋해줘` |
| **Behavioral Rules** | 행동 규칙 | 한글 선호, 짧은 세션 |

### Step 3: Classification

패턴을 4가지 타입으로 자동 분류:

| 패턴 | 분류 | 제안 |
|------|------|------|
| 도구 시퀀스 반복 | **Skill** | `read-edit-bash.md` |
| 프롬프트 템플릿 | **Slash Command** | `/commit` |
| 복잡한 멀티스텝 | **Agent** | `code-reviewer` |
| 행동 규칙 | **CLAUDE.md Rule** | `Output language: Korean` |

### Step 4: Proposal Generation

우선순위별 제안 생성:

```markdown
## Priority 1 (High Impact, Easy)
- [ ] 📋 Output language: Korean (CLAUDE.md rule)
- [ ] 📋 Prefer short sessions (CLAUDE.md rule)

## Priority 2 (High Impact, Medium Effort)
- [ ] 🔧 bash-bash-bash.md (skill) - Git 작업 자동화
- [ ] ⚡ /commit (slash command)

## Priority 3 (Nice to Have)
- [ ] 🔧 read-edit-bash.md (skill)
...
```

### Step 5: Interactive Approval

AskUserQuestion으로 적용할 제안 선택:

```
Which optimizations would you like to apply?

[x] Output language: Korean (CLAUDE.md)
[x] /commit command
[ ] bash-bash-bash.md skill
```

### Step 6: Apply Changes

선택된 제안 적용:
1. CLAUDE.md 규칙 → `~/.claude/CLAUDE.md`에 추가
2. Slash Commands → `~/.claude/commands/`에 생성
3. Skills → `.claude/skills/`에 생성

**반드시 diff 미리보기 후 사용자 승인 필요**

---

## V1 Pipeline (Legacy)

기존 방식 (LLM 기반 분석):

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
