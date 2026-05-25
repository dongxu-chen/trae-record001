import os
import tempfile
import shutil
from typing import Dict, List, Any, Optional
from github import Github
import gitlab


class GitIntegration:
    def __init__(self, platform: str = "github", token: str = None, gitlab_url: str = None):
        self.platform = platform.lower()
        self.token = token
        self.gitlab_url = gitlab_url or "https://gitlab.com"
        self.client = self._init_client()
        
    def _init_client(self):
        if self.platform == "github":
            return Github(self.token) if self.token else Github()
        elif self.platform == "gitlab":
            return gitlab.Gitlab(self.gitlab_url, private_token=self.token)
        else:
            raise ValueError(f"Unsupported platform: {self.platform}")
    
    def get_pr_diff(self, repo_owner: str, repo_name: str, pr_number: int) -> str:
        if self.platform == "github":
            return self._get_github_pr_diff(repo_owner, repo_name, pr_number)
        elif self.platform == "gitlab":
            return self._get_gitlab_mr_diff(repo_owner, repo_name, pr_number)
    
    def _get_github_pr_diff(self, repo_owner: str, repo_name: str, pr_number: int) -> str:
        repo = self.client.get_repo(f"{repo_owner}/{repo_name}")
        pr = repo.get_pull(pr_number)
        return pr.get_files()
    
    def _get_gitlab_mr_diff(self, repo_owner: str, repo_name: str, mr_iid: int) -> str:
        project = self.client.projects.get(f"{repo_owner}/{repo_name}")
        mr = project.mergerequests.get(mr_iid)
        return mr.changes()
    
    def get_pr_details(self, repo_owner: str, repo_name: str, pr_number: int) -> Dict[str, Any]:
        if self.platform == "github":
            return self._get_github_pr_details(repo_owner, repo_name, pr_number)
        elif self.platform == "gitlab":
            return self._get_gitlab_mr_details(repo_owner, repo_name, pr_number)
    
    def _get_github_pr_details(self, repo_owner: str, repo_name: str, pr_number: int) -> Dict[str, Any]:
        repo = self.client.get_repo(f"{repo_owner}/{repo_name}")
        pr = repo.get_pull(pr_number)
        return {
            "title": pr.title,
            "description": pr.body or "",
            "author": pr.user.login,
            "created_at": pr.created_at,
            "state": pr.state,
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files
        }
    
    def _get_gitlab_mr_details(self, repo_owner: str, repo_name: str, mr_iid: int) -> Dict[str, Any]:
        project = self.client.projects.get(f"{repo_owner}/{repo_name}")
        mr = project.mergerequests.get(mr_iid)
        return {
            "title": mr.title,
            "description": mr.description or "",
            "author": mr.author["name"],
            "created_at": mr.created_at,
            "state": mr.state,
            "base_branch": mr.target_branch,
            "head_branch": mr.source_branch,
            "additions": mr.diff_refs["head_sha"],
            "deletions": 0,
            "changed_files": len(mr.changes()["changes"])
        }
    
    def download_pr_files(self, repo_owner: str, repo_name: str, pr_number: int, 
                          target_dir: Optional[str] = None) -> str:
        if target_dir is None:
            target_dir = tempfile.mkdtemp(prefix="code_review_")
        
        if self.platform == "github":
            self._download_github_pr_files(repo_owner, repo_name, pr_number, target_dir)
        elif self.platform == "gitlab":
            self._download_gitlab_mr_files(repo_owner, repo_name, pr_number, target_dir)
        
        return target_dir
    
    def _download_github_pr_files(self, repo_owner: str, repo_name: str, 
                                  pr_number: int, target_dir: str):
        repo = self.client.get_repo(f"{repo_owner}/{repo_name}")
        pr = repo.get_pull(pr_number)
        
        for file in pr.get_files():
            if file.status == "removed":
                continue
            
            file_path = os.path.join(target_dir, file.filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            content = repo.get_contents(file.filename, ref=pr.head.sha)
            with open(file_path, 'wb') as f:
                f.write(content.decoded_content)
    
    def _download_gitlab_mr_files(self, repo_owner: str, repo_name: str, 
                                  mr_iid: int, target_dir: str):
        project = self.client.projects.get(f"{repo_owner}/{repo_name}")
        mr = project.mergerequests.get(mr_iid)
        changes = mr.changes()
        
        for change in changes["changes"]:
            if change["new_file"] == False and change["deleted_file"]:
                continue
            
            file_path = os.path.join(target_dir, change["new_path"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            try:
                content = project.files.get(change["new_path"], ref=mr.source_branch)
                with open(file_path, 'wb') as f:
                    f.write(content.decode())
            except Exception:
                pass
    
    def get_changed_files_list(self, repo_owner: str, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        if self.platform == "github":
            return self._get_github_changed_files(repo_owner, repo_name, pr_number)
        elif self.platform == "gitlab":
            return self._get_gitlab_changed_files(repo_owner, repo_name, pr_number)
    
    def _get_github_changed_files(self, repo_owner: str, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        repo = self.client.get_repo(f"{repo_owner}/{repo_name}")
        pr = repo.get_pull(pr_number)
        
        files = []
        for file in pr.get_files():
            files.append({
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "changes": file.changes,
                "patch": file.patch or ""
            })
        return files
    
    def _get_gitlab_changed_files(self, repo_owner: str, repo_name: str, mr_iid: int) -> List[Dict[str, Any]]:
        project = self.client.projects.get(f"{repo_owner}/{repo_name}")
        mr = project.mergerequests.get(mr_iid)
        changes = mr.changes()
        
        files = []
        for change in changes["changes"]:
            files.append({
                "filename": change["new_path"],
                "status": "added" if change["new_file"] else "modified" if not change["deleted_file"] else "removed",
                "additions": change["diff"].count("\n+"),
                "deletions": change["diff"].count("\n-"),
                "changes": change["diff"].count("\n"),
                "patch": change["diff"]
            })
        return files
