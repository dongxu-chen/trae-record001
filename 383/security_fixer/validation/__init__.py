"""修复验证模块 - 修复后自动运行单元测试"""

import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TestResult:
    """测试结果"""
    test_command: str
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0


@dataclass
class ValidationResult:
    """验证结果"""
    file_path: str
    before_fix: Optional[TestResult] = None
    after_fix: Optional[TestResult] = None
    validation_passed: bool = False
    break_detected: bool = False
    error: str = ""


class FixValidator:
    """修复验证器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()

    def detect_test_framework(self) -> Optional[str]:
        """检测项目使用的测试框架"""
        if (self.project_root / "pytest.ini").exists() or (self.project_root / "pyproject.toml").exists():
            content = ""
            pyproject = self.project_root / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text(encoding="utf-8", errors="replace")
            if "pytest" in content or (self.project_root / "pytest.ini").exists():
                return "pytest"

        if (self.project_root / "package.json").exists():
            try:
                pkg = json.loads((self.project_root / "package.json").read_text(encoding="utf-8", errors="replace"))
                scripts = pkg.get("scripts", {})
                if "test" in scripts:
                    return "npm"
            except:
                pass

        if (self.project_root / "pom.xml").exists():
            return "maven"

        if (self.project_root / "build.gradle").exists() or (self.project_root / "build.gradle.kts").exists():
            return "gradle"

        if any(self.project_root.rglob("*test*")):
            return "python"

        return None

    def run_tests(self, test_framework: str = None) -> TestResult:
        """运行测试"""
        if test_framework is None:
            test_framework = self.detect_test_framework()

        commands = {
            "pytest": ["python", "-m", "pytest", "-v", "--tb=short"],
            "npm": ["npm", "test"],
            "maven": ["mvn", "test"],
            "gradle": ["./gradlew", "test"],
            "python": ["python", "-m", "unittest", "discover"],
        }

        cmd = commands.get(test_framework, ["python", "-m", "unittest", "discover"])

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300
            )
            duration = time.time() - start_time

            tests_run, tests_passed, tests_failed = self._parse_test_output(result.stdout, test_framework)

            return TestResult(
                test_command=" ".join(cmd),
                passed=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                test_command=" ".join(cmd),
                passed=False,
                exit_code=-1,
                stdout="",
                stderr="Test execution timed out",
                duration=300
            )
        except Exception as e:
            return TestResult(
                test_command=" ".join(cmd),
                passed=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration=time.time() - start_time
            )

    def _parse_test_output(self, output: str, framework: str) -> tuple:
        """解析测试输出"""
        tests_run = 0
        tests_passed = 0
        tests_failed = 0

        if framework == "pytest":
            run_match = re.search(r'(\d+)\s+passed', output)
            fail_match = re.search(r'(\d+)\s+failed', output)
            if run_match:
                tests_run = int(run_match.group(1))
                tests_passed = tests_run
            if fail_match:
                tests_failed = int(fail_match.group(1))
                tests_run += tests_failed

        elif framework == "npm":
            pass_match = re.search(r'(\d+)\s+passing', output)
            fail_match = re.search(r'(\d+)\s+failing', output)
            if pass_match:
                tests_passed = int(pass_match.group(1))
                tests_run += tests_passed
            if fail_match:
                tests_failed = int(fail_match.group(1))
                tests_run += tests_failed

        elif framework in ("maven", "gradle"):
            run_match = re.search(r'Tests run:\s*(\d+)', output)
            fail_match = re.search(r'Failures:\s*(\d+)', output)
            err_match = re.search(r'Errors:\s*(\d+)', output)
            if run_match:
                tests_run = int(run_match.group(1))
            if fail_match:
                tests_failed += int(fail_match.group(1))
            if err_match:
                tests_failed += int(err_match.group(1))
            tests_passed = tests_run - tests_failed

        return tests_run, tests_passed, tests_failed

    def validate_fix(self, file_path: str, run_before: bool = True) -> ValidationResult:
        """验证修复结果"""
        result = ValidationResult(file_path=file_path)

        if run_before:
            result.before_fix = self.run_tests()

        result.after_fix = self.run_tests()

        if result.before_fix and result.after_fix:
            if result.before_fix.passed and not result.after_fix.passed:
                result.break_detected = True
                result.validation_passed = False
                result.error = "修复后测试失败，可能引入了回归问题"
            elif result.after_fix.tests_failed > result.before_fix.tests_failed:
                result.break_detected = True
                result.validation_passed = False
                result.error = f"修复后失败测试增加: {result.before_fix.tests_failed} -> {result.after_fix.tests_failed}"
            else:
                result.validation_passed = True
        elif result.after_fix:
            result.validation_passed = result.after_fix.passed
            if not result.after_fix.passed:
                result.error = "修复后测试未通过"

        return result


import json
import re
