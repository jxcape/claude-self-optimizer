"""
Self-Optimizer Core Module

/optimize-me 커맨드의 핵심 로직을 담당
- 세션 수집
- 패턴 분석용 데이터 준비
- Gap 분석용 데이터 준비
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Optional


# ============================================================
# 설정
# ============================================================

# Claude Code 세션 저장 경로
SESSION_SOURCES = [
    Path.home() / ".claude/projects",  # CLI 세션 (주 저장소)
    Path.home() / "Library/Application Support/Claude/local-agent-mode-sessions",  # VM 세션
]
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
SESSIONS_DIR = DATA_DIR / "sessions"
REPORTS_DIR = DATA_DIR / "reports"

# 제외 패턴
EXCLUDE_PATTERNS = ["agent-"]  # 서브에이전트 파일 제외


# ============================================================
# 설정 로드
# ============================================================

def load_config() -> Dict[str, Any]:
    """플러그인 설정에서 사용자 설정 로드"""
    config_file = PROJECT_ROOT / ".claude-plugin" / "user_config.json"

    default_config = {
        "analysis_days": 7,
        "auto_sync": True,
        "focus_areas": ["slash_commands", "claude_md", "workflows"]
    }

    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            default_config.update(user_config)

    return default_config


# ============================================================
# 세션 수집
# ============================================================

def collect_sessions(days: int = 7) -> List[Dict[str, Any]]:
    """최근 N일간 세션 수집 및 요약"""

    print(f"\n[Session Collection] Last {days} days")
    print("-" * 40)

    cutoff_date = datetime.now() - timedelta(days=days)
    sessions = []
    session_files = []

    # 모든 세션 소스에서 파일 수집
    for source in SESSION_SOURCES:
        if not source.exists():
            print(f"  Skip: {source.name} (not found)")
            continue

        # CLI 세션 (~/.claude/projects/)
        if ".claude/projects" in str(source):
            cli_count = 0
            for project_dir in source.iterdir():
                if not project_dir.is_dir():
                    continue
                for f in project_dir.glob("*.jsonl"):
                    # 서브에이전트 파일 제외
                    if any(pat in f.name for pat in EXCLUDE_PATTERNS):
                        continue
                    session_files.append(("cli", f))
                    cli_count += 1
            print(f"  Found {cli_count} CLI sessions in ~/.claude/projects/")
        else:
            # VM 세션 (audit.jsonl)
            vm_files = list(source.glob("**/audit.jsonl"))
            for f in vm_files:
                session_files.append(("vm", f))
            print(f"  Found {len(vm_files)} VM sessions")

    print(f"  Total: {len(session_files)} session files")

    for session_type, session_file in session_files:
        try:
            if session_type == "cli":
                summary = parse_cli_session(session_file, cutoff_date)
            else:
                summary = parse_audit_jsonl(session_file, cutoff_date)

            if summary:
                sessions.append(summary)

        except Exception as e:
            print(f"  Error parsing {session_file.name}: {e}")

    print(f"  Collected: {len(sessions)} sessions (after date filter)")
    return sessions


def parse_audit_jsonl(file_path: Path, cutoff_date: datetime) -> Optional[Dict]:
    """audit.jsonl 형식 파싱 (새로운 VM 기반 세션)"""

    messages = []
    tool_sequence = []
    user_messages = []
    session_id = None
    project = None
    created_at = None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    messages.append(entry)

                    entry_type = entry.get("type")

                    # 시스템 초기화에서 세션 정보 추출
                    if entry_type == "system" and entry.get("subtype") == "init":
                        session_id = entry.get("session_id")
                        cwd = entry.get("cwd", "")
                        if "/mnt/gemmy" in cwd or "Projects" in cwd:
                            project = cwd.split("/")[-1] if cwd else "Unknown"

                    # 사용자 메시지 추출
                    elif entry_type == "user":
                        msg = entry.get("message", {})
                        content = msg.get("content", "")
                        text = extract_text_from_content(content)
                        if text and len(text) > 10:  # 너무 짧은 메시지 제외
                            user_messages.append(text[:500])
                        if not created_at:
                            created_at = datetime.now()  # 첫 메시지 시간

                    # 도구 사용 추출
                    elif entry_type == "assistant":
                        msg = entry.get("message", {})
                        content = msg.get("content", [])
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "tool_use":
                                    tool_sequence.append(c.get("name", "Unknown"))

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        print(f"  Error reading {file_path}: {e}")
        return None

    if not user_messages:
        return None

    # 메타데이터 파일에서 추가 정보 가져오기
    meta_file = file_path.parent.parent / f"{file_path.parent.name}.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                session_id = session_id or meta.get("sessionId")
                created_at_ts = meta.get("createdAt", 0)
                if created_at_ts:
                    created_at = datetime.fromtimestamp(created_at_ts / 1000)
                project = project or meta.get("title", "Unknown")[:50]
        except:
            pass

    # 날짜 필터링
    if created_at and created_at < cutoff_date:
        return None

    return {
        "session_id": session_id or file_path.parent.name,
        "project": project or "Unknown",
        "message_count": len(messages),
        "user_messages": user_messages[:5],
        "first_message": user_messages[0] if user_messages else "",
        "tools_used": list(set(tool_sequence)),
        "tool_counts": dict(Counter(tool_sequence)),
        "tool_sequence": tool_sequence[:30],
    }


def parse_cli_session(file_path: Path, cutoff_date: datetime) -> Optional[Dict]:
    """CLI 세션 JSONL 파싱 (~/.claude/projects/{project}/{uuid}.jsonl)"""

    messages = []
    tool_sequence = []
    user_messages = []
    session_id = file_path.stem
    # 프로젝트명 추출: -Users-xcape-gemmy-10-Projects-DAIOps → gemmy/10_Projects/DAIOps
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
                    entry_type = entry.get("type")

                    # timestamp 추출 (첫 번째 것 사용)
                    ts = entry.get("timestamp")
                    if ts and not created_at:
                        try:
                            created_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except ValueError:
                            pass

                    # 사용자 메시지
                    if entry_type == "user":
                        msg = entry.get("message", {})
                        content = msg.get("content", "")
                        text = extract_text_from_content(content)
                        # 시스템 태그, 짧은 메시지 제외
                        if text and len(text) > 10 and not text.startswith("<"):
                            user_messages.append(text[:500])

                    # 도구 사용 (assistant 메시지)
                    elif entry_type == "assistant":
                        msg = entry.get("message", {})
                        content = msg.get("content", [])
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "tool_use":
                                    tool_sequence.append(c.get("name", "Unknown"))

                    messages.append(entry)
                except json.JSONDecodeError:
                    continue

    except Exception as e:
        print(f"  Error reading {file_path.name}: {e}")
        return None

    # 날짜 필터
    if created_at:
        # timezone aware → naive 변환
        created_naive = created_at.replace(tzinfo=None) if created_at.tzinfo else created_at
        if created_naive < cutoff_date:
            return None

    if not user_messages:
        return None

    return {
        "session_id": session_id,
        "project": project,
        "message_count": len(messages),
        "user_messages": user_messages[:5],
        "first_message": user_messages[0] if user_messages else "",
        "tools_used": list(set(tool_sequence)),
        "tool_counts": dict(Counter(tool_sequence)),
        "tool_sequence": tool_sequence[:30],
    }


def extract_session_date(data: Dict, session_file: Path) -> Optional[datetime]:
    """세션 날짜 추출"""
    # 파일명에서 추출
    filename = session_file.name
    if filename[:10].count("-") == 2:
        try:
            return datetime.strptime(filename[:10], "%Y-%m-%d")
        except ValueError:
            pass

    # 데이터에서 추출
    created_at = data.get("created_at", data.get("createdAt", 0))
    if isinstance(created_at, (int, float)) and created_at > 0:
        return datetime.fromtimestamp(created_at / 1000)
    elif isinstance(created_at, str):
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            pass

    return None


def extract_session_summary(data: Dict, session_file: Path) -> Optional[Dict]:
    """세션에서 분석에 필요한 요약 추출"""

    messages = data.get("messages", [])
    if not messages:
        return None

    # 프로젝트 추출
    project = data.get("project", str(session_file.parent))
    if "Projects" in project:
        parts = project.split("Projects/")
        project = parts[-1].split("/")[0] if len(parts) > 1 else "Unknown"

    # 사용자 메시지 및 도구 사용 추출
    user_messages = []
    tool_sequence = []

    for msg in messages:
        msg_type = msg.get("type", "")
        inner = msg.get("message", {})
        content = inner.get("content", "")

        # 사용자 메시지
        if msg_type == "user":
            text = extract_text_from_content(content)
            if text:
                user_messages.append(text[:500])

        # 도구 사용
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tool_sequence.append(c.get("name", "Unknown"))

    if not user_messages:
        return None

    return {
        "session_id": data.get("session_id", data.get("sessionId", "unknown")),
        "project": project,
        "message_count": len(messages),
        "user_messages": user_messages[:5],  # 처음 5개
        "first_message": user_messages[0],
        "tools_used": list(set(tool_sequence)),
        "tool_counts": dict(Counter(tool_sequence)),
        "tool_sequence": tool_sequence[:30],  # 처음 30개
    }


def extract_text_from_content(content) -> str:
    """content에서 텍스트 추출"""
    if isinstance(content, str):
        return content.strip()
    elif isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                return c.get("text", "").strip()
    return ""


# ============================================================
# 패턴 분석 데이터 준비
# ============================================================

def prepare_pattern_analysis(sessions: List[Dict]) -> Dict[str, Any]:
    """LLM 패턴 분석을 위한 데이터 준비"""

    # 전체 도구 사용 통계
    all_tools = Counter()
    for s in sessions:
        all_tools.update(s.get("tool_counts", {}))

    # 프로젝트별 세션 수
    projects = Counter(s.get("project", "Unknown") for s in sessions)

    # 도구 시퀀스 패턴 (3-gram)
    sequence_patterns = Counter()
    for s in sessions:
        seq = s.get("tool_sequence", [])
        for i in range(len(seq) - 2):
            pattern = f"{seq[i]} -> {seq[i+1]} -> {seq[i+2]}"
            sequence_patterns[pattern] += 1

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

    # 사용자 메시지 샘플 (분석용)
    message_samples = []
    for s in sessions[:10]:
        message_samples.extend(s.get("user_messages", [])[:2])

    return {
        "summary": {
            "total_sessions": len(sessions),
            "total_tool_calls": sum(all_tools.values()),
            "unique_tools": len(all_tools),
            "projects_count": len(projects),
        },
        "tool_usage": dict(all_tools.most_common(15)),
        "projects": dict(projects.most_common(5)),
        "sequence_patterns": dict(sequence_patterns.most_common(10)),
        "session_size_distribution": size_dist,
        "message_samples": message_samples[:20],
    }


# ============================================================
# Gap 분석 데이터 준비
# ============================================================

def prepare_gap_analysis(pattern_data: Dict, focus_areas: List[str]) -> Dict[str, Any]:
    """LLM Gap 분석을 위한 데이터 준비"""

    # Knowledge base 로드
    catalog_file = KNOWLEDGE_DIR / "catalog.json"
    if not catalog_file.exists():
        return {"error": "Knowledge base not found. Run /sync-knowledge first."}

    with open(catalog_file, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    gap_data = {
        "user_patterns": pattern_data,
        "available_resources": {},
        "focus_areas": focus_areas,
    }

    # 포커스 영역별 리소스 로드
    area_mapping = {
        "slash_commands": "slash_commands",
        "claude_md": "claude_md_patterns",
        "workflows": "workflows",
        "skills": "skills",
    }

    for area in focus_areas:
        kb_category = area_mapping.get(area, area)
        resources = catalog.get("categories", {}).get(kb_category, [])

        # 상세 정보 로드
        category_dir = KNOWLEDGE_DIR / kb_category
        if category_dir.exists():
            detailed = []
            for f in category_dir.glob("*.json"):
                if f.name.startswith("_"):
                    continue
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    detailed.extend(data.get("resources", []))
            gap_data["available_resources"][area] = detailed
        else:
            gap_data["available_resources"][area] = resources

    return gap_data


# ============================================================
# 리포트 생성
# ============================================================

def generate_analysis_prompt(pattern_data: Dict, gap_data: Dict) -> str:
    """LLM 분석용 프롬프트 생성"""

    prompt = f"""# Self-Optimization Analysis Request

## Your Usage Patterns (Last {pattern_data['summary']['total_sessions']} sessions)

### Tool Usage
```json
{json.dumps(pattern_data['tool_usage'], indent=2)}
```

### Common Sequences (3-gram patterns)
```json
{json.dumps(pattern_data['sequence_patterns'], indent=2)}
```

### Projects
```json
{json.dumps(pattern_data['projects'], indent=2)}
```

### Sample User Messages
```json
{json.dumps(pattern_data['message_samples'][:10], ensure_ascii=False, indent=2)}
```

## Available Best Practices

### Slash Commands ({len(gap_data['available_resources'].get('slash_commands', []))} available)
Focus on commands that match your usage patterns:
- Git/version control commands if you use git frequently
- Testing commands if you write tests
- Context loading if you do exploration

### CLAUDE.md Patterns ({len(gap_data['available_resources'].get('claude_md', []))} available)
Templates for different languages and domains.

### Workflows ({len(gap_data['available_resources'].get('workflows', []))} available)
Structured approaches like TDD, spec-driven development.

## Analysis Request

Based on the above data:

1. **Pattern Analysis**: What are the user's main workflows and habits?

2. **Gap Analysis**: Compare with best practices and identify:
   - Which slash commands would benefit this user most?
   - What CLAUDE.md rules should be added?
   - Which workflows could improve their process?

3. **Prioritized Recommendations**:
   - P1 (High impact, easy to adopt)
   - P2 (High impact, medium effort)
   - P3 (Nice to have)

4. **Concrete Suggestions**:
   For each recommendation, provide:
   - What: Specific command/rule/workflow
   - Why: How it matches their patterns
   - How: Implementation steps

Output as structured markdown suitable for user review.
"""

    return prompt


def save_report(pattern_data: Dict, gap_data: Dict, prompt: str) -> Path:
    """분석 리포트 저장"""

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    # 데이터 저장
    data_file = REPORTS_DIR / f"{today}_analysis_data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump({
            "pattern_data": pattern_data,
            "gap_data": {k: v for k, v in gap_data.items() if k != "available_resources"},
            "generated_at": datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)

    # 프롬프트 저장
    prompt_file = REPORTS_DIR / f"{today}_analysis_prompt.md"
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"\n[Report Saved]")
    print(f"  Data: {data_file}")
    print(f"  Prompt: {prompt_file}")

    return prompt_file


# ============================================================
# 메인 실행
# ============================================================

def run_optimization(days: int = None, dry_run: bool = False) -> Dict[str, Any]:
    """최적화 파이프라인 실행"""

    config = load_config()
    days = days or config["analysis_days"]
    focus_areas = config["focus_areas"]

    print("\n" + "=" * 60)
    print("Self-Optimizer")
    print("=" * 60)
    print(f"Analysis period: {days} days")
    print(f"Focus areas: {', '.join(focus_areas)}")

    # 1. 세션 수집
    sessions = collect_sessions(days)

    if not sessions:
        return {"error": "No sessions found", "sessions": 0}

    # 2. 패턴 분석 데이터 준비
    print("\n[Preparing Pattern Analysis]")
    pattern_data = prepare_pattern_analysis(sessions)
    print(f"  Total tool calls: {pattern_data['summary']['total_tool_calls']}")
    print(f"  Top tools: {', '.join(list(pattern_data['tool_usage'].keys())[:5])}")

    # 3. Gap 분석 데이터 준비
    print("\n[Preparing Gap Analysis]")
    gap_data = prepare_gap_analysis(pattern_data, focus_areas)

    if "error" in gap_data:
        print(f"  Error: {gap_data['error']}")
        return gap_data

    for area, resources in gap_data.get("available_resources", {}).items():
        print(f"  {area}: {len(resources)} resources available")

    # 4. 분석 프롬프트 생성
    print("\n[Generating Analysis Prompt]")
    prompt = generate_analysis_prompt(pattern_data, gap_data)

    # 5. 리포트 저장
    prompt_file = save_report(pattern_data, gap_data, prompt)

    if dry_run:
        print("\n[Dry Run] Skipping LLM analysis")
        return {
            "status": "dry_run",
            "sessions": len(sessions),
            "prompt_file": str(prompt_file),
        }

    print("\n" + "=" * 60)
    print("Next Step")
    print("=" * 60)
    print(f"""
The analysis data is ready. Now run the LLM analysis:

Option 1: Read the prompt file
  > Read {prompt_file} and analyze

Option 2: Run /optimize-me in Claude Code
  This will run the full pipeline including LLM analysis

The LLM will:
1. Analyze your usage patterns
2. Compare with best practices
3. Generate personalized recommendations
""")

    return {
        "status": "ready",
        "sessions": len(sessions),
        "pattern_summary": pattern_data["summary"],
        "prompt_file": str(prompt_file),
    }


# ============================================================
# V2: Smart Compression Pipeline
# ============================================================

def run_optimization_v2(days: int = 7, limit_kb: int = 100, dry_run: bool = False) -> Dict[str, Any]:
    """V2 최적화 파이프라인 - Smart Compression 기반"""

    from compressor import collect_for_analysis
    from pattern_extractor import extract_all_patterns, save_patterns
    from classifier import classify_all, prioritize, save_classified
    from generate_proposals import load_classified, generate_from_classified, save_proposals_v2

    print("\n" + "=" * 60)
    print("Self-Optimizer V2 (Smart Compression)")
    print("=" * 60)
    print(f"Analysis period: {days} days")
    print(f"Size limit: {limit_kb}KB")

    # 1. 스마트 압축으로 세션 수집
    print("\n[Step 1] Collecting & Compressing Sessions...")
    compressed_sessions = collect_for_analysis(limit_kb=limit_kb, days=days)

    if not compressed_sessions:
        return {"error": "No sessions found", "sessions": 0}

    total_size = sum(s.size_bytes for s in compressed_sessions)
    print(f"  Collected: {len(compressed_sessions)} sessions ({total_size / 1024:.1f}KB)")

    # 압축 텍스트 생성
    compressed_texts = [s.compressed for s in compressed_sessions]

    # 2. 패턴 추출
    print("\n[Step 2] Extracting Patterns...")
    patterns = extract_all_patterns(compressed_texts)
    total_patterns = sum(len(v) for v in patterns.values())
    print(f"  Found: {total_patterns} patterns")
    print(f"    - Tool sequences: {len(patterns.get('tool_sequences', []))}")
    print(f"    - Prompt templates: {len(patterns.get('prompt_templates', []))}")
    print(f"    - Behavioral: {len(patterns.get('behavioral', []))}")

    # 패턴 저장
    patterns_dir = DATA_DIR / "analysis" / "patterns"
    save_patterns(patterns, str(patterns_dir))

    # 3. 분류
    print("\n[Step 3] Classifying Patterns...")
    classified = classify_all(patterns)
    classified = prioritize(classified)

    # 분류 저장
    classified_dir = DATA_DIR / "analysis" / "classified"
    save_classified(classified, str(classified_dir))

    # 우선순위별 카운트
    p1 = len([c for c in classified if c.priority == "P1"])
    p2 = len([c for c in classified if c.priority == "P2"])
    p3 = len([c for c in classified if c.priority == "P3"])
    print(f"  Classified: {len(classified)} suggestions")
    print(f"    - P1 (high): {p1}")
    print(f"    - P2 (medium): {p2}")
    print(f"    - P3 (low): {p3}")

    if dry_run:
        print("\n[Dry Run] Skipping proposal generation")
        return {
            "status": "dry_run",
            "version": "v2",
            "sessions": len(compressed_sessions),
            "patterns": total_patterns,
            "suggestions": len(classified),
        }

    # 4. 제안 생성
    print("\n[Step 4] Generating Proposals...")
    suggestions = generate_from_classified(classified)
    report_path = save_proposals_v2(suggestions)
    print(f"  Saved: {report_path}")

    # 5. 요약 출력
    print("\n" + "=" * 60)
    print("V2 Optimization Complete!")
    print("=" * 60)
    print(f"""
Sessions analyzed: {len(compressed_sessions)}
Patterns found: {total_patterns}
Suggestions generated: {len(suggestions)}
  - P1 (apply now): {p1}
  - P2 (consider): {p2}
  - P3 (later): {p3}

Report: {report_path}

Next steps:
1. Review the proposals in the report
2. Select which to apply
3. Run with --apply flag or manually apply
""")

    return {
        "status": "complete",
        "version": "v2",
        "sessions": len(compressed_sessions),
        "patterns": total_patterns,
        "suggestions": len(suggestions),
        "report": str(report_path),
        "priority_summary": {"P1": p1, "P2": p2, "P3": p3},
    }


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv
    use_v2 = "--v2" in sys.argv

    if use_v2:
        # V2 파이프라인
        days = 7
        limit_kb = 100

        # --days N 파싱
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            if idx + 1 < len(sys.argv):
                days = int(sys.argv[idx + 1])

        # --limit N 파싱
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            if idx + 1 < len(sys.argv):
                limit_kb = int(sys.argv[idx + 1])

        result = run_optimization_v2(days=days, limit_kb=limit_kb, dry_run=dry_run)
    else:
        # V1 파이프라인 (기존)
        result = run_optimization(dry_run=dry_run)

    print(f"\nResult: {json.dumps(result, indent=2)}")
