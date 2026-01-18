# Agent Self-Optimization - No-API MVP

## Overview

Claude Code API 없이 Claude Code 내 에이전트만으로 구현하는 자기 최적화 시스템.

---

## Core Philosophy

**Zero External API**: Claude Code 구독형 플랜 활용만으로 구현.
- Claude API 호출 X
- Supabase API 직접 호출 X (MCP는 사용 가능)
- 별도 LLM 서비스 X

---

## Revised Architecture

### 1. Data Collection (Claude Code MCP)

```
[User Request]
   ↓
[Session Collector Agent]
   ├─ session_list() → 전체 세션
   ├─ session_read() → 세션 상세
   └─ write() → 로컬 JSON 저장
```

### 2. Analysis (Claude Code Agent)

```
[Local JSON Files]
   ↓
[Analysis Agent]
   ├─ 사용자 성향 분석 (Claude 자체)
   ├─ 도메인/문제 파악 (Claude 자체)
   ├─ 패턴 추출 (Claude 자체)
   └─ write() → 분석 결과 저장
```

### 3. Proposal Generation (Claude Code Agent)

```
[Analysis Results]
   ↓
[Proposal Agent]
   ├─ CLAUDE.md 업데이트 제안
   ├─ 신규 Skill 제안
   └─ write() → Obsidian 노트 생성
```

### 4. Feedback Loop (User + Claude Code)

```
[Obsidian Feedback Note]
   ↓
[User Review]
   ├─ 승인/거부
   ├─ 만족도 점수
   └─ write() → 피드백 저장
   ↓
[Update Agent]
   ├─ CLAUDE.md 자동 수정
   ├─ Skill 생성
   └─ git commit (선택)
```

---

## Data Flow

```
1. Collection
   session_list → session_read → write(json)

2. Analysis
   read(json) → Claude 분석 → write(analysis)

3. Proposal
   read(analysis) → Claude 제안 → write(proposal)

4. Feedback
   read(proposal) → User 피드백 → write(feedback)

5. Update
   read(feedback) → Claude 업데이트 → write(CLAUDE.md)
```

---

## Storage Structure

```
agent_self_optimization/
├── data/
│   ├── sessions/
│   │   ├── 2026-01-13_session_1.json
│   │   ├── 2026-01-13_session_2.json
│   │   └── ...
│   ├── analysis/
│   │   ├── 2026-01-13_weekly_analysis.md
│   │   └── ...
│   ├── proposals/
│   │   ├── 2026-01-13_claude_md_update.md
│   │   └── ...
│   └── feedback/
│       ├── 2026-01-13_feedback_1.md
│       └── ...
├── .claude/
│   └── skills/
│       ├── analyze_sessions.md
│       ├── generate_proposals.md
│       └── apply_updates.md
└── logs/
    └── collection.log
```

---

## Skills Required

### 1. /collect-sessions

```markdown
---
name: collect-sessions
description: 최근 세션 로그를 수집하여 로컬에 저장
---

{{#task}}
1. session_list()로 최근 7일 세션 목록 가져오기
2. session_read()로 각 세션 상세 다운로드
3. data/sessions/에 YYYY-MM-DD_session_{id}.json 형식으로 저장
4. 수집된 세션 수 리포트
{{/task}}
```

### 2. /analyze-sessions

```markdown
---
name: analyze-sessions
description: 수집된 세션을 분석하여 사용자 성향, 도메인, 패턴 추출
---

{{#task}}
1. data/sessions/에서 최신 세션 JSON 파일들을 읽기
2. 다음을 분석:
   - 사용자 성향 (질문 스타일, 선호도)
   - 도메인/문제 (현재 작업, 전문 분야)
   - 패턴 (도구 사용, 워크플로우)
   - 성공/실패 (기술적 + 과정적)
3. data/analysis/에 YYYY-MM-DD_weekly_analysis.md 저장
{{/task}}
```

### 3. /generate-proposals

```markdown
---
name: generate-proposals
description: 분석 결과를 바탕으로 CLAUDE.md/Skill 업데이트 제안 생성
---

{{#task}}
1. data/analysis/에서 최신 분석 읽기
2. 다음 제안 생성:
   - CLAUDE.md 업데이트 제안
   - 신규 Skill 제안
   - 워크플로우 최적화 제안
3. data/proposals/에 YYYY-MM-DD_claude_md_update.md 저장
4. Obsidian에 피드백 요청 노트 생성
{{/task}}
```

### 4. /apply-feedback

```markdown
---
name: apply-feedback
description: 사용자 피드백을 적용하여 CLAUDE.md/Skill 업데이트
---

{{#task}}
1. data/feedback/에서 최신 피드백 읽기
2. 승인된 제안 확인:
   - CLAUDE.md 업데이트가 있으면 .claude/CLAUDE.md 수정
   - Skill 생성이 있으면 .claude/skills/에 파일 생성
3. 변경사항 요약
4. (선택) git commit
{{/task}}
```

---

## User Workflow

### Weekly Process

```
1. 월요일: /collect-sessions
   → 지난 주 세션 수집

2. 화요일: /analyze-sessions
   → 분석 리포트 생성

3. 수요일: /generate-proposals
   → 제안 생성 + Obsidian 노트

4. 목요일-토요일: User Review
   → Obsidian에서 피드백 작성

5. 일요일: /apply-feedback
   → 승인된 제안 적용
```

### On-Demand Process

```
[사용자 필요할 때마다]
1. /collect-sessions (최신 세션만)
2. /analyze-sessions (특정 세션만)
3. /generate-proposals (즉시 제안)
4. /apply-feedback (즉시 적용)
```

---

## Integration with Claude Code

### Session Start Protocol

`.claude/CLAUDE.md`:
```markdown
## Session Start

Every session start:
1. Check if there are pending proposals in data/proposals/
2. If yes, summarize and ask for feedback
3. Check if there are pending feedback in data/feedback/
4. If yes, apply with user confirmation
```

### MCP Integration (Optional)

```
[data/sessions/]
   ↓
[MCP Server - Read Only]
   → Obsidian 검색 가능
   → 다른 도구에서 접근 가능
```

---

## Benefits of No-API Approach

| Aspect | API 방식 | No-API 방식 |
|--------|---------|-------------|
| **비용** | Claude API 추가 비용 | 이미 구독 중인 Claude Code만 사용 |
| **복잡도** | 외부 API 연동, 인증 관리 | Claude Code 내에서만 처리 |
| **보안** | API 키 관리 필요 | 추가 자격증명 불필요 |
| **속도** | API 호출 지연 | 로컬 처리 (빠름) |
| **유지보수** | API 버전 관리 필요 | Claude Code 업데이트만 따름 |

---

## Limitations & Mitigations

### Limitation 1: 수동 트리거

**문제**: cron 자동화 없음
**완화**:
- 매일 첫 세션에서 "최신 세션 수집할까?" 자동 물어보기
- CLAUDE.md에서 정기적 체크 규칙 추가

### Limitation 2: 대규모 세션 분석

**문제**: Claude Code 컨텍스트 제한
**완화**:
- 최근 10-20개 세션만 분석
- 주간 리포트 요약

### Limitation 3: 데이터베이스 기능 제한

**문제**: 로컬 JSON만으로는 복잡한 쿼리 어려움
**완화**:
- 간단한 파일 시스템 구조
- 필요 시 MCP로 Supabase 연동 (read-only)

---

## Success Metrics (No-API MVP)

| Metric | Target (1 Month) |
|--------|-----------------|
| 세션 수집 정확도 | 100% |
| 분석 품질 (주관적) | 사용자 만족도 >70% |
| 제안 승인율 | >50% |
| 자동 업데이트 빈도 | 주 1회 이상 |
| 사용자 편의성 | 수동 조작 <5분/주 |

---

## Next Steps

1. **Skills 구현** (Week 1)
   - /collect-sessions
   - /analyze-sessions
   - /generate-proposals
   - /apply-feedback

2. **데이터 파이프라인 구축** (Week 2)
   - 로컬 저장소 구조
   - 로깅 시스템

3. **CLAUDE.md 프로토콜** (Week 3)
   - 세션 시작 체크
   - 피드백 흐름

4. **테스트 & 고도화** (Week 4)
   - 사용성 테스트
   - 품질 개선

---

## Comparison: API vs No-API

### Full API Version (Original Plan)

```
[Claude Code] → [Supabase] → [Claude API] → [Analysis]
                                     ↓
                              [Additional Cost]
```

### No-API MVP

```
[Claude Code] → [Local Files] → [Claude Code Analysis]
                                     ↓
                                [Zero Cost]
```

---

## Conclusion

**No-API MVP**가 더 현실적이고 빠르다:
- 이미 구독 중인 Claude Code만 사용
- 추가 비용/복잡도 없음
- 로컬에서 빠르게 처리
- MVP로 충분히 가치 있음

→ API 버전은 MVP 검증 후 고도화 시 고려
