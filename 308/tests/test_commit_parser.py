import unittest
from git_commit_checker.commit_checker import (
    CommitMessageParser,
    ConventionalCommitsChecker,
    ParsedCommit,
)
from git_commit_checker.config import ConfigLoader


class TestCommitMessageParser(unittest.TestCase):
    def setUp(self):
        self.config = ConfigLoader()
        self.checker = ConventionalCommitsChecker(self.config)

    def test_parse_single_type(self):
        message = "feat(auth): add user login"
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.types, ["feat"])
        self.assertEqual(parsed.scopes, ["auth"])
        self.assertEqual(parsed.subject, "add user login")
        self.assertFalse(parsed.breaking)

    def test_parse_multiple_types_comma(self):
        message = "feat,fix: add login and fix bug"
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.types, ["feat", "fix"])

    def test_parse_multiple_types_slash(self):
        message = "feat/fix: add login and fix bug"
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.types, ["feat", "fix"])

    def test_parse_multiple_scopes(self):
        message = "feat(auth,api): add user login endpoint"
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.scopes, ["auth", "api"])

    def test_parse_multiple_types_and_scopes(self):
        message = "feat,fix(auth,api): add feature and fix bug"
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.types, ["feat", "fix"])
        self.assertEqual(parsed.scopes, ["auth", "api"])

    def test_parse_with_body(self):
        message = """feat: add login

Add OAuth2 login support with Google and GitHub.
Includes proper error handling.

Closes #123
"""
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed.body is not None and "OAuth2" in parsed.body)
        self.assertTrue(parsed.footer is not None and "Closes #123" in parsed.footer)

    def test_parse_breaking_change_exclamation(self):
        message = "feat!: remove deprecated API"
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed.breaking)

    def test_parse_breaking_change_footer(self):
        message = """feat: change API

BREAKING CHANGE: The API now requires authentication.
"""
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed.breaking)

    def test_parse_multiline_header(self):
        message = """# This is a comment
feat(api): add new endpoint

Add new REST API endpoint.
"""
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.types, ["feat"])
        self.assertEqual(parsed.scopes, ["api"])
        self.assertEqual(parsed.subject, "add new endpoint")

    def test_parse_with_trailers(self):
        message = """feat: add feature

Add new feature.

Reviewed-by: John Doe
Signed-off-by: Jane Smith
Fixes: #456
"""
        parsed = CommitMessageParser.parse(message)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.trailers.get("Reviewed-by"), "John Doe")
        self.assertEqual(parsed.trailers.get("Signed-off-by"), "Jane Smith")
        self.assertEqual(parsed.trailers.get("Fixes"), "#456")

    def test_parse_empty_message(self):
        parsed = CommitMessageParser.parse("")
        self.assertIsNone(parsed)

    def test_parse_invalid_format(self):
        message = "add login feature"
        parsed = CommitMessageParser.parse(message)
        self.assertIsNone(parsed)

    def test_check_multiple_types_valid(self):
        message = "feat,fix: add feature and fix bug"
        result = self.checker.check(message)
        self.assertTrue(result.valid)
        self.assertEqual(result.details.get("types"), ["feat", "fix"])

    def test_check_multiple_scopes_valid(self):
        message = "feat(auth,api): add new endpoint"
        result = self.checker.check(message)
        self.assertTrue(result.valid)
        self.assertEqual(result.details.get("scopes"), ["auth", "api"])

    def test_check_too_many_types(self):
        message = "feat,fix,docs,style: too many types"
        result = self.checker.check(message)
        self.assertTrue(any("类型数量过多" in i for i in result.issues))

    def test_check_body_line_length(self):
        long_line = "x" * 150
        message = f"""feat: add feature

{long_line}
"""
        result = self.checker.check(message)
        self.assertTrue(any("过长" in i for i in result.issues))

    def test_check_breaking_change_bonus(self):
        message = "feat!: remove deprecated API"
        result = self.checker.check(message)
        self.assertTrue(result.details.get("breaking", False))
        self.assertGreater(result.score, 30)

    def test_get_primary_type(self):
        message = "feat,fix: add feature and fix bug"
        result = self.checker.check(message)
        primary = self.checker.get_primary_type(result.parsed)
        self.assertEqual(primary, "feat")


if __name__ == "__main__":
    unittest.main()
