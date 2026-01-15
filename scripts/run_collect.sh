#!/bin/bash
# 세션 수집 자동화 스크립트
# LaunchAgent에서 호출됨

set -e

PROJECT_DIR="/Users/xcape/gemmy/10_Projects/agent_self_optimization"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/collection_$(date +%Y-%m-%d).log"

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR"

# 시작 로그
echo "=====================================" >> "$LOG_FILE"
echo "세션 수집 시작: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "=====================================" >> "$LOG_FILE"

# 프로젝트 디렉토리로 이동
cd "$PROJECT_DIR"

# Python 스크립트 실행
python3 scripts/save_all_sessions.py >> "$LOG_FILE" 2>&1

# 완료 로그
echo "" >> "$LOG_FILE"
echo "세션 수집 완료: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 30일 이상 된 로그 삭제
find "$LOG_DIR" -name "collection_*.log" -mtime +30 -delete 2>/dev/null || true
