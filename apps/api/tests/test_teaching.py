"""主观题评分证据与课程交叉引用回归检查。"""
import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app import teaching


class TeachingTest(unittest.TestCase):
    def test_course_links(self):
        def rows(relative):
            path = teaching.KB_DIR / relative
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

        course = teaching.course()
        abilities = {item["id"]: item for item in course["abilities"]}
        questions = {item["qid"]: item for item in rows("graph/questions.jsonl")}
        knowledge = {item["kp_id"] for item in rows("graph/nodes.jsonl")}
        tested_abilities = set()
        for ability in abilities.values():
            self.assertLessEqual(set(ability["prerequisites"]), abilities.keys())
        linked = set()
        for edge in rows("graph/question_edges.jsonl"):
            self.assertLess(questions[edge["source"]]["layer"], questions[edge["target"]]["layer"])
            self.assertTrue(edge["why"])
            linked.update((edge["source"], edge["target"]))
        self.assertEqual(linked, questions.keys())
        for case in course["cases"]:
            self.assertTrue(case["theme"])
            self.assertLessEqual(set(case["kp_ids"]), knowledge)
            self.assertLessEqual(set(case["question_ids"]), questions.keys())
            self.assertEqual(sum(item["points"] for item in case["rubric"]), 10)
            for item in case["rubric"]:
                teaching.Criterion.model_validate(item)
                self.assertIn(item["ability_id"], abilities)
                tested_abilities.add(item["ability_id"])
            scenario = case["scenario"]
            self.assertIn(scenario["criterion_id"], {item["id"] for item in case["rubric"]})
            self.assertEqual(len(scenario["choices"]), len({item["id"] for item in scenario["choices"]}))
            self.assertGreaterEqual(len(scenario["choices"]), 2)
            flagged = [
                teaching.diagnose(teaching.ReviewRequest(case_id=case["id"], answer=answer))["diagnoses"]
                for _, answer in case["demo_responses"]
            ]
            self.assertTrue(flagged[0])
            self.assertFalse(flagged[-1])
        self.assertEqual(tested_abilities, abilities.keys())

    def test_review_checks_points_quotes_and_error_ids(self):
        case = teaching.course()["cases"][0]
        rubric = [teaching.Criterion.model_validate(item) for item in case["rubric"]]
        answer = "两份报告总和相同，但甲的 B 区更高。"
        raw = {"items": [
            {"id": "P1", "score": 1, "quote": "总和相同", "feedback": "没有展示计算", "error_ids": ["unknown"]},
            {"id": "P2", "score": 3, "quote": "甲的 B 区更高", "feedback": "指出局部差异", "error_ids": ["P2-E1"]},
            {"id": "P3", "score": 0, "quote": "", "feedback": "未提出验证资料", "error_ids": []},
        ]}
        payload = teaching.ReviewRequest(case_id=case["id"], answer=answer)
        with patch.object(teaching.llm, "LLM_PROVIDER", "test"), patch.object(teaching.llm, "LLM_API_KEY", "test"):
            with patch.object(teaching.llm, "_http_chat", return_value=json.dumps(raw)):
                result = teaching.review(payload)
            self.assertEqual(result["total"], 4)
            self.assertEqual([item["error_ids"] for item in result["items"]], [[], [], []])
            raw["items"][0]["quote"] = "作答中不存在的引文"
            with patch.object(teaching.llm, "_http_chat", return_value=json.dumps(raw)):
                with self.assertRaises(HTTPException) as caught:
                    teaching.review(payload)
            self.assertEqual(caught.exception.status_code, 502)
        raw["items"][0].update(score=5, quote="总和相同")
        with self.assertRaises(ValueError):
            teaching.normalize_review(rubric, answer, raw)

    def test_model_off_returns_unavailable_instead_of_guessing(self):
        with patch.object(teaching.llm, "LLM_PROVIDER", "mock"):
            with self.assertRaises(HTTPException) as caught:
                teaching.review(teaching.ReviewRequest(case_id="power-map", answer="作答"))
        self.assertEqual(caught.exception.status_code, 503)

    def test_scenario_grades_selected_branch_and_validates_diagnostic_evidence(self):
        raw = {"items": [
            {"id": "P1", "score": 0, "quote": "", "feedback": "无计算"},
            {"id": "P2", "score": 0, "quote": "", "feedback": "结论超出证据"},
            {"id": "P3", "score": 0, "quote": "", "feedback": "无验证"},
        ], "diagnoses": [
            {"criterion_id": "P2", "error_id": "P2-E1", "label": "ignored", "quote": "等价", "reason": "过早下结论"},
            {"criterion_id": "P2", "error_id": "", "label": "伪造引文", "quote": "无此作答", "reason": ""},
        ]}
        with patch.object(teaching.llm, "LLM_PROVIDER", "test"), patch.object(teaching.llm, "LLM_API_KEY", "test"):
            with patch.object(teaching.llm, "_http_chat", return_value=json.dumps(raw)) as model:
                result = teaching.review(teaching.ReviewRequest(
                    case_id="power-map", answer="两份报告等价。", scenario={"choice": "resolution"},
                ))
            payload = json.loads(model.call_args.args[0][1]["content"])
            self.assertIn("135", payload["学生取得的补充证据"])
            self.assertIn("135", payload["量规"][2]["expected"])
            self.assertEqual([entry["label"] for entry in result["diagnoses"]], ["用总体相同推断局部相同"])
            self.assertEqual(result["diagnoses"][0]["quote"], "等价")
