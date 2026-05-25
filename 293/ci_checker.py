"""CI检查集成模块 - 支持GitHub Actions、GitLab CI等自动化检查"""

import os
import sys
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from colorama import Fore, Style

from dockerfile_parser import DockerfileParser
from cache_analyzer import CacheAnalyzer
from optimizer import Optimizer, OptimizationSeverity
from build_time_predictor import BuildTimePredictor


class CIProvider(Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    GENERIC = "generic"


class CheckStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class CheckResult:
    check_name: str
    status: CheckStatus
    message: str
    severity: Optional[OptimizationSeverity] = None
    details: Dict[str, Any] = field(default_factory=dict)


class CIChecker:
    def __init__(self, dockerfile_path: str, context_path: Optional[str] = None):
        self.dockerfile_path = dockerfile_path
        self.context_path = context_path
        self.checks: List[CheckResult] = []
        self._analyze()

    def _analyze(self):
        """执行所有分析"""
        self.parser = DockerfileParser(self.dockerfile_path, self.context_path)
        self.parser.analyze_stage_dependencies()
        self.analyzer = CacheAnalyzer(self.parser, self.context_path)
        self.optimizer = Optimizer(self.parser, self.analyzer)
        self.time_predictor = BuildTimePredictor(self.parser, self.optimizer)
        self._run_checks()

    def _run_checks(self):
        """运行所有检查项"""
        self._check_cache_score()
        self._check_critical_issues()
        self._check_high_risk_cache_breakers()
        self._check_high_churn_files()
        self._check_multistage_dependencies()
        self._check_large_layers()
        self._check_duplicate_commands()

    def _check_cache_score(self):
        """检查整体缓存得分"""
        score = self.analyzer.get_overall_cache_score()

        if score >= 0.7:
            status = CheckStatus.PASS
            message = f"缓存得分优秀: {score:.1%}"
        elif score >= 0.3:
            status = CheckStatus.WARN
            message = f"缓存得分一般: {score:.1%}，建议优化"
        else:
            status = CheckStatus.FAIL
            message = f"缓存得分较差: {score:.1%}，急需优化"

        self.checks.append(CheckResult(
            check_name="cache_score",
            status=status,
            message=message,
            details={"score": score}
        ))

    def _check_critical_issues(self):
        """检查严重问题"""
        critical_count = len(self.optimizer.get_suggestions_by_severity(OptimizationSeverity.CRITICAL))

        if critical_count == 0:
            self.checks.append(CheckResult(
                check_name="critical_issues",
                status=CheckStatus.PASS,
                message="无严重问题",
                details={"count": 0}
            ))
        else:
            self.checks.append(CheckResult(
                check_name="critical_issues",
                status=CheckStatus.FAIL,
                message=f"发现 {critical_count} 个严重问题，需要立即修复",
                severity=OptimizationSeverity.CRITICAL,
                details={"count": critical_count}
            ))

    def _check_high_risk_cache_breakers(self):
        """检查高风险缓存破坏点"""
        breakers = self.analyzer.get_cache_breakers()

        if len(breakers) == 0:
            self.checks.append(CheckResult(
                check_name="cache_breakers",
                status=CheckStatus.PASS,
                message="无高风险缓存破坏点",
                details={"count": 0}
            ))
        else:
            self.checks.append(CheckResult(
                check_name="cache_breakers",
                status=CheckStatus.WARN,
                message=f"发现 {len(breakers)} 个高风险缓存破坏点",
                severity=OptimizationSeverity.HIGH,
                details={"count": len(breakers)}
            ))

    def _check_high_churn_files(self):
        """检查高频文件顺序问题"""
        misplaced = self.analyzer.get_misplaced_high_churn_layers()

        if len(misplaced) == 0:
            self.checks.append(CheckResult(
                check_name="file_order",
                status=CheckStatus.PASS,
                message="文件顺序合理",
                details={"count": 0}
            ))
        else:
            self.checks.append(CheckResult(
                check_name="file_order",
                status=CheckStatus.WARN,
                message=f"发现 {len(misplaced)} 处高频文件前置问题",
                severity=OptimizationSeverity.MEDIUM,
                details={"count": len(misplaced)}
            ))

    def _check_multistage_dependencies(self):
        """检查多阶段构建依赖"""
        cross_deps = self.parser.get_cross_stage_copies()

        if len(cross_deps) == 0:
            self.checks.append(CheckResult(
                check_name="multistage",
                status=CheckStatus.PASS,
                message="无跨阶段依赖（或非多阶段构建）",
                details={"count": 0}
            ))
        else:
            self.checks.append(CheckResult(
                check_name="multistage",
                status=CheckStatus.PASS,
                message=f"多阶段构建正常，{len(cross_deps)} 处跨阶段复制",
                details={"count": len(cross_deps)}
            ))

    def _check_large_layers(self):
        """检查过大的层"""
        from size_analyzer import SizeAnalyzer
        size_analyzer = SizeAnalyzer(self.parser)
        warnings = size_analyzer.get_size_warnings()

        if len(warnings) == 0:
            self.checks.append(CheckResult(
                check_name="layer_size",
                status=CheckStatus.PASS,
                message="层大小合理",
                details={"count": 0}
            ))
        else:
            self.checks.append(CheckResult(
                check_name="layer_size",
                status=CheckStatus.WARN,
                message=f"发现 {len(warnings)} 个过大的层",
                severity=OptimizationSeverity.MEDIUM,
                details={"count": len(warnings)}
            ))

    def _check_duplicate_commands(self):
        """检查重复命令"""
        shared_layers = self.optimizer.get_shared_layers()

        if len(shared_layers) == 0:
            self.checks.append(CheckResult(
                check_name="duplicate_layers",
                status=CheckStatus.PASS,
                message="无重复层",
                details={"count": 0}
            ))
        else:
            total_savings = sum(l.incremental_savings for l in shared_layers)
            from size_analyzer import SizeAnalyzer
            self.checks.append(CheckResult(
                check_name="duplicate_layers",
                status=CheckStatus.WARN,
                message=f"发现 {len(shared_layers)} 个重复层，可共享优化",
                severity=OptimizationSeverity.LOW,
                details={
                    "count": len(shared_layers),
                    "potential_savings": total_savings
                }
            ))

    def get_status(self) -> CheckStatus:
        """获取整体状态"""
        if any(c.status == CheckStatus.FAIL for c in self.checks):
            return CheckStatus.FAIL
        if any(c.status == CheckStatus.WARN for c in self.checks):
            return CheckStatus.WARN
        return CheckStatus.PASS

    def format_github_annotations(self) -> List[Dict]:
        """格式化为GitHub Actions注解"""
        annotations = []

        for check in self.checks:
            if check.status == CheckStatus.PASS:
                continue

            annotation_level = "failure" if check.status == CheckStatus.FAIL else "warning"

            annotations.append({
                "path": self.dockerfile_path,
                "start_line": 1,
                "end_line": 1,
                "annotation_level": annotation_level,
                "title": check.check_name,
                "message": check.message
            })

        return annotations

    def print_github_output(self):
        """输出GitHub Actions格式结果"""
        status = self.get_status()
        exit_code = 0 if status == CheckStatus.PASS else 1

        annotations = self.format_github_annotations()

        output = {
            "status": status.value,
            "checks": [
                {
                    "name": c.check_name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details
                }
                for c in self.checks
            ],
            "annotations": annotations,
            "summary": self._generate_summary()
        }

        with open(os.environ.get('GITHUB_OUTPUT', 'ci-results.json'), 'w') as f:
            f.write(f"results={json.dumps(output, ensure_ascii=False)}\n")

        print(json.dumps(output, indent=2, ensure_ascii=False))
        return exit_code

    def print_gitlab_output(self):
        """输出GitLab CI格式结果"""
        status = self.get_status()
        exit_code = 0 if status == CheckStatus.PASS else 1

        report = {
            "version": "2.0",
            "$schema": "https://gitlab.com/gitlab-org/ci-cd/codequality/-/blob/master/schemas/codequality.json",
            "issues": []
        }

        severity_map = {
            OptimizationSeverity.CRITICAL: "blocker",
            OptimizationSeverity.HIGH: "critical",
            OptimizationSeverity.MEDIUM: "major",
            OptimizationSeverity.LOW: "minor",
            None: "info"
        }

        for check in self.checks:
            if check.status == CheckStatus.PASS:
                continue

            report["issues"].append({
                "description": check.message,
                "severity": severity_map.get(check.severity, "info"),
                "location": {
                    "path": self.dockerfile_path,
                    "lines": {
                        "begin": 1
                    }
                }
            })

        with open('gl-code-quality-report.json', 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(json.dumps(report, indent=2, ensure_ascii=False))
        return exit_code

    def _generate_summary(self) -> str:
        """生成摘要"""
        status = self.get_status()
        status_icon = "✅" if status == CheckStatus.PASS else ("⚠️" if status == CheckStatus.WARN else "❌")

        lines = [
            f"{status_icon} Dockerfile 检查结果: {status.value.upper()}",
            "",
            "| 检查项 | 状态 | 消息 |",
            "|--------|------|------|"
        ]

        for check in self.checks:
            icon = "✅" if check.status == CheckStatus.PASS else ("⚠️" if check.status == CheckStatus.WARN else "❌")
            lines.append(f"| {check.check_name} | {icon} | {check.message} |")

        lines.extend([
            "",
            f"**缓存得分**: {self.analyzer.get_overall_cache_score():.1%}",
            f"**优化建议**: {len(self.optimizer.suggestions)} 条",
        ])

        speedup = self.time_predictor.get_speedup_percentage()
        if speedup > 0:
            lines.append(f"**预计加速**: +{speedup:.1f}%")

        return '\n'.join(lines)

    def print_console_report(self):
        """打印控制台格式报告"""
        status = self.get_status()

        print("\n" + "=" * 80)
        print("🔍 CI 检查报告")
        print("=" * 80)

        status_icon = {
            CheckStatus.PASS: Fore.GREEN + "✅ PASS",
            CheckStatus.WARN: Fore.YELLOW + "⚠️  WARN",
            CheckStatus.FAIL: Fore.RED + "❌ FAIL"
        }[status] + Style.RESET_ALL

        print(f"\n整体状态: {status_icon}")
        print("-" * 80)

        for check in self.checks:
            icon = {
                CheckStatus.PASS: "✅",
                CheckStatus.WARN: "⚠️",
                CheckStatus.FAIL: "❌"
            }[check.status]

            color = {
                CheckStatus.PASS: Fore.GREEN,
                CheckStatus.WARN: Fore.YELLOW,
                CheckStatus.FAIL: Fore.RED
            }[check.status]

            print(f"{icon} {color}{check.check_name:20s}{Style.RESET_ALL} - {check.message}")

        print("\n" + "=" * 80)
        print(self._generate_summary())
        print("=" * 80)

        return 0 if status == CheckStatus.PASS else 1

    def generate_github_workflow(self) -> str:
        """生成GitHub Actions工作流配置"""
        return """name: Dockerfile Analysis

on:
  push:
    paths:
      - '**/Dockerfile*'
  pull_request:
    paths:
      - '**/Dockerfile*'

jobs:
  dockerfile-analysis:
    runs-on: ubuntu-latest
    name: Dockerfile Cache Analysis
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install dockerfile-parse pyyaml tabulate colorama

      - name: Copy analyzer scripts
        run: |
          curl -sSL https://raw.githubusercontent.com/your-repo/tools/main.py -o main.py
          curl -sSL https://raw.githubusercontent.com/your-repo/tools/dockerfile_parser.py -o dockerfile_parser.py
          curl -sSL https://raw.githubusercontent.com/your-repo/tools/cache_analyzer.py -o cache_analyzer.py
          curl -sSL https://raw.githubusercontent.com/your-repo/tools/optimizer.py -o optimizer.py
          curl -sSL https://raw.githubusercontent.com/your-repo/tools/size_analyzer.py -o size_analyzer.py
          curl -sSL https://raw.githubusercontent.com/your-repo/tools/build_time_predictor.py -o build_time_predictor.py
          curl -sSL https://raw.githubusercontent.com/your-repo/tools/ci_checker.py -o ci_checker.py

      - name: Run Dockerfile analysis
        id: analysis
        run: |
          python main.py Dockerfile --ci github
        continue-on-error: true

      - name: Add PR comment
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const results = JSON.parse(process.env.ANALYSIS_RESULTS || '{}')
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: results.summary || 'Dockerfile analysis complete'
            })
"""

    def generate_gitlab_ci_config(self) -> str:
        """生成GitLab CI配置"""
        return """dockerfile_analysis:
  stage: test
  image: python:3.11-slim
  script:
    - pip install dockerfile-parse pyyaml tabulate colorama
    - python main.py Dockerfile --ci gitlab
  artifacts:
    reports:
      codequality: gl-code-quality-report.json
  rules:
    - changes:
        - "**/Dockerfile*"
  allow_failure: true
"""
