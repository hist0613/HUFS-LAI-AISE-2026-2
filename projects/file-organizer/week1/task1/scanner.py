"""파일 본문을 읽지 않는 메타데이터 탐색과 JSON 저장 (Python 3.10+)."""
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class ScannedFile(TypedDict):
    file_id: str
    rel_path: str
    name: str
    ext: str
    size_bytes: int
    mtime: str
    selected: bool


def scan_files(source_root, *, exclude_paths=()) -> list[ScannedFile]:
    """하위 폴더까지 탐색한다. 오류 시 부분 결과 대신 OSError를 전달한다.

    ID는 상대 경로 정렬 순서로 부여하며, 한 번의 결과 안에서만 고유하다.
    exclude_paths에는 탐색에서 제외할 출력 파일 경로 등을 전달한다.
    """
    root = Path(source_root).resolve(strict=True)
    if not stat.S_ISDIR(root.stat().st_mode):
        raise NotADirectoryError(20, "폴더 경로를 지정해주세요", str(root))
    excluded = {Path(path).resolve() for path in exclude_paths}
    pending, files = [root], []
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                if entry.name.startswith(".") or entry.name.lower() == "desktop.ini":
                    continue
                metadata = entry.stat(follow_symlinks=False)
                attributes = getattr(metadata, "st_file_attributes", 0)
                if stat.S_ISLNK(metadata.st_mode) or attributes & (
                    stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_REPARSE_POINT
                ):
                    continue  # Windows 정션도 reparse point이므로 따라가지 않는다.
                path = Path(entry.path)
                if path in excluded:
                    continue
                if stat.S_ISDIR(metadata.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(metadata.st_mode):
                    files.append(ScannedFile(
                        file_id="", rel_path=path.relative_to(root).as_posix(),
                        name=path.name, ext=path.suffix.lower(),
                        size_bytes=metadata.st_size,
                        mtime=datetime.fromtimestamp(metadata.st_mtime, timezone.utc)
                        .isoformat(timespec="seconds").replace("+00:00", "Z"),
                        selected=False,
                    ))
    files.sort(key=lambda item: item["rel_path"])
    for number, item in enumerate(files, 1):
        item["file_id"] = f"f_{number:04d}"
    return files


def save_json(files: list[ScannedFile], output_path) -> Path:
    """UTF-8 JSON 배열을 새 파일로 저장한다. 기존 파일은 덮어쓰지 않는다."""
    output = Path(output_path).absolute()
    payload = json.dumps(files, ensure_ascii=False, indent=2) + "\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    return output
