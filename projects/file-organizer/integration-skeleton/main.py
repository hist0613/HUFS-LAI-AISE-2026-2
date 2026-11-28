"""실행 진입점. --demo는 Mock 흐름, 일반 --gui/--cli는 미구현 스켈레톤."""

import argparse, os
from pathlib import Path


def main() -> int:
    """실행 옵션 -> 종료 코드. TODO: 각 담당 모듈의 내부 구현 완료 후 사용."""
    parser = argparse.ArgumentParser(description="자동 파일 정리 통합 스켈레톤")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gui", action="store_true", help="GUI 기본 화면 열기")
    mode.add_argument("--cli", nargs=2, metavar=("SOURCE", "OUTPUT"), help="CLI 연결 지점")
    parser.add_argument("--demo", action="store_true", help="Mock 데이터로 실행 (실제 파일 작업 없음)")
    args = parser.parse_args()
    if args.demo and args.cli:
        parser.error("--demo는 고정 샘플을 사용합니다. --cli 경로 옵션을 빼주세요.")

    not_headless = os.name != "posix" or os.environ.get("DISPLAY") is not None
    if args.gui and not_headless:
        from gui import launch

        launch(demo=args.demo)
    elif args.demo:
        from demo import run_cli

        if args.gui:
            print(f"headless 환경이므로, cli로 재개합니다.")

        run_cli()
    elif args.cli:
        from cli import run_cli

        try:
            run_cli(*(str(Path(path).resolve()) for path in args.cli))
        except (NotImplementedError, ValueError, OSError, RuntimeError) as error:
            print(error)
            return 1
    else:
        parser.print_help()
        print("핵심 로직은 TODO입니다. --demo 또는 --gui --demo로 Mock 흐름을 확인하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
