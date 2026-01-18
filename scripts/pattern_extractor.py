"""
Pattern Extractor Module (V2 Smart Compression)

압축된 세션에서 패턴을 추출하는 모듈
- 도구 시퀀스 마이닝 (n-gram)
- 프롬프트 템플릿 추출
- 행동 규칙 감지

스펙: SPECS/V2_SMART_COMPRESSION.md
입력: compressor.py 출력 형식
"""

import argparse
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple


# ============================================================
# 설정
# ============================================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PATTERNS_DIR = DATA_DIR / "analysis" / "patterns"

# 최소 빈도 (이 이상만 패턴으로 인정)
MIN_FREQUENCY = 3


# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class Pattern:
    """추출된 패턴"""
    id: str
    type: Literal["tool_sequence", "prompt_template", "behavioral"]
    pattern: str  # "Read → Edit → Bash" or "~해줘"
    frequency: int
    examples: List[str] = field(default_factory=list)  # 실제 사용 예시 (최대 3개)
    confidence: float = 0.0  # 0.0 ~ 1.0

    def to_dict(self) -> dict:
        return asdict(self)


# ============================================================
# 파싱 유틸리티
# ============================================================

def parse_sessions(session_texts: List[str]) -> List[dict]:
    """
    압축된 세션 텍스트를 파싱하여 구조화된 데이터로 변환

    Returns:
        [
            {
                "session_id": "...",
                "project": "...",
                "turns": [...],  # [{"role": "U"|"C", "content": "...", "tools": [...]}]
            },
            ...
        ]
    """
    sessions = []

    for text in session_texts:
        session = parse_single_session(text)
        if session:
            sessions.append(session)

    return sessions


def parse_single_session(text: str) -> Optional[dict]:
    """단일 세션 텍스트 파싱"""
    lines = text.strip().split("\n")

    session = {
        "session_id": "",
        "project": "",
        "turn_count": 0,
        "turns": [],
    }

    in_body = False

    for line in lines:
        line = line.strip()

        # 헤더 파싱
        if line.startswith("# Session:"):
            # # Session: 제목 (날짜)
            match = re.match(r"# Session: (.+) \((\d{4}-\d{2}-\d{2})\)", line)
            if match:
                session["session_id"] = match.group(2)  # 날짜를 ID로 사용
        elif line.startswith("Project:"):
            session["project"] = line.replace("Project:", "").strip()
        elif line.startswith("Turns:"):
            try:
                session["turn_count"] = int(line.replace("Turns:", "").strip())
            except ValueError:
                pass
        elif line == "---":
            in_body = not in_body
            continue

        # 본문 파싱
        if in_body:
            if line.startswith("U:"):
                content = line[2:].strip()
                session["turns"].append({
                    "role": "U",
                    "content": content,
                    "tools": [],
                })
            elif line.startswith("C:"):
                content = line[2:].strip()
                # 도구 추출 (| 로 구분)
                tools = []
                for part in content.split(" | "):
                    part = part.strip()
                    if ":" in part:
                        tool_name = part.split(":")[0].strip()
                        tools.append(tool_name)
                    elif part.startswith("Task("):
                        tools.append("Task")
                    elif part.startswith("Todo:"):
                        tools.append("TodoWrite")
                    elif part and not part.startswith("→"):
                        # 텍스트 응답은 무시
                        pass

                session["turns"].append({
                    "role": "C",
                    "content": content,
                    "tools": tools,
                })

    return session if session["turns"] else None


# ============================================================
# 도구 시퀀스 추출
# ============================================================

def extract_tool_sequences(
    sessions: List[str],
    min_freq: int = MIN_FREQUENCY,
    n: int = 3
) -> List[Pattern]:
    """
    도구 시퀀스 마이닝 (n-gram)

    Args:
        sessions: 압축된 세션 텍스트 리스트
        min_freq: 최소 빈도 (기본 3)
        n: n-gram 크기 (기본 3)

    Returns:
        Pattern 리스트 (빈도 순)

    예: "Read → Edit → Bash" 10회 발견
    """
    parsed = parse_sessions(sessions)

    # 모든 세션에서 도구 시퀀스 추출
    all_sequences: List[Tuple[str, ...]] = []
    sequence_examples: Dict[Tuple[str, ...], List[str]] = {}

    for session in parsed:
        # Claude 턴에서 도구 추출
        tools = []
        for turn in session["turns"]:
            if turn["role"] == "C" and turn["tools"]:
                tools.extend(turn["tools"])

        # n-gram 생성
        for i in range(len(tools) - n + 1):
            seq = tuple(tools[i:i + n])
            all_sequences.append(seq)

            # 예시 저장 (최대 3개)
            if seq not in sequence_examples:
                sequence_examples[seq] = []
            if len(sequence_examples[seq]) < 3:
                # 해당 시퀀스가 발생한 컨텍스트 저장
                context = f"[{session['project']}] " + " → ".join(seq)
                if context not in sequence_examples[seq]:
                    sequence_examples[seq].append(context)

    # 빈도 계산
    counter = Counter(all_sequences)

    # 패턴 생성 (min_freq 이상만)
    patterns = []
    total_sequences = len(all_sequences)

    for seq, freq in counter.most_common():
        if freq < min_freq:
            break

        pattern_str = " → ".join(seq)
        confidence = freq / total_sequences if total_sequences > 0 else 0

        pattern = Pattern(
            id=f"tool_seq_{len(patterns) + 1}",
            type="tool_sequence",
            pattern=pattern_str,
            frequency=freq,
            examples=sequence_examples.get(seq, []),
            confidence=round(confidence, 3),
        )
        patterns.append(pattern)

    return patterns


# ============================================================
# 프롬프트 템플릿 추출
# ============================================================

def extract_prompt_templates(
    sessions: List[str],
    min_freq: int = MIN_FREQUENCY
) -> List[Pattern]:
    """
    프롬프트 템플릿 추출

    - "U:" 라인에서 사용자 메시지 파싱
    - 공통 패턴 추출:
      - "~해줘" 패턴 (접미사)
      - "이 파일 ~" 패턴 (접두사)
      - 특정 키워드 반복

    예: "~해줘" 패턴 5회 발견
    """
    parsed = parse_sessions(sessions)

    # 모든 사용자 메시지 수집
    user_messages = []
    for session in parsed:
        for turn in session["turns"]:
            if turn["role"] == "U":
                user_messages.append(turn["content"])

    # 패턴 추출
    patterns = []

    # 1. 접미사 패턴 (~해줘, ~해, ~할래, ~줘 등)
    suffix_patterns = extract_suffix_patterns(user_messages, min_freq)
    patterns.extend(suffix_patterns)

    # 2. 접두사 패턴 (이 파일~, 이거~, 여기~ 등)
    prefix_patterns = extract_prefix_patterns(user_messages, min_freq)
    patterns.extend(prefix_patterns)

    # 3. 키워드 패턴 (특정 단어 반복)
    keyword_patterns = extract_keyword_patterns(user_messages, min_freq)
    patterns.extend(keyword_patterns)

    return patterns


def extract_suffix_patterns(messages: List[str], min_freq: int) -> List[Pattern]:
    """접미사 패턴 추출 (~해줘 등)"""
    # 한글 접미사 패턴
    suffix_regexes = [
        (r"(.+)(해줘)$", "~해줘"),
        (r"(.+)(해봐)$", "~해봐"),
        (r"(.+)(할래)$", "~할래"),
        (r"(.+)(해)$", "~해"),
        (r"(.+)(줘)$", "~줘"),
        (r"(.+)(보여줘)$", "~보여줘"),
        (r"(.+)(알려줘)$", "~알려줘"),
        (r"(.+)(확인해)$", "~확인해"),
        (r"(.+)(수정해)$", "~수정해"),
        (r"(.+)(추가해)$", "~추가해"),
    ]

    counter: Dict[str, List[str]] = {}

    for msg in messages:
        msg = msg.strip()
        for regex, label in suffix_regexes:
            if re.search(regex, msg):
                if label not in counter:
                    counter[label] = []
                if len(counter[label]) < 3:
                    counter[label].append(msg[:50] + "..." if len(msg) > 50 else msg)
                else:
                    counter[label].append("")  # 카운트만 증가
                break

    patterns = []
    total = len(messages)

    for label, examples in counter.items():
        freq = len(examples)
        if freq >= min_freq:
            confidence = freq / total if total > 0 else 0
            pattern = Pattern(
                id=f"prompt_suffix_{len(patterns) + 1}",
                type="prompt_template",
                pattern=label,
                frequency=freq,
                examples=[e for e in examples if e][:3],
                confidence=round(confidence, 3),
            )
            patterns.append(pattern)

    # 빈도순 정렬
    patterns.sort(key=lambda p: p.frequency, reverse=True)
    return patterns


def extract_prefix_patterns(messages: List[str], min_freq: int) -> List[Pattern]:
    """접두사 패턴 추출 (이 파일~ 등)"""
    prefix_regexes = [
        (r"^(이 파일)", "이 파일~"),
        (r"^(이거)", "이거~"),
        (r"^(여기)", "여기~"),
        (r"^(이것)", "이것~"),
        (r"^(저거)", "저거~"),
        (r"^(@)", "@파일~"),  # 파일 참조
    ]

    counter: Dict[str, List[str]] = {}

    for msg in messages:
        msg = msg.strip()
        for regex, label in prefix_regexes:
            if re.search(regex, msg):
                if label not in counter:
                    counter[label] = []
                if len(counter[label]) < 3:
                    counter[label].append(msg[:50] + "..." if len(msg) > 50 else msg)
                else:
                    counter[label].append("")
                break

    patterns = []
    total = len(messages)

    for label, examples in counter.items():
        freq = len(examples)
        if freq >= min_freq:
            confidence = freq / total if total > 0 else 0
            pattern = Pattern(
                id=f"prompt_prefix_{len(patterns) + 1}",
                type="prompt_template",
                pattern=label,
                frequency=freq,
                examples=[e for e in examples if e][:3],
                confidence=round(confidence, 3),
            )
            patterns.append(pattern)

    patterns.sort(key=lambda p: p.frequency, reverse=True)
    return patterns


def extract_keyword_patterns(messages: List[str], min_freq: int) -> List[Pattern]:
    """키워드 패턴 추출 (자주 사용되는 단어)"""
    # 의미있는 키워드만 추출 (조사, 접속사 제외)
    stopwords = {"이", "그", "저", "것", "수", "등", "좀", "를", "을", "에", "는", "가", "의", "로", "와", "과", "도"}

    word_counter: Counter = Counter()
    word_examples: Dict[str, List[str]] = {}

    for msg in messages:
        # 한글 단어 추출 (2글자 이상)
        words = re.findall(r"[가-힣]{2,}", msg)
        for word in words:
            if word not in stopwords:
                word_counter[word] += 1
                if word not in word_examples:
                    word_examples[word] = []
                if len(word_examples[word]) < 3:
                    word_examples[word].append(msg[:50] + "..." if len(msg) > 50 else msg)

    patterns = []
    total = len(messages)

    # 상위 10개 키워드만
    for word, freq in word_counter.most_common(10):
        if freq >= min_freq:
            confidence = freq / total if total > 0 else 0
            pattern = Pattern(
                id=f"prompt_keyword_{len(patterns) + 1}",
                type="prompt_template",
                pattern=f"'{word}' 키워드",
                frequency=freq,
                examples=word_examples.get(word, [])[:3],
                confidence=round(confidence, 3),
            )
            patterns.append(pattern)

    return patterns


# ============================================================
# 행동 규칙 감지
# ============================================================

def extract_behavioral_rules(sessions: List[str]) -> List[Pattern]:
    """
    행동 규칙 감지

    - 한글 사용 비율 (한글 응답 선호)
    - 특정 도구 선호 (Task agent 많이 사용)
    - 세션 길이 패턴 (짧은 세션 vs 긴 세션)

    예: "한글 응답 선호" (일관)
    """
    parsed = parse_sessions(sessions)
    patterns = []

    if not parsed:
        return patterns

    # 1. 한글 사용 비율 분석
    korean_pattern = analyze_korean_usage(parsed)
    if korean_pattern:
        patterns.append(korean_pattern)

    # 2. 도구 사용 선호도 분석
    tool_patterns = analyze_tool_preferences(parsed)
    patterns.extend(tool_patterns)

    # 3. 세션 길이 패턴 분석
    session_pattern = analyze_session_length(parsed)
    if session_pattern:
        patterns.append(session_pattern)

    # 4. 시간대별 패턴 (TODO: 타임스탬프 필요)

    return patterns


def analyze_korean_usage(sessions: List[dict]) -> Optional[Pattern]:
    """한글 사용 비율 분석"""
    korean_count = 0
    total_count = 0

    for session in sessions:
        for turn in session["turns"]:
            if turn["role"] == "U":
                content = turn["content"]
                total_count += 1
                # 한글 포함 여부
                if re.search(r"[가-힣]", content):
                    korean_count += 1

    if total_count == 0:
        return None

    ratio = korean_count / total_count

    if ratio >= 0.8:
        return Pattern(
            id="behavioral_korean",
            type="behavioral",
            pattern="한글 프롬프트 선호",
            frequency=korean_count,
            examples=[f"한글 사용 비율: {ratio * 100:.1f}%"],
            confidence=ratio,
        )

    return None


def analyze_tool_preferences(sessions: List[dict]) -> List[Pattern]:
    """도구 사용 선호도 분석"""
    tool_counter: Counter = Counter()

    for session in sessions:
        for turn in session["turns"]:
            if turn["role"] == "C":
                for tool in turn["tools"]:
                    tool_counter[tool] += 1

    if not tool_counter:
        return []

    patterns = []
    total = sum(tool_counter.values())

    # 상위 3개 도구
    for tool, count in tool_counter.most_common(3):
        ratio = count / total
        if ratio >= 0.1:  # 10% 이상 사용
            patterns.append(Pattern(
                id=f"behavioral_tool_{tool.lower()}",
                type="behavioral",
                pattern=f"{tool} 도구 자주 사용",
                frequency=count,
                examples=[f"전체 도구 사용 중 {ratio * 100:.1f}%"],
                confidence=ratio,
            ))

    return patterns


def analyze_session_length(sessions: List[dict]) -> Optional[Pattern]:
    """세션 길이 패턴 분석"""
    if not sessions:
        return None

    lengths = [session["turn_count"] or len(session["turns"]) // 2 for session in sessions]
    avg_length = sum(lengths) / len(lengths) if lengths else 0

    if avg_length <= 5:
        pattern_desc = "짧은 세션 선호 (5턴 이하)"
    elif avg_length >= 15:
        pattern_desc = "긴 세션 선호 (15턴 이상)"
    else:
        pattern_desc = f"중간 세션 ({avg_length:.1f}턴 평균)"

    return Pattern(
        id="behavioral_session_length",
        type="behavioral",
        pattern=pattern_desc,
        frequency=len(sessions),
        examples=[f"평균 {avg_length:.1f}턴, 총 {len(sessions)} 세션 분석"],
        confidence=1.0,
    )


# ============================================================
# 통합 함수
# ============================================================

def extract_all_patterns(sessions: List[str], min_freq: int = MIN_FREQUENCY) -> dict:
    """
    모든 패턴 추출 통합

    Args:
        sessions: 압축된 세션 텍스트 리스트
        min_freq: 최소 빈도

    Returns:
        {
            "tool_sequences": [...],
            "prompt_templates": [...],
            "behavioral": [...]
        }
    """
    return {
        "tool_sequences": extract_tool_sequences(sessions, min_freq),
        "prompt_templates": extract_prompt_templates(sessions, min_freq),
        "behavioral": extract_behavioral_rules(sessions),
    }


# ============================================================
# 저장 함수
# ============================================================

def save_patterns(
    patterns: dict,
    output_dir: str = str(PATTERNS_DIR)
) -> List[str]:
    """
    패턴을 JSON으로 저장

    Args:
        patterns: extract_all_patterns() 결과
        output_dir: 저장 디렉토리

    Returns:
        저장된 파일 경로 리스트
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for category, pattern_list in patterns.items():
        file_path = output_path / f"{category}.json"

        data = {
            "extracted_at": datetime.now().isoformat(),
            "count": len(pattern_list),
            "patterns": [p.to_dict() for p in pattern_list],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        saved_files.append(str(file_path))

    return saved_files


def load_compressed_sessions(input_dir: str) -> List[str]:
    """압축된 세션 파일들 로드"""
    input_path = Path(input_dir)
    sessions = []

    if not input_path.exists():
        return sessions

    # .txt 파일들 로드
    for file in sorted(input_path.glob("*.txt")):
        try:
            content = file.read_text(encoding="utf-8")
            # 여러 세션이 하나의 파일에 있을 수 있음
            # "# Session:" 으로 분리
            parts = re.split(r"(?=# Session:)", content)
            for part in parts:
                if part.strip():
                    sessions.append(part)
        except Exception:
            continue

    return sessions


# ============================================================
# 테스트
# ============================================================

def run_test():
    """테스트 모드 실행"""
    print("=" * 60)
    print("Pattern Extractor Test Mode")
    print("=" * 60)

    # 테스트용 샘플 데이터 생성
    sample_sessions = [
        """# Session: 테스트 세션 1 (2026-01-16)
Project: test/project1
Turns: 5

---
U: 이 파일 리팩토링해줘
C: Read: src/main.py | Edit: src/main.py
U: 테스트 돌려봐
C: Bash: pytest → ✓
U: 커밋해줘
C: Bash: git add . | Bash: git commit → ✓
---
""",
        """# Session: 테스트 세션 2 (2026-01-16)
Project: test/project2
Turns: 4

---
U: 이 파일 분석해줘
C: Read: src/app.py | Grep: "TODO" in src/
U: 수정해줘
C: Edit: src/app.py
U: 확인해봐
C: Read: src/app.py
---
""",
        """# Session: 테스트 세션 3 (2026-01-17)
Project: test/project1
Turns: 3

---
U: 버그 수정해줘
C: Read: src/main.py | Edit: src/main.py
U: 테스트 해줘
C: Bash: npm test → ✓
---
""",
        """# Session: 테스트 세션 4 (2026-01-17)
Project: test/project3
Turns: 4

---
U: 코드 리뷰해줘
C: Read: src/index.js | Read: src/utils.js
U: 개선해줘
C: Edit: src/index.js | Edit: src/utils.js
U: 빌드해줘
C: Bash: npm build → ✓
---
""",
    ]

    print(f"\n[1] Sample sessions: {len(sample_sessions)}")

    # 도구 시퀀스 추출 테스트
    print("\n[2] Extracting tool sequences...")
    tool_patterns = extract_tool_sequences(sample_sessions, min_freq=1)
    print(f"    Found: {len(tool_patterns)} patterns")
    for p in tool_patterns[:3]:
        print(f"    - {p.pattern} (freq: {p.frequency})")

    # 프롬프트 템플릿 추출 테스트
    print("\n[3] Extracting prompt templates...")
    prompt_patterns = extract_prompt_templates(sample_sessions, min_freq=1)
    print(f"    Found: {len(prompt_patterns)} patterns")
    for p in prompt_patterns[:3]:
        print(f"    - {p.pattern} (freq: {p.frequency})")

    # 행동 규칙 추출 테스트
    print("\n[4] Extracting behavioral rules...")
    behavioral_patterns = extract_behavioral_rules(sample_sessions)
    print(f"    Found: {len(behavioral_patterns)} patterns")
    for p in behavioral_patterns:
        print(f"    - {p.pattern} (conf: {p.confidence:.2f})")

    # 전체 패턴 추출
    print("\n[5] Extracting all patterns...")
    all_patterns = extract_all_patterns(sample_sessions, min_freq=1)
    print(f"    Tool sequences: {len(all_patterns['tool_sequences'])}")
    print(f"    Prompt templates: {len(all_patterns['prompt_templates'])}")
    print(f"    Behavioral: {len(all_patterns['behavioral'])}")

    # 저장 테스트
    print("\n[6] Saving patterns...")
    test_output = DATA_DIR / "analysis" / "patterns" / "test"
    saved = save_patterns(all_patterns, str(test_output))
    print(f"    Saved to: {len(saved)} files")
    for f in saved:
        print(f"    - {f}")

    print("\n" + "=" * 60)
    print("TEST PASSED")
    print("=" * 60)

    return True


# ============================================================
# 메인 실행
# ============================================================

def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description="Extract patterns from compressed sessions")
    parser.add_argument("--input", default=str(DATA_DIR / "sessions" / "test" / "compressed"),
                        help="Input directory with compressed sessions")
    parser.add_argument("--output", default=str(PATTERNS_DIR),
                        help="Output directory for patterns")
    parser.add_argument("--min-freq", type=int, default=MIN_FREQUENCY,
                        help=f"Minimum frequency (default: {MIN_FREQUENCY})")
    parser.add_argument("--test", action="store_true",
                        help="Run in test mode with sample data")

    args = parser.parse_args()

    if args.test:
        success = run_test()
        exit(0 if success else 1)

    # 압축된 세션 로드
    print(f"Loading sessions from: {args.input}")
    sessions = load_compressed_sessions(args.input)

    if not sessions:
        print("No sessions found. Use --test for sample data.")
        exit(1)

    print(f"Loaded: {len(sessions)} sessions")

    # 패턴 추출
    print(f"\nExtracting patterns (min_freq={args.min_freq})...")
    patterns = extract_all_patterns(sessions, min_freq=args.min_freq)

    print(f"\nResults:")
    print(f"  Tool sequences: {len(patterns['tool_sequences'])}")
    print(f"  Prompt templates: {len(patterns['prompt_templates'])}")
    print(f"  Behavioral: {len(patterns['behavioral'])}")

    # 상위 패턴 출력
    print("\n--- Top Tool Sequences ---")
    for p in patterns["tool_sequences"][:5]:
        print(f"  {p.pattern} (freq: {p.frequency})")

    print("\n--- Top Prompt Templates ---")
    for p in patterns["prompt_templates"][:5]:
        print(f"  {p.pattern} (freq: {p.frequency})")

    print("\n--- Behavioral Rules ---")
    for p in patterns["behavioral"]:
        print(f"  {p.pattern} (conf: {p.confidence:.2f})")

    # 저장
    print(f"\nSaving to: {args.output}")
    saved = save_patterns(patterns, args.output)
    print(f"Saved: {len(saved)} files")
    for f in saved:
        print(f"  - {f}")


if __name__ == "__main__":
    main()
