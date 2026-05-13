#!/usr/bin/env python3
"""
Docker 镜像漏洞扫描器 - 集成 Trivy
"""
import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Vulnerability:
    """漏洞信息"""
    id: str
    severity: str
    package_name: str
    installed_version: str
    fixed_version: str
    title: str
    description: str
    url: str


@dataclass
class ScanResult:
    """扫描结果"""
    image_name: str
    success: bool = False
    total_vulns: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    unknown: int = 0
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    raw_output: str = ""


class TrivyScanner:
    """Trivy 漏洞扫描器"""

    SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    SEVERITY_COLORS = {
        "CRITICAL": "\033[91m",
        "HIGH": "\033[93m",
        "MEDIUM": "\033[94m",
        "LOW": "\033[92m",
        "UNKNOWN": "\033[90m",
    }
    COLOR_RESET = "\033[0m"

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化扫描器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.scan_config = self.config.get("scan", {})
        self.trivy_path = self.scan_config.get("trivy_path", "trivy")
        self.use_docker = self.scan_config.get("use_docker", False)
        self.offline_scan = self.scan_config.get("offline", False)
        self.ignore_unfixed = self.scan_config.get("ignore_unfixed", False)
        self.ignore_file = self.scan_config.get("ignore_file", ".trivyignore")

        self._trivy_available = None

    def _run_command(self, args: List[str], capture: bool = True) -> tuple[bool, str, str]:
        """
        运行命令

        Args:
            args: 命令参数列表
            capture: 是否捕获输出

        Returns:
            (是否成功, stdout, stderr)
        """
        try:
            if capture:
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    shell=False,
                )
                return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
            else:
                result = subprocess.run(
                    args,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    shell=False,
                )
                return result.returncode == 0, "", ""
        except FileNotFoundError:
            return False, "", f"命令未找到: {args[0]}"
        except Exception as e:
            return False, "", str(e)

    def check_trivy_available(self, force_check: bool = False) -> bool:
        """
        检查 Trivy 是否可用

        Args:
            force_check: 强制重新检查

        Returns:
            是否可用
        """
        if self._trivy_available is not None and not force_check:
            return self._trivy_available

        if self.use_docker:
            success, _, _ = self._run_command(["docker", "info"], capture=True)
            if success:
                self._trivy_available = True
                return True
        else:
            success, stdout, _ = self._run_command([self.trivy_path, "--version"], capture=True)
            if success:
                print(f"检测到 Trivy: {stdout}")
                self._trivy_available = True
                return True

        print("错误: Trivy 不可用")
        print("请安装 Trivy: https://aquasecurity.github.io/trivy/")
        print("或设置 'scan.use_docker: true' 使用 Docker 运行")
        self._trivy_available = False
        return False

    def _build_trivy_command(
        self,
        image_name: str,
        scan_types: List[str] = None,
        severity: List[str] = None,
        output_format: str = "table",
        output_file: Optional[str] = None,
        exit_code: Optional[int] = None,
    ) -> List[str]:
        """
        构建 Trivy 命令

        Args:
            image_name: 镜像名称
            scan_types: 扫描类型 (vuln, config, secret)
            severity: 严重级别列表
            output_format: 输出格式 (table, json, sarif)
            output_file: 输出文件路径
            exit_code: 发现漏洞时的退出码

        Returns:
            命令参数列表
        """
        scan_types = scan_types or ["vuln", "config"]
        severity = severity or ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

        if self.use_docker:
            cmd = [
                "docker", "run", "--rm",
                "-v", "/var/run/docker.sock:/var/run/docker.sock",
                "-v", f"{Path.cwd()}:/root/.cache/",
                "aquasec/trivy:latest",
            ]
        else:
            cmd = [self.trivy_path]

        cmd.extend(["image", "--scanners", ",".join(scan_types)])
        cmd.extend(["--severity", ",".join(severity)])

        if self.ignore_unfixed:
            cmd.append("--ignore-unfixed")

        if self.ignore_file and Path(self.ignore_file).exists():
            cmd.extend(["--ignorefile", self.ignore_file])

        if self.offline_scan:
            cmd.append("--offline-scan")

        cmd.extend(["--format", output_format])

        if output_file:
            cmd.extend(["--output", output_file])

        if exit_code is not None:
            cmd.extend(["--exit-code", str(exit_code)])

        cmd.append(image_name)

        return cmd

    def scan(
        self,
        image_name: str,
        scan_types: List[str] = None,
        severity: List[str] = None,
        fail_on_severity: Optional[str] = None,
        output_format: str = "table",
        output_file: Optional[str] = None,
        show_output: bool = True,
    ) -> ScanResult:
        """
        扫描镜像

        Args:
            image_name: 镜像名称
            scan_types: 扫描类型
            severity: 要显示的严重级别
            fail_on_severity: 发现此级别及以上漏洞时失败
            output_format: 输出格式
            output_file: 输出文件
            show_output: 是否显示输出

        Returns:
            扫描结果
        """
        result = ScanResult(image_name=image_name)

        if not self.check_trivy_available():
            return result

        print(f"\n{'='*60}")
        print(f"开始扫描镜像: {image_name}")
        print(f"{'='*60}\n")

        exit_code = None
        if fail_on_severity:
            exit_code = 1

        cmd = self._build_trivy_command(
            image_name=image_name,
            scan_types=scan_types,
            severity=severity,
            output_format="json" if output_format == "json" else output_format,
            output_file=output_file,
            exit_code=exit_code,
        )

        print(f"执行扫描命令: {' '.join(cmd)}")

        if output_format == "json":
            success, stdout, stderr = self._run_command(cmd, capture=True)
            result.raw_output = stdout
            if success and stdout:
                result.success = True
                self._parse_json_result(result, stdout)
            else:
                print(f"扫描失败: {stderr}")
        else:
            success, stdout, stderr = self._run_command(cmd, capture=not show_output)
            if success:
                result.success = True
                if not show_output:
                    print(stdout)
            else:
                print(f"扫描失败: {stderr}")

        self._print_summary(result)

        if fail_on_severity and self._should_fail(result, fail_on_severity):
            result.success = False

        return result

    def _parse_json_result(self, result: ScanResult, json_output: str) -> None:
        """
        解析 JSON 格式的扫描结果

        Args:
            result: 结果对象
            json_output: JSON 输出
        """
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError:
            return

        for result_entry in data.get("Results", []):
            for vuln in result_entry.get("Vulnerabilities", []):
                vulnerability = Vulnerability(
                    id=vuln.get("VulnerabilityID", ""),
                    severity=vuln.get("Severity", "UNKNOWN"),
                    package_name=vuln.get("PkgName", ""),
                    installed_version=vuln.get("InstalledVersion", ""),
                    fixed_version=vuln.get("FixedVersion", ""),
                    title=vuln.get("Title", ""),
                    description=vuln.get("Description", "")[:200],
                    url=vuln.get("PrimaryURL", ""),
                )
                result.vulnerabilities.append(vulnerability)

                severity = vulnerability.severity.upper()
                if severity == "CRITICAL":
                    result.critical += 1
                elif severity == "HIGH":
                    result.high += 1
                elif severity == "MEDIUM":
                    result.medium += 1
                elif severity == "LOW":
                    result.low += 1
                else:
                    result.unknown += 1

        result.total_vulns = len(result.vulnerabilities)

    def _should_fail(self, result: ScanResult, fail_on_severity: str) -> bool:
        """
        判断是否应该失败

        Args:
            result: 扫描结果
            fail_on_severity: 失败级别

        Returns:
            是否应该失败
        """
        fail_on = fail_on_severity.upper()
        if fail_on == "CRITICAL":
            return result.critical > 0
        elif fail_on == "HIGH":
            return result.critical > 0 or result.high > 0
        elif fail_on == "MEDIUM":
            return result.critical > 0 or result.high > 0 or result.medium > 0
        elif fail_on == "LOW":
            return result.total_vulns > 0
        return False

    def _print_summary(self, result: ScanResult) -> None:
        """
        打印扫描摘要

        Args:
            result: 扫描结果
        """
        if not result.vulnerabilities:
            return

        print(f"\n{'='*60}")
        print(f"扫描摘要: {result.image_name}")
        print(f"{'='*60}")

        print(f"{'严重级别':<12} {'数量':<8}")
        print("-" * 20)
        for sev in self.SEVERITY_ORDER:
            count = getattr(result, sev.lower(), 0)
            color = self.SEVERITY_COLORS.get(sev, "")
            print(f"{color}{sev:<12} {count:<8}{self.COLOR_RESET}")
        print("-" * 20)
        print(f"{'总计':<12} {result.total_vulns:<8}")

        if result.vulnerabilities:
            print(f"\n漏洞详情 (前 20 个):")
            print("-" * 80)
            for vuln in result.vulnerabilities[:20]:
                color = self.SEVERITY_COLORS.get(vuln.severity.upper(), "")
                print(f"{color}[{vuln.severity:^10}]{self.COLOR_RESET} {vuln.id:<20} {vuln.package_name}")
                if vuln.fixed_version:
                    print(f"           修复版本: {vuln.fixed_version}")

            if len(result.vulnerabilities) > 20:
                print(f"\n... 还有 {len(result.vulnerabilities) - 20} 个漏洞未显示")

    def scan_and_save_report(
        self,
        image_name: str,
        output_dir: str = "scan-reports",
        formats: List[str] = None,
        **kwargs,
    ) -> Dict[str, str]:
        """
        扫描并保存多格式报告

        Args:
            image_name: 镜像名称
            output_dir: 输出目录
            formats: 输出格式列表
            **kwargs: 其他扫描参数

        Returns:
            格式到文件路径的映射
        """
        formats = formats or ["json", "sarif", "table"]
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        report_files = {}
        image_safe = image_name.replace("/", "_").replace(":", "_")

        for fmt in formats:
            output_file = f"{output_dir}/{image_safe}-report.{fmt}"
            self.scan(
                image_name=image_name,
                output_format=fmt,
                output_file=output_file,
                show_output=(fmt == "table"),
                **kwargs,
            )
            report_files[fmt] = output_file

        return report_files


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Docker 镜像漏洞扫描工具（集成 Trivy）")

    parser.add_argument(
        "-c",
        "--config",
        default="build_config.json",
        help="配置文件路径",
    )

    parser.add_argument(
        "-n",
        "--name",
        required=True,
        help="镜像名称",
    )

    parser.add_argument(
        "-t",
        "--tag",
        default="latest",
        help="镜像标签",
    )

    parser.add_argument(
        "--scanners",
        nargs="*",
        choices=["vuln", "config", "secret", "misconfig", "rbac"],
        default=["vuln"],
        help="扫描类型",
    )

    parser.add_argument(
        "--severity",
        nargs="*",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"],
        default=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        help="要检查的严重级别",
    )

    parser.add_argument(
        "--fail-on",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        help="发现此级别及以上漏洞时退出码为 1",
    )

    parser.add_argument(
        "--ignore-unfixed",
        action="store_true",
        help="忽略未修复的漏洞",
    )

    parser.add_argument(
        "--format",
        choices=["table", "json", "sarif"],
        default="table",
        help="输出格式",
    )

    parser.add_argument(
        "--output",
        help="输出文件路径",
    )

    parser.add_argument(
        "--output-dir",
        default="scan-reports",
        help="多格式报告输出目录",
    )

    parser.add_argument(
        "--save-reports",
        action="store_true",
        help="保存多格式报告",
    )

    parser.add_argument(
        "--use-docker",
        action="store_true",
        help="使用 Docker 运行 Trivy",
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    config = {}
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    if args.use_docker:
        if "scan" not in config:
            config["scan"] = {}
        config["scan"]["use_docker"] = True

    scanner = TrivyScanner(config)

    image_full = f"{args.name}:{args.tag}"

    if args.save_reports:
        reports = scanner.scan_and_save_report(
            image_name=image_full,
            output_dir=args.output_dir,
            scan_types=args.scanners,
            severity=args.severity,
            fail_on_severity=args.fail_on,
        )
        print(f"\n报告已保存:")
        for fmt, path in reports.items():
            print(f"  {fmt}: {path}")
        return 0
    else:
        result = scanner.scan(
            image_name=image_full,
            scan_types=args.scanners,
            severity=args.severity,
            fail_on_severity=args.fail_on,
            output_format=args.format,
            output_file=args.output,
        )

        if args.fail_on and not result.success:
            return 1

        return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
