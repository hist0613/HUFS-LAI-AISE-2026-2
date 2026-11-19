"""선택된 파일 예시 데이터에 기본 분류 목적지 규칙을 적용하고 결과를 출력한다."""

import json

from destination_planner import plan_destinations

files = [
    {
        "file_id": "f_0001",
        "rel_path": "프로젝트A/2026_최종보고서.pdf",
        "name": "2026_최종보고서.pdf",
        "ext": ".pdf",
        "size_bytes": 1048576,
        "mtime": "2026-11-14T10:30:00Z",
        "selected": True,
    },
    {
        "file_id": "f_0002",
        "rel_path": "스크린샷/화면캡처.png",
        "name": "화면캡처.png",
        "ext": ".png",
        "size_bytes": 524288,
        "mtime": "2026-11-14T11:00:00Z",
        "selected": True,
    },
    {
        "file_id": "f_0003",
        "rel_path": "음악/배경음.mp3",
        "name": "배경음.mp3",
        "ext": ".mp3",
        "size_bytes": 3145728,
        "mtime": "2026-11-14T12:00:00Z",
        "selected": True,
    },
    {
        "file_id": "f_0004",
        "rel_path": "압축/백업.zip",
        "name": "백업.zip",
        "ext": ".zip",
        "size_bytes": 204800,
        "mtime": "2026-11-14T13:00:00Z",
        "selected": True,
    },
    {
        "file_id": "f_0005",
        "rel_path": "프로젝트A/메모.txt",
        "name": "메모.txt",
        "ext": ".txt",
        "size_bytes": 100,
        "mtime": "2026-11-13T10:30:00Z",
        "selected": False,
    },
]


if __name__ == "__main__":
    plans = plan_destinations(files)
    print("생성된 정리 계획안(Plan) JSON:")
    print(json.dumps(plans, ensure_ascii=False, indent=2))
    print(f"\n전체 {len(files)}개 중 선택된 {len(plans)}개 파일의 목적지를 결정했습니다.")
