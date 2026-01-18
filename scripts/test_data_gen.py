#!/usr/bin/env python3
"""
Mock 세션 데이터 생성기

패턴 추출 및 분류 테스트를 위한 테스트 데이터 생성.
4개 시나리오 x 5회 반복 = 최소 20개 세션 생성.
"""

import json
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


# 시나리오 정의
SCENARIOS = {
    "refactor": {
        "tools": ["Read", "Grep", "Edit", "Bash"],
        "prompts": [
            "이 파일 리팩토링해줘",
            "테스트 돌려봐",
            "중복 코드 정리해줘",
            "함수 분리해줘",
            "변수명 개선해줘",
        ],
        "repeat": 5,
        "project": "test-refactor-project",
        "description": "코드 리팩토링 작업",
    },
    "git_commit": {
        "tools": ["Bash", "Bash", "Bash"],  # git add, commit, push
        "prompts": [
            "커밋해줘",
            "푸시해줘",
            "변경사항 커밋하고 푸시해줘",
            "git status 보여줘",
        ],
        "repeat": 5,
        "project": "test-git-project",
        "description": "Git 커밋 작업",
    },
    "exploration": {
        "tools": ["Task", "Glob", "Grep", "Read"],
        "prompts": [
            "이 코드베이스 분석해줘",
            "어디서 에러 처리하는지 찾아봐",
            "이 프로젝트 구조 설명해줘",
            "main 함수 찾아줘",
            "의존성 파악해줘",
        ],
        "repeat": 5,
        "project": "test-exploration-project",
        "description": "코드베이스 탐색",
    },
    "bug_fix": {
        "tools": ["Read", "Edit", "Bash", "Edit", "Bash"],
        "prompts": [
            "이 버그 수정해줘",
            "에러 고쳐줘",
            "테스트 실패 원인 찾아줘",
            "이 이슈 해결해줘",
        ],
        "repeat": 5,
        "project": "test-bugfix-project",
        "description": "버그 수정 작업",
    },
}

# 도구별 Mock 입력/출력
TOOL_TEMPLATES = {
    "Read": {
        "input": {"file_path": "/src/main.py"},
        "output": "# main.py\ndef main():\n    print('Hello')\n",
    },
    "Grep": {
        "input": {"pattern": "def ", "path": "/src"},
        "output": "src/main.py:1:def main():\nsrc/utils.py:5:def helper():\n",
    },
    "Edit": {
        "input": {"file_path": "/src/main.py", "old_string": "Hello", "new_string": "World"},
        "output": "File edited successfully",
    },
    "Bash": {
        "input": {"command": "git status"},
        "output": "On branch main\nnothing to commit, working tree clean",
    },
    "Glob": {
        "input": {"pattern": "**/*.py"},
        "output": "/src/main.py\n/src/utils.py\n/tests/test_main.py",
    },
    "Task": {
        "input": {"description": "Analyze codebase structure"},
        "output": "Analysis complete. Found 15 Python files across 3 directories.",
    },
}


def generate_uuid() -> str:
    """UUID 생성"""
    return str(uuid.uuid4())


def generate_timestamp(base_time: datetime, offset_seconds: int = 0) -> str:
    """타임스탬프 생성 (ISO 형식)"""
    ts = base_time + timedelta(seconds=offset_seconds)
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def generate_tool_use_message(
    tool_name: str,
    parent_uuid: str,
    session_id: str,
    timestamp: datetime,
    cwd: str,
) -> Dict[str, Any]:
    """도구 사용 assistant 메시지 생성"""
    tool_id = f"toolu_{generate_uuid()[:24]}"
    template = TOOL_TEMPLATES.get(tool_name, TOOL_TEMPLATES["Bash"])

    return {
        "parentUuid": parent_uuid,
        "isSidechain": False,
        "userType": "external",
        "cwd": cwd,
        "sessionId": session_id,
        "version": "2.1.5",
        "gitBranch": "main",
        "message": {
            "model": "claude-sonnet-4-20250514",
            "id": f"msg_{generate_uuid()[:24]}",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": tool_name,
                    "input": template["input"],
                }
            ],
            "stop_reason": "tool_use",
            "usage": {
                "input_tokens": random.randint(500, 2000),
                "output_tokens": random.randint(100, 500),
            },
        },
        "type": "assistant",
        "uuid": generate_uuid(),
        "timestamp": generate_timestamp(timestamp),
        "tool_id": tool_id,  # 도구 결과 연결용
    }


def generate_tool_result_message(
    tool_name: str,
    tool_id: str,
    parent_uuid: str,
    session_id: str,
    timestamp: datetime,
    cwd: str,
) -> Dict[str, Any]:
    """도구 결과 user 메시지 생성"""
    template = TOOL_TEMPLATES.get(tool_name, TOOL_TEMPLATES["Bash"])

    return {
        "parentUuid": parent_uuid,
        "isSidechain": False,
        "userType": "external",
        "cwd": cwd,
        "sessionId": session_id,
        "version": "2.1.5",
        "gitBranch": "main",
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "tool_use_id": tool_id,
                    "type": "tool_result",
                    "content": template["output"],
                }
            ],
        },
        "uuid": generate_uuid(),
        "timestamp": generate_timestamp(timestamp),
    }


def generate_user_message(
    content: str,
    parent_uuid: Optional[str],
    session_id: str,
    timestamp: datetime,
    cwd: str,
) -> Dict[str, Any]:
    """사용자 메시지 생성"""
    return {
        "parentUuid": parent_uuid,
        "isSidechain": False,
        "userType": "external",
        "cwd": cwd,
        "sessionId": session_id,
        "version": "2.1.5",
        "gitBranch": "main",
        "type": "user",
        "message": {
            "role": "user",
            "content": content,
        },
        "uuid": generate_uuid(),
        "timestamp": generate_timestamp(timestamp),
    }


def generate_assistant_text_message(
    content: str,
    parent_uuid: str,
    session_id: str,
    timestamp: datetime,
    cwd: str,
) -> Dict[str, Any]:
    """어시스턴트 텍스트 응답 생성"""
    return {
        "parentUuid": parent_uuid,
        "isSidechain": False,
        "userType": "external",
        "cwd": cwd,
        "sessionId": session_id,
        "version": "2.1.5",
        "gitBranch": "main",
        "message": {
            "model": "claude-sonnet-4-20250514",
            "id": f"msg_{generate_uuid()[:24]}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": content}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": random.randint(500, 2000),
                "output_tokens": random.randint(100, 500),
            },
        },
        "type": "assistant",
        "uuid": generate_uuid(),
        "timestamp": generate_timestamp(timestamp),
    }


def generate_mock_session(scenario_name: str, index: int) -> Dict[str, Any]:
    """
    시나리오 기반 Mock 세션 생성

    Returns:
        {
            "session_id": "mock-refactor-001",
            "project": "test-project",
            "messages": [...],
            "created_at": "...",
            "last_updated": "...",
            "message_count": N,
        }
    """
    scenario = SCENARIOS[scenario_name]
    session_id = f"mock-{scenario_name}-{index:03d}"
    cwd = f"/Users/test/projects/{scenario['project']}"

    # 랜덤 시작 시간 (최근 7일 이내)
    base_time = datetime.now() - timedelta(days=random.randint(0, 6), hours=random.randint(0, 23))

    messages = []
    current_time = base_time
    last_uuid = None

    # 사용자 프롬프트 선택
    prompt = random.choice(scenario["prompts"])

    # 1. 초기 사용자 메시지
    user_msg = generate_user_message(prompt, last_uuid, session_id, current_time, cwd)
    messages.append(user_msg)
    last_uuid = user_msg["uuid"]
    current_time += timedelta(seconds=random.randint(1, 3))

    # 2. 도구 사용 시퀀스
    for tool_name in scenario["tools"]:
        # Assistant가 도구 호출
        tool_msg = generate_tool_use_message(tool_name, last_uuid, session_id, current_time, cwd)
        tool_id = tool_msg.pop("tool_id")  # 내부용 필드 제거
        messages.append(tool_msg)
        last_uuid = tool_msg["uuid"]
        current_time += timedelta(seconds=random.randint(1, 5))

        # 도구 결과
        result_msg = generate_tool_result_message(
            tool_name, tool_id, last_uuid, session_id, current_time, cwd
        )
        messages.append(result_msg)
        last_uuid = result_msg["uuid"]
        current_time += timedelta(seconds=random.randint(1, 3))

    # 3. 최종 Assistant 응답
    final_responses = [
        "작업이 완료되었습니다.",
        "요청하신 작업을 마쳤습니다.",
        "모든 변경사항이 적용되었습니다.",
        "완료했습니다. 다른 필요한 작업이 있으신가요?",
    ]
    final_msg = generate_assistant_text_message(
        random.choice(final_responses), last_uuid, session_id, current_time, cwd
    )
    messages.append(final_msg)

    return {
        "session_id": session_id,
        "project": cwd,
        "title": prompt[:50],
        "created_at": base_time.isoformat(),
        "last_updated": current_time.isoformat(),
        "message_count": len(messages),
        "file_size_kb": round(len(json.dumps(messages)) / 1024, 2),
        "version": "2.1.5",
        "messages": messages,
        "scenario": scenario_name,  # 메타데이터: 분류 검증용
    }


def generate_all_mock_sessions() -> List[Dict[str, Any]]:
    """모든 시나리오에 대해 Mock 세션 생성"""
    sessions = []

    for scenario_name, scenario in SCENARIOS.items():
        for i in range(1, scenario["repeat"] + 1):
            session = generate_mock_session(scenario_name, i)
            sessions.append(session)
            print(f"  Generated: {session['session_id']} ({len(session['messages'])} messages)")

    return sessions


def to_compressed_format(session: Dict[str, Any]) -> str:
    """
    compressor.py 출력 포맷과 동일하게 변환

    # Session: Mock-Refactor-001 (2026-01-18)
    Project: test-project
    Turns: 15

    ---
    U: 이 파일 리팩토링해줘
    C: Read: src/main.py | Edit: src/main.py
    ---
    """
    lines = []

    # 헤더
    session_id = session["session_id"]
    date = session["created_at"][:10]
    lines.append(f"# Session: {session_id} ({date})")
    lines.append(f"Project: {session['project']}")
    lines.append(f"Turns: {session['message_count']}")
    if session.get("scenario"):
        lines.append(f"Scenario: {session['scenario']}")
    lines.append("")
    lines.append("---")

    # 메시지 압축: 턴 단위로 묶기
    current_user_msg = None
    current_tools = []

    for msg in session["messages"]:
        msg_type = msg.get("type")
        content = msg.get("message", {}).get("content", "")

        if msg_type == "user":
            # tool_result인 경우 스킵 (도구 결과는 어시스턴트 턴의 일부)
            if isinstance(content, list):
                is_tool_result = any(c.get("type") == "tool_result" for c in content)
                if is_tool_result:
                    continue

            # 이전 턴 출력 (있으면)
            if current_user_msg is not None:
                lines.append(f"U: {current_user_msg}")
                if current_tools:
                    lines.append(f"C: {' | '.join(current_tools)}")
                lines.append("---")

            # 새 턴 시작
            if isinstance(content, str):
                current_user_msg = content[:80]
            else:
                current_user_msg = str(content)[:80]
            current_tools = []

        elif msg_type == "assistant":
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "tool_use":
                        tool_name = item.get("name", "Unknown")
                        tool_input = item.get("input", {})
                        # 파일 경로 등 주요 인자 추출
                        if "file_path" in tool_input:
                            path = Path(tool_input["file_path"]).name
                            current_tools.append(f"{tool_name}: {path}")
                        elif "pattern" in tool_input:
                            current_tools.append(f"{tool_name}: {tool_input['pattern']}")
                        elif "command" in tool_input:
                            cmd = tool_input["command"][:20]
                            current_tools.append(f"{tool_name}: {cmd}")
                        else:
                            current_tools.append(tool_name)
                    elif item.get("type") == "text":
                        text = item.get("text", "")[:50]
                        if text and not current_tools:
                            current_tools.append(f"[{text}...]")

    # 마지막 턴 출력
    if current_user_msg is not None:
        lines.append(f"U: {current_user_msg}")
        if current_tools:
            lines.append(f"C: {' | '.join(current_tools)}")
        lines.append("---")

    return "\n".join(lines)


def save_test_data(
    sessions: List[Dict[str, Any]],
    output_dir: str = "data/sessions/test/",
) -> None:
    """
    테스트 데이터 저장

    - raw/: 원본 JSON
    - compressed/: 압축 포맷 텍스트
    """
    base_dir = Path(__file__).parent.parent / output_dir
    raw_dir = base_dir / "raw"
    compressed_dir = base_dir / "compressed"

    # 디렉토리 생성
    raw_dir.mkdir(parents=True, exist_ok=True)
    compressed_dir.mkdir(parents=True, exist_ok=True)

    for session in sessions:
        session_id = session["session_id"]

        # Raw JSON 저장
        raw_path = raw_dir / f"{session_id}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

        # 압축 포맷 저장
        compressed_path = compressed_dir / f"{session_id}.txt"
        compressed = to_compressed_format(session)
        with open(compressed_path, "w", encoding="utf-8") as f:
            f.write(compressed)

    print(f"\nSaved {len(sessions)} sessions to {base_dir}")
    print(f"  - Raw JSON: {raw_dir}")
    print(f"  - Compressed: {compressed_dir}")

    # 인덱스 파일 생성
    index = {
        "generated_at": datetime.now().isoformat(),
        "total_sessions": len(sessions),
        "scenarios": {},
    }

    for scenario_name in SCENARIOS:
        scenario_sessions = [s for s in sessions if s.get("scenario") == scenario_name]
        index["scenarios"][scenario_name] = {
            "count": len(scenario_sessions),
            "session_ids": [s["session_id"] for s in scenario_sessions],
        }

    index_path = base_dir / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"  - Index: {index_path}")


def main() -> None:
    print("=" * 60)
    print("Mock Session Data Generator")
    print("=" * 60)
    print()

    print("Generating mock sessions...")
    sessions = generate_all_mock_sessions()

    print()
    print(f"Total sessions generated: {len(sessions)}")

    # 시나리오별 통계
    print("\nScenario breakdown:")
    for scenario_name in SCENARIOS:
        count = len([s for s in sessions if s.get("scenario") == scenario_name])
        print(f"  - {scenario_name}: {count} sessions")

    print()
    save_test_data(sessions)

    print()
    print("Done!")


if __name__ == "__main__":
    main()
