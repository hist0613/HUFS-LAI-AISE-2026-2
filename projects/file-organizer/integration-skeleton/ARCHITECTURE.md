# 통합 규약과 협업 안내

## 1. 요구사항 범위

원문: `../MILESTONE.md`. 모듈 번호 M3가 아니라 **5절의 3주차까지**가 기준입니다.
따라서 M4/M5도 포함합니다. 아래는 인터페이스만 정의한 상태이며 기능 완료 목록이 아닙니다.

| 주차 / 원문 | 포함 기능 | 담당 파일 / 입력 → 출력 |
|---|---|---|
| 1주차 M0.1 | Windows/Linux 심링크 권한 확인 | safety: 출력 루트 → None 또는 예외 |
| 1주차 M0.2~0.3 | 경로 격리, 이탈 차단, 원본 보호 작업 경계 | safety/executor: 계획 → 검증/허용된 작업 |
| 1주차 M1.1 | 탐색, 숨김/시스템/.git 제외 | scanner: 원본 루트 → ScannedFile 목록 |
| 1~2주차 M1.2 | CLI 체크박스 선택 | cli: 파일 목록 → selected 반영 목록 |
| 1주차 M1.3 | 확장자/이름/수정 연도·월 규칙 | classifier: 선택 목록+Rule 목록 → PlanItem 목록 |
| 2주차 M1.4 | 기존 이름/계획 내 충돌 사전 해결 | planner: Plan → 미승인 Plan |
| 2주차 Role B 표 | 계획 JSON 저장·불러오기 | planner: Plan ↔ JSON 파일 |
| 2주차 M2.1 | 전후 비교, 목적지 수정, 항목 승인·제외 | cli: Plan → 검토한 Plan |
| 2주차 M2.2 | 직전 재확인, 심링크 생성, 새 충돌 시 중단 | executor: 승인 Plan → JournalEntry 목록 |
| 2주차 M2.3~2.4 | 기록, 중단 재개, 중복 방지, 보수적 원복 | journal/executor: 계획+기록 → 추가 기록 |
| 2~3주차 M3.1 | 선택 메타데이터+출력 구조 요약 | content: 목록+루트+추출 결과 → LLMRequest |
| 3주차 M3.2~3.3 | JSON 응답 검증, API 오류 격리, 동일 실행 흐름 연결 | classifier/workflow: 동의한 요청 → Plan |
| 3주차 M4.1 | 깊이 및 사용자 제외 폴더 | scanner: max_depth/exclude_dirs 인자 |
| 3주차 M4.2 | 허용한 문서 앞부분 추출, 실패 사유, 전송 전 검토 | content/cli: 허용 ID → Excerpt 목록/동의 |
| 3주차 M4.3 선택 | 규칙 미일치 파일만 LLM 분류 | classifier: 요청+규칙 → PlanItem 목록 |
| 3주차 M5.1~5.2 | 명시적 실제 이동, 동일 볼륨 제한, 두 차례 경고, 역순 원복 | executor: move 계획+확인 → 기록 |
| 3주차 착수 / 4주차 M6.1 | 폴더/파일 선택, 전후 트리, 충돌 안내, 이력, 원클릭 원복 | gui: 이벤트 → 공통 엔진 호출 지점 |
| 1~3주차 Role D 표 | 공통 테스트 환경과 통합/예외 테스트 자리 | tests: 가상 데이터로 연결 계약 검증 |

M4.2 상세 본문에는 TXT/MD/PDF/DOCX가 있어 네 형식의 추출 계약을 둡니다.
제외 폴더는 원문이 허용한 옵션 방식 하나만 사용합니다. `.organizerignore` 파서는 추가하지 않습니다.
선택 M4.3은 함수 하나만 남기며 기본 분류는 rules, 기본 실행은 symlink입니다.
4주차 비GUI 과제(대용량 성능 개선, 별도 교차 검증 캠페인, MCP, 실행 파일 패키징)와
M8 해시/머클 트리/추적/보안 확장은 제외합니다. 기본 Windows/Linux 지원과 M2 복구 계약은 포함합니다.

## 2. 최소 구조와 책임

모든 Python 파일은 이 폴더 바로 아래에 둡니다. 다단계 패키지/플러그인/추상 클래스는 없습니다.

| 파일 | 책임 |
|---|---|
| models.py | JSON 구조를 설명하는 TypedDict와 Literal만 정의 |
| scanner.py | 파일 메타데이터 탐색과 제외/깊이 처리 |
| content.py | 허용된 본문 추출, LLM용 정보 요약 |
| classifier.py | 규칙/LLM/선택 하이브리드 분류 및 LLM JSON 검증 |
| planner.py | 미리보기 이름 확정, 계획 저장·불러오기 |
| safety.py | 루트/경로/권한 검증 |
| executor.py | 심링크/이동 실행, 중단 재개, 원복; 파일 변경의 유일한 진입점 |
| journal.py | 복구용 JSONL 읽기/추가 저장 |
| workflow.py | 분류→검증→충돌 해결 연결 |
| cli.py / gui.py | 사용자 입력/선택/동의/승인/표시; 파일 처리 알고리즘 없음 |
| main.py | 실행 옵션과 UI 진입 |
| tests/test_contracts.py | Mock 기반 계약 검증, 테스트 전용 샘플 |
| requirements-dev.txt / pytest.ini | pytest 개발 환경 |

본문 읽기는 메타데이터 탐색과 읽기 동의 조건이 달라 content.py로 분리했습니다.
복구는 실행과 동일한 파일 작업 책임이므로 executor.py에 함께 둡니다.
핵심 모듈은 UI를 import하지 않습니다. models는 다른 프로젝트 모듈을 import하지 않습니다.
workflow → classifier/planner/safety, executor → safety/journal 방향만 사용합니다.
planner/journal은 executor를 import하지 않습니다. 순환 import를 만들지 않습니다.

## 3. 공통 데이터 규약

모두 일반 dict/list이고 JSON으로 직렬화할 수 있습니다. TypedDict는 별도의 객체 생성기나
런타임 검증기가 아닙니다. 파일/API에서 읽은 데이터는 해당 입력 함수가 검증합니다.

| 타입 | 필드 / 의미 |
|---|---|
| ScannedFile | file_id, rel_path, name, ext, size_bytes, mtime, selected |
| Rule | field(ext/name_contains/modified_year/modified_month), value, target_dir |
| Excerpt | file_id, text, error(None=성공, 문자열=읽지 못한 사유) |
| LLMRequest | files(선택 파일만), output_dirs(상대 디렉터리), excerpts(허용·성공한 본문만) |
| PlanItem | plan_id(항목 고유 ID), file_id, action(symlink/move), target_rel_path, reason, approved |
| Plan | source_root, output_root, files(선택 스냅샷), items(PlanItem 목록) |
| JournalEntry | job_id, seq_no, plan_id, file_id, src_abs_path, dst_abs_path, action, status, timestamp, created_dirs, message |

Plan은 분류 이후에도 ID→원본 경로를 찾고 저장/재개할 수 있도록 루트와 선택 스냅샷을 함께 보관합니다.
created_dirs는 이 작업이 생성한 빈 폴더만 원복하기 위해 필요합니다.
message는 실패/원복 충돌 표시용이며 성공 시 빈 문자열입니다.
status는 PENDING/COMMITTED/ROLLED_BACK/FAILED/CONFLICT만 사용합니다.
실행 기록은 상태 변경을 추가하는 JSONL입니다. 같은 (job_id, seq_no)의 마지막 상태가 현재 상태입니다.
한 기록 파일은 한 job에 대응하며, 동일 항목의 plan_id와 파일/경로 매핑은 재개 시에도 유지합니다.
새 작업은 새 기록 파일을 사용합니다. 원복 기록에도 원래 작업의 매핑을 유지합니다.

- 경로는 모든 공개 함수에서 **str**. 루트/계획 저장 경로/기록 경로는 정규화한 절대 경로입니다.
- rel_path/target_rel_path/target_dir/output_dirs/exclude_dirs는 `/`로 구분하는 상대 경로입니다.
  드라이브, UNC, 선행 `/`, `..`는 허용하지 않습니다. 루트 자체를 의미하는 target_dir은 `.`입니다.
- UI 경계에서 pathlib로 절대 경로를 만들고, 실제 경계 검증은 safety에서 합니다.
  문자열 접두어 비교만으로 검사하지 않습니다. 원본/결과 루트는 서로 겹칠 수 없습니다.
- 계획/기록 파일은 원본 루트 밖에 둡니다. 실행 시 사용자 목적지와 기록 파일의 충돌도 차단합니다.
- ext는 점 포함 소문자, 확장자가 없으면 빈 문자열. size_bytes는 0 이상 정수입니다.
- mtime/timestamp는 UTC ISO 8601 문자열(예: 2026-11-22T00:00:00Z)입니다.
- Rule은 목록 순서대로 첫 일치를 적용합니다. 연도 값은 YYYY, 월 값은 YYYY-MM입니다.
  규칙 미일치는 계획에서 제외하며 암묵적인 기타 폴더를 만들지 않습니다.
- file_id는 한 번의 탐색/선택/저장/재개 동안 불변. 입력 dict를 임의로 변경하지 않고 새 결과를 반환합니다.
- 선택되지 않은 파일은 분류/본문 읽기/API 전송에서 제외합니다. 파일당 계획은 최대 하나입니다.
- LLM 응답 원문은 `[{"file_id": "...", "target_rel_path": "...", "reason": "..."}]`만 허용합니다.
  절대 루트를 보내지 않으며 파일명/상대 경로/허용 본문은 전송 전 보여줍니다.
- 분류 함수는 symlink/미승인 항목을 반환하고 workflow가 사용자의 명시적 action을 적용합니다.
  한 Plan 안에서 action은 통일합니다. 저장 데이터를 불러와도 자동 승인하지 않습니다.

## 4. 함수 입출력 명세

정확한 매개변수 이름/타입/기본값은 코드가 기준이며 아래 표는 읽기용 요약입니다.
`*` 뒤 인자는 키워드로 전달합니다. 각 함수 docstring에 입력 제한과 TODO가 있습니다.

| 함수 | 입력 | 반환 |
|---|---|---|
| scan_files | source_root; max_depth=None, exclude_dirs=() | list[ScannedFile] |
| select_files | files | list[ScannedFile] |
| extract_excerpts | source_root, files; allowed_ids, max_chars | list[Excerpt] |
| build_llm_request | files, output_root, excerpts | LLMRequest |
| confirm_llm_request | request | bool |
| classify_rules | files, rules | list[PlanItem] |
| parse_llm_response | response_json, files | list[PlanItem] |
| classify_llm | request; endpoint, model | list[PlanItem] |
| classify_hybrid | request, rules; endpoint, model | list[PlanItem] |
| validate_roots | source_root, output_root | None |
| validate_plan | plan | None |
| check_symlink_permission | output_root | None |
| create_plan | source_root, output_root, files, rules; action, method, request, endpoint, model | Plan |
| prepare_review / resolve_conflicts | plan | Plan |
| save_plan / load_plan | plan, path / path | None / Plan |
| review_plan | plan | Plan |
| execute_plan / resume_job | plan, journal_path; move_confirmed=False | list[JournalEntry] |
| rollback_job | journal_path | list[JournalEntry] |
| append_entry / read_entries | journal_path, entry / journal_path | None / list[JournalEntry] |

### 실패 규약

- 미구현: `NotImplementedError`. 성공한 것처럼 빈 결과를 반환하지 않습니다.
- 잘못된 인자/JSON/ID/경로/새 목적지 충돌: `ValueError`.
- 권한/파일 부재/파일 시스템 문제: 표준 `OSError` 및 하위 예외.
- LLM 통신/API 실패: `RuntimeError`. UI에서 오류를 보여주고 규칙 모드로 다시 시도할 수 있습니다.
- 정상인데 대상 없음: `[]`. 승인 항목이 없으면 실행도 아무 작업 없이 `[]`입니다.
- 문서별 읽기 실패는 Excerpt.error, 보수적 원복 중 외부 변경은 CONFLICT 기록으로 전달합니다.
- 실행 중 예외는 그 전에 수행한 작업의 기록을 남기고 전파합니다. UI는 부분 실행 사실과
  기록 경로를 표시하고 재개/원복으로 연결해야 합니다. 임의 자동 재시도/묵시적 이동은 하지 않습니다.

## 5. 호출 순서와 승인 경계

1. UI가 경로를 절대 경로로 정규화 → validate_roots → scan_files → select_files.
2. 규칙 모드면 바로 create_plan으로 전달합니다. 규칙 목록은 UI가 Rule 목록으로 준비합니다.
3. LLM/선택 하이브리드 모드면 허용한 파일만 extract_excerpts → build_llm_request
   → 전송 내용 미리보기/confirm_llm_request → 동의한 요청으로 create_plan.
   내용 읽기를 허용하지 않으면 추출을 생략하고 excerpts=[]로 만듭니다.
4. create_plan은 선택 파일만 분류하고 action/미승인 상태를 통일합니다.
   prepare_review가 validate_plan → resolve_conflicts → validate_plan을 호출합니다.
5. UI가 전후 경로/이름 변경을 보여주고 항목별 승인/제외를 받습니다.
   목적지를 수정하면 prepare_review로 되돌아가 충돌/경로를 재검사한 뒤 다시 승인합니다.
   최종 승인 뒤에는 이름을 바꾸지 않습니다. load_plan도 같은 재검토 절차를 사용합니다.
6. symlink면 권한을 확인하고 execute_plan에 전달합니다. executor 내부에서도 검증합니다.
   move면 모드 선택 시와 최종 실행 직전 MOVE_WARNING을 표시합니다.
   최종 확인을 받은 그 호출에만 move_confirmed=True를 전달합니다. 동의는 저장하지 않습니다.
7. executor는 직전 상태를 대조하고 journal.append_entry로 PENDING을 내구 저장한 뒤
   작업하고 COMMITTED를 저장합니다. 생성 폴더도 중단 시 소유권을 판별할 수 있게 기록합니다.
8. 중단 후 같은 저장 계획/기록을 resume_job에 전달합니다. 원복은 rollback_job에 기록을 전달합니다.
   조회는 read_entries를 사용합니다. 두 UI가 같은 기록 형식을 씁니다.

현재 구현된 것은 **4번의 연결 코드와 GUI 껍데기/실행 안내뿐**입니다.
1~3, 5~8의 내부 동작과 UI 상태 관리는 TODO입니다. GUI 버튼은 해당 이름의 on_* 함수까지
연결되어 있고, 그 안에서 공통 엔진을 호출하는 부분을 담당자가 채웁니다.
빈 Treeview는 표/트리 자리이며 체크박스 동작·실제 데이터 표시·이력 선택도 아직 미구현입니다.

리뷰 반영: `--demo`에서는 demo.py가 샘플 선택/계획/승인/가짜 실행/원복을 연결합니다.
`--gui --demo`는 같은 GUI 위젯을 사용하며 일반 모드의 TODO는 유지합니다.
데모의 검증/분류 대체는 workflow 호출 동안만 적용하고 즉시 해제합니다. 실제 안전 검증은 아닙니다.

## 6. 4명 권장 분담과 TODO

역할명은 원문 A~D를 따릅니다. 실제 팀원 이름은 팀에서 배정합니다.

| 역할 | 주로 수정할 파일 | TODO / 완료 조건 |
|---|---|---|
| A: 탐색·선택·정보 | scanner.py, content.py, cli.py의 select_files | 기본 제외/깊이/ID, 체크박스 선택, 허용 본문 추출, 전송 정보 구성 |
| B: 분류·계획 | classifier.py, planner.py | 규칙/LLM 검증, 선택 하이브리드, 이름 충돌, 계획 저장/불러오기 |
| C: 안전·실행·복구 | safety.py, executor.py, journal.py | OS 권한/경로 검사, 승인 실행, 내구 기록, 중단 재개/중복 방지, 두 모드의 보수적 원복 |
| D: 화면·통합 | gui.py, main.py, cli.py의 나머지, tests/ | CLI 호출 연결, GUI 체크/전후 트리/수정·승인/충돌/이력/원복, 계약 및 통합 테스트 |

models.py/workflow.py는 공동 계약 파일입니다. B/D가 변경안을 정리하고 A~D가 영향받는 부분을 확인합니다.
cli.py는 A/D가 함수 단위로 나누어 같은 함수를 동시에 수정하지 않습니다.
공유 파일을 더 쪼개기보다 이 작은 접점 하나를 작업 전에 조율합니다.

구현 순서는 규칙 기반 스캔→검토→심링크→기록/원복부터 연결하고, 이후 LLM/내용/이동을 채웁니다.
GUI는 공통 함수를 호출하며 독자적인 분류/실행 코드를 만들지 않습니다.
규칙/LLM 설정 화면, 계획 저장/불러오기 동작, 재개 UI도 기존 on_* 함수 안에 연결합니다.

## 7. 협업 규칙

- 자유롭게 바꿀 부분: 맡은 함수의 TODO 내부, 해당 모듈 안의 작은 보조 함수, 담당 기능 테스트.
- 임의로 바꾸지 않을 부분: 공개 함수 이름/매개변수/기본값/반환 타입, JSON 키, ID/경로/승인/오류 규약.
- 새 기능을 넣기 전 원문 Unit/주차를 먼저 확인합니다. 범위 밖이면 이번 구현에서 제외합니다.
- 책임이 다르고 독립적으로 수정할 필요가 있을 때만 파일을 나눕니다.
  함수 하나라는 이유로 파일을 만들거나 base class/manager/service 계층을 추가하지 않습니다.
- 변경이 필요하면 관련 이슈에 기존/변경 시그니처와 JSON 예시, 영향을 받는 호출자를 제시합니다.
  영향을 받는 담당자와 합의 → models/문서/호출부/테스트를 함께 변경 → 통합 확인 순서입니다.
- 인터페이스를 유지한 채 팀원별 브랜치에서 구현합니다. 주차 이슈 번호와 완료 조건을 적고
  담당 파일 위주로 작은 PR을 만듭니다. 이번 스켈레톤 작업에서는 원격 작업을 하지 않습니다.
- 오류를 숨기기 위한 `except Exception: return []`, 실제 처리처럼 보이는 임시 성공값은 금지합니다.
  Mock은 tests 및 명시적 --demo 모드의 demo.py에만 둡니다. 실제 기능의 NotImplementedError는 유지합니다.

AI에게 내부 구현을 요청할 때 사용할 예시:

> ARCHITECTURE.md와 models.py를 먼저 읽어라. 이번 작업은 [파일/함수]의
> [마일스톤 Unit] TODO만 구현한다. 공개 함수 시그니처, 반환 JSON, 경로/오류/승인 규약을
> 유지하라. 다른 담당자의 파일과 기존 프로젝트는 수정하지 마라. 범위 밖 기능, 새 추상 계층,
> 설정 시스템을 추가하지 마라. 계약 변경이 필요하면 먼저 이유와 영향받는 호출부를 제시하라.
> 해당 기능의 실제 동작을 검증하는 최소 테스트를 추가하고 실행 결과를 알려라.

## 8. 검증과 한계

현재 8개 테스트는 모듈 import/타입 힌트, JSON 구조, 함수 간 타입 호환,
선택 파일만 분류, 승인 초기화, 수정 계획 재검증, LLM 입력 일치/실패 전파,
미구현 함수가 성공을 가장하지 않는지 확인합니다. 네트워크와 파일 변경은 하지 않습니다.

추가 데모 테스트 3개는 선택/승인 전달, I/O 차단, Mock 해제, CLI 데모 흐름을 확인합니다.

담당 기능 구현 후에는 그때 의미 있는 실제 테스트를 추가합니다:
경로 이탈/중첩, 충돌 후 재승인, PENDING 중단 복구, 중복 실행/반복 원복,
교체된 파일 보존, 깨진 링크 원복, 이동 동의/동일 볼륨, 잘못된 LLM 응답.
이 기능들은 현재 테스트로 보장하지 않습니다. 기존 코드도 테스트 대상으로 가져오지 않습니다.

최종 설계 점검: 데이터 타입 외 클래스 없음, 실행/복구 엔진 구현 없음,
실제 필요한 I/O/분류/UI 책임만 파일 분리, 연결용 함수만 구현,
MCP/해시/확장 설정/플러그인/자동 재시도/고급 GUI 없음.
