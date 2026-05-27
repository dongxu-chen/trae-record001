"""GitHub API客户端 - 分支管理、提交、PR创建、自动回退"""

import base64
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PRCreateResult:
    """PR创建结果"""
    success: bool
    pr_url: str = ""
    pr_number: int = 0
    branch_name: str = ""
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    rolled_back: bool = False
    rollback_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "branch_name": self.branch_name,
            "error": self.error,
            "details": self.details,
            "rolled_back": self.rolled_back,
            "rollback_details": self.rollback_details,
        }


class GitHubClient:
    """GitHub API客户端，支持本地Git操作和通过GitHub API创建PR及自动回退"""

    def __init__(self, token: Optional[str] = None, repo_path: Optional[str] = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.repo_path = repo_path or os.getcwd()
        self._github_api = None

        if self.token:
            try:
                from github import Github
                self._github_api = Github(self.token)
            except ImportError:
                print("[警告] PyGithub未安装，将使用git命令行和HTTP API")
                self._github_api = None

    def _run_git(self, *args: str, cwd: Optional[str] = None) -> Tuple[str, str, int]:
        """运行git命令"""
        cmd = ["git"] + list(args)
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except Exception as e:
            return "", str(e), 1

    def is_git_repo(self) -> bool:
        """检查是否在Git仓库中"""
        _, _, code = self._run_git("rev-parse", "--git-dir")
        return code == 0

    def get_current_branch(self) -> str:
        """获取当前分支名"""
        stdout, _, _ = self._run_git("branch", "--show-current")
        return stdout or "main"

    def get_repo_info(self) -> Dict[str, str]:
        """获取仓库信息"""
        stdout, _, _ = self._run_git("remote", "-v")
        info = {"remote": stdout, "branch": self.get_current_branch()}

        for line in stdout.splitlines():
            if "origin" in line and "fetch" in line:
                url = line.split()[1]
                if "github.com" in url:
                    parts = url.replace("git@github.com:", "").replace("https://github.com/", "").rstrip(".git")
                    info["owner"] = parts.split("/")[0] if "/" in parts else ""
                    info["repo"] = parts.split("/")[-1] if "/" in parts else parts
                    info["full_name"] = parts
                break

        return info

    def create_branch(self, branch_name: str, base: str = "") -> Tuple[bool, str]:
        """创建新分支"""
        if not base:
            base = self.get_current_branch()

        _, stderr, code = self._run_git("checkout", "-b", branch_name, base)
        if code != 0:
            return False, stderr

        return True, f"分支 {branch_name} 已创建"

    def checkout_branch(self, branch_name: str) -> Tuple[bool, str]:
        """切换分支"""
        _, stderr, code = self._run_git("checkout", branch_name)
        if code != 0:
            return False, stderr
        return True, f"已切换到分支 {branch_name}"

    def delete_local_branch(self, branch_name: str, force: bool = True) -> Tuple[bool, str]:
        """删除本地分支"""
        flag = "-D" if force else "-d"
        _, stderr, code = self._run_git("branch", flag, branch_name)
        if code != 0:
            return False, stderr
        return True, f"本地分支 {branch_name} 已删除"

    def delete_remote_branch(self, branch_name: str, remote: str = "origin") -> Tuple[bool, str]:
        """删除远程分支"""
        _, stderr, code = self._run_git("push", remote, "--delete", branch_name)
        if code != 0:
            return False, stderr
        return True, f"远程分支 {remote}/{branch_name} 已删除"

    def commit_changes(self, file_paths: List[str], message: str) -> Tuple[bool, str]:
        """提交更改"""
        for file_path in file_paths:
            _, stderr, code = self._run_git("add", file_path)
            if code != 0:
                return False, f"添加文件失败: {stderr}"

        _, stderr, code = self._run_git("commit", "-m", message)
        if code != 0:
            return False, f"提交失败: {stderr}"

        return True, "提交成功"

    def push_branch(self, branch_name: str, remote: str = "origin") -> Tuple[bool, str]:
        """推送分支到远程"""
        _, stderr, code = self._run_git("push", "-u", remote, branch_name)
        if code != 0:
            return False, f"推送失败: {stderr}"
        return True, "推送成功"

    def close_pull_request(self, owner: str, repo: str, pr_number: int) -> Tuple[bool, str]:
        """关闭PR"""
        if not self.token:
            return False, "缺少GitHub Token"

        try:
            import requests

            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            }
            payload = {"state": "closed"}

            response = requests.patch(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                return True, f"PR #{pr_number} 已关闭"
            else:
                return False, f"关闭PR失败: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"关闭PR异常: {str(e)}"

    def add_pr_comment(self, owner: str, repo: str, pr_number: int, comment: str) -> Tuple[bool, str]:
        """给PR添加评论"""
        if not self.token:
            return False, "缺少GitHub Token"

        try:
            import requests

            url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            }
            payload = {"body": comment}

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 201:
                return True, f"评论已添加到 PR #{pr_number}"
            else:
                return False, f"添加评论失败: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"添加评论异常: {str(e)}"

    def create_pull_request_via_api(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main",
    ) -> PRCreateResult:
        """通过GitHub API创建PR"""
        if not self.token:
            return PRCreateResult(
                success=False,
                error="缺少GitHub Token，请设置GITHUB_TOKEN环境变量",
                branch_name=head_branch,
            )

        try:
            import requests

            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            }
            payload = {
                "title": title,
                "body": body,
                "head": head_branch,
                "base": base_branch,
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 201:
                data = response.json()
                return PRCreateResult(
                    success=True,
                    pr_url=data.get("html_url", ""),
                    pr_number=data.get("number", 0),
                    branch_name=head_branch,
                    details=data,
                )
            else:
                return PRCreateResult(
                    success=False,
                    error=f"API返回 {response.status_code}: {response.text}",
                    branch_name=head_branch,
                )

        except ImportError:
            return self._create_pr_via_gh_cli(
                owner, repo, title, body, head_branch, base_branch
            )
        except Exception as e:
            return PRCreateResult(
                success=False,
                error=f"创建PR失败: {str(e)}",
                branch_name=head_branch,
            )

    def _create_pr_via_gh_cli(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ) -> PRCreateResult:
        """通过gh CLI创建PR"""
        try:
            cmd = [
                "gh", "pr", "create",
                "--title", title,
                "--body", body,
                "--base", base_branch,
                "--head", head_branch,
            ]
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode == 0:
                pr_url = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
                return PRCreateResult(
                    success=True,
                    pr_url=pr_url,
                    branch_name=head_branch,
                )
            else:
                return PRCreateResult(
                    success=False,
                    error=result.stderr or "gh CLI执行失败",
                    branch_name=head_branch,
                )
        except FileNotFoundError:
            return PRCreateResult(
                success=False,
                error="gh CLI未安装，请安装GitHub CLI或提供GITHUB_TOKEN",
                branch_name=head_branch,
            )
        except Exception as e:
            return PRCreateResult(
                success=False,
                error=f"gh CLI执行异常: {str(e)}",
                branch_name=head_branch,
            )

    def rollback_pr_creation(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        original_branch: str,
        pr_number: int = 0,
        error_message: str = "",
    ) -> Dict[str, Any]:
        """
        PR创建失败时的自动回退：
        1. 给PR添加注释说明失败原因（如果PR已创建）
        2. 关闭PR（如果PR已创建）
        3. 删除远程分支
        4. 切换回原分支
        5. 删除本地分支
        """
        rollback_steps: List[Dict[str, Any]] = []
        all_successful = True

        if pr_number > 0 and self.token:
            comment = self._generate_rollback_comment(error_message)
            success, msg = self.add_pr_comment(owner, repo, pr_number, comment)
            rollback_steps.append({
                "step": "add_comment",
                "success": success,
                "message": msg,
            })
            if not success:
                all_successful = False

            success, msg = self.close_pull_request(owner, repo, pr_number)
            rollback_steps.append({
                "step": "close_pr",
                "success": success,
                "message": msg,
            })
            if not success:
                all_successful = False

        success, msg = self.delete_remote_branch(branch_name)
        rollback_steps.append({
            "step": "delete_remote_branch",
            "success": success,
            "message": msg,
        })
        if not success:
            all_successful = False

        success, msg = self.checkout_branch(original_branch)
        rollback_steps.append({
            "step": "checkout_original",
            "success": success,
            "message": msg,
        })
        if not success:
            all_successful = False

        success, msg = self.delete_local_branch(branch_name)
        rollback_steps.append({
            "step": "delete_local_branch",
            "success": success,
            "message": msg,
        })
        if not success:
            all_successful = False

        return {
            "all_successful": all_successful,
            "steps": rollback_steps,
            "original_branch": original_branch,
            "cleanup_branch": branch_name,
        }

    def _generate_rollback_comment(self, error_message: str) -> str:
        """生成PR失败回退的评论"""
        comment = [
            "## ❌ PR自动回退",
            "",
            "此安全修复PR已自动回退，原因如下：",
            "",
            f"```",
            f"{error_message}",
            f"```",
            "",
            "### 回退操作：",
            "- PR已关闭",
            "- 修复分支已删除",
            "- 本地更改已回退",
            "",
            "### 建议处理步骤：",
            "1. 请检查上述错误原因",
            "2. 修复后重新运行安全修复工具",
            "3. 或手动创建PR解决这些安全问题",
            "",
            "---",
            "*由 Security Fixer v1.0 自动生成*",
        ]
        return "\n".join(comment)

    def create_pr_from_fixes(
        self,
        fixes: List[Dict[str, Any]],
        branch_prefix: str = "security-fix",
        base_branch: str = "main",
        auto_rollback: bool = True,
    ) -> PRCreateResult:
        """根据修复结果自动创建PR，支持失败时自动回退"""
        if not fixes:
            return PRCreateResult(
                success=False,
                error="没有需要创建PR的修复内容",
            )

        repo_info = self.get_repo_info()
        owner = repo_info.get("owner", "")
        repo_name = repo_info.get("repo", "")

        if not owner or not repo_name:
            return PRCreateResult(
                success=False,
                error="无法获取仓库信息，请确保在GitHub仓库中且已配置远程origin",
            )

        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"{branch_prefix}/{timestamp}"

        current_branch = self.get_current_branch()

        success, msg = self.create_branch(branch_name, base_branch)
        if not success:
            return PRCreateResult(
                success=False,
                error=f"创建分支失败: {msg}",
                branch_name=branch_name,
            )

        file_paths = []
        total_fixes = 0
        vuln_types = set()

        for fix in fixes:
            file_path = fix.get("file_path", "")
            if file_path:
                file_paths.append(file_path)
            total_fixes += fix.get("fixed_count", 0)
            for vt in fix.get("vuln_types", []):
                vuln_types.add(vt)

        if not file_paths:
            self.checkout_branch(current_branch)
            self.delete_local_branch(branch_name)
            return PRCreateResult(
                success=False,
                error="没有需要提交的文件更改",
                branch_name=branch_name,
            )

        vuln_summary = ", ".join(sorted(vuln_types))
        commit_msg = f"🔒 安全修复: 修复{total_fixes}个漏洞 ({vuln_summary})"

        success, msg = self.commit_changes(file_paths, commit_msg)
        if not success:
            self.checkout_branch(current_branch)
            self.delete_local_branch(branch_name)
            return PRCreateResult(
                success=False,
                error=f"提交失败: {msg}",
                branch_name=branch_name,
            )

        success, msg = self.push_branch(branch_name)
        if not success:
            self.checkout_branch(current_branch)
            self.delete_local_branch(branch_name)
            return PRCreateResult(
                success=False,
                error=f"推送失败: {msg}",
                branch_name=branch_name,
            )

        pr_title = f"🔒 安全修复: {total_fixes}个漏洞自动修复"
        pr_body = self._generate_pr_body(fixes, total_fixes, vuln_types, branch_name)

        result = self.create_pull_request_via_api(
            owner, repo_name, pr_title, pr_body, branch_name, base_branch
        )

        if not result.success and auto_rollback:
            rollback_result = self.rollback_pr_creation(
                owner,
                repo_name,
                branch_name,
                current_branch,
                result.pr_number,
                result.error,
            )
            result.rolled_back = True
            result.rollback_details = rollback_result
            result.error = f"PR创建失败，已自动回退: {result.error}"
        else:
            self.checkout_branch(current_branch)

        return result

    def _generate_pr_body(
        self,
        fixes: List[Dict[str, Any]],
        total_fixes: int,
        vuln_types: set,
        branch_name: str,
    ) -> str:
        """生成PR描述"""
        lines = [
            "## 🔒 安全漏洞自动修复",
            "",
            "此PR由Security Fixer工具自动生成，修复了以下安全漏洞：",
            "",
            f"- **修复漏洞总数**: {total_fixes}",
            f"- **漏洞类型**: {', '.join(sorted(vuln_types))}",
            f"- **分支名称**: {branch_name}",
            "",
            "---",
            "",
            "### 📋 修复详情",
            "",
        ]

        for fix in fixes:
            file_path = fix.get("file_path", "")
            fixed_count = fix.get("fixed_count", 0)
            skipped_count = fix.get("skipped_count", 0)
            actions = fix.get("actions", [])

            lines.append(f"#### 📄 {file_path}")
            lines.append(f"- 修复: {fixed_count} | 跳过: {skipped_count}")

            for action in actions[:5]:
                lines.append(f"  - {action.get('description', '')}")

            if len(actions) > 5:
                lines.append(f"  - ... 及其他 {len(actions) - 5} 个修复")

            lines.append("")

        lines.extend([
            "---",
            "",
            "### ⚠️ 注意事项",
            "",
            "- 此PR由自动化工具生成，请人工审查所有更改",
            "- 部分修复可能需要进一步调整以适应具体业务逻辑",
            "- 建议运行完整的测试套件确保功能正常",
            "- 请在合并前确认修复覆盖了所有安全风险",
            "",
            "---",
            "",
            "### 🔧 修复建议",
            "",
        ])

        for vt in sorted(vuln_types):
            suggestions = {
                "sql_injection": "SQL注入: 建议对所有数据库查询使用参数化查询，避免字符串拼接",
                "xss": "XSS: 建议对所有用户输入进行HTML转义或使用安全的模板渲染",
                "path_traversal": "路径遍历: 建议对文件路径进行白名单验证和规范化处理",
                "command_injection": "命令注入: 建议使用参数列表形式执行命令，避免shell=True",
            }
            if vt in suggestions:
                lines.append(f"- **{vt}**: {suggestions[vt]}")

        lines.extend([
            "",
            "---",
            "*由 Security Fixer v1.0 自动生成*",
        ])

        return "\n".join(lines)

    def get_changed_files(self, base_branch: str = "main") -> List[str]:
        """获取与基准分支的差异文件"""
        stdout, _, _ = self._run_git("diff", "--name-only", f"{base_branch}...HEAD")
        if stdout:
            return [f.strip() for f in stdout.splitlines() if f.strip()]
        return []

    def get_file_diff(self, file_path: str, base_branch: str = "main") -> str:
        """获取指定文件的差异"""
        stdout, _, _ = self._run_git("diff", f"{base_branch}...HEAD", "--", file_path)
        return stdout
