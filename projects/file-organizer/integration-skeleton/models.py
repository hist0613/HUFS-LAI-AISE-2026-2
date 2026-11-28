"""공통 JSON 규약. TypedDict는 타입 설명이며 실행 중 검증을 대신하지 않는다."""

from typing import Literal, TypedDict

Action = Literal["symlink", "move"]
Method = Literal["rules", "llm", "hybrid"]


class ScannedFile(TypedDict):
    file_id: str
    rel_path: str
    name: str
    ext: str
    size_bytes: int
    mtime: str
    selected: bool


class Rule(TypedDict):
    field: Literal["ext", "name_contains", "modified_year", "modified_month"]
    value: str
    target_dir: str


class Excerpt(TypedDict):
    file_id: str
    text: str
    error: str | None


class LLMRequest(TypedDict):
    files: list[ScannedFile]
    output_dirs: list[str]
    excerpts: list[Excerpt]


class PlanItem(TypedDict):
    plan_id: str
    file_id: str
    action: Action
    target_rel_path: str
    reason: str
    approved: bool


class Plan(TypedDict):
    source_root: str
    output_root: str
    files: list[ScannedFile]
    items: list[PlanItem]


class JournalEntry(TypedDict):
    job_id: str
    seq_no: int
    plan_id: str
    file_id: str
    src_abs_path: str
    dst_abs_path: str
    action: Action
    status: Literal["PENDING", "COMMITTED", "ROLLED_BACK", "FAILED", "CONFLICT"]
    timestamp: str
    created_dirs: list[str]
    message: str
