"""
최근 7일간의 Claude Code 세션 전체 수집 및 저장
"""

import json
import re
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

            # 세션 정보 추출
            session_info = {
                "id": session_file.stem,
                "project": project_path,
                "file_path": str(session_file),
                "modified": mtime,
                "size_kb": session_file.stat().st_size / 1024,
                "first_message": None,
                "version": None,
                "messages_count": 0,
            }

            # 파일 내용 파싱
            try:
                with open(session_file, "r") as f:
                    msg_count = 0
                    for line in f:
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        msg_count += 1

                        if data.get("type") == "user" and not data.get("isMeta"):
                            msg = data.get("message", {}).get("content", "")
                            # 명령어 태그 제외한 실제 메시지 추출
                            if (
                                "<command-name>" not in msg
                                and len(msg) < 200
                                and not session_info["first_message"]
                            ):
                                session_info["first_message"] = msg[:80]
                            session_info["version"] = data.get("version")

                    session_info["messages_count"] = msg_count
            except (json.JSONDecodeError, IOError):
                pass

            sessions.append(session_info)

    # 최근 수정순 정렬
    sessions.sort(key=lambda x: x["modified"], reverse=True)
    return sessions


def sanitize_filename(name):
    """파일명에 사용 가능한 문자열로 변환"""
    # 특수 문자 제거
    name = re.sub(r"[^\w\s-]", "", name)
    # 공백을 _로 변환
    name = re.sub(r"\s+", "_", name)
    # 길이 제한
    return name[:50]


def save_session_to_json(session, output_dir):
    """세션을 JSON 파일로 저장"""
    date_str = session["modified"].strftime("%Y-%m-%d")
    session_id = session["id"]
    project_safe = sanitize_filename(session["project"].replace("/", "_"))

    filename = f"{date_str}_{session_id}_{project_safe}.json"
    output_path = Path(output_dir) / filename

    # 원본 JSONL 파일 파싱
    try:
        with open(session["file_path"], "r") as f:
            messages = []
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                messages.append(data)
    except (json.JSONDecodeError, IOError) as e:
        print(f"   ❌ JSON 파싱 실패: {e}")
        return False

    # 가공된 데이터 구조
    session_data = {
        "session_id": session["id"],
        "project": session["project"],
        "title": session["first_message"] or "(No title)",
        "created_at": session["modified"].isoformat(),
        "last_updated": session["modified"].isoformat(),
        "message_count": session["messages_count"],
        "file_size_kb": round(session["size_kb"], 2),
        "version": session["version"],
        "messages": messages,
    }

    # JSON 파일로 저장
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ 저장됨: {filename}")
        return True
    except IOError as e:
        print(f"   ❌ 저장 실패: {e}")
        return False


def main():
    sessions = get_recent_sessions(days=7)

    if not sessions:
        print("최근 7일간 세션이 없습니다.")
        return

    print(f"\n{'=' * 80}")
    print(f"최근 7일간 Claude Code 세션 전체 저장 ({len(sessions)}개)")
    print(f"{'=' * 80}\n")

    # 출력 디렉토리 생성
    output_dir = Path("data/sessions")
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for i, s in enumerate(sessions, 1):
        print(f"\n[{i}/{len(sessions)}] {s['project']}")
        print(f"   ID: {s['id']}")
        print(f"   메시지: {s['messages_count']}개")
        print(f"   크기: {s['size_kb']:.1f} KB")

        # Warmup 세션 건너뛰기 (메시지가 3개 미만)
        if s["messages_count"] < 3:
            print(f"   ⏭️  건너뜀 (Warmup 세션)")
            skipped_count += 1
            continue

        if save_session_to_json(s, output_dir):
            success_count += 1
        else:
            fail_count += 1

    # 결과 요약
    print(f"\n{'=' * 80}")
    print("저장 결과 요약")
    print(f"{'=' * 80}")
    print(f"총 세션: {len(sessions)}개")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"건너뜀: {skipped_count}개")
    print(f"저장 경로: {output_dir.absolute()}")
    print()


if __name__ == "__main__":
    main()
