"""파일 메타데이터와 조건 목록을 받아 selected 값을 계산한다."""

import operator
from typing import Any


_FIELDS = {"file_id", "rel_path", "name", "ext", "size_bytes", "mtime"}
_OPERATORS = {
    "eq": operator.eq,
    "in": lambda actual, expected: actual in expected,
    "contains": lambda actual, expected: expected in actual,
    "gte": operator.ge,
    "lte": operator.le,
}


def _matches(file_info: dict[str, Any], condition: dict[str, Any]) -> bool:
    field, op, expected = condition["field"], condition["op"], condition["value"]
    if field not in file_info:
        return False
    return _OPERATORS[op](file_info[field], expected)


def select_files(
    files: list[dict[str, Any]],
    conditions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """각 파일의 selected(bool)를 다시 계산해 새 목록을 반환한다.

    파일 수집기는 selected=False를 전달한다. 반환값의 selected는 조건으로 결정된다.
    파일의 mtime과 시각을 비교하는 조건값(in의 각 원소 포함)은 모두 초 단위 UTC
    문자열(YYYY-MM-DDTHH:MM:SSZ)이라고 가정한다. 이 형식에서는 문자열 순서가
    시간 순서와 같다. contains는 날짜처럼 문자열의 일부를 검색한다.

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
