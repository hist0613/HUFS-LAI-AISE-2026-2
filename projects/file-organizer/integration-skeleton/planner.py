"""Role B: 계획의 이름 충돌 해결과 JSON 저장/불러오기."""

from models import Plan


def resolve_conflicts(plan: Plan) -> Plan:
    """검증된 계획 -> 기존 항목/계획 내 충돌을 피한 새 미승인 계획.

    TODO: 확장자를 유지한 '이름 (1).확장자' 확정. 입력 객체는 변경하지 않는다.
    모든 approved=False. 실행 시에는 이 함수를 호출해 이름을 바꾸지 않는다.
    """
    raise NotImplementedError("TODO: resolve_conflicts")


def save_plan(plan: Plan, path: str) -> None:
    """계획 -> 절대 path의 UTF-8 JSON. TODO: Plan 구조 그대로 저장."""
    raise NotImplementedError("TODO: save_plan")


def load_plan(path: str) -> Plan:
    """절대 JSON 경로 -> 계획. TODO: 스키마 검사 후 승인 전부 해제.

    불러온 뒤 workflow.prepare_review를 거쳐 경로/충돌을 다시 검증한다.
    """
    raise NotImplementedError("TODO: load_plan")
