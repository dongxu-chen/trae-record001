import re
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from config import DEFAULT_CONFIG


@dataclass
class ResponseFingerprint:
    content_hash: str
    content_length: int
    status_code: Optional[int]
    content_type: str
    structure_signature: str


@dataclass
class Anomaly:
    type: str
    severity: str
    description: str
    evidence: str
    test_param: Optional[str] = None
    test_value: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'severity': self.severity,
            'description': self.description,
            'evidence': self.evidence,
            'test_param': self.test_param,
            'test_value': self.test_value
        }


class ResponseBodyAnalyzer:
    def __init__(self):
        self.error_field_patterns = [
            'error', 'errors', 'err', 'err_msg', 'error_msg', 'message',
            'msg', 'detail', 'details', 'reason', 'code', 'error_code',
            'status', 'success', 'ok', 'failed', 'is_success',
            'exception', 'trace', 'stack'
        ]
        
        self.error_value_indicators = [
            False, 0, -1, 'false', 'error', 'fail', 'failed',
            'err', 'exception', 'invalid'
        ]
        
        self.success_value_indicators = [
            True, 1, 200, 'true', 'success', 'ok', 'yes'
        ]
    
    def extract_error_fields(self, body: Any) -> List[Dict[str, Any]]:
        errors = []
        
        if isinstance(body, dict):
            self._search_error_fields(body, [], errors)
        elif isinstance(body, list):
            for i, item in enumerate(body):
                if isinstance(item, dict):
                    self._search_error_fields(item, [str(i)], errors)
        
        return errors
    
    def _search_error_fields(self, obj: Dict[str, Any], path: List[str], 
                             errors: List[Dict[str, Any]]) -> None:
        for key, value in obj.items():
            key_lower = key.lower()
            
            if any(err_field in key_lower for err_field in self.error_field_patterns):
                if self._is_error_indicator(value):
                    errors.append({
                        'path': '.'.join(path + [key]),
                        'key': key,
                        'value': value,
                        'type': 'error_field'
                    })
            
            if isinstance(value, dict):
                self._search_error_fields(value, path + [key], errors)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._search_error_fields(item, path + [key, str(i)], errors)
    
    def _is_error_indicator(self, value: Any) -> bool:
        if value is None:
            return False
        
        if isinstance(value, bool):
            return value is False
        
        if isinstance(value, (int, float)):
            return value < 0 or value >= 400
        
        if isinstance(value, str):
            val_lower = value.lower()
            return any(err in val_lower for err in [
                'error', 'fail', 'invalid', 'exception', 'denied',
                'unauthorized', 'forbidden', 'not found', 'bad request',
                'server error', 'internal', 'timeout'
            ])
        
        return False
    
    def check_response_structure(self, body: Any, baseline: Optional[Any] = None) -> Dict[str, Any]:
        result = {
            'type': type(body).__name__,
            'keys': [],
            'depth': 0,
            'structure_changed': False,
            'missing_keys': [],
            'new_keys': []
        }
        
        if isinstance(body, dict):
            result['keys'] = list(body.keys())
            result['depth'] = self._calculate_depth(body)
            
            if baseline and isinstance(baseline, dict):
                baseline_keys = set(baseline.keys())
                body_keys = set(body.keys())
                result['missing_keys'] = list(baseline_keys - body_keys)
                result['new_keys'] = list(body_keys - baseline_keys)
                result['structure_changed'] = bool(result['missing_keys'] or result['new_keys'])
        
        return result
    
    def _calculate_depth(self, obj: Any, current_depth: int = 0) -> int:
        if not isinstance(obj, (dict, list)):
            return current_depth
        
        max_depth = current_depth
        
        if isinstance(obj, dict):
            for value in obj.values():
                depth = self._calculate_depth(value, current_depth + 1)
                max_depth = max(max_depth, depth)
        elif isinstance(obj, list):
            for item in obj:
                depth = self._calculate_depth(item, current_depth + 1)
                max_depth = max(max_depth, depth)
        
        return max_depth
    
    def calculate_fingerprint(self, response_data: Dict[str, Any]) -> ResponseFingerprint:
        body = response_data.get('response_body', '')
        body_str = str(body)
        
        content_hash = hashlib.md5(body_str.encode('utf-8')).hexdigest()
        
        structure_sig = ''
        if isinstance(body, dict):
            structure_sig = self._generate_structure_signature(body)
        elif isinstance(body, list):
            structure_sig = f"list[{len(body)}]"
        
        return ResponseFingerprint(
            content_hash=content_hash,
            content_length=len(body_str),
            status_code=response_data.get('status_code'),
            content_type=response_data.get('response_headers', {}).get('Content-Type', ''),
            structure_signature=structure_sig
        )
    
    def _generate_structure_signature(self, obj: Dict[str, Any]) -> str:
        keys = sorted(obj.keys())
        sig_parts = []
        
        for key in keys:
            value = obj[key]
            if isinstance(value, dict):
                sig_parts.append(f"{key}:{{{self._generate_structure_signature(value)}}}")
            elif isinstance(value, list):
                sig_parts.append(f"{key}:[{len(value)}]")
            else:
                sig_parts.append(f"{key}:{type(value).__name__}")
        
        return ','.join(sig_parts)
    
    def detect_business_logic_errors(self, body: Any, status_code: Optional[int] = None) -> List[Dict[str, Any]]:
        errors = []
        
        if status_code and 200 <= status_code < 300:
            if isinstance(body, dict):
                error_fields = self.extract_error_fields(body)
                for err in error_fields:
                    errors.append({
                        'type': 'business_error_despite_200',
                        'description': f"HTTP 200 but contains error field: {err['path']}",
                        'evidence': f"{err['key']} = {err['value']}"
                    })
                
                for key in body:
                    key_lower = key.lower()
                    if 'success' in key_lower or 'ok' in key_lower:
                        value = body[key]
                        if isinstance(value, bool) and not value:
                            errors.append({
                                'type': 'success_flag_false',
                                'description': f"Success flag is false despite HTTP 200",
                                'evidence': f"{key} = {value}"
                            })
                        elif isinstance(value, str) and value.lower() in self.error_value_indicators:
                            errors.append({
                                'type': 'success_flag_error',
                                'description': f"Success flag indicates error",
                                'evidence': f"{key} = {value}"
                            })
        
        return errors


class AnomalyDetector:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**DEFAULT_CONFIG.get('anomaly_detection', {}), **(config or {})}
        self.body_analyzer = ResponseBodyAnalyzer()
        
        self.sql_error_patterns = [
            re.compile(r'syntax error.*sql', re.IGNORECASE),
            re.compile(r'mysql.*error', re.IGNORECASE),
            re.compile(r'ORA-\d+', re.IGNORECASE),
            re.compile(r'PostgreSQL.*error', re.IGNORECASE),
            re.compile(r'unclosed quotation mark', re.IGNORECASE),
            re.compile(r'SQLServer', re.IGNORECASE),
            re.compile(r'Incorrect syntax near', re.IGNORECASE),
            re.compile(r'you have an error in your SQL syntax', re.IGNORECASE),
            re.compile(r'unknown column', re.IGNORECASE),
            re.compile(r'table.*doesn\'t exist', re.IGNORECASE),
            re.compile(r'constraint.*violation', re.IGNORECASE),
            re.compile(r'integrity constraint', re.IGNORECASE),
            re.compile(r'duplicate entry', re.IGNORECASE),
            re.compile(r'data too long', re.IGNORECASE),
            re.compile(r'invalid.*number', re.IGNORECASE)
        ]
        
        self.nosql_error_patterns = [
            re.compile(r'MongoDB', re.IGNORECASE),
            re.compile(r'mongo.*error', re.IGNORECASE),
            re.compile(r'$cmd.*failed', re.IGNORECASE),
            re.compile(r'could not be cast to', re.IGNORECASE)
        ]
        
        self.error_keywords = self.config.get('error_keywords', [
            'error', 'exception', 'traceback', 'fatal', 'warning',
            'undefined', 'null', 'none', 'invalid', 'fail'
        ])
        
        self.server_info_patterns = [
            re.compile(r'X-Powered-By:.*', re.IGNORECASE),
            re.compile(r'Server:.*', re.IGNORECASE),
            re.compile(r'X-AspNet-Version:.*', re.IGNORECASE)
        ]
        
        self.template_injection_patterns = [
            re.compile(r'jinja2', re.IGNORECASE),
            re.compile(r'TemplateAssertionError', re.IGNORECASE),
            re.compile(r'freemarker', re.IGNORECASE),
            re.compile(r'thymeleaf', re.IGNORECASE),
            re.compile(r'{{.*}}'),
            re.compile(r'{%.*%}')
        ]
        
        self.language_specific_errors = {
            'python': [
                re.compile(r'Traceback.*\n.*File.*line.*in', re.DOTALL),
                re.compile(r'NameError:'),
                re.compile(r'TypeError:'),
                re.compile(r'ValueError:'),
                re.compile(r'KeyError:'),
                re.compile(r'IndexError:'),
                re.compile(r'AttributeError:'),
                re.compile(r'ZeroDivisionError:')
            ],
            'java': [
                re.compile(r'java\.\w+\.Exception'),
                re.compile(r'NullPointerException'),
                re.compile(r'ArrayIndexOutOfBoundsException'),
                re.compile(r'StringIndexOutOfBoundsException'),
                re.compile(r'ClassCastException'),
                re.compile(r'IllegalArgumentException')
            ],
            'php': [
                re.compile(r'Fatal error:'),
                re.compile(r'Warning:'),
                re.compile(r'Notice:'),
                re.compile(r'PHP Parse error:'),
                re.compile(r'Undefined variable:'),
                re.compile(r'Undefined index:')
            ],
            'nodejs': [
                re.compile(r'ReferenceError:'),
                re.compile(r'TypeError:'),
                re.compile(r'SyntaxError:'),
                re.compile(r'at\s+\w+\s+\(.*:\d+:\d+\)'),
                re.compile(r'Error: ENOENT')
            ],
            'dotnet': [
                re.compile(r'System\.\w+Exception'),
                re.compile(r'NullReferenceException'),
                re.compile(r'IndexOutOfRangeException'),
                re.compile(r'ArgumentException'),
                re.compile(r'InvalidOperationException')
            ]
        }
    
    def detect(
        self,
        response_data: Dict[str, Any],
        baseline_data: Optional[Dict[str, Any]] = None,
        test_param: Optional[str] = None,
        test_value: Optional[Any] = None
    ) -> List[Anomaly]:
        anomalies = []
        
        if self.config.get('check_status_code', True):
            anomalies.extend(self._check_status_code(response_data, test_param, test_value))
        
        if self.config.get('check_response_time', True):
            anomalies.extend(self._check_response_time(response_data, baseline_data, test_param, test_value))
        
        if self.config.get('check_error_messages', True):
            anomalies.extend(self._check_error_messages(response_data, test_param, test_value))
        
        if self.config.get('check_sql_errors', True):
            anomalies.extend(self._check_sql_errors(response_data, test_param, test_value))
            anomalies.extend(self._check_nosql_errors(response_data, test_param, test_value))
        
        if self.config.get('check_xss_reflection', True):
            anomalies.extend(self._check_xss_reflection(response_data, test_param, test_value))
        
        anomalies.extend(self._check_server_info_leak(response_data, test_param, test_value))
        anomalies.extend(self._check_content_smuggling(response_data, test_param, test_value))
        anomalies.extend(self._check_language_specific_errors(response_data, test_param, test_value))
        anomalies.extend(self._check_template_injection(response_data, test_param, test_value))
        anomalies.extend(self._check_response_body_deep(response_data, baseline_data, test_param, test_value))
        anomalies.extend(self._check_content_consistency(response_data, baseline_data, test_param, test_value))
        anomalies.extend(self._check_nonstandard_status(response_data, test_param, test_value))
        
        return anomalies
    
    def _check_status_code(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        status_code = response_data.get('status_code')
        error_type = response_data.get('error_type')
        
        if error_type:
            severity = 'high' if error_type in ('timeout', 'connection_error') else 'medium'
            anomalies.append(Anomaly(
                type='request_error',
                severity=severity,
                description=f'Request failed with error type: {error_type}',
                evidence=response_data.get('error', 'Unknown error'),
                test_param=test_param,
                test_value=test_value
            ))
            return anomalies
        
        if status_code is None:
            return anomalies
        
        if status_code >= 500:
            anomalies.append(Anomaly(
                type='server_error',
                severity='high',
                description=f'Server returned 5xx status code: {status_code}',
                evidence=f'Status code {status_code} indicates server-side error',
                test_param=test_param,
                test_value=test_value
            ))
        
        if status_code == 401 or status_code == 403:
            anomalies.append(Anomaly(
                type='auth_issue',
                severity='medium',
                description=f'Access issue with status code: {status_code}',
                evidence=f'Status code {status_code} may indicate authorization bypass',
                test_param=test_param,
                test_value=test_value
            ))
        
        return anomalies
    
    def _check_response_time(
        self,
        response_data: Dict[str, Any],
        baseline_data: Optional[Dict[str, Any]],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        response_time = response_data.get('response_time', 0)
        max_time = self.config.get('max_response_time', 5000)
        
        if response_time > max_time:
            anomalies.append(Anomaly(
                type='slow_response',
                severity='medium',
                description=f'Response time exceeded threshold: {response_time:.0f}ms > {max_time}ms',
                evidence=f'Response took {response_time:.0f}ms',
                test_param=test_param,
                test_value=test_value
            ))
        
        if baseline_data and 'response_time' in baseline_data:
            baseline_time = baseline_data['response_time']
            if baseline_time > 0:
                ratio = response_time / baseline_time
                if ratio > 5 and response_time > 1000:
                    anomalies.append(Anomaly(
                        type='time_based_anomaly',
                        severity='high',
                        description=f'Response time significantly slower than baseline: {ratio:.1f}x slower',
                        evidence=f'Baseline: {baseline_time:.0f}ms, Test: {response_time:.0f}ms',
                        test_param=test_param,
                        test_value=test_value
                    ))
        
        return anomalies
    
    def _check_error_messages(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        body = response_data.get('response_body', '')
        
        if not body:
            return anomalies
        
        body_str = str(body).lower()
        
        for keyword in self.error_keywords:
            if keyword.lower() in body_str:
                anomalies.append(Anomaly(
                    type='error_message',
                    severity='medium',
                    description=f'Error keyword detected in response: {keyword}',
                    evidence=f'Response contains: {keyword}',
                    test_param=test_param,
                    test_value=test_value
                ))
                break
        
        stack_trace_patterns = [
            re.compile(r'Traceback.*\n.*File.*line.*in', re.DOTALL),
            re.compile(r'at.*\(.*:\d+\)', re.IGNORECASE),
            re.compile(r'\.java:\d+'),
            re.compile(r'\.py:\d+')
        ]
        
        for pattern in stack_trace_patterns:
            if pattern.search(str(body)):
                anomalies.append(Anomaly(
                    type='stack_trace_leak',
                    severity='high',
                    description='Stack trace detected in response',
                    evidence='Response contains stack trace information',
                    test_param=test_param,
                    test_value=test_value
                ))
                break
        
        return anomalies
    
    def _check_sql_errors(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        body = response_data.get('response_body', '')
        
        if not body:
            return anomalies
        
        body_str = str(body)
        
        for pattern in self.sql_error_patterns:
            match = pattern.search(body_str)
            if match:
                anomalies.append(Anomaly(
                    type='sql_error',
                    severity='high',
                    description='SQL error message detected - possible SQL injection vulnerability',
                    evidence=f'Matched: {match.group(0)}',
                    test_param=test_param,
                    test_value=test_value
                ))
                break
        
        return anomalies
    
    def _check_nosql_errors(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        body = response_data.get('response_body', '')
        
        if not body:
            return anomalies
        
        body_str = str(body)
        
        for pattern in self.nosql_error_patterns:
            match = pattern.search(body_str)
            if match:
                anomalies.append(Anomaly(
                    type='nosql_error',
                    severity='high',
                    description='NoSQL error message detected - possible NoSQL injection vulnerability',
                    evidence=f'Matched: {match.group(0)}',
                    test_param=test_param,
                    test_value=test_value
                ))
                break
        
        return anomalies
    
    def _check_xss_reflection(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        
        if test_value is None:
            return anomalies
        
        body = response_data.get('response_body', '')
        if not body:
            return anomalies
        
        body_str = str(body)
        test_str = str(test_value)
        
        xss_payloads = ['<script', 'alert(', 'onerror=', 'onload=', 'javascript:']
        
        if any(payload.lower() in test_str.lower() for payload in xss_payloads):
            if test_str in body_str:
                anomalies.append(Anomaly(
                    type='xss_reflection',
                    severity='high',
                    description='XSS payload reflected without sanitization',
                    evidence=f'Payload "{test_str[:50]}..." found in response',
                    test_param=test_param,
                    test_value=test_value
                ))
        
        return anomalies
    
    def _check_server_info_leak(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        headers = response_data.get('response_headers', {})
        
        sensitive_headers = ['X-Powered-By', 'Server', 'X-AspNet-Version', 'X-AspNetMvc-Version']
        
        for header in sensitive_headers:
            if header in headers:
                anomalies.append(Anomaly(
                    type='info_leak',
                    severity='low',
                    description=f'Server information leak via header: {header}',
                    evidence=f'{header}: {headers[header]}',
                    test_param=test_param,
                    test_value=test_value
                ))
        
        return anomalies
    
    def _check_content_smuggling(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        body = response_data.get('response_body', '')
        status_code = response_data.get('status_code', 0)
        
        if test_value is None:
            return anomalies
        
        if str(test_value) in ['', ' ', None] and status_code == 200:
            content_length = len(str(body)) if body else 0
            if content_length == 0:
                anomalies.append(Anomaly(
                    type='empty_response',
                    severity='low',
                    description='Empty response for empty input',
                    evidence='Empty input resulted in empty response body',
                    test_param=test_param,
                    test_value=test_value
                ))
        
        return anomalies
    
    def _check_language_specific_errors(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        body = response_data.get('response_body', '')
        
        if not body:
            return anomalies
        
        body_str = str(body)
        
        for lang, patterns in self.language_specific_errors.items():
            for pattern in patterns:
                match = pattern.search(body_str)
                if match:
                    anomalies.append(Anomaly(
                        type=f'{lang}_error',
                        severity='high',
                        description=f'{lang.title()} specific error detected',
                        evidence=f'Matched pattern: {match.group(0)[:100]}',
                        test_param=test_param,
                        test_value=test_value
                    ))
                    break
        
        return anomalies
    
    def _check_template_injection(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        body = response_data.get('response_body', '')
        
        if not body:
            return anomalies
        
        body_str = str(body)
        
        for pattern in self.template_injection_patterns:
            match = pattern.search(body_str)
            if match:
                anomalies.append(Anomaly(
                    type='template_injection',
                    severity='high',
                    description='Template engine error detected - possible SSTI vulnerability',
                    evidence=f'Matched: {match.group(0)}',
                    test_param=test_param,
                    test_value=test_value
                ))
                break
        
        return anomalies
    
    def _check_response_body_deep(
        self,
        response_data: Dict[str, Any],
        baseline_data: Optional[Dict[str, Any]],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        body = response_data.get('response_body', '')
        status_code = response_data.get('status_code')
        
        if not body:
            return anomalies
        
        if isinstance(body, dict) or isinstance(body, list):
            error_fields = self.body_analyzer.extract_error_fields(body)
            for err in error_fields:
                anomalies.append(Anomaly(
                    type='error_field_detected',
                    severity='medium',
                    description=f"Error field detected: {err['path']}",
                    evidence=f"{err['key']} = {err['value']}",
                    test_param=test_param,
                    test_value=test_value
                ))
            
            biz_errors = self.body_analyzer.detect_business_logic_errors(body, status_code)
            for biz_err in biz_errors:
                anomalies.append(Anomaly(
                    type=biz_err['type'],
                    severity='medium',
                    description=biz_err['description'],
                    evidence=biz_err['evidence'],
                    test_param=test_param,
                    test_value=test_value
                ))
            
            if baseline_data:
                baseline_body = baseline_data.get('response_body')
                structure = self.body_analyzer.check_response_structure(body, baseline_body)
                if structure['structure_changed']:
                    if structure['missing_keys']:
                        anomalies.append(Anomaly(
                            type='structure_change_missing',
                            severity='low',
                            description='Response structure changed - missing keys',
                            evidence=f"Missing keys: {', '.join(structure['missing_keys'])}",
                            test_param=test_param,
                            test_value=test_value
                        ))
                    if structure['new_keys']:
                        anomalies.append(Anomaly(
                            type='structure_change_new',
                            severity='low',
                            description='Response structure changed - new keys',
                            evidence=f"New keys: {', '.join(structure['new_keys'])}",
                            test_param=test_param,
                            test_value=test_value
                        ))
        
        return anomalies
    
    def _check_content_consistency(
        self,
        response_data: Dict[str, Any],
        baseline_data: Optional[Dict[str, Any]],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        
        if not baseline_data:
            return anomalies
        
        fp_current = self.body_analyzer.calculate_fingerprint(response_data)
        fp_baseline = self.body_analyzer.calculate_fingerprint(baseline_data)
        
        headers = response_data.get('response_headers', {})
        content_type = headers.get('Content-Type', '')
        body = response_data.get('response_body', '')
        
        if 'application/json' in content_type:
            if not isinstance(body, (dict, list)):
                anomalies.append(Anomaly(
                    type='content_type_mismatch',
                    severity='low',
                    description='Content-Type header indicates JSON but body is not JSON',
                    evidence=f"Content-Type: {content_type}, Body type: {type(body).__name__}",
                    test_param=test_param,
                    test_value=test_value
                ))
        
        if 'text/html' in content_type or 'application/json' in content_type:
            body_str = str(body)
            if '<html' in body_str.lower() and 'application/json' in content_type:
                anomalies.append(Anomaly(
                    type='mixed_content',
                    severity='low',
                    description='JSON endpoint returning HTML content',
                    evidence='Response contains HTML tags despite JSON Content-Type',
                    test_param=test_param,
                    test_value=test_value
                ))
        
        if fp_baseline.content_length > 0:
            length_ratio = fp_current.content_length / fp_baseline.content_length
            if length_ratio > 10 and fp_current.content_length > 10000:
                anomalies.append(Anomaly(
                    type='excessive_content_length',
                    severity='medium',
                    description=f'Response size significantly larger than baseline: {length_ratio:.1f}x',
                    evidence=f"Baseline: {fp_baseline.content_length} bytes, Current: {fp_current.content_length} bytes",
                    test_param=test_param,
                    test_value=test_value
                ))
            elif length_ratio < 0.1 and fp_baseline.content_length > 100:
                anomalies.append(Anomaly(
                    type='reduced_content_length',
                    severity='low',
                    description=f'Response size significantly smaller than baseline: {length_ratio:.1f}x',
                    evidence=f"Baseline: {fp_baseline.content_length} bytes, Current: {fp_current.content_length} bytes",
                    test_param=test_param,
                    test_value=test_value
                ))
        
        return anomalies
    
    def _check_nonstandard_status(
        self,
        response_data: Dict[str, Any],
        test_param: Optional[str],
        test_value: Optional[Any]
    ) -> List[Anomaly]:
        anomalies = []
        status_code = response_data.get('status_code')
        
        if status_code is None:
            return anomalies
        
        standard_statuses = {
            100, 101, 102,
            200, 201, 202, 203, 204, 205, 206, 207, 208, 226,
            300, 301, 302, 303, 304, 305, 306, 307, 308,
            400, 401, 402, 403, 404, 405, 406, 407, 408, 409,
            410, 411, 412, 413, 414, 415, 416, 417, 418, 421,
            422, 423, 424, 425, 426, 428, 429, 431, 451,
            500, 501, 502, 503, 504, 505, 506, 507, 508, 510, 511
        }
        
        if status_code not in standard_statuses and status_code > 0:
            anomalies.append(Anomaly(
                type='nonstandard_status_code',
                severity='low',
                description=f'Non-standard HTTP status code: {status_code}',
                evidence=f'Status code {status_code} is not in the standard HTTP status code list',
                test_param=test_param,
                test_value=test_value
            ))
        
        return anomalies
    
    def analyze_trends(self, anomalies_history: List[List[Anomaly]]) -> Dict[str, Any]:
        if not anomalies_history:
            return {}
        
        type_counts = {}
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        affected_params = set()
        
        for anomalies in anomalies_history:
            for anomaly in anomalies:
                type_counts[anomaly.type] = type_counts.get(anomaly.type, 0) + 1
                severity_counts[anomaly.severity] += 1
                if anomaly.test_param:
                    affected_params.add(anomaly.test_param)
        
        return {
            'total_tests': len(anomalies_history),
            'tests_with_anomalies': sum(1 for a in anomalies_history if a),
            'anomaly_type_distribution': type_counts,
            'severity_distribution': severity_counts,
            'affected_params': list(affected_params),
            'vulnerability_score': min(100, severity_counts['high'] * 10 + severity_counts['medium'] * 5 + severity_counts['low'] * 1)
        }
