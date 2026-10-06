"""학교 공개 페이지 요청(fetch_*)과 해석(parse_*). robots.txt 가 막는 경로는 쓰지 않는다."""

from __future__ import annotations

import datetime as dt
import re

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "HUFS-LAI-AISE campus MCP (course lab)"}
TIMEOUT = 10

CALENDAR_URL = "https://www.hufs.ac.kr/hufs/11360/subview.do"
MENU_URL = "https://www.hufs.ac.kr/cafeteria/hufs/1/getMenu"
SEATS_URL = "https://lib.hufs.ac.kr/pyxis-api/1/seat-rooms"

CAFETERIAS = {
    "인문관식당": "h101",
    "교수회관식당": "h102",
    "외대 한상 식당": "h202",
    "한그릇 식당": "h203",
    "HufsDorm 식당": "h205",
}
LIBRARY_GROUPS = {"서울": 1, "글로벌": 2}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# 학사일정 --------------------------------------------------------------

def fetch_calendar_html() -> str:
    r = requests.get(CALENDAR_URL, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def parse_calendar(html: str, academic_year: int) -> list[dict]:
    """학사일정 페이지 → [{"start": "2026-03-02", "end": "2026-03-02", "title": ...}]

    페이지는 3월부터 이듬해 2월까지 한 학년도를 보여 준다. 1·2월은 academic_year + 1 년.
    """
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for li in soup.select("#timeTableList > ul > li"):
        for box in li.select(".list-box"):
            date_text = _clean(box.select_one(".list-date").get_text(" "))
            title = _clean(box.select_one(".list-content").get_text(" "))
            parts = [p.strip() for p in date_text.split("~")]
            start, end = (_to_date(parts[0], academic_year), _to_date(parts[-1], academic_year))
            events.append({"start": start.isoformat(), "end": end.isoformat(), "title": title})
    return events


def _to_date(mmdd: str, academic_year: int) -> dt.date:
    month, day = (int(x) for x in mmdd.split("."))
    year = academic_year if month >= 3 else academic_year + 1
    return dt.date(year, month, day)


def current_academic_year(today: dt.date) -> int:
    return today.year if today.month >= 3 else today.year - 1


# 학식 ------------------------------------------------------------------

def week_bounds(day: dt.date) -> tuple[int, int]:
    """식단 요청에 쓰는 그 주의 첫날·마지막 날(일~토, 같은 달 안으로 자름)."""
    sunday = day - dt.timedelta(days=(day.weekday() + 1) % 7)
    saturday = sunday + dt.timedelta(days=6)
    first = sunday.day if sunday.month == day.month else 1
    last = saturday.day if saturday.month == day.month else _month_end(day).day
    return first, last


def _month_end(day: dt.date) -> dt.date:
    nxt = day.replace(day=28) + dt.timedelta(days=4)
    return nxt - dt.timedelta(days=nxt.day)


def fetch_menu_html(day: dt.date, cafeteria_id: str) -> str:
    first, last = week_bounds(day)
    data = {
        "selCafId": cafeteria_id,
        "selWeekFirstDay": first,
        "selWeekLastDay": last,
        "selYear": day.year,
        "selMonth": f"{day.month:02d}",
    }
    r = requests.post(MENU_URL, data=data, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def parse_menu(html: str, day: dt.date) -> list[dict]:
    """주간 식단표 → 그날의 [{"meal": "중식(1)", "time": "11:00~14:30", "items": [...]}]"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []
    headers = [_clean(th.get_text(" ")) for th in table.select("thead th")]
    key = f"{day.month:02d}/{day.day:02d}"
    if key not in headers:
        return []
    col = headers.index(key)
    meals = []
    for tr in table.select("tbody tr"):
        cells = tr.find_all(["th", "td"])
        if col >= len(cells):
            continue
        cell = cells[col]
        items = [_clean(li.get_text(" ")) for li in cell.select("li")]
        items = [x for x in items if x]
        if not items:
            continue
        head = list(cells[0].stripped_strings)
        kcal, pay = cell.select_one(".calorie"), cell.select_one(".pay")
        meals.append({
            "meal": head[0] if head else "",
            "time": _clean(" ".join(head[1:])).strip("()"),
            "items": items,
            "kcal": kcal.get_text(strip=True) if kcal else "",
            "price": pay.get_text(strip=True) if pay else "",
        })
    return meals


# 도서관 좌석 -----------------------------------------------------------

def fetch_seats_json(campus: str) -> dict:
    params = {"smufMethodCode": "PC", "branchGroupId": LIBRARY_GROUPS[campus]}
    r = requests.get(SEATS_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def parse_seats(payload: dict) -> list[dict]:
    rooms = []
    for room in payload["data"]["list"]:
        seats = room["seats"]
        rooms.append({
            "room": room["name"],
            "floor": room["floor"],
            "total": seats["total"],
            "available": seats["available"],
        })
    return rooms

