import datetime as dt
import json
from pathlib import Path

import sources

FIX = Path(__file__).parent / "fixtures"


def read(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_calendar_single_day():
    events = sources.parse_calendar(read("calendar.html"), 2026)
    assert {"start": "2026-03-02", "end": "2026-03-02",
            "title": "2026학년도 제1학기 개강·대체휴업일"} in events


def test_calendar_range_and_next_year():
    events = sources.parse_calendar(read("calendar.html"), 2026)
    feb = [e for e in events if e["start"].startswith("2027-02")]
    assert feb, "2월 일정은 다음 해로 읽어야 한다"
    assert any(e["start"] != e["end"] for e in events)


def test_week_bounds_clipped_to_month():
    assert sources.week_bounds(dt.date(2026, 9, 30)) == (27, 30)
    assert sources.week_bounds(dt.date(2026, 10, 1)) == (1, 3)


def test_menu_for_one_day():
    meals = sources.parse_menu(read("menu_h101_2026-09-27.html"), dt.date(2026, 9, 28))
    breakfast = meals[0]
    assert breakfast["meal"] == "조식"
    assert breakfast["items"][0] == "참치김치찌개"
    assert breakfast["kcal"] == "850Kcal"


def test_menu_empty_day():
    assert sources.parse_menu(read("menu_h101_2026-09-27.html"), dt.date(2026, 9, 27)) == []


def test_seats():
    rooms = sources.parse_seats(json.loads(read("seats_seoul.json")))
    assert rooms and {"room", "floor", "total", "available"} <= rooms[0].keys()
    assert all(0 <= r["available"] <= r["total"] for r in rooms)

