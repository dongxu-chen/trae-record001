import os
from typing import List, Optional, Dict, Any

from .config import ConfigLoader
from .commit_checker import ConventionalCommitsChecker
from .scope_analyzer import ChangeScopeAnalyzer
from .size_analyzer import ChangeSizeAnalyzer
from .consistency_checker import ConsistencyChecker
from .history_analyzer import HistoryAnalyzer
from .template_recommender import TemplateRecommender
from .scoring_engine import ScoringEngine, CommitQualityReport
from .custom_rules import CustomRuleLoader
from .git_integration import GitRepository


class CommitQualityChecker:
    def __init__(self, config_path: Optional[str] = None, repo_path: Optional[str] = None):
        self.config = ConfigLoader(config_path)
        self.repo_path = repo_path or os.getcwd()
        self.repo = GitRepository(repo_path)

        self.format_checker = ConventionalCommitsChecker(self.config)
        self.scope_analyzer = ChangeScopeAnalyzer(self.config, self.repo_path)
        self.size_analyzer = ChangeSizeAnalyzer(self.config)
        self.consistency_checker = ConsistencyChecker(self.config)
        self.history_analyzer = HistoryAnalyzer(self.config, self.repo_path)
        self.template_recommender = TemplateRecommender(self.config)
        self.scoring_engine = ScoringEngine(self.config)
        self.custom_rules = CustomRuleLoader(self.config)

    def check_commit(self, commit_hash: Optional[str] = None) -> CommitQualityReport:
        if commit_hash:
            commit = self.repo.get_commit(commit_hash)
        else:
            commit = self.repo.get_latest_commit()

        commit_message = self.repo.get_commit_message(commit)
        changed_files = self.repo.get_changed_files(commit)
        file_stats = self.repo.get_file_stats(commit)
        commit_info = self.repo.get_commit_info(commit)

        format_result = self.format_checker.check(commit_message)

        commit_types = []
        parsed = getattr(format_result, "parsed", None)
        if parsed and hasattr(parsed, "types"):
            commit_types = parsed.types

        scope_result = self.scope_analyzer.analyze(changed_files)
        size_result = self.size_analyzer.analyze(file_stats, commit_message, commit_types)
        consistency_result = self.consistency_checker.check(
            changed_files, commit_types, file_stats
        )

        history_info = self.history_analyzer.extract_history_from_git(self.repo, n=100)
        history_result = self.history_analyzer.analyze(
            commit_info["hash"],
            changed_files,
            commit_info["author_name"],
            history_info
        )

        template_result = self.template_recommender.recommend(
            changed_files, file_stats, commit_message
        )

        custom_results = self.custom_rules.run_rules(
            commit_message, changed_files, file_stats, commit_info
        )

        report = self.scoring_engine.generate_report(
            commit_hash=commit_info["hash"],
            commit_message=commit_message,
            author=commit_info["author"],
            date=commit_info["date"],
            format_result=format_result,
            scope_result=scope_result,
            size_result=size_result,
            consistency_result=consistency_result,
            history_result=history_result,
            template_result=template_result,
            custom_results=custom_results,
        )

        return report

    def check_last_n_commits(self, n: int = 1) -> List[CommitQualityReport]:
        commits = self.repo.get_last_n_commits(n)
        reports = []
        for commit in reversed(commits):
            reports.append(self.check_commit(commit.hexsha))
        return reports

    def check_commits_in_range(self, start_ref: str, end_ref: str) -> List[CommitQualityReport]:
        commits = self.repo.get_commits_in_range(start_ref, end_ref)
        reports = []
        for commit in reversed(commits):
            reports.append(self.check_commit(commit.hexsha))
        return reports

    def check_staged(self) -> Optional[CommitQualityReport]:
        if self.repo.is_clean():
            return None

        raise NotImplementedError(
            "Staged commit checking is not yet implemented. "
            "Please commit your changes first, then run the checker."
        )

    def get_repo_info(self) -> Dict[str, Any]:
        return {
            "path": self.repo.repo_path,
            "branch": self.repo.get_current_branch(),
            "is_clean": self.repo.is_clean(),
        }
