import os
import re
import statistics
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class CommitHistoryInfo:
    hash: str
    author: str
    author_email: str
    timestamp: int
    date: str
    files: List[str]
    message: str


@dataclass
class HistoryAnalysisResult:
    valid: bool
    score: float
    max_score: float
    issues: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileConflictInfo:
    file: str
    authors: Set[str]
    recent_commits: int
    last_commit_by: str
    risk_level: str


class HistoryAnalyzer:
    def __init__(self, config: Any, repo_path: Optional[str] = None):
        self.config = config
        self.repo_path = repo_path or os.getcwd()
        self.enabled = config.get("history_analysis.enabled", True)
        self.weight = config.get("history_analysis.weight", 15)
        self.lookback_days = config.get("history_analysis.lookback_days", 30)
        self.frequency_threshold = config.get("history_analysis.frequency_threshold", 10)
        self.hotspot_threshold = config.get("history_analysis.hotspot_threshold", 5)
        self.conflict_file_threshold = config.get("history_analysis.conflict_file_threshold", 3)
        self.min_commits_for_analysis = config.get("history_analysis.min_commits_for_analysis", 5)

    def analyze(
        self,
        current_commit_hash: str,
        current_changed_files: List[str],
        current_author: str,
        commit_history: List[CommitHistoryInfo]
    ) -> HistoryAnalysisResult:
        if not self.enabled:
            return HistoryAnalysisResult(
                valid=True,
                score=self.weight,
                max_score=self.weight,
                issues=[],
                details={"skipped": True}
            )

        issues: List[str] = []
        score = self.weight
        max_score = self.weight
        details: Dict[str, Any] = {}

        recent_commits = self._filter_recent_commits(commit_history)
        details["recent_commits_count"] = len(recent_commits)
        details["lookback_days"] = self.lookback_days

        if len(recent_commits) < self.min_commits_for_analysis:
            details["insufficient_data"] = True
            details["reason"] = f"需要至少 {self.min_commits_for_analysis} 条提交记录进行分析"
            return HistoryAnalysisResult(
                valid=True,
                score=self.weight,
                max_score=max_score,
                issues=[],
                details=details
            )

        frequency_analysis = self._analyze_commit_frequency(recent_commits, current_author)
        details["frequency_analysis"] = frequency_analysis

        if frequency_analysis["is_abnormal"]:
            issues.append(
                f"提交频率异常: {frequency_analysis['frequency']:.1f} 次/天，"
                f"超过阈值 {self.frequency_threshold} 次/天。"
            )
            issues.append(
                "建议：请确认是正常的高频开发还是需要拆分/合并提交。"
            )
            score *= 0.85

            if frequency_analysis["is_very_high"]:
                issues.append(
                    "警告：极高频提交可能影响代码评审质量，建议适当降低提交频率。"
                )
                score *= 0.85

        pattern_analysis = self._analyze_commit_patterns(recent_commits, current_author)
        details["pattern_analysis"] = pattern_analysis

        if pattern_analysis["large_commit_ratio"] > 0.3:
            issues.append(
                f"近期大提交比例较高 ({pattern_analysis['large_commit_ratio']:.0%})，"
                f"建议拆分为更小的原子提交。"
            )
            score *= 0.9

        conflict_analysis = self._analyze_file_conflicts(
            current_changed_files, recent_commits, current_author
        )
        details["conflict_analysis"] = conflict_analysis

        high_risk_files = conflict_analysis["high_risk_files"]
        if high_risk_files:
            for file_info in high_risk_files:
                issues.append(
                    f"文件冲突风险 [{file_info['risk_level']}]: "
                    f"'{file_info['file']}' 最近被 {len(file_info['authors'])} 人修改"
                    f"({file_info['recent_commits']} 次修改)，"
                    f"最近修改者: {file_info['last_commit_by']}"
                )

            if len(high_risk_files) >= 2:
                score *= 0.7
            else:
                score *= 0.8

            issues.append(
                "建议：修改前与相关作者沟通，拉取最新代码，避免合并冲突。"
            )

        contribution_analysis = self._analyze_contribution_patterns(
            recent_commits, current_author
        )
        details["contribution_analysis"] = contribution_analysis

        if contribution_analysis["is_solo_developer"] and len(recent_commits) >= 20:
            issues.append(
                "检测到单人开发模式，建议定期进行代码审查。"
            )
            score = min(score * 1.02, self.weight)

        work_pattern = self._analyze_work_pattern(recent_commits, current_author)
        details["work_pattern"] = work_pattern

        if work_pattern["after_hours_ratio"] > 0.5:
            issues.append(
                "注意：近期非工作时间提交较多，请保持工作生活平衡。"
            )

        hotspot_warnings = self._find_hotspot_files(current_changed_files, recent_commits)
        details["hotspot_files"] = hotspot_warnings

        if hotspot_warnings:
            issues.append(
                f"检测到 {len(hotspot_warnings)} 个热点文件，"
                f"这些文件近期被频繁修改：{', '.join(h[:3] for h in hotspot_warnings[:3])}"
            )

        score = round(score, 2)
        valid = score >= (max_score * 0.6)

        return HistoryAnalysisResult(
            valid=valid,
            score=score,
            max_score=max_score,
            issues=issues,
            details=details
        )

    def _filter_recent_commits(
        self, commit_history: List[CommitHistoryInfo]
    ) -> List[CommitHistoryInfo]:
        cutoff_time = (
            datetime.now() - timedelta(days=self.lookback_days)
        ).timestamp()

        return [
            commit for commit in commit_history
            if commit.timestamp >= cutoff_time
        ]

    def _analyze_commit_frequency(
        self, recent_commits: List[CommitHistoryInfo], current_author: str
    ) -> Dict[str, Any]:
        author_commits = [
            c for c in recent_commits
            if c.author == current_author or c.author_email == current_author
        ]

        if not author_commits:
            return {
                "frequency": 0,
                "is_abnormal": False,
                "is_very_high": False,
                "author_commits_count": 0
            }

        now = datetime.now().timestamp()
        oldest_timestamp = min(c.timestamp for c in author_commits)
        days_diff = max((now - oldest_timestamp) / 86400, 0.01)

        frequency = len(author_commits) / days_diff
        is_abnormal = frequency > self.frequency_threshold
        is_very_high = frequency > self.frequency_threshold * 2

        return {
            "frequency": round(frequency, 2),
            "is_abnormal": is_abnormal,
            "is_very_high": is_very_high,
            "author_commits_count": len(author_commits),
            "threshold": self.frequency_threshold,
            "days_analyzed": round(days_diff, 1)
        }

    def _analyze_commit_patterns(
        self, recent_commits: List[CommitHistoryInfo], current_author: str
    ) -> Dict[str, Any]:
        author_commits = [
            c for c in recent_commits
            if c.author == current_author or c.author_email == current_author
        ]

        if not author_commits:
            return {"large_commit_ratio": 0}

        large_commits = sum(
            1 for c in author_commits if len(c.files) > 10
        )
        ratio = large_commits / len(author_commits) if author_commits else 0

        return {
            "large_commit_ratio": round(ratio, 2),
            "large_commits": large_commits,
            "total_author_commits": len(author_commits)
        }

    def _analyze_file_conflicts(
        self,
        current_changed_files: List[str],
        recent_commits: List[CommitHistoryInfo],
        current_author: str
    ) -> Dict[str, Any]:
        file_activity: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"authors": set(), "commits": 0, "last_author": None}
        )

        for commit in recent_commits:
            for f in commit.files:
                file_activity[f]["authors"].add(commit.author)
                file_activity[f]["commits"] += 1
                file_activity[f]["last_author"] = commit.author

        high_risk_files: List[Dict[str, Any]] = []

        for current_file in current_changed_files:
            activity = file_activity.get(current_file, {})
            authors = activity.get("authors", set())
            commit_count = activity.get("commits", 0)
            last_author = activity.get("last_author", "")

            other_authors = [
                a for a in authors
                if a != current_author and a != last_author
            ]

            if len(authors) >= self.conflict_file_threshold or (
                len(authors) >= 2 and commit_count >= self.hotspot_threshold
            ):
                if len(authors) >= 3:
                    risk_level = "HIGH"
                elif len(authors) == 2 and commit_count >= self.hotspot_threshold:
                    risk_level = "MEDIUM"
                else:
                    continue

                high_risk_files.append({
                    "file": current_file,
                    "authors": sorted(authors),
                    "author_count": len(authors),
                    "other_authors": sorted(other_authors),
                    "recent_commits": commit_count,
                    "last_commit_by": last_author,
                    "risk_level": risk_level
                })

        return {
            "high_risk_files": high_risk_files,
            "total_files_analyzed": len(current_changed_files),
            "files_with_activity": len(file_activity)
        }

    def _analyze_contribution_patterns(
        self, recent_commits: List[CommitHistoryInfo], current_author: str
    ) -> Dict[str, Any]:
        all_authors = set(c.author for c in recent_commits)
        author_commit_counts: Dict[str, int] = defaultdict(int)

        for commit in recent_commits:
            author_commit_counts[commit.author] += 1

        author_commits = author_commit_counts.get(current_author, 0)
        total_commits = len(recent_commits)
        author_ratio = author_commits / total_commits if total_commits > 0 else 0

        is_solo_developer = len(all_authors) == 1 and list(all_authors)[0] == current_author

        return {
            "total_authors": len(all_authors),
            "author_commits": author_commits,
            "author_ratio": round(author_ratio, 2),
            "is_solo_developer": is_solo_developer,
            "all_authors": sorted(all_authors)
        }

    def _analyze_work_pattern(
        self, recent_commits: List[CommitHistoryInfo], current_author: str
    ) -> Dict[str, Any]:
        author_commits = [
            c for c in recent_commits
            if c.author == current_author or c.author_email == current_author
        ]

        if not author_commits:
            return {"after_hours_ratio": 0}

        after_hours = 0
        for commit in author_commits:
            dt = datetime.fromtimestamp(commit.timestamp)
            hour = dt.hour
            if hour < 9 or hour >= 19:
                after_hours += 1

        ratio = after_hours / len(author_commits)

        return {
            "after_hours_ratio": round(ratio, 2),
            "after_hours_commits": after_hours,
            "total_author_commits": len(author_commits)
        }

    def _find_hotspot_files(
        self, current_changed_files: List[str], recent_commits: List[CommitHistoryInfo]
    ) -> List[str]:
        file_commit_counts: Dict[str, int] = defaultdict(int)

        for commit in recent_commits:
            for f in commit.files:
                file_commit_counts[f] += 1

        hotspots = []
        for f in current_changed_files:
            count = file_commit_counts.get(f, 0)
            if count >= self.hotspot_threshold:
                hotspots.append(f"{f}({count}次)")

        return sorted(hotspots, key=lambda x: int(x.split("(")[1].rstrip("次)")), reverse=True)

    def extract_history_from_git(
        self, git_repo: Any, n: int = 100
    ) -> List[CommitHistoryInfo]:
        try:
            commits = git_repo.get_last_n_commits(n)
        except Exception:
            return []

        history: List[CommitHistoryInfo] = []
        for commit in commits:
            try:
                info = git_repo.get_commit_info(commit)
                files = git_repo.get_changed_files(commit)

                history.append(CommitHistoryInfo(
                    hash=info["hash"],
                    author=info["author_name"],
                    author_email=info["author_email"],
                    timestamp=info["timestamp"],
                    date=info["date"],
                    files=files,
                    message=info["message"]
                ))
            except Exception:
                continue

        return history
