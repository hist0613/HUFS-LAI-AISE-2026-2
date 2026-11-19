"""plan_io 모듈 및 main CLI의 JSON 입출력·오류 처리 단위 테스트."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from destination_planner import plan_destinations
from main import main
from plan_io import load_scanned_files, save_plan_json


class PlanIoAndCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.sample_files = [
            {
                "file_id": "f_0001",
                "rel_path": "프로젝트/보고서.pdf",
                "name": "보고서.pdf",
                "ext": ".pdf",
                "size_bytes": 1024,
                "mtime": "2026-11-14T10:30:00Z",
                "selected": True,
            },
            {
                "file_id": "f_0002",
                "rel_path": "메모.txt",
                "name": "메모.txt",
                "ext": ".txt",
                "size_bytes": 128,
                "mtime": "2026-11-14T11:00:00Z",
                "selected": False,
            },
        ]

    def _write_json(self, filename: str, content: str) -> Path:
        path = self.root / filename
        path.write_text(content, encoding="utf-8")
        return path

    def test_load_and_save_json_roundtrip(self):
        input_path = self._write_json(
            "scan.json", json.dumps(self.sample_files, ensure_ascii=False)
        )
        loaded = load_scanned_files(input_path)
        self.assertEqual(loaded, self.sample_files)

        plans = plan_destinations(loaded)
        output_path = self.root / "plan.json"
        saved = save_plan_json(plans, output_path)

        self.assertEqual(saved, output_path.absolute())
        saved_data = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(len(saved_data), 1)
        self.assertEqual(saved_data[0]["target_rel_path"], "문서/보고서.pdf")

    def test_save_plan_json_prevents_overwrite_unless_requested(self):
        output_path = self._write_json("plan.json", "existing")
        with self.assertRaises(FileExistsError):
            save_plan_json([], output_path)
        self.assertEqual(output_path.read_text(encoding="utf-8"), "existing")

        save_plan_json([], output_path, overwrite=True)
        self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), [])

    def test_load_scanned_files_rejects_invalid_json_and_schema(self):
        broken_path = self._write_json("broken.json", "{not valid json")
        not_list_path = self._write_json("dict.json", '{"file_id": "f_0001"}')
        bad_item_path = self._write_json("bad_item.json", "[123]")

        for path in (broken_path, not_list_path, bad_item_path):
            with self.subTest(path=path.name), self.assertRaises(ValueError):
                load_scanned_files(path)

    def test_cli_end_to_end_and_overwrite_flag(self):
        input_path = self._write_json(
            "입력.json", json.dumps(self.sample_files, ensure_ascii=False)
        )
        output_path = self.root / "계획.json"

        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            first_code = main([str(input_path), "-o", str(output_path)])
            duplicate_code = main([str(input_path), "-o", str(output_path)])
            overwrite_code = main(
                [str(input_path), "-o", str(output_path), "--overwrite"]
            )

        self.assertEqual(first_code, 0)
        self.assertEqual(duplicate_code, 1)
        self.assertEqual(overwrite_code, 0)
        self.assertIn("계획 JSON 저장 완료", stdout.getvalue())
        self.assertIn("이미 존재", stderr.getvalue())
        result = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(result[0]["file_id"], "f_0001")

    def test_cli_reports_missing_input_and_invalid_content(self):
        output_path = self.root / "plan.json"
        broken_path = self._write_json("broken.json", "[1]")

        with redirect_stderr(io.StringIO()) as stderr:
            missing_code = main([str(self.root / "없는파일.json"), "-o", str(output_path)])
            invalid_code = main([str(broken_path), "-o", str(output_path)])

        self.assertEqual(missing_code, 1)
        self.assertEqual(invalid_code, 1)
        self.assertIn("경로를 찾을 수 없습니다", stderr.getvalue())
        self.assertIn("객체(dict)여야 합니다", stderr.getvalue())
        self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
