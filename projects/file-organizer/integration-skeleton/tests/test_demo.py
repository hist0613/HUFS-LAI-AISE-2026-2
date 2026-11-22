"""데모의 선택/승인 전달, 실제 파일 작업 격리, 임시 Mock 해제를 검증한다."""

import io
import unittest
from unittest.mock import patch

import demo
import executor
import safety
from models import JournalEntry


class DemoTests(unittest.TestCase):
    def test_selected_and_approved_only_without_io(self):
        files = demo.sample_files()
        files[0]["selected"] = files[2]["selected"] = True
        with patch("builtins.open", side_effect=AssertionError("file I/O")), \
             patch("os.symlink", side_effect=AssertionError("symlink")), \
             patch("os.rename", side_effect=AssertionError("move")), \
             patch("socket.socket", side_effect=AssertionError("network")), \
             patch.object(executor, "execute_plan", side_effect=AssertionError("real executor")):
            plan = demo.create_plan(files)
            self.assertEqual([item["file_id"] for item in plan["items"]], ["f_0001", "f_0003"])
            self.assertFalse(any(item["approved"] for item in plan["items"]))
            self.assertEqual(demo.execute(plan), [])
            plan["items"][1]["approved"] = True
            entries = demo.execute(plan)
            self.assertEqual([entry["file_id"] for entry in entries], ["f_0003"])
            self.assertEqual(set(entries[0]), JournalEntry.__required_keys__)
            undone = demo.rollback(entries)
            self.assertEqual(undone[0]["status"], "ROLLED_BACK")
            self.assertEqual(entries[0]["status"], "COMMITTED")
            self.assertEqual(demo.rollback(undone), [])

    def test_empty_selection_and_mock_restoration(self):
        original = safety.validate_plan
        self.assertEqual(demo.create_plan(demo.sample_files())["items"], [])
        self.assertIs(safety.validate_plan, original)
        with self.assertRaises(NotImplementedError):
            safety.validate_plan(demo.create_plan([]))

    def test_cli_selection_approval_and_rollback(self):
        with patch("builtins.input", side_effect=["f_0001 f_0002", "f_0002", "y"]), \
             patch("sys.stdout", new_callable=io.StringIO) as output:
            demo.run_cli()
        self.assertIn("COMMITTED", output.getvalue())
        self.assertIn("ROLLED_BACK", output.getvalue())
