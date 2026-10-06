"""캠퍼스 정보 MCP 서버. 실행과 연결 방법은 README.md."""

from __future__ import annotations

import datetime as dt

from mcp.server import MCPServer

import sources

mcp = MCPServer("hufs-campus")


@mcp.tool()
def get_academic_calendar(month: int | None = None, keyword: str | None = None) -> list[dict]:
    """이번 학년도 학사일정을 찾는다. month(1~12)나 keyword(예: "수강", "시험")로 거를 수 있다."""
    year = sources.current_academic_year(dt.date.today())
    events = sources.parse_calendar(sources.fetch_calendar_html(), year)
    if month is not None:
        events = [e for e in events if int(e["start"][5:7]) == month]
    if keyword:
        events = [e for e in events if keyword in e["title"]]
    return events


@mcp.tool()
def get_cafeteria_menu(date: str | None = None, cafeteria: str = "인문관식당") -> list[dict]:
    """학식 메뉴를 찾는다. date 는 YYYY-MM-DD(없으면 오늘).
    cafeteria: 인문관식당, 교수회관식당(서울) / 외대 한상 식당, 한그릇 식당, HufsDorm 식당(글로벌)."""
    day = dt.date.fromisoformat(date) if date else dt.date.today()
    html = sources.fetch_menu_html(day, sources.CAFETERIAS[cafeteria])
    return sources.parse_menu(html, day)


@mcp.tool()
def get_library_seats(campus: str = "서울") -> list[dict]:
    """도서관 열람실별 남은 좌석 수. campus: 서울 또는 글로벌."""
    return sources.parse_seats(sources.fetch_seats_json(campus))


@mcp.resource("hufs://cafeterias")
def cafeterias() -> str:
    """조회할 수 있는 식당 이름 목록."""
    return "\n".join(sources.CAFETERIAS)


if __name__ == "__main__":
    mcp.run(transport="stdio")
