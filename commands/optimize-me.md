# /optimize-me

세션 분석 → 깊은 수준 개인화 → 제안 → 승인 후 적용

> **LLM First**: Python은 압축만, 모든 분석/판단/제안은 LLM이 직접 수행
> **V2**: Hook 수집 데이터 우선, 해결책 지식베이스 활용, 5 Whys 분석

---

## Execution

### Step 0: Hook 수집 데이터 확인 (우선)

```bash
# Hook 데이터가 있으면 먼저 분석 (가벼움)
python3 scripts/analyze_patterns.py --days 30
```

Hook 데이터가 충분하면 (100+ 패턴) Step 1 스킵 가능.
없거나 부족하면 Step 1로 진행.

### Step 1: 세션 데이터 압축 (초기/보충용)

```bash
python3 scripts/compressor.py --limit 100 --days 30
```

출력된 압축 데이터를 **전부 읽어라**.

### Step 2: Knowledge Base 요약 확인

**필수 파일 읽기**:
```bash
Read knowledge/best_practices/summary.md
```

베스트 프랙티스 요약 파일에서 다음 섹션 확인:
- 개발 프랙티스 (TDD, Spec-first, 검증 습관)
- 세션 관리 (한 세션 한 작업, Context 효율화)
- 피드백 방식 (구체적 지시, 검증 요청)
- 흔한 실수 패턴 (검증 누락, Spec 무시, 롤백 반복)

추가 참조: `knowledge/catalog.json` (110+ 리소스 인덱스)

### Step 3: 깊은 분석 수행

**금지 - 피상적 분석**:
```
❌ "Read 40%, Edit 30% 사용"
❌ "세션 평균 15턴"
❌ "Python 파일 많이 다룸"
→ 어쩌라고?
```

**필수 - 깊은 분석**:

| 영역 | 분석 내용 |
|------|----------|
| **도메인 파악** | MLOps? 리서치? 웹개발? 프로젝트별 기술 스택? |
| **개발 프랙티스** | TDD 쓰는지? Spec 먼저 읽는지? 빌드/테스트 검증? |
| **작업 패턴** | 세션당 작업 수? 모호한 요청? 실수 패턴 (롤백, 삭제)? |
| **LLM 활용** | 과의존 (체크 없이 완료 선언)? 피드백 방식? |

세션 데이터에서 **구체적 증거**를 찾아라:
- "node 추가해줘" → (구현) → "spec에 없네 삭제" = **실수 패턴**
- "구현했어" → 다음 턴에 "빌드 깨짐" = **검증 누락**
- 같은 요청 3회 반복 = **자동화 후보**

### Step 4: 필요시 CLAUDE.md 참조

세션에 나온 프로젝트의 CLAUDE.md 직접 Read:
- 글로벌: `~/.claude/CLAUDE.md`
- 프로젝트별: 프로젝트 내 `CLAUDE.md`

### Step 5: 해결책 지식베이스 참조

**필수 파일 읽기**:
```bash
Read knowledge/solutions/patterns.json
```

발견된 패턴을 지식베이스와 매칭:
- `heavy_exploration` → 탐색 과다
- `context_reset` → Context 리셋
- `repeated_corrections` → 반복 수정
- `same_file_repeated_reads` → 같은 파일 반복
- `shallow_analysis` → 피상적 분석 (금지)
- `missing_tests` → 테스트 누락

### Step 6: 제안 생성

```markdown
## 분석 결과

### 도메인
- **주요 프로젝트**: [프로젝트명] ([기술 스택])
- **기술 스택**: [언어], [프레임워크], [도구]

### 발견된 패턴

#### 실수/비효율 패턴
- **[패턴ID]** [프로젝트] 구체적 설명 (발생 횟수)
  - 증거: "사용자 발화 인용" 또는 Hook 데이터
  - **5 Whys**:
    - Why1: [직접 원인]
    - Why2: [더 깊은 원인]
    - Why3: [근본 원인]

#### 좋은 패턴 (유지)
- [프로젝트] 유지할 패턴

---

## 제안

### P1: 즉시 적용 권장

| 패턴 | 해결책 | 유형 | Effort | Impact |
|------|--------|------|--------|--------|
| [패턴ID] | [action] | command/workflow/claude_md/hook | low/med | high |

- **근거**: 세션/Hook에서 발견한 증거
- **검증 방법**: [어떻게 효과 측정]
- **성공 기준**: [언제 성공으로 볼 것인지]

### P2: 고려
- [ ] ...

### P3: 나중에
- [ ] ...
```

**해결책 유형**:
- `command`: /gsd:map-codebase, /bugfix 등 실행
- `workflow`: 작업 순서/프로세스 변경
- `claude_md`: CLAUDE.md에 규칙 추가
- `hook`: 자동화 훅 설치
- `process`: 습관/방식 변경

### Step 7: 사용자 선택

AskUserQuestion으로 제안 중 적용할 항목 선택:
- `multiSelect: true`로 복수 선택 가능
- 각 제안의 근거와 적용 위치 명시

### Step 8: 적용

승인된 제안을 적용:
1. **diff 미리보기 필수** - 변경 내용 보여주기
2. CLAUDE.md 규칙 → 해당 파일에 추가
3. Skill/Slash → `.claude/skills/` 파일 생성
4. 백업 권장

---

## Usage

```bash
/optimize-me              # 기본 실행 (30일, 100KB)
/optimize-me --days 7     # 최근 7일만
/optimize-me --limit 50   # 50KB로 제한
```

## Safety

- 모든 수정 전 diff 미리보기 필수
- CLAUDE.md 수정 시 백업 권장
- 사용자 승인 후에만 적용
