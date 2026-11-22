"""Role B: 분류. 경로 충돌 해결, 승인, 파일 실행은 하지 않는다."""

from models import LLMRequest, PlanItem, Rule, ScannedFile


def classify_rules(files: list[ScannedFile], rules: list[Rule]) -> list[PlanItem]:
    """선택 파일 + 순서 있는 규칙 -> 미승인 symlink 계획 목록.

    TODO: 첫 일치 규칙 적용, 미일치 파일은 계획에서 제외. 파일당 최대 1개.
    plan_id는 목록 내 고유값. 이름/확장자/수정 연도·월 규칙만 지원한다.
    """
    raise NotImplementedError("TODO: classify_rules")


def parse_llm_response(response_json: str, files: list[ScannedFile]) -> list[PlanItem]:
    """[{file_id, target_rel_path, reason}] JSON 문자열 -> 공통 PlanItem 목록.

    TODO: 스키마, 알 수 없는/미선택/중복 ID, 절대/상위 경로 차단(ValueError).
    plan_id 부여, action='symlink', approved=False; 응답의 승인값은 허용 안 함.
    실제 파일 시스템 경로 검사는 safety.validate_plan에서 다시 수행한다.
    """
    raise NotImplementedError("TODO: parse_llm_response")


def classify_llm(request: LLMRequest, *, endpoint: str, model: str) -> list[PlanItem]:
    """검토·전송 동의된 요청 -> parse_llm_response로 검증한 계획.

    TODO: JSON 응답 요청 및 파싱 연결. API/통신 실패는 RuntimeError.
    요청을 몰래 규칙 분류로 대체하지 않는다. 규칙 함수는 API에 의존하지 않는다.
    """
    raise NotImplementedError("TODO: classify_llm")


def classify_hybrid(request: LLMRequest, rules: list[Rule], *,
                    endpoint: str, model: str) -> list[PlanItem]:
    """3주차 선택 기능: 규칙 일치 결과 + 미일치 파일의 LLM 계획.

    TODO(선택): 미일치 파일/본문만 재구성해서 전송; 중복 없이 고유 plan_id 부여.
    """
    raise NotImplementedError("TODO(선택): classify_hybrid")
