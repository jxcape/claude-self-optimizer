"""최근 7일간의 Claude Code 세션 목록 조회"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path


def get_recent_sessions(days=7):
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        print("Claude 세션 디렉토리를 찾을 수 없습니다.")
        return []

    cutoff = datetime.now() - timedelta(days=days)
    sessions = []

    for project_dir in claude_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # 프로젝트 경로 복원 (- → /)
        project_path = "/" + project_dir.name.replace("-", "/")

        for session_file in project_dir.glob("*.jsonl"):
            mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
            if mtime < cutoff:
                continue

            # 첫 번째 user 메시지에서 세션 정보 추출
            session_info = {
                "id": session_file.stem,
                "project": project_path,
                "modified": mtime,
                "size_kb": session_file.stat().st_size / 1024,
                "first_message": None,
                "version": None,
            }

            try:
                with open(session_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        if data.get("type") == "user" and not data.get("isMeta"):
                            msg = data.get("message", {}).get("content", "")
                            # 명령어 태그 제외한 실제 메시지 추출
                            if "<command-name>" not in msg and len(msg) < 200:
                                session_info["first_message"] = msg[:80]
                            session_info["version"] = data.get("version")
                            break
            except (json.JSONDecodeError, IOError):
                pass

            sessions.append(session_info)

    # 최근 수정순 정렬
    sessions.sort(key=lambda x: x["modified"], reverse=True)
    return sessions


def main():
    sessions = get_recent_sessions(days=7)

    if not sessions:
        print("최근 7일간 세션이 없습니다.")
        return

    print(f"{'=' * 80}")
    print(f"최근 7일간 Claude Code 세션 ({len(sessions)}개)")
    print(f"{'=' * 80}\n")

    for s in sessions:
        print(f"📁 {s['project']}")
        print(f"   ID: {s['id']}")
        print(f"   수정: {s['modified'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   크기: {s['size_kb']:.1f} KB")
        if s["first_message"]:
            print(f"   첫 메시지: {s['first_message']}...")
        print()


if __name__ == "__main__":
    main()
