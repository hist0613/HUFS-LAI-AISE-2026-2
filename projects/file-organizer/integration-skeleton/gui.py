"""Role D: tkinter 기본 화면과 이벤트 자리. 처리 로직은 공통 핵심 모듈에 둔다."""

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk


def on_scan(source_root: str) -> None:
    """절대 원본 경로 -> 파일 체크 목록 갱신. TODO: scanner.scan_files 연결.

    max_depth/exclude_dirs 입력, selected 체크 변경은 화면에서 관리한다.
    """
    raise NotImplementedError("TODO: 탐색 결과 표시와 체크박스 선택 연결")


def on_preview(source_root: str, output_root: str) -> None:
    """두 절대 루트 -> 미승인 계획과 전후 트리 표시. TODO: workflow.create_plan.

    TODO: 규칙 입력, rules/llm/hybrid 및 symlink/move 선택, 본문 읽기 허용.
    content.build_llm_request 결과를 전송 전에 보여주고 동의받는다.
    경로 수정은 workflow.prepare_review 재호출; 확정 경로에만 항목별 승인.
    move 선택 시 MOVE_WARNING 확인. 계획 저장/불러오기 버튼도 이 화면에 연결.
    """
    raise NotImplementedError("TODO: 계획 생성, 비교, 수정, 승인 화면 연결")


def on_execute() -> None:
    """화면의 승인 계획 -> 실행 결과 표시. TODO: executor.execute_plan 연결.

    move 최종 경고 확인, 기록 저장 경로 선택. 실패/새 충돌은 재검토 안내.
    """
    raise NotImplementedError("TODO: 승인 계획 실행 연결")


def on_history() -> None:
    """사용자가 선택한 기록 -> 이력 표 표시. TODO: journal.read_entries 연결.

    이력에서 중단 작업을 선택하면 executor.resume_job에 저장 계획과 기록 전달.
    """
    raise NotImplementedError("TODO: 실행 이력과 중단 작업 재개 연결")


def on_rollback() -> None:
    """선택된 실행 이력 -> 원클릭 원복 결과. TODO: executor.rollback_job 연결."""
    raise NotImplementedError("TODO: 선택 이력 되돌리기 연결")


def launch(*, demo: bool = False) -> None:
    """최소 화면 실행. 폴더 선택/버튼 연결만 구현; 처리 이벤트는 명시적 TODO."""
    root = tk.Tk()
    root.title("자동 파일 정리 — " + ("MOCK 데모 (실제 작업 없음)" if demo else "통합 스켈레톤"))
    root.geometry("900x600")
    source, output = tk.StringVar(), tk.StringVar()
    for label, variable in (("원본 폴더", source), ("결과 폴더", output)):
        row = ttk.Frame(root)
        row.pack(fill="x", padx=10, pady=5)
        ttk.Label(row, text=label, width=12).pack(side="left")
        ttk.Entry(row, textvariable=variable, state="readonly" if demo else "normal").pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="선택", state="disabled" if demo else "normal", command=lambda v=variable: v.set(
            filedialog.askdirectory(parent=root) or v.get())).pack(side="left")

    def invoke(callback: Callable[[], None]) -> None:
        """UI 경계에서만 미구현/기본 오류를 표시한다."""
        try:
            callback()
        except (NotImplementedError, ValueError, OSError, RuntimeError) as error:
            messagebox.showinfo("처리 안내", str(error), parent=root)

    toolbar = ttk.Frame(root)
    toolbar.pack(fill="x", padx=10)
    buttons = {}
    for text, callback in (
        ("파일 탐색", lambda: on_scan(source.get())),
        ("계획 미리보기", lambda: on_preview(source.get(), output.get())),
        ("승인 항목 실행", on_execute), ("실행 이력", on_history),
        ("선택 이력 되돌리기", on_rollback),
    ):
        buttons[text] = ttk.Button(toolbar, text=text, command=lambda fn=callback: invoke(fn))
        buttons[text].pack(side="left")
    ttk.Label(root, text=("MOCK: 파일 행 더블클릭 → 미리보기 → 오른쪽 행 더블클릭 승인 → 실행 (파일 변경 없음)"
                         if demo else "미구현 스켈레톤: 실제 파일 작업은 수행하지 않습니다.")).pack(pady=8)
    files = ttk.Treeview(root, columns=("selected", "file"), show="headings", height=5)
    files.heading("selected", text="선택 (체크박스 연결 TODO)")
    files.heading("file", text="탐색된 파일")
    files.pack(fill="x", padx=10)
    comparison = ttk.Frame(root)
    comparison.pack(fill="both", expand=True, padx=10, pady=8)
    comparison_trees = []
    for title in ("정리 전", "정리 후 · 이름 충돌/경로 수정/승인 TODO"):
        panel = ttk.LabelFrame(comparison, text=title)
        panel.pack(side="left", fill="both", expand=True)
        tree = ttk.Treeview(panel)
        tree.pack(fill="both", expand=True)
        comparison_trees.append(tree)
    history = ttk.Treeview(root, columns=("status", "message"), show="headings", height=4)
    history.heading("status", text="실행 상태")
    history.heading("message", text="기록 / 충돌 안내")
    history.pack(fill="x", padx=10, pady=8)
    if demo:
        from demo import connect_gui
        connect_gui(source, output, files, *comparison_trees, history, buttons)
    root.mainloop()
