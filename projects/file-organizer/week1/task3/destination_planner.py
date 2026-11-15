"""선택된 파일 목록에 대해 규칙 기반 분류 목적지 계획(Plan)을 생성한다."""

from pathlib import PurePosixPath
from typing import Any, TypedDict

DEFAULT_CATEGORY = "기타"

CATEGORY_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "문서": (
        ".pdf", ".doc", ".docx", ".txt", ".md", ".hwp",
        ".hwpx", ".ppt", ".pptx", ".xls", ".xlsx", ".csv",
    ),
    "이미지": (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"),
    "음악": (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"),
}


class PlanItem(TypedDict):
    """MILESTONE.md 표준 정리 계획안 항목 규격."""

    plan_id: str
    file_id: str
    action: str
    target_rel_path: str
    reason: str
    approved: bool


def _validate_single_segment(value: Any, field_name: str) -> str:
    """단일 폴더·파일명만 허용해 상위/하위 경로 이탈을 차단한다."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} 값은 비어 있지 않은 문자열이어야 합니다.")
    if value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"안전하지 않은 {field_name} 값입니다: {value!r}")
    return value


def filter_selected_files(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """전체 목록에서 selected가 정확히 True인 파일만 골라낸다."""
    selected_files: list[dict[str, Any]] = []
    for file_info in files:
        # 문자열 "false" 같은 truthy 값 오인식을 막기 위해 bool True만 허용한다.
        if file_info.get("selected") is True:
            selected_files.append(file_info)
    return selected_files


def validate_file_info(file_info: dict[str, Any]) -> tuple[str, str]:
    """선택된 파일의 필수 식별자와 안전한 파일명을 검증해 반환한다."""
    file_id = file_info.get("file_id")
    if not isinstance(file_id, str) or not file_id.strip():
        raise ValueError("선택된 파일에는 유효한 file_id가 필요합니다.")
    file_name = _validate_single_segment(file_info.get("name"), "name")
    return file_id, file_name


def _normalize_ext_text(raw_extension: str) -> str:
    """확장자 문자열을 공백 제거·소문자·선행 점(.) 형식으로 통일한다."""
    extension = raw_extension.strip().lower()
    if extension and not extension.startswith("."):
        return f".{extension}"
    return extension


def extract_extension(file_info: dict[str, Any]) -> str:
    """파일 메타데이터 ext(없으면 파일명 끝)에서 소문자 확장자를 추출한다."""
    raw_extension = file_info.get("ext")
    if raw_extension is None:
        file_name = str(file_info.get("name", ""))
        return PurePosixPath(file_name).suffix.lower()
    if not isinstance(raw_extension, str):
        raise ValueError("ext 값은 문자열이어야 합니다.")
    return _normalize_ext_text(raw_extension)


def classify_by_extension(
    extension: str,
    category_by_ext: dict[str, str] | None = None,
) -> str | None:
    """확장자 규칙에 맞는 카테고리를 찾고, 없으면 None을 반환한다."""
    if category_by_ext is not None:
        for raw_ext, category in category_by_ext.items():
            if extension == _normalize_ext_text(raw_ext):
                return category
        return None

    for category, extensions in CATEGORY_EXTENSIONS.items():
        if extension in extensions:
            return category
    return None


def classify_file(
    file_info: dict[str, Any],
    category_by_ext: dict[str, str] | None = None,
) -> tuple[str, str]:
    """분류 규칙을 순서대로 적용해 (카테고리, 분류 사유)를 결정한다."""
    extension = extract_extension(file_info)

    # 1순위: 확장자 규칙 (추후 키워드·LLM 규칙도 같은 방식으로 이 앞에 추가 가능)
    category = classify_by_extension(extension, category_by_ext)
    if category is not None:
        return category, f"확장자({extension}) 규칙 일치 -> {category}"

    # 기본값: 어떤 규칙에도 해당하지 않으면 기타로 분류한다.
    return DEFAULT_CATEGORY, f"기본 분류 규칙 -> {DEFAULT_CATEGORY}"


def build_target_path(category: str, file_name: str) -> str:
    """카테고리 폴더명과 파일명을 검증한 뒤 목적지 상대 경로를 조합한다."""
    safe_category = _validate_single_segment(category, "category")
    safe_name = _validate_single_segment(file_name, "name")
    return f"{safe_category}/{safe_name}"


def create_plan_item(
    plan_number: int,
    file_id: str,
    target_rel_path: str,
    reason: str,
) -> PlanItem:
    """MILESTONE.md 표준 형식의 정리 계획 항목 1개를 생성한다."""
    return PlanItem(
        plan_id=f"p_{plan_number:04d}",
        file_id=file_id,
        action="symlink",
        target_rel_path=target_rel_path,
        reason=reason,
        approved=False,
    )


def plan_destinations(
    files: list[dict[str, Any]],
    category_by_ext: dict[str, str] | None = None,
) -> list[PlanItem]:
    """선택된 파일들의 분류 목적지 계획을 단계별로 생성한다."""
    selected_files = filter_selected_files(files)
    plan_items: list[PlanItem] = []

    for plan_number, file_info in enumerate(selected_files, start=1):
        file_id, file_name = validate_file_info(file_info)
        category, reason = classify_file(file_info, category_by_ext)
        target_rel_path = build_target_path(category, file_name)
        plan_item = create_plan_item(plan_number, file_id, target_rel_path, reason)
        plan_items.append(plan_item)

    return plan_items
