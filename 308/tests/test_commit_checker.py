import unittest
from git_commit_checker.config import ConfigLoader
from git_commit_checker.commit_checker import ConventionalCommitsChecker


class TestConventionalCommitsChecker(unittest.TestCase):
    def setUp(self):
        self.config = ConfigLoader()
        self.checker = ConventionalCommitsChecker(self.config)

    def test_valid_feat_commit(self):
        message = "feat(auth): add user login functionality"
        result = self.checker.check(message)
        self.assertTrue(result.valid)
        self.assertGreater(result.score, result.max_score * 0.8)
        self.assertEqual(result.details.get("types"), ["feat"])
        self.assertEqual(result.details.get("scopes"), ["auth"])

    def test_valid_fix_commit(self):
        message = "fix: resolve null pointer exception in user service"
        result = self.checker.check(message)
        self.assertTrue(result.valid)
        self.assertEqual(result.details.get("types"), ["fix"])

    def test_invalid_format(self):
        message = "add login feature"
        result = self.checker.check(message)
        self.assertFalse(result.details.get("format_valid", False))
        self.assertLess(result.score, result.max_score * 0.6)

    def test_unknown_type(self):
        message = "unknown: some change"
        result = self.checker.check(message)
        self.assertTrue(any("未知的提交类型" in i for i in result.issues))

    def test_subject_too_long(self):
        long_subject = "x" * 100
        message = f"feat: {long_subject}"
        result = self.checker.check(message)
        self.assertTrue(any("过长" in i for i in result.issues))

    def test_breaking_change(self):
        message = "feat!: remove deprecated API"
        result = self.checker.check(message)
        self.assertTrue(result.details.get("breaking", False))

    def test_empty_message(self):
        message = ""
        result = self.checker.check(message)
        self.assertFalse(result.valid)
        self.assertEqual(result.score, 0)

    def test_with_body(self):
        message = """feat(api): add new endpoint

This adds a new REST API endpoint for user management.
It supports CRUD operations with proper authentication.

Closes #123
"""
        result = self.checker.check(message)
        self.assertTrue(result.details.get("has_body", False))
        self.assertTrue(result.details.get("has_footer", False))

    def test_uppercase_subject(self):
        message = "feat: Add login feature"
        result = self.checker.check(message)
        self.assertTrue(any("大写字母" in i for i in result.issues))

    def test_trailing_period(self):
        message = "feat: add login feature."
        result = self.checker.check(message)
        self.assertTrue(any("句号" in i for i in result.issues))


if __name__ == "__main__":
    unittest.main()
