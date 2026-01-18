"""
Pattern Classifier Module (V2 Smart Compression)

추출된 패턴을 Skill/Slash/Agent/CLAUDE.md로 분류하는 모듈

분류 기준:
- tool_sequence + 빈도 3+ → SKILL
- prompt_template + 빈도 3+ → SLASH_COMMAND
- complex_task + Task agent 사용 or 10+ turns → AGENT
- behavioral → CLAUDE_MD_RULE

스펙: SPECS/V2_SMART_COMPRESSION.md
입력: pattern_extractor.py 출력 형식
"""

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional


# ============================================================
# 설정
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PATTERNS_DIR = DATA_DIR / "analysis" / "patterns"
CLASSIFIED_DIR = DATA_DIR / "analysis" / "classified"

# 분류 임계값
MIN_SKILL_FREQUENCY = 3
MIN_SLASH_FREQUENCY = 3
HIGH_CONFIDENCE = 0.8
MEDIUM_CONFIDENCE = 0.6
HIGH_FREQUENCY = 5


# ============================================================
# Enum & 데이터 클래스
# ============================================================

class SuggestionType(Enum):
    """분류 결과 타입"""
    SKILL = "skill"
    SLASH_COMMAND = "slash_command"
    AGENT = "agent"
    CLAUDE_MD_RULE = "claude_md_rule"
    UNKNOWN = "unknown"


@dataclass
class Pattern:
    """pattern_extractor.py에서 추출된 패턴 (입력)"""
    id: str
    type: Literal["tool_sequence", "prompt_template", "behavioral"]
    pattern: str  # "Read → Edit → Bash" or "~해줘"
    frequency: int
    examples: List[str]
    confidence: float


@dataclass
class ClassifiedPattern:
    """분류된 패턴 (출력)"""
    pattern_id: str
    pattern_type: str  # tool_sequence, prompt_template, behavioral
    pattern: str
    frequency: int
    confidence: float
    suggestion_type: SuggestionType
    suggested_name: str  # 제안 이름 (예: "/commit", "refactor.md")
    reason: str  # 분류 이유
    priority: str = "P3"  # P1, P2, P3

    def to_dict(self) -> dict:
        result = asdict(self)
        result["suggestion_type"] = self.suggestion_type.value
        return result


# ============================================================
# 분류 함수
# ============================================================

def classify_pattern(pattern: Pattern) -> ClassifiedPattern:
    """
    단일 패턴 분류

    Rules:
    - tool_sequence + 빈도 3+ → SKILL
    - prompt_template + 빈도 3+ → SLASH_COMMAND
    - behavioral → CLAUDE_MD_RULE
    - Task agent 사용 or 10+ turns → AGENT
    """
    suggestion_type = SuggestionType.UNKNOWN
    reason = ""

    # 1. SKILL: 도구 시퀀스 반복 (빈도 3+)
    if pattern.type == "tool_sequence":
        if pattern.frequency >= MIN_SKILL_FREQUENCY:
            suggestion_type = SuggestionType.SKILL
            reason = f"도구 시퀀스 반복 ({pattern.frequency}회) - 자동화 가능"
        else:
            reason = f"도구 시퀀스지만 빈도 부족 ({pattern.frequency} < {MIN_SKILL_FREQUENCY})"

    # 2. AGENT: 복잡한 멀티스텝
    elif pattern.type == "complex_task":
        if uses_task_subagent(pattern) or has_many_turns(pattern):
            suggestion_type = SuggestionType.AGENT
            reason = "복잡한 탐색/멀티스텝 패턴 - 서브에이전트 필요"
        else:
            reason = "complex_task지만 에이전트 조건 미충족"

    # 3. SLASH_COMMAND: 프롬프트 템플릿 (빈도 3+)
    elif pattern.type == "prompt_template":
        if pattern.frequency >= MIN_SLASH_FREQUENCY:
            suggestion_type = SuggestionType.SLASH_COMMAND
            reason = f"프롬프트 템플릿 반복 ({pattern.frequency}회) - 명령어화 가능"
        else:
            reason = f"프롬프트 템플릿이지만 빈도 부족 ({pattern.frequency} < {MIN_SLASH_FREQUENCY})"

    # 4. CLAUDE_MD_RULE: 행동 규칙
    elif pattern.type == "behavioral":
        suggestion_type = SuggestionType.CLAUDE_MD_RULE
        reason = "일관된 행동 규칙 - CLAUDE.md에 추가 권장"

    # 신뢰도 재계산
    confidence = calculate_confidence(pattern, suggestion_type)

    # 제안 이름 생성
    suggested_name = generate_suggested_name(pattern, suggestion_type)

    return ClassifiedPattern(
        pattern_id=pattern.id,
        pattern_type=pattern.type,
        pattern=pattern.pattern,
        frequency=pattern.frequency,
        confidence=confidence,
        suggestion_type=suggestion_type,
        suggested_name=suggested_name,
        reason=reason,
    )


def uses_task_subagent(pattern: Pattern) -> bool:
    """Task 서브에이전트 사용 여부 확인"""
    pattern_lower = pattern.pattern.lower()
    examples_str = " ".join(pattern.examples).lower()

    return "task" in pattern_lower or "task(" in examples_str


def has_many_turns(pattern: Pattern) -> bool:
    """10턴 이상 세션 여부 확인"""
    # examples에서 턴 수 추출 시도
    for example in pattern.examples:
        match = re.search(r"(\d+)\s*턴", example)
        if match:
            turns = int(match.group(1))
            if turns >= 10:
                return True
    return False


# ============================================================
# 신뢰도 계산
# ============================================================

def calculate_confidence(pattern: Pattern, suggestion_type: SuggestionType) -> float:
    """
    신뢰도 계산 (0.0 ~ 1.0)

    요소:
    - 빈도 (높을수록 좋음)
    - 예시 다양성 (다양할수록 좋음)
    - 패턴 복잡도 (적절할수록 좋음)
    - 분류 타입과의 적합성
    """
    base_confidence = pattern.confidence

    # 분류 불가능한 경우
    if suggestion_type == SuggestionType.UNKNOWN:
        return min(base_confidence * 0.5, 0.3)

    # 빈도 보정 (3회 기준, 최대 20회까지)
    freq_score = min(pattern.frequency / 20, 1.0)

    # 예시 다양성 보정 (0~3개)
    example_score = min(len(pattern.examples) / 3, 1.0)

    # 복잡도 보정 (패턴 길이 기반)
    pattern_len = len(pattern.pattern)
    if 5 <= pattern_len <= 50:
        complexity_score = 1.0
    elif pattern_len < 5:
        complexity_score = 0.6
    else:
        complexity_score = 0.8

    # 타입별 가중치
    type_weights = {
        SuggestionType.SKILL: 0.3,
        SuggestionType.SLASH_COMMAND: 0.25,
        SuggestionType.AGENT: 0.25,
        SuggestionType.CLAUDE_MD_RULE: 0.2,
    }
    type_weight = type_weights.get(suggestion_type, 0.1)

    # 종합 신뢰도
    confidence = (
        base_confidence * 0.4 +
        freq_score * 0.25 +
        example_score * 0.15 +
        complexity_score * 0.1 +
        type_weight
    )

    return round(min(confidence, 1.0), 3)


# ============================================================
# 이름 생성
# ============================================================

def generate_suggested_name(pattern: Pattern, suggestion_type: SuggestionType) -> str:
    """
    분류에 맞는 제안 이름 생성

    예:
    - "Read → Edit → Bash" → "read-edit-bash.md"
    - "~해줘" 템플릿 → "/quick-task"
    - "커밋해줘" → "/commit"
    - 한글 프롬프트 선호 → "Output language: Korean"
    """
    if suggestion_type == SuggestionType.SKILL:
        return generate_skill_name(pattern)
    elif suggestion_type == SuggestionType.SLASH_COMMAND:
        return generate_slash_name(pattern)
    elif suggestion_type == SuggestionType.AGENT:
        return generate_agent_name(pattern)
    elif suggestion_type == SuggestionType.CLAUDE_MD_RULE:
        return generate_claude_md_name(pattern)
    else:
        return "unknown"


def generate_skill_name(pattern: Pattern) -> str:
    """Skill 이름 생성 (예: read-edit-bash.md)"""
    # "Read → Edit → Bash" → "read-edit-bash"
    tools = re.split(r"\s*→\s*", pattern.pattern)
    name_parts = [tool.lower().replace("(", "-").replace(")", "") for tool in tools]
    return "-".join(name_parts) + ".md"


def generate_slash_name(pattern: Pattern) -> str:
    """Slash Command 이름 생성 (예: /commit)"""
    pat = pattern.pattern

    # 키워드 패턴인 경우: "'커밋' 키워드" → "/commit"
    keyword_match = re.match(r"'(.+)'\s*키워드", pat)
    if keyword_match:
        keyword = keyword_match.group(1)
        return "/" + korean_to_english_command(keyword)

    # 접미사 패턴인 경우: "~해줘" → examples에서 추출
    if pat.startswith("~"):
        if pattern.examples:
            # 첫 번째 예시에서 핵심 동사 추출
            example = pattern.examples[0]
            return "/" + extract_command_from_example(example)
        return "/quick-task"

    # 접두사 패턴인 경우: "이 파일~" → "/file-action"
    if pat.endswith("~"):
        prefix = pat.rstrip("~").strip()
        return "/" + korean_to_english_command(prefix) + "-action"

    return "/custom-command"


def generate_agent_name(pattern: Pattern) -> str:
    """Agent 이름 생성 (예: code-reviewer)"""
    pat = pattern.pattern.lower()

    if "review" in pat or "리뷰" in pat:
        return "code-reviewer"
    elif "refactor" in pat or "리팩토링" in pat:
        return "code-refactorer"
    elif "explore" in pat or "탐색" in pat:
        return "code-explorer"
    elif "test" in pat or "테스트" in pat:
        return "test-runner"
    elif "debug" in pat or "디버그" in pat:
        return "debugger"
    else:
        return "custom-agent"


def generate_claude_md_name(pattern: Pattern) -> str:
    """CLAUDE.md 규칙 이름 생성"""
    pat = pattern.pattern

    if "한글" in pat or "korean" in pat.lower():
        return "Output language: Korean"
    elif "짧은" in pat or "short" in pat.lower():
        return "Prefer short sessions"
    elif "긴" in pat or "long" in pat.lower():
        return "Prefer detailed responses"
    elif "도구" in pat or "tool" in pat.lower():
        # 도구 이름 추출
        tool_match = re.search(r"(\w+)\s*도구", pat)
        if tool_match:
            tool = tool_match.group(1)
            return f"Prefer {tool} tool"
        return "Tool preference rule"
    else:
        return pat[:50]  # 패턴 자체를 규칙명으로


def korean_to_english_command(korean: str) -> str:
    """한글 키워드를 영문 명령어로 변환"""
    mapping = {
        "커밋": "commit",
        "푸시": "push",
        "테스트": "test",
        "빌드": "build",
        "배포": "deploy",
        "리팩토링": "refactor",
        "수정": "fix",
        "추가": "add",
        "삭제": "delete",
        "확인": "check",
        "분석": "analyze",
        "요약": "summarize",
        "정리": "organize",
        "이 파일": "file",
        "이거": "this",
        "여기": "here",
    }
    return mapping.get(korean, "action")


def extract_command_from_example(example: str) -> str:
    """예시에서 명령어 추출"""
    # "이 파일 리팩토링해줘..." → "refactor"
    keywords = ["리팩토링", "커밋", "테스트", "빌드", "수정", "분석", "요약", "확인", "추가"]

    for kw in keywords:
        if kw in example:
            return korean_to_english_command(kw)

    return "task"


# ============================================================
# 전체 분류
# ============================================================

def classify_all(patterns: dict) -> List[ClassifiedPattern]:
    """
    모든 패턴 분류

    Input: pattern_extractor.py 출력
        {
            "tool_sequences": [...],
            "prompt_templates": [...],
            "behavioral": [...]
        }

    Returns: 분류된 패턴 리스트
    """
    classified = []

    for category in ["tool_sequences", "prompt_templates", "behavioral"]:
        pattern_list = patterns.get(category, [])

        for p_data in pattern_list:
            # dict → Pattern 변환
            pattern = Pattern(
                id=p_data.get("id", ""),
                type=p_data.get("type", ""),
                pattern=p_data.get("pattern", ""),
                frequency=p_data.get("frequency", 0),
                examples=p_data.get("examples", []),
                confidence=p_data.get("confidence", 0.0),
            )

            result = classify_pattern(pattern)
            classified.append(result)

    return classified


# ============================================================
# 우선순위 정렬
# ============================================================

def prioritize(classified: List[ClassifiedPattern]) -> List[ClassifiedPattern]:
    """
    우선순위 정렬

    P1: 신뢰도 0.8+ AND 빈도 5+
    P2: 신뢰도 0.6+ AND 빈도 3+
    P3: 나머지
    """
    for pattern in classified:
        if pattern.confidence >= HIGH_CONFIDENCE and pattern.frequency >= HIGH_FREQUENCY:
            pattern.priority = "P1"
        elif pattern.confidence >= MEDIUM_CONFIDENCE and pattern.frequency >= MIN_SKILL_FREQUENCY:
            pattern.priority = "P2"
        else:
            pattern.priority = "P3"

    # 우선순위 → 신뢰도 → 빈도 순 정렬
    return sorted(
        classified,
        key=lambda p: (
            {"P1": 0, "P2": 1, "P3": 2}[p.priority],
            -p.confidence,
            -p.frequency,
        )
    )


# ============================================================
# 저장 함수
# ============================================================

def save_classified(
    classified: List[ClassifiedPattern],
    output_dir: str = str(CLASSIFIED_DIR)
) -> str:
    """
    분류 결과 JSON으로 저장

    Returns: 저장된 파일 경로
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / "classified_patterns.json"

    # 타입별 그룹화
    by_type = {
        "skill": [],
        "slash_command": [],
        "agent": [],
        "claude_md_rule": [],
        "unknown": [],
    }

    for pattern in classified:
        by_type[pattern.suggestion_type.value].append(pattern.to_dict())

    data = {
        "classified_at": datetime.now().isoformat(),
        "total_count": len(classified),
        "by_priority": {
            "P1": len([p for p in classified if p.priority == "P1"]),
            "P2": len([p for p in classified if p.priority == "P2"]),
            "P3": len([p for p in classified if p.priority == "P3"]),
        },
        "by_type": {
            "skill": len(by_type["skill"]),
            "slash_command": len(by_type["slash_command"]),
            "agent": len(by_type["agent"]),
            "claude_md_rule": len(by_type["claude_md_rule"]),
            "unknown": len(by_type["unknown"]),
        },
        "patterns": by_type,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return str(file_path)


# ============================================================
# 로드 함수
# ============================================================

def load_patterns(input_dir: str = str(PATTERNS_DIR)) -> dict:
    """
    패턴 파일들 로드

    Returns:
        {
            "tool_sequences": [...],
            "prompt_templates": [...],
            "behavioral": [...]
        }
    """
    input_path = Path(input_dir)
    patterns = {
        "tool_sequences": [],
        "prompt_templates": [],
        "behavioral": [],
    }

    if not input_path.exists():
        return patterns

    # 카테고리별 파일 로드
    for category in patterns.keys():
        file_path = input_path / f"{category}.json"
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    patterns[category] = data.get("patterns", [])
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}")

    return patterns


# ============================================================
# 테스트
# ============================================================

def run_test():
    """테스트 모드 실행"""
    print("=" * 60)
    print("Pattern Classifier Test Mode")
    print("=" * 60)

    # 테스트용 샘플 패턴
    sample_patterns = {
        "tool_sequences": [
            {
                "id": "tool_seq_1",
                "type": "tool_sequence",
                "pattern": "Read → Edit → Bash",
                "frequency": 10,
                "examples": ["[project1] Read → Edit → Bash", "[project2] Read → Edit → Bash"],
                "confidence": 0.5,
            },
            {
                "id": "tool_seq_2",
                "type": "tool_sequence",
                "pattern": "Grep → Read → Edit",
                "frequency": 5,
                "examples": ["[project1] Grep → Read → Edit"],
                "confidence": 0.3,
            },
            {
                "id": "tool_seq_3",
                "type": "tool_sequence",
                "pattern": "Read → Read",
                "frequency": 2,  # 빈도 부족
                "examples": [],
                "confidence": 0.1,
            },
        ],
        "prompt_templates": [
            {
                "id": "prompt_suffix_1",
                "type": "prompt_template",
                "pattern": "~해줘",
                "frequency": 15,
                "examples": ["이 파일 리팩토링해줘", "커밋해줘", "테스트 돌려줘"],
                "confidence": 0.6,
            },
            {
                "id": "prompt_keyword_1",
                "type": "prompt_template",
                "pattern": "'커밋' 키워드",
                "frequency": 7,
                "examples": ["커밋해줘", "커밋 메시지 작성해줘"],
                "confidence": 0.4,
            },
            {
                "id": "prompt_prefix_1",
                "type": "prompt_template",
                "pattern": "이 파일~",
                "frequency": 8,
                "examples": ["이 파일 분석해줘", "이 파일 수정해줘"],
                "confidence": 0.35,
            },
        ],
        "behavioral": [
            {
                "id": "behavioral_korean",
                "type": "behavioral",
                "pattern": "한글 프롬프트 선호",
                "frequency": 50,
                "examples": ["한글 사용 비율: 95.0%"],
                "confidence": 0.95,
            },
            {
                "id": "behavioral_tool_read",
                "type": "behavioral",
                "pattern": "Read 도구 자주 사용",
                "frequency": 30,
                "examples": ["전체 도구 사용 중 35.0%"],
                "confidence": 0.35,
            },
            {
                "id": "behavioral_session_length",
                "type": "behavioral",
                "pattern": "중간 세션 (8.5턴 평균)",
                "frequency": 20,
                "examples": ["평균 8.5턴, 총 20 세션 분석"],
                "confidence": 1.0,
            },
        ],
    }

    print(f"\n[1] Sample patterns loaded:")
    print(f"    Tool sequences: {len(sample_patterns['tool_sequences'])}")
    print(f"    Prompt templates: {len(sample_patterns['prompt_templates'])}")
    print(f"    Behavioral: {len(sample_patterns['behavioral'])}")

    # 분류 테스트
    print("\n[2] Classifying patterns...")
    classified = classify_all(sample_patterns)
    print(f"    Classified: {len(classified)} patterns")

    # 타입별 카운트
    type_counts = {}
    for p in classified:
        t = p.suggestion_type.value
        type_counts[t] = type_counts.get(t, 0) + 1

    print("\n[3] Classification results:")
    for t, count in type_counts.items():
        print(f"    {t}: {count}")

    # 우선순위 정렬 테스트
    print("\n[4] Prioritizing...")
    prioritized = prioritize(classified)

    priority_counts = {"P1": 0, "P2": 0, "P3": 0}
    for p in prioritized:
        priority_counts[p.priority] += 1

    print(f"    P1 (high): {priority_counts['P1']}")
    print(f"    P2 (medium): {priority_counts['P2']}")
    print(f"    P3 (low): {priority_counts['P3']}")

    # 상세 결과 출력
    print("\n[5] Classified patterns (by priority):")
    for p in prioritized:
        print(f"    [{p.priority}] {p.suggestion_type.value}: {p.pattern}")
        print(f"         → {p.suggested_name} (conf: {p.confidence:.2f})")
        print(f"         {p.reason}")

    # 저장 테스트
    print("\n[6] Saving classified patterns...")
    test_output = CLASSIFIED_DIR / "test"
    saved_path = save_classified(prioritized, str(test_output))
    print(f"    Saved to: {saved_path}")

    # 저장 결과 확인
    with open(saved_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        print(f"\n[7] Saved data summary:")
        print(f"    Total: {saved_data['total_count']}")
        print(f"    By priority: {saved_data['by_priority']}")
        print(f"    By type: {saved_data['by_type']}")

    print("\n" + "=" * 60)
    print("TEST PASSED")
    print("=" * 60)

    return True


# ============================================================
# 메인 실행
# ============================================================

def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description="Classify extracted patterns")
    parser.add_argument("--input", default=str(PATTERNS_DIR),
                        help="Input directory with pattern files")
    parser.add_argument("--output", default=str(CLASSIFIED_DIR),
                        help="Output directory for classified patterns")
    parser.add_argument("--test", action="store_true",
                        help="Run in test mode with sample data")

    args = parser.parse_args()

    if args.test:
        success = run_test()
        exit(0 if success else 1)

    # 패턴 로드
    print(f"Loading patterns from: {args.input}")
    patterns = load_patterns(args.input)

    total = sum(len(v) for v in patterns.values())
    if total == 0:
        print("No patterns found. Run pattern_extractor.py first, or use --test.")
        exit(1)

    print(f"Loaded: {total} patterns")
    print(f"  Tool sequences: {len(patterns['tool_sequences'])}")
    print(f"  Prompt templates: {len(patterns['prompt_templates'])}")
    print(f"  Behavioral: {len(patterns['behavioral'])}")

    # 분류
    print("\nClassifying patterns...")
    classified = classify_all(patterns)

    # 우선순위 정렬
    print("Prioritizing...")
    prioritized = prioritize(classified)

    # 결과 요약
    type_counts = {}
    priority_counts = {"P1": 0, "P2": 0, "P3": 0}

    for p in prioritized:
        t = p.suggestion_type.value
        type_counts[t] = type_counts.get(t, 0) + 1
        priority_counts[p.priority] += 1

    print("\nResults:")
    print("  By type:")
    for t, count in sorted(type_counts.items()):
        print(f"    {t}: {count}")
    print("  By priority:")
    print(f"    P1 (high): {priority_counts['P1']}")
    print(f"    P2 (medium): {priority_counts['P2']}")
    print(f"    P3 (low): {priority_counts['P3']}")

    # 상위 5개 출력
    print("\n--- Top 5 Suggestions ---")
    for p in prioritized[:5]:
        print(f"[{p.priority}] {p.suggestion_type.value}: {p.pattern}")
        print(f"    → {p.suggested_name}")
        print(f"    Confidence: {p.confidence:.2f}, Frequency: {p.frequency}")
        print(f"    Reason: {p.reason}")
        print()

    # 저장
    print(f"Saving to: {args.output}")
    saved_path = save_classified(prioritized, args.output)
    print(f"Saved: {saved_path}")


if __name__ == "__main__":
    main()
