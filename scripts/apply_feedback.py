"""
피드백 적용 스크립트: 승인된 제안을 CLAUDE.md/Skill에 적용
"""

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def load_proposals() -> List[Tuple[Path, str]]:
    """제안 파일 로드"""
    proposals_dir = Path("data/proposals")

    if not proposals_dir.exists():
        print("제안 디렉토리를 찾을 수 없습니다.")
        return []

    proposals = []
    for proposal_file in sorted(proposals_dir.glob("*.md"), reverse=True):
        with open(proposal_file, "r", encoding="utf-8") as f:
            content = f.read()
        proposals.append((proposal_file, content))

    return proposals


def check_approval(content: str) -> Tuple[bool, str]:
    """피드백에서 승인 여부 확인"""
    # [x] 바로 적용 또는 [x] 적용 패턴 찾기
    approved_patterns = [
        r"\[x\]\s*바로 적용",
        r"\[x\]\s*적용",
        r"\[x\]\s*바로 생성",
        r"\[x\]\s*생성",
        r"status:\s*approved",
        r"status:\s*ready",
    ]

    for pattern in approved_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True, "approved"

    # [x] 수정 후 적용
    if re.search(r"\[x\]\s*수정 후 적용", content, re.IGNORECASE):
        return True, "modified"

    # 거부됨
    if re.search(r"\[x\]\s*적용 안 함", content, re.IGNORECASE):
        return False, "rejected"
    if re.search(r"\[x\]\s*거부", content, re.IGNORECASE):
        return False, "rejected"

    # 아직 피드백 없음 (pending 상태)
    return False, "pending"


def extract_claude_md_sections(content: str) -> Dict[str, str]:
    """제안에서 CLAUDE.md에 추가할 섹션 추출"""
    sections = {}

    # User Style Preferences 섹션 추출
    user_style_match = re.search(
        r"```markdown\s*\n(## User Style Preferences.*?)```",
        content,
        re.DOTALL
    )
    if user_style_match:
        sections["user_style"] = user_style_match.group(1).strip()

    # LLM Agent Development 섹션 추출
    domain_match = re.search(
        r"```markdown\s*\n(## LLM Agent Development.*?)```",
        content,
        re.DOTALL
    )
    if domain_match:
        sections["domain_specific"] = domain_match.group(1).strip()

    # Error Handling 섹션 추출
    error_match = re.search(
        r"```markdown\s*\n(## Error Handling.*?)```",
        content,
        re.DOTALL
    )
    if error_match:
        sections["error_handling"] = error_match.group(1).strip()

    return sections


def backup_file(file_path: Path) -> Path:
    """파일 백업 생성"""
    backup_dir = file_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{file_path.name}.backup.{timestamp}"

    if file_path.exists():
        shutil.copy(file_path, backup_path)
        print(f"  백업 생성: {backup_path}")

    return backup_path


def update_claude_md(sections: Dict[str, str], target_path: Path) -> bool:
    """CLAUDE.md 업데이트"""
    if not target_path.exists():
        print(f"  ❌ 파일을 찾을 수 없음: {target_path}")
        return False

    # 백업
    backup_file(target_path)

    # 현재 내용 읽기
    with open(target_path, "r", encoding="utf-8") as f:
        current_content = f.read()

    # 새 섹션 추가 (파일 끝에)
    new_content = current_content.rstrip()

    additions = []
    for section_name, section_content in sections.items():
        # 이미 존재하는 섹션인지 확인
        section_header = section_content.split("\n")[0]
        if section_header in current_content:
            print(f"  ⏭️ 이미 존재하는 섹션: {section_header}")
            continue

        new_content += f"\n\n{section_content}"
        additions.append(section_name)

    if not additions:
        print("  ℹ️ 추가할 새 섹션 없음")
        return True

    # 저장
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  ✅ {len(additions)}개 섹션 추가: {', '.join(additions)}")
    return True


def create_skill(skill_name: str, skill_content: str, skills_dir: Path) -> bool:
    """신규 Skill 생성"""
    skill_file = skills_dir / f"{skill_name}.md"

    if skill_file.exists():
        print(f"  ⏭️ 이미 존재하는 Skill: {skill_name}")
        return True

    skills_dir.mkdir(parents=True, exist_ok=True)

    with open(skill_file, "w", encoding="utf-8") as f:
        f.write(skill_content)

    print(f"  ✅ Skill 생성: {skill_file}")
    return True


def record_applied_feedback(
    applied_proposals: List[str],
    feedback_dir: Path
) -> None:
    """적용 결과 기록"""
    feedback_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    result_file = feedback_dir / f"{today}_applied_feedback.md"

    content = f"""---
type: feedback_applied
date: {today}
tags: [✅applied]
---

# 피드백 적용 결과

## 적용 시간
{datetime.now().strftime("%Y-%m-%d %H:%M")}

## 적용된 제안
"""

    for i, proposal in enumerate(applied_proposals, 1):
        content += f"\n### {i}. {proposal}\n- ✅ 적용 완료\n"

    content += f"""
## 다음 단계
- 새 세션에서 업데이트된 규칙이 적용되는지 확인
- 문제 발생 시 `data/proposals/` 백업에서 복원 가능
"""

    with open(result_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  📝 적용 결과 기록: {result_file}")


def main():
    print("피드백 적용 시작...\n")

    # 제안 로드
    proposals = load_proposals()
    if not proposals:
        print("적용할 제안이 없습니다.")
        return

    print(f"발견된 제안 파일: {len(proposals)}개\n")

    applied_proposals = []

    for proposal_file, content in proposals:
        print(f"--- {proposal_file.name} ---")

        # 승인 여부 확인
        is_approved, status = check_approval(content)

        if status == "pending":
            print(f"  ⏳ 상태: 피드백 대기 중")
            print(f"  → 제안 파일을 열고 '적용 여부'에 [x]를 체크하세요")
            continue
        elif status == "rejected":
            print(f"  ❌ 상태: 거부됨")
            continue
        elif not is_approved:
            print(f"  ⏭️ 상태: {status}")
            continue

        print(f"  ✅ 상태: 승인됨 ({status})")

        # CLAUDE.md 업데이트 제안인 경우
        if "claude_md_update" in proposal_file.name:
            sections = extract_claude_md_sections(content)
            if sections:
                target = Path.home() / ".claude" / "CLAUDE.md"
                if update_claude_md(sections, target):
                    applied_proposals.append("CLAUDE.md 업데이트")

        # 신규 Skill 제안인 경우
        elif "new_skill" in proposal_file.name:
            # weekly-optimize Skill 생성
            skill_content = """---
name: weekly-optimize
description: 주간 세션 분석 및 최적화 제안 통합 실행
---

{{#task}}
## 주간 최적화 워크플로우

1. `python scripts/collect_sessions.py` - 세션 수집
2. `python scripts/analyze_all_sessions.py` - 분석 실행
3. `python scripts/generate_proposals.py` - 제안 생성
4. 사용자에게 피드백 요청
5. 승인 시 `python scripts/apply_feedback.py` 실행
{{/task}}
"""
            skills_dir = Path.home() / ".claude" / "skills"
            if create_skill("weekly-optimize", skill_content, skills_dir):
                applied_proposals.append("Skill: weekly-optimize")

        print()

    # 적용 결과 기록
    if applied_proposals:
        feedback_dir = Path("data/feedback")
        record_applied_feedback(applied_proposals, feedback_dir)

        print(f"\n{'='*60}")
        print("피드백 적용 완료!")
        print(f"{'='*60}")
        print(f"\n적용된 항목: {len(applied_proposals)}개")
        for item in applied_proposals:
            print(f"  - {item}")
    else:
        print("\n적용된 제안이 없습니다.")
        print("제안 파일에서 '적용 여부'에 [x]를 체크하세요:")
        for proposal_file, _ in proposals:
            print(f"  - {proposal_file}")


if __name__ == "__main__":
    main()
