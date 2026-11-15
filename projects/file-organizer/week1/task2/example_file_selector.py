"""예시 파일 정보 3개에 선택 조건을 적용하고 결과를 출력한다."""

import json

from file_selector import select_files


# test_file_selector.py의 setUp과 동일한 예시 데이터입니다.
# 디스크에 실제 파일이 없어도 이 메타데이터만으로 실행할 수 있습니다.
files = [
    {
        "file_id": "f_0001",
        "rel_path": "프로젝트A/2026_최종보고서.pdf",
        "name": "2026_최종보고서.pdf",
        "ext": ".pdf",
        "size_bytes": 1048576,
        "mtime": "2026-11-14T10:30:00Z",
    },
    {
        "file_id": "f_0002",
        "rel_path": "프로젝트B/2026_최종보고서.pdf",
        "name": "2026_최종보고서.pdf",
        "ext": ".pdf",
        "size_bytes": 2097152,
        "mtime": "2026-11-14T20:30:00+09:00",
    },
    {
        "file_id": "f_0003",
        "rel_path": "프로젝트A/메모.txt",
        "name": "메모.txt",
        "ext": ".txt",
        "size_bytes": 100,
        "mtime": "2026-11-13T10:30:00Z",
    },
]

# 사용자 요구: "프로젝트A 폴더에 있는 PDF만 선택"
# 두 조건을 모두 만족한 파일만 selected=True가 됩니다.
conditions = [
    {"field": "ext", "op": "eq", "value": ".pdf"},
    {"field": "rel_path", "op": "contains", "value": "프로젝트A/"},
]


if __name__ == "__main__":
    result = select_files(files, conditions)

    print("selected가 추가된 전체 결과:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    print("\n파일별 선택 상태:")
    for file_info in result:
        selected_json = json.dumps(file_info["selected"])
        print(f"{file_info['rel_path']} -> selected: {selected_json}")

    selected_count = sum(file_info["selected"] for file_info in result)
    print(f"\n전체 {len(result)}개 중 {selected_count}개 선택됨")
