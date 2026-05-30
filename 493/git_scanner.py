import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import git
from git import Repo, Commit, Blob


@dataclass
class LargeFileInfo:
    file_path: str
    max_size: int
    current_size: int
    first_introduced: datetime
    last_modified: datetime
    commit_count: int
    blob_ids: Set[str] = field(default_factory=set)
    file_type: str = "unknown"


class GitHistoryScanner:
    def __init__(self, repo_path: str):
        self.repo_path = os.path.abspath(repo_path)
        self.repo = Repo(self.repo_path)
        self.large_files: Dict[str, LargeFileInfo] = {}
        self.size_threshold: int = 10 * 1024 * 1024
        self.all_blobs: Dict[str, int] = {}

    def scan_history(self, size_threshold_mb: float = 10.0) -> Dict[str, LargeFileInfo]:
        self.size_threshold = int(size_threshold_mb * 1024 * 1024)
        self.large_files = {}

        refs = []
        try:
            refs.extend(self.repo.remotes.origin.refs)
        except (git.InvalidGitRepositoryError, AttributeError):
            pass

        try:
            refs.extend(self.repo.branches)
        except AttributeError:
            pass

        if not refs:
            refs = [self.repo.head.ref]

        scanned_commits: Set[str] = set()

        for ref in refs:
            try:
                for commit in self.repo.iter_commits(ref.name, reverse=True):
                    if commit.hexsha in scanned_commits:
                        continue
                    scanned_commits.add(commit.hexsha)
                    self._process_commit(commit)
            except (git.GitCommandError, ValueError):
                continue

        return self.large_files

    def _process_commit(self, commit: Commit):
        commit_time = datetime.fromtimestamp(commit.committed_date)

        try:
            for blob in self._get_all_blobs(commit.tree):
                self._process_blob(blob, commit_time, commit.hexsha)
        except (git.BadObject, ValueError):
            pass

    def _get_all_blobs(self, tree, prefix: str = "") -> List[Blob]:
        blobs = []
        try:
            for item in tree.traverse():
                if item.type == 'blob':
                    blobs.append(item)
        except (git.BadObject, ValueError):
            pass
        return blobs

    def _process_blob(self, blob: Blob, commit_time: datetime, commit_hexsha: str):
        file_path = blob.path
        blob_size = blob.size

        blob_id = blob.hexsha
        if blob_id in self.all_blobs:
            if self.all_blobs[blob_id] != blob_size:
                pass
        else:
            self.all_blobs[blob_id] = blob_size

        if blob_size >= self.size_threshold:
            self._update_large_file_info(
                file_path, blob_size, blob_id, commit_time, commit_hexsha
            )

    def _update_large_file_info(
        self,
        file_path: str,
        size: int,
        blob_id: str,
        commit_time: datetime,
        commit_hexsha: str
    ):
        if file_path not in self.large_files:
            self.large_files[file_path] = LargeFileInfo(
                file_path=file_path,
                max_size=size,
                current_size=size,
                first_introduced=commit_time,
                last_modified=commit_time,
                commit_count=1,
                blob_ids={blob_id}
            )
        else:
            info = self.large_files[file_path]
            info.max_size = max(info.max_size, size)
            info.current_size = size
            info.last_modified = commit_time
            info.commit_count += 1
            info.blob_ids.add(blob_id)

    def get_total_large_size(self) -> int:
        total = 0
        seen_blobs: Set[str] = set()
        for info in self.large_files.values():
            for blob_id in info.blob_ids:
                if blob_id not in seen_blobs:
                    seen_blobs.add(blob_id)
                    total += self.all_blobs.get(blob_id, 0)
        return total

    def get_repo_size(self) -> int:
        objects_dir = os.path.join(self.repo_path, '.git', 'objects')
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(objects_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size
