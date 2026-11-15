import copy
import unittest

from file_selector import select_files


class FileSelectorTests(unittest.TestCase):
    def setUp(self):
        self.files = [
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

    def test_missing_or_empty_conditions_select_nothing(self):
        for conditions in (None, []):
            with self.subTest(conditions=conditions):
                result = select_files(self.files, conditions)
                self.assertEqual([f["selected"] for f in result], [False, False, False])

    def test_combined_conditions_select_only_matching_file_and_preserve_metadata(self):
        original = copy.deepcopy(self.files)
        result = select_files(self.files, [
            {"field": "ext", "op": "eq", "value": ".pdf"},
            {"field": "rel_path", "op": "contains", "value": "프로젝트A/"},
            {"field": "name", "op": "contains", "value": "최종"},
            {"field": "size_bytes", "op": "lte", "value": 1048576},
        ])
        self.assertEqual([f["selected"] for f in result], [True, False, False])
        self.assertEqual(self.files, original)
        self.assertEqual(
            [{k: v for k, v in f.items() if k != "selected"} for f in result], original
        )

    def test_file_id_list_selects_only_explicit_ids(self):
        result = select_files(self.files, [
            {"field": "file_id", "op": "in", "value": ["f_0001", "f_0003"]}
        ])
        self.assertEqual([f["selected"] for f in result], [True, False, True])

    def test_modification_time_compares_instants_across_timezones(self):
        result = select_files(self.files, [
            {"field": "mtime", "op": "gte", "value": "2026-11-14T19:30:00+09:00"},
            {"field": "mtime", "op": "lte", "value": "2026-11-14T10:30:00Z"},
        ])
        self.assertEqual([f["selected"] for f in result], [True, False, False])

    def test_invalid_conditions_raise_instead_of_silently_selecting(self):
        for condition in (
            {"field": "extension", "op": "eq", "value": ".pdf"},
            {"field": "ext", "op": "unknown", "value": ".pdf"},
            {"field": "ext", "op": "eq"},
        ):
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                select_files(self.files, [condition])

    def test_empty_input_and_previous_selection(self):
        self.assertEqual(select_files([]), [])
        self.files[0]["selected"] = True
        self.assertIs(select_files(self.files)[0]["selected"], False)


if __name__ == "__main__":
    unittest.main()
