"""JSON 파일을 입력받아 목적지 정리 계획 JSON을 생성하는 독립 실행 CLI."""

import argparse
import sys
from pathlib import Path

if __package__:
    from .destination_planner import plan_destinations
    from .plan_io import load_scanned_files, save_plan_json
else:
    from destination_planner import plan_destinations
    from plan_io import load_scanned_files, save_plan_json


def _format_os_error(error: OSError) -> str:
    """파일 입출력 예외 종류에 따라 사용자에게 안내할 오류 문구를 만든다."""
    if isinstance(error, FileExistsError):
        return "출력 파일이 이미 존재합니다. 새 파일명을 쓰거나 --overwrite를 지정하세요."
    if isinstance(error, PermissionError):
        return "파일 읽기/쓰기 권한이 없습니다. 경로 권한을 확인하세요."
    if isinstance(error, (FileNotFoundError, NotADirectoryError, IsADirectoryError)):
        return "입력 파일 또는 출력 상위 폴더 경로를 찾을 수 없습니다."
    return f"파일 작업 중 오류가 발생했습니다: {error.strerror}"


def main(argv: list[str] | None = None) -> int:
    """입력 JSON을 읽어 분류 목적지 계획을 생성하고 출력 JSON으로 저장한다."""
    parser = argparse.ArgumentParser(
        description="자파(Task 3): 선택된 파일들의 분류 목적지 계획(Plan) JSON 생성"
    )
    parser.add_argument("input_json", help="Task 1/2 형식의 입력 JSON 파일 경로")
    parser.add_argument("-o", "--output", required=True, help="저장할 계획 JSON 경로")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="출력 JSON 파일이 이미 있어도 덮어씁니다.",
    )
    args = parser.parse_args(argv)

    try:
        scanned_files = load_scanned_files(args.input_json)
        plan_items = plan_destinations(scanned_files)
        saved_path = save_plan_json(
            plan_items,
            args.output,
            overwrite=args.overwrite,
        )
    except OSError as error:
        target = error.filename or args.input_json
        print(f"오류: {_format_os_error(error)} ({target})", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1

    print(f"입력 파일: {Path(args.input_json).resolve()}")
    print(
        f"전체 {len(scanned_files)}개 중 선택된 {len(plan_items)}개 파일의 목적지를 계획했습니다."
    )
    print(f"계획 JSON 저장 완료: {saved_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
