import os
import json
import time
import shlex
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from urllib.parse import urlencode
from config import REPORTS_DIR, DEFAULT_CONFIG
from .param_generator import ParameterGenerator
from .dependency_resolver import DependencyResolver, StepResult
from .request_sender import RequestSender, RequestResult
from .anomaly_detector import AnomalyDetector, Anomaly
from .case_evolver import EvolutionEngine
from .security_tester import SecurityScanner, SecurityFinding


@dataclass
class ReproduceInfo:
    curl_command: str
    python_code: str
    raw_request: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'curl_command': self.curl_command,
            'python_code': self.python_code,
            'raw_request': self.raw_request
        }


@dataclass
class TestCaseResult:
    test_id: str
    test_name: str
    tested_param: str
    test_value: Any
    value_type: str
    description: str
    request: RequestResult
    reproduce: ReproduceInfo
    anomalies: List[Anomaly] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_id': self.test_id,
            'test_name': self.test_name,
            'tested_param': self.tested_param,
            'test_value': self.test_value,
            'value_type': self.value_type,
            'description': self.description,
            'request': self.request.to_dict(),
            'reproduce': self.reproduce.to_dict(),
            'anomalies': [a.to_dict() for a in self.anomalies],
            'timestamp': self.timestamp
        }


@dataclass
class TestResult:
    test_run_id: str
    api_name: str
    start_time: float
    end_time: float = 0.0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    test_cases: List[TestCaseResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_run_id': self.test_run_id,
            'api_name': self.api_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.end_time - self.start_time,
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'test_cases': [tc.to_dict() for tc in self.test_cases],
            'summary': self.summary,
            'config': self.config
        }


class TestEngine:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.param_generator = ParameterGenerator()
        self.dependency_resolver = DependencyResolver()
        self.request_sender = RequestSender(self.config)
        self.anomaly_detector = AnomalyDetector(self.config.get('anomaly_detection', {}))
        self.evolution_engine = EvolutionEngine()
        self.security_scanner = SecurityScanner()
        
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        self._baseline_result: Optional[RequestResult] = None
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        self._progress_callback = callback
    
    def _report_progress(self, current: int, total: int, message: str) -> None:
        if self._progress_callback:
            self._progress_callback(current, total, message)
    
    def generate_reproduce_info(
        self,
        url: str,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        param_location: str
    ) -> ReproduceInfo:
        raw_request = {
            'url': url,
            'method': method,
            'params': params,
            'headers': headers,
            'param_location': param_location
        }
        
        curl_parts = ['curl']
        curl_parts.extend(['-X', method])
        
        for key, value in headers.items():
            curl_parts.extend(['-H', shlex.quote(f'{key}: {value}')])
        
        if param_location == 'query':
            if params:
                query_string = urlencode(params)
                curl_url = f"{url}?{query_string}" if '?' not in url else f"{url}&{query_string}"
            else:
                curl_url = url
            curl_parts.append(shlex.quote(curl_url))
        elif param_location == 'body':
            content_type = headers.get('Content-Type', '')
            if 'application/json' in content_type:
                body_json = json.dumps(params, ensure_ascii=False)
                curl_parts.extend(['-d', shlex.quote(body_json)])
            else:
                body_form = urlencode(params)
                curl_parts.extend(['-d', shlex.quote(body_form)])
            curl_parts.append(shlex.quote(url))
        elif param_location == 'path':
            curl_url = url
            for key, value in params.items():
                curl_url = curl_url.replace(f'{{{key}}}', str(value))
            curl_parts.append(shlex.quote(curl_url))
        else:
            curl_parts.append(shlex.quote(url))
        
        curl_parts.append('-s')
        curl_parts.append('-i')
        curl_command = ' '.join(curl_parts)
        
        python_code = self._generate_python_code(url, method, params, headers, param_location)
        
        return ReproduceInfo(
            curl_command=curl_command,
            python_code=python_code,
            raw_request=raw_request
        )
    
    def _generate_python_code(
        self,
        url: str,
        method: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        param_location: str
    ) -> str:
        lines = [
            'import requests',
            '',
            f'url = {json.dumps(url, ensure_ascii=False)}',
            ''
        ]
        
        if headers:
            lines.append('headers = {')
            for key, value in headers.items():
                lines.append(f'    {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},')
            lines.append('}')
            lines.append('')
        
        lines.append('params = {')
        for key, value in params.items():
            lines.append(f'    {json.dumps(key)}: {json.dumps(value, ensure_ascii=False, default=str)},')
        lines.append('}')
        lines.append('')
        
        if param_location == 'query':
            lines.append(f'response = requests.{method.lower()}(url, params=params, headers=headers)')
        elif param_location == 'body':
            lines.append(f'response = requests.{method.lower()}(url, json=params, headers=headers)')
        elif param_location == 'path':
            lines.append('import string')
            lines.append('formatter = string.Formatter()')
            lines.append('formatted_url = url')
            lines.append('for key, value in params.items():')
            lines.append('    formatted_url = formatted_url.replace(f"{{{key}}}", str(value))')
            lines.append('')
            lines.append(f'response = requests.{method.lower()}(formatted_url, headers=headers)')
        else:
            lines.append(f'response = requests.{method.lower()}(url, params=params, headers=headers)')
        
        lines.extend([
            '',
            'print(f"Status: {response.status_code}")',
            'print(f"Response: {response.text}")'
        ])
        
        return '\n'.join(lines)
    
    def run_baseline_test(
        self,
        url: str,
        method: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        param_location: str = 'query'
    ) -> Optional[RequestResult]:
        if param_location == 'query':
            result = self.request_sender.send_request(
                url=url,
                method=method,
                params=params,
                headers=headers
            )
        elif param_location == 'body':
            result = self.request_sender.send_request(
                url=url,
                method=method,
                body=params,
                headers=headers
            )
        elif param_location == 'path':
            result = self.request_sender.send_request(
                url=url,
                method=method,
                path_params=params,
                headers=headers
            )
        else:
            result = self.request_sender.send_request(
                url=url,
                method=method,
                params=params,
                headers=headers
            )
        
        if result.status_code and 200 <= result.status_code < 400:
            self._baseline_result = result
        
        return result
    
    def run_test(
        self,
        api_config: Dict[str, Any],
        test_mode: str = 'single',
        max_combinations: int = 100
    ) -> TestResult:
        test_run_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000)}"
        api_name = api_config.get('name', 'Unknown API')
        url = api_config['url']
        method = api_config.get('method', 'GET')
        headers = api_config.get('headers', {})
        param_location = api_config.get('param_location', 'query')
        api_params = api_config.get('params', [])
        
        default_params = {p['name']: p.get('default', '') for p in api_params}
        
        result = TestResult(
            test_run_id=test_run_id,
            api_name=api_name,
            start_time=time.time(),
            config={
                'url': url,
                'method': method,
                'param_location': param_location,
                'test_mode': test_mode,
                'max_combinations': max_combinations
            }
        )
        
        baseline = self.run_baseline_test(url, method, default_params, headers, param_location)
        baseline_dict = baseline.to_dict() if baseline else None
        
        test_combinations = list(self.param_generator.generate_param_combinations(
            api_params=api_params,
            test_mode=test_mode,
            max_combinations=max_combinations
        ))
        
        total_tests = len(test_combinations)
        result.total_tests = total_tests
        
        for idx, combo in enumerate(test_combinations, 1):
            params = combo['params']
            tested_param = combo['tested_param']
            value_info = combo['value_info'] or {}
            
            test_id = f"{test_run_id}_{idx}"
            
            self._report_progress(idx, total_tests, f"Testing: {tested_param} = {value_info.get('value', 'N/A')}")
            
            if param_location == 'query':
                request_result = self.request_sender.send_request(
                    url=url,
                    method=method,
                    params=params,
                    headers=headers
                )
            elif param_location == 'body':
                request_result = self.request_sender.send_request(
                    url=url,
                    method=method,
                    body=params,
                    headers=headers
                )
            elif param_location == 'path':
                request_result = self.request_sender.send_request(
                    url=url,
                    method=method,
                    path_params=params,
                    headers=headers
                )
            else:
                request_result = self.request_sender.send_request(
                    url=url,
                    method=method,
                    params=params,
                    headers=headers
                )
            
            anomalies = self.anomaly_detector.detect(
                response_data=request_result.to_dict(),
                baseline_data=baseline_dict,
                test_param=tested_param,
                test_value=value_info.get('value')
            )
            
            reproduce_info = self.generate_reproduce_info(
                url=url,
                method=method,
                params=params,
                headers=headers,
                param_location=param_location
            )
            
            test_case = TestCaseResult(
                test_id=test_id,
                test_name=f"{api_name}_{idx}",
                tested_param=tested_param,
                test_value=value_info.get('value'),
                value_type=value_info.get('type', 'unknown'),
                description=value_info.get('description', ''),
                request=request_result,
                reproduce=reproduce_info,
                anomalies=anomalies
            )
            
            result.test_cases.append(test_case)
            
            if anomalies:
                result.failed_tests += 1
            else:
                result.passed_tests += 1
        
        result.end_time = time.time()
        result.summary = self._generate_summary(result)
        
        return result
    
    def run_workflow_test(
        self,
        workflow_config: Dict[str, Any]
    ) -> TestResult:
        test_run_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        workflow_name = workflow_config.get('name', 'Unknown Workflow')
        steps = workflow_config.get('steps', [])
        
        result = TestResult(
            test_run_id=test_run_id,
            api_name=workflow_name,
            start_time=time.time(),
            config=workflow_config
        )
        
        validation = self.dependency_resolver.validate_dependencies(steps)
        if not validation['valid']:
            raise ValueError(f"Workflow validation failed: {validation['errors']}")
        
        execution_order = validation['execution_order']
        step_map = {step['name']: step for step in steps}
        
        total_tests = 0
        for step_name in execution_order:
            step = step_map[step_name]
            api_params = step.get('params_def', [])
            test_mode = step.get('test_mode', 'single')
            
            test_combinations = list(self.param_generator.generate_param_combinations(
                api_params=api_params,
                test_mode=test_mode
            ))
            total_tests += len(test_combinations)
        
        result.total_tests = total_tests
        current_test = 0
        
        for step_name in execution_order:
            step = step_map[step_name]
            url = step['url']
            method = step.get('method', 'GET')
            headers = step.get('headers', {})
            param_location = step.get('param_location', 'query')
            api_params = step.get('params_def', [])
            extract_rules = step.get('extract', {})
            
            for alias, json_path in extract_rules.items():
                self.dependency_resolver.add_extract_rule(step_name, json_path, alias)
            
            test_combinations = list(self.param_generator.generate_param_combinations(
                api_params=api_params,
                test_mode=step.get('test_mode', 'single')
            ))
            
            default_params = {p['name']: p.get('default', '') for p in api_params}
            resolved_defaults = self.dependency_resolver.resolve_params(default_params)
            
            baseline = self.run_baseline_test(url, method, resolved_defaults, headers, param_location)
            baseline_dict = baseline.to_dict() if baseline else None
            
            step_result = StepResult(
                step_name=step_name,
                success=baseline is not None and baseline.status_code and 200 <= baseline.status_code < 400,
                response=baseline.response_body if baseline else None
            )
            self.dependency_resolver.set_step_result(step_result)
            
            for combo in test_combinations:
                current_test += 1
                params = combo['params']
                tested_param = combo['tested_param']
                value_info = combo['value_info'] or {}
                
                resolved_params = self.dependency_resolver.resolve_params(params)
                
                unresolved = [k for k, v in resolved_params.items() 
                             if isinstance(v, str) and v.startswith('__UNRESOLVED__')]
                if unresolved:
                    continue
                
                test_id = f"{test_run_id}_{current_test}"
                
                self._report_progress(
                    current_test, 
                    total_tests, 
                    f"Step {step_name}: {tested_param} = {value_info.get('value', 'N/A')}"
                )
                
                if param_location == 'query':
                    request_result = self.request_sender.send_request(
                        url=url,
                        method=method,
                        params=resolved_params,
                        headers=headers
                    )
                elif param_location == 'body':
                    request_result = self.request_sender.send_request(
                        url=url,
                        method=method,
                        body=resolved_params,
                        headers=headers
                    )
                else:
                    request_result = self.request_sender.send_request(
                        url=url,
                        method=method,
                        params=resolved_params,
                        headers=headers
                    )
                
                anomalies = self.anomaly_detector.detect(
                    response_data=request_result.to_dict(),
                    baseline_data=baseline_dict,
                    test_param=tested_param,
                    test_value=value_info.get('value')
                )
                
                reproduce_info = self.generate_reproduce_info(
                    url=url,
                    method=method,
                    params=resolved_params,
                    headers=headers,
                    param_location=param_location
                )
                
                test_case = TestCaseResult(
                    test_id=test_id,
                    test_name=f"{step_name}_{current_test}",
                    tested_param=f"{step_name}.{tested_param}",
                    test_value=value_info.get('value'),
                    value_type=value_info.get('type', 'unknown'),
                    description=value_info.get('description', ''),
                    request=request_result,
                    reproduce=reproduce_info,
                    anomalies=anomalies
                )
                
                result.test_cases.append(test_case)
                
                if anomalies:
                    result.failed_tests += 1
                else:
                    result.passed_tests += 1
        
        result.end_time = time.time()
        result.summary = self._generate_summary(result)
        
        self.dependency_resolver.clear()
        
        return result
    
    def _generate_summary(self, result: TestResult) -> Dict[str, Any]:
        all_anomalies = [tc.anomalies for tc in result.test_cases]
        trend_analysis = self.anomaly_detector.analyze_trends(all_anomalies)
        
        type_distribution = {}
        severity_distribution = {'high': 0, 'medium': 0, 'low': 0}
        param_anomalies = {}
        
        for tc in result.test_cases:
            for anomaly in tc.anomalies:
                type_distribution[anomaly.type] = type_distribution.get(anomaly.type, 0) + 1
                severity_distribution[anomaly.severity] += 1
                
                if anomaly.test_param:
                    if anomaly.test_param not in param_anomalies:
                        param_anomalies[anomaly.test_param] = {'count': 0, 'anomalies': []}
                    param_anomalies[anomaly.test_param]['count'] += 1
                    param_anomalies[anomaly.test_param]['anomalies'].append(anomaly.to_dict())
        
        return {
            **trend_analysis,
            'type_distribution': type_distribution,
            'severity_distribution': severity_distribution,
            'param_anomalies': param_anomalies,
            'pass_rate': (result.passed_tests / result.total_tests * 100) if result.total_tests > 0 else 0,
            'duration_seconds': result.end_time - result.start_time,
            'recommendations': self._generate_recommendations(type_distribution, severity_distribution)
        }
    
    def _generate_recommendations(
        self,
        type_distribution: Dict[str, int],
        severity_distribution: Dict[str, int]
    ) -> List[str]:
        recommendations = []
        
        if severity_distribution.get('high', 0) > 0:
            recommendations.append('Critical issues detected. Immediate remediation is recommended.')
        
        if 'sql_error' in type_distribution:
            recommendations.append('SQL injection vulnerabilities detected. Implement parameterized queries and input validation.')
        
        if 'xss_reflection' in type_distribution:
            recommendations.append('XSS vulnerabilities detected. Implement output encoding and CSP headers.')
        
        if 'stack_trace_leak' in type_distribution:
            recommendations.append('Stack traces are being exposed. Configure production error handling.')
        
        if 'info_leak' in type_distribution:
            recommendations.append('Server information is being leaked. Remove sensitive response headers.')
        
        if 'time_based_anomaly' in type_distribution:
            recommendations.append('Time-based anomalies detected. Potential for blind SQL injection.')
        
        if 'request_error' in type_distribution:
            recommendations.append('Request failures detected. Check API availability and network connectivity.')
        
        return recommendations
    
    def save_report(self, result: TestResult, format: str = 'json') -> str:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        if format == 'json':
            filename = f"{result.test_run_id}.json"
            filepath = os.path.join(REPORTS_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        elif format == 'html':
            filename = f"{result.test_run_id}.html"
            filepath = os.path.join(REPORTS_DIR, filename)
            self._generate_html_report(result, filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return filepath
    
    def _generate_html_report(self, result: TestResult, filepath: str) -> None:
        template_path = os.path.join(os.path.dirname(__file__), '..', 'web', 'templates', 'report_template.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        report_data = result.to_dict()
        json_data = json.dumps(report_data, ensure_ascii=False, default=str)
        
        html_content = template_content.replace('{{ report_data|safe }}', json_data)
        html_content = html_content.replace('{{ test_run_id }}', result.test_run_id)
        html_content = html_content.replace('{{ api_name }}', result.api_name)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def list_reports(self) -> List[Dict[str, Any]]:
        if not os.path.exists(REPORTS_DIR):
            return []
        
        reports = []
        for filename in os.listdir(REPORTS_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(REPORTS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    reports.append({
                        'test_run_id': data.get('test_run_id', filename),
                        'api_name': data.get('api_name', 'Unknown'),
                        'start_time': data.get('start_time', 0),
                        'total_tests': data.get('total_tests', 0),
                        'pass_rate': data.get('summary', {}).get('pass_rate', 0),
                        'filename': filename,
                        'filepath': filepath
                    })
                except Exception:
                    continue
        
        return sorted(reports, key=lambda x: x['start_time'], reverse=True)
    
    def load_report(self, test_run_id: str) -> Optional[Dict[str, Any]]:
        filepath = os.path.join(REPORTS_DIR, f"{test_run_id}.json")
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def run_security_scan(
        self,
        api_config: Dict[str, Any],
        quick: bool = False
    ) -> TestResult:
        test_run_id = f"security_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        api_name = api_config.get('name', 'Unknown API')
        url = api_config['url']
        method = api_config.get('method', 'GET')
        headers = api_config.get('headers', {})
        param_location = api_config.get('param_location', 'query')
        api_params = api_config.get('params', [])
        
        result = TestResult(
            test_run_id=test_run_id,
            api_name=api_name,
            start_time=time.time(),
            config={
                'url': url,
                'method': method,
                'param_location': param_location,
                'scan_type': 'security'
            }
        )
        
        default_params = {p['name']: p.get('default', '') for p in api_params}
        baseline = self.run_baseline_test(url, method, default_params, headers, param_location)
        baseline_dict = baseline.to_dict() if baseline else None
        
        total_tests = 0
        test_cases_list = []
        
        for param in api_params:
            param_name = param['name']
            param_type = param.get('type', 'string')
            
            sqli_payloads = self.security_scanner.sqli_tester.get_payloads_for_test()
            xss_payloads = self.security_scanner.xss_tester.get_payloads_for_test()
            
            if quick:
                sqli_payloads = sqli_payloads[:5]
                xss_payloads = xss_payloads[:5]
            
            total_tests += len(sqli_payloads) + len(xss_payloads)
            
            for payload, payload_type in sqli_payloads:
                test_params = default_params.copy()
                test_params[param_name] = payload
                
                if param_location == 'query':
                    request_result = self.request_sender.send_request(
                        url=url, method=method, params=test_params, headers=headers
                    )
                elif param_location == 'body':
                    request_result = self.request_sender.send_request(
                        url=url, method=method, body=test_params, headers=headers
                    )
                else:
                    request_result = self.request_sender.send_request(
                        url=url, method=method, params=test_params, headers=headers
                    )
                
                response_data = request_result.to_dict()
                response_data['tested_param'] = param_name
                response_data['param_location'] = param_location
                
                findings = self.security_scanner.sqli_tester.detect_sqli(response_data, payload)
                
                anomalies = []
                for finding in findings:
                    anomalies.append(Anomaly(
                        type=f'sqli_{finding.sub_type}',
                        severity=finding.severity,
                        description=finding.description,
                        test_param=param_name,
                        test_value=payload,
                        evidence=finding.evidence
                    ))
                
                reproduce_info = self.generate_reproduce_info(
                    url, method, test_params, headers, param_location
                )
                
                test_case = TestCaseResult(
                    test_id=f"{test_run_id}_sqli_{len(test_cases_list)}",
                    test_name=f"SQLi_{param_name}",
                    tested_param=param_name,
                    test_value=payload,
                    value_type=f'sqli_{payload_type}',
                    description=f"SQL injection test: {payload_type}",
                    request=request_result,
                    reproduce=reproduce_info,
                    anomalies=anomalies
                )
                
                test_cases_list.append(test_case)
            
            for payload, payload_type in xss_payloads:
                test_params = default_params.copy()
                test_params[param_name] = payload
                
                if param_location == 'query':
                    request_result = self.request_sender.send_request(
                        url=url, method=method, params=test_params, headers=headers
                    )
                elif param_location == 'body':
                    request_result = self.request_sender.send_request(
                        url=url, method=method, body=test_params, headers=headers
                    )
                else:
                    request_result = self.request_sender.send_request(
                        url=url, method=method, params=test_params, headers=headers
                    )
                
                response_data = request_result.to_dict()
                response_data['tested_param'] = param_name
                response_data['param_location'] = param_location
                
                findings = self.security_scanner.xss_tester.detect_xss(response_data, payload)
                
                anomalies = []
                for finding in findings:
                    anomalies.append(Anomaly(
                        type=f'xss_{finding.sub_type}',
                        severity=finding.severity,
                        description=finding.description,
                        test_param=param_name,
                        test_value=payload,
                        evidence=finding.evidence
                    ))
                
                reproduce_info = self.generate_reproduce_info(
                    url, method, test_params, headers, param_location
                )
                
                test_case = TestCaseResult(
                    test_id=f"{test_run_id}_xss_{len(test_cases_list)}",
                    test_name=f"XSS_{param_name}",
                    tested_param=param_name,
                    test_value=payload,
                    value_type=f'xss_{payload_type}',
                    description=f"XSS injection test: {payload_type}",
                    request=request_result,
                    reproduce=reproduce_info,
                    anomalies=anomalies
                )
                
                test_cases_list.append(test_case)
        
        result.total_tests = len(test_cases_list)
        result.test_cases = test_cases_list
        
        for tc in test_cases_list:
            if tc.anomalies:
                result.failed_tests += 1
            else:
                result.passed_tests += 1
        
        result.end_time = time.time()
        result.summary = self._generate_summary(result)
        
        return result
    
    def run_case_evolution(self, test_result: TestResult) -> TestResult:
        failed_cases = []
        for tc in test_result.test_cases:
            if tc.anomalies:
                failed_cases.append({
                    'test_id': tc.test_id,
                    'tested_param': tc.tested_param,
                    'test_value': tc.test_value,
                    'anomalies': [a.to_dict() for a in tc.anomalies]
                })
        
        if not failed_cases:
            evolved_result = TestResult(
                test_run_id=f"{test_result.test_run_id}_evolved",
                api_name=f"{test_result.api_name}_evolved",
                start_time=time.time(),
                config=test_result.config
            )
            evolved_result.end_time = time.time()
            return evolved_result
        
        api_config = test_result.config
        url = api_config.get('url', '')
        method = api_config.get('method', 'GET')
        headers = api_config.get('headers', {})
        param_location = api_config.get('param_location', 'query')
        default_params = {}
        
        def run_evolved_test(evolved_case: Dict[str, Any]) -> Dict[str, Any]:
            test_params = default_params.copy()
            test_params[evolved_case['tested_param']] = evolved_case['test_value']
            
            if param_location == 'query':
                request_result = self.request_sender.send_request(
                    url=url, method=method, params=test_params, headers=headers
                )
            elif param_location == 'body':
                request_result = self.request_sender.send_request(
                    url=url, method=method, body=test_params, headers=headers
                )
            else:
                request_result = self.request_sender.send_request(
                    url=url, method=method, params=test_params, headers=headers
                )
            
            anomalies = self.anomaly_detector.detect(
                response_data=request_result.to_dict(),
                baseline_data=None,
                test_param=evolved_case['tested_param'],
                test_value=evolved_case['test_value']
            )
            
            return {
                'request_result': request_result,
                'anomalies': anomalies
            }
        
        evolution_results = self.evolution_engine.run_evolution_cycle(failed_cases, run_evolved_test)
        
        evolved_result = TestResult(
            test_run_id=f"{test_result.test_run_id}_evolved",
            api_name=f"{test_result.api_name}_evolved",
            start_time=time.time(),
            config={**test_result.config, 'evolution': True}
        )
        
        for idx, evolved_case in enumerate(evolution_results):
            if 'request_result' in evolved_case:
                request_result = evolved_case['request_result']
                anomalies = evolved_case.get('anomalies', [])
                evolution_info = evolved_case.get('evolution', {})
                
                reproduce_info = self.generate_reproduce_info(
                    url, method, 
                    {evolution_info.get('original_id', ''): evolution_info.get('evolved_value', '')},
                    headers, param_location
                )
                
                test_case = TestCaseResult(
                    test_id=f"evolved_{idx}",
                    test_name=f"Evolved_{idx}",
                    tested_param=evolution_info.get('original_id', '').split('_')[0] if '_' in evolution_info.get('original_id', '') else 'unknown',
                    test_value=evolution_info.get('evolved_value', ''),
                    value_type=f"evolved_{evolution_info.get('mutation_type', 'unknown')}",
                    description=f"Evolved test - Generation {evolution_info.get('generation', 1)}",
                    request=request_result,
                    reproduce=reproduce_info,
                    anomalies=anomalies
                )
                
                evolved_result.test_cases.append(test_case)
                
                if anomalies:
                    evolved_result.failed_tests += 1
                else:
                    evolved_result.passed_tests += 1
        
        evolved_result.total_tests = len(evolved_result.test_cases)
        evolved_result.end_time = time.time()
        evolved_result.summary = self._generate_summary(evolved_result)
        evolved_result.summary['evolution'] = self.get_evolution_summary()
        
        return evolved_result
    
    def get_security_report(self) -> Dict[str, Any]:
        return self.security_scanner.get_security_report()
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        return self.evolution_engine.get_summary()
    
    @staticmethod
    def generate_html_report_from_json(json_data: Dict[str, Any], output_path: str) -> None:
        template_path = os.path.join(os.path.dirname(__file__), '..', 'web', 'templates', 'report_template.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        json_str = json.dumps(json_data, ensure_ascii=False, default=str)
        
        html_content = template_content.replace('{{ report_data|safe }}', json_str)
        html_content = html_content.replace('{{ test_run_id }}', json_data.get('test_run_id', 'unknown'))
        html_content = html_content.replace('{{ api_name }}', json_data.get('api_name', 'Unknown API'))
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def close(self) -> None:
        self.request_sender.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
