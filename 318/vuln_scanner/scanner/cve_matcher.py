"""
CVE 漏洞匹配器
支持从 NVD 和其他数据源获取 CVE 信息
"""
import os
import json
import re
from typing import List, Dict, Any, Optional
import requests

from ..models import Dependency, Vulnerability, SeverityLevel, PackageManager
from .version_utils import is_version_affected, parse_version


class CVEMatcher:
    """CVE 漏洞匹配器"""

    NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    MITRE_URL = "https://cve.mitre.org/cgi-bin/cvename.cgi?name={cve_id}"

    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        self.api_key = api_key
        self.cache_dir = cache_dir or os.path.join(os.path.expanduser("~"), ".vuln_scanner", "cve_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cpe_from_package(self, dependency: Dependency) -> List[str]:
        """从包信息生成可能的 CPE 标识符"""
        cpes = []
        name = dependency.name.lower()

        if dependency.package_manager == PackageManager.PIP:
            cpes.append(f"cpe:2.3:a:python:{name}:*:*:*:*:*:*:*:*")
            cpes.append(f"cpe:2.3:a:{name}_project:{name}:*:*:*:*:*:*:*:*")
        elif dependency.package_manager == PackageManager.NPM:
            cpes.append(f"cpe:2.3:a:{name}_project:{name}:*:*:*:*:*:node.js:*:*")
            cpes.append(f"cpe:2.3:a:npmjs:{name}:*:*:*:*:*:*:*:*")
        elif dependency.package_manager == PackageManager.MAVEN:
            if dependency.group_id:
                vendor = dependency.group_id.lower().split(".")[-1]
                cpes.append(f"cpe:2.3:a:{vendor}:{name}:*:*:*:*:*:*:*:*")
            cpes.append(f"cpe:2.3:a:{name}_project:{name}:*:*:*:*:*:*:*:*")
        elif dependency.package_manager == PackageManager.GO:
            parts = name.split("/")
            if len(parts) >= 2:
                vendor = parts[-2]
                pkg = parts[-1]
                cpes.append(f"cpe:2.3:a:{vendor}:{pkg}:*:*:*:*:*:*:*:*")

        return cpes

    def search_cves_for_package(
        self, dependency: Dependency, timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """搜索指定包的 CVE 漏洞"""
        vulnerabilities = []
        cache_key = f"{dependency.package_manager.value}_{dependency.full_name}_{dependency.version}"
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        try:
            cves = self._search_nvd_api(dependency, timeout)
            vulnerabilities.extend(cves)
        except Exception:
            pass

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(vulnerabilities, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return vulnerabilities

    def _search_nvd_api(
        self, dependency: Dependency, timeout: int
    ) -> List[Dict[str, Any]]:
        """通过 NVD API 搜索 CVE"""
        cves = []
        headers = {}
        params = {}

        if self.api_key:
            headers["apiKey"] = self.api_key

        keywords = [dependency.name]
        if dependency.group_id:
            keywords.append(dependency.group_id)

        for keyword in keywords[:2]:
            params["keywordSearch"] = keyword
            params["resultsPerPage"] = 10

            try:
                response = requests.get(
                    self.NVD_API_URL,
                    headers=headers,
                    params=params,
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()

                for vuln in data.get("vulnerabilities", []):
                    cve_data = vuln.get("cve", {})
                    cve_id = cve_data.get("id", "")
                    descriptions = cve_data.get("descriptions", [])
                    description = ""
                    for desc in descriptions:
                        if desc.get("lang") == "en":
                            description = desc.get("value", "")
                            break

                    metrics = cve_data.get("metrics", {})
                    cvss_score = 0.0
                    cvss_vector = ""
                    severity = SeverityLevel.UNKNOWN

                    for metric_type in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                        if metric_type in metrics:
                            metric = metrics[metric_type][0]
                            cvss_data = metric.get("cvssData", {})
                            cvss_score = cvss_data.get("baseScore", 0.0)
                            cvss_vector = cvss_data.get("vectorString", "")
                            severity_str = metric.get("baseSeverity", "") or cvss_data.get("baseSeverity", "")
                            if severity_str:
                                severity = SeverityLevel(severity_str.upper())
                            else:
                                severity = SeverityLevel.from_cvss(cvss_score)
                            break

                    affected = []
                    for conf in cve_data.get("configurations", []):
                        for node in conf.get("nodes", []):
                            for cpe_match in node.get("cpeMatch", []):
                                if cpe_match.get("vulnerable", False):
                                    version_start = cpe_match.get("versionStartIncluding") or cpe_match.get("versionStartExcluding")
                                    version_end = cpe_match.get("versionEndExcluding") or cpe_match.get("versionEndIncluding")
                                    version = cpe_match.get("version", "*")

                                    if version != "*":
                                        affected.append(version)
                                    elif version_start and version_end:
                                        affected.append(f">={version_start},<{version_end}")
                                    elif version_start:
                                        affected.append(f">={version_start}")
                                    elif version_end:
                                        affected.append(f"<{version_end}")

                    if is_version_affected(dependency.version, affected) or not affected:
                        cves.append({
                            "cve_id": cve_id,
                            "title": description[:100] + "..." if len(description) > 100 else description,
                            "description": description,
                            "severity": severity,
                            "cvss_score": cvss_score,
                            "cvss_vector": cvss_vector,
                            "affected_versions": affected,
                            "references": [
                                ref.get("url", "")
                                for ref in cve_data.get("references", [])
                            ],
                            "publish_date": cve_data.get("published", ""),
                        })

            except Exception as e:
                continue

        return cves

    def get_cve_details(self, cve_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """获取指定 CVE 的详细信息"""
        params = {"cveId": cve_id}
        headers = {}

        if self.api_key:
            headers["apiKey"] = self.api_key

        try:
            response = requests.get(
                self.NVD_API_URL,
                headers=headers,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("vulnerabilities"):
                vuln = data["vulnerabilities"][0].get("cve", {})
                return self._parse_cve_data(vuln)

        except Exception:
            pass

        return None

    def _parse_cve_data(self, cve_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析 CVE 数据"""
        descriptions = cve_data.get("descriptions", [])
        description = ""
        for desc in descriptions:
            if desc.get("lang") == "en":
                description = desc.get("value", "")
                break

        metrics = cve_data.get("metrics", {})
        cvss_score = 0.0
        cvss_vector = ""
        severity = SeverityLevel.UNKNOWN

        for metric_type in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
            if metric_type in metrics:
                metric = metrics[metric_type][0]
                cvss_data = metric.get("cvssData", {})
                cvss_score = cvss_data.get("baseScore", 0.0)
                cvss_vector = cvss_data.get("vectorString", "")
                severity_str = metric.get("baseSeverity", "") or cvss_data.get("baseSeverity", "")
                if severity_str:
                    severity = SeverityLevel(severity_str.upper())
                else:
                    severity = SeverityLevel.from_cvss(cvss_score)
                break

        return {
            "cve_id": cve_data.get("id", ""),
            "title": description[:100] + "..." if len(description) > 100 else description,
            "description": description,
            "severity": severity,
            "cvss_score": cvss_score,
            "cvss_vector": cvss_vector,
            "references": [ref.get("url", "") for ref in cve_data.get("references", [])],
            "publish_date": cve_data.get("published", ""),
        }
