"""Git Commit Quality Checker - A tool for analyzing Git commit quality."""

__version__ = "1.0.0"
__author__ = "Commit Quality Team"

from .checker import CommitQualityChecker
from .commit_checker import (
    ConventionalCommitsChecker,
    CommitMessageParser,
    ParsedCommit,
    CommitFormatResult,
)
from .scope_analyzer import ChangeScopeAnalyzer
from .size_analyzer import ChangeSizeAnalyzer
from .consistency_checker import ConsistencyChecker, TestConsistencyResult
from .history_analyzer import (
    HistoryAnalyzer,
    HistoryAnalysisResult,
    CommitHistoryInfo,
    FileConflictInfo,
)
from .template_recommender import (
    TemplateRecommender,
    TemplateRecommendationResult,
    CommitRecommendation,
    FileContentHint,
)
from .scoring_engine import ScoringEngine, CommitQualityReport, QualityGrade
from .git_integration import GitRepository
from .config import ConfigLoader
from .custom_rules import CustomRuleLoader
