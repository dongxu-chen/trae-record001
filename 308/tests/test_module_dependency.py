import unittest
import os
import tempfile
import shutil
from git_commit_checker.module_dependency import (
    ModuleDependencyGraph,
    DependencyExtractor,
    CrossModuleAnalyzer,
)
from git_commit_checker.config import ConfigLoader


class TestModuleDependencyGraph(unittest.TestCase):
    def setUp(self):
        self.graph = ModuleDependencyGraph()

    def test_add_module(self):
        self.graph.add_module("auth")
        self.assertIn("auth", self.graph.modules)

    def test_add_dependency(self):
        self.graph.add_dependency("auth", "database")
        self.assertIn("database", self.graph.dependencies["auth"])
        self.assertIn("auth", self.graph.dependents["database"])

    def test_get_related_modules(self):
        self.graph.add_dependency("auth", "database")
        self.graph.add_dependency("database", "utils")
        self.graph.add_dependency("api", "auth")

        related = self.graph.get_related_modules("auth", max_depth=2)
        self.assertIn("database", related)
        self.assertIn("utils", related)
        self.assertIn("api", related)

    def test_are_modules_related(self):
        self.graph.add_dependency("auth", "database")
        self.graph.add_dependency("database", "utils")

        self.assertTrue(self.graph.are_modules_related("auth", "database"))
        self.assertTrue(self.graph.are_modules_related("auth", "utils"))
        self.assertFalse(self.graph.are_modules_related("auth", "other"))

    def test_get_module_clusters(self):
        self.graph.add_dependency("auth", "database")
        self.graph.add_dependency("api", "auth")
        self.graph.add_dependency("frontend", "ui")

        clusters = self.graph.get_module_clusters()
        self.assertEqual(len(clusters), 2)

    def test_find_shortest_path(self):
        self.graph.add_dependency("a", "b")
        self.graph.add_dependency("b", "c")
        self.graph.add_dependency("a", "c")

        path = self.graph.find_shortest_path("a", "c")
        self.assertIsNotNone(path)
        self.assertEqual(len(path), 2)

    def test_calculate_cohesion_score(self):
        self.graph.add_dependency("auth", "database")
        self.graph.add_dependency("auth", "api")

        score = self.graph.calculate_cohesion_score({"auth", "database", "api"})
        self.assertGreater(score, 0.5)

        score = self.graph.calculate_cohesion_score({"auth", "other", "unrelated"})
        self.assertEqual(score, 0)


class TestCrossModuleAnalyzer(unittest.TestCase):
    def setUp(self):
        self.graph = ModuleDependencyGraph()
        self.graph.add_dependency("auth", "database")
        self.graph.add_dependency("auth", "api")
        self.graph.add_dependency("database", "utils")
        self.graph.add_module("unrelated")
        self.analyzer = CrossModuleAnalyzer(self.graph)

    def test_single_module(self):
        score, issues, details = self.analyzer.analyze_cross_module_change({"auth"})
        self.assertEqual(score, 1.0)
        self.assertEqual(len(issues), 0)
        self.assertFalse(details["cross_module"])

    def test_related_modules(self):
        score, issues, details = self.analyzer.analyze_cross_module_change({"auth", "database", "api"})
        self.assertGreater(score, 0.8)
        self.assertTrue(details["cross_module"])
        self.assertGreater(details["cohesion_score"], 0.5)

    def test_unrelated_modules(self):
        score, issues, details = self.analyzer.analyze_cross_module_change({"auth", "unrelated"})
        self.assertLess(score, 0.7)
        self.assertIn("unrelated", details["unrelated_modules"])

    def test_multiple_clusters(self):
        score, issues, details = self.analyzer.analyze_cross_module_change({"auth", "database", "unrelated"})
        self.assertEqual(len(details["related_clusters"]), 2)

    def test_dependency_chain(self):
        score, issues, details = self.analyzer.analyze_cross_module_change({"auth", "database", "utils"})
        self.assertIn("dependency_chains", details)
        self.assertTrue(len(details["dependency_chains"]) > 0)


class TestDependencyExtractor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config = ConfigLoader()
        import re
        self.module_patterns = [
            re.compile(r"^src/([^/]+)/"),
            re.compile(r"^([^/]+)/"),
        ]
        self.extractor = DependencyExtractor(self.test_dir, self.module_patterns)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_extract_python_dependencies(self):
        os.makedirs(os.path.join(self.test_dir, "src", "auth"))
        os.makedirs(os.path.join(self.test_dir, "src", "database"))

        with open(os.path.join(self.test_dir, "src", "auth", "login.py"), "w") as f:
            f.write("from src.database.models import User\n")
            f.write("import os\n")

        with open(os.path.join(self.test_dir, "src", "database", "models.py"), "w") as f:
            f.write("class User:\n")
            f.write("    pass\n")

        graph = self.extractor.extract_graph()
        self.assertIn("auth", graph.modules)
        self.assertIn("database", graph.modules)

    def test_skip_directories(self):
        os.makedirs(os.path.join(self.test_dir, "node_modules", "test"))
        os.makedirs(os.path.join(self.test_dir, "src", "auth"))

        with open(os.path.join(self.test_dir, "node_modules", "test", "file.py"), "w") as f:
            f.write("print('test')\n")

        with open(os.path.join(self.test_dir, "src", "auth", "main.py"), "w") as f:
            f.write("print('auth')\n")

        graph = self.extractor.extract_graph()
        self.assertIn("auth", graph.modules)


if __name__ == "__main__":
    unittest.main()
