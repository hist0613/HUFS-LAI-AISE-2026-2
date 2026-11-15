"""
symlink builder using pathlib
"""

from typing import Self
from pathlib import Path
from dataclasses import dataclass
import argparse


@dataclass
class SymlinkBuilder:
    src: Path
    dest: Path

    @classmethod
    def from_paths(cls, src: str | Path, dest: str | Path) -> Self:
        return cls(
            src=Path(src).expanduser().absolute(),
            dest=Path(dest).expanduser().absolute(),
        )

    def link(self) -> Path:
        src = self.src.resolve(strict=True)  # FileNotFoundError if src does not exist
        self.dest.parent.mkdir(parents=True, exist_ok=True)
        self.dest.symlink_to(src, target_is_directory=src.is_dir())
        return self.dest

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
        print(
            f"symlink created: {builder.dest} -> {builder.src}"
            if builder.is_valid()
            else "failed to create symlink"
        )
