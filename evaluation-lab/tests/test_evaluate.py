import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import EvaluationError, evaluate, load_jsonl


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.gold = [
            {"id": "a", "label": "testing"},
            {"id": "b", "label": "security"},
            {"id": "c", "label": "frontend"},
        ]
        self.predictions = [
            {"id": "a", "label": "testing", "confidence": 0.9, "probabilities": {"frontend": 0.05, "security": 0.05, "testing": 0.9}},
            {"id": "b", "label": "abstain", "confidence": 0.4, "probabilities": {"frontend": 0.2, "security": 0.4, "testing": 0.4}},
            {"id": "c", "label": "frontend", "confidence": 0.8, "probabilities": {"frontend": 0.8, "security": 0.1, "testing": 0.1}},
        ]

    def test_reports_accuracy_coverage_and_abstention(self):
        report = evaluate(self.gold, self.predictions)
        self.assertEqual(report["dataset_size"], 3)
        self.assertAlmostEqual(report["metrics"]["accuracy"], 2 / 3)
        self.assertAlmostEqual(report["metrics"]["coverage"], 2 / 3)
        self.assertAlmostEqual(report["metrics"]["abstention_rate"], 1 / 3)
        self.assertAlmostEqual(report["metrics"]["selective_accuracy"], 1.0)
        self.assertIsNotNone(report["calibration"])

    def test_rejects_missing_prediction(self):
        with self.assertRaisesRegex(EvaluationError, "missing predictions"):
            evaluate(self.gold, self.predictions[:-1])

    def test_rejects_unknown_label(self):
        rows = [dict(row) for row in self.predictions]
        rows[0]["label"] = "made-up-class"
        with self.assertRaisesRegex(EvaluationError, "unknown label"):
            evaluate(self.gold, rows)

    def test_rejects_bad_probability_sum(self):
        rows = [dict(row) for row in self.predictions]
        rows[0]["probabilities"] = {"frontend": 0.1, "security": 0.1, "testing": 0.1}
        rows[0]["confidence"] = 0.1
        with self.assertRaisesRegex(EvaluationError, "sum to 1"):
            evaluate(self.gold, rows)

    def test_rejects_mixed_calibration_rows(self):
        rows = [dict(row) for row in self.predictions]
        del rows[1]["probabilities"]
        del rows[1]["confidence"]
        with self.assertRaisesRegex(EvaluationError, "every prediction"):
            evaluate(self.gold, rows)

    def test_rejects_duplicate_ids_when_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.jsonl"
            path.write_text('{"id":"x","label":"a"}\n{"id":"x","label":"b"}\n', encoding="utf-8")
            with self.assertRaisesRegex(EvaluationError, "duplicate id"):
                load_jsonl(path, kind="gold")

    def test_all_abstentions_have_null_selective_accuracy(self):
        rows = [{"id": row["id"], "label": "abstain"} for row in self.gold]
        report = evaluate(self.gold, rows)
        self.assertEqual(report["metrics"]["coverage"], 0)
        self.assertIsNone(report["metrics"]["selective_accuracy"])
        self.assertEqual(report["metrics"]["accuracy"], 0)

    def test_rejects_probability_confidence_mismatch(self):
        rows = [dict(row) for row in self.predictions]
        rows[0]["confidence"] = 0.2
        with self.assertRaisesRegex(EvaluationError, "confidence conflicts"):
            evaluate(self.gold, rows)


if __name__ == "__main__":
    unittest.main()
