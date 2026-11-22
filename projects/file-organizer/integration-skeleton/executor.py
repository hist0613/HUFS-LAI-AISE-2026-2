"""Role C: 원본 보호 파일 작업 경계. 실행/복구/되돌리기만 파일을 변경한다."""

from models import JournalEntry, Plan

MOVE_WARNING = (
    "실제로 파일을 이동한 뒤 프로그램을 거치지 않고 외부에서 위치나 이름을 "
    "변경하면 추적이 불가능해 되돌리기(롤백)가 불가능할 수 있습니다."
)


def execute_plan(plan: Plan, journal_path: str, *,
                 move_confirmed: bool = False) -> list[JournalEntry]:
    """승인 계획 + 절대 JSONL 기록 경로 -> 이번 호출에서 추가한 실행 기록.

    TODO: validate_plan/권한 재점검, 승인 항목만 실행, 직전 상태/충돌 재확인.
    새 충돌은 ValueError로 중단하고 재승인 요구; 임의 이름 변경/덮어쓰기 금지.
    TODO: journal에 PENDING 내구 저장 -> 작업 -> COMMITTED 저장, 중복 실행 방지.
    symlink는 원본 변경 금지. move는 명시적 모드 선택과 move_confirmed 필수.
    실패 시 이미 수행한 작업의 기록을 보존하고 예외 전달; 성공처럼 반환 금지.
    """
    raise NotImplementedError("TODO: execute_plan")


def resume_job(plan: Plan, journal_path: str, *,
               move_confirmed: bool = False) -> list[JournalEntry]:
    """저장 계획 + 기존 기록 -> 이번 재개에서 추가한 기록.

    TODO: 기록/계획 일치 확인, PENDING의 실제 상태 대조, 완료 항목 건너뛰기.
    불확실한 소유권/충돌은 중단. move는 경고 재확인. 승인과 경로를 재검증한다.
    """
    raise NotImplementedError("TODO: resume_job")


def rollback_job(journal_path: str) -> list[JournalEntry]:
    """절대 기록 경로 -> 이번 원복의 ROLLED_BACK/CONFLICT 기록 목록.

    TODO: 역순 원복. 직접 만든 링크(끊긴 링크 포함)와 빈 생성 폴더만 삭제.
    대체된 일반 파일/변경된 링크는 보존하고 CONFLICT 기록; 반복 원복은 중복 방지.
    move는 기록과 실제 상태 일치할 때만 복귀, 원래 경로가 차 있으면 충돌.
    원본/출력 경계와 기록을 검증하고 PENDING도 대조한다. 원본 삭제 함수는 만들지 않는다.
    """
    raise NotImplementedError("TODO: rollback_job")
