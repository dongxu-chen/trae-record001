import os
import subprocess
from typing import List, Optional, Set, Tuple, Dict
from dataclasses import dataclass
from enum import Enum

try:
    from git import Repo, InvalidGitRepositoryError, Diff
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    UNTRACKED = "untracked"
    STAGED_ADDED = "staged_added"
    STAGED_MODIFIED = "staged_modified"
    STAGED_DELETED = "staged_deleted"
    UNCHANGED = "unchanged"
    SCANNED = "scanned"
    UNKNOWN = "unknown"
    SPECIFIED = "specified"


@dataclass
class FileChange:
    path: str
    change_type: str
    abs_path: str
    old_path: Optional[str] = None


class GitRepoManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = os.path.abspath(repo_path)
        self.repo = None
        if GIT_AVAILABLE:
            try:
                self.repo = Repo(self.repo_path)
            except InvalidGitRepositoryError:
                self.repo = None

    def is_git_repo(self) -> bool:
        return self.repo is not None

    def get_changed_files(
        self,
        base_branch: str = "main",
        include_untracked: bool = True,
        extensions: Optional[List[str]] = None,
    ) -> List[FileChange]:
        if not self.is_git_repo():
            return self._scan_all_files(extensions)

        file_changes: List[FileChange] = []
        processed_new_paths: Set[str] = set()

        try:
            base_commit = self.repo.commit(base_branch)
            diffs = base_commit.diff(None, find_renames=True)

            for diff in diffs:
                change_type_str = self._get_diff_change_type(diff)

                if diff.renamed_file and diff.a_path and diff.b_path:
                    print(f"  Renamed detected: {diff.a_path} -> {diff.b_path}")
                    if diff.b_path not in processed_new_paths:
                        abs_path = os.path.join(self.repo_path, diff.b_path)
                        if os.path.isfile(abs_path):
                            if not extensions or self._matches_extension(diff.b_path, extensions):
                                file_changes.append(
                                    FileChange(
                                        path=diff.b_path,
                                        change_type=ChangeType.RENAMED.value,
                                        abs_path=abs_path,
                                        old_path=diff.a_path,
                                    )
                                )
                                processed_new_paths.add(diff.b_path)
                    continue

                if diff.b_path and not diff.deleted_file:
                    new_path = diff.b_path
                    if new_path in processed_new_paths:
                        continue
                    abs_path = os.path.join(self.repo_path, new_path)
                    if not os.path.isfile(abs_path):
                        continue
                    if extensions and not self._matches_extension(new_path, extensions):
                        continue
                    file_changes.append(
                        FileChange(
                            path=new_path,
                            change_type=change_type_str,
                            abs_path=abs_path,
                        )
                    )
                    processed_new_paths.add(new_path)

            if include_untracked:
                for untracked_file in self.repo.untracked_files:
                    if untracked_file in processed_new_paths:
                        continue
                    abs_path = os.path.join(self.repo_path, untracked_file)
                    if not os.path.isfile(abs_path):
                        continue
                    if extensions and not self._matches_extension(untracked_file, extensions):
                        continue
                    file_changes.append(
                        FileChange(
                            path=untracked_file,
                            change_type=ChangeType.UNTRACKED.value,
                            abs_path=abs_path,
                        )
                    )

        except Exception as e:
            print(f"Warning: Failed to get changed files: {e}")
            import traceback
            traceback.print_exc()
            return self._scan_all_files(extensions)

        return file_changes

    def _get_diff_change_type(self, diff) -> str:
        if diff.new_file:
            return ChangeType.ADDED.value
        if diff.deleted_file:
            return ChangeType.DELETED.value
        if diff.renamed_file:
            return ChangeType.RENAMED.value
        return ChangeType.MODIFIED.value

    def get_all_files(
        self,
        extensions: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
    ) -> List[FileChange]:
        if exclude_dirs is None:
            exclude_dirs = [
                ".git",
                "node_modules",
                "__pycache__",
                "venv",
                ".venv",
                "dist",
                "build",
                "target",
            ]

        file_changes: List[FileChange] = []

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for file_name in files:
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, self.repo_path)
                rel_path = rel_path.replace("\\", "/")

                if extensions and not self._matches_extension(file_name, extensions):
                    continue

                file_changes.append(
                    FileChange(
                        path=rel_path,
                        change_type=ChangeType.SCANNED.value,
                        abs_path=file_path,
                    )
                )

        return file_changes

    def _scan_all_files(
        self, extensions: Optional[List[str]] = None
    ) -> List[FileChange]:
        print("Not a git repository or git unavailable, scanning all files...")
        return self.get_all_files(extensions)

    def _matches_extension(self, file_path: str, extensions: List[str]) -> bool:
        _, ext = os.path.splitext(file_path)
        return ext.lower() in [e.lower() for e in extensions]

    def _get_change_type(self, file_path: str) -> str:
        if not self.repo:
            return ChangeType.UNKNOWN.value

        try:
            if file_path in self.repo.untracked_files:
                return ChangeType.UNTRACKED.value

            diffs = self.repo.index.diff(None)
            for diff in diffs:
                if diff.a_path == file_path or diff.b_path == file_path:
                    if diff.new_file:
                        return ChangeType.ADDED.value
                    if diff.deleted_file:
                        return ChangeType.DELETED.value
                    if diff.renamed_file:
                        return ChangeType.RENAMED.value
                    return ChangeType.MODIFIED.value

            staged_diffs = self.repo.head.commit.diff("HEAD")
            for diff in staged_diffs:
                if diff.a_path == file_path or diff.b_path == file_path:
                    if diff.new_file:
                        return ChangeType.STAGED_ADDED.value
                    if diff.deleted_file:
                        return ChangeType.STAGED_DELETED.value
                    return ChangeType.STAGED_MODIFIED.value

            return ChangeType.UNCHANGED.value
        except Exception:
            return ChangeType.UNKNOWN.value

    def get_current_branch(self) -> Optional[str]:
        if not self.repo:
            return None
        try:
            return self.repo.active_branch.name
        except Exception:
            return None

    def get_commit_hash(self) -> Optional[str]:
        if not self.repo:
            return None
        try:
            return self.repo.head.commit.hexsha
        except Exception:
            return None


def filter_files_by_extension(
    files: List[FileChange], extensions: List[str]
) -> List[FileChange]:
    return [f for f in files if f.path.lower().endswith(tuple(extensions))]


def detect_ci_platform() -> Optional[str]:
    ci_env = os.environ

    if "GITHUB_ACTIONS" in ci_env:
        return "github"
    elif "GITLAB_CI" in ci_env:
        return "gitlab"
    elif "TRAVIS" in ci_env:
        return "travis"
    elif "CIRCLECI" in ci_env:
        return "circleci"
    elif "JENKINS_URL" in ci_env:
        return "jenkins"
    elif "BITBUCKET_BUILD_NUMBER" in ci_env:
        return "bitbucket"

    return None


def get_ci_environment() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    ci_env = os.environ
    pr_number = None
    commit_sha = None
    platform = detect_ci_platform()

    if platform == "github":
        pr_number = (
            ci_env.get("GITHUB_PR_NUMBER")
            or ci_env.get("PR_NUMBER")
            or ci_env.get("GITHUB_EVENT_PULL_REQUEST_NUMBER")
        )
        commit_sha = ci_env.get("GITHUB_SHA")
        if not pr_number:
            ref = ci_env.get("GITHUB_REF", "")
            if ref.startswith("refs/pull/"):
                parts = ref.split("/")
                if len(parts) >= 3:
                    pr_number = parts[2]
    elif platform == "gitlab":
        pr_number = ci_env.get("CI_MERGE_REQUEST_IID")
        commit_sha = ci_env.get("CI_COMMIT_SHA")
    elif platform == "travis":
        pr_number = ci_env.get("TRAVIS_PULL_REQUEST")
        if pr_number == "false":
            pr_number = None
        commit_sha = ci_env.get("TRAVIS_COMMIT")
    elif platform == "circleci":
        pr_number = ci_env.get("CIRCLE_PR_NUMBER")
        commit_sha = ci_env.get("CIRCLE_SHA1")
    elif platform == "jenkins":
        pr_number = ci_env.get("CHANGE_ID")
        commit_sha = ci_env.get("GIT_COMMIT")
    elif platform == "bitbucket":
        pr_number = ci_env.get("BITBUCKET_PR_ID")
        commit_sha = ci_env.get("BITBUCKET_COMMIT")

    return platform, pr_number, commit_sha
