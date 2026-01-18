# Claude Code Session Storage Structure

## 실제 세션 위치

```
/Users/xcape/Library/Application Support/Claude/local-agent-mode-sessions/
├── [UUID1]/               # Agent/Process 세션
│   └── [UUID2]/           # 프로젝트 세션
│       └── [UUID3].json   # 세션 데이터 (UUID 파일명)
└── skills-plugin/
    └── [UUID]/
        └── [UUID]/...
```

## 세션 JSON 구조

```json
{
  "sessionId": "local_22b5e566-5502-4b40-bcb3-219ba5eeb013",
  "title": "Behavioral economics in index investing strategy",
  "createdAt": 1768276831204,  // UNIX timestamp (ms)
  "lastActivityAt": 1768276893284,
  "model": "claude-opus-4-5-20251101",
  "isArchived": false,
  "initialMessage": "이 글은...",
  "cwd": "/sessions/beautiful-focused-bardeen",
  "userSelectedFolders": ["/Users/xcape/gemmy"]
}
```

## 문제점

### 1. UUID 파일명
- **파일명**: `local_22b5e566-5502-4b40-bcb3-219ba5eeb013.json`
- **문제**: 사람이 읽기 어려움
- **해결**: `YYYY-MM-DD_title.json`으로 변환 필요

### 2. 중첩 디렉토리 구조
- **구조**: `UUID1/UUID2/UUID.json`
- **문제**: 세션 위치 찾기 복잡
- **해결**: `find`로 재귀적 검색 필요

### 3. 시간 순서
- **파일명**: 시간 정보 없음
- **해결**: JSON `createdAt` 필드로 정렬 필요

## 해결 방안

### Option 1: session_list API 사용 (추천)

```python
sessions = session_list()
# 이미 시간 순서로 정렬되어 있음
```

### Option 2: 파일 시스템 직접 스캔

```bash
# 모든 세션 JSON 찾기
find ~/Library/Application\ Support/Claude/local-agent-mode-sessions/ \
  -name "*.json" -type f
```

### Option 3: 하이브리드

```python
# 1. session_list로 목록 가져오기
session_list_data = session_list()

# 2. 파일 시스템에서 실제 JSON 경로 찾기
for session in session_list_data:
    json_path = find_session_file(session['id'])
    data = read_json(json_path)
    # 사람이 읽기 쉬운 이름으로 저장
    save_with_readable_name(data)
```

## 추천 접근

**Option 1 (session_list API)** 사용:
- 이미 시간 순서 정렬
- 메타데이터(메시지 수, 에이전트 등) 바로 접근
- `session_read`로 상세 내용 가져오기

**보존용 이름 변환**:
```python
def get_readable_name(session):
    # createdAt을 YYYY-MM-DD로 변환
    date = datetime.fromtimestamp(session['createdAt'] / 1000)
    date_str = date.strftime('%Y-%m-%d')

    # title에서 파일명에 적합한 문자 추출
    title = re.sub(r'[^\w\s-]', '', session['title'])[:50]

    return f"{date_str}_{title}.json"
```

## 결론

1. **모든 세션**: `/Users/xcape/Library/Application Support/Claude/local-agent-mode-sessions/`
2. **시간 순서**: `createdAt` 필드로 정렬 필요 (파일명 X)
3. **사람 읽기**: UUID 파일명 → `YYYY-MM-DD_title.json` 변환 필요
