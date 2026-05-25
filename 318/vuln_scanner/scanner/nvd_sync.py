"""
NVD (National Vulnerability Database) 实时同步模块
支持从 NVD API 拉取最新漏洞数据，每小时自动同步更新
"""
import os
import json
import time
import threading
import requests
import tempfile
import gzip
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path

from ..models import SeverityLevel


class NVDSync:
    """NVD 漏洞数据库同步器"""

    NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    CACHE_FILE = "nvd_cache.json.gz"
    META_FILE = "nvd_meta.json"
    DEFAULT_SYNC_INTERVAL = 3600

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[str] = None,
        sync_interval: int = DEFAULT_SYNC_INTERVAL,
        auto_sync: bool = True,
    ):
        self.api_key = api_key
        self.cache_dir = cache_dir or tempfile.gettempdir()
        self.sync_interval = sync_interval
        self.auto_sync = auto_sync

        self.cache_file = os.path.join(self.cache_dir, self.CACHE_FILE)
        self.meta_file = os.path.join(self.cache_dir, self.META_FILE)

        self._db: Dict[str, List[Dict[str, Any]]] = {}
        self._last_sync: Optional[datetime] = None
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._sync_callback: Optional[Callable[[int, int], None]] = None
        self._loaded = False

    def set_sync_callback(self, callback: Callable[[int, int], None]) -> None:
        """设置同步完成回调函数 (new_count, total_count)"""
        self._sync_callback = callback

    def load(self) -> bool:
        """加载本地缓存的 NVD 数据库"""
        if self._loaded:
            return True

        if os.path.exists(self.meta_file):
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    if "last_sync" in meta:
                        self._last_sync = datetime.fromisoformat(meta["last_sync"])
            except Exception:
                pass

        if os.path.exists(self.cache_file):
            try:
                with gzip.open(self.cache_file, "rt", encoding="utf-8") as f:
                    self._db = json.load(f)
                self._loaded = True
                print(f"📦 Loaded NVD cache with {len(self._db)} packages")

                if self.auto_sync and self._should_sync():
                    self._start_background_sync()

                return True
            except Exception as e:
                print(f"⚠️  Failed to load NVD cache: {e}")

        if self.auto_sync:
            self.sync()
            self._start_background_sync()

        return self._loaded

    def _should_sync(self) -> bool:
        """判断是否需要同步"""
        if not self._last_sync:
            return True
        return (datetime.now() - self._last_sync).total_seconds() > self.sync_interval

    def _start_background_sync(self) -> None:
        """启动后台同步线程"""
        if self._sync_thread and self._sync_thread.is_alive():
            return

        self._stop_event.clear()
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        print(f"🔄 NVD background sync started (interval: {self.sync_interval}s)")

    def _sync_loop(self) -> None:
        """同步循环，每小时执行一次"""
        while not self._stop_event.is_set():
            try:
                if self._should_sync():
                    print(f"\n🔄 Starting NVD sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    self.sync()
            except Exception as e:
                print(f"⚠️  NVD sync error: {e}")

            self._stop_event.wait(self.sync_interval)

    def stop(self) -> None:
        """停止后台同步"""
        self._stop_event.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)

    def sync(self, full_sync: bool = False) -> Dict[str, Any]:
        """
        同步 NVD 漏洞数据
        :param full_sync: 是否全量同步，否则增量同步
        :return: 同步结果统计
        """
        print("   ↳ Fetching NVD data...")

        if full_sync or not self._last_sync:
            start_date = datetime.now() - timedelta(days=120)
        else:
            start_date = self._last_sync - timedelta(hours=1)

        results = self._fetch_nvd_data(start_date)
        new_count = self._process_nvd_data(results)

        self._last_sync = datetime.now()
        self._save_cache()
        self._save_meta()

        total_count = sum(len(v) for v in self._db.values())
        print(f"   ↳ Synced {new_count} new vulnerabilities, total: {total_count}")

        if self._sync_callback:
            try:
                self._sync_callback(new_count, total_count)
            except Exception:
                pass

        return {
            "new_vulnerabilities": new_count,
            "total_vulnerabilities": total_count,
            "last_sync": self._last_sync.isoformat(),
            "packages": len(self._db),
        }

    def _fetch_nvd_data(self, start_date: datetime) -> List[Dict[str, Any]]:
        """从 NVD API 拉取漏洞数据"""
        all_cves = []
        start_index = 0
        results_per_page = 2000

        headers = {}
        if self.api_key:
            headers["apiKey"] = self.api_key

        while True:
            params = {
                "pubStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
                "pubEndDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000"),
                "startIndex": start_index,
                "resultsPerPage": results_per_page,
            }

            try:
                response = requests.get(
                    self.NVD_API_BASE,
                    params=params,
                    headers=headers,
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()

                cves = data.get("vulnerabilities", [])
                all_cves.extend(cves)

                if len(cves) < results_per_page:
                    break

                start_index += results_per_page

                if not self.api_key:
                    time.sleep(6)

            except requests.exceptions.RequestException as e:
                print(f"⚠️  NVD API request failed: {e}")
                break

        return all_cves

    def _process_nvd_data(self, cve_items: List[Dict[str, Any]]) -> int:
        """处理 NVD 数据，转换为内部格式"""
        new_count = 0
        existing_cves = self._get_existing_cves()

        for item in cve_items:
            try:
                cve_data = item.get("cve", {})
                cve_id = cve_data.get("id", "")

                if not cve_id or cve_id in existing_cves:
                    continue

                vuln = self._parse_cve(cve_data)
                if not vuln:
                    continue

                affected_packages = self._extract_affected_packages(cve_data)

                for pkg_name in affected_packages:
                    pkg_lower = pkg_name.lower()
                    if pkg_lower not in self._db:
                        self._db[pkg_lower] = []

                    vuln_copy = dict(vuln)
                    vuln_copy["package"] = pkg_name
                    self._db[pkg_lower].append(vuln_copy)

                new_count += 1
                existing_cves.add(cve_id)

            except Exception as e:
                continue

        return new_count

    def _get_existing_cves(self) -> set:
        """获取已存在的 CVE ID 集合"""
        cves = set()
        for vulns in self._db.values():
            for v in vulns:
                if "cve" in v:
                    cves.add(v["cve"])
        return cves

    def _parse_cve(self, cve_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析 CVE 数据"""
        cve_id = cve_data.get("id", "")
        if not cve_id:
            return None

        descriptions = cve_data.get("descriptions", [])
        description = ""
        for desc in descriptions:
            if desc.get("lang") == "en":
                description = desc.get("value", "")
                break

        cvss_score = 0.0
        cvss_vector = ""
        severity = SeverityLevel.UNKNOWN

        metrics = cve_data.get("metrics", {})
        for metric_type in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
            if metric_type in metrics and metrics[metric_type]:
                metric = metrics[metric_type][0]
                cvss_data = metric.get("cvssData", {})
                cvss_score = cvss_data.get("baseScore", 0.0)
                cvss_vector = cvss_data.get("vectorString", "")

                if "baseSeverity" in metric:
                    severity = SeverityLevel(metric["baseSeverity"].upper())
                elif cvss_score > 0:
                    severity = SeverityLevel.from_cvss(cvss_score)
                break

        references = []
        for ref in cve_data.get("references", []):
            if "url" in ref:
                references.append(ref["url"])

        cwe_ids = []
        for weak in cve_data.get("weaknesses", []):
            for desc in weak.get("description", []):
                if desc.get("lang") == "en" and desc.get("value", "").startswith("CWE-"):
                    cwe_ids.append(desc["value"])

        config = cve_data.get("configurations", [])
        affected_versions = self._extract_versions_from_config(config)

        return {
            "cve": cve_id,
            "description": description[:500],
            "cvss": cvss_score,
            "cvss_vector": cvss_vector,
            "severity": severity.value,
            "references": references[:5],
            "cwe_ids": cwe_ids,
            "v": ", ".join(affected_versions) if affected_versions else "",
            "published": cve_data.get("published", ""),
            "lastModified": cve_data.get("lastModified", ""),
        }

    def _extract_affected_packages(self, cve_data: Dict[str, Any]) -> List[str]:
        """从 CVE 数据中提取受影响的包名"""
        packages = []
        config = cve_data.get("configurations", [])

        for conf in config:
            nodes = conf.get("nodes", [])
            for node in nodes:
                cpe_match = node.get("cpeMatch", [])
                for match in cpe_match:
                    cpe_uri = match.get("cpe23Uri", "")
                    if cpe_uri:
                        pkg_name = self._parse_cpe_package(cpe_uri)
                        if pkg_name and pkg_name not in packages:
                            packages.append(pkg_name)

        return packages

    def _parse_cpe_package(self, cpe_uri: str) -> Optional[str]:
        """从 CPE URI 中解析包名"""
        parts = cpe_uri.split(":")
        if len(parts) >= 5:
            vendor = parts[3]
            product = parts[4]

            if vendor and product and product not in ["*", "-"]:
                candidates = [
                    product,
                    f"{vendor}.{product}",
                    f"{vendor}/{product}",
                    f"{vendor}:{product}",
                ]
                return candidates[0]

        return None

    def _extract_versions_from_config(self, config: List[Dict[str, Any]]) -> List[str]:
        """从配置中提取受影响的版本范围"""
        versions = []

        for conf in config:
            nodes = conf.get("nodes", [])
            for node in nodes:
                cpe_match = node.get("cpeMatch", [])
                for match in cpe_match:
                    version_start = match.get("versionStartIncluding", "")
                    version_end = match.get("versionEndExcluding", "")
                    version_end_inc = match.get("versionEndIncluding", "")

                    range_parts = []
                    if version_start:
                        range_parts.append(f">={version_start}")
                    if version_end:
                        range_parts.append(f"<{version_end}")
                    elif version_end_inc:
                        range_parts.append(f"<={version_end_inc}")

                    if range_parts:
                        versions.append(",".join(range_parts))

        return list(set(versions))[:5]

    def _save_cache(self) -> None:
        """保存缓存到磁盘"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with gzip.open(self.cache_file, "wt", encoding="utf-8") as f:
                json.dump(self._db, f, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Failed to save NVD cache: {e}")

    def _save_meta(self) -> None:
        """保存元数据"""
        try:
            meta = {
                "last_sync": self._last_sync.isoformat() if self._last_sync else None,
                "sync_interval": self.sync_interval,
                "packages": len(self._db),
                "total_vulnerabilities": sum(len(v) for v in self._db.values()),
            }
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save NVD meta: {e}")

    def get_vulnerabilities_for_package(self, package_name: str) -> List[Dict[str, Any]]:
        """获取指定包的漏洞列表"""
        if not self._loaded:
            self.load()

        vulnerabilities = []
        name_lower = package_name.lower()

        if name_lower in self._db:
            vulnerabilities.extend(self._db[name_lower])

        base_name = package_name.split("/")[-1].split(":")[-1]
        if base_name.lower() in self._db and base_name.lower() != name_lower:
            for v in self._db[base_name.lower()]:
                if v not in vulnerabilities:
                    vulnerabilities.append(v)

        return vulnerabilities

    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            "loaded": self._loaded,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "packages": len(self._db),
            "total_vulnerabilities": sum(len(v) for v in self._db.values()),
            "sync_interval": self.sync_interval,
            "auto_sync": self.auto_sync,
            "background_sync_running": self._sync_thread is not None and self._sync_thread.is_alive(),
        }
