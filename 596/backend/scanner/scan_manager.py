import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Any
from .config import ScanConfig, ScanResult, Vulnerability, ExploitResult
from .request_engine import RequestEngine
from .vulnerability_detector import VulnerabilityDetector
from .business_logic_detector import BusinessLogicDetector
from .vulnerability_manager import VulnerabilityManager


class ScanManager:
    def __init__(self, config: ScanConfig):
        self.config = config
        self.request_engine = RequestEngine(config)
        self.detector = VulnerabilityDetector(self.request_engine, config)
        self.business_logic_detector = BusinessLogicDetector(self.request_engine, config)
        self.vuln_manager = VulnerabilityManager()
        self.semaphore = asyncio.Semaphore(config.concurrency)
        self.is_scanning = False
        self.scan_id = f"scan_{uuid.uuid4().hex[:12]}"
        self.endpoint_sessions: Dict[str, str] = {}

    async def _scan_endpoint_with_semaphore(self, url: str) -> List[Vulnerability]:
        async with self.semaphore:
            vulns = await self.detector.scan_endpoint(url)
            
            if "business_logic" in self.config.scan_types:
                biz_vulns = await self.business_logic_detector.scan_endpoint(url)
                vulns.extend(biz_vulns)
            
            return vulns

    async def _exploit_vulnerabilities(self, vulns: List[Vulnerability]) -> List[Dict[str, Any]]:
        if not self.config.enable_exploit:
            return []
        
        all_exploited = []
        
        for vuln in vulns:
            try:
                exploited = await self.business_logic_detector.exploit_data_exfiltration(vuln)
                if exploited:
                    exploit_result = ExploitResult(
                        exploit_type=vuln.type,
                        success=True,
                        data_extracted=exploited[:10],
                        evidence=f"成功提取 {len(exploited)} 条敏感数据"
                    )
                    vuln.exploit_result = exploit_result
                    all_exploited.extend(exploited)
            except Exception as e:
                print(f"Exploit failed for {vuln.type}: {e}")
        
        return all_exploited

    async def scan(self, endpoints: List[str]) -> ScanResult:
        self.is_scanning = True
        start_time = datetime.now()
        
        all_vulnerabilities = []
        
        tasks = [self._scan_endpoint_with_semaphore(url) for url in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_vulnerabilities.extend(result)
            elif isinstance(result, Exception):
                print(f"Scan error: {result}")
        
        exploited_data = await self._exploit_vulnerabilities(all_vulnerabilities)
        
        for vuln in all_vulnerabilities:
            self.vuln_manager.add_vulnerability(vuln, self.scan_id)
        
        self.is_scanning = False
        
        total_requests = (self.detector.total_requests + 
                         self.business_logic_detector.total_requests)
        
        role_names = self.request_engine.get_all_role_names()
        
        return ScanResult(
            target_url=self.config.target_url,
            scan_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
            total_requests=total_requests,
            vulnerabilities=all_vulnerabilities,
            scan_status="completed",
            roles_scanned=role_names if role_names else None,
            session_id=self.scan_id,
            exploited_data=exploited_data[:50] if exploited_data else None
        )

    def get_scan_stats(self) -> Dict[str, Any]:
        total_requests = (self.detector.total_requests + 
                         self.business_logic_detector.total_requests)
        
        return {
            "scan_id": self.scan_id,
            "is_scanning": self.is_scanning,
            "total_requests": total_requests,
            "session_stats": self.request_engine.get_session_stats(),
            "roles": self.request_engine.get_all_role_names(),
            "enable_exploit": self.config.enable_exploit,
            "scan_types": self.config.scan_types
        }

    def get_vulnerability_manager(self) -> VulnerabilityManager:
        return self.vuln_manager

    def stop(self):
        self.is_scanning = False
