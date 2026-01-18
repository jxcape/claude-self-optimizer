# V2: Smart Compression Analysis

> **목표**: 임베딩 없이 스마트 압축으로 세션 분석 → Skill/Slash/Agent/CLAUDE.md 자동 제안

---

## 1. 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **No Embedding** | 한국어 로컬 임베딩 성능 이슈 → 압축만으로 해결 |
| **분석 시점 압축** | 세션 중 오버헤드 없음, 원본 보존 |
| **파일 리미트 기반** | 고정 세션 수 X → 크기 맞춰 동적 수집 |
| **최신 우선** | 오래된 세션 자연 탈락 |

---

## 2. 압축 전략

### 2.1 압축 규칙

```
┌─────────────────────────────────────────────────────────┐
│                    원본 세션                              │
├─────────────────────────────────────────────────────────┤
│ User 메시지      → 전문 보존 (평균 100자, 짧음)           │
│ Claude 텍스트    → 첫 100자 또는 생략                    │
│ Claude 도구 호출 → 도구명 + 핵심 param 요약              │
│ 도구 결과        → 성공/실패만 (내용 버림)               │
└─────────────────────────────────────────────────────────┘
```

### 2.2 도구별 압축 포맷

| 도구 | 원본 | 압축 후 |
|------|------|---------|
| Read | `{"file_path": "/Users/xcape/project/src/main.py", "result": "500줄..."}` | `Read: src/main.py` |
| Edit | `{"file_path": "...", "old_string": "...", "new_string": "..."}` | `Edit: src/main.py` |
| Write | `{"file_path": "...", "content": "..."}` | `Write: src/new_file.py` |
| Bash | `{"command": "npm test", "result": "..."}` | `Bash: npm test → ✓` |
| Grep | `{"pattern": "TODO", "path": "src/"}` | `Grep: "TODO" in src/` |
| Glob | `{"pattern": "**/*.py"}` | `Glob: **/*.py` |
| Task | `{"subagent_type": "Explore", "prompt": "..."}` | `Task(Explore): 코드베이스 탐색` |
| TodoWrite | `{"todos": [...]}` | `Todo: 3개 항목 추가` |

### 2.3 압축 예시

**원본** (약 50KB):
```json
{"role": "user", "content": "이 파일 리팩토링해줘"}
{"role": "assistant", "tool_use": {"name": "Read", "file_path": "/Users/xcape/project/src/main.py"}, "result": "... 500줄 ..."}
{"role": "assistant", "tool_use": {"name": "Edit", "file_path": "...", "old_string": "def old_func():", "new_string": "def new_func():"}}
{"role": "assistant", "content": "리팩토링을 완료했습니다. 함수명을 old_func에서 new_func로 변경하고..."}
```

**압축 후** (약 200B):
```
U: 이 파일 리팩토링해줘
C: Read: src/main.py | Edit: src/main.py | 리팩토링 완료
```

### 2.4 압축률

```
원본 세션 (50 msg):     ~250KB
압축 후:                ~3-5KB
압축률:                 ~98%

100KB 리미트 기준:      ~20-30 세션 수집 가능
```

---

## 3. 동적 수집

### 3.1 수집 로직

```python
def collect_for_analysis(limit_kb: int = 100) -> List[CompressedSession]:
    """
    최신 세션부터 limit_kb에 맞춰 동적 수집

    Args:
        limit_kb: 목표 크기 (기본 100KB)
                  - 100KB = Claude context ~10%
                  - 충분한 여유 + 분석 프롬프트 공간

    Returns:
        압축된 세션 리스트 (최신순)
    """
    sessions = get_all_sessions(sorted_by="recent")
    collected = []
    total_size = 0

    for session in sessions:
        compressed = compress_session(session)
        size = len(compressed.encode('utf-8'))

        # 리미트 초과 시 중단
        if total_size + size > limit_kb * 1024:
            break

        collected.append(compressed)
        total_size += size

    return collected
```

### 3.2 리미트 가이드

| 리미트 | 예상 세션 수 | 용도 |
|--------|-------------|------|
| 50KB | ~10-15개 | 빠른 분석 |
| 100KB | ~20-30개 | 기본값 (1-2주) |
| 200KB | ~40-60개 | 심층 분석 (1달) |

---

## 4. 자동 분류

### 4.1 분류 기준

```
┌─────────────────────────────────────────────────────────┐
│                   패턴 감지                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [반복 패턴?]                                            │
│       │                                                 │
│       ├─ 도구 시퀀스 반복 (Read→Edit→Bash)              │
│       │       └─→ Skill (코드화 가능)                   │
│       │                                                 │
│       ├─ 프롬프트 템플릿 반복 ("~해줘" 패턴)             │
│       │       └─→ Slash Command                        │
│       │                                                 │
│       ├─ 복잡한 탐색+멀티스텝 (Task 사용, 10+ turns)     │
│       │       └─→ Agent (서브에이전트 필요)             │
│       │                                                 │
│       └─ 행동 규칙 반복 (한글 응답, 특정 스타일)         │
│               └─→ CLAUDE.md 패턴                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.2 분류 로직

```python
@dataclass
class Pattern:
    type: Literal["tool_sequence", "prompt_template", "complex_task", "behavioral"]
    frequency: int
    examples: List[str]
    confidence: float

def classify_pattern(pattern: Pattern) -> SuggestionType:
    # Skill: 도구 시퀀스 반복 (코드화 가능)
    if pattern.type == "tool_sequence":
        if pattern.frequency >= 3:
            return SuggestionType.SKILL

    # Agent: 복잡한 멀티스텝
    if pattern.type == "complex_task":
        if uses_task_subagent(pattern) or avg_turns(pattern) > 10:
            return SuggestionType.AGENT

    # Slash: 프롬프트 템플릿
    if pattern.type == "prompt_template":
        if pattern.frequency >= 3:
            return SuggestionType.SLASH_COMMAND

    # CLAUDE.md: 행동 규칙
    if pattern.type == "behavioral":
        return SuggestionType.CLAUDE_MD_RULE

    return SuggestionType.UNKNOWN
```

### 4.3 분류 예시

| 패턴 | 빈도 | 분류 | 제안 |
|------|------|------|------|
| "파일 읽고 요약해줘" | 5회 | Slash | `/summarize-file` |
| Read→Grep→Edit 시퀀스 | 10회 | Skill | `refactor-pattern.md` |
| Task(Explore) 후 Plan 작성 | 8회 | Agent | `code-architect` |
| 한글 응답 선호 | 일관 | CLAUDE.md | `Output language: Korean` |
| 커밋 전 테스트 실행 | 7회 | Skill | `pre-commit-test.md` |

---

## 5. 훅 조건

### 5.1 수집 트리거

```yaml
# 원본 세션 수집 (압축은 분석 시점)
collection_triggers:

  # 1. 세션 종료 시 (기본)
  on_session_end:
    action: save_raw_session
    path: data/sessions/raw/

  # 2. 수동 트리거 (/collect-sessions)
  on_command:
    command: /collect-sessions
    action: collect_recent_sessions
```

### 5.2 분석 트리거

```yaml
analysis_triggers:

  # 1. 수동 (/optimize-me)
  on_command:
    command: /optimize-me
    action: run_full_analysis

  # 2. 예약 실행 (비근무시간)
  scheduled:
    time: "22:00"
    action: run_incremental_analysis

  # 3. 세션 시작 시 (대기 제안 있으면)
  on_session_start:
    condition: pending_proposals_exist
    action: show_proposals
```

---

## 6. 데이터 구조

### 6.1 디렉토리

```
data/
├── sessions/
│   ├── raw/                    # 원본 세션 (압축 전)
│   │   ├── 2026-01-16_uuid1.json
│   │   └── ...
│   └── compressed/             # 분석용 압축본 (캐시)
│       └── 2026-01-16_batch.txt
├── analysis/
│   ├── patterns/               # 추출된 패턴
│   │   ├── tool_sequences.json
│   │   ├── prompt_templates.json
│   │   └── behavioral_rules.json
│   └── reports/
│       └── 2026-01-16_analysis.md
└── proposals/
    ├── skills/                 # Skill 제안
    ├── slash_commands/         # Slash 제안
    ├── agents/                 # Agent 제안
    └── claude_md_rules/        # CLAUDE.md 규칙 제안
```

### 6.2 압축 세션 포맷

```
# Session: 리팩토링 작업 (2026-01-16)
Project: /Users/xcape/gemmy/10_Projects/DAIOps
Turns: 23
Duration: 45min

---
U: 이 파일 리팩토링해줘
C: Read: src/main.py | Edit: src/main.py

U: 테스트 돌려봐
C: Bash: pytest → ✓ (15 passed)

U: 커밋해줘
C: Bash: git add . | Bash: git commit → ✓
---
```

### 6.3 패턴 스키마

```python
@dataclass
class ExtractedPattern:
    id: str
    type: str                    # tool_sequence, prompt_template, etc.
    pattern: str                 # "Read→Edit→Bash" or "~해줘"
    frequency: int
    sessions: List[str]          # 발견된 세션 ID
    examples: List[str]          # 실제 사용 예시 (3개)
    confidence: float            # 0.0 ~ 1.0

@dataclass
class Suggestion:
    pattern_id: str
    type: SuggestionType         # SKILL, SLASH, AGENT, CLAUDE_MD
    name: str                    # 제안 이름
    description: str             # 설명
    implementation: str          # 실제 코드/프롬프트
    estimated_impact: str        # 예상 효과
    status: str                  # pending, approved, rejected
```

---

## 7. 구현 순서

### Phase 1: 압축 모듈 (3일) ✅ 완료

- [x] `scripts/compressor.py`
  - [x] 세션 로드 함수
  - [x] 도구별 압축 함수
  - [x] 동적 수집 함수 (리미트 기반)
  - [x] 압축률 99.8% 달성

- [x] `scripts/test_data_gen.py` (collector 대체)
  - [x] Mock 세션 생성 (4 시나리오 x 5 반복)
  - [x] 압축 포맷 출력

### Phase 2: 패턴 추출 (4일) ✅ 완료

- [x] `scripts/pattern_extractor.py`
  - [x] 도구 시퀀스 마이닝 (3-gram)
  - [x] 프롬프트 템플릿 추출
  - [x] 행동 규칙 감지

- [x] `scripts/classifier.py`
  - [x] Skill/Slash/Agent/CLAUDE.md 분류
  - [x] 신뢰도 계산
  - [x] 우선순위 정렬 (P1/P2/P3)

### Phase 3: 제안 생성 (3일) ✅ 완료

- [x] `scripts/generate_proposals.py` (V2 연동)
  - [x] 패턴 → 제안 변환
  - [x] 템플릿 기반 코드 생성
  - [x] Markdown 리포트 생성

- [ ] `/optimize-me` 업데이트
  - [ ] 압축 기반 분석 연동
  - [ ] 제안 표시 + 승인 흐름

### Phase 4: 예약 실행 (2일) 🔜 다음 단계

- [ ] LaunchAgent 설정
- [ ] 로깅 + 알림
- [ ] 세션 시작 시 제안 표시

---

## 8. 파이프라인 요약

```
[세션 종료]
     ↓
[원본 저장] → data/sessions/raw/
     ↓
[/optimize-me 또는 예약 실행]
     ↓
[동적 수집] ← 100KB 리미트, 최신 우선
     ↓
[압축] → 유저 전문 + 도구 요약
     ↓
[패턴 추출] → 시퀀스, 템플릿, 규칙
     ↓
[분류] → Skill / Slash / Agent / CLAUDE.md
     ↓
[제안 생성] → data/proposals/
     ↓
[사용자 승인] → AskUserQuestion
     ↓
[적용] → .claude/skills/, CLAUDE.md
```

---

## 9. 예상 효과

| 지표 | V1 (현재) | V2 (압축) |
|------|-----------|-----------|
| 분석 대상 크기 | 전체 (~10MB) | 100KB (리미트) |
| 처리 세션 수 | 수동 선택 | 자동 20-30개 |
| 분류 방식 | 수동 | 자동 (4종) |
| 세션 중 오버헤드 | - | 없음 |
| 압축률 | - | ~98% |

---

## 10. 리스크 & 완화

| 리스크 | 완화 |
|--------|------|
| 압축 시 정보 손실 | 도구 호출은 핵심 param 보존 |
| 패턴 추출 정확도 | 빈도 3회 이상만 제안 |
| 분류 오류 | 사용자 승인 필수 |
| 오래된 세션 누락 | 주기적 심층 분석 (200KB 리미트) |

---

## 11. 다음 단계

1. **즉시**: 기존 세션 83개 압축 테스트
2. **D1-3**: 압축 모듈 구현
3. **D4-7**: 패턴 추출 + 분류
4. **D8-10**: 제안 생성 + /optimize-me 연동
5. **D11-12**: 예약 실행 설정
