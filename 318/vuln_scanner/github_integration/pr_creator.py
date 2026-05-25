"""
PR 创建器
自动生成修复 PR
"""
import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .api_client import GitHubAPIClient
from ..models import FixSuggestion, ScanResult, SeverityLevel, Vulnerability


class PRCreator:
    """自动 PR 创建器"""

    def __init__(self, github_client: GitHubAPIClient):
        self.github = github_client

    def create_fix_pr(
        self,
        owner: str,
        repo: str,
        suggestions: List[FixSuggestion],
        base_branch: str = "main",
        branch_prefix: str = "fix/vulnerabilities",
        draft: bool = False,
    ) -> Dict[str, Any]:
        """创建修复 PR"""
        if not suggestions:
            raise ValueError("No fix suggestions provided")

        branch_name = self._generate_branch_name(branch_prefix, suggestions)
        pr_title = self._generate_pr_title(suggestions)
        pr_body = self._generate_pr_body(suggestions)

        self.github.create_branch(owner, repo, branch_name, base_branch)

        file_updates = self._prepare_file_updates(suggestions)
        for file_path, (old_content, new_content) in file_updates.items():
            try:
                file_info = self.github.get_file_content(owner, repo, file_path, base_branch)
                sha = file_info["sha"]
                message = f"fix: update {file_path} to fix vulnerabilities"

                self.github.update_file(
                    owner,
                    repo,
                    file_path,
                    new_content,
                    message,
                    sha,
                    branch_name,
                )
            except Exception as e:
                print(f"Warning: Failed to update {file_path}: {e}")

        pr = self.github.create_pull_request(
            owner=owner,
            repo=repo,
            title=pr_title,
            head=branch_name,
            base=base_branch,
            body=pr_body,
            draft=draft,
        )

        labels = self._get_labels_for_pr(suggestions)
        if labels:
            try:
                self.github.add_labels_to_issue(owner, repo, pr["number"], labels)
            except Exception:
                pass

        return {
            "pr": pr,
            "branch": branch_name,
            "suggestions": [s.to_dict() for s in suggestions],
            "files_updated": list(file_updates.keys()),
        }

    def _generate_branch_name(self, prefix: str, suggestions: List[FixSuggestion]) -> str:
        """生成分支名称"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if len(suggestions) == 1:
            dep = suggestions[0].dependency
            name = dep.name.lower().replace("_", "-")
            return f"{prefix}/{name}-{timestamp}"
        return f"{prefix}/batch-{timestamp}"

    def _generate_pr_title(self, suggestions: List[FixSuggestion]) -> str:
        """生成 PR 标题"""
        if len(suggestions) == 1:
            s = suggestions[0]
            dep = s.dependency
            highest = max(v.severity for v in s.vulnerabilities)
            return f"🔒 [{highest.value}] Fix vulnerabilities in {dep.full_name} ({s.current_version} → {s.suggested_version})"

        max_severity = SeverityLevel.LOW
        for s in suggestions:
            for v in s.vulnerabilities:
                if v.severity.order > max_severity.order:
                    max_severity = v.severity

        return (
            f"🔒 [{max_severity.value}] Fix {len(suggestions)} "
            f"vulnerabilit{'y' if len(suggestions) == 1 else 'ies'} in dependencies"
        )

    def _generate_pr_body(self, suggestions: List[FixSuggestion]) -> str:
        """生成 PR 描述"""
        body = []

        body.append("## 🔒 Security Vulnerability Fix")
        body.append("")
        body.append("This PR automatically fixes security vulnerabilities found in dependencies.")
        body.append("")

        summary = self._get_summary(suggestions)
        body.append("### 📊 Summary")
        body.append("")
        body.append(f"- **Total dependencies updated**: {len(suggestions)}")
        body.append(f"- **Critical**: {summary['critical']}")
        body.append(f"- **High**: {summary['high']}")
        body.append(f"- **Medium**: {summary['medium']}")
        body.append(f"- **Low**: {summary['low']}")
        body.append("")

        body.append("### 📦 Changes")
        body.append("")
        body.append("| Package | Current Version | New Version | Severity | CVEs | Breaking Changes |")
        body.append("|---------|----------------|-------------|----------|------|------------------|")

        for s in suggestions:
            cves = ", ".join(v.cve_id for v in s.vulnerabilities)
            highest = max(v.severity for v in s.vulnerabilities)
            breaking = "⚠️ Yes" if s.breaking_changes else "✅ No"
            body.append(
                f"| `{s.dependency.full_name}` | `{s.current_version}` | `{s.suggested_version}` | "
                f"{highest.value} | {cves} | {breaking} |"
            )

        body.append("")

        body.append("### 🐛 Vulnerability Details")
        body.append("")
        for s in suggestions:
            body.append(f"#### `{s.dependency.full_name}` {s.current_version} → {s.suggested_version}")
            body.append("")
            for v in s.vulnerabilities:
                body.append(f"- **{v.cve_id}** ({v.severity.value}, CVSS: {v.cvss_score})")
                body.append(f"  - {v.title}")
                if v.description:
                    body.append(f"  - {v.description[:150]}...")
                if v.fixed_versions:
                    body.append(f"  - Fixed in: {', '.join(v.fixed_versions)}")
                if v.references:
                    body.append(f"  - References: {v.references[0]}")
            body.append("")

        body.append("### ⚠️ Notes")
        body.append("")
        breaking_count = sum(1 for s in suggestions if s.breaking_changes)
        if breaking_count > 0:
            body.append(
                f"- **{breaking_count} package(s) have breaking changes**. "
                "Please review the changes carefully."
            )
        else:
            body.append("- No breaking changes detected. All updates are patch/minor versions.")
        body.append("")
        body.append("- This PR was generated automatically by the vulnerability scanner.")
        body.append("- Please verify the changes before merging.")
        body.append("- Run tests to ensure no regressions.")
        body.append("")
        body.append("---")
        body.append("*Generated by Dependency Vulnerability Scanner*")

        return "\n".join(body)

    def _get_summary(self, suggestions: List[FixSuggestion]) -> Dict[str, int]:
        """获取漏洞统计摘要"""
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
        for s in suggestions:
            for v in s.vulnerabilities:
                summary[v.severity.value.lower()] = summary.get(v.severity.value.lower(), 0) + 1
        return summary

    def _get_labels_for_pr(self, suggestions: List[FixSuggestion]) -> List[str]:
        """获取 PR 标签"""
        labels = ["security", "dependencies"]

        max_severity = SeverityLevel.LOW
        for s in suggestions:
            for v in s.vulnerabilities:
                if v.severity.order > max_severity.order:
                    max_severity = v.severity

        labels.append(f"severity: {max_severity.value.lower()}")

        for s in suggestions:
            if s.breaking_changes:
                labels.append("breaking change")
                break
            break

        return list(set(labels))

    def _prepare_file_updates(
        self,
        suggestions: List[FixSuggestion],
    ) -> Dict[str, Tuple[str, str]]:
        """准备文件更新内容"""
        updates = {}
        file_groups: Dict[str, List[FixSuggestion]] = {}

        for s in suggestions:
            dep = s.dependency
            dep_file = dep.path
            if dep_file:
                if dep_file not in file_groups:
                    file_groups[dep_file] = []
                file_groups[dep_file].append(s)

        for file_path, file_suggestions in file_groups.items():
            if not os.path.exists(file_path):
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                old_content = f.read()

            new_content = old_content
            for s in file_suggestions:
                new_content = self._apply_version_update(
                    file_path, new_content, s.dependency, s.suggested_version
                )

            if new_content != old_content:
                updates[file_path] = (old_content, new_content)

        return updates

    def _apply_version_update(
        self,
        file_path: str,
        content: str,
        dependency,
        new_version: str,
    ) -> str:
        """应用版本更新到文件内容"""
        file_name = os.path.basename(file_path)

        if file_name == "requirements.txt" or file_name.endswith(".txt"):
            pattern = re.compile(
                rf'(^{re.escape(dependency.name)}\s*)([=><!~]+[^,\n]*)',
                re.MULTILINE | re.IGNORECASE,
            )
            return pattern.sub(rf'\1=={new_version}', content)

        elif file_name == "package.json":
            try:
                data = json.loads(content)
                for dep_type in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
                    if dep_type in data and dependency.name in data[dep_type]:
                        old = data[dep_type][dependency.name]
                        if old.startswith("^"):
                            data[dep_type][dependency.name] = f"^{new_version}"
                        elif old.startswith("~"):
                            data[dep_type][dependency.name] = f"~{new_version}"
                        else:
                            data[dep_type][dependency.name] = new_version
                return json.dumps(data, indent=2) + "\n"
            except Exception:
                pass

        elif file_name == "go.mod":
            pattern = re.compile(
                rf'(\s*)({re.escape(dependency.name)})\s+([^\s]+)',
            )
            return pattern.sub(rf'\1\2 {new_version}', content)

        elif file_name == "pom.xml":
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(content)
                ns = ""
                if root.tag.startswith("{"):
                    ns = root.tag.split("}")[0] + "}"

                for dep in root.iter(f"{ns}dependency"):
                    group_id_elem = dep.find(f"{ns}groupId")
                    artifact_id_elem = dep.find(f"{ns}artifactId")
                    version_elem = dep.find(f"{ns}version")

                    if (
                        group_id_elem is not None
                        and artifact_id_elem is not None
                        and version_elem is not None
                        and group_id_elem.text == dependency.group_id
                        and artifact_id_elem.text == dependency.name
                    ):
                        version_elem.text = new_version

                return ET.tostring(root, encoding="unicode", xml_declaration=True)
            except Exception:
                pass

        return content

    def create_vulnerability_issue(
        self,
        owner: str,
        repo: str,
        vulnerabilities: List[Vulnerability],
        suggestions: Optional[List[FixSuggestion]] = None,
    ) -> Dict[str, Any]:
        """创建漏洞 Issue"""
        if not vulnerabilities:
            raise ValueError("No vulnerabilities provided")

        title = self._generate_issue_title(vulnerabilities)
        body = self._generate_issue_body(vulnerabilities, suggestions)

        labels = ["security", "vulnerability"]
        max_severity = max(v.severity for v in vulnerabilities)
        labels.append(f"severity: {max_severity.value.lower()}")

        return self.github.create_issue(owner, repo, title, body, labels)

    def _generate_issue_title(self, vulnerabilities: List[Vulnerability]) -> str:
        """生成 Issue 标题"""
        max_severity = max(v.severity for v in vulnerabilities)
        if len(vulnerabilities) == 1:
            v = vulnerabilities[0]
            return f"🔒 [{max_severity.value}] {v.cve_id} in {v.dependency.full_name}"
        return f"🔒 [{max_severity.value}] {len(vulnerabilities)} security vulnerabilities found"

    def _generate_issue_body(
        self,
        vulnerabilities: List[Vulnerability],
        suggestions: Optional[List[FixSuggestion]] = None,
    ) -> str:
        """生成 Issue 描述"""
        body = []

        body.append("## 🔒 Security Vulnerabilities Detected")
        body.append("")

        body.append("### 📊 Summary")
        body.append("")
        body.append(f"- **Total vulnerabilities**: {len(vulnerabilities)}")

        severity_counts = {}
        for v in vulnerabilities:
            sev = v.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]:
            if sev in severity_counts:
                body.append(f"- **{sev}**: {severity_counts[sev]}")
        body.append("")

        body.append("### 🐛 Vulnerabilities")
        body.append("")
        body.append("| CVE | Package | Severity | CVSS | Description |")
        body.append("|-----|---------|----------|------|-------------|")

        for v in vulnerabilities:
            body.append(
                f"| {v.cve_id} | `{v.dependency.full_name}` {v.dependency.version} | "
                f"{v.severity.value} | {v.cvss_score} | {v.title[:80]} |"
            )
        body.append("")

        if suggestions:
            body.append("### 💡 Suggested Fixes")
            body.append("")
            for s in suggestions:
                breaking = "⚠️ **Breaking Changes**" if s.breaking_changes else "✅ No breaking changes"
                body.append(
                    f"- `{s.dependency.full_name}`: {s.current_version} → **{s.suggested_version}** "
                    f"({s.upgrade_type}) - {breaking}"
                )
            body.append("")

        body.append("---")
        body.append("*Generated by Dependency Vulnerability Scanner*")

        return "\n".join(body)
