"""연결 계약만 검사한다. Mock 성공은 파일 처리 기능의 완성을 의미하지 않는다."""

import copy
import importlib
import inspect
import json
import unittest
from typing import get_type_hints
from unittest.mock import patch

import classifier
import executor
import models
import scanner
import workflow


def sample_file(file_id: str = "f_0001", selected: bool = True) -> models.ScannedFile:
    return {"file_id": file_id, "rel_path": "보고서.pdf", "name": "보고서.pdf",
            "ext": ".pdf", "size_bytes": 12, "mtime": "2026-11-22T00:00:00Z",
            "selected": selected}


def sample_plan() -> models.Plan:
    # 가상 문자열 경로이며 실제 파일 시스템에는 접근하지 않는다.
    return {"source_root": "C:/Source", "output_root": "C:/Output",
            "files": [sample_file()], "items": [{"plan_id": "p_0001",
            "file_id": "f_0001", "action": "symlink", "target_rel_path": "문서/보고서.pdf",
            "reason": "테스트 전용", "approved": True}]}


class ContractTests(unittest.TestCase):
    def test_modules_import_and_public_annotations_resolve(self):
        for name in ("models", "scanner", "content", "classifier", "planner", "safety",
                     "executor", "journal", "workflow", "cli", "gui", "main"):
            module = importlib.import_module(name)
            for _, function in inspect.getmembers(module, inspect.isfunction):
                if function.__module__ != name:
                    continue
                hints = get_type_hints(function)
                self.assertIn("return", hints, function.__name__)
                for parameter in inspect.signature(function).parameters:
                    self.assertIn(parameter, hints, function.__name__)

    def test_json_models_and_producer_consumer_types(self):
        plan = sample_plan()
        self.assertEqual(json.loads(json.dumps(plan, ensure_ascii=False)), plan)
        self.assertEqual(set(plan), models.Plan.__required_keys__)
        self.assertEqual(set(plan["files"][0]), models.ScannedFile.__required_keys__)
        self.assertEqual(set(plan["items"][0]), models.PlanItem.__required_keys__)
        import cli
        import planner
        import journal
        self.assertEqual(get_type_hints(scanner.scan_files)["return"],
                         get_type_hints(cli.select_files)["files"])
        self.assertEqual(get_type_hints(cli.select_files)["return"],
                         get_type_hints(classifier.classify_rules)["files"])
        self.assertEqual(get_type_hints(classifier.classify_rules)["return"],
                         get_type_hints(models.Plan)["items"])
        self.assertEqual(get_type_hints(planner.resolve_conflicts)["return"],
                         get_type_hints(executor.execute_plan)["plan"])
        self.assertEqual(get_type_hints(executor.execute_plan)["return"],
                         get_type_hints(journal.read_entries)["return"])

    def test_rules_flow_filters_selection_and_resets_approval(self):
        files = [sample_file(), sample_file("f_0002", False)]
        original = copy.deepcopy(files)
        with patch("safety.validate_roots"), patch("safety.validate_plan"), \
             patch("classifier.classify_rules", return_value=sample_plan()["items"]) as classify, \
             patch("planner.resolve_conflicts", side_effect=lambda plan: plan), \
             patch("classifier.classify_llm") as llm:
            result = workflow.create_plan("C:/Source", "C:/Output", files, [], action="move")
        classify.assert_called_once_with([files[0]], [])
        llm.assert_not_called()
        self.assertEqual(result["files"], [files[0]])
        self.assertEqual(result["items"][0]["action"], "move")
        self.assertFalse(result["items"][0]["approved"])
        self.assertEqual(files, original)

    def test_modified_plan_revalidated_without_mutating_input(self):
        plan = sample_plan()
        original = copy.deepcopy(plan)

        def fake_conflicts(draft):
            self.assertFalse(draft["items"][0]["approved"])
            changed = copy.deepcopy(draft)
            changed["items"][0]["target_rel_path"] = "문서/보고서 (1).pdf"
            return changed

        with patch("safety.validate_plan") as validate, \
             patch("planner.resolve_conflicts", side_effect=fake_conflicts):
            result = workflow.prepare_review(plan)
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(validate.call_args.args[0], result)
        self.assertFalse(result["items"][0]["approved"])
        self.assertEqual(plan, original)

    def test_llm_uses_reviewed_request_and_same_plan_pipeline(self):
        files = [sample_file()]
        request: models.LLMRequest = {"files": files, "output_dirs": [], "excerpts": []}
        with patch("safety.validate_roots"), patch("safety.validate_plan"), \
             patch("classifier.classify_llm", return_value=sample_plan()["items"]) as llm, \
             patch("planner.resolve_conflicts", side_effect=lambda plan: plan) as resolve:
            result = workflow.create_plan("C:/Source", "C:/Output", files, [],
                                          method="llm", request=request, endpoint="mock", model="mock")
        llm.assert_called_once_with(request, endpoint="mock", model="mock")
        resolve.assert_called_once()
        self.assertFalse(result["items"][0]["approved"])

    def test_changed_selection_blocks_llm_submission(self):
        request = {"files": [sample_file()], "output_dirs": [], "excerpts": []}
        with patch("safety.validate_roots"), patch("classifier.classify_llm") as llm:
            with self.assertRaises(ValueError):
                workflow.create_plan("C:/Source", "C:/Output", [], [], method="llm", request=request)
        llm.assert_not_called()

    def test_llm_failure_is_not_silently_treated_as_success(self):
        files = [sample_file()]
        request = {"files": files, "output_dirs": [], "excerpts": []}
        with patch("safety.validate_roots"), \
             patch("classifier.classify_llm", side_effect=RuntimeError("API unavailable")), \
             patch("classifier.classify_rules") as rules:
            with self.assertRaises(RuntimeError):
                workflow.create_plan("C:/Source", "C:/Output", files, [], method="llm", request=request)
        rules.assert_not_called()

    def test_stubs_never_claim_to_have_processed_files(self):
        plan = sample_plan()
        for function, args in ((scanner.scan_files, ("C:/Source",)),
                               (classifier.classify_rules, (plan["files"], [])),
                               (executor.execute_plan, (plan, "C:/Output/job.jsonl")),
                               (executor.resume_job, (plan, "C:/Output/job.jsonl")),
                               (executor.rollback_job, ("C:/Output/job.jsonl",))):
            with self.subTest(function=function.__name__):
                with self.assertRaises(NotImplementedError):
                    function(*args)


if __name__ == "__main__":
    unittest.main()
