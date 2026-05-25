import unittest
from git_commit_checker.config import ConfigLoader
from git_commit_checker.size_analyzer import ChangeSizeAnalyzer, FileChangeStats


class TestChangeSizeAnalyzer(unittest.TestCase):
    def setUp(self):
        self.config = ConfigLoader()
        self.analyzer = ChangeSizeAnalyzer(self.config)

    def test_small_commit(self):
        stats = [
            FileChangeStats("src/auth/login.py", 10, 5, 15),
        ]
        result = self.analyzer.analyze(stats, "feat: add login")
        self.assertTrue(result.valid)
        self.assertEqual(result.details["total_lines_changed"], 15)
        self.assertEqual(result.details["total_files_changed"], 1)

    def test_large_commit(self):
        stats = [
            FileChangeStats(f"src/file{i}.py", 100, 50, 150)
            for i in range(5)
        ]
        result = self.analyzer.analyze(stats, "feat: big change")
        self.assertTrue(any("过大" in i for i in result.issues))
        self.assertLess(result.score, result.max_score * 0.8)

    def test_too_many_files(self):
        self.analyzer.use_dynamic_thresholds = False
        stats = [
            FileChangeStats(f"src/file{i}.py", 5, 5, 10)
            for i in range(25)
        ]
        result = self.analyzer.analyze(stats, "feat: many files")
        self.assertTrue(any("过多" in i for i in result.issues))

    def test_excluded_files(self):
        stats = [
            FileChangeStats("src/app.py", 10, 5, 15),
            FileChangeStats("package-lock.json", 1000, 500, 1500),
            FileChangeStats("dist/bundle.min.js", 5000, 0, 5000),
        ]
        result = self.analyzer.analyze(stats, "feat: update")
        self.assertEqual(result.details["total_lines_changed"], 15)
        self.assertEqual(result.details["total_files_changed"], 1)
        self.assertEqual(len(result.details["excluded_files"]), 2)

    def test_large_single_file(self):
        stats = [
            FileChangeStats("src/big_file.py", 300, 50, 350),
            FileChangeStats("src/small.py", 10, 5, 15),
        ]
        result = self.analyzer.analyze(stats, "refactor: rewrite big module")
        self.assertTrue(any("变更量较大的文件" in i for i in result.issues))

    def test_refactoring_detection(self):
        stats = [
            FileChangeStats("src/old.py", 0, 200, 200),
            FileChangeStats("src/new.py", 195, 0, 195),
        ]
        result = self.analyzer.analyze(stats, "refactor: move code to new module")
        self.assertTrue(any("重构操作" in i for i in result.issues))

    def test_renaming_keyword(self):
        stats = [
            FileChangeStats("src/old_name.py", 0, 100, 100),
            FileChangeStats("src/new_name.py", 100, 0, 100),
        ]
        result = self.analyzer.analyze(stats, "rename: rename User to Customer")
        self.assertTrue(any("重构操作" in i for i in result.issues))

    def test_uneven_distribution(self):
        stats = [
            FileChangeStats("src/main.py", 180, 20, 200),
            FileChangeStats("src/util.py", 5, 5, 10),
            FileChangeStats("src/constants.py", 2, 2, 4),
        ]
        result = self.analyzer.analyze(stats, "feat: update main logic")
        self.assertTrue(any("分布不均" in i for i in result.issues))

    def test_empty_commit(self):
        stats = []
        result = self.analyzer.analyze(stats, "chore: empty commit")
        self.assertTrue(any("没有代码变更" in i for i in result.issues))


if __name__ == "__main__":
    unittest.main()
