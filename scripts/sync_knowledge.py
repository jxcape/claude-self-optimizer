"""
Knowledge Base Sync Script

awesome-claude-code의 THE_RESOURCES_TABLE.csv를 파싱하여
로컬 knowledge/ 디렉토리에 구조화된 형태로 저장
"""

import csv
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any


# ============================================================
# 설정
# ============================================================

CSV_URL = "https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/THE_RESOURCES_TABLE.csv"
PROJECT_ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"

# 카테고리 매핑 (CSV 카테고리 -> 로컬 디렉토리)
CATEGORY_MAP = {
    "Slash-Commands": "slash_commands",
    "CLAUDE.md Files": "claude_md_patterns",
    "Workflows & Knowledge Guides": "workflows",
    "Agent Skills": "skills",
    "Tooling": "tooling",
    "Hooks": "hooks",
    "Status Lines": "status_lines",
    "Output Styles": "output_styles",
    "Alternative Clients": "alternative_clients",
    "Official Documentation": "official_docs",
}

# 서브카테고리 매핑 (Slash-Commands 하위)
SUBCATEGORY_MAP = {
    "Git & Version Control": "git",
    "Code Analysis & Testing": "testing",
    "Context Loading & Priming": "context",
    "Documentation": "docs",
    "Deployment": "deployment",
    "Utilities": "utilities",
}


# ============================================================
# CSV 다운로드 및 파싱
# ============================================================

def download_csv() -> str:
    """CSV 파일 다운로드"""
    print(f"Downloading: {CSV_URL}")
    try:
        with urllib.request.urlopen(CSV_URL, timeout=30) as response:
            content = response.read().decode('utf-8')
            print(f"Downloaded: {len(content)} bytes")
            return content
    except urllib.error.URLError as e:
        print(f"Download failed: {e}")
        raise


def parse_csv(content: str) -> List[Dict[str, Any]]:
    """CSV 파싱하여 리소스 목록 반환"""
    resources = []

    lines = content.strip().split('\n')
    reader = csv.DictReader(lines)

    for row in reader:
        # 활성 상태 리소스만 포함 (Removed, Stale 제외)
        if row.get('Removed From Origin') == 'TRUE':
            continue
        if row.get('Stale') == 'TRUE':
            continue

        resource = {
            "id": row.get('ID', '').strip(),
            "name": row.get('Display Name', '').strip(),
            "category": row.get('Category', '').strip(),
            "subcategory": row.get('Sub-Category', '').strip(),
            "description": row.get('Description', '').strip(),
            "primary_url": row.get('Primary Link', '').strip(),
            "secondary_url": row.get('Secondary Link', '').strip(),
            "author": row.get('Author Name', '').strip(),
            "author_url": row.get('Author GitHub', '').strip(),
            "license": row.get('License', '').strip(),
            "added_date": row.get('Added to ACC', '').strip(),
            "last_checked": row.get('Last Validity Check', '').strip(),
        }

        # 빈 항목 제거
        if resource["name"] and resource["category"]:
            resources.append(resource)

    print(f"Parsed: {len(resources)} active resources")
    return resources


# ============================================================
# 지식 베이스 구조화
# ============================================================

def structure_resources(resources: List[Dict]) -> Dict[str, Any]:
    """리소스를 카테고리별로 구조화"""

    structured = defaultdict(lambda: defaultdict(list))
    stats = defaultdict(int)

    for r in resources:
        category = r["category"]
        subcategory = r.get("subcategory", "general")

        # 카테고리 매핑
        local_category = CATEGORY_MAP.get(category, "other")

        # 서브카테고리 매핑 (Slash-Commands의 경우)
        if local_category == "slash_commands":
            local_subcategory = SUBCATEGORY_MAP.get(subcategory, "other")
        else:
            local_subcategory = subcategory.lower().replace(" ", "_").replace("&", "and") if subcategory else "general"

        structured[local_category][local_subcategory].append(r)
        stats[local_category] += 1

    return dict(structured), dict(stats)


def save_knowledge_base(structured: Dict, stats: Dict):
    """구조화된 데이터를 knowledge/ 디렉토리에 저장"""

    # 디렉토리 생성
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for category, subcategories in structured.items():
        category_dir = KNOWLEDGE_DIR / category
        category_dir.mkdir(exist_ok=True)

        # 카테고리별 인덱스
        category_index = {
            "category": category,
            "total_resources": sum(len(items) for items in subcategories.values()),
            "subcategories": {},
        }

        for subcategory, resources in subcategories.items():
            # 서브카테고리 파일 저장
            subcategory_file = category_dir / f"{subcategory}.json"

            subcategory_data = {
                "subcategory": subcategory,
                "count": len(resources),
                "resources": resources,
            }

            with open(subcategory_file, "w", encoding="utf-8") as f:
                json.dump(subcategory_data, f, ensure_ascii=False, indent=2)

            saved_files.append(str(subcategory_file.relative_to(PROJECT_ROOT)))
            category_index["subcategories"][subcategory] = len(resources)

        # 카테고리 인덱스 저장
        index_file = category_dir / "_index.json"
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(category_index, f, ensure_ascii=False, indent=2)

    return saved_files


def create_catalog(structured: Dict, stats: Dict) -> Dict:
    """메인 카탈로그 파일 생성"""

    catalog = {
        "version": "1.0.0",
        "last_synced": datetime.now().isoformat(),
        "source": "https://github.com/hesreallyhim/awesome-claude-code",
        "source_file": "THE_RESOURCES_TABLE.csv",
        "categories": {},
        "stats": {
            "total_resources": sum(stats.values()),
            **stats
        }
    }

    # 카테고리별 리소스 이름 목록
    for category, subcategories in structured.items():
        catalog["categories"][category] = []
        for subcategory, resources in subcategories.items():
            for r in resources:
                catalog["categories"][category].append({
                    "id": r["id"],
                    "name": r["name"],
                    "subcategory": subcategory,
                })

    # 카탈로그 저장
    catalog_file = KNOWLEDGE_DIR / "catalog.json"
    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    return catalog


# ============================================================
# 메인 실행
# ============================================================

def main(force: bool = False):
    print("\n" + "=" * 60)
    print("Knowledge Base Sync")
    print("=" * 60 + "\n")

    # 기존 카탈로그 확인
    catalog_file = KNOWLEDGE_DIR / "catalog.json"
    if catalog_file.exists() and not force:
        with open(catalog_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
        last_synced = existing.get("last_synced", "")
        print(f"Existing catalog found (synced: {last_synced})")
        print("Use --force to re-sync")
        # TODO: diff 체크 구현

    # 1. CSV 다운로드
    print("\n[Step 1] Downloading CSV...")
    content = download_csv()

    # 2. 파싱
    print("\n[Step 2] Parsing resources...")
    resources = parse_csv(content)

    # 3. 구조화
    print("\n[Step 3] Structuring knowledge base...")
    structured, stats = structure_resources(resources)

    # 4. 저장
    print("\n[Step 4] Saving files...")
    saved_files = save_knowledge_base(structured, stats)

    # 5. 카탈로그 생성
    print("\n[Step 5] Creating catalog...")
    catalog = create_catalog(structured, stats)

    # 결과 출력
    print("\n" + "=" * 60)
    print("Sync Complete!")
    print("=" * 60)
    print(f"\nTotal resources: {catalog['stats']['total_resources']}")
    print("\nBy category:")
    for cat, count in stats.items():
        print(f"  - {cat}: {count}")
    print(f"\nSaved to: {KNOWLEDGE_DIR}")
    print(f"Catalog: {catalog_file}")


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    main(force=force)
