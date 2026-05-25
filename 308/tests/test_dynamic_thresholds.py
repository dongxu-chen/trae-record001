import unittest
from git_commit_checker.size_analyzer import (
    ChangeSizeAnalyzer,
    FileChangeStats,
    TypeThreshold,
    DEFAULT_TYPE_THRESHOLDS,
)
from git_commit_checker.config import ConfigLoader


class TestTypeThreshold(unittest.TestCase):
    def test_default_thresholds(self):
        self.assertIn("feat", DEFAULT_TYPE_THRESHOLDS)
        self.assertIn("fix", DEFAULT_TYPE_THRESHOLDS)
        self.assertIn("refactor", DEFAULT_TYPE_THRESHOLDS)
        self.assertIn("docs", DEFAULT_TYPE_THRESHOLDS)

    def test_refactor_threshold(self):
        threshold = DEFAULT_TYPE_THRESHOLDS["refactor"]
        self.assertEqual(threshold.max_lines, 1000)
        self.assertEqual(threshold.max_files, 50)

    def test_fix_threshold(self):
        threshold = DEFAULT_TYPE_THRESHOLDS["fix"]
        self.assertEqual(threshold.max_lines, 300)
        self.assertEqual(threshold.max_files, 15)


class TestDynamicThresholds(unittest.TestCase):
    def setUp(self):
        self.config = ConfigLoader()
        self.analyzer = ChangeSizeAnalyzer(self.config)

    def test_get_effective_threshold_base(self):
        self.analyzer.use_dynamic_thresholds = False
        stats = []
        threshold, details = self.analyzer._get_effective_threshold([], "", stats, 0)
        self.assertEqual(threshold.max_lines, 400)
        self.assertFalse(details["used_dynamic"])

    def test_get_effective_threshold_feat(self):
        stats = []
        threshold, details = self.analyzer._get_effective_threshold(["feat"], "", stats, 0)
        self.assertTrue(details["used_dynamic"])
        self.assertEqual(threshold.max_lines, 500)
        self.assertEqual(threshold.max_files, 25)
        self.assertEqual(details["applied_types"], ["feat"])

    def test_get_effective_threshold_refactor(self):
        stats = []
        threshold, details = self.analyzer._get_effective_threshold(["refactor"], "", stats, 0)
        self.assertEqual(threshold.max_lines, 1000)
        self.assertEqual(threshold.max_files, 50)

    def test_get_effective_threshold_multiple_types(self):
        stats = []
        threshold, details = self.analyzer._get_effective_threshold(
            ["feat", "fix"], "", stats, 0
        )
        self.assertEqual(threshold.max_lines, 500)
        self.assertEqual(threshold.max_files, 25)

    def test_get_effective_threshold_auto_detect_refactor(self):
        stats = [
            FileChangeStats("src/old.py", 0, 200, 200),
            FileChangeStats("src/new.py", 195, 0, 195),
        ]
        message = "refactor: move code to new module"
        threshold, details = self.analyzer._get_effective_threshold(
            [], message, stats, 395
        )
        self.assertTrue(details["is_refactoring"])
        self.assertTrue(details["auto_detected_refactor"])
        self.assertEqual(threshold.max_lines, 1000)

    def test_analyze_with_feat_type(self):
        stats = [
            FileChangeStats("src/app.py", 300, 150, 450),
        ]
        result = self.analyzer.analyze(stats, "feat: add big feature", ["feat"])
        self.assertTrue(result.details["used_dynamic"])
        self.assertEqual(result.details["applied_types"], ["feat"])
        self.assertEqual(result.details["effective_max_lines"], 500)

    def test_analyze_with_refactor_type(self):
        stats = [
            FileChangeStats(f"src/file{i}.py", 100, 50, 150)
            for i in range(30)
        ]
        result = self.analyzer.analyze(
            stats, "refactor: major refactoring", ["refactor"]
        )
        self.assertEqual(result.details["effective_max_lines"], 1000)
        self.assertEqual(result.details["effective_max_files"], 50)
        total_lines = sum(s.total for s in stats)
        self.assertEqual(total_lines, 4500)
        self.assertFalse(result.valid)

    def test_analyze_with_docs_type(self):
        stats = [
            FileChangeStats("docs/chapter1.md", 500, 0, 500),
            FileChangeStats("docs/chapter2.md", 400, 0, 400),
        ]
        result = self.analyzer.analyze(stats, "docs: update documentation", ["docs"])
        self.assertEqual(result.details["effective_max_lines"], 1000)
        self.assertTrue(result.valid)

    def test_refactoring_bonus_score(self):
        stats = [
            FileChangeStats("src/old.py", 0, 100, 100),
            FileChangeStats("src/new.py", 95, 0, 95),
        ]
        result = self.analyzer.analyze(
            stats, "refactor: rename class", ["refactor"]
        )
        self.assertTrue(result.details["is_refactoring"])
        self.assertGreater(result.score, 30)

    def test_commit_without_types_uses_base(self):
        self.analyzer.use_dynamic_thresholds = False
        stats = [
            FileChangeStats("src/app.py", 250, 100, 350),
        ]
        result = self.analyzer.analyze(stats, "some change", [])
        self.assertFalse(result.details.get("used_dynamic", False))
        self.assertEqual(result.details.get("applied_threshold"), "base")

    def test_revert_has_very_high_threshold(self):
        stats = [
            FileChangeStats(f"src/file{i}.py", 100, 100, 200)
            for i in range(100)
        ]
        result = self.analyzer.analyze(
            stats, "revert: revert bad commit", ["revert"]
        )
        self.assertEqual(result.details["effective_max_lines"], 10000)
        self.assertEqual(result.details["effective_max_files"], 1000)


if __name__ == "__main__":
    unittest.main()
