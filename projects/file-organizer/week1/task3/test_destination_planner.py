"""destination_planner 모듈의 기본 분류 및 예외 처리 단위 테스트."""

import copy
import unittest

from destination_planner import (
    build_target_path,
    classify_by_extension,
    filter_selected_files,
    plan_destinations,
)


def _file(file_id: str, name: str, ext: str, selected: bool = True) -> dict:
    return {
        "file_id": file_id,
        "rel_path": f"폴더/{name}",
        "name": name,
        "ext": ext,
        "size_bytes": 1024,
        "mtime": "2026-11-14T10:30:00Z",
        "selected": selected,
    }


class DestinationPlannerTests(unittest.TestCase):
    def setUp(self):
        self.files = [
            _file("f_0001", "최종.PDF", ".PDF", selected=True),
            _file("f_0002", "여행.jpg", ".jpg", selected=True),
            _file("f_0003", "노래.mp3", ".mp3", selected=True),
            _file("f_0004", "README", "", selected=True),
            _file("f_0005", "메모.txt", ".txt", selected=False),
        ]

    def test_classifies_selected_files_into_default_categories(self):
        original = copy.deepcopy(self.files)
        plans = plan_destinations(self.files)

        self.assertEqual(self.files, original)
        self.assertEqual([p["plan_id"] for p in plans], ["p_0001", "p_0002", "p_0003", "p_0004"])
        self.assertEqual([p["file_id"] for p in plans], ["f_0001", "f_0002", "f_0003", "f_0004"])
        self.assertEqual(
            [p["target_rel_path"] for p in plans],
            ["문서/최종.PDF", "이미지/여행.jpg", "음악/노래.mp3", "기타/README"],
        )
        self.assertTrue(all(p["action"] == "symlink" and p["approved"] is False for p in plans))
        self.assertIn("확장자(.pdf)", plans[0]["reason"])
        self.assertIn("기본 분류 규칙", plans[3]["reason"])

    def test_helper_functions_work_independently(self):
        selected = filter_selected_files(self.files)
        self.assertEqual([item["file_id"] for item in selected], ["f_0001", "f_0002", "f_0003", "f_0004"])
        self.assertEqual(classify_by_extension(".pdf"), "문서")
        self.assertIsNone(classify_by_extension(".zip"))
        self.assertEqual(build_target_path("문서", "보고서.pdf"), "문서/보고서.pdf")

    def test_empty_or_all_unselected_returns_empty_plan(self):
        self.assertEqual(plan_destinations([]), [])
        unselected = [{**item, "selected": False} for item in self.files]
        self.assertEqual(plan_destinations(unselected), [])
        self.assertEqual(plan_destinations([{**self.files[0], "selected": "false"}]), [])

    def test_custom_category_mapping_overrides_default(self):
        plans = plan_destinations(self.files[:2], category_by_ext={".pdf": "중요문서"})
        self.assertEqual([p["target_rel_path"] for p in plans], ["중요문서/최종.PDF", "기타/여행.jpg"])

    def test_rejects_unsafe_names_and_missing_fields(self):
        invalid_items = [
            {**self.files[0], "name": "../탈출.pdf"},
            {**self.files[0], "name": "하위/파일.pdf"},
            {**self.files[0], "name": "하위\\파일.pdf"},
            {**self.files[0], "name": ""},
            {**self.files[0], "file_id": ""},
        ]
        for item in invalid_items:
            with self.subTest(item=item), self.assertRaises(ValueError):
                plan_destinations([item])


if __name__ == "__main__":
    unittest.main()
