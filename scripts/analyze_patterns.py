#!/usr/bin/env python3
"""
Pattern Analyzer for Self-Optimizer

Analyzes collected patterns from hooks and generates insights:
- Negative reaction frequency & severity
- Tool usage patterns
- Project-specific patterns
- Time-based trends

Usage:
    python3 scripts/analyze_patterns.py [--days N] [--project NAME] [--json]
"""

import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
PATTERNS_FILE = DATA_DIR / "patterns.jsonl"
SOLUTIONS_FILE = Path(__file__).parent.parent / "knowledge" / "solutions" / "patterns.json"


def load_solutions() -> dict:
    """Load solutions knowledge base."""
    if not SOLUTIONS_FILE.exists():
        return {"patterns": []}

    with open(SOLUTIONS_FILE) as f:
        return json.load(f)


def load_patterns(days: int = 30, project: str = None) -> list[dict]:
    """Load patterns from JSONL file."""
    if not PATTERNS_FILE.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    patterns = []

    with open(PATTERNS_FILE) as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                timestamp = datetime.fromisoformat(record.get("timestamp", ""))

                if timestamp < cutoff:
                    continue

                if project and record.get("project") != project:
                    continue

                patterns.append(record)
            except (json.JSONDecodeError, ValueError):
                continue

    return patterns


def analyze_negative_reactions(patterns: list[dict]) -> dict:
    """Analyze negative reaction patterns."""
    negative = [p for p in patterns if p.get("type") == "negative_reaction"]

    if not negative:
        return {"count": 0, "by_severity": {}, "by_type": {}, "by_project": {}}

    by_severity = defaultdict(int)
    by_type = defaultdict(int)
    by_project = defaultdict(int)

    for p in negative:
        by_severity[p.get("severity", "unknown")] += 1
        by_type[p.get("pattern_type", "unknown")] += 1
        by_project[p.get("project", "unknown")] += 1

    return {
        "count": len(negative),
        "by_severity": dict(by_severity),
        "by_type": dict(by_type),
        "by_project": dict(by_project),
    }


def analyze_tool_usage(patterns: list[dict]) -> dict:
    """Analyze tool usage patterns."""
    tools = [p for p in patterns if p.get("type") == "tool_usage"]

    if not tools:
        return {"count": 0, "by_tool": {}, "by_category": {}, "repeated_files": []}

    by_tool = defaultdict(int)
    by_category = defaultdict(int)
    file_reads = defaultdict(int)

    for p in tools:
        by_tool[p.get("tool", "unknown")] += 1
        by_category[p.get("category", "unknown")] += 1

        if p.get("tool") == "Read" and p.get("file_path"):
            file_reads[p["file_path"]] += 1

    # Find files read more than 3 times
    repeated_files = [
        {"file": f, "count": c}
        for f, c in sorted(file_reads.items(), key=lambda x: -x[1])
        if c >= 3
    ][:10]

    return {
        "count": len(tools),
        "by_tool": dict(by_tool),
        "by_category": dict(by_category),
        "repeated_files": repeated_files,
    }


def get_solution_by_id(solutions: dict, pattern_id: str) -> Optional[dict]:
    """Get solution pattern by ID from knowledge base."""
    for pattern in solutions.get("patterns", []):
        if pattern.get("id") == pattern_id:
            return pattern
    return None


def generate_insights(negative_analysis: dict, tool_analysis: dict) -> list[dict]:
    """Generate actionable insights from analysis using solutions knowledge base."""
    insights = []
    solutions = load_solutions()

    # High severity negative reactions → repeated_corrections pattern
    if negative_analysis.get("by_severity", {}).get("critical", 0) > 0:
        solution = get_solution_by_id(solutions, "repeated_corrections")
        insight = {
            "priority": "P0",
            "pattern_id": "repeated_corrections",
            "type": "critical_frustration",
            "message": f"Critical frustration detected {negative_analysis['by_severity']['critical']} times",
        }
        if solution:
            insight["root_cause"] = solution.get("root_cause", {})
            insight["solutions"] = solution.get("solutions", [])
            insight["verification"] = solution.get("verification", {})
        else:
            insight["suggestion"] = "Review session context before major implementations"
        insights.append(insight)

    if negative_analysis.get("by_severity", {}).get("high", 0) >= 3:
        solution = get_solution_by_id(solutions, "repeated_corrections")
        insight = {
            "priority": "P1",
            "pattern_id": "repeated_corrections",
            "type": "frequent_retry",
            "message": f"Frequent retry requests ({negative_analysis['by_severity']['high']} times)",
        }
        if solution:
            insight["root_cause"] = solution.get("root_cause", {})
            insight["solutions"] = solution.get("solutions", [])
            insight["verification"] = solution.get("verification", {})
        else:
            insight["suggestion"] = "Consider adding spec-interview step before implementation"
        insights.append(insight)

    # Repeated file reads → same_file_repeated_reads pattern
    if tool_analysis.get("repeated_files"):
        top_file = tool_analysis["repeated_files"][0]
        if top_file["count"] >= 5:
            solution = get_solution_by_id(solutions, "same_file_repeated_reads")
            insight = {
                "priority": "P2",
                "pattern_id": "same_file_repeated_reads",
                "type": "repeated_reads",
                "message": f"File '{top_file['file']}' read {top_file['count']} times",
                "context": {"file": top_file["file"], "count": top_file["count"]},
            }
            if solution:
                insight["root_cause"] = solution.get("root_cause", {})
                insight["solutions"] = solution.get("solutions", [])
                insight["verification"] = solution.get("verification", {})
            else:
                insight["suggestion"] = "Consider caching file summary in CLAUDE.md"
            insights.append(insight)

    # Heavy exploration pattern
    exploration_count = (
        tool_analysis.get("by_category", {}).get("file_read", 0) +
        tool_analysis.get("by_category", {}).get("code_search", 0) +
        tool_analysis.get("by_category", {}).get("file_search", 0)
    )
    total_count = tool_analysis.get("count", 1)

    if total_count > 0 and exploration_count / total_count > 0.7:
        solution = get_solution_by_id(solutions, "heavy_exploration")
        ratio = exploration_count / total_count
        insight = {
            "priority": "P2",
            "pattern_id": "heavy_exploration",
            "type": "heavy_exploration",
            "message": f"Heavy exploration pattern ({exploration_count}/{total_count} = {ratio:.0%})",
        }
        if solution:
            insight["root_cause"] = solution.get("root_cause", {})
            insight["solutions"] = solution.get("solutions", [])
            insight["verification"] = solution.get("verification", {})
        else:
            insight["suggestion"] = "Run /gsd:map-codebase to create a codebase map"
        insights.append(insight)

    return insights


def format_report(negative: dict, tools: dict, insights: list[dict]) -> str:
    """Format analysis report as text."""
    lines = ["# Pattern Analysis Report", ""]

    # Negative Reactions
    lines.append("## Negative Reactions")
    if negative["count"] == 0:
        lines.append("No negative reactions detected.")
    else:
        lines.append(f"Total: {negative['count']}")
        lines.append("")
        lines.append("By Severity:")
        for sev, count in sorted(negative["by_severity"].items()):
            lines.append(f"  - {sev}: {count}")
        lines.append("")
        lines.append("By Type:")
        for typ, count in sorted(negative["by_type"].items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  - {typ}: {count}")
    lines.append("")

    # Tool Usage
    lines.append("## Tool Usage")
    if tools["count"] == 0:
        lines.append("No tool usage recorded.")
    else:
        lines.append(f"Total: {tools['count']}")
        lines.append("")
        lines.append("By Tool:")
        for tool, count in sorted(tools["by_tool"].items(), key=lambda x: -x[1]):
            lines.append(f"  - {tool}: {count}")

        if tools["repeated_files"]:
            lines.append("")
            lines.append("Frequently Read Files:")
            for item in tools["repeated_files"][:5]:
                lines.append(f"  - {item['file']}: {item['count']} times")
    lines.append("")

    # Insights
    lines.append("## Insights")
    if not insights:
        lines.append("No significant patterns detected.")
    else:
        for insight in insights:
            lines.append(f"### [{insight['priority']}] {insight['type']}")
            lines.append(f"- {insight['message']}")

            # Root cause analysis (5 Whys)
            if root_cause := insight.get("root_cause"):
                lines.append("")
                lines.append("**Root Cause (5 Whys):**")
                for key, value in root_cause.items():
                    lines.append(f"  - {key}: {value}")

            # Solutions from knowledge base
            if solutions_list := insight.get("solutions"):
                lines.append("")
                lines.append("**Solutions:**")
                for sol in solutions_list:
                    effort = sol.get("effort", "?")
                    impact = sol.get("impact", "?")
                    lines.append(f"  - [{effort}/{impact}] {sol.get('action', '')}")
                    if desc := sol.get("description"):
                        lines.append(f"    {desc}")

            # Verification method
            if verification := insight.get("verification"):
                lines.append("")
                lines.append(f"**Verification:** {verification.get('method', '')}")
                lines.append(f"**Success Criteria:** {verification.get('success_criteria', '')}")

            # Fallback to simple suggestion
            if suggestion := insight.get("suggestion"):
                lines.append(f"- **Suggestion**: {suggestion}")

            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze collected patterns")
    parser.add_argument("--days", type=int, default=30, help="Days to analyze")
    parser.add_argument("--project", type=str, help="Filter by project")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    patterns = load_patterns(days=args.days, project=args.project)

    if not patterns:
        print("No patterns collected yet. Install the hook first.")
        return

    negative = analyze_negative_reactions(patterns)
    tools = analyze_tool_usage(patterns)
    insights = generate_insights(negative, tools)

    if args.json:
        result = {
            "negative_reactions": negative,
            "tool_usage": tools,
            "insights": insights,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_report(negative, tools, insights))


if __name__ == "__main__":
    main()
