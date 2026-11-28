"""Role A/D: CLI 입출력. 함수 내부에서 분류/파일 실행 알고리즘을 만들지 않는다."""

from models import LLMRequest, Plan, ScannedFile


def select_files(files: list[ScannedFile]) -> list[ScannedFile]:
    """탐색 목록 -> 체크박스 선택을 반영한 새 목록(동일 ID/순서).

    TODO: selected만 변경, 취소는 모든 selected=False. 원본 목록은 수정하지 않는다.
    """
    raise NotImplementedError("TODO: CLI select_files")


def confirm_llm_request(request: LLMRequest) -> bool:
    """전송할 메타데이터/본문 -> 사용자 동의 여부. TODO: 미리보기 후 확인."""
    raise NotImplementedError("TODO: CLI confirm_llm_request")


def review_plan(plan: Plan) -> Plan:
    """미승인 계획 -> 항목별 승인/제외 및 목적지 수정이 반영된 새 계획.

    TODO: 원본→목적지/이름 변경 표시. 수정 후 workflow.prepare_review 재호출.
    TODO: 재검토한 최종 경로만 승인. 취소 시 모든 approved=False.
    move는 모드 선택 시와 최종 실행 직전 executor.MOVE_WARNING 확인.
    """
    raise NotImplementedError("TODO: CLI review_plan")


def run_cli(source_root: str, output_root: str) -> None:
    """두 절대 루트 -> CLI 상호작용. TODO: ARCHITECTURE의 호출 순서 연결.

    스캔/선택 → 규칙 또는 동의한 LLM 요청 → 계획 → 검토 → 실행.
    계획 저장/불러오기, 기록 기반 재개/되돌리기도 같은 핵심 함수를 호출한다.
    """
    raise NotImplementedError("TODO: CLI 전체 흐름 연결")
