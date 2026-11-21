# Week 1 / Task 1

Python 3.10 이상, 외부 패키지 없이 실행한다. CMD에서 저장소 루트 기준:

```bat
python projects\file-organizer\week1\task1\main.py "C:\작업 폴더" -o "%TEMP%\japa-scan.json"
python -B -m unittest discover -s projects/file-organizer/week1/task1 -v
```

- 원본 폴더와 출력 상위 폴더는 존재해야 한다. 기존 출력 파일은 덮어쓰지 않는다.
- 상대 출력 경로는 CMD의 현재 작업 폴더 기준이며, 완료 시 전체 저장 경로를 출력한다.
- 하위 폴더를 포함한다. 점으로 시작하는 항목, desktop.ini(대소문자 무관),
  Windows 숨김 항목, 심볼릭 링크와 정션을 제외한다. 지정한 출력 경로도 제외한다.
- 상대 경로를 정렬하여 f_0001부터 ID를 붙인다. 파일이 추가/삭제되면 ID는 바뀔 수 있다.
- JSON은 UTF-8 배열이며 rel_path는 / 구분자, ext는 소문자, mtime은 UTC 초 단위다.
  selected는 false이고, 절대 경로는 저장하지 않는다. 파일 본문을 읽거나 수정하지 않는다.
- 다른 모듈은 scan_files(source_root, exclude_paths=[output_path])와
  save_json(files, output_path)를 각각 호출할 수 있다. 파일 시스템 오류는 OSError로 전달한다.
- Task 2는 json.load()로 배열을 읽어 file_id를 기준으로 selected를 바꾸면 된다.
  실제 파일 경로는 별도로 전달받은 source_root / rel_path로 구성한다.
  외부에서 편집한 JSON을 사용할 때는 경로 이탈·링크를 다시 검증해야 한다.
- 실행 결과는 저장소 밖에 보관한다. 이 폴더의 *.json과 Python 캐시는 Git에서 제외한다.
