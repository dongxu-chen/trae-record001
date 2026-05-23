import sys
import os
from typing import Optional, List

import click

from . import __version__
from .config import load_config
from .checker import CodeQualityChecker


@click.group()
@click.version_option(version=__version__, prog_name="code-quality-checker")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=False, dir_okay=False),
    default=".code-quality.yml",
    help="Path to configuration file.",
)
@click.option(
    "--repo-path",
    "-r",
    type=click.Path(exists=True, file_okay=False),
    default=".",
    help="Path to the Git repository.",
)
@click.pass_context
def main(ctx, config: str, repo_path: str):
    """Code Quality Checker - A comprehensive code quality checking tool."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["repo_path"] = repo_path


@main.command()
@click.option(
    "--incremental/--no-incremental",
    default=None,
    help="Enable/disable incremental check (only changed files).",
)
@click.option(
    "--base-branch",
    "-b",
    type=str,
    default=None,
    help="Base branch for incremental check (default: main).",
)
@click.option(
    "--fix/--no-fix",
    default=False,
    help="Enable auto-fix for supported linters.",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "text"]),
    default=None,
    help="Output format.",
)
@click.option(
    "--save-report/--no-save-report",
    default=True,
    help="Save JSON report to file.",
)
@click.option(
    "--html/--no-html",
    default=None,
    help="Generate HTML report with charts.",
)
@click.argument("files", nargs=-1, type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def check(
    ctx,
    incremental: Optional[bool],
    base_branch: Optional[str],
    fix: bool,
    format: Optional[str],
    save_report: bool,
    html: Optional[bool],
    files: List[str],
):
    """Run code quality checks on the repository."""
    config_path = ctx.obj["config_path"]
    repo_path = ctx.obj["repo_path"]

    config = load_config(config_path)
    checker = CodeQualityChecker(config, repo_path)

    specific_files = list(files) if files else None

    if specific_files:
        click.echo(f"Checking specific files: {', '.join(specific_files)}")

    report, exit_code = checker.run(
        incremental=incremental,
        base_branch=base_branch,
        auto_fix=fix,
        specific_files=specific_files,
        format=format,
        save_report=save_report,
        generate_html=html if html is not None else False,
    )

    if exit_code != 0:
        click.echo()
        click.echo(click.style("✗ Quality checks failed!", fg="red", bold=True))
    else:
        click.echo()
        click.echo(click.style("✓ All quality checks passed!", fg="green", bold=True))

    sys.exit(exit_code)


@main.command("list")
@click.option(
    "--enabled/--all",
    default=False,
    help="Show only enabled linters.",
)
@click.pass_context
def list_linters(ctx, enabled: bool):
    """List available and enabled linters."""
    config_path = ctx.obj["config_path"]
    repo_path = ctx.obj["repo_path"]

    config = load_config(config_path)
    checker = CodeQualityChecker(config, repo_path)

    if enabled:
        linters = checker.list_enabled_linters()
        click.echo("Enabled linters:")
    else:
        linters = checker.list_available_linters()
        click.echo("Available linters:")

    for linter in linters:
        click.echo(f"  - {linter}")

    if not linters:
        click.echo("  (none)")


@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
    default=".code-quality.yml",
    help="Output path for the config file.",
)
def init_config(output: str):
    """Generate a default configuration file."""
    if os.path.exists(output):
        if not click.confirm(f"Config file {output} already exists. Overwrite?"):
            click.echo("Aborted.")
            return

    default_config = """thresholds:
  error: 0
  warning: 10
  pylint_score: 8.0

linters:
  eslint:
    enabled: true
    config_file: ".eslintrc.js"
    auto_fix: true
    extensions: [".js", ".jsx", ".ts", ".tsx", ".vue"]

  pylint:
    enabled: true
    config_file: ".pylintrc"
    auto_fix: false
    extensions: [".py"]
    args: ["--max-line-length=120"]

  black:
    enabled: true
    config_file: "pyproject.toml"
    auto_fix: true
    extensions: [".py", ".pyi"]
    args: ["--line-length", "120"]

  checkstyle:
    enabled: true
    config_file: "checkstyle.xml"
    auto_fix: false
    extensions: [".java"]
    jar_path: "checkstyle.jar"

custom_rules:
  - name: "no-todo-comment"
    pattern: "TODO|FIXME"
    message: "Found TODO/FIXME comment: {match}"
    severity: "warning"
    extensions: [".py", ".js", ".ts", ".java"]
    case_sensitive: false
    fixable: false

  - name: "no-console-log"
    pattern: "console\\\\.log\\\\("
    message: "Avoid using console.log in production code"
    severity: "warning"
    extensions: [".js", ".ts"]
    exclude_patterns: ["test", "spec"]
    fixable: false

  - name: "no-print-statement"
    pattern: "^\\\\s*print\\\\("
    message: "Avoid using print statements, use logging instead"
    severity: "warning"
    extensions: [".py"]
    exclude_patterns: ["test", "__init__"]
    fixable: false

quality_gate:
  enabled: true
  block_merge: true
  rules:
    - linter: "pylint"
      min_score: 8.0
      max_errors: 0
      max_warnings: 10

    - linter: "eslint"
      max_errors: 0
      max_warnings: 20

    - linter: "black"
      max_errors: 0

    - linter: "checkstyle"
      max_errors: 0
      max_warnings: 50

    - linter: "custom"
      max_errors: 0
      max_warnings: 10

incremental:
  enabled: true
  base_branch: "main"

report:
  format: "table"
  output_dir: "quality-reports"
  show_summary: true
  html:
    enabled: true
    include_charts: true
    include_trend: true
    include_details: true
    theme: "default"

ci:
  fail_on_threshold: true
  generate_badge: true
"""

    with open(output, "w", encoding="utf-8") as f:
        f.write(default_config)

    click.echo(f"Default config file created at: {output}")


@main.command()
@click.option(
    "--base-branch",
    "-b",
    type=str,
    default="main",
    help="Base branch to compare against.",
)
@click.pass_context
def show_changed(ctx, base_branch: str):
    """Show files that would be checked in incremental mode."""
    config_path = ctx.obj["config_path"]
    repo_path = ctx.obj["repo_path"]

    config = load_config(config_path)
    checker = CodeQualityChecker(config, repo_path)

    files = checker.get_files_to_check(
        incremental=True,
        base_branch=base_branch,
    )

    click.echo(f"Files changed since {base_branch}:")
    click.echo()

    if not files:
        click.echo("  (no changed files)")
        return

    for f in files:
        change_type = f.change_type or "unknown"
        color = "green" if change_type in ["added", "untracked"] else "yellow"
        if change_type == "renamed" and f.old_path:
            click.echo(f"  [{click.style(change_type, fg='cyan')}] {f.old_path} -> {f.path}")
        else:
            click.echo(f"  [{click.style(change_type, fg=color)}] {f.path}")

    click.echo()
    click.echo(f"Total: {len(files)} files")


if __name__ == "__main__":
    main(obj={})
