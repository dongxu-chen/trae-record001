import unittest
from unittest.mock import MagicMock
from git_commit_checker.consistency_checker import ConsistencyChecker
from git_commit_checker.size_analyzer import FileChangeStats


class TestConsistencyCheckerClass(unittest.TestCase):

    def setUp(self):
        self.config = MagicMock()
        self.config.get.side_effect = lambda key, default=None: {
            "test_consistency.enabled": True,
            "test_consistency.weight": 20,
            "test_consistency.require_test_for_types": ["feat", "fix", "perf"],
            "test_consistency.exclude_patterns": [r"^docs?/", r"^LICENSE$", r"^README\.", r"\.md$"],
            "test_consistency.test_file_extensions": [
                "py", "js", "ts", "java", "go"
            ],
        }.get(key, default)

        self.checker = ConsistencyChecker(self.config)

    def test_check_disabled(self):
        self.config.get.side_effect = lambda key, default=None: {
            "test_consistency.enabled": False,
            "test_consistency.weight": 20,
        }.get(key, default)

        checker = ConsistencyChecker(self.config)
        result = checker.check([], [], None)

        self.assertTrue(result.valid)
        self.assertEqual(result.score, 20)
        self.assertEqual(result.max_score, 20)
        self.assertEqual(result.details["skipped"], True)

    def test_check_no_source_changes(self):
        changed_files = ["docs/README.md", "docs/guide.md"]
        result = self.checker.check(changed_files, ["feat"], None)

        self.assertTrue(result.valid)
        self.assertEqual(result.score, 20)
        self.assertEqual(result.details["has_source_changes"], False)
        self.assertEqual(result.details["source_count"], 0)

    def test_check_missing_tests_feat_type(self):
        changed_files = [
            "src/auth/login.py",
            "src/auth/user.py",
        ]
        result = self.checker.check(changed_files, ["feat"], None)

        self.assertFalse(result.valid)
        self.assertLess(result.score, 20)
        self.assertTrue(any("缺少对应测试更新" in issue for issue in result.issues))
        self.assertEqual(result.details["missing_tests"], changed_files)

    def test_check_with_tests(self):
        changed_files = [
            "src/auth/login.py",
            "tests/auth/test_login.py",
            "src/auth/user.py",
            "tests/auth/test_user.py",
        ]
        result = self.checker.check(changed_files, ["feat"], None)

        self.assertTrue(result.valid)
        self.assertEqual(result.details["source_count"], 2)
        self.assertEqual(result.details["test_count"], 2)
        self.assertEqual(result.details["missing_tests"], [])

    def test_check_test_in_src_directory(self):
        changed_files = [
            "src/auth/login.py",
            "src/auth/__tests__/test_login.py",
        ]
        result = self.checker.check(changed_files, ["feat"], None)

        self.assertEqual(result.details["test_count"], 1)
        self.assertEqual(result.details["missing_tests"], [])

    def test_check_test_file_naming_patterns(self):
        test_patterns = [
            "src/login.test.js",
            "src/login.spec.js",
            "src/login_test.py",
            "src/login_spec.rb",
            "tests/test_login.py",
            "spec/login_spec.rb",
            "__tests__/login.test.js",
        ]

        for test_file in test_patterns:
            with self.subTest(test_file=test_file):
                self.assertTrue(self.checker._is_test_file(test_file))

    def test_check_non_test_file(self):
        non_test_files = [
            "src/login.py",
            "src/utils/helpers.js",
            "docs/README.md",
        ]

        for file in non_test_files:
            with self.subTest(file=file):
                self.assertFalse(self.checker._is_test_file(file))

    def test_check_excluded_files(self):
        excluded_files = [
            "docs/guide.md",
            "README.md",
            "doc/api.md",
            "LICENSE",
        ]

        for file in excluded_files:
            with self.subTest(file=file):
                self.assertTrue(self.checker._is_excluded(file))

    def test_check_non_excluded_files(self):
        non_excluded_files = [
            "src/login.py",
            "tests/test_login.py",
            "README",
        ]

        for file in non_excluded_files:
            with self.subTest(file=file):
                self.assertFalse(self.checker._is_excluded(file))

    def test_check_with_file_stats_test_insertions(self):
        changed_files = [
            "src/auth/login.py",
            "tests/test_login.py",
        ]
        file_stats = [
            FileChangeStats("src/auth/login.py", 20, 10, 30),
            FileChangeStats("tests/test_login.py", 30, 5, 35),
        ]
        result = self.checker.check(changed_files, ["feat"], file_stats)

        self.assertTrue(result.valid)
        self.assertEqual(
            result.details["test_line_changes"]["test_insertions"], 30
        )
        self.assertTrue(
            any("新增测试代码" in issue for issue in result.issues)
        )

    def test_check_test_coverage_ratio(self):
        src_files = ["src/module1/a.py", "src/module1/b.py", "src/module2/c.py"]
        test_files = ["tests/module1/test_a.py"]

        ratio = self.checker._calculate_test_coverage_ratio(src_files, test_files)
        self.assertGreater(ratio, 0)
        self.assertLess(ratio, 1)

    def test_check_needs_test_update(self):
        self.assertTrue(self.checker._needs_test_update(["feat"]))
        self.assertTrue(self.checker._needs_test_update(["fix"]))
        self.assertTrue(self.checker._needs_test_update(["perf"]))
        self.assertFalse(self.checker._needs_test_update(["docs"]))
        self.assertFalse(self.checker._needs_test_update(["refactor"]))
        self.assertFalse(self.checker._needs_test_update([]))

    def test_check_multiple_types_with_feat(self):
        self.assertTrue(self.checker._needs_test_update(["refactor", "feat"]))

    def test_check_get_src_base(self):
        self.assertEqual(
            self.checker._get_src_base("src/auth/login.py"),
            "auth/login"
        )
        self.assertEqual(
            self.checker._get_src_base("lib/utils/helpers.js"),
            "utils/helpers"
        )
        self.assertEqual(
            self.checker._get_src_base("main.py"),
            "main"
        )

    def test_check_get_test_basenames(self):
        test_files = [
            "tests/auth/test_login.py",
            "tests/auth/login_spec.py",
            "__tests__/user.test.js",
        ]

        basenames = self.checker._get_test_basenames(test_files)
        self.assertIn("auth/login", basenames)
        self.assertIn("auth/login", basenames)
        self.assertIn("user", basenames)

    def test_check_multiple_missing_tests_penalty(self):
        changed_files = [
            "src/a.py", "src/b.py", "src/c.py", "src/d.py", "src/e.py"
        ]
        result = self.checker.check(changed_files, ["feat"], None)

        self.assertLess(result.score, 10)

    def test_check_no_types_no_test_required(self):
        changed_files = ["src/auth/login.py"]
        result = self.checker.check(changed_files, [], None)

        self.assertTrue(result.valid)
        self.assertEqual(result.score, 20)

    def test_check_test_ratio_bonus(self):
        changed_files = [
            "src/a.py", "src/b.py",
            "tests/test_a.py", "tests/test_b.py",
        ]
        result = self.checker.check(changed_files, ["feat"], None)

        self.assertEqual(result.details["test_ratio_bonus"], True)
        self.assertEqual(result.score, 20)

    def test_check_classify_files(self):
        files = [
            "src/login.py",
            "tests/test_login.py",
            "docs/README.md",
            "src/utils.js",
            "test_utils.spec.js",
        ]

        src, test = self.checker._classify_files(files)

        self.assertIn("src/login.py", src)
        self.assertIn("src/utils.js", src)
        self.assertNotIn("docs/README.md", src)
        self.assertIn("tests/test_login.py", test)
        self.assertIn("test_utils.spec.js", test)


if __name__ == "__main__":
    unittest.main()
