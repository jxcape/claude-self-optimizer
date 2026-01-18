# Agent Self-Optimization - No-API Milestones

## Overview

Claude Code API 없이 Claude Code 내 에이전트만으로 구현하는 자기 최적화 시스템 개발 4주 마일스톤.

---

## Phase 1: 기반 구축 (Week 1)

### 목표

세션 수집 및 로컬 저장소 구축.

### 작업

#### Day 1-2: 저장소 구조

- [ ] **디렉토리 생성**
  - [ ] data/sessions/
  - [ ] data/analysis/
  - [ ] data/proposals/
  - [ ] data/feedback/
  - [ ] logs/

- [ ] **데이터 포맷 정의**
  - [ ] Session JSON 포맷
  - [ ] Analysis Markdown 포맷
  - [ ] Proposal Markdown 포맷
  - [ ] Feedback Markdown 포맷

#### Day 3-4: /collect-sessions Skill

- [ ] **Skill 생성**
  - [ ] `.claude/skills/collect-sessions.md` 생성
  - [ ] session_list() 호출 로직
  - [ ] session_read() 호출 로직
  - [ ] 로컬 JSON 저장 로직

- [ ] **테스트**
  - [ ] 최근 7일 세션 수집 테스트
  - [ ] JSON 포맷 검증
  - [ ] 에러 핸들링 테스트

#### Day 5-7: 로깅 및 검증

- [ ] **로깅 시스템**
  - [ ] 수집 로그 저장 (logs/collection.log)
  - [ ] 성공/실패 카운트

- [ ] **검증**
  - [ ] 데이터 무결성 검사
  - [ ] 중복 확인
  - [ ] 수집 완료 리포트

### 성공 기준

- [ ] 최근 7일 세션 100% 수집
- [ ] JSON 포맷 일관성 유지
- [ ] 에러율 <5%

---

## Phase 2: 분석 시스템 (Week 2)

### 목표

세션 분석 및 사용자 성향/도메인 파악.

### 작업

#### Day 1-2: /analyze-sessions Skill

- [ ] **Skill 생성**
  - [ ] `.claude/skills/analyze-sessions.md` 생성
  - [ ] 로컬 JSON 읽기 로직
  - [ ] LLM 분석 프롬프트 설계
  - [ ] 분석 결과 저장 로직

- [ ] **분석 프롬프트**
  - [ ] 사용자 성향 분석
  - [ ] 도메인/문제 파악
  - [ ] 패턴 추출
  - [ ] 성공/실패 추정

#### Day 3-4: 분석 품질 향상

- [ ] **프롬프트 튜닝**
  - [ ] 예시 포함 (few-shot)
  - [ ] 출력 포맷 명확화
  - [ ] 에지 케이스 처리

- [ ] **분석 다양성**
  - [ ] 여러 세션 비교 분석
  - [ ] 시간 추이 분석
  - [ ] 패턴 변화 감지

#### Day 5-7: 리포트 생성

- [ ] **주간 분석 리포트**
  - [ ] data/analysis/YYYY-MM-DD_weekly_analysis.md
  - [ ] 사용자 스타일 요약
  - [ ] 패턴 목록
  - [ ] 개선 제안

- [ ] **테스트**
  - [ ] 최근 10개 세션 분석 테스트
  - [ ] 분석 품질 검증
  - [ ] 리포트 가독성 체크

### 성공 기준

- [ ] 분석 정확도 (주관적) >70%
- [ ] 주간 리포트 생성 완료
- [ ] 패턴 추출 성공

---

## Phase 3: 제안 생성 (Week 3)

### 목표

분석 결과를 바탕으로 CLAUDE.md/Skill 업데이트 제안 생성.

### 작업

#### Day 1-2: /generate-proposals Skill

- [ ] **Skill 생성**
  - [ ] `.claude/skills/generate-proposals.md` 생성
  - [ ] 분석 결과 읽기 로직
  - [ ] 제안 생성 로직
  - [ ] 제안 저장 로직

- [ ] **제안 타입**
  - [ ] CLAUDE.md 업데이트 제안
  - [ ] 신규 Skill 제안
  - [ ] 워크플로우 최적화 제안

#### Day 3-4: 제안 포맷 정의

- [ ] **제안 템플릿**
  - [ ] 제안 타입 (추가/수정/삭제)
  - [ ] 근거 (데이터 기반)
  - [ ] 변경사항 (diff 형식)
  - [ ] 효과 예상

- [ ] **피드백 폼**
  - [ ] 승인/거부
  - [ ] 만족도 (1-5점)
  - [ ] 추가 제안

#### Day 5-7: Obsidian 노트 생성

- [ ] **자동 노트 생성**
  - [ ] `06_Weekly_Review/YYYY-MM-DD_Proposal.md`
  - [ ] 제안 요약
  - [ ] 피드백 요청
  - [ ] 쉬운 수정 폼

- [ ] **테스트**
  - [ ] 제안 품질 테스트
  - [ ] Obsidian 노트 가독성
  - [ ] 피드백 용이성

### 성공 기준

- [ ] 주간 제안 3개 이상 생성
- [ ] 제안 품질 (주관적) >70%
- [ ] Obsidian 노트 자동 생성

---

## Phase 4: 피드백 루프 (Week 4)

### 목표

피드백 수집 및 자동 업데이트 시스템 구현.

### 작업

#### Day 1-2: /apply-feedback Skill

- [ ] **Skill 생성**
  - [ ] `.claude/skills/apply-feedback.md` 생성
  - [ ] 피드백 읽기 로직
  - [ ] 승인된 제안 적용 로직
  - [ ] CLAUDE.md/Skill 수정 로직

- [ ] **업데이트 메커니즘**
  - [ ] CLAUDE.md 자동 수정
  - [ ] 신규 Skill 파일 생성
  - [ ] 버전 관리 (git)

#### Day 3-4: CLAUDE.md 프로토콜

- [ ] **세션 시작 체크**
  - [ ] data/proposals/ 확인
  - [ ] 대기 중 제안 표시
  - [ ] 피드백 요청

- [ ] **세션 종료 체크** (선택)
  - [ ] data/feedback/ 확인
  - [ ] 즉시 적용 제안

#### Day 5-7: 완전 통합 테스트

- [ ] **엔드 투 엔드 테스트**
  - [ ] 세션 수집 → 분석 → 제안 → 피드백 → 업데이트
  - [ ] 전체 흐름 검증

- [ ] **사용성 테스트**
  - [ ] 사용자 편의성 체크
  - [ ] 수동 조작 시간 측정

- [ ] **문서화**
  - [ ] 사용 가이드 작성
  - [ ] 문제 해결 가이드
  - [ ] README 업데이트

### 성공 기준

- [ ] 피드백 루프 완전 작동
- [ ] 자동 업데이트 정상 작동
- [ ] 사용자 만족도 >70%

---

## Weekly Summary

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1 | 기반 구축 | 세션 수집, 로컬 저장소 |
| 2 | 분석 시스템 | 사용자 성향, 도메인, 패턴 분석 |
| 3 | 제안 생성 | CLAUDE.md/Skill 업데이트 제안 |
| 4 | 피드백 루프 | 자동 업데이트, 완전 통합 |

---

## Daily Workflow (MVP)

### 월요일: 세션 수집

```
1. /collect-sessions
2. data/sessions/에 저장
3. 수집 리포트 확인
```

### 화요일: 세션 분석

```
1. /analyze-sessions
2. data/analysis/에 저장
3. 분석 리포트 확인
```

### 수요일: 제안 생성

```
1. /generate-proposals
2. data/proposals/에 저장
3. Obsidian 노트 확인
```

### 목요일-토요일: 사용자 리뷰

```
1. Obsidian에서 제안 검토
2. 피드백 작성
3. data/feedback/에 저장
```

### 일요일: 업데이트 적용

```
1. /apply-feedback
2. CLAUDE.md/Skill 업데이트
3. 변경사항 확인
```

---

## Integration with Claude Code

### CLAUDE.md 추가

```markdown
## Agent Self-Optimization

### Session Start
1. Check data/proposals/ for pending proposals
2. If found, summarize and ask for feedback
3. Check data/feedback/ for pending feedback
4. If found, ask if user wants to apply

### Daily Workflow
- Monday: /collect-sessions
- Tuesday: /analyze-sessions
- Wednesday: /generate-proposals
- Thursday-Saturday: User review (Obsidian)
- Sunday: /apply-feedback
```

---

## Risk & Mitigation

### Risk 1: 수동 트리거 불편

- **완화**: CLAUDE.md에서 자동 체크
- **대안**: 첫 세션에서 "최신 세션 수집?" 물어보기

### Risk 2: 분석 품질 낮음

- **완화**: 피드백 루프로 지속적 개선
- **대안**: 수동 분석 도입

### Risk 3: 자동 업데이트 오류

- **완화**: 사용자 승인 필수
- **대안**: 롤백 메커니즘 (git)

---

## Success Metrics (4 Weeks)

- [ ] 세션 수집 100%
- [ ] 분석 품질 >70%
- [ ] 제안 승인율 >50%
- [ ] 자동 업데이트 정상 작동
- [ ] 사용자 만족도 >70%
- [ ] 수동 조작 시간 <5분/주

---

## Post-MVP (Month 2-6)

### Month 2: 개인화 완성

- [ ] 사용자 성향 정확도 >85%
- [ ] 도메인별 최적화
- [ ] 워크플로우 완전 최적화

### Month 3: 자기 개선 루프

- [ ] 패턴 DB 학습 (로컬)
- [ ] 분석 품질 자동 향상
- [ ] 피드백 루프 고도화

### Month 4-6: 확장

- [ ] 다른 프로젝트 적용
- [ ] 커뮤니티 오픈소스
- [ ] 오피셜 MCP로 제안?
