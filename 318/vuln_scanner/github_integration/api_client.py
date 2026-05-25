"""
GitHub API 客户端
"""
import os
import json
import base64
from typing import List, Dict, Any, Optional, Tuple
import requests

from ..models import FixSuggestion


class GitHubAPIClient:
    """GitHub API 客户端"""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None, api_version: str = "2022-11-28"):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.api_version = api_version
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": api_version,
        })
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送 API 请求"""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        response = self.session.request(method, url, timeout=30, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}

    def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """获取仓库信息"""
        return self._request("GET", f"repos/{owner}/{repo}")

    def get_branch(self, owner: str, repo: str, branch: str) -> Dict[str, Any]:
        """获取分支信息"""
        return self._request("GET", f"repos/{owner}/{repo}/branches/{branch}")

    def create_branch(
        self,
        owner: str,
        repo: str,
        new_branch: str,
        from_branch: str = "main",
    ) -> Dict[str, Any]:
        """创建新分支"""
        branch_info = self.get_branch(owner, repo, from_branch)
        sha = branch_info["commit"]["sha"]

        data = {
            "ref": f"refs/heads/{new_branch}",
            "sha": sha,
        }
        return self._request("POST", f"repos/{owner}/{repo}/git/refs", json=data)

    def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """获取文件内容"""
        return self._request(
            "GET",
            f"repos/{owner}/{repo}/contents/{path}",
            params={"ref": branch},
        )

    def update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        sha: str,
        branch: str,
    ) -> Dict[str, Any]:
        """更新文件内容"""
        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        data = {
            "message": message,
            "content": content_b64,
            "sha": sha,
            "branch": branch,
        }
        return self._request("PUT", f"repos/{owner}/{repo}/contents/{path}", json=data)

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
        draft: bool = False,
    ) -> Dict[str, Any]:
        """创建 Pull Request"""
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft,
        }
        return self._request("POST", f"repos/{owner}/{repo}/pulls", json=data)

    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """创建 Issue"""
        data = {
            "title": title,
            "body": body,
        }
        if labels:
            data["labels"] = labels
        return self._request("POST", f"repos/{owner}/{repo}/issues", json=data)

    def add_labels_to_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: List[str],
    ) -> Dict[str, Any]:
        """为 Issue 添加标签"""
        data = {"labels": labels}
        return self._request(
            "POST",
            f"repos/{owner}/{repo}/issues/{issue_number}/labels",
            json=data,
        )

    def search_repositories(self, query: str, per_page: int = 10) -> Dict[str, Any]:
        """搜索仓库"""
        return self._request(
            "GET",
            "search/repositories",
            params={"q": query, "per_page": per_page},
        )

    def get_user(self) -> Dict[str, Any]:
        """获取当前用户信息"""
        return self._request("GET", "user")

    def get_pulls(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """获取 Pull Request 列表"""
        return self._request(
            "GET",
            f"repos/{owner}/{repo}/pulls",
            params={"state": state, "per_page": per_page},
        )

    def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_title: Optional[str] = None,
        commit_message: Optional[str] = None,
        merge_method: str = "squash",
    ) -> Dict[str, Any]:
        """合并 Pull Request"""
        data = {"merge_method": merge_method}
        if commit_title:
            data["commit_title"] = commit_title
        if commit_message:
            data["commit_message"] = commit_message
        return self._request(
            "PUT",
            f"repos/{owner}/{repo}/pulls/{pull_number}/merge",
            json=data,
        )

    def compare_branches(
        self,
        owner: str,
        repo: str,
        base: str,
        head: str,
    ) -> Dict[str, Any]:
        """比较两个分支"""
        return self._request(
            "GET",
            f"repos/{owner}/{repo}/compare/{base}...{head}",
        )
