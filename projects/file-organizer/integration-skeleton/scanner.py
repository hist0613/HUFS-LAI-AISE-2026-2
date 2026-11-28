"""Role A: 파일 탐색. 선택 UI, 분류, 파일 변경은 하지 않는다."""

from models import ScannedFile


def scan_files(
    source_root: str, *, max_depth: int | None = None, exclude_dirs: tuple[str, ...] = ()
) -> list[ScannedFile]:
    """절대 원본 경로 -> 파일 목록. rel_path는 '/' 상대 경로, selected=False.

    TODO: 숨김/시스템/.git 제외, 심링크 디렉터리 미추적, 안정적인 ID 부여.
    TODO: 루트 파일 깊이=0, None=무제한, 음수는 ValueError.
    exclude_dirs는 원본 기준 상대 디렉터리. 사용자 제외는 이 옵션 하나로 제공.
    """
    raise NotImplementedError("TODO: scan_files")
