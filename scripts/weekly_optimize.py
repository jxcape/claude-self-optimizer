"""
주간 최적화 통합 스크립트

1단계: 세션 수집 + 요약 추출 (Python)
2단계: Claude Code에게 분석 요청할 프롬프트 생성
3단계: 분석 결과 기반 제안 생성

핵심: Python은 데이터 준비만, 실제 분석은 Claude Code(LLM)가 수행
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any


# ============================================================
# 설정
# ============================================================

SESSION_SOURCE = Path.home() / "Library/Application Support/Claude/local-agent-mode-sessions"
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SESSIONS_DIR = DATA_DIR / "sessions"
ANALYSIS_DIR = DATA_DIR / "analysis"
PROPOSALS_DIR = DATA_DIR / "proposals"


# ============================================================
# 1단계: 세션 수집 + 요약 추출
# ============================================================

def collect_and_summarize_sessions(days: int = 7) -> Dict[str, Any]:
    """
    최근 N일간 세션을 수집하고 LLM 분석용 요약을 생성

    Returns:
        {
            "metadata": {...},
            "sessions": [
                {
                    "session_id": "...",
                    "project": "...",
                    "first_user_message": "...",
                    "last_user_message": "...",
                    "tools_used": ["Read", "Bash", ...],
                    "tool_sequence": ["Read", "Read", "Bash", "Edit", ...],
                    "message_count": 50,
                    "user_messages_sample": ["...", "...", ...]
                }
            ]
        }
    """
    print("=" * 60)
    print("1단계: 세션 수집 + 요약 추출")
    print("=" * 60)

    cutoff_date = datetime.now() - timedelta(days=days)

    summary = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "days_analyzed": days,
            "cutoff_date": cutoff_date.isoformat(),
        },
        "sessions": []
    }

    # 1. 먼저 이미 수집된 세션 확인 (data/sessions/)
    session_files = list(SESSIONS_DIR.glob("*.json"))
    if session_files:
        print(f"이미 수집된 세션 사용: {SESSIONS_DIR}")
        print(f"발견된 세션: {len(session_files)}개")
    else:
        # 2. 없으면 원본 위치에서 수집
        if not SESSION_SOURCE.exists():
            print(f"❌ 세션 디렉토리 없음: {SESSION_SOURCE}")
            return summary
        session_files = list(SESSION_SOURCE.glob("**/session.json"))
        print(f"원본에서 수집: {SESSION_SOURCE}")
        print(f"발견된 세션: {len(session_files)}개")

    for session_file in session_files:
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 날짜 필터링 (파일명 또는 데이터에서)
            session_date = None

            # 1. 파일명에서 날짜 추출 (2026-01-15_xxx.json 형식)
            filename = session_file.name
            if filename[:10].count("-") == 2:
                try:
                    session_date = datetime.strptime(filename[:10], "%Y-%m-%d")
                except ValueError:
                    pass

            # 2. 데이터에서 날짜 추출
            if not session_date:
                created_at = data.get("created_at", data.get("createdAt", 0))
                if isinstance(created_at, (int, float)) and created_at > 0:
                    session_date = datetime.fromtimestamp(created_at / 1000)
                elif isinstance(created_at, str):
                    try:
                        session_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    except ValueError:
                        pass

            # 날짜가 없거나 오래된 세션 건너뛰기
            if not session_date or session_date < cutoff_date:
                continue

            # 세션 요약 추출
            session_summary = extract_session_summary(data, session_file)
            if session_summary:
                summary["sessions"].append(session_summary)

        except Exception as e:
            print(f"  ⚠️ 파싱 실패: {session_file.name} - {e}")

    summary["metadata"]["total_sessions"] = len(summary["sessions"])
    print(f"✅ 수집된 세션: {len(summary['sessions'])}개")

    return summary


def extract_session_summary(data: Dict, session_file: Path) -> Dict[str, Any]:
    """세션에서 LLM 분석에 필요한 요약 추출"""

    messages = data.get("messages", [])
    if not messages:
        return None

    # 프로젝트 경로에서 도메인 추출
    project = data.get("project", str(session_file.parent))
    if "Projects" in project:
        parts = project.split("Projects/")
        if len(parts) > 1:
            project = parts[-1].split("/")[0]
        else:
            project = "Unknown"
    elif "gemmy" in project and "Projects" not in project:
        project = "Main"

    # 사용자 메시지 추출
    user_messages = []
    tool_sequence = []

    for msg in messages:
        msg_type = msg.get("type", "")
        inner = msg.get("message", {})
        content = inner.get("content", "")

        # 사용자 메시지
        if msg_type == "user":
            if isinstance(content, str) and content.strip():
                user_messages.append(content[:500])  # 최대 500자
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        text = c.get("text", "")[:500]
                        if text.strip():
                            user_messages.append(text)
                        break

        # 도구 사용 추출 (assistant 메시지의 content에서)
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tool_name = c.get("name", "Unknown")
                    tool_sequence.append(tool_name)

    if not user_messages:
        return None

    # 도구 사용 통계
    tool_counter = Counter(tool_sequence)

    return {
        "session_id": data.get("session_id", data.get("sessionId", "unknown")),
        "project": project,
        "created_at": data.get("created_at", data.get("createdAt")),
        "message_count": data.get("message_count", len(messages)),
        "first_user_message": user_messages[0] if user_messages else "",
        "last_user_message": user_messages[-1] if len(user_messages) > 1 else "",
        "user_messages_count": len(user_messages),
        "user_messages_sample": user_messages[:5],  # 처음 5개 메시지 샘플
        "tools_used": list(tool_counter.keys()),
        "tool_counts": dict(tool_counter),
        "tool_sequence_length": len(tool_sequence),
        "tool_sequence_sample": tool_sequence[:20],  # 처음 20개 도구 순서
    }


# ============================================================
# 2단계: LLM 분석용 프롬프트 생성
# ============================================================

def generate_analysis_prompt(summary: Dict) -> str:
    """
    Claude Code가 분석할 프롬프트 생성

    이 프롬프트를 Claude Code에 붙여넣으면 LLM이 실제로 분석함
    """

    sessions = summary.get("sessions", [])

    prompt = f"""# 세션 분석 요청

## 분석 대상
- 기간: 최근 {summary['metadata']['days_analyzed']}일
- 세션 수: {len(sessions)}개

## 세션 요약 데이터

```json
{json.dumps(sessions[:10], ensure_ascii=False, indent=2)}
```

## 분석 요청

위 세션 데이터를 분석하여 다음을 추출해주세요:

### 1. 사용자 성향 분석
- 질문 스타일 (간결 vs 상세, 맥락 포함 여부)
- 선호하는 응답 형식 (코드 중심 vs 설명 중심)
- 피드백 패턴 (긍정/부정/재시도 빈도)

### 2. 도구 사용 패턴
- 가장 많이 사용하는 도구 Top 5
- **의미있는 도구 시퀀스 패턴** (예: "Read → Grep → Edit" 패턴이 자주 나타남)
- 프로젝트/도메인별 도구 선호도 차이

### 3. 워크플로우 패턴
- 일반적인 작업 흐름 (계획 → 실행 → 검증?)
- 복잡한 작업 vs 단순 조회 비율
- 반복되는 실패 패턴이 있는지

### 4. CLAUDE.md 업데이트 제안
- 위 분석을 바탕으로 CLAUDE.md에 추가할 규칙 제안
- 구체적인 마크다운 형식으로 제안

## 출력 형식

분석 결과를 `data/analysis/{datetime.now().strftime('%Y-%m-%d')}_llm_analysis.md`에 저장해주세요.
"""

    return prompt


# ============================================================
# 3단계: 전체 통계 (Python으로 처리 가능한 부분)
# ============================================================

def generate_statistics(summary: Dict) -> Dict[str, Any]:
    """기본 통계 생성 (Rule-based, LLM 분석 전 참고용)"""

    sessions = summary.get("sessions", [])

    # 도구 통계
    all_tools = Counter()
    for s in sessions:
        all_tools.update(s.get("tool_counts", {}))

    # 프로젝트별 세션 수
    projects = Counter(s.get("project", "Unknown") for s in sessions)

    # 세션 크기 분포
    size_dist = {"small": 0, "medium": 0, "large": 0}
    for s in sessions:
        count = s.get("message_count", 0)
        if count < 10:
            size_dist["small"] += 1
        elif count < 50:
            size_dist["medium"] += 1
        else:
            size_dist["large"] += 1

    return {
        "total_sessions": len(sessions),
        "tool_usage": dict(all_tools.most_common(10)),
        "projects": dict(projects.most_common(5)),
        "session_size_distribution": size_dist,
    }


# ============================================================
# 메인 실행
# ============================================================

def main():
    print("\n" + "=" * 60)
    print("주간 최적화 시작")
    print("=" * 60 + "\n")

    # 디렉토리 생성
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)

    # 1단계: 세션 수집 + 요약
    summary = collect_and_summarize_sessions(days=7)

    # 요약 저장
    today = datetime.now().strftime("%Y-%m-%d")
    summary_file = ANALYSIS_DIR / f"{today}_session_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 세션 요약 저장: {summary_file}")

    # 2단계: 기본 통계 생성
    print("\n" + "=" * 60)
    print("2단계: 기본 통계 생성")
    print("=" * 60)

    stats = generate_statistics(summary)
    print(f"\n총 세션: {stats['total_sessions']}개")
    print(f"\n도구 사용 Top 5:")
    for tool, count in list(stats['tool_usage'].items())[:5]:
        print(f"  - {tool}: {count}회")
    print(f"\n프로젝트별 세션:")
    for project, count in stats['projects'].items():
        print(f"  - {project}: {count}개")

    # 3단계: LLM 분석 프롬프트 생성
    print("\n" + "=" * 60)
    print("3단계: LLM 분석 프롬프트 생성")
    print("=" * 60)

    prompt = generate_analysis_prompt(summary)
    prompt_file = ANALYSIS_DIR / f"{today}_analysis_prompt.md"
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"\n✅ 분석 프롬프트 저장: {prompt_file}")

    # 안내 메시지
    print("\n" + "=" * 60)
    print("다음 단계")
    print("=" * 60)
    print(f"""
📋 생성된 파일:
   1. {summary_file} (세션 요약 데이터)
   2. {prompt_file} (LLM 분석 프롬프트)

🔥 이제 Claude Code에서 다음을 실행하세요:

   방법 1: 프롬프트 파일 읽기
   > {prompt_file} 읽고 분석해줘

   방법 2: Skill 실행 (권장)
   > /analyze-sessions

Claude Code가 세션을 실제로 읽고 LLM으로 분석합니다.
Rule-based가 아닌 의미있는 패턴을 추출합니다.
""")


if __name__ == "__main__":
    main()
