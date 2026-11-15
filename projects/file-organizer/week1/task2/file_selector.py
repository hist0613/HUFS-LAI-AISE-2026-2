"""파일 메타데이터와 조건 목록을 받아 selected 값을 추가한다."""

import operator
from datetime import datetime
from typing import Any


_FIELDS = {"file_id", "rel_path", "name", "ext", "size_bytes", "mtime"}
_OPERATORS = {
    "eq": operator.eq,
    "in": lambda actual, expected: actual in expected,
    "contains": lambda actual, expected: expected in actual,
    "gte": operator.ge,
    "lte": operator.le,
}


def _parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("mtime에는 Z 또는 +09:00 같은 시간대가 필요합니다.")
    return result


def _matches(file_info: dict[str, Any], condition: dict[str, Any]) -> bool:
    field, op, expected = condition["field"], condition["op"], condition["value"]
    if field not in file_info:
        return False
    actual = file_info[field]

    if field == "mtime" and op != "contains":
        actual = _parse_time(actual)
        expected = (
            [_parse_time(value) for value in expected]
            if op == "in" else _parse_time(expected)
        )

    return _OPERATORS[op](actual, expected)


def select_files(
    files: list[dict[str, Any]],
    conditions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """각 파일에 selected(bool)를 추가한 새 목록을 반환한다.

    conditions 예시:
        [{"field": "ext", "op": "eq", "value": ".pdf"},
         {"field": "name", "op": "contains", "value": "최종"}]

    모든 조건을 만족해야 선택된다(AND). 조건이 없으면 전부 False.
    eq: 일치, in: 목록 중 일치, contains: 문자열 포함,
    gte: 이상/이후(포함), lte: 이하/이전(포함).
    문자열은 대소문자를 구분하며 원본 목록과 딕셔너리는 수정하지 않는다.
    """
    conditions = conditions or []
    for condition in conditions:
        if not {"field", "op", "value"}.issubset(condition):
            raise ValueError("각 조건에는 field, op, value가 필요합니다.")
        if condition["field"] not in _FIELDS:
            raise ValueError(f"지원하지 않는 필드: {condition['field']}")
        if condition["op"] not in _OPERATORS:
            raise ValueError(f"지원하지 않는 연산자: {condition['op']}")

    return [
        {
            **file_info,
            "selected": bool(conditions) and all(
                _matches(file_info, condition) for condition in conditions
            ),
        }
        for file_info in files
    ]
