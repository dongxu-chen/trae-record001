import unittest
from git_commit_checker.config import ConfigLoader
from git_commit_checker.scope_analyzer import ChangeScopeAnalyzer


class TestChangeScopeAnalyzer(unittest.TestCase):
    def setUp(self):
        self.config = ConfigLoader()
        self.analyzer = ChangeScopeAnalyzer(self.config)

    def test_single_module(self):
        files = [
            "src/auth/login.py",
            "src/auth/register.py",
        ]
        result = self.analyzer.analyze(files)
        self.assertTrue(result.valid)
        self.assertEqual(len(result.details.get("modules", [])), 1)
        self.assertIn("auth", result.details.get("modules", []))

    def test_cross_module(self):
        files = [
            "src/auth/login.py",
            "src/payment/process.py",
        ]
        result = self.analyzer.analyze(files)
        self.assertEqual(len(result.details.get("modules", [])), 2)

    def test_too_many_modules(self):
        files = [
            "src/module1/file1.py",
            "src/module2/file2.py",
            "src/module3/file3.py",
            "src/module4/file4.py",
        ]
        result = self.analyzer.analyze(files)
        self.assertTrue(any("超过了最大建议值" in i for i in result.issues))

    def test_root_level_files(self):
        files = [
            "frontend/app.js",
            "backend/server.py",
        ]
        result = self.analyzer.analyze(files)
        modules = result.details.get("modules", [])
        self.assertIn("frontend", modules)
        self.assertIn("backend", modules)

    def test_unknown_module(self):
        files = [
            "random_file.txt",
        ]
        result = self.analyzer.analyze(files)
        modules = result.details.get("modules", [])
        self.assertEqual(len(modules), 0)

    def test_mixed_file_types(self):
        files = [
            "src/auth/login.py",
            "src/auth/styles.css",
            "src/auth/config.json",
            "src/auth/test.spec.js",
            "src/docs/readme.md",
        ]
        result = self.analyzer.analyze(files)
        self.assertEqual(len(result.details.get("modules", [])), 2)

    def test_monorepo_structure(self):
        files = [
            "packages/ui/components/Button.js",
            "packages/api/routes/user.js",
        ]
        result = self.analyzer.analyze(files)
        modules = result.details.get("modules", [])
        self.assertIn("ui", modules)
        self.assertIn("api", modules)


if __name__ == "__main__":
    unittest.main()
