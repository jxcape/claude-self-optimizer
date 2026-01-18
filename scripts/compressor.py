"""
Session Compressor Module (V2 Smart Compression)

세션 데이터를 분석용으로 압축하는 모듈
- 원본 세션 로드
- 도구별 압축 (핵심 param만 추출)
- 동적 수집 (크기 리미트 기반)

스펙: SPECS/V2_SMART_COMPRESSION.md
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import re


# ============================================================
# 설정
# ============================================================

SESSION_SOURCES = [
    Path.home() / ".claude/projects",  # CLI 세션 (주 저장소)
]
EXCLUDE_PATTERNS = ["agent-"]  # 서브에이전트 파일 제외

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"


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
    """
    경로를 축약
    /Users/xcape/gemmy/10_Projects/DAIOps/src/main.py
    → DAIOps/src/main.py
    """
    if not path:
        return ""

    parts = path.split("/")

    # Projects 이후 부분만 추출
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

    # MCP 도구 처리 (mcp__로 시작)
    if tool_name.startswith("mcp__"):
        # mcp__supabase__execute_sql → Supabase.execute_sql
        parts = tool_name.split("__")
        if len(parts) >= 3:
            return f"{parts[1]}.{parts[2]}"
        return tool_name.replace("mcp__", "")

    # 기타 도구
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
    - User 메시지: 전문 보존 (단, 시스템 태그 제외)
    - Claude 도구 호출: 도구명 + 핵심 param 요약
    - Claude 텍스트: 첫 100자 또는 생략
    """
    msg_type = msg.get("type")
    inner = msg.get("message", {})
    content = inner.get("content", "")

    if msg_type == "user":
        text = extract_text_from_content(content)
        # 시스템 태그 제거
        if text.startswith("<"):
            # <system-reminder> 등 제거
            text = re.sub(r"<[^>]+>.*?</[^>]+>", "", text, flags=re.DOTALL).strip()
        if not text or len(text) < 5:
            return None
        return f"U: {text}"

    elif msg_type == "assistant":
        tool_uses = []
        text_content = ""

        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict):
                    if c.get("type") == "tool_use":
                        tool_name = c.get("name", "Unknown")
                        params = c.get("input", {})
                        tool_uses.append(compress_tool_use(tool_name, params))
                    elif c.get("type") == "text":
                        text_content = c.get("text", "")
        elif isinstance(content, str):
            text_content = content

        parts = []
        if tool_uses:
            parts.append(" | ".join(tool_uses))
        if text_content and not tool_uses:
            # 도구 없이 텍스트만 있는 경우, 첫 100자
            parts.append(truncate(text_content, 100))

        if parts:
            return f"C: {' '.join(parts)}"

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

        # CLI 세션 (~/.claude/projects/)
        for project_dir in source.iterdir():
            if not project_dir.is_dir():
                continue

            for session_file in project_dir.glob("*.jsonl"):
                # 서브에이전트 파일 제외
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
    # 프로젝트명 추출
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

                    # timestamp 추출 (첫 번째 것 사용)
                    ts = entry.get("timestamp")
                    if ts and not created_at:
                        try:
                            created_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            created_at = created_at.replace(tzinfo=None)
                        except ValueError:
                            pass

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        return None

    # 날짜 필터
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
    Turns: {turns}

    ---
    U: {user_message}
    C: {tool1} | {tool2}
    ---
    """

    session_id = raw_session.get("session_id", "unknown")
    project = raw_session.get("project", "Unknown")
    messages = raw_session.get("messages", [])
    created_at = raw_session.get("created_at")

    # 메시지 압축
    compressed_lines = []
    user_count = 0

    for msg in messages:
        compressed = compress_message(msg)
        if compressed:
            compressed_lines.append(compressed)
            if compressed.startswith("U:"):
                user_count += 1

    # 제목 추출 (첫 번째 사용자 메시지에서)
    title = "Session"
    for line in compressed_lines:
        if line.startswith("U:"):
            title = truncate(line[3:], 50)
            break

    # 날짜 포맷
    date_str = created_at.strftime("%Y-%m-%d") if created_at else "Unknown"

    # 최종 압축 텍스트 생성
    header = f"# Session: {title} ({date_str})\n"
    header += f"Project: {project}\n"
    header += f"Turns: {user_count}\n"
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

def collect_for_analysis(limit_kb: int = 100, days: int = 30) -> List[CompressedSession]:
    """
    최신 세션부터 limit_kb에 맞춰 동적 수집

    Args:
        limit_kb: 목표 크기 (기본 100KB)
        days: 수집 기간 (기본 30일)

    Returns:
        압축된 세션 리스트 (최신순)
    """

    # 세션 로드 (최신순 정렬됨)
    raw_sessions = load_sessions(days=days)

    collected = []
    total_size = 0
    limit_bytes = limit_kb * 1024

    for raw_session in raw_sessions:
        compressed = compress_session(raw_session)

        # 리미트 초과 시 중단
        if total_size + compressed.size_bytes > limit_bytes:
            break

        collected.append(compressed)
        total_size += compressed.size_bytes

    return collected


def generate_analysis_input(sessions: List[CompressedSession]) -> str:
    """분석용 통합 텍스트 생성"""

    if not sessions:
        return "No sessions collected."

    total_turns = sum(s.turns for s in sessions)
    total_size = sum(s.size_bytes for s in sessions)

    header = f"""# Session Analysis Data
Sessions: {len(sessions)}
Total Turns: {total_turns}
Total Size: {total_size / 1024:.1f}KB
Period: {sessions[-1].created_at.strftime('%Y-%m-%d') if sessions[-1].created_at else 'Unknown'} ~ {sessions[0].created_at.strftime('%Y-%m-%d') if sessions[0].created_at else 'Unknown'}

"""

    body = "\n\n".join(s.compressed for s in sessions)

    return header + body


# ============================================================
# 메인 실행
# ============================================================

def run_test():
    """테스트 모드 실행"""

    print("=" * 60)
    print("Compressor Test Mode")
    print("=" * 60)

    # 1. 세션 로드 테스트
    print("\n[1] Loading sessions (7 days)...")
    raw_sessions = load_sessions(days=7)
    print(f"    Loaded: {len(raw_sessions)} sessions")

    if not raw_sessions:
        print("    No sessions found. Trying 30 days...")
        raw_sessions = load_sessions(days=30)
        print(f"    Loaded: {len(raw_sessions)} sessions")

    if not raw_sessions:
        print("    ERROR: No sessions found")
        return False

    # 2. 단일 세션 압축 테스트
    print("\n[2] Compressing single session...")
    sample = raw_sessions[0]
    compressed = compress_session(sample)
    print(f"    Session: {compressed.session_id[:20]}...")
    print(f"    Project: {compressed.project}")
    print(f"    Turns: {compressed.turns}")
    print(f"    Size: {compressed.size_bytes} bytes")
    print(f"    Preview (first 500 chars):")
    print("-" * 40)
    print(compressed.compressed[:500])
    print("-" * 40)

    # 3. 동적 수집 테스트
    print("\n[3] Dynamic collection (100KB limit)...")
    collected = collect_for_analysis(limit_kb=100, days=30)
    total_size = sum(s.size_bytes for s in collected)
    print(f"    Collected: {len(collected)} sessions")
    print(f"    Total size: {total_size / 1024:.2f}KB")

    # 4. 압축률 계산
    print("\n[4] Compression stats...")
    raw_sizes = []
    for s in raw_sessions[:len(collected)]:
        try:
            raw_size = Path(s.get("file_path", "")).stat().st_size
            raw_sizes.append(raw_size)
        except:
            pass

    if raw_sizes:
        raw_total = sum(raw_sizes)
        compression_ratio = (1 - total_size / raw_total) * 100 if raw_total > 0 else 0
        print(f"    Raw total: {raw_total / 1024:.2f}KB")
        print(f"    Compressed: {total_size / 1024:.2f}KB")
        print(f"    Compression: {compression_ratio:.1f}%")

    # 5. 분석 입력 생성 테스트
    print("\n[5] Generating analysis input...")
    analysis_input = generate_analysis_input(collected)
    print(f"    Total length: {len(analysis_input)} chars")

    print("\n" + "=" * 60)
    print("TEST PASSED")
    print("=" * 60)

    return True


def main():
    """메인 실행"""
    import sys

    if "--test" in sys.argv:
        success = run_test()
        sys.exit(0 if success else 1)

    # 기본 실행: 수집 및 압축 후 출력
    print("Collecting and compressing sessions...")

    limit_kb = 100
    days = 30

    # 인자 파싱
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--limit" and i < len(sys.argv) - 1:
            limit_kb = int(sys.argv[i + 1])
        elif arg == "--days" and i < len(sys.argv) - 1:
            days = int(sys.argv[i + 1])

    collected = collect_for_analysis(limit_kb=limit_kb, days=days)

    if not collected:
        print("No sessions collected.")
        sys.exit(1)

    # 결과 출력
    print(f"\nCollected {len(collected)} sessions ({sum(s.size_bytes for s in collected) / 1024:.1f}KB)")
    print("\n" + "-" * 60)

    analysis_input = generate_analysis_input(collected)
    print(analysis_input)


if __name__ == "__main__":
    main()
