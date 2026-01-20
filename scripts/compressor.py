"""
Session Compressor Module (V4 Simplified)

세션 데이터를 압축하는 모듈 (분석/분류 없음)
- 원본 세션 로드
- 도구별 압축 (핵심 param만 추출)
- 동적 수집 (크기 리미트 기반)

분석/판단은 LLM이 직접 수행
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable
import re


# ============================================================
# 설정
# ============================================================

SESSION_SOURCES = [
    Path.home() / ".claude/projects",  # CLI 세션 (주 저장소)
]
EXCLUDE_PATTERNS = ["agent-"]  # 서브에이전트 파일 제외


# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class CompressedSession:
    """압축된 세션 데이터"""
    session_id: str
    project: str
    turns: int
    compressed: str
    size_bytes: int
    created_at: Optional[datetime] = None


# ============================================================
# 유틸리티 함수
# ============================================================

def shorten_path(path: str, max_depth: int = 3) -> str:
    """경로 축약: /Users/xcape/gemmy/10_Projects/DAIOps/src/main.py → DAIOps/src/main.py"""
    if not path:
        return ""

    parts = path.split("/")

    if "Projects" in parts:
        idx = parts.index("Projects")
        parts = parts[idx + 1:]
    elif len(parts) > max_depth:
        parts = parts[-max_depth:]

    return "/".join(parts)


def truncate(text: str, max_len: int = 30) -> str:
    """텍스트 축약"""
    if not text:
        return ""
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def clean_user_message(text: str, max_len: int = 500) -> str:
    """
    사용자 메시지 정리
    - 복붙 패턴 제거 (코드블록, 테이블, Claude 마커)
    - 길면 첫 200자 + 마지막 200자만 유지 (실제 요청은 보통 끝에)
    """
    # 코드블록 제거
    text = re.sub(r"```[\s\S]*?```", "[code]", text)

    # 테이블 패턴 제거
    text = re.sub(r"^.*[┌┐└┘├┤┬┴┼─│].*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.MULTILINE)

    # Claude 출력 마커 제거
    text = re.sub(r"^.*[⏺✻⎿☒☐].*$", "", text, flags=re.MULTILINE)

    # 구분선 제거
    text = re.sub(r"^[-=]{3,}$", "", text, flags=re.MULTILINE)

    # 연속 빈 줄 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    text = text.strip()

    # 길면 첫 200자 + 마지막 200자만 (실제 요청은 끝에 있음)
    if len(text) > max_len:
        head = text[:200]
        tail = text[-200:]
        text = f"{head}\n[...]\n{tail}"

    return text


# ============================================================
# 도구별 압축 규칙
# ============================================================

COMPRESS_RULES: Dict[str, Callable[[Dict], str]] = {
    "Read": lambda p: f"Read: {shorten_path(p.get('file_path', ''))}",
    "Edit": lambda p: f"Edit: {shorten_path(p.get('file_path', ''))}",
    "Write": lambda p: f"Write: {shorten_path(p.get('file_path', ''))}",
    "Bash": lambda p: f"Bash: {truncate(p.get('command', ''), 40)}",
    "Grep": lambda p: f"Grep: \"{p.get('pattern', '')}\" in {shorten_path(p.get('path', ''), 2)}",
    "Glob": lambda p: f"Glob: {p.get('pattern', '')}",
    "Task": lambda p: f"Task({p.get('subagent_type', 'Unknown')})",
    "TodoWrite": lambda p: f"Todo: {len(p.get('todos', []))}개",
    "WebFetch": lambda p: f"WebFetch: {truncate(p.get('url', ''), 40)}",
    "WebSearch": lambda p: f"WebSearch: \"{truncate(p.get('query', ''), 30)}\"",
    "Skill": lambda p: f"Skill: {p.get('skill', '')}",
    "NotebookEdit": lambda p: f"NotebookEdit: {shorten_path(p.get('notebook_path', ''))}",
}


def compress_tool_use(tool_name: str, params: dict) -> str:
    """도구 사용을 압축 문자열로 변환"""
    if tool_name in COMPRESS_RULES:
        try:
            return COMPRESS_RULES[tool_name](params)
        except Exception:
            return f"{tool_name}: ..."

    # MCP 도구 처리 (mcp__supabase__execute_sql → Supabase.execute_sql)
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__")
        if len(parts) >= 3:
            return f"{parts[1]}.{parts[2]}"
        return tool_name.replace("mcp__", "")

    return tool_name


# ============================================================
# 메시지 압축
# ============================================================

def extract_text_from_content(content) -> str:
    """content에서 텍스트 추출"""
    if isinstance(content, str):
        return content.strip()
    elif isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                return c.get("text", "").strip()
    return ""


def compress_message(msg: dict) -> Optional[str]:
    """
    메시지를 압축 문자열로 변환
    - User 메시지: 원문 보존 (시스템 태그만 제거) - 요청 내용이 핵심
    - Claude 도구 호출: 도구명 + 핵심 param만
    - Claude 텍스트: 도구 호출 있으면 생략, 없으면 50자
    """
    msg_type = msg.get("type")
    inner = msg.get("message", {})
    content = inner.get("content", "")

    if msg_type == "user":
        text = extract_text_from_content(content)
        # 시스템 태그 제거
        if text.startswith("<"):
            text = re.sub(r"<[^>]+>.*?</[^>]+>", "", text, flags=re.DOTALL).strip()
        if not text or len(text) < 5:
            return None
        # 복붙 패턴 제거 (코드블록, 테이블, 긴 출력)
        text = clean_user_message(text)
        if not text or len(text) < 5:
            return None
        return f"U: {text}"

    elif msg_type == "assistant":
        tool_uses = []

        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tool_name = c.get("name", "Unknown")
                    params = c.get("input", {})
                    tool_uses.append(compress_tool_use(tool_name, params))

        # 도구 호출이 있으면 도구만 출력 (텍스트 생략)
        if tool_uses:
            return f"C: {' | '.join(tool_uses)}"

        # 도구 호출 없으면 텍스트 50자만
        text_content = ""
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    text_content = c.get("text", "")
                    break
        elif isinstance(content, str):
            text_content = content

        if text_content:
            return f"C: {truncate(text_content, 50)}"

    return None


# ============================================================
# 세션 로드
# ============================================================

def load_sessions(days: int = 7) -> List[dict]:
    """~/.claude/projects/ 에서 최근 N일 세션 로드"""

    cutoff_date = datetime.now() - timedelta(days=days)
    sessions = []

    for source in SESSION_SOURCES:
        if not source.exists():
            continue

        for project_dir in source.iterdir():
            if not project_dir.is_dir():
                continue

            for session_file in project_dir.glob("*.jsonl"):
                if any(pat in session_file.name for pat in EXCLUDE_PATTERNS):
                    continue

                session = load_single_session(session_file, cutoff_date)
                if session:
                    sessions.append(session)

    # 최신순 정렬
    sessions.sort(key=lambda s: s.get("created_at") or datetime.min, reverse=True)

    return sessions


def load_single_session(file_path: Path, cutoff_date: datetime) -> Optional[dict]:
    """단일 세션 파일 로드"""

    messages = []
    session_id = file_path.stem
    project_raw = file_path.parent.name
    project = project_raw.replace("-Users-xcape-", "").replace("-", "/")
    created_at = None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    messages.append(entry)

                    ts = entry.get("timestamp")
                    if ts and not created_at:
                        try:
                            created_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            created_at = created_at.replace(tzinfo=None)
                        except ValueError:
                            pass

                except json.JSONDecodeError:
                    continue

    except Exception:
        return None

    if created_at and created_at < cutoff_date:
        return None

    if not messages:
        return None

    return {
        "session_id": session_id,
        "project": project,
        "messages": messages,
        "created_at": created_at,
        "file_path": str(file_path),
    }


# ============================================================
# 세션 압축
# ============================================================

def compress_session(raw_session: dict) -> CompressedSession:
    """
    전체 세션을 압축 포맷으로 변환

    출력 포맷:
    # Session: {title} ({date})
    Project: {project}

    ---
    U: {user_message}
    C: {tool1} | {tool2}
    ---
    """

    session_id = raw_session.get("session_id", "unknown")
    project = raw_session.get("project", "Unknown")
    messages = raw_session.get("messages", [])
    created_at = raw_session.get("created_at")

    compressed_lines = []
    user_count = 0

    for msg in messages:
        compressed = compress_message(msg)
        if compressed:
            compressed_lines.append(compressed)
            if compressed.startswith("U:"):
                user_count += 1

    # 제목 추출 (첫 번째 사용자 메시지)
    title = "Session"
    for line in compressed_lines:
        if line.startswith("U:"):
            title = truncate(line[3:], 50)
            break

    date_str = created_at.strftime("%Y-%m-%d") if created_at else "Unknown"

    # 최종 압축 텍스트
    header = f"# Session: {title} ({date_str})\n"
    header += f"Project: {project}\n"
    header += "\n---\n"

    body = "\n".join(compressed_lines)

    compressed_text = header + body + "\n---\n"

    return CompressedSession(
        session_id=session_id,
        project=project,
        turns=user_count,
        compressed=compressed_text,
        size_bytes=len(compressed_text.encode("utf-8")),
        created_at=created_at,
    )


# ============================================================
# 동적 수집
# ============================================================

def collect_sessions(limit_kb: int = 100, days: int = 30) -> List[CompressedSession]:
    """최신 세션부터 limit_kb에 맞춰 수집"""

    raw_sessions = load_sessions(days=days)

    collected = []
    total_size = 0
    limit_bytes = limit_kb * 1024

    for raw_session in raw_sessions:
        compressed = compress_session(raw_session)

        if total_size + compressed.size_bytes > limit_bytes:
            break

        collected.append(compressed)
        total_size += compressed.size_bytes

    return collected


def generate_output(sessions: List[CompressedSession]) -> str:
    """압축된 세션들을 출력 텍스트로 변환"""
    if not sessions:
        return "No sessions collected."

    total_turns = sum(s.turns for s in sessions)
    total_size = sum(s.size_bytes for s in sessions)

    start_date = sessions[-1].created_at.strftime('%Y-%m-%d') if sessions[-1].created_at else 'Unknown'
    end_date = sessions[0].created_at.strftime('%Y-%m-%d') if sessions[0].created_at else 'Unknown'

    header = f"""# Compressed Sessions
Sessions: {len(sessions)}
Total Turns: {total_turns}
Size: {total_size / 1024:.1f}KB
Period: {start_date} ~ {end_date}

"""

    body = "\n\n".join(s.compressed for s in sessions)

    return header + body


# ============================================================
# 메인 실행
# ============================================================

def main():
    """메인 실행"""
    import sys

    limit_kb = 100
    days = 30

    # 인자 파싱
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--limit" and i + 1 < len(args):
            limit_kb = int(args[i + 1])
        elif arg == "--days" and i + 1 < len(args):
            days = int(args[i + 1])

    if "--test" in args:
        # 테스트 모드
        print("=" * 60)
        print("Compressor Test")
        print("=" * 60)

        raw = load_sessions(days=7)
        print(f"\n[1] Loaded: {len(raw)} sessions (7 days)")

        if raw:
            sample = compress_session(raw[0])
            print(f"\n[2] Sample compression:")
            print(f"    Project: {sample.project}")
            print(f"    Turns: {sample.turns}")
            print(f"    Size: {sample.size_bytes} bytes")

        collected = collect_sessions(limit_kb=100, days=30)
        total = sum(s.size_bytes for s in collected)
        print(f"\n[3] Collected: {len(collected)} sessions ({total / 1024:.1f}KB)")

        print("\n" + "=" * 60)
        print("TEST PASSED")
        return

    # 기본 실행
    collected = collect_sessions(limit_kb=limit_kb, days=days)

    if not collected:
        print("No sessions collected.")
        sys.exit(1)

    output = generate_output(collected)
    print(output)


if __name__ == "__main__":
    main()
