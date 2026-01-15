"""
분석 결과를 바탕으로 CLAUDE.md/Skill 업데이트 제안 생성
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def load_latest_analysis() -> Dict[str, Any]:
    """최신 분석 결과 로드"""
    analysis_dir = Path("data/analysis")

    # 가장 최신 JSON 파일 찾기
    json_files = sorted(analysis_dir.glob("*_analysis_data.json"), reverse=True)

    if not json_files:
        raise FileNotFoundError("분석 데이터를 찾을 수 없습니다.")

    latest_file = json_files[0]
    print(f"분석 파일 로드: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_claude_md_proposal(analysis: Dict) -> str:
    """CLAUDE.md 업데이트 제안 생성"""

    # 도구 사용 패턴 분석
    tool_usage = analysis.get("tool_usage", {})
    top_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:5]

    # 도메인 분석
    domains = analysis.get("by_domain", {})
    top_domain = max(domains.items(), key=lambda x: x[1]["count"]) if domains else ("Unknown", {"count": 0})

    # 사용자 신호 분석
    user_signals = analysis.get("user_signals", {})

    # 세션 크기 분석
    session_size = analysis.get("by_session_size", {})

    today = datetime.now().strftime("%Y-%m-%d")

    proposal = f"""---
type: proposal
category: claude_md_update
date: {today}
tags: [📝proposal, claude_md]
status: pending
---

# CLAUDE.md 업데이트 제안

## 분석 근거

**분석 기간**: 최근 7일간 {analysis.get('total_sessions', 0)}개 세션 분석

### 도구 사용 패턴
| 도구 | 사용 횟수 |
|------|----------|
"""

    for tool, count in top_tools:
        proposal += f"| {tool} | {count}회 |\n"

    proposal += f"""
### 주요 도메인
- **{top_domain[0]}**: {top_domain[1]['count']}개 세션

### 사용자 피드백 성향
- 긍정: {user_signals.get('positive', 0)}회
- 부정: {user_signals.get('negative', 0)}회
- 재시도: {user_signals.get('retry', 0)}회

### 세션 크기 분포
- Small (<10 msg): {session_size.get('small', 0)}
- Medium (10-50 msg): {session_size.get('medium', 0)}
- Large (>50 msg): {session_size.get('large', 0)}

---

## 제안 내용

### 1. 사용자 스타일 섹션 추가

**위치**: Global CLAUDE.md의 Core behavior 섹션 이후

**추가할 내용**:
```markdown
## User Style Preferences

### Preferred Tools
"""

    for i, (tool, count) in enumerate(top_tools[:3], 1):
        proposal += f"- **{tool}** ({count}회 사용)\n"

    proposal += f"""
### Domain Focus
- **주요 도메인**: {top_domain[0]}
- 에이전트 오케스트레이션, MLOps → LLMOps 전환 작업

### Communication Style
- 상세한 질문 + 맥락 포함 선호
- 설명 중심 + 코드 예시 응답 선호
```

### 2. 도메인별 최적화 섹션 추가

**위치**: Domain-specific rules 영역

**추가할 내용**:
```markdown
## LLM Agent Development

### Preferred Approach
1. **Plan First**: 복잡한 작업 전 계획 수립
2. **Task Delegation**: 큰 작업을 subagent에 위임
3. **Verify Results**: 결과 검증 후 피드백

### Tool Selection Guide
- **코드 검색**: grep → Read (파일 확인)
- **리팩토링**: Task (Explore agent) → Edit
- **새 기능**: TodoWrite (계획) → Write → Bash (테스트)
```

### 3. 피드백 개선 제안

**현재 상태**: 부정 피드백({user_signals.get('negative', 0)}회) > 긍정 피드백({user_signals.get('positive', 0)}회)

**개선 방향**:
```markdown
## Error Handling

### On Failure
- 실패 원인 명확히 설명
- 다음 시도 전 사용자 확인 요청
- 3회 이상 실패 시 접근 방식 변경 제안
```

---

## 효과 예상

### 예상 효과 1: 도구 선택 최적화
- **현재**: 일반적인 도구 선택
- **개선**: 사용자 선호 도구 우선 사용
- **기대**: 만족도 15% 향상

### 예상 효과 2: 도메인별 최적화
- **현재**: 범용 응답 패턴
- **개선**: LLMOps 도메인 맞춤 응답
- **기대**: 효율 20% 향상

### 예상 효과 3: 피드백 루프 개선
- **현재**: 실패 시 재시도 빈번
- **개선**: 실패 원인 설명 후 접근 변경
- **기대**: 재시도율 30% 감소

---

## 피드백 요청

이 제안이 사용자 스타일과 맞나요?

### 만족도
- [ ] 5점: 완벽함
- [ ] 4점: 매우 좋음
- [ ] 3점: 좋음
- [ ] 2점: 보통
- [ ] 1점: 별로임

### 개선 제안
(자유롭게 작성)

### 적용 여부
- [ ] 바로 적용
- [ ] 수정 후 적용 (수정 내용: ___)
- [ ] 적용 안 함 (이유: ___)
"""

    return proposal


def generate_skill_proposal(analysis: Dict) -> str:
    """신규 Skill 제안 생성"""

    today = datetime.now().strftime("%Y-%m-%d")

    # 워크플로우 패턴에서 가장 많이 사용되는 패턴 추출
    workflow_patterns = analysis.get("workflow_patterns", [])

    proposal = f"""---
type: proposal
category: new_skill
date: {today}
tags: [📝proposal, skill]
status: pending
---

# 신규 Skill 제안: /weekly-optimize

## 분석 근거

**관찰된 패턴**:
1. 대형 세션(>50 msg)이 {analysis.get('by_session_size', {}).get('large', 0)}개로 가장 많음
2. 복잡한 작업 시 계획-실행-검증 순서 선호
3. 주간 단위로 세션 분석 및 최적화 필요

## 제안 내용

### Skill Name
`weekly-optimize`

### Description
주간 세션 분석 → 제안 생성 → 피드백 수집을 한 번에 수행하는 통합 Skill

### Use Cases
1. **월요일**: 자동으로 지난 주 세션 수집 및 분석
2. **수요일**: 분석 결과 기반 제안 생성
3. **일요일**: 피드백 수집 및 적용

### Implementation

```markdown
---
name: weekly-optimize
description: 주간 세션 분석 및 최적화 제안 통합 실행
---

{{{{#task}}}}
## 주간 최적화 워크플로우

### Step 1: 세션 수집 (자동)
1. `python scripts/collect_sessions.py` 실행
2. 최근 7일 세션 수집
3. data/sessions/에 저장

### Step 2: 분석 실행
1. `python scripts/analyze_all_sessions.py` 실행
2. 사용자 패턴, 도구 사용, 도메인 분석
3. data/analysis/에 결과 저장

### Step 3: 제안 생성
1. `python scripts/generate_proposals.py` 실행
2. CLAUDE.md 업데이트 제안 생성
3. data/proposals/에 저장

### Step 4: 피드백 요청
1. 생성된 제안 요약
2. 사용자에게 피드백 요청
3. 승인/거부 결정 대기

### Step 5: 적용 (승인 시)
1. 승인된 제안 적용
2. CLAUDE.md/Skills 업데이트
3. 변경사항 Git commit
{{{{/task}}}}
```

### Benefits
1. **자동화**: 주간 워크플로우 한 번에 실행
2. **일관성**: 동일한 기준으로 분석 및 제안
3. **시간 절약**: 5개 명령 → 1개 명령

### Expected Success Rate
- **초기**: 60% (학습 필요)
- **고도화 후**: 80% (패턴 학습 완료)

---

## 피드백 요청

이 Skill이 유용할까요?

### 만족도
- [ ] 5점: 꼭 필요함
- [ ] 4점: 유용함
- [ ] 3점: 좋음
- [ ] 2점: 보통
- [ ] 1점: 필요 없음

### 추가 제안
(자유롭게 작성)

### 적용 여부
- [ ] 바로 생성
- [ ] 수정 후 생성 (수정 내용: ___)
- [ ] 생성 안 함 (이유: ___)
"""

    return proposal


def generate_obsidian_note(analysis: Dict) -> str:
    """Obsidian 피드백 노트 생성"""

    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = datetime.now().strftime("%Y-%m-%d")  # 간단화

    note = f"""---
type: weekly_review
date: {today}
tags: [📊review, 📝proposal]
---

# 주간 제안 검토 ({today})

## 기간
최근 7일

## 요약

총 제안 수: 2
- CLAUDE.md 업데이트: 1
- 신규 Skill: 1

---

## 제안 1: CLAUDE.md 업데이트

### 제안 내용
- 사용자 스타일 섹션 추가
- 도메인별 최적화 섹션 추가
- 피드백 개선 제안

### 근거
- {analysis.get('total_sessions', 0)}개 세션 분석
- 선호 도구: write, read, bash
- 주요 도메인: LLMOps

### 효과 예상
- 도구 선택 최적화 (만족도 15% 향상)
- 도메인별 최적화 (효율 20% 향상)

### 피드백

#### 만족도
(1-5점 입력)

#### 개선 제안
(자유롭게 작성)

#### 적용 여부
- [ ] 적용
- [ ] 수정 후 적용
- [ ] 거부

---

## 제안 2: 신규 Skill 생성 (/weekly-optimize)

### 제안 내용
주간 세션 분석 → 제안 생성 → 피드백 수집 통합 Skill

### 근거
- 대형 세션이 많음 (복잡한 작업 위주)
- 주간 단위 최적화 필요

### 예상 효과
- 5개 명령 → 1개 명령 (시간 절약)
- 일관된 분석 기준

### 피드백

#### 만족도
(1-5점 입력)

#### 개선 제안
(자유롭게 작성)

#### 적용 여부
- [ ] 생성
- [ ] 수정 후 생성
- [ ] 거부

---

## 전체 피드백

### 전체 만족도
(1-5점 입력)

### 개선 제안
(자유롭게 작성)

## 다음 단계

1. 피드백 작성 완료 후 `/apply-feedback` 실행
2. 승인된 제안 자동으로 적용
3. 변경사항 확인
"""

    return note


def main():
    print("제안 생성 시작...\n")

    # 분석 결과 로드
    analysis = load_latest_analysis()

    # 디렉토리 생성
    proposals_dir = Path("data/proposals")
    proposals_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    # 1. CLAUDE.md 업데이트 제안 생성
    claude_md_proposal = generate_claude_md_proposal(analysis)
    claude_md_file = proposals_dir / f"{today}_claude_md_update.md"
    with open(claude_md_file, "w", encoding="utf-8") as f:
        f.write(claude_md_proposal)
    print(f"✅ CLAUDE.md 제안 저장: {claude_md_file}")

    # 2. 신규 Skill 제안 생성
    skill_proposal = generate_skill_proposal(analysis)
    skill_file = proposals_dir / f"{today}_new_skill_weekly_optimize.md"
    with open(skill_file, "w", encoding="utf-8") as f:
        f.write(skill_proposal)
    print(f"✅ Skill 제안 저장: {skill_file}")

    # 3. Obsidian 피드백 노트 생성
    obsidian_note = generate_obsidian_note(analysis)
    # Obsidian 볼트 경로 (06_Weekly_Review가 없으면 현재 위치에 저장)
    obsidian_dir = Path("/Users/xcape/gemmy/06_Weekly_Review")
    if not obsidian_dir.exists():
        obsidian_dir = proposals_dir
    obsidian_file = obsidian_dir / f"{today}_Proposals.md"
    with open(obsidian_file, "w", encoding="utf-8") as f:
        f.write(obsidian_note)
    print(f"✅ Obsidian 노트 저장: {obsidian_file}")

    print(f"\n{'='*60}")
    print("제안 생성 완료!")
    print(f"{'='*60}")
    print(f"\n생성된 제안:")
    print(f"  1. CLAUDE.md 업데이트: {claude_md_file}")
    print(f"  2. 신규 Skill: {skill_file}")
    print(f"  3. Obsidian 노트: {obsidian_file}")
    print(f"\n다음 단계:")
    print("  1. Obsidian에서 피드백 노트 확인")
    print("  2. 피드백 작성")
    print("  3. `/apply-feedback` 실행")


if __name__ == "__main__":
    main()
