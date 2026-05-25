import os
import sys
import re
from typing import Optional, List

import click

from .config import ConfigLoader
from .checker import CommitQualityChecker
from .output_formatter import OutputFormatter
from .scoring_engine import CommitQualityReport


@click.group(invoke_without_command=True)
@click.version_option(version="1.0.0", prog_name="git-commit-checker")
@click.option("--config", "-c", type=click.Path(exists=True, dir_okay=False),
              help="Path to custom configuration file")
@click.option("--repo", "-r", type=click.Path(exists=True, file_okay=False),
              help="Path to git repository (defaults to current directory)")
@click.option("--format", "-f", "output_format",
              type=click.Choice(["human", "json", "markdown"]), default=None,
              help="Output format")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], repo: Optional[str],
        output_format: Optional[str], no_color: bool):
    """Git Commit Quality Checker - Analyze and score your Git commits."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["repo_path"] = repo
    ctx.obj["output_format"] = output_format
    ctx.obj["no_color"] = no_color

    if ctx.invoked_subcommand is None:
        ctx.invoke(check, commit=None, count=1)


@cli.command()
@click.argument("commit", required=False)
@click.option("--count", "-n", type=int, default=1,
              help="Check the last N commits")
@click.option("--range", "commit_range", type=str,
              help="Check commits in range (e.g., develop..feature/x)")
@click.option("--all", "check_all", is_flag=True, help="Check all commits")
@click.option("--strict", is_flag=True, help="Exit with non-zero code if any check fails")
@click.pass_context
def check(ctx: click.Context, commit: Optional[str], count: int,
          commit_range: Optional[str], check_all: bool, strict: bool):
    """Check commit quality."""
    try:
        checker = CommitQualityChecker(
            config_path=ctx.obj["config_path"],
            repo_path=ctx.obj["repo_path"]
        )

        config = checker.config
        output_format = ctx.obj["output_format"] or config.get("output.format", "human")
        use_color = not ctx.obj["no_color"] and config.get("output.color", True)
        formatter = OutputFormatter(config, use_color=use_color)

        reports: List[CommitQualityReport] = []

        if commit_range:
            match = re.match(r"^(\w+)\.\.(\w+)$", commit_range)
            if not match:
                click.echo(f"Invalid range format: {commit_range}. Use start..end", err=True)
                sys.exit(1)
            start, end = match.groups()
            reports = checker.check_commits_in_range(start, end)
        elif check_all:
            import git
            all_commits = list(checker.repo.repo.iter_commits())
            for c in reversed(all_commits):
                reports.append(checker.check_commit(c.hexsha))
        elif commit:
            reports = [checker.check_commit(commit)]
        else:
            reports = checker.check_last_n_commits(count)

        if not reports:
            click.echo("No commits found to check.", err=True)
            sys.exit(1)

        output = formatter.format(reports, output_format)
        click.echo(output)

        if strict:
            failed = sum(1 for r in reports if not r.passed)
            if failed > 0:
                sys.exit(1)

    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)


@cli.command()
@click.option("--path", type=click.Path(), default=".commit-checker.yaml",
              help="Path to generate config file")
@click.option("--force", is_flag=True, help="Overwrite existing file")
def init_config(path: str, force: bool):
    """Generate a default configuration file."""
    default_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "default_config.yaml"
    )

    if os.path.exists(path) and not force:
        click.echo(f"Config file already exists: {path}. Use --force to overwrite.", err=True)
        sys.exit(1)

    try:
        with open(default_path, "r", encoding="utf-8") as src:
            content = src.read()

        with open(path, "w", encoding="utf-8") as dst:
            dst.write(content)

        click.echo(f"Configuration file generated: {path}")
    except Exception as e:
        click.echo(f"Failed to generate config: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--ci", type=click.Choice(["github", "gitlab", "jenkins", "generic"]),
              default="generic", help="CI platform type")
@click.option("--output", type=click.Path(), help="Output file path")
def generate_ci(ci: str, output: Optional[str]):
    """Generate CI integration configuration."""
    ci_configs = {
        "github": """name: Commit Quality Check

on: [pull_request, push]

jobs:
  commit-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install git-commit-quality-checker

      - name: Check commit quality
        run: |
          if [ "${{ github.event_name }}" = "pull_request" ]; then
            git-commit-check check --range ${{ github.base_ref }}..${{ github.head_ref }} --strict
          else
            git-commit-check check -n 1 --strict
          fi
""",
        "gitlab": """commit-quality-check:
  stage: test
  image: python:3.11-slim
  before_script:
    - pip install git-commit-quality-checker
  script:
    - |
      if [ "$CI_COMMIT_BRANCH" = "main" ] || [ "$CI_COMMIT_BRANCH" = "master" ]; then
        git-commit-check check -n 1 --strict
      elif [ "$CI_PIPELINE_SOURCE" = "merge_request_event" ]; then
        git-commit-check check --range $CI_MERGE_REQUEST_DIFF_BASE_SHA..$CI_COMMIT_SHA --strict
      else
        git-commit-check check -n 1 --strict
      fi
  rules:
    - if: '$CI_COMMIT_BRANCH'
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
""",
        "jenkins": """pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install git-commit-quality-checker
                '''
            }
        }

        stage('Commit Quality Check') {
            steps {
                sh '''
                    . venv/bin/activate
                    if [ -n "${CHANGE_BRANCH}" ]; then
                        git-commit-check check --range ${CHANGE_TARGET}..${CHANGE_BRANCH} --strict
                    else
                        git-commit-check check -n 1 --strict
                    fi
                '''
            }
        }
    }
}
""",
        "generic": """#!/bin/bash
# Git Commit Quality Checker - Generic CI Script

set -e

echo "Running Git Commit Quality Checker..."

# Install
pip install git-commit-quality-checker

# Check last commit (adjust as needed)
git-commit-check check -n 1 --strict

echo "Commit quality check passed!"
""",
    }

    content = ci_configs.get(ci, ci_configs["generic"])

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"CI configuration for {ci} generated: {output}")
    else:
        click.echo(content)


@cli.command()
@click.pass_context
@click.argument("message", required=False)
@click.option("--file", "-f", type=click.Path(exists=True, dir_okay=False),
              help="Read commit message from file")
@click.option("--type", "-t", help="Commit type (feat, fix, docs, etc.)")
@click.option("--scope", "-s", help="Commit scope")
@click.option("--subject", help="Commit subject")
@click.option("--body", help="Commit body")
@click.option("--output", "-o", type=click.Choice(["raw", "json"]), default="raw",
              help="Output format")
def format_commit(ctx: click.Context, message: Optional[str], file: Optional[str], type: Optional[str],
                  scope: Optional[str], subject: Optional[str], body: Optional[str],
                  output: str):
    """Format or validate a commit message."""
    if file:
        with open(file, "r", encoding="utf-8") as f:
            message = f.read()
    elif not message and not subject:
        message = click.edit()
        if not message:
            click.echo("No commit message provided.", err=True)
            sys.exit(1)

    if not message and subject:
        parts = []
        if type:
            scope_part = f"({scope})" if scope else ""
            parts.append(f"{type}{scope_part}:")
        parts.append(subject)
        message = " ".join(parts)
        if body:
            message += f"\n\n{body}"

    if not message:
        click.echo("No commit message provided.", err=True)
        sys.exit(1)

    config = ConfigLoader(ctx.obj.get("config_path"))
    checker = CommitQualityChecker(
        config_path=ctx.obj.get("config_path"),
        repo_path=ctx.obj.get("repo_path")
    )

    format_result = checker.format_checker.check(message)

    if output == "json":
        import json
        result = {
            "valid": format_result.valid,
            "score": format_result.score,
            "max_score": format_result.max_score,
            "issues": format_result.issues,
            "details": format_result.details,
            "formatted_message": message,
        }
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if format_result.valid:
            click.echo("✅ Commit message format is valid!")
            click.echo()
            click.echo("Formatted message:")
            click.echo("-" * 40)
            click.echo(message)
            click.echo("-" * 40)
        else:
            click.echo("❌ Commit message format issues found:")
            for issue in format_result.issues:
                click.echo(f"  - {issue}")
            click.echo()
            click.echo("Expected format: <type>[optional scope]: <description>")
            click.echo("Example: feat(auth): add user login functionality")
            sys.exit(1)


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def pre_commit(output: Optional[str]):
    """Generate a pre-commit hook script."""
    script = """#!/usr/bin/env python3
\"\"\"Pre-commit hook for Git Commit Quality Checker.\"\"\"

import sys
import subprocess
import tempfile
import os

def main():
    # Get the commit message
    commit_msg_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.environ.get('GIT_DIR', '.git'), 'COMMIT_EDITMSG'
    )

    with open(commit_msg_file, 'r', encoding='utf-8') as f:
        message = f.read()

    # Skip comments and empty lines
    lines = [l for l in message.split('\\n') if not l.startswith('#')]
    cleaned = '\\n'.join(lines).strip()

    if not cleaned:
        return 0

    # Run format check
    try:
        from git_commit_checker.cli import format_commit
        result = subprocess.run(
            ['git-commit-check', 'format-commit', cleaned, '--output', 'json'],
            capture_output=True, text=True
        )
        import json
        data = json.loads(result.stdout)

        if not data['valid']:
            print('\\n❌ Commit message quality check failed:')
            for issue in data['issues']:
                print(f'   - {issue}')
            print()
            print('   Expected format: <type>[optional scope]: <description>')
            print('   Example: feat(auth): add user login functionality')
            print()
            return 1
    except ImportError:
        print('Warning: git-commit-checker not installed, skipping format check')
    except Exception as e:
        print(f'Warning: Could not run commit check: {e}')

    return 0

if __name__ == '__main__':
    sys.exit(main())
"""

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(script)
        os.chmod(output, 0o755)
        click.echo(f"Pre-commit hook generated: {output}")
        click.echo(f"Install with: cp {output} .git/hooks/commit-msg")
    else:
        click.echo(script)


@cli.command()
@click.option("--staged", is_flag=True, help="Use staged files for recommendation")
@click.option("--files", "-f", multiple=True, help="Specific files to analyze")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text",
              help="Output format")
@click.option("--count", "-n", type=int, default=3,
              help="Number of recommendations to show")
@click.pass_context
def recommend(ctx: click.Context, staged: bool, files: tuple, output: str, count: int):
    """Recommend commit message templates based on changed files."""
    try:
        from .template_recommender import TemplateRecommender
        from .git_integration import GitRepository
        from .size_analyzer import FileChangeStats

        config = ConfigLoader(ctx.obj.get("config_path"))
        recommender = TemplateRecommender(config)

        repo_path = ctx.obj.get("repo_path") or os.getcwd()

        if staged or not files:
            repo = GitRepository(repo_path)
            try:
                changed_files = repo.get_changed_files(repo.repo.head.commit)
                file_stats = repo.get_file_stats(repo.repo.head.commit)
            except Exception:
                import git
                try:
                    repo_obj = git.Repo(repo_path, search_parent_directories=True)
                    changed_files = [item.a_path for item in repo_obj.index.diff(None)]
                    changed_files += [item.a_path for item in repo_obj.index.diff("HEAD")]
                    changed_files = list(set(changed_files))
                    file_stats = []
                except Exception:
                    changed_files = []
                    file_stats = []
        else:
            changed_files = list(files)
            file_stats = []

        if not changed_files:
            click.echo("No changed files detected for recommendation.", err=True)
            sys.exit(1)

        result = recommender.recommend(changed_files, file_stats, None, None)

        if output == "json":
            import json
            output_data = {
                "valid": result.valid,
                "score": result.score,
                "details": result.details,
                "recommendations": [
                    {
                        "template": rec.template,
                        "type": rec.type,
                        "scopes": rec.scopes,
                        "subject": rec.subject_suggestion,
                        "body": rec.body_suggestion,
                        "confidence": rec.confidence,
                        "reason": rec.reason
                    } for rec in result.recommendations[:count]
                ]
            }
            click.echo(json.dumps(output_data, indent=2, ensure_ascii=False))
        else:
            click.echo("📝 Commit Message Recommendations")
            click.echo("=" * 50)
            click.echo()
            click.echo(f"Analyzing {len(changed_files)} changed files:")
            for f in changed_files[:5]:
                click.echo(f"  - {f}")
            if len(changed_files) > 5:
                click.echo(f"  ... and {len(changed_files) - 5} more")
            click.echo()

            if not result.recommendations:
                click.echo("No recommendations generated.")
            else:
                formatted = recommender.format_recommendations(
                    result.recommendations[:count], "text"
                )
                click.echo(formatted)

    except Exception as e:
        click.echo(f"Error generating recommendations: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--days", "-d", type=int, default=30, help="Days of history to analyze")
@click.option("--output", "-o", type=click.Choice(["text", "json"]), default="text",
              help="Output format")
@click.pass_context
def analyze_history(ctx: click.Context, days: int, output: str):
    """Analyze commit history for frequency anomalies and conflict risks."""
    try:
        from .history_analyzer import HistoryAnalyzer, CommitHistoryInfo
        from .git_integration import GitRepository

        config = ConfigLoader(ctx.obj.get("config_path"))
        config_data = config._config if hasattr(config, "_config") else {}
        config_data["history_analysis.lookback_days"] = days
        analyzer = HistoryAnalyzer(config)

        repo_path = ctx.obj.get("repo_path") or os.getcwd()
        repo = GitRepository(repo_path)

        try:
            commits = list(repo.repo.iter_commits(max_count=200))
        except Exception:
            click.echo("Failed to get commit history.", err=True)
            sys.exit(1)

        if len(commits) < 5:
            click.echo("Not enough commit history for analysis (need at least 5 commits).")
            sys.exit(0)

        history: List[CommitHistoryInfo] = []
        from datetime import datetime
        for commit in commits:
            try:
                info = repo.get_commit_info(commit)
                files = repo.get_changed_files(commit)
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

        if not history:
            click.echo("No valid commit history found.", err=True)
            sys.exit(1)

        current_commit = history[0] if history else None
        current_files = current_commit.files if current_commit else []
        current_author = current_commit.author if current_commit else ""
        current_hash = current_commit.hash if current_commit else ""

        result = analyzer.analyze(current_hash, current_files, current_author, history)

        if output == "json":
            import json
            output_data = {
                "valid": result.valid,
                "score": result.score,
                "details": result.details,
                "issues": result.issues,
                "history_summary": {
                    "total_commits": len(history),
                    "days_analyzed": days,
                    "unique_authors": len(set(c.author for c in history)),
                }
            }
            click.echo(json.dumps(output_data, indent=2, ensure_ascii=False))
        else:
            click.echo("📊 Commit History Analysis")
            click.echo("=" * 50)
            click.echo()
            click.echo(f"Total commits analyzed: {len(history)}")
            click.echo(f"Time period: Last {days} days")
            click.echo(f"Unique authors: {len(set(c.author for c in history))}")
            click.echo()

            details = result.details

            if "frequency_analysis" in details:
                freq = details["frequency_analysis"]
                click.echo("📈 Commit Frequency:")
                click.echo(f"  Your frequency: {freq.get('frequency', 0):.1f} commits/day")
                click.echo(f"  Threshold: {freq.get('threshold', 10)} commits/day")
                if freq.get("is_abnormal"):
                    click.echo("  ⚠️  High frequency detected!")
                click.echo()

            if "conflict_analysis" in details:
                conflicts = details["conflict_analysis"]
                high_risk = conflicts.get("high_risk_files", [])
                if high_risk:
                    click.echo("⚠️  Potential Conflict Risks:")
                    for f in high_risk:
                        click.echo(f"  - [{f['risk_level']}] {f['file']}")
                        click.echo(f"      Authors: {', '.join(f['authors'])}")
                        click.echo(f"      Recent changes: {f['recent_commits']} commits")
                    click.echo()

            if "hotspot_files" in details and details["hotspot_files"]:
                click.echo("🔥 Hotspot Files (frequently modified):")
                for h in details["hotspot_files"][:5]:
                    click.echo(f"  - {h}")
                click.echo()

            if "contribution_analysis" in details:
                contrib = details["contribution_analysis"]
                click.echo("👥 Contribution Patterns:")
                click.echo(f"  Total authors: {contrib.get('total_authors', 1)}")
                click.echo(f"  Your commits: {contrib.get('author_commits', 0)} "
                          f"({contrib.get('author_ratio', 0):.0%} of total)")
                if contrib.get("is_solo_developer"):
                    click.echo("  💡 Tip: Solo development detected, consider code reviews.")
                click.echo()

            if result.issues:
                click.echo("💡 Recommendations:")
                for issue in result.issues:
                    click.echo(f"  - {issue}")

    except Exception as e:
        click.echo(f"Error analyzing history: {e}", err=True)
        sys.exit(1)


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
