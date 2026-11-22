"""명시적 --demo 전용 Mock. 파일/네트워크 I/O 없이 메모리에서만 동작한다."""

from pathlib import PurePosixPath
from tkinter import StringVar, ttk
from unittest.mock import patch

import workflow
from models import JournalEntry, Plan, PlanItem, Rule, ScannedFile

SOURCE, OUTPUT = "/DEMO/source", "/DEMO/output"
STAMP = "2026-11-22T00:00:00Z"
SAMPLES = {"f_0001": ("보고서.pdf", "문서/보고서.pdf"),
           "f_0002": ("사진.jpg", "사진/사진.jpg"),
           "f_0003": ("메모.txt", "문서/메모.txt")}


def sample_files() -> list[ScannedFile]:
    """매번 독립적인 미선택 샘플 목록을 반환한다. 실제 폴더를 읽지 않는다."""
    return [{"file_id": key, "rel_path": name, "name": name,
             "ext": PurePosixPath(name).suffix, "size_bytes": 100, "mtime": STAMP,
             "selected": False} for key, (name, _) in SAMPLES.items()]


def classify(files: list[ScannedFile], rules: list[Rule]) -> list[PlanItem]:
    """분류 알고리즘 대신 선택 샘플에 대응하는 고정 목적지를 반환한다."""
    return [{"plan_id": "p_" + file["file_id"], "file_id": file["file_id"],
             "action": "symlink", "target_rel_path": SAMPLES[file["file_id"]][1],
             "reason": "MOCK: 고정 샘플 분류", "approved": False}
            for file in files if file["selected"]]


def create_plan(files: list[ScannedFile]) -> Plan:
    """실제 workflow 연결에 가짜 분류/검증을 잠시 공급한다. 종료 시 원복한다."""
    with patch("safety.validate_roots"), patch("safety.validate_plan"), \
         patch("classifier.classify_rules", side_effect=classify), \
         patch("planner.resolve_conflicts", side_effect=lambda plan: plan):
        return workflow.create_plan(SOURCE, OUTPUT, files, [])


def execute(plan: Plan) -> list[JournalEntry]:
    """승인 항목의 가짜 성공 기록만 반환한다. 파일/심링크/기록 파일 생성 없음."""
    files = {file["file_id"]: file for file in plan["files"]}
    return [{"job_id": "MOCK_JOB", "seq_no": index, "plan_id": item["plan_id"],
             "file_id": item["file_id"], "src_abs_path": SOURCE + "/" + files[item["file_id"]]["rel_path"],
             "dst_abs_path": OUTPUT + "/" + item["target_rel_path"], "action": item["action"],
             "status": "COMMITTED", "timestamp": STAMP, "created_dirs": [],
             "message": "MOCK: 실제 파일 작업 없음"}
            for index, item in enumerate((i for i in plan["items"] if i["approved"]), 1)]


def rollback(entries: list[JournalEntry]) -> list[JournalEntry]:
    """데모 결과의 원복 표시만 반환한다. 실제 복구 알고리즘이 아니다."""
    return [{**entry, "status": "ROLLED_BACK", "message": "MOCK: 가짜 되돌리기"}
            for entry in reversed(entries) if entry["status"] == "COMMITTED"]


def run_cli() -> None:
    """샘플 ID 선택 → 계획 확인 → 승인 ID 입력 → 가짜 실행/원복 표시."""
    print("[MOCK 데모] 실제 파일 작업/API 호출 없음. 빈 입력은 선택/승인 취소.")
    files = sample_files()
    for file in files:
        print(file["file_id"], file["name"])
    selected = input("정리할 file_id (공백 구분): ").split()
    for file in files:
        file["selected"] = file["file_id"] in selected
    plan = create_plan(files)
    for item in plan["items"]:
        print(item["file_id"], "->", item["target_rel_path"])
    approved = input("위 계획 중 승인할 file_id (공백 구분): ").split() if plan["items"] else []
    for item in plan["items"]:
        item["approved"] = item["file_id"] in approved
    entries = execute(plan)
    print("MOCK 실행 결과:", entries)
    if entries and input("가짜 되돌리기도 확인할까요? (y/N): ").lower() == "y":
        print("MOCK 원복 결과:", rollback(entries))


def connect_gui(source: StringVar, output: StringVar, files_view: ttk.Treeview,
                before: ttk.Treeview, after: ttk.Treeview, history: ttk.Treeview,
                buttons: dict[str, ttk.Button]) -> None:
    """기존 GUI 위젯에 데모 이벤트를 연결한다. 상태는 창별로 메모리에만 보관."""
    from tkinter import messagebox
    files, plan, entries = sample_files(), None, []
    source.set(SOURCE)
    output.set(OUTPUT)
    files_view.heading("selected", text="선택 (행 더블클릭)")
    after.heading("#0", text="승인 (행 더블클릭)")

    def clear(tree):
        for row in tree.get_children():
            tree.delete(row)

    def scan():
        nonlocal files, plan
        files, plan = sample_files(), None
        for tree in (files_view, before, after):
            clear(tree)
        for file in files:
            files_view.insert("", "end", iid=file["file_id"], values=("☐", file["name"]))

    def select(event):
        nonlocal plan
        row = files_view.identify_row(event.y)
        for file in files:
            if file["file_id"] == row:
                file["selected"] = not file["selected"]
                files_view.set(row, "selected", "☑" if file["selected"] else "☐")
                plan = None  # 선택을 바꾸면 이전 계획/승인 폐기.
                clear(before)
                clear(after)

    def preview():
        nonlocal plan
        plan = create_plan(files)
        clear(before)
        clear(after)
        for item in plan["items"]:
            before.insert("", "end", text=SAMPLES[item["file_id"]][0])
            after.insert("", "end", iid=item["plan_id"], text="☐ " + item["target_rel_path"])

    def approve(event):
        if plan is not None:
            for item in plan["items"]:
                if item["plan_id"] == after.identify_row(event.y):
                    item["approved"] = not item["approved"]
                    after.item(item["plan_id"], text=("☑ " if item["approved"] else "☐ ") + item["target_rel_path"])

    def show_history():
        clear(history)
        for entry in entries:
            history.insert("", "end", values=(entry["status"], entry["file_id"] + " " + entry["message"]))

    def apply():
        nonlocal plan, entries
        if plan is None or not any(item["approved"] for item in plan["items"]):
            messagebox.showinfo("MOCK", "파일 선택 → 미리보기 → 오른쪽 항목 승인 후 실행하세요.", parent=files_view.winfo_toplevel())
            return
        entries = execute(plan)
        plan = None  # 같은 승인으로 중복 실행하지 않음.
        clear(after)
        show_history()

    def undo():
        nonlocal entries
        if any(entry["status"] == "COMMITTED" for entry in entries):
            entries = rollback(entries)
        show_history()

    files_view.bind("<Double-1>", select)
    after.bind("<Double-1>", approve)
    for text, callback in (("파일 탐색", scan), ("계획 미리보기", preview),
                           ("승인 항목 실행", apply), ("실행 이력", show_history),
                           ("선택 이력 되돌리기", undo)):
        buttons[text].configure(command=callback)
    scan()
