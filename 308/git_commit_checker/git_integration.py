import os
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import git
    from git import Repo, Commit
except ImportError:
    raise ImportError("GitPython is required. Install with: pip install GitPython")

from .size_analyzer import FileChangeStats


class GitRepository:
    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path or os.getcwd()
        self.repo = self._initialize_repo()

    def _initialize_repo(self) -> Repo:
        try:
            return Repo(self.repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def get_commit(self, commit_hash: str) -> Commit:
        try:
            return self.repo.commit(commit_hash)
        except git.BadName:
            raise ValueError(f"Invalid commit hash: {commit_hash}")

    def get_latest_commit(self) -> Commit:
        return self.repo.head.commit

    def get_last_n_commits(self, n: int) -> List[Commit]:
        commits = []
        try:
            for i, commit in enumerate(self.repo.iter_commits(max_count=n)):
                commits.append(commit)
                if i >= n - 1:
                    break
        except Exception:
            if n >= 1:
                commits.append(self.repo.head.commit)
        return commits

    def get_commits_in_range(self, start_ref: str, end_ref: str) -> List[Commit]:
        try:
            return list(self.repo.iter_commits(f"{start_ref}..{end_ref}"))
        except Exception as e:
            raise ValueError(f"Invalid commit range: {start_ref}..{end_ref}. Error: {e}")

    def get_commit_message(self, commit: Commit) -> str:
        return commit.message

    def get_changed_files(self, commit: Commit) -> List[str]:
        if commit.parents:
            parent = commit.parents[0]
            diffs = parent.diff(commit)
        else:
            diffs = commit.diff(git.NULL_TREE)

        changed_files = []
        for diff in diffs:
            if diff.a_path:
                changed_files.append(diff.a_path)
            if diff.b_path and diff.b_path != diff.a_path:
                changed_files.append(diff.b_path)

        return list(dict.fromkeys(changed_files))

    def get_file_stats(self, commit: Commit) -> List[FileChangeStats]:
        if commit.parents:
            parent = commit.parents[0]
            diffs = parent.diff(commit, create_patch=True)
        else:
            diffs = commit.diff(git.NULL_TREE, create_patch=True)

        stats: List[FileChangeStats] = []
        for diff in diffs:
            path = diff.b_path or diff.a_path
            if not path:
                continue

            insertions = 0
            deletions = 0

            if diff.diff:
                try:
                    diff_text = diff.diff.decode("utf-8", errors="replace")
                    for line in diff_text.split("\n"):
                        if line.startswith("+") and not line.startswith("+++"):
                            insertions += 1
                        elif line.startswith("-") and not line.startswith("---"):
                            deletions += 1
                except Exception:
                    pass

            if insertions == 0 and deletions == 0:
                try:
                    raw_stats = commit.stats.total
                    insertions = raw_stats.get("insertions", 0)
                    deletions = raw_stats.get("deletions", 0)
                except Exception:
                    pass

            stats.append(FileChangeStats(
                path=path,
                insertions=insertions,
                deletions=deletions,
                total=insertions + deletions
            ))

        return stats

    def get_commit_info(self, commit: Commit) -> Dict[str, Any]:
        return {
            "hash": commit.hexsha,
            "short_hash": commit.hexsha[:7],
            "message": commit.message,
            "subject": commit.message.split("\n")[0] if commit.message else "",
            "author": f"{commit.author.name} <{commit.author.email}>",
            "author_name": commit.author.name,
            "author_email": commit.author.email,
            "date": datetime.fromtimestamp(commit.committed_date).strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": commit.committed_date,
            "parents": [p.hexsha for p in commit.parents],
        }

    def get_current_branch(self) -> str:
        try:
            return self.repo.active_branch.name
        except TypeError:
            return "HEAD (detached)"

    def is_clean(self) -> bool:
        return not self.repo.is_dirty(untracked_files=True)
