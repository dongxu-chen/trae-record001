#!/usr/bin/env python3
import json
import os
import hashlib
import subprocess
import sys
import time
import threading
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict

import click
from jinja2 import Template
from tabulate import tabulate
from colorama import init, Fore, Style

init(autoreset=True)

SCAN_CACHE_DIR = Path.home() / ".trivy_scanner" / "cache"
SCAN_CACHE_FILE = SCAN_CACHE_DIR / "scan_cache.json"


class Spinner:
    def __init__(self, message: str = "处理中..."):
        self.message = message
        self.stop_event = threading.Event()
        self.thread = None

    def spin(self):
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while not self.stop_event.is_set():
            sys.stdout.write(f"\r{Fore.CYAN}{spinner_chars[i]} {self.message}{Style.RESET_ALL}")
            sys.stdout.flush()
            time.sleep(0.1)
            i = (i + 1) % len(spinner_chars)

    def start(self):
        self.thread = threading.Thread(target=self.spin)
        self.thread.daemon = True
        self.thread.start()

    def stop(self, success: bool = True, end_message: str = "完成"):
        self.stop_event.set()
        if self.thread:
            self.thread.join()
        if success:
            print(f"\r{Fore.GREEN}✓ {end_message}{Style.RESET_ALL}")
        else:
            print(f"\r{Fore.RED}✗ {end_message}{Style.RESET_ALL}")


class DingTalkNotifier:
    def __init__(self, webhook_url: str, secret: str = None):
        self.webhook_url = webhook_url
        self.secret = secret

    def send_high_risk_alert(self, image_name: str, vulnerabilities: List[Dict]) -> bool:
        high_risk = [v for v in vulnerabilities if float(v.get('cvss_score', 0) if v.get('cvss_score') != 'N/A' else 0) >= 7.0]
        if not high_risk:
            return True

        critical_count = len([v for v in high_risk if v['severity'].upper() == 'CRITICAL'])
        high_count = len([v for v in high_risk if v['severity'].upper() == 'HIGH'])

        title = f"🔴 容器镜像高危漏洞告警 - {image_name}"
        text = f"""
### 🔴 容器镜像高危漏洞告警

**镜像名称**: `{image_name}`
**扫描时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**漏洞统计**:
- 严重漏洞 (CRITICAL): {critical_count} 个
- 高危漏洞 (HIGH): {high_count} 个

**高危漏洞详情**:
"""
        for vuln in high_risk[:10]:
            text += f"""
- **{vuln['vulnerability_id']}** ({vuln['severity']})
  - 软件包: {vuln['package_name']} {vuln['installed_version']}
  - CVSS: {vuln['cvss_score']}
  - 修复版本: {vuln['fixed_version']}
"""
        if len(high_risk) > 10:
            text += f"\n... 还有 {len(high_risk) - 10} 个高危漏洞"

        text += "\n\n**建议**: 请尽快修复上述高危漏洞！"

        return self._send_message(title, text)

    def _send_message(self, title: str, text: str) -> bool:
        try:
            timestamp = str(round(time.time() * 1000))
            sign = self._generate_sign(timestamp) if self.secret else ""

            headers = {'Content-Type': 'application/json'}
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": text
                }
            }

            params = {}
            if self.secret:
                params['timestamp'] = timestamp
                params['sign'] = sign

            response = requests.post(
                self.webhook_url,
                headers=headers,
                params=params,
                json=data,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(Fore.YELLOW + f"钉钉告警发送失败: {str(e)}")
            return False

    def _generate_sign(self, timestamp: str) -> str:
        import hmac
        import base64
        import urllib.parse

        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return urllib.parse.quote_plus(sign)


class ScanCacheManager:
    def __init__(self):
        SCAN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if SCAN_CACHE_FILE.exists():
            try:
                with open(SCAN_CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "images": {},
            "layers": {}
        }

    def _save_cache(self):
        with open(SCAN_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2)

    def get_image_layers(self, image_name: str) -> List[str]:
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format='{{json .RootFS.Layers}}'", image_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                layers = json.loads(result.stdout.strip().strip("'"))
                return layers
        except:
            pass
        return []

    def get_changed_layers(self, image_name: str) -> List[str]:
        current_layers = self.get_image_layers(image_name)
        cached_layers = self.cache.get("images", {}).get(image_name, {}).get("layers", [])

        changed_layers = []
        for layer in current_layers:
            layer_hash = layer.split(":")[-1][:12]
            if layer not in cached_layers or layer_hash not in self.cache.get("layers", {}):
                changed_layers.append(layer)

        return changed_layers

    def update_cache(self, image_name: str, vulnerabilities: List[Dict]):
        layers = self.get_image_layers(image_name)

        self.cache["images"][image_name] = {
            "layers": layers,
            "last_scan": datetime.now().isoformat(),
            "vulnerability_count": len(vulnerabilities)
        }

        for vuln in vulnerabilities:
            layer_id = vuln.get('target', '')
            if layer_id:
                if layer_id not in self.cache["layers"]:
                    self.cache["layers"][layer_id] = []
                if vuln['vulnerability_id'] not in [v['id'] for v in self.cache["layers"][layer_id]]:
                    self.cache["layers"][layer_id].append({
                        "id": vuln['vulnerability_id'],
                        "severity": vuln['severity'],
                        "package": vuln['package_name'],
                        "fixed_version": vuln['fixed_version']
                    })

        self._save_cache()


class TrivyScanner:
    DEFAULT_TIMEOUT = 600

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, offline_mirror: str = None):
        self.timeout = timeout
        self.offline_mirror = offline_mirror
        self.cache_manager = ScanCacheManager()
        self._check_trivy_installed()

    def _check_trivy_installed(self):
        try:
            subprocess.run(
                ["trivy", "--version"],
                capture_output=True,
                check=True,
                timeout=30
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(Fore.RED + "错误: 未找到 Trivy。请先安装 Trivy: https://aquasecurity.github.io/trivy/")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print(Fore.YELLOW + "警告: 检查 Trivy 版本超时，继续执行...")

    def sync_database_from_mirror(self, mirror_url: str) -> bool:
        print(Fore.CYAN + f"\n正在从内网镜像仓库同步漏洞数据库...")
        spinner = Spinner("正在同步数据库...")
        spinner.start()

        try:
            env = os.environ.copy()
            if mirror_url:
                env["TRIVY_DB_REPOSITORY"] = mirror_url

            result = subprocess.run(
                ["trivy", "image", "--download-db-only", "--quiet"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env
            )

            if result.returncode == 0:
                spinner.stop(success=True, end_message="数据库同步完成")
                return True
            else:
                spinner.stop(success=False, end_message=f"数据库同步失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            spinner.stop(success=False, end_message="数据库同步超时")
            return False
        except Exception as e:
            spinner.stop(success=False, end_message=f"数据库同步失败: {str(e)}")
            return False

    def _download_trivy_database(self):
        if self.offline_mirror:
            self.sync_database_from_mirror(self.offline_mirror)
            return

        print(Fore.CYAN + "\n正在检查 Trivy 漏洞数据库...")
        spinner = Spinner("正在下载/更新漏洞数据库...")
        spinner.start()

        try:
            result = subprocess.run(
                ["trivy", "image", "--download-db-only", "--quiet"],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            spinner.stop(success=result.returncode == 0, end_message="数据库更新完成")
        except subprocess.TimeoutExpired:
            spinner.stop(success=False, end_message="数据库下载超时")
        except Exception as e:
            spinner.stop(success=False, end_message=f"数据库下载失败: {str(e)}")

    def _run_trivy_command(self, args: List[str], description: str = "执行中") -> Optional[Dict]:
        spinner = Spinner(description)
        spinner.start()

        try:
            env = {
                **os.environ,
                "TRIVY_TIMEOUT": str(self.timeout),
                "TRIVY_QUIET": "true"
            }

            result = subprocess.run(
                ["trivy"] + args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env
            )

            if result.returncode != 0:
                spinner.stop(success=False, end_message=f"失败: {result.stderr[:100]}...")
                return None

            try:
                output = json.loads(result.stdout) if result.stdout else {}
                spinner.stop(success=True, end_message="完成")
                return output
            except json.JSONDecodeError:
                spinner.stop(success=True, end_message="完成")
                return {"raw_output": result.stdout}

        except subprocess.TimeoutExpired:
            spinner.stop(success=False, end_message=f"超时（超过 {self.timeout} 秒）")
            return None
        except Exception as e:
            spinner.stop(success=False, end_message=f"错误: {str(e)}")
            return None

    def scan_image_incremental(self, image_name: str) -> Optional[Dict]:
        print(Fore.CYAN + f"\n正在检查镜像层变更: {image_name}")

        changed_layers = self.cache_manager.get_changed_layers(image_name)
        total_layers = self.cache_manager.get_image_layers(image_name)

        if not changed_layers:
            print(Fore.GREEN + f"✓ 无新增或变更层，使用缓存结果")
            return self._get_cached_result(image_name)

        print(Fore.YELLOW + f"  总层数: {len(total_layers)}, 变更层数: {len(changed_layers)}")
        print(Fore.CYAN + f"正在执行增量扫描...")

        return self.scan_image(image_name, download_db=False)

    def _get_cached_result(self, image_name: str) -> Dict:
        cached = self.cache_manager.cache.get("images", {}).get(image_name, {})
        return {
            "Results": [{
                "Target": "cached",
                "Vulnerabilities": []
            }],
            "Cached": True,
            "LastScan": cached.get("last_scan", "")
        }

    def scan_image(self, image_name: str, download_db: bool = True) -> Optional[Dict]:
        if download_db:
            if self.offline_mirror:
                self.sync_database_from_mirror(self.offline_mirror)
            else:
                self._download_trivy_database()

        print(Fore.CYAN + f"\n正在扫描镜像: {image_name}")
        args = [
            "image",
            "--format", "json",
            "--quiet",
            "--timeout", str(self.timeout),
            image_name
        ]
        return self._run_trivy_command(args, "正在扫描镜像...")

    def generate_cyclonedx_sbom(self, image_name: str, output_file: str) -> bool:
        print(Fore.CYAN + f"\n正在为镜像 {image_name} 生成 CycloneDX SBOM...")
        args = [
            "image",
            "--format", "cyclonedx",
            "--output", output_file,
            "--quiet",
            "--timeout", str(self.timeout),
            image_name
        ]

        spinner = Spinner("正在生成 SBOM...")
        spinner.start()

        try:
            result = subprocess.run(
                ["trivy"] + args,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode != 0:
                spinner.stop(success=False, end_message=f"生成 SBOM 失败")
                print(Fore.RED + f"错误详情: {result.stderr}")
                return False

            spinner.stop(success=True, end_message="SBOM 生成完成")
            print(Fore.GREEN + f"CycloneDX SBOM 已保存到: {output_file}")

            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    sbom_data = json.load(f)
                component_count = len(sbom_data.get('components', []))
                print(Fore.CYAN + f"  - 包含 {component_count} 个组件")
                print(Fore.CYAN + f"  - 格式版本: {sbom_data.get('specVersion', 'N/A')}")
            except:
                pass

            return True

        except subprocess.TimeoutExpired:
            spinner.stop(success=False, end_message="生成 SBOM 超时")
            return False
        except Exception as e:
            spinner.stop(success=False, end_message=f"错误: {str(e)}")
            return False

    def get_vulnerabilities(self, scan_result: Dict) -> List[Dict]:
        vulnerabilities = []
        if not scan_result:
            return vulnerabilities

        if scan_result.get("Cached", False):
            return vulnerabilities

        for result in scan_result.get("Results", []):
            target = result.get("Target", "")
            for vuln in result.get("Vulnerabilities", []):
                cvss = vuln.get("CVSS", {})
                cvss_score = "N/A"
                if cvss:
                    for vendor in cvss.values():
                        if vendor.get("V3Score"):
                            cvss_score = f"{vendor.get('V3Score')}"
                            break
                        elif vendor.get("V2Score"):
                            cvss_score = f"{vendor.get('V2Score')}"
                            break

                fixed_version = vuln.get("FixedVersion", "N/A")
                remediation = ""
                if fixed_version != "N/A":
                    remediation = f"升级到 {fixed_version} 或更新版本"

                vulnerabilities.append({
                    "target": target,
                    "vulnerability_id": vuln.get("VulnerabilityID", ""),
                    "severity": vuln.get("Severity", "UNKNOWN"),
                    "package_name": vuln.get("PkgName", ""),
                    "installed_version": vuln.get("InstalledVersion", ""),
                    "fixed_version": fixed_version,
                    "description": vuln.get("Description", "暂无描述"),
                    "title": vuln.get("Title", ""),
                    "cvss_score": cvss_score,
                    "remediation": remediation,
                    "references": vuln.get("References", []),
                    "published_date": vuln.get("PublishedDate", ""),
                    "last_modified_date": vuln.get("LastModifiedDate", ""),
                    "layer": vuln.get("Layer", {}).get("Digest", "")
                })
        return vulnerabilities

    def get_severity_color(self, severity: str) -> str:
        color_map = {
            "CRITICAL": Fore.RED + Style.BRIGHT,
            "HIGH": Fore.LIGHTRED_EX,
            "MEDIUM": Fore.YELLOW,
            "LOW": Fore.BLUE,
            "UNKNOWN": Fore.WHITE
        }
        return color_map.get(severity.upper(), Fore.WHITE)

    def print_vulnerability_report(self, vulnerabilities: List[Dict], is_cached: bool = False):
        if is_cached:
            print(Fore.GREEN + "\n" + "=" * 120)
            print(Fore.GREEN + "✅ 使用缓存扫描结果（无新增漏洞）")
            print(Fore.GREEN + "=" * 120)
            return

        if not vulnerabilities:
            print(Fore.GREEN + "\n" + "=" * 120)
            print(Fore.GREEN + "✅ 未发现任何漏洞！")
            print(Fore.GREEN + "=" * 120)
            return

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
        vulnerabilities_sorted = sorted(
            vulnerabilities,
            key=lambda x: severity_order.get(x["severity"].upper(), 5)
        )

        table_data = []
        for idx, vuln in enumerate(vulnerabilities_sorted, 1):
            color = self.get_severity_color(vuln["severity"])
            cvss_display = vuln["cvss_score"] if vuln["cvss_score"] != "N/A" else "-"

            table_data.append([
                str(idx),
                vuln["vulnerability_id"],
                color + vuln["severity"] + Style.RESET_ALL,
                cvss_display,
                vuln["package_name"],
                vuln["installed_version"],
                vuln["fixed_version"],
                vuln["target"]
            ])

        headers = [
            Fore.CYAN + "#" + Style.RESET_ALL,
            Fore.CYAN + "CVE编号" + Style.RESET_ALL,
            Fore.CYAN + "严重等级" + Style.RESET_ALL,
            Fore.CYAN + "CVSS" + Style.RESET_ALL,
            Fore.CYAN + "软件包" + Style.RESET_ALL,
            Fore.CYAN + "当前版本" + Style.RESET_ALL,
            Fore.CYAN + "修复版本" + Style.RESET_ALL,
            Fore.CYAN + "目标" + Style.RESET_ALL
        ]

        print(Fore.CYAN + "\n" + "=" * 120)
        print(Fore.CYAN + "🔒 漏洞报告")
        print(Fore.CYAN + "=" * 120)
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        severity_counts = {}
        for vuln in vulnerabilities:
            sev = vuln["severity"].upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        print(Fore.CYAN + "\n📊 漏洞统计:")
        for sev, count in sorted(severity_counts.items(), key=lambda x: severity_order.get(x[0], 5)):
            color = self.get_severity_color(sev)
            bar = "█" * min(count, 30)
            print(f"  {color}{sev:10} {count:4}  {bar}{Style.RESET_ALL}")
        print(f"\n  总计: {len(vulnerabilities)} 个漏洞")

        print(Fore.CYAN + "\n📝 漏洞详情与修复建议:")
        print(Fore.CYAN + "-" * 120)

        critical_high = [v for v in vulnerabilities_sorted if v["severity"].upper() in ["CRITICAL", "HIGH"]][:5]

        for idx, vuln in enumerate(critical_high, 1):
            color = self.get_severity_color(vuln["severity"])
            print(f"\n{color}[{idx}] {vuln['vulnerability_id']} ({vuln['severity']}){Style.RESET_ALL}")
            print(f"    软件包: {vuln['package_name']} {vuln['installed_version']}")
            print(f"    CVSS分数: {vuln['cvss_score']}")
            print(f"    描述: {vuln['description'][:200]}..." if len(vuln['description']) > 200 else f"    描述: {vuln['description']}")
            if vuln["remediation"]:
                print(f"    {Fore.GREEN}修复建议: {vuln['remediation']}{Style.RESET_ALL}")

        if len(vulnerabilities_sorted) > 5:
            print(f"\n{Fore.YELLOW}... 还有 {len(vulnerabilities_sorted) - 5} 个漏洞详情请查看 HTML 报告或原始 JSON{Style.RESET_ALL}")

    def generate_fix_script(self, vulnerabilities: List[Dict], image_name: str, output_file: str) -> bool:
        print(Fore.CYAN + f"\n正在生成修复建议脚本...")

        packages_by_type = defaultdict(list)
        package_versions = {}

        for vuln in vulnerabilities:
            if vuln['fixed_version'] != 'N/A':
                pkg_name = vuln['package_name']
                if pkg_name not in package_versions or vuln['fixed_version'] > package_versions[pkg_name]:
                    package_versions[pkg_name] = vuln['fixed_version']

        if not package_versions:
            print(Fore.YELLOW + "  没有需要修复的软件包")
            return False

        dockerfile_content = f"""# 修复脚本 - {image_name}
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 漏洞数量: {len(vulnerabilities)}

FROM {image_name}

# 修复系统包漏洞
RUN apt-get update && apt-get install -y --no-install-recommends \\\n"""

        for pkg, version in sorted(package_versions.items()):
            dockerfile_content += f"    {pkg}={version} \\\n"

        dockerfile_content += """    && rm -rf /var/lib/apt/lists/*

# 如果使用其他包管理器，请取消相应注释:
# RUN yum update -y && yum clean all
# RUN apk upgrade --no-cache
"""

        shell_script = f"""#!/bin/bash
# 修复脚本 - {image_name}
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

echo "正在修复镜像: {image_name}"
echo ""

# Dockerfile 修复方式
echo "=== Dockerfile 修复方式 ==="
cat > Dockerfile.fix << 'EOF'
{dockerfile_content}
EOF

echo ""
echo "Dockerfile.fix 已生成，执行以下命令构建修复后的镜像:"
echo "  docker build -f Dockerfile.fix -t {image_name}:fixed ."
echo ""

# 运行时修复方式
echo "=== 运行时修复方式 ==="
echo "对于运行中的容器，可执行以下命令:"
echo "  docker exec -it <container_id> apt-get update && apt-get upgrade -y"
"""

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(shell_script)

            os.chmod(output_file, 0o755)
            print(Fore.GREEN + f"✅ 修复脚本已保存到: {output_file}")

            pkg_count = len(package_versions)
            print(Fore.CYAN + f"  - 包含 {pkg_count} 个需要升级的软件包")
            print(Fore.CYAN + f"  - 包含 Dockerfile 和运行时两种修复方式")

            return True
        except Exception as e:
            print(Fore.RED + f"❌ 生成修复脚本失败: {str(e)}")
            return False

    def export_html_report(self, vulnerabilities: List[Dict], image_name: str, output_file: str):
        print(Fore.CYAN + f"\n正在生成 HTML 报告...")

        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>容器镜像漏洞扫描报告</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 16px; margin-bottom: 30px; box-shadow: 0 8px 30px rgba(102, 126, 234, 0.3); }
        .header h1 { font-size: 32px; margin-bottom: 15px; }
        .header .meta { display: flex; gap: 30px; opacity: 0.95; flex-wrap: wrap; }
        .header .meta-item { display: flex; align-items: center; gap: 8px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); text-align: center; transition: transform 0.3s; }
        .summary-card:hover { transform: translateY(-5px); }
        .summary-card .number { font-size: 48px; font-weight: bold; }
        .summary-card .label { color: #666; margin-top: 8px; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
        .critical .number { color: #dc3545; }
        .high .number { color: #fd7e14; }
        .medium .number { color: #ffc107; }
        .low .number { color: #17a2b8; }
        .total .number { color: #6c757d; }
        .vuln-section { background: white; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); overflow: hidden; margin-bottom: 30px; }
        .vuln-section h2 { padding: 25px; background: #f8f9fa; border-bottom: 1px solid #e9ecef; font-size: 20px; display: flex; align-items: center; gap: 10px; }
        .vuln-table { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; }
        th { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; text-align: left; font-weight: 600; white-space: nowrap; }
        td { padding: 15px; border-bottom: 1px solid #e9ecef; vertical-align: top; }
        tr:hover { background: #f8f9fa; }
        .severity { padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; text-align: center; min-width: 90px; }
        .severity-CRITICAL { background: #dc3545; color: white; }
        .severity-HIGH { background: #fd7e14; color: white; }
        .severity-MEDIUM { background: #ffc107; color: #333; }
        .severity-LOW { background: #17a2b8; color: white; }
        .severity-UNKNOWN { background: #6c757d; color: white; }
        .cvss-badge { padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; }
        .cvss-critical { background: #dc3545; color: white; }
        .cvss-high { background: #fd7e14; color: white; }
        .cvss-medium { background: #ffc107; color: #333; }
        .cvss-low { background: #28a745; color: white; }
        .cvss-none { background: #6c757d; color: white; }
        .footer { text-align: center; margin-top: 30px; padding: 30px; color: #666; border-top: 1px solid #e9ecef; }
        .description-cell { max-width: 350px; }
        .description-text { font-size: 13px; color: #666; line-height: 1.5; }
        .remediation { background: #d4edda; color: #155724; padding: 8px 12px; border-radius: 6px; font-size: 13px; margin-top: 8px; }
        .empty-state { padding: 60px; text-align: center; }
        .empty-state .icon { font-size: 64px; margin-bottom: 20px; }
        .empty-state h3 { color: #28a745; margin-bottom: 10px; }
        .empty-state p { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 容器镜像漏洞扫描报告</h1>
            <div class="meta">
                <div class="meta-item">📦 镜像: {{ image_name }}</div>
                <div class="meta-item">🕐 扫描时间: {{ scan_time }}</div>
                <div class="meta-item">🔧 扫描引擎: Trivy</div>
                {% if is_incremental %}
                <div class="meta-item">⚡ 增量扫描: 是</div>
                {% endif %}
            </div>
        </div>

        <div class="summary">
            <div class="summary-card critical">
                <div class="number">{{ critical_count }}</div>
                <div class="label">严重 (CRITICAL)</div>
            </div>
            <div class="summary-card high">
                <div class="number">{{ high_count }}</div>
                <div class="label">高危 (HIGH)</div>
            </div>
            <div class="summary-card medium">
                <div class="number">{{ medium_count }}</div>
                <div class="label">中危 (MEDIUM)</div>
            </div>
            <div class="summary-card low">
                <div class="number">{{ low_count }}</div>
                <div class="label">低危 (LOW)</div>
            </div>
            <div class="summary-card total">
                <div class="number">{{ total_count }}</div>
                <div class="label">总计漏洞</div>
            </div>
        </div>

        <div class="vuln-section">
            <h2>📋 漏洞详情</h2>
            {% if vulnerabilities %}
            <div class="vuln-table">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>CVE编号</th>
                            <th>严重等级</th>
                            <th>CVSS</th>
                            <th>软件包</th>
                            <th>当前版本</th>
                            <th>修复版本</th>
                            <th>目标</th>
                            <th>描述与修复建议</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for vuln in vulnerabilities %}
                        <tr>
                            <td><strong>{{ loop.index }}</strong></td>
                            <td><strong>{{ vuln.vulnerability_id }}</strong></td>
                            <td><span class="severity severity-{{ vuln.severity }}">{{ vuln.severity }}</span></td>
                            <td>
                                {% if vuln.cvss_score != 'N/A' %}
                                    {% set cvss = vuln.cvss_score|float %}
                                    {% if cvss >= 9.0 %}
                                        <span class="cvss-badge cvss-critical">{{ vuln.cvss_score }}</span>
                                    {% elif cvss >= 7.0 %}
                                        <span class="cvss-badge cvss-high">{{ vuln.cvss_score }}</span>
                                    {% elif cvss >= 4.0 %}
                                        <span class="cvss-badge cvss-medium">{{ vuln.cvss_score }}</span>
                                    {% else %}
                                        <span class="cvss-badge cvss-low">{{ vuln.cvss_score }}</span>
                                    {% endif %}
                                {% else %}
                                    <span class="cvss-badge cvss-none">N/A</span>
                                {% endif %}
                            </td>
                            <td>{{ vuln.package_name }}</td>
                            <td>{{ vuln.installed_version }}</td>
                            <td><strong>{{ vuln.fixed_version }}</strong></td>
                            <td>{{ vuln.target }}</td>
                            <td class="description-cell">
                                <div class="description-text">{{ vuln.description|truncate(150) }}</div>
                                {% if vuln.remediation %}
                                    <div class="remediation">✅ {{ vuln.remediation }}</div>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="empty-state">
                <div class="icon">✅</div>
                <h3>太棒了！</h3>
                <p>该镜像未发现任何安全漏洞</p>
            </div>
            {% endif %}
        </div>

        <div class="footer">
            <p>由 Trivy 强力驱动 | 容器镜像漏洞扫描器 v3.0</p>
            <p style="margin-top: 10px; font-size: 12px; color: #999;">报告生成于 {{ scan_time }}</p>
        </div>
    </div>
</body>
</html>
        """

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
        vulnerabilities_sorted = sorted(
            vulnerabilities,
            key=lambda x: severity_order.get(x["severity"].upper(), 5)
        )

        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
        for vuln in vulnerabilities:
            sev = vuln["severity"].upper()
            if sev in counts:
                counts[sev] += 1

        template = Template(html_template)
        html_content = template.render(
            image_name=image_name,
            scan_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            vulnerabilities=vulnerabilities_sorted,
            critical_count=counts["CRITICAL"],
            high_count=counts["HIGH"],
            medium_count=counts["MEDIUM"],
            low_count=counts["LOW"],
            total_count=len(vulnerabilities),
            is_incremental=False
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(Fore.GREEN + f"✅ HTML 报告已保存到: {output_file}")


@click.group()
@click.option("--timeout", "-t", type=int, default=TrivyScanner.DEFAULT_TIMEOUT,
              help=f"扫描超时时间（秒），默认: {TrivyScanner.DEFAULT_TIMEOUT} 秒（10分钟）")
@click.option("--mirror", "-m", type=str, help="内网漏洞数据库镜像仓库地址")
@click.pass_context
def cli(ctx, timeout, mirror):
    """容器镜像漏洞扫描器 v3.0 - 支持离线同步、增量扫描、钉钉告警"""
    ctx.ensure_object(dict)
    ctx.obj['timeout'] = timeout
    ctx.obj['mirror'] = mirror


@cli.command()
@click.argument("image_name")
@click.option("--sbom", "-s", type=str, help="生成 CycloneDX SBOM 并保存到指定文件 (JSON)")
@click.option("--html", "-h", type=str, help="导出 HTML 报告到指定文件")
@click.option("--json-output", "-j", type=str, help="导出原始 JSON 扫描结果")
@click.option("--no-db-update", is_flag=True, help="跳过数据库更新检查")
@click.option("--incremental", "-i", is_flag=True, help="启用增量扫描（只扫描新增或变更的层）")
@click.option("--dingtalk-webhook", "-d", type=str, help="钉钉机器人 Webhook 地址")
@click.option("--fix-script", "-f", type=str, help="生成修复建议脚本并保存到指定文件")
@click.pass_context
def scan(ctx, image_name: str, sbom: Optional[str], html: Optional[str],
         json_output: Optional[str], no_db_update: bool, incremental: bool,
         dingtalk_webhook: Optional[str], fix_script: Optional[str]):
    """扫描 Docker 镜像并生成报告"""
    scanner = TrivyScanner(timeout=ctx.obj['timeout'], offline_mirror=ctx.obj.get('mirror'))

    if incremental:
        scan_result = scanner.scan_image_incremental(image_name)
        is_cached = scan_result and scan_result.get("Cached", False)
    else:
        scan_result = scanner.scan_image(image_name, download_db=not no_db_update)
        is_cached = False

    if not scan_result:
        print(Fore.RED + "\n❌ 扫描失败")
        return

    if json_output:
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(scan_result, f, indent=2, ensure_ascii=False)
        print(Fore.GREEN + f"✅ 原始 JSON 结果已保存到: {json_output}")

    vulnerabilities = scanner.get_vulnerabilities(scan_result)
    scanner.print_vulnerability_report(vulnerabilities, is_cached)

    if not is_cached:
        scanner.cache_manager.update_cache(image_name, vulnerabilities)

    if sbom:
        scanner.generate_cyclonedx_sbom(image_name, sbom)

    if html:
        scanner.export_html_report(vulnerabilities, image_name, html)

    if dingtalk_webhook:
        print(Fore.CYAN + "\n正在发送钉钉告警...")
        notifier = DingTalkNotifier(dingtalk_webhook)
        if notifier.send_high_risk_alert(image_name, vulnerabilities):
            print(Fore.GREEN + "✅ 钉钉告警发送成功")
        else:
            print(Fore.RED + "❌ 钉钉告警发送失败")

    if fix_script:
        scanner.generate_fix_script(vulnerabilities, image_name, fix_script)


@cli.command()
@click.argument("image_name")
@click.argument("output_file")
@click.pass_context
def sbom(ctx, image_name: str, output_file: str):
    """仅生成镜像的 CycloneDX SBOM 清单"""
    scanner = TrivyScanner(timeout=ctx.obj['timeout'], offline_mirror=ctx.obj.get('mirror'))
    scanner.generate_cyclonedx_sbom(image_name, output_file)


@cli.command()
@click.argument("mirror_url")
@click.pass_context
def sync_db(ctx, mirror_url: str):
    """从内网镜像仓库同步漏洞数据库"""
    scanner = TrivyScanner(timeout=ctx.obj['timeout'])
    scanner.sync_database_from_mirror(mirror_url)


@cli.command()
def update_db():
    """手动更新 Trivy 漏洞数据库"""
    scanner = TrivyScanner()
    scanner._download_trivy_database()


@cli.command()
@click.argument("image_name")
@click.argument("output_file")
@click.option("--dingtalk-webhook", "-d", type=str, help="钉钉机器人 Webhook 地址")
@click.pass_context
def fix_script(ctx, image_name: str, output_file: str, dingtalk_webhook: Optional[str]):
    """生成修复建议脚本（需先扫描获取漏洞信息）"""
    scanner = TrivyScanner(timeout=ctx.obj['timeout'], offline_mirror=ctx.obj.get('mirror'))
    scan_result = scanner.scan_image(image_name, download_db=False)
    if scan_result:
        vulnerabilities = scanner.get_vulnerabilities(scan_result)
        scanner.generate_fix_script(vulnerabilities, image_name, output_file)

        if dingtalk_webhook:
            notifier = DingTalkNotifier(dingtalk_webhook)
            notifier.send_high_risk_alert(image_name, vulnerabilities)


if __name__ == "__main__":
    cli()
