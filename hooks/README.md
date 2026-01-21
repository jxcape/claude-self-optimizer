# Pattern Collector Hook

실시간으로 사용 패턴을 수집하는 Claude Code 훅.

## 수집 대상

### 부정적 반응 (Negative Reactions)
사용자 불만족 신호를 감지:
- `다시 해줘`, `틀렸어` → retry_request, wrong_output
- `전부 다 틀렸어` → all_wrong (critical)
- `왜 이렇게`, `아니야` → frustration, correction

### 도구 사용 패턴 (Tool Usage)
- 파일 읽기/검색 빈도
- 같은 파일 반복 읽기
- Agent 스폰 패턴

## 설치

### 1. settings.json에 훅 등록

`~/.claude/settings.json` (또는 프로젝트별 `.claude/settings.json`):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          "python3 /path/to/agent_self_optimization/hooks/pattern_collector.py"
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          "python3 /path/to/agent_self_optimization/hooks/pattern_collector.py"
        ]
      }
    ]
  }
}
```

### 2. 경로 수정

위 경로를 실제 설치 위치로 변경:
```bash
# 현재 경로 확인
pwd
# /Users/xcape/gemmy/10_Projects/agent_self_optimization
```

### 3. 권한 확인

```bash
chmod +x hooks/pattern_collector.py
```

## 데이터 저장 위치

`data/patterns.jsonl` - JSONL 형식으로 저장

```jsonl
{"timestamp": "2026-01-20T15:30:00", "type": "negative_reaction", "pattern_type": "retry_request", "severity": "high", ...}
{"timestamp": "2026-01-20T15:31:00", "type": "tool_usage", "tool": "Read", "file_path": "/path/to/file", ...}
```

## 분석

```bash
# 기본 분석 (최근 30일)
python3 scripts/analyze_patterns.py

# 특정 프로젝트만
python3 scripts/analyze_patterns.py --project DAIOps

# JSON 출력
python3 scripts/analyze_patterns.py --json

# 최근 7일만
python3 scripts/analyze_patterns.py --days 7
```

## /optimize-me 연동

`/optimize-me` 실행 시 자동으로 수집된 패턴을 분석에 포함.
- 초기: 세션 전체 분석 (무거움)
- 이후: 훅 수집 데이터 우선 사용 (가벼움)
