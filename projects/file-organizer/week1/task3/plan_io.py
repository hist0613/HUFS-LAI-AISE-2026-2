"""탐색 결과 JSON 파일 읽기 및 정리 계획안(Plan) JSON 파일 저장을 담당한다."""

import json
from pathlib import Path
from typing import Any

if __package__:
    from .destination_planner import PlanItem
else:
    from destination_planner import PlanItem


def load_scanned_files(input_path: str | Path) -> list[dict[str, Any]]:
    """UTF-8 JSON 파일에서 ScannedFile 딕셔너리 목록을 읽어 반환한다."""
    path = Path(input_path)
    with path.open("r", encoding="utf-8") as stream:
        try:
            raw_data = json.load(stream)
        except json.JSONDecodeError as error:
            raise ValueError(f"유효한 JSON 형식이 아닙니다: {path}") from error

    if not isinstance(raw_data, list):
        raise ValueError("입력 JSON의 최상위 구조는 파일 정보 배열(list)이어야 합니다.")

    for index, item in enumerate(raw_data):
        if not isinstance(item, dict):
            raise ValueError(
                f"입력 JSON의 {index}번째 항목은 객체(dict)여야 합니다."
            )

    return raw_data


def save_plan_json(
    plan_items: list[PlanItem],
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """정리 계획안 목록을 UTF-8 JSON 파일로 저장한다.

    기본값(overwrite=False)에서는 기존 파일을 실수로 덮어쓰지 않도록
    배타적 생성 모드('x')를 사용한다.
    """
    output = Path(output_path).absolute()
    payload = json.dumps(plan_items, ensure_ascii=False, indent=2) + "\n"
    write_mode = "w" if overwrite else "x"

    with output.open(write_mode, encoding="utf-8") as stream:
        stream.write(payload)

    return output
