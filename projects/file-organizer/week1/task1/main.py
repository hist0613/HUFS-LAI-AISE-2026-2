"""폴더 경로와 출력 JSON 경로를 받는 CLI 진입점."""
import argparse
import sys
from pathlib import Path

if __package__:
    from .scanner import save_json, scan_files
else:
    from scanner import save_json, scan_files


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="자파: 파일 목록을 JSON으로 저장")
    parser.add_argument("source", help="하위 폴더까지 탐색할 원본 폴더")
    parser.add_argument("-o", "--output", required=True, help="새 JSON 파일 경로")
    args = parser.parse_args(argv)
    try:
        files = scan_files(args.source, exclude_paths=[args.output])
        output = save_json(files, args.output)
    except OSError as error:
        if isinstance(error, PermissionError):
            message = "접근 권한이 없습니다. 폴더 읽기/출력 위치 쓰기 권한을 확인해주세요."
        elif isinstance(error, FileExistsError):
            message = "출력 파일이 이미 존재합니다. 다른 새 파일명을 지정해주세요."
        elif isinstance(error, (FileNotFoundError, NotADirectoryError)):
            message = "원본 폴더 또는 출력 상위 폴더가 없거나, 폴더가 아닌 경로입니다."
        else:
            message = f"파일 작업에 실패했습니다: {error.strerror}"
        print(f"오류: {message} ({error.filename or '경로 확인 필요'})", file=sys.stderr)
        return 1
    print(f"폴더 경로: {Path(args.source).resolve()}")
    for number, item in enumerate(files, 1):
        print(f"{number}. {item['rel_path']}")
    print(f"총 {len(files)}개의 파일을 찾았습니다.")
    print(f"JSON 저장 완료: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
