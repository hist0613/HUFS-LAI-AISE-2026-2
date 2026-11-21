"""파일 메타데이터와 조건 목록을 받아 selected 값을 계산한다."""

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
    # Python 3.10에서도 파일 수집기가 붙이는 UTC 접미사 Z를 처리한다.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    result = datetime.fromisoformat(value)
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
    """각 파일의 selected(bool)를 다시 계산해 새 목록을 반환한다.

    파일 수집기는 selected=False와 UTC mtime(예: 2026-11-14T16:30:00Z)을
    전달한다. 반환값의 selected는 입력에 있는 값과 관계없이 조건으로 결정된다.
    mtime의 contains는 저장된 UTC 문자열을 그대로 검사한다. 다른 연산자는
    +09:00 같은 시간대가 지정된 조건값도 받아 실제 시각을 비교한다.

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
