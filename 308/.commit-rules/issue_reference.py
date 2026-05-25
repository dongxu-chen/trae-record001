"""Custom rule: Require issue reference in commit messages."""
import re

name = "issue-reference"
weight = 10
config = {
    "pattern": r"(#\d+|ISSUE-\d+|JIRA-\d+)",
    "required": True,
}


def check(commit_info):
    """Check if commit message contains an issue reference."""
    from git_commit_checker.custom_rules import CustomRuleResult

    message = commit_info.get("message", "")
    pattern = config.get("pattern", r"(#\d+|ISSUE-\d+)")

    issues = []
    score = weight
    max_score = weight
    details = {}

    match = re.search(pattern, message)
    if not match:
        issues.append(
            "Commit message should contain an issue reference "
            "(e.g., #123, ISSUE-456, JIRA-789)"
        )
        score = 0
    else:
        details["issue_reference"] = match.group(0)

    valid = score >= max_score * 0.6
    return CustomRuleResult(
        rule_name=name,
        valid=valid,
        score=score,
        max_score=max_score,
        issues=issues,
        details=details
    )
