#!/usr/bin/env python3
"""
Pattern Collector Hook for Claude Code

Collects usage patterns for self-optimization:
- Negative reactions (user frustration signals)
- Tool usage patterns (repeated reads, context resets, etc.)

Usage in settings.json:
{
  "hooks": {
    "UserPromptSubmit": ["python3 /path/to/pattern_collector.py"],
    "PostToolUse": ["python3 /path/to/pattern_collector.py"]
  }
}
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Data file location
DATA_DIR = Path(__file__).parent.parent / "data"
PATTERNS_FILE = DATA_DIR / "patterns.jsonl"

# Negative reaction patterns (Korean + English)
NEGATIVE_PATTERNS = [
    # Frustration signals
    (r"다시\s*(해|작성|만들)", "retry_request", "high"),
    (r"틀렸", "wrong_output", "high"),
    (r"전부\s*(다\s*)?(틀|잘못)", "all_wrong", "critical"),
    (r"왜\s*이렇게", "frustration", "medium"),
    (r"아니\s*(야|거든|잖아|지|요)", "correction", "medium"),
    (r"그거\s*말고", "not_that", "medium"),
    (r"필요\s*없", "unnecessary", "low"),
    (r"이미\s*말했", "already_said", "medium"),
    # English patterns
    (r"wrong|incorrect", "wrong_output", "high"),
    (r"try again|redo", "retry_request", "high"),
    (r"not what i (asked|wanted|meant)", "misunderstanding", "high"),
    (r"no,?\s*(that's|it's) not", "correction", "medium"),
]

# Tool patterns to track
TOOL_PATTERNS = {
    "Read": "file_read",
    "Grep": "code_search",
    "Glob": "file_search",
    "Edit": "file_edit",
    "Write": "file_write",
    "Task": "agent_spawn",
}


def detect_negative_reaction(prompt: str) -> List[Dict]:
    """Detect negative reaction patterns in user prompt."""
    detected = []
    prompt_lower = prompt.lower()

    for pattern, pattern_type, severity in NEGATIVE_PATTERNS:
        if re.search(pattern, prompt_lower):
            detected.append({
                "type": "negative_reaction",
                "pattern_type": pattern_type,
                "severity": severity,
                "matched_text": re.search(pattern, prompt_lower).group(),
            })

    return detected


def track_tool_usage(tool_name: str, tool_input: dict, tool_output: dict = None) -> Optional[Dict]:
    """Track tool usage patterns."""
    if tool_name not in TOOL_PATTERNS:
        return None

    pattern = {
        "type": "tool_usage",
        "tool": tool_name,
        "category": TOOL_PATTERNS[tool_name],
    }

    # Extract relevant info based on tool type
    if tool_name == "Read" and "file_path" in tool_input:
        pattern["file_path"] = tool_input["file_path"]
    elif tool_name in ("Grep", "Glob") and "pattern" in tool_input:
        pattern["search_pattern"] = tool_input["pattern"]
    elif tool_name == "Task" and "subagent_type" in tool_input:
        pattern["agent_type"] = tool_input["subagent_type"]

    return pattern


def save_pattern(pattern: dict, session_id: str = None, project: str = None):
    """Save pattern to JSONL file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "project": project,
        **pattern,
    }

    with open(PATTERNS_FILE, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    """Main hook handler using environment variables."""
    # Read from environment variables (Claude Code hooks)
    hook_type = os.environ.get("CLAUDE_HOOK_TYPE", "")
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    cwd = os.environ.get("CLAUDE_CWD", "")
    project = cwd.split("/")[-1] if cwd else None

    patterns_detected = []

    if hook_type == "UserPromptSubmit":
        # Detect negative reactions in user prompt
        prompt = os.environ.get("CLAUDE_PROMPT", "")
        patterns_detected = detect_negative_reaction(prompt)

    elif hook_type == "PostToolUse":
        # Track tool usage
        tool_name = os.environ.get("CLAUDE_TOOL_NAME", "")
        tool_input_str = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
        try:
            tool_input = json.loads(tool_input_str)
        except json.JSONDecodeError:
            tool_input = {}

        pattern = track_tool_usage(tool_name, tool_input)
        if pattern:
            patterns_detected = [pattern]

    # Save all detected patterns
    for pattern in patterns_detected:
        save_pattern(pattern, session_id, project)


if __name__ == "__main__":
    main()
