import unittest
from unittest.mock import MagicMock
from git_commit_checker.template_recommender import TemplateRecommender
from git_commit_checker.size_analyzer import FileChangeStats


class TestTemplateRecommender(unittest.TestCase):

    def setUp(self):
        self.config = MagicMock()
        self.config.get.side_effect = lambda key, default=None: {
            "template_recommendation.enabled": True,
            "template_recommendation.weight": 10,
            "template_recommendation.analyze_content": True,
            "template_recommendation.max_recommendations": 3,
            "template_recommendation.custom_templates": {},
        }.get(key, default)

        self.recommender = TemplateRecommender(self.config)

    def test_recommend_disabled(self):
        self.config.get.side_effect = lambda key, default=None: {
            "template_recommendation.enabled": False,
            "template_recommendation.weight": 10,
        }.get(key, default)

        recommender = TemplateRecommender(self.config)
        result = recommender.recommend([], None, None, None)

        self.assertTrue(result.valid)
        self.assertEqual(result.score, 10)
        self.assertEqual(result.details["skipped"], True)

    def test_recommend_docs_files(self):
        changed_files = ["docs/README.md", "docs/guide.md"]
        result = self.recommender.recommend(changed_files, None, None, None)

        self.assertTrue(result.valid)
        self.assertGreater(len(result.recommendations), 0)
        self.assertEqual(result.recommendations[0].type, "docs")

    def test_recommend_test_files(self):
        changed_files = ["tests/test_login.py", "tests/test_user.py"]
        result = self.recommender.recommend(changed_files, None, None, None)

        self.assertGreater(len(result.recommendations), 0)
        self.assertEqual(result.recommendations[0].type, "test")

    def test_recommend_ci_files(self):
        changed_files = [".github/workflows/test.yml", ".github/workflows/build.yml"]
        result = self.recommender.recommend(changed_files, None, None, None)

        self.assertGreater(len(result.recommendations), 0)
        self.assertEqual(result.recommendations[0].type, "ci")

    def test_recommend_build_files(self):
        changed_files = ["Dockerfile", "docker-compose.yml"]
        result = self.recommender.recommend(changed_files, None, None, None)

        self.assertGreater(len(result.recommendations), 0)
        self.assertEqual(result.recommendations[0].type, "build")

    def test_recommend_chore_files(self):
        changed_files = ["package.json", "requirements.txt"]
        result = self.recommender.recommend(changed_files, None, None, None)

        self.assertGreater(len(result.recommendations), 0)
        self.assertEqual(result.recommendations[0].type, "chore")

    def test_recommend_with_content_analysis(self):
        changed_files = ["src/auth/login.py"]
        file_contents = {
            "src/auth/login.py": "def login_user(username, password):\n    # add new feature\n    return authenticate(username, password)\n"
        }
        result = self.recommender.recommend(changed_files, None, None, file_contents)

        self.assertGreater(len(result.recommendations), 0)
        self.assertIn(result.recommendations[0].type, ["feat", "fix"])

    def test_recommend_detect_breaking_changes(self):
        changed_files = ["src/api/v2.py"]
        file_contents = {
            "src/api/v2.py": "BREAKING CHANGE: remove old API endpoint\n"
        }
        result = self.recommender.recommend(changed_files, None, None, file_contents)

        self.assertTrue(result.details["has_breaking_changes"])
        self.assertIn("!", result.recommendations[0].template)

    def test_recommend_with_existing_message(self):
        changed_files = ["src/auth/login.py", "tests/test_login.py"]
        existing_message = "update something"

        result = self.recommender.recommend(
            changed_files, None, existing_message, None
        )

        self.assertTrue(result.details["message_quality"]["needs_improvement"])
        self.assertTrue(
            any("建议使用推荐类型" in issue for issue in result.issues)
        )

    def test_recommend_with_good_existing_message(self):
        changed_files = ["src/auth/login.py"]
        existing_message = "feat: add login feature"

        result = self.recommender.recommend(
            changed_files, None, existing_message, None
        )

        self.assertFalse(result.details["message_quality"]["needs_improvement"])

    def test_recommend_dominant_module(self):
        changed_files = [
            "src/auth/login.py",
            "src/auth/user.py",
            "src/auth/session.py",
            "README.md",
        ]
        result = self.recommender.recommend(changed_files, None, None, None)

        self.assertEqual(result.details["dominant_module"], "auth")
        self.assertEqual(result.recommendations[0].scopes, ["auth"])

    def test_recommend_large_changes_refactor(self):
        changed_files = [
            "src/module1/a.py",
            "src/module1/b.py",
            "src/module1/c.py",
            "src/module2/d.py",
        ]
        file_stats = [
            FileChangeStats(f, 150, 150, 300) for f in changed_files
        ]
        result = self.recommender.recommend(changed_files, file_stats, None, None)

        type_scores = result.details["type_scores"]
        self.assertIn("refactor", type_scores)
        self.assertGreater(type_scores["refactor"], 0)

    def test_recommend_multiple_recommendations(self):
        changed_files = ["src/auth/login.py", "tests/test_login.py", "docs/README.md"]
        result = self.recommender.recommend(changed_files, None, None, None)

        self.assertGreaterEqual(len(result.recommendations), 2)
        self.assertNotEqual(
            result.recommendations[0].type,
            result.recommendations[1].type
        )

    def test_recommend_no_empty_message(self):
        changed_files = ["src/auth/login.py"]
        result = self.recommender.recommend(changed_files, None, "", None)

        self.assertTrue(result.details["message_quality"]["needs_improvement"])
        self.assertTrue(
            any("提交信息为空" in issue for issue in result.issues)
        )

    def test_extract_module(self):
        self.assertEqual(
            self.recommender._extract_module("src/auth/login.py"),
            "auth"
        )
        self.assertEqual(
            self.recommender._extract_module("packages/api/routes.py"),
            "api"
        )
        self.assertEqual(
            self.recommender._extract_module("app/main.py"),
            "main"
        )
        self.assertIsNone(
            self.recommender._extract_module("main.py")
        )

    def test_extract_keywords_from_content(self):
        content = """
        def add_new_feature():
            # fix bug in authentication
            return result
        """

        keywords = self.recommender._extract_keywords_from_content(content)
        self.assertIn("add", keywords)
        self.assertIn("fix", keywords)
        self.assertIn("new", keywords)

    def test_detect_type_from_keywords(self):
        self.assertEqual(
            self.recommender._detect_type_from_keywords(["add", "new", "feature"]),
            "feat"
        )
        self.assertEqual(
            self.recommender._detect_type_from_keywords(["fix", "bug", "error"]),
            "fix"
        )
        self.assertEqual(
            self.recommender._detect_type_from_keywords(["refactor", "restructure"]),
            "refactor"
        )

    def test_find_dominant_module(self):
        from git_commit_checker.template_recommender import FileContentHint

        hints = [
            FileContentHint("src/auth/a.py", [], "feat", "auth"),
            FileContentHint("src/auth/b.py", [], "feat", "auth"),
            FileContentHint("src/auth/c.py", [], "feat", "auth"),
            FileContentHint("src/utils/x.py", [], "feat", "utils"),
        ]

        self.assertEqual(self.recommender._find_dominant_module(hints), "auth")

    def test_calculate_type_scores(self):
        from git_commit_checker.template_recommender import FileContentHint

        hints = [
            FileContentHint("src/auth/login.py", ["add", "new"], "feat", "auth"),
            FileContentHint("tests/test_login.py", ["test"], "test", "auth"),
        ]

        scores = self.recommender._calculate_type_scores(hints, None)
        self.assertIn("feat", scores)
        self.assertIn("test", scores)
        self.assertGreater(scores["feat"], 0)
        self.assertGreater(scores["test"], 0)

    def test_generate_template_with_breaking(self):
        template = self.recommender._build_template(
            "feat", ["auth"], "add feature", "details", True
        )
        self.assertIn("!", template)
        self.assertIn("feat(auth)!:", template)

    def test_generate_template_without_breaking(self):
        template = self.recommender._build_template(
            "fix", ["api"], "fix bug", "", False
        )
        self.assertEqual(template, "fix(api): fix bug")

    def test_format_recommendations_text(self):
        from git_commit_checker.template_recommender import CommitRecommendation

        recs = [
            CommitRecommendation(
                template="feat: add feature",
                type="feat",
                scopes=[],
                subject_suggestion="add feature",
                body_suggestion="",
                confidence=0.9,
                reason="高置信度推荐"
            )
        ]

        formatted = self.recommender.format_recommendations(recs, "text")
        self.assertIn("推荐 1", formatted)
        self.assertIn("置信度: 90%", formatted)
        self.assertIn("feat: add feature", formatted)

    def test_format_recommendations_json(self):
        from git_commit_checker.template_recommender import CommitRecommendation
        import json

        recs = [
            CommitRecommendation(
                template="feat: add feature",
                type="feat",
                scopes=[],
                subject_suggestion="add feature",
                body_suggestion="",
                confidence=0.9,
                reason="高置信度推荐"
            )
        ]

        formatted = self.recommender.format_recommendations(recs, "json")
        parsed = json.loads(formatted)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["type"], "feat")

    def test_recommend_confidence_decay(self):
        changed_files = ["src/auth/login.py", "tests/test_login.py", "docs/README.md"]
        result = self.recommender.recommend(changed_files, None, None, None)

        if len(result.recommendations) >= 2:
            self.assertGreater(
                result.recommendations[0].confidence,
                result.recommendations[1].confidence
            )

    def test_generate_reason_high_confidence(self):
        from git_commit_checker.template_recommender import FileContentHint

        hints = [FileContentHint("src/auth/login.py", ["add", "new"], "feat", "auth")]
        reason = self.recommender._generate_reason("feat", hints, 0.75)

        self.assertIn("高置信度", reason)

    def test_generate_reason_low_confidence(self):
        from git_commit_checker.template_recommender import FileContentHint

        hints = [FileContentHint("src/file.py", [], "unknown", "")]
        reason = self.recommender._generate_reason("feat", hints, 0.2)

        self.assertIn("低置信度", reason)


if __name__ == "__main__":
    unittest.main()
