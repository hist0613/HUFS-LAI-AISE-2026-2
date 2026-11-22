# 자동 파일 정리: 최소 통합 스켈레톤

기준 문서는 `../MILESTONE.md`의 **5절 주차별 표**입니다.
1~3주차 전체(M0~M5, 선택 M4.3 포함)와 4주차 GUI(M6.1)만 다룹니다.
기존 코드와 독립적인 새 폴더이며 기존 모듈을 가져오지 않습니다.

## 시작하기

Python 3.11 이상, 이 폴더를 작업 디렉터리로 사용합니다.

```powershell
python main.py
python main.py --gui
python -m unittest discover -s tests -v
```

`main.py`는 안내를 출력합니다. `--gui`는 폴더 선택, 빈 표/트리, 버튼을 표시합니다.
GUI 처리 버튼은 미구현 안내를 띄웁니다. 실제 탐색·분류·API 호출·파일 변경은 하지 않습니다.
`python main.py --cli SOURCE OUTPUT`은 미구현 안내와 종료 코드 1을 반환합니다.

## Mock 데이터로 실행하기

```powershell
python main.py --gui --demo
python main.py --demo
```

GUI: 샘플 파일 행 더블클릭으로 선택 → 계획 미리보기 → 오른쪽 행 더블클릭으로 승인
→ 승인 항목 실행 → 실행 이력/되돌리기. 선택을 바꾸면 이전 계획과 승인을 폐기합니다.
CLI: 안내에 따라 file_id를 공백으로 구분해 입력합니다. 빈 입력은 선택/승인하지 않습니다.
`demo.py`의 고정 데이터만 사용하며, 일반 모드의 NotImplementedError는 그대로 유지합니다.
데모의 경로는 표시용이고 실제 파일 조회/변경/API 호출은 없습니다. 이력은 이번 창의 마지막
실행 결과만 메모리에 보관합니다. 검증/분류는 가짜이므로 안전 기능의 구현을 뜻하지 않습니다.

마일스톤의 pytest 환경을 사용하려면:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest -q
```

동일한 테스트를 표준 라이브러리 unittest로도 실행할 수 있습니다.
tkinter는 Windows 일반 Python 설치에 포함됩니다. Linux에서 GUI를 실행하려면
배포판의 Tk 패키지와 디스플레이가 필요합니다. PDF/DOCX/API 패키지는 해당 TODO를
구현할 때 필요한 것만 선정합니다.

## 먼저 읽을 문서

- [ARCHITECTURE.md](ARCHITECTURE.md): 범위, 파일 책임, 데이터/함수 규약, 호출 순서, 분담, TODO, AI 작업 규칙.
- [models.py](models.py): 모든 모듈이 공유하는 JSON 데이터 타입.
- [workflow.py](workflow.py): 실제로 작성된 최소 연결 코드.

테스트는 import/타입/Mock 기반 연결을 확인합니다. 안전 검증, 파일 실행, 복구 기능이
완성됐음을 뜻하지 않습니다. 핵심 함수의 `NotImplementedError`를 담당자가 채워 넣습니다.
