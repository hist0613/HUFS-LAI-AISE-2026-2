"""Role C: Windows/Linux 공통 안전 검증. 위반은 ValueError/OSError."""

from models import Plan


def check_symlink_permission(output_root: str) -> None:
    """절대 출력 경로 -> 성공 시 None. TODO: OS별 권한 점검 및 설정 안내 오류.

    테스트 링크가 필요하면 원본 외부에서 만들고 정리한다.
    """
    raise NotImplementedError("TODO: check_symlink_permission")


def validate_roots(source_root: str, output_root: str) -> None:
    """두 절대 루트 -> None. TODO: 같은 경로/상하위 중첩을 실제 경로로 차단."""
    raise NotImplementedError("TODO: validate_roots")


def validate_plan(plan: Plan) -> None:
    """Plan -> None. TODO: 루트, ID 매핑, 선택 여부, 경로 이탈, action 검증.

    심링크/junction을 포함한 실제 경로 확인; move는 같은 볼륨으로 제한.
    파일당 계획 1개, 계획 내 action 통일. 이름 충돌 해결 전에도 호출 가능.
    실행 직전 존재/충돌/원본 상태 재확인은 executor의 책임이다.
    """
    raise NotImplementedError("TODO: validate_plan")
