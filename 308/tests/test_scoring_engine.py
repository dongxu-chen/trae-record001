import unittest
from git_commit_checker.config import ConfigLoader
from git_commit_checker.scoring_engine import ScoringEngine, QualityGrade


class TestScoringEngine(unittest.TestCase):
    def setUp(self):
        self.config = ConfigLoader()
        self.engine = ScoringEngine(self.config)

    def test_grade_excellent(self):
        self.assertEqual(self.engine.calculate_grade(95), QualityGrade.EXCELLENT)
        self.assertEqual(self.engine.calculate_grade(90), QualityGrade.EXCELLENT)

    def test_grade_good(self):
        self.assertEqual(self.engine.calculate_grade(85), QualityGrade.GOOD)
        self.assertEqual(self.engine.calculate_grade(75), QualityGrade.GOOD)

    def test_grade_fair(self):
        self.assertEqual(self.engine.calculate_grade(70), QualityGrade.FAIR)
        self.assertEqual(self.engine.calculate_grade(60), QualityGrade.FAIR)

    def test_grade_poor(self):
        self.assertEqual(self.engine.calculate_grade(50), QualityGrade.POOR)
        self.assertEqual(self.engine.calculate_grade(40), QualityGrade.POOR)

    def test_grade_fail(self):
        self.assertEqual(self.engine.calculate_grade(30), QualityGrade.FAIL)
        self.assertEqual(self.engine.calculate_grade(0), QualityGrade.FAIL)


if __name__ == "__main__":
    unittest.main()
