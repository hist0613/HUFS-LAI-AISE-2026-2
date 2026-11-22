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


def test_symlink_builder() -> None:
    from tempfile import TemporaryDirectory
    from unittest import TestCase

    check = TestCase()
    with TemporaryDirectory() as temp:
        root = Path(temp)
        file, folder = root / "file.txt", root / "한글 폴더"
        folder.mkdir()

        for src in (file, folder):
            content = src / "sample.txt" if src.is_dir() else src
            content.write_text("hello", encoding="utf-8")
            dest = root / "nested" / "links" / src.name
            builder = SymlinkBuilder.from_paths(str(src), str(dest))
            assert not builder.is_valid()  # link 없기에 not valid해야

            plain = SymlinkBuilder.from_paths(src, src)
            assert not plain.is_valid()  # 파일/폴더 그 자체는 symlink가 아니므로 not valid해야
            with check.assertRaises(FileExistsError):
                plain.link()  # dest가 이미 있는 link는 실패해야
            plain.unlink()  # is_symlink가 아니므로 unlink는 no-op
            assert content.read_text(encoding="utf-8") == "hello"  # L82에서 작성한 내용 유지돼야

            created = builder.link()
            assert created == dest  # link() -> dest를 반환하니 동일해야
            assert builder.is_valid() and dest.samefile(src)  # symlink는 valid하면서 src와 동일한 파일/폴더를 가리켜야
            linked_content = dest / "sample.txt" if src.is_dir() else dest
            assert linked_content.read_text(encoding="utf-8") == "hello"  # linked src의 내용이 src와 동일해야
            linked_content.write_text("updated", encoding="utf-8")
            assert content.read_text(encoding="utf-8") == "updated"  # 원본도 업데이트돼 동일해야

            with check.assertRaises(FileExistsError):
                builder.link()  # 이미 있는 symlink를 다시 만드려면 실패해야
            assert dest.samefile(src)

            builder.unlink()
            assert src.exists() and not dest.is_symlink()  # unlink 후 src는 존재하고, dest는 symlink 아니어야
            assert content.read_text(encoding="utf-8") == "updated"  # src 내용은 유지돼야

            builder.link()  # L106의 unlink 복구
            content.unlink()  # file.txt or sample.txt 삭제 (SymlinkBuilder가 아닌 Path.unlink()임)
            if src.is_dir():
                src.rmdir()
            assert dest.is_symlink() and not builder.is_valid()  # 깨진 symlink니 is_symlink지만, is_valid는 아니어야
            builder.unlink()  # 깨진 symlink 제거
            builder.unlink()  # is_symlink가 아니므로 no-op
            assert not dest.is_symlink() and not dest.exists()  # symlink도 아니고, 존재하지도 않아야

            with check.assertRaises(FileNotFoundError):
                builder.link()  # src가 없기에 link는 실패해야
            assert not dest.is_symlink()  # link 실패니 symlink 없어야
            print(f"PASS: {src.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="symlink builder using pathlib")
    parser.add_argument("--src", help="source")
    parser.add_argument("--dest", help="destination")
    parser.add_argument("--test", action="store_true", help="test symlink builder")
    args = parser.parse_args()

    if args.test:
        test_symlink_builder()
        input("press enter to exit: ")
    else:
        if args.src is None or args.dest is None:
            parser.error("src and dest are required unless --test is set")
        builder = SymlinkBuilder.from_paths(args.src, args.dest)
        builder.link()
        print(f"symlink created: {builder.dest} -> {builder.src}" if builder.is_valid() else "failed to create symlink")
