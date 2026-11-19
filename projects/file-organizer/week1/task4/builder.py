"""
symlink builder using pathlib
"""

from typing import ClassVar, Self
from pathlib import Path
from dataclasses import dataclass
from functools import wraps
from subprocess import list2cmdline
import argparse, ctypes, sys


def requires_admin(method):
    """
    윈도우 환경에서 관리자 권한이 필요할 수 있는 method를 wrapping합니다.
    `OSError: [WinError 1314] 클라이언트가 필요한 권한을 가지고 있지 않습니다`
    """

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if self._needs_elevation:
            runas = ctypes.windll.shell32.ShellExecuteW
            runas.restype = ctypes.c_void_p
            result = runas(
                None,
                "runas",
                sys.executable,
                list2cmdline(sys.argv),
                str(Path.cwd()),
                1,
            )
            if not result or result <= 32:
                raise PermissionError(f"failed or canceled relaunch: {result}")
            raise exit(0)
        return method(self, *args, **kwargs)

    return wrapper


@dataclass
class SymlinkBuilder:
    src: Path
    dest: Path
    _needs_elevation: ClassVar[bool] = sys.platform == "win32" and not ctypes.windll.shell32.IsUserAnAdmin()

    @classmethod
    def from_paths(cls, src: str | Path, dest: str | Path) -> Self:
        return cls(
            src=Path(src).expanduser().absolute(),
            dest=Path(dest).expanduser().absolute(),
        )

    @requires_admin
    def link(self) -> Path:
        src = self.src.resolve(strict=True)  # FileNotFoundError if src does not exist
        self.dest.parent.mkdir(parents=True, exist_ok=True)
        self.dest.symlink_to(src, target_is_directory=src.is_dir())
        return self.dest

    @requires_admin
    def unlink(self) -> None:
        if self.dest.is_symlink():
            self.dest.unlink(missing_ok=True)

    def is_valid(self) -> bool:
        """is_symlink && exists"""
        return self.dest.is_symlink() and self.dest.exists()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="symlink builder using pathlib")
    parser.add_argument("--src", help="source")
    parser.add_argument("--dest", help="destination")
    parser.add_argument("--test", action="store_true", help="test symlink builder")
    args = parser.parse_args()

    if args.test:
        raise NotImplementedError("test not implemented yet")
    else:
        if args.src is None or args.dest is None:
            parser.error("src and dest are required unless --test is set")
        builder = SymlinkBuilder.from_paths(args.src, args.dest)
        builder.link()
        print(f"symlink created: {builder.dest} -> {builder.src}" if builder.is_valid() else "failed to create symlink")
