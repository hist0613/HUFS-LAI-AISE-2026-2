"""실행 진입점. 기본 실행은 안내, --gui는 빈 화면, --cli는 미구현 안내."""

import argparse
from pathlib import Path


def main() -> int:
    """실행 옵션 -> 종료 코드. TODO: 각 담당 모듈의 내부 구현 완료 후 사용."""
    parser = argparse.ArgumentParser(description="자동 파일 정리 통합 스켈레톤")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gui", action="store_true", help="GUI 기본 화면 열기")
    mode.add_argument("--cli", nargs=2, metavar=("SOURCE", "OUTPUT"), help="CLI 연결 지점")
    args = parser.parse_args()
    if args.gui:
        from gui import launch
        launch()
    elif args.cli:
        from cli import run_cli
        try:
            run_cli(*(str(Path(path).resolve()) for path in args.cli))
        except (NotImplementedError, ValueError, OSError, RuntimeError) as error:
            print(error)
            return 1
    else:
        parser.print_help()
        print("핵심 로직은 TODO입니다. GUI 화면만 실행할 수 있습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
