"""공유 연결 코드. CLI/GUI는 같은 함수를 쓰고 분류 알고리즘을 갖지 않는다."""

import classifier
import planner
import safety
from models import Action, LLMRequest, Method, Plan, Rule, ScannedFile


def create_plan(
    source_root: str,
    output_root: str,
    files: list[ScannedFile],
    rules: list[Rule],
    *,
    action: Action = "symlink",
    method: Method = "rules",
    request: LLMRequest | None = None,
    endpoint: str = "",
    model: str = ""
) -> Plan:
    """선택 파일 -> 미승인 계획. LLM request는 전송 동의 후에만 전달한다.

    연결 코드만 구현됨. TODO(담당 모듈): 분류/검증/충돌 해결 본체 채우기.
    """
    safety.validate_roots(source_root, output_root)
    if action not in ("symlink", "move"):
        raise ValueError("지원하지 않는 실행 방식")
    selected = [file for file in files if file["selected"]]
    if method == "rules":
        items = classifier.classify_rules(selected, rules)
    elif method in ("llm", "hybrid"):
        if request is None or request["files"] != selected:
            raise ValueError("전송을 승인한 요청과 현재 선택 파일이 일치해야 합니다")
        if method == "llm":
            items = classifier.classify_llm(request, endpoint=endpoint, model=model)
        else:
            items = classifier.classify_hybrid(request, rules, endpoint=endpoint, model=model)
    else:
        raise ValueError("지원하지 않는 분류 방식")
    plan: Plan = {
        "source_root": source_root,
        "output_root": output_root,
        "files": selected,
        "items": [{**item, "action": action, "approved": False} for item in items],
    }
    return prepare_review(plan)


def prepare_review(plan: Plan) -> Plan:
    """초안/수정/불러온 계획 -> 경로·충돌을 재검사한 미승인 계획.

    TODO(담당 모듈): 검증/충돌 해결 본체. 이후 화면에서 최종 승인한다.
    """
    unapproved: Plan = {**plan, "items": [{**item, "approved": False} for item in plan["items"]]}
    safety.validate_plan(unapproved)
    prepared = planner.resolve_conflicts(unapproved)
    safety.validate_plan(prepared)
    return prepared
