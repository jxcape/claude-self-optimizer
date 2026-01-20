# /optimize-me 스펙

> 인터뷰 기반 스펙 (2026-01-20)

## 개요

- **목적**: 세션 분석을 통한 **깊은 수준**의 개인화 최적화
- **대상 사용자**: Claude Code 사용자 (나 자신)
- **핵심 가치**: 피상적 통계("Read 40%") 대신 **실질적 인사이트** 제공

---

## 핵심 원칙

### Zero External API
- Claude Code 구독만 사용 (별도 API 호출 X)
- 모든 데이터 로컬 처리

### LLM First Analysis
- Python은 **데이터 압축만** 수행
- 모든 분석/판단/제안은 **LLM이 직접** 수행
- 하드코딩된 분류 로직 없음

---

## 분석 수준 (핵심)

### 금지 - 피상적 분석
```
❌ "Read 40%, Edit 30% 사용"
❌ "세션 평균 15턴"
❌ "Python 파일 많이 다룸"
→ 어쩌라고?
```

### 필수 - 깊은 분석

| 영역 | 분석 내용 | 예시 |
|------|----------|------|
| **도메인 파악** | MLOps? 리서치? 웹개발? | "DAIOps는 LangGraph 기반 MLOps 파이프라인" |
| **개발 프랙티스** | TDD 쓰는지? Clean architecture? | "테스트 없이 구현 먼저 → TDD 권장" |
| **작업 패턴** | 세션 과부하? 모호한 입력? | "한 세션에 5개 이상 작업 → 분리 권장" |
| **LLM 활용** | 과의존? 체크 부족? | "빌드 안 돌리고 완료 선언 3회" |
| **피드백 방식** | 명확한 지시? 모호한 요청? | "'이거 해줘' 같은 모호한 입력 잦음" |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    /optimize-me Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [1. 세션 압축]        Python (compressor.py)               │
│      ↓                 - 최근 N일 세션 로드                  │
│      ↓                 - 도구별 압축 (Read: file.py)        │
│      ↓                 - 100KB 리미트 동적 수집              │
│                                                             │
│  [2. Knowledge Base]   Python (sync_knowledge.py)           │
│      ↓                 - awesome-claude-code 동기화         │
│      ↓                 - 베스트 프랙티스 요약 추출           │
│                                                             │
│  [3. LLM 분석]         Claude Code 직접 수행                │
│      ↓                 - 압축 세션 + KB 요약 읽기           │
│      ↓                 - 깊은 분석 (도메인, 프랙티스, 패턴)  │
│      ↓                 - 리포트 생성                        │
│                                                             │
│  [4. 제안 생성]        Claude Code 직접 수행                │
│      ↓                 - CLAUDE.md 규칙 제안                │
│      ↓                 - Skill/Slash 제안                   │
│      ↓                 - 우선순위 (P1/P2/P3)                │
│                                                             │
│  [5. 사용자 선택]      AskUserQuestion                      │
│      ↓                 - 제안 목록 표시                     │
│      ↓                 - 멀티셀렉트로 선택                  │
│                                                             │
│  [6. 적용]             Claude Code 직접 수행                │
│                        - 선택된 제안 CLAUDE.md에 추가       │
│                        - Skill 파일 생성                    │
│                        - diff 미리보기 필수                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 세부 설계

### 1. 세션 압축 (compressor.py)

**입력**: ~/.claude/projects/ 세션 파일들
**출력**: 압축된 텍스트 (100KB 이내)

```
# Session: 리팩토링 작업 (2026-01-20)
Project: DAIOps

---
U: node 빠진거 없나 확인해줘
C: Read: spec.md | Grep: "node" in src/
U: 괜찮으면 구현해줘
C: Edit: src/pipeline.py | Bash: pytest → ✓
---
```

**압축 규칙**:
- User 메시지: 원문 보존 (핵심 요청 파악 위해)
- Claude 도구: 도구명 + 핵심 param만
- Claude 텍스트: 도구 호출 있으면 생략

### 2. Knowledge Base (sync_knowledge.py)

**소스**: awesome-claude-code, 커스텀 베스트 프랙티스
**저장**: knowledge/catalog.json

**LLM에게 전달할 요약**:
```markdown
## 베스트 프랙티스 요약

### 개발 프랙티스
- TDD: 테스트 먼저 작성 후 구현
- Spec-first: 스펙 문서 먼저 읽고 구현
- Clean architecture: 의존성 역전, 레이어 분리

### 세션 관리
- 한 세션 한 작업 원칙
- 복잡한 작업은 새 세션에서

### 피드백 방식
- 구체적 지시: "X 파일의 Y 함수를 Z로 변경"
- 검증 요청: "빌드 돌려봐", "테스트 통과 확인"
```

### 3. LLM 분석 프롬프트

```markdown
# 세션 분석 요청

## 데이터
[압축된 세션 데이터]

## 베스트 프랙티스
[KB 요약]

## 분석 항목

1. **도메인 파악**
   - 어떤 프로젝트를 주로 다루는가?
   - 기술 스택은?

2. **개발 프랙티스 평가**
   - TDD 적용 여부 (테스트 먼저?)
   - Spec 참조 여부 (스펙 먼저 읽는가?)
   - 빌드/테스트 검증 여부

3. **작업 패턴 평가**
   - 한 세션에 몇 개 작업?
   - 모호한 요청 빈도?
   - 실수 패턴 (롤백, 삭제, "필요없었네")

4. **LLM 활용 방식**
   - 과의존 (체크 없이 완료 선언?)
   - 피드백 방식 (명확한 지시?)

## 출력 포맷
[아래 "출력 포맷" 섹션 참조]
```

### 4. 출력 포맷

```markdown
## 분석 결과

### 도메인
- **주요 프로젝트**: DAIOps (LangGraph MLOps), agent_self_optimization
- **기술 스택**: Python, LangGraph, Supabase

### 발견된 패턴

#### 실수 패턴
- [DAIOps] SPECS 안 읽고 node 추가 → 롤백 2회
  - 세션: "node 추가해줘" → (구현) → "spec에 없네 삭제"

#### 비효율 패턴
- [전체] 빌드 안 돌리고 "완료" 3회
  - 세션: "구현했어" → 다음 턴에 "빌드 깨짐"

#### 좋은 패턴
- [DAIOps] spec 먼저 읽고 구현하는 세션은 롤백 0회

---

## 제안

### P1: 즉시 적용 권장
- [ ] [글로벌] "구현 전 관련 spec 먼저 Read" 규칙
  - 근거: spec 안 읽은 세션에서 롤백 2회
  - 적용: ~/.claude/CLAUDE.md

- [ ] [DAIOps] "/daiops-validate" - 파이프라인 검증 커맨드
  - 근거: "node 빠진거 확인" 요청 3회
  - 적용: .claude/skills/daiops-validate.md

### P2: 고려
- [ ] [글로벌] "빌드/테스트 통과 후 완료 선언" 규칙
  - 근거: 빌드 안 돌리고 완료 선언 3회
```

---

## 요구사항

### 기능 요구사항 (Functional)

| ID | 요구사항 | 우선순위 | 상태 |
|----|----------|----------|------|
| F1 | 세션 압축 (100KB 리미트) | Must | 구현됨 |
| F2 | LLM 직접 분석 (도메인, 프랙티스, 패턴) | Must | 미구현 |
| F3 | KB 요약 프롬프트 포함 | Must | 미구현 |
| F4 | 제안 목록 + 사용자 선택 | Must | 미구현 |
| F5 | 선택된 제안 자동 적용 | Must | 미구현 |

### 비기능 요구사항 (Non-functional)

| ID | 요구사항 | 기준 |
|----|----------|------|
| NF1 | 외부 API 사용 금지 | Zero External API |
| NF2 | 분석 시간 | 압축 < 10초, 분석은 LLM 턴 |
| NF3 | 적용 전 diff 미리보기 | 필수 |

---

## 파일 구조

```
agent_self_optimization/
├── commands/
│   └── optimize-me.md       # 커맨드 정의 (LLM 프롬프트)
├── scripts/
│   ├── compressor.py        # 세션 압축 (유지)
│   └── sync_knowledge.py    # KB 동기화 (유지)
├── knowledge/
│   ├── catalog.json         # KB 인덱스
│   └── best_practices/      # 베스트 프랙티스 요약
├── SPECS/
│   └── OPTIMIZE_ME.md       # 이 문서
└── data/
    └── reports/             # 분석 리포트 저장
```

---

## 삭제 대상

- `SPECS/NO_API_MVP.md` - 오래된 아키텍처
- `SPECS/V2_SMART_COMPRESSION.md` - 복잡한 파이프라인, 삭제됨
- `SPECS/V4_CONTEXT_AWARE.md` - 모듈 다 삭제됨
- `scripts/optimizer.py`의 V4 관련 코드 (없는 모듈 import)

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-01-20 | 인터뷰 기반 스펙 작성 - LLM First 원칙 확립 |
