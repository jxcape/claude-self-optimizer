"""
전체 83개 세션 분석 - 사용자 패턴, 도구 사용, 도메인 추출
"""

import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any


def analyze_sessions():
    """모든 세션을 분석하여 사용자 패턴 추출"""
    sessions_dir = Path("data/sessions")

    if not sessions_dir.exists():
        print("세션 디렉토리를 찾을 수 없습니다.")
        return

    # 분석 결과 저장
    analysis_result = {
        "total_sessions": 0,
        "by_domain": defaultdict(lambda: {"count": 0, "sessions": []}),
        "by_question_type": defaultdict(int),
        "by_session_size": {"small": 0, "medium": 0, "large": 0},
        "tool_usage": Counter(),
        "user_signals": Counter(),
        "workflow_patterns": [],
        "sessions": [],
    }

    # 모든 세션 파일 읽기
    for session_file in sorted(sessions_dir.glob("*.json")):
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session = json.load(f)

            analysis_result["total_sessions"] += 1

            # 세션 크기 분류
            msg_count = session.get("message_count", 0)
            if msg_count < 10:
                analysis_result["by_session_size"]["small"] += 1
            elif msg_count < 50:
                analysis_result["by_session_size"]["medium"] += 1
            else:
                analysis_result["by_session_size"]["large"] += 1

            # 첫 메시지에서 질문 유형 추출
            first_message = ""
            messages = session.get("messages", [])
            for msg in messages:
                if msg.get("type") == "user":
                    inner = msg.get("message", {})
                    content = inner.get("content", "")
                    if isinstance(content, str):
                        first_message = content
                    elif isinstance(content, list):
                        # text 타입에서 텍스트 추출
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "text":
                                first_message = c.get("text", "")
                                break
                    break

            # 질문 유형 분석
            question_type = classify_question_type(first_message)
            analysis_result["by_question_type"][question_type] += 1

            # 프로젝트/도메인 추출
            project = session.get("project", "")
            domain = classify_domain(project)
            analysis_result["by_domain"][domain]["count"] += 1
            analysis_result["by_domain"][domain]["sessions"].append(
                {
                    "session_id": session.get("session_id"),
                    "title": session.get("title", ""),
                    "message_count": msg_count,
                    "first_message": first_message[:100],
                }
            )

            # 도구 사용 패턴 분석
            tool_patterns = extract_tool_patterns(messages)
            for tool, count in tool_patterns.items():
                analysis_result["tool_usage"][tool] += count

            # 사용자 신호 분석 (긍정/부정)
            user_signals = extract_user_signals(messages)
            for signal, count in user_signals.items():
                analysis_result["user_signals"][signal] += count

            # 워크플로우 패턴 추출
            workflow = extract_workflow_pattern(messages, first_message, tool_patterns)
            analysis_result["workflow_patterns"].append(workflow)

            # 세션 요약
            analysis_result["sessions"].append(
                {
                    "session_id": session.get("session_id"),
                    "project": project,
                    "domain": domain,
                    "title": session.get("title", ""),
                    "message_count": msg_count,
                    "question_type": question_type,
                    "tools_used": list(tool_patterns.keys()),
                }
            )

        except (json.JSONDecodeError, Exception) as e:
            print(f"   ❌ 파일 파싱 실패: {session_file.name} - {e}")

    return analysis_result


def classify_question_type(message: str) -> str:
    """질문 유형 분류"""
    message_lower = message.lower()

    # 상세한 질문
    if any(
        word in message_lower
        for word in ["상세히", "자세히", "어떻게", "설명해줘", "자세", "알려줘"]
    ):
        return "상세_질문"

    # 정보 조회
    if any(
        word in message_lower for word in ["확인", "어떻", "보여줘", "있어", "찾아"]
    ):
        return "정보_조회"

    # 구현 요청
    if any(
        word in message_lower for word in ["만들어줘", "구현", "써줘", "작성", "만들"]
    ):
        return "구현_요청"

    # 분석/탐색
    if any(
        word in message_lower for word in ["분석", "찾아줘", "탐색", "search", "grep"]
    ):
        return "분석_탐색"

    # 테스트/버그 수정
    if any(
        word in message_lower for word in ["테스트", "버그", "실패", "안되", "오류"]
    ):
        return "버그_수정"

    # 설치/환경설정
    if any(word in message_lower for word in ["설치", "설정", "환경", "세팅"]):
        return "설치_설정"

    # 일반 질문
    return "일반_질문"


def classify_domain(project: str) -> str:
    """프로젝트/도메인 분류"""
    project_lower = project.lower()

    # MLOps/LLMOps
    if any(
        word in project_lower
        for word in ["daiops", "llmops", "mlops", "agent", "orchestration"]
    ):
        return "LLMOps"

    # HWP/임베딩
    if any(word in project_lower for word in ["hwp", "embedding", "ingest", "ocr"]):
        return "HWP_Embedding"

    # RAG 프레임워크
    if any(word in project_lower for word in ["rag", "framework", "experiment"]):
        return "RAG_Framework"

    # 루틴/자동화
    if any(word in project_lower for word in ["agent", "workflow", "automation"]):
        return "Agent_Automation"

    # 테스트 정책
    if any(word in project_lower for word in ["test", "policy", "claude.md", "skill"]):
        return "Test_Policy"

    # 일반/메인
    if "/" in project and "projects" not in project_lower:
        return "Main_Workspace"

    return "Other"


def extract_tool_patterns(messages: List[Dict]) -> Dict[str, int]:
    """도구 사용 패턴 추출 (Claude Code 세션 구조에 맞게)"""
    tool_usage = defaultdict(int)

    for msg in messages:
        # 새로운 세션 구조: msg['message']['content']에 tool_use 포함
        inner = msg.get("message", {})
        content = inner.get("content", [])

        if not isinstance(content, list):
            continue

        for c in content:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                tool_name = c.get("name", "").lower()
                if tool_name:
                    tool_usage[tool_name] += 1

    # 비슷한 도구 그룹화
    grouped_tools = {}
    for tool, count in tool_usage.items():
        if tool in ["read", "readfile"]:
            grouped_tools["read"] = grouped_tools.get("read", 0) + count
        elif tool in ["grep", "rg", "ast_grep"]:
            grouped_tools["grep"] = grouped_tools.get("grep", 0) + count
        elif tool in ["bash", "run", "execute"]:
            grouped_tools["bash"] = grouped_tools.get("bash", 0) + count
        elif tool in ["write", "edit"]:
            grouped_tools["write"] = grouped_tools.get("write", 0) + count
        elif tool in ["glob"]:
            grouped_tools["glob"] = grouped_tools.get("glob", 0) + count
        elif tool in ["task"]:
            grouped_tools["task"] = grouped_tools.get("task", 0) + count
        elif tool in ["todowrite"]:
            grouped_tools["todowrite"] = grouped_tools.get("todowrite", 0) + count
        else:
            grouped_tools[tool] = grouped_tools.get(tool, 0) + count

    return grouped_tools


def extract_user_signals(messages: List[Dict]) -> Dict[str, int]:
    """사용자 신호(긍정/부정) 추출 (Claude Code 세션 구조에 맞게)"""
    signals = defaultdict(int)

    for msg in messages:
        if msg.get("type") != "user":
            continue

        inner = msg.get("message", {})
        raw_content = inner.get("content", "")

        # content가 string이면 그대로, list면 text 타입에서 추출
        if isinstance(raw_content, str):
            content = raw_content.lower()
        elif isinstance(raw_content, list):
            texts = []
            for c in raw_content:
                if isinstance(c, dict) and c.get("type") == "text":
                    texts.append(c.get("text", ""))
            content = " ".join(texts).lower()
        else:
            continue

        # 긍정 신호
        positive_signals = [
            "고마워",
            "잘했어",
            "좋아",
            "잘됐어",
            "좋았어",
            "완료",
            "성공",
            "옳",
        ]
        for sig in positive_signals:
            if sig in content:
                signals["positive"] += 1
                break

        # 부정 신호
        negative_signals = ["아니야", "틀렸어", "안되", "실패", "오류", "아니", "없어"]
        for sig in negative_signals:
            if sig in content:
                signals["negative"] += 1
                break

        # 재시도 신호
        retry_signals = ["다시", "다른", "또", "retry", "다시 시도"]
        for sig in retry_signals:
            if sig in content:
                signals["retry"] += 1
                break

        # 요청/질문 신호
        question_signals = ["?", "어떻게", "어떻", "설명", "방법", "방법은"]
        if any(sig in content for sig in question_signals):
            signals["question"] += 1

        # 명령/요청
        command_signals = ["@", "/", "실행", "만들어"]
        if any(sig in content for sig in command_signals):
            signals["command"] += 1

    return dict(signals)


def extract_workflow_pattern(
    messages: List[Dict], first_message: str, tools: Dict[str, int]
) -> Dict[str, Any]:
    """워크플로우 패턴 추출"""
    workflow = {
        "type": "unknown",
        "tools": list(tools.keys()),
        "estimated_stage": "unknown",
    }

    # 워크플로우 유형 분류
    first_msg_lower = first_message.lower()

    # 정보 조회형
    if any(word in first_msg_lower for word in ["확인", "보여줘", "어떻", "있어"]):
        workflow["type"] = "info_lookup"
        workflow["estimated_stage"] = "discovery"

    # 구현/개발형
    elif any(word in first_msg_lower for word in ["만들어줘", "구현", "작성", "써줘"]):
        workflow["type"] = "implementation"
        workflow["estimated_stage"] = "execution"

    # 분석/탐색형
    elif any(word in first_msg_lower for word in ["분석", "찾아", "탐색"]):
        workflow["type"] = "analysis"
        workflow["estimated_stage"] = "exploration"

    # 문제 해결형
    elif any(word in first_msg_lower for word in ["해결", "고쳐", "버그", "안되"]):
        workflow["type"] = "debugging"
        workflow["estimated_stage"] = "resolution"

    # 도구 기반 워크플로우 패턴
    if "read" in tools and "grep" in tools:
        workflow["pattern"] = "file_then_search"
    elif "bash" in tools and "grep" in tools:
        workflow["pattern"] = "command_then_search"
    elif "write" in tools and "bash" in tools:
        workflow["pattern"] = "modify_then_test"

    return workflow


def generate_analysis_report(analysis: Dict) -> str:
    """분석 리포트 생성"""
    report = []
    report.append("=" * 80)
    report.append("세션 분석 리포트")
    report.append(f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 80)
    report.append("")

    # 1. 전체 통계
    report.append("## 1. 전체 통계")
    report.append("")
    report.append(f"총 세션 수: {analysis['total_sessions']}")
    report.append(f"세션 크기 분포:")
    report.append(f"  - Small (<10 msg): {analysis['by_session_size']['small']}")
    report.append(f"  - Medium (10-50 msg): {analysis['by_session_size']['medium']}")
    report.append(f"  - Large (>50 msg): {analysis['by_session_size']['large']}")
    report.append("")

    # 2. 질문 유형 분석
    report.append("## 2. 질문 유형 분석")
    report.append("")
    for qtype, count in sorted(
        analysis["by_question_type"].items(), key=lambda x: x[1], reverse=True
    ):
        pct = (count / analysis["total_sessions"]) * 100
        bar = "█" * int(pct / 5)
        report.append(f"{qtype}: {count} ({pct:.1f}%) {bar}")
    report.append("")

    # 3. 도메인별 세션 분석
    report.append("## 3. 도메인별 세션")
    report.append("")
    for domain, data in sorted(
        analysis["by_domain"].items(), key=lambda x: x[1]["count"], reverse=True
    ):
        report.append(f"{domain}: {data['count']}개 세션")
        if len(data["sessions"]) > 0:
            sample = data["sessions"][0]
            report.append(f"  예시: {sample['title'][:50]}...")
    report.append("")

    # 4. 도구 사용 패턴 (Top 10)
    report.append("## 4. 도구 사용 패턴 (Top 10)")
    report.append("")
    for tool, count in analysis["tool_usage"].most_common(10):
        pct = (count / analysis["total_sessions"]) * 100
        report.append(f"{tool}: {count}회 ({pct:.1f}%)")
    report.append("")

    # 5. 사용자 신호 분석
    report.append("## 5. 사용자 신호 분석")
    report.append("")
    for signal, count in analysis["user_signals"].most_common():
        report.append(f"{signal}: {count}회")
    report.append("")

    # 6. 워크플로우 패턴
    report.append("## 6. 워크플로우 패턴")
    report.append("")
    workflow_counter = Counter([w["type"] for w in analysis["workflow_patterns"]])
    for wtype, count in workflow_counter.most_common():
        pct = (count / analysis["total_sessions"]) * 100
        report.append(f"{wtype}: {count}회 ({pct:.1f}%)")
    report.append("")

    # 7. 핵심 인사이트
    report.append("## 7. 핵심 인사이트")
    report.append("")

    # 가장 자주 쓰는 도구
    top_tools = analysis["tool_usage"].most_common(3)
    report.append(f"### 선호 도구")
    for tool, _ in top_tools:
        report.append(f"  - {tool}")
    report.append("")

    # 질문 유형
    top_question = max(analysis["by_question_type"].items(), key=lambda x: x[1])
    report.append(f"### 주요 질문 유형")
    report.append(f"  - {top_question[0]}: {top_question[1]}회")
    report.append("")

    # 사용자 피드백 성향
    if analysis["user_signals"]["positive"] > analysis["user_signals"]["negative"]:
        report.append("### 사용자 피드백 성향")
        report.append("  - 긍정 피드백이 더 많음 (성공 사례 많음)")
    elif analysis["user_signals"]["negative"] > analysis["user_signals"]["positive"]:
        report.append("### 사용자 피드백 성향")
        report.append("  - 부정 피드백이 더 많음 (실패 사례 많음)")
    else:
        report.append("### 사용자 피드백 성향")
        report.append("  - 긍정/부정 피드백이 비슷함")
    report.append("")

    # 8. 개선 제안
    report.append("## 8. 개선 제안")
    report.append("")

    # 도구 사용 패턴 기반
    if analysis["tool_usage"]["read"] > analysis["tool_usage"].get("grep", 0) * 2:
        report.append("### CLAUDE.md 업데이트 제안 1")
        report.append("**사용자 스타일**: 파일 먼저 읽고, 그 다음 grep")
        report.append("- grep보다 read 먼저 사용하는 패턴이 있음")
        report.append("- '파일 확인 후 검색' 워크플로우 추가 권장")
        report.append("")

    # 워크플로우 기반
    workflow_counter = Counter([w["type"] for w in analysis["workflow_patterns"]])
    if workflow_counter["info_lookup"] > workflow_counter["implementation"]:
        report.append("### CLAUDE.md 업데이트 제안 2")
        report.append("**빠른 정보 조회 패턴**: 정보 조회 > 구현")
        report.append("- 정보 조회형 세션이 구현형보다 많음")
        report.append("- 정보 조회 시 더 빠르고 간결하게 응답하도록 지시사항 추가")
        report.append("")

    # 도메인별 제안
    llmops_count = analysis["by_domain"].get("LLMOps", {}).get("count", 0)
    if llmops_count > 10:
        report.append("### 도메인별 최적화 제안: LLMOps")
        report.append("- LLMOps 관련 세션이 {llmops_count}개")
        report.append("- 이 도메인에서 에이전트 오케스트레이션 패턴 정리 필요")
        report.append("- '복잡한 작업 시 oracle 먼저 상담 후 위임' 지시사항 추가")
        report.append("")

    # 세션 크기 기반
    if analysis["by_session_size"]["large"] > analysis["by_session_size"]["medium"]:
        report.append("### 세션 크기 관찰")
        report.append("- Large 세션(>50 msg)이 Medium 세션보다 많음")
        report.append("- 복잡한 작업 위주")
        report.append("- 복잡한 작업 시 계획 후 위임 지시사항 강화")
        report.append("")

    return "\n".join(report)


def main():
    print("세션 분석 시작...\n")

    # 분석 실행
    analysis = analyze_sessions()

    # 리포트 생성
    report = generate_analysis_report(analysis)

    # 콘솔에 출력
    print(report)

    # 파일 저장
    output_dir = Path("data/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    report_file = output_dir / f"{today}_weekly_analysis.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    # JSON 데이터 저장
    json_file = output_dir / f"{today}_analysis_data.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2, default=list)

    print(f"\n\n리포트 저장됨: {report_file}")
    print(f"데이터 저장됨: {json_file}")


if __name__ == "__main__":
    main()
