# 캠퍼스 정보 MCP 서버

학교 공개 페이지를 그때그때 조회해 에이전트에게 도구로 제공합니다. 각자 자기 컴퓨터에서 실행하고, 서버에 개인정보를 저장하지 않습니다.

## 실행

```
pip install -r tools/mcp/requirements.txt
python -m pytest -q tools/mcp/tests
claude mcp add --transport stdio campus -- python tools/mcp/server.py
```

Claude Code 에서 `/mcp` 로 연결 상태를 확인한 뒤 "10월 시험 일정 알려줘", "지금 도서관 남은 자리" 처럼 물어봅니다.

## 도구

| 도구 | 하는 일 | 출처 |
|---|---|---|
| `get_academic_calendar` | 학년도 학사일정 (월·키워드로 거르기) | 학교 홈페이지 학사일정 |
| `get_cafeteria_menu` | 날짜·식당별 학식 메뉴 | 학교 홈페이지 식단 |
| `get_library_seats` | 열람실별 남은 좌석 | 도서관 홈페이지 |

Resource `hufs://cafeterias`: 조회할 수 있는 식당 이름 목록.

## 쓰지 않는 출처

robots.txt 가 자동 접근을 막는 곳은 도구로 만들지 않습니다.

- 공지 게시판(`www.hufs.ac.kr/bbs/*`), 학사종합정보시스템(`wis.hufs.ac.kr`, 강의시간표 포함)

## 기여

기능 하나를 이슈 하나로 열고, 도구·테스트·fixture 를 한 PR 에 담습니다. 브랜치·커밋·PR 규칙은 [CONTRIBUTING.md](../../CONTRIBUTING.md).
