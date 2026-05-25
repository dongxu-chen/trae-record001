import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from git_commit_checker.history_analyzer import (
    HistoryAnalyzer,
    CommitHistoryInfo,
)


class TestHistoryAnalyzer(unittest.TestCase):

    def setUp(self):
        self.config = MagicMock()
        self.config.get.side_effect = lambda key, default=None: {
            "history_analysis.enabled": True,
            "history_analysis.weight": 15,
            "history_analysis.lookback_days": 30,
            "history_analysis.frequency_threshold": 10,
            "history_analysis.hotspot_threshold": 5,
            "history_analysis.conflict_file_threshold": 3,
            "history_analysis.min_commits_for_analysis": 5,
        }.get(key, default)

        self.analyzer = HistoryAnalyzer(self.config)

    def _create_test_history(
        self,
        count: int,
        author: str = "Test User",
        days_back: int = 30,
        files_per_commit: int = 2,
        multiple_authors: bool = False,
    ) -> list:
        history = []
        now = datetime.now()
        authors = [author, "Other User 1", "Other User 2"] if multiple_authors else [author]

        for i in range(count):
            commit_time = now - timedelta(days=days_back * i / max(count, 1))
            author_idx = i % len(authors) if multiple_authors else 0

            files = [f"src/module{i % 3}/file{j}.py" for j in range(files_per_commit)]
            files.append(f"src/common/utils.py")

            history.append(CommitHistoryInfo(
                hash=f"commit{i:08x}",
                author=authors[author_idx],
                author_email=f"{authors[author_idx].lower().replace(' ', '.')}@example.com",
                timestamp=int(commit_time.timestamp()),
                date=commit_time.strftime("%Y-%m-%d %H:%M:%S"),
                files=files,
                message=f"Commit {i}: change something",
            ))

        return history

    def test_analyze_disabled(self):
        self.config.get.side_effect = lambda key, default=None: {
            "history_analysis.enabled": False,
            "history_analysis.weight": 15,
        }.get(key, default)

        analyzer = HistoryAnalyzer(self.config)
        result = analyzer.analyze("hash1", [], "Test User", [])

        self.assertTrue(result.valid)
        self.assertEqual(result.score, 15)
        self.assertEqual(result.details["skipped"], True)

    def test_analyze_insufficient_data(self):
        history = self._create_test_history(count=3)
        result = self.analyzer.analyze("hash1", ["src/file.py"], "Test User", history)

        self.assertTrue(result.valid)
        self.assertEqual(result.score, 15)
        self.assertTrue(result.details["insufficient_data"])

    def test_analyze_normal_frequency(self):
        history = self._create_test_history(count=10, days_back=10)
        result = self.analyzer.analyze("hash1", ["src/file.py"], "Test User", history)

        self.assertTrue(result.valid)
        self.assertFalse(result.details["frequency_analysis"]["is_abnormal"])

    def test_analyze_high_frequency(self):
        history = self._create_test_history(count=50, days_back=2)
        result = self.analyzer.analyze("hash1", ["src/file.py"], "Test User", history)

        self.assertTrue(result.details["frequency_analysis"]["is_abnormal"])
        self.assertTrue(any("提交频率异常" in issue for issue in result.issues))
        self.assertLess(result.score, 15)

    def test_analyze_very_high_frequency(self):
        history = self._create_test_history(count=100, days_back=1)
        result = self.analyzer.analyze("hash1", ["src/file.py"], "Test User", history)

        self.assertTrue(result.details["frequency_analysis"]["is_very_high"])
        self.assertTrue(any("极高频提交" in issue for issue in result.issues))

    def test_analyze_file_conflicts_multiple_authors(self):
        history = self._create_test_history(
            count=20,
            multiple_authors=True,
            files_per_commit=3,
        )
        current_files = ["src/common/utils.py", "src/module0/file0.py"]
        result = self.analyzer.analyze("hash1", current_files, "Test User", history)

        conflict_analysis = result.details["conflict_analysis"]
        self.assertGreater(len(conflict_analysis["high_risk_files"]), 0)
        self.assertTrue(any("冲突风险" in issue for issue in result.issues))

    def test_analyze_large_commit_ratio(self):
        history = self._create_test_history(count=20, files_per_commit=15)
        result = self.analyzer.analyze("hash1", ["src/file.py"], "Test User", history)

        self.assertGreater(result.details["pattern_analysis"]["large_commit_ratio"], 0.3)
        self.assertTrue(any("大提交比例较高" in issue for issue in result.issues))

    def test_analyze_solo_developer(self):
        history = self._create_test_history(count=30, multiple_authors=False)
        result = self.analyzer.analyze("hash1", ["src/file.py"], "Test User", history)

        self.assertTrue(result.details["contribution_analysis"]["is_solo_developer"])
        self.assertTrue(any("单人开发模式" in issue for issue in result.issues))

    def test_analyze_hotspot_files(self):
        history = self._create_test_history(count=50, files_per_commit=1)
        current_files = ["src/common/utils.py"]
        result = self.analyzer.analyze("hash1", current_files, "Test User", history)

        self.assertGreater(len(result.details["hotspot_files"]), 0)
        self.assertTrue(any("热点文件" in issue for issue in result.issues))

    def test_analyze_after_hours_work(self):
        history = []
        now = datetime.now()

        for i in range(10):
            commit_time = now.replace(hour=22, minute=0) - timedelta(days=i)
            history.append(CommitHistoryInfo(
                hash=f"commit{i:08x}",
                author="Test User",
                author_email="test@example.com",
                timestamp=int(commit_time.timestamp()),
                date=commit_time.strftime("%Y-%m-%d %H:%M:%S"),
                files=["src/file.py"],
                message=f"Commit {i}",
            ))

        result = self.analyzer.analyze("hash1", ["src/file.py"], "Test User", history)

        self.assertGreater(result.details["work_pattern"]["after_hours_ratio"], 0.5)
        self.assertTrue(any("非工作时间" in issue for issue in result.issues))

    def test_filter_recent_commits(self):
        old_commit = CommitHistoryInfo(
            hash="old12345",
            author="Test User",
            author_email="test@example.com",
            timestamp=int((datetime.now() - timedelta(days=60)).timestamp()),
            date="2024-01-01 00:00:00",
            files=["old/file.py"],
            message="Old commit",
        )
        new_commit = CommitHistoryInfo(
            hash="new12345",
            author="Test User",
            author_email="test@example.com",
            timestamp=int((datetime.now() - timedelta(days=5)).timestamp()),
            date="2024-02-20 00:00:00",
            files=["new/file.py"],
            message="New commit",
        )

        recent = self.analyzer._filter_recent_commits([old_commit, new_commit])

        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].hash, "new12345")

    def test_analyze_commit_frequency(self):
        now = datetime.now()
        history = []

        for i in range(15):
            commit_time = now - timedelta(hours=i * 2)
            history.append(CommitHistoryInfo(
                hash=f"commit{i}",
                author="Test User",
                author_email="test@example.com",
                timestamp=int(commit_time.timestamp()),
                date=commit_time.strftime("%Y-%m-%d %H:%M:%S"),
                files=["file.py"],
                message=f"Commit {i}",
            ))

        analysis = self.analyzer._analyze_commit_frequency(history, "Test User")

        self.assertGreater(analysis["frequency"], 10)
        self.assertTrue(analysis["is_abnormal"])

    def test_analyze_file_conflicts_medium_risk(self):
        now = datetime.now()
        history = []
        authors = ["User A", "User B"]

        for i in range(10):
            author = authors[i % 2]
            history.append(CommitHistoryInfo(
                hash=f"commit{i}",
                author=author,
                author_email=f"{author.lower()}@example.com",
                timestamp=int((now - timedelta(hours=i)).timestamp()),
                date="",
                files=["src/shared/module.py"],
                message="Update",
            ))

        result = self.analyzer._analyze_file_conflicts(
            ["src/shared/module.py"], history, "User A"
        )

        self.assertEqual(len(result["high_risk_files"]), 1)
        self.assertEqual(result["high_risk_files"][0]["risk_level"], "MEDIUM")

    def test_analyze_contribution_patterns(self):
        history = self._create_test_history(count=20, multiple_authors=True)
        analysis = self.analyzer._analyze_contribution_patterns(history, "Test User")

        self.assertGreater(analysis["total_authors"], 1)
        self.assertFalse(analysis["is_solo_developer"])
        self.assertGreater(analysis["author_commits"], 0)

    def test_analyze_with_no_author_commits(self):
        history = self._create_test_history(count=10, author="Other User")
        result = self.analyzer.analyze("hash1", ["src/file.py"], "Test User", history)

        self.assertTrue(result.valid)
        self.assertEqual(result.score, 15)

    def test_multiple_high_risk_files(self):
        history = []
        now = datetime.now()
        authors = ["User A", "User B", "User C"]

        for i in range(30):
            author = authors[i % 3]
            files = [
                f"src/core/file1.py",
                f"src/core/file2.py",
                f"src/utils/helper.py",
            ]
            history.append(CommitHistoryInfo(
                hash=f"commit{i}",
                author=author,
                author_email=f"{author.lower()}@example.com",
                timestamp=int((now - timedelta(hours=i)).timestamp()),
                date="",
                files=files,
                message="Update",
            ))

        current_files = [
            "src/core/file1.py",
            "src/core/file2.py",
        ]
        result = self.analyzer.analyze("hash1", current_files, "User A", history)

        conflict_analysis = result.details["conflict_analysis"]
        self.assertGreaterEqual(len(conflict_analysis["high_risk_files"]), 2)

        for file_info in conflict_analysis["high_risk_files"]:
            self.assertEqual(file_info["risk_level"], "HIGH")
            self.assertGreaterEqual(len(file_info["authors"]), 3)

        self.assertLess(result.score, 12)


if __name__ == "__main__":
    unittest.main()
