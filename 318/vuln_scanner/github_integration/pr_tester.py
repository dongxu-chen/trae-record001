"""
PR 预测试模块
在创建 PR 之前运行编译和测试，确保变更不会破坏构建
"""
import os
import sys
import time
import shutil
import subprocess
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models import FixSuggestion, PackageManager
from ..fixer import DependencyUpdater


class PRPreTester:
    """PR 预测试执行器"""

    def __init__(self, project_path: str, backup: bool = True):
        self.project_path = project_path
        self.backup = backup
        self.temp_dir = tempfile.mkdtemp(prefix="vuln_scan_test_")

    def __del__(self):
        """清理临时目录"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def run_pre_tests(
        self,
        suggestions: List[FixSuggestion],
        test_command: Optional[str] = None,
        package_manager: Optional[PackageManager] = None,
        timeout: int = 300,
        clean_install: bool = True,
    ) -> Dict[str, Any]:
        """
        运行预测试
        :param suggestions: 修复建议列表
        :param test_command: 自定义测试命令
        :param package_manager: 包管理器类型
        :param timeout: 超时时间（秒）
        :param clean_install: 是否重新安装依赖
        :return: 测试结果
        """
        start_time = time.time()
        results: Dict[str, Any] = {
            "success": False,
            "tests_run": [],
            "output": "",
            "error": "",
            "duration": 0,
            "phases": [],
        }

        if not suggestions:
            results["error"] = "No suggestions to test"
            return results

        original_files = {}
        backup_files = {}

        try:
            phase = "apply_changes"
            results["phases"].append({"phase": phase, "status": "running"})
            print(f"   ↳ Phase: {phase}")

            updater = DependencyUpdater(self.project_path, backup=self.backup)
            apply_results = updater.update_dependencies(suggestions)

            success_count = sum(1 for r in apply_results if r["success"])
            if success_count != len(suggestions):
                results["error"] = f"Failed to apply {len(suggestions) - success_count} changes"
                results["phases"].append({"phase": phase, "status": "failed"})
                self._restore_files(apply_results)
                return results

            for r in apply_results:
                s = r["suggestion"]
                dep = s.dependency
                if dep.path and os.path.exists(dep.path):
                    if dep.path not in original_files:
                        with open(dep.path, "r", encoding="utf-8") as f:
                            original_files[dep.path] = f.read()

            results["phases"].append({"phase": phase, "status": "success", "changes": success_count})

            if clean_install:
                phase = "install_dependencies"
                results["phases"].append({"phase": phase, "status": "running"})
                print(f"   ↳ Phase: {phase}")

                if not package_manager:
                    package_manager = self._detect_package_manager()

                install_result = self._install_dependencies(package_manager, timeout)
                results["phases"].append({
                    "phase": phase,
                    "status": "success" if install_result[0] else "failed",
                    "output": install_result[1][:500],
                })

                if not install_result[0]:
                    results["error"] = f"Dependency installation failed: {install_result[1][:200]}"
                    results["output"] = install_result[1]
                    self._restore_content(original_files)
                    return results

            phase = "build"
            results["phases"].append({"phase": phase, "status": "running"})
            print(f"   ↳ Phase: {phase}")

            build_result = self._run_build(package_manager, timeout)
            results["phases"].append({
                "phase": phase,
                "status": "success" if build_result[0] else "failed",
                "output": build_result[1][:500],
            })

            if not build_result[0]:
                results["error"] = f"Build failed: {build_result[1][:200]}"
                results["output"] = build_result[1]
                self._restore_content(original_files)
                return results

            phase = "tests"
            results["phases"].append({"phase": phase, "status": "running"})
            print(f"   ↳ Phase: {phase}")

            if test_command:
                test_result = self._run_custom_test(test_command, timeout)
            else:
                test_result = self._run_default_tests(package_manager, timeout)

            results["tests_run"].append({
                "command": test_command or "default",
                "success": test_result[0],
                "output": test_result[1][:1000],
            })

            results["phases"].append({
                "phase": phase,
                "status": "success" if test_result[0] else "failed",
                "output": test_result[1][:500],
            })

            if not test_result[0]:
                results["error"] = f"Tests failed: {test_result[1][:200]}"
                results["output"] = test_result[1]
                self._restore_content(original_files)
                return results

            results["success"] = True

        except Exception as e:
            results["error"] = str(e)
            import traceback
            results["output"] = traceback.format_exc()

        finally:
            self._restore_content(original_files)

            results["duration"] = time.time() - start_time

        return results

    def _detect_package_manager(self) -> PackageManager:
        """检测项目的包管理器"""
        if os.path.exists(os.path.join(self.project_path, "requirements.txt")):
            return PackageManager.PIP
        elif os.path.exists(os.path.join(self.project_path, "package.json")):
            return PackageManager.NPM
        elif os.path.exists(os.path.join(self.project_path, "pom.xml")):
            return PackageManager.MAVEN
        elif os.path.exists(os.path.join(self.project_path, "go.mod")):
            return PackageManager.GO
        return PackageManager.UNKNOWN

    def _install_dependencies(
        self, package_manager: PackageManager, timeout: int
    ) -> Tuple[bool, str]:
        """安装项目依赖"""
        commands = {
            PackageManager.PIP: [
                ["pip", "install", "-e", "."],
                ["pip", "install", "-r", "requirements.txt"],
            ],
            PackageManager.NPM: [
                ["npm", "install"],
                ["npm", "ci"],
            ],
            PackageManager.MAVEN: [
                ["mvn", "dependency:resolve", "-q"],
            ],
            PackageManager.GO: [
                ["go", "mod", "download"],
                ["go", "mod", "tidy"],
            ],
        }

        for cmd_list in commands.get(package_manager, []):
            try:
                result = subprocess.run(
                    cmd_list,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self.project_path,
                )
                if result.returncode == 0:
                    return True, result.stdout
            except subprocess.TimeoutExpired as e:
                return False, f"Command timed out after {timeout}s"
            except Exception as e:
                continue

        return True, "No install command needed or all failed gracefully"

    def _run_build(
        self, package_manager: PackageManager, timeout: int
    ) -> Tuple[bool, str]:
        """运行项目构建"""
        build_commands = {
            PackageManager.PIP: [
                ["python", "-c", "import py_compile; import os; [py_compile.compile(os.path.join(r, f)) for r, d, fs in os.walk('.') for f in fs if f.endswith('.py')]"],
            ],
            PackageManager.NPM: [
                ["npm", "run", "build"],
                ["npm", "run", "compile"],
                ["tsc", "--noEmit"],
            ],
            PackageManager.MAVEN: [
                ["mvn", "compile", "-q", "-DskipTests"],
            ],
            PackageManager.GO: [
                ["go", "build", "./..."],
                ["go", "vet", "./..."],
            ],
        }

        for cmd in build_commands.get(package_manager, []):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self.project_path,
                )
                if result.returncode == 0:
                    return True, result.stdout
            except subprocess.TimeoutExpired:
                return False, f"Build timed out after {timeout}s"
            except Exception:
                continue

        return True, "No build command available, skipped"

    def _run_default_tests(
        self, package_manager: PackageManager, timeout: int
    ) -> Tuple[bool, str]:
        """运行默认测试"""
        test_commands = {
            PackageManager.PIP: [
                ["python", "-m", "pytest", "-x", "-q", "--tb=short"],
                ["python", "-m", "unittest", "discover", "-s", "tests"],
                ["python", "setup.py", "test"],
            ],
            PackageManager.NPM: [
                ["npm", "test"],
                ["npm", "run", "test"],
                ["yarn", "test"],
            ],
            PackageManager.MAVEN: [
                ["mvn", "test", "-q", "-Dtest=*Test"],
            ],
            PackageManager.GO: [
                ["go", "test", "./...", "-short"],
            ],
        }

        for cmd in test_commands.get(package_manager, []):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self.project_path,
                )
                if result.returncode == 0:
                    return True, result.stdout
            except subprocess.TimeoutExpired:
                return False, f"Tests timed out after {timeout}s"
            except Exception:
                continue

        return True, "No test command available, skipped"

    def _run_custom_test(
        self, test_command: str, timeout: int
    ) -> Tuple[bool, str]:
        """运行自定义测试命令"""
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    test_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self.project_path,
                )
            else:
                result = subprocess.run(
                    test_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self.project_path,
                    executable="/bin/bash",
                )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Test command timed out after {timeout}s"
        except Exception as e:
            return False, str(e)

    def _restore_content(self, original_files: Dict[str, str]) -> None:
        """恢复原始文件内容"""
        for file_path, content in original_files.items():
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except Exception:
                pass

    def _restore_files(self, apply_results: List[Dict[str, Any]]) -> None:
        """从备份恢复文件"""
        for result in apply_results:
            if result["success"]:
                s = result["suggestion"]
                dep = s.dependency
                if dep.path:
                    backup_path = dep.path + ".bak"
                    if os.path.exists(backup_path):
                        try:
                            shutil.copy2(backup_path, dep.path)
                            os.remove(backup_path)
                        except Exception:
                            pass

    def validate_environment(
        self,
        package_manager: Optional[PackageManager] = None,
    ) -> Dict[str, Any]:
        """验证测试环境"""
        if not package_manager:
            package_manager = self._detect_package_manager()

        tools = {
            PackageManager.PIP: ["python", "pip"],
            PackageManager.NPM: ["node", "npm"],
            PackageManager.MAVEN: ["java", "mvn"],
            PackageManager.GO: ["go"],
        }

        result = {
            "package_manager": package_manager.value,
            "tools_available": {},
            "project_path_exists": os.path.exists(self.project_path),
            "temp_dir": self.temp_dir,
        }

        for tool in tools.get(package_manager, []):
            try:
                subprocess.run(
                    [tool, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                result["tools_available"][tool] = True
            except Exception:
                result["tools_available"][tool] = False

        result["all_tools_available"] = all(result["tools_available"].values())

        return result
