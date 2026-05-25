import os
import re
import ast
from typing import Dict, List, Any, Optional


class CustomRulesChecker:
    def __init__(self, rules_config: Dict[str, Any] = None):
        self.rules_config = rules_config or {}
        
    def check_file(self, file_path: str) -> Dict[str, Any]:
        issues = []
        
        if file_path.endswith('.py'):
            issues.extend(self._check_python_rules(file_path))
        elif any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx']):
            issues.extend(self._check_javascript_rules(file_path))
        
        issues.extend(self._check_security_rules(file_path))
        issues.extend(self._check_naming_rules(file_path))
        
        return {
            "file": file_path,
            "issues": issues,
            "summary": self._summarize_issues(issues)
        }
    
    def _check_python_rules(self, file_path: str) -> List[Dict[str, Any]]:
        issues = []
        python_rules = self.rules_config.get('custom_rules', {}).get('python', {})
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            tree = ast.parse(content)
            
            if python_rules.get('max_function_args', {}).get('enabled', False):
                max_args = python_rules['max_function_args'].get('max_args', 5)
                severity = python_rules['max_function_args'].get('severity', 'medium')
                message = python_rules['max_function_args'].get('message', '函数参数过多')
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if len(node.args.args) > max_args:
                            issues.append({
                                "type": "custom",
                                "rule": "max_function_args",
                                "severity": severity,
                                "message": f"{message}: {node.name} has {len(node.args.args)} args",
                                "line": node.lineno,
                                "file": file_path
                            })
            
            if python_rules.get('max_nesting_depth', {}).get('enabled', False):
                max_depth = python_rules['max_nesting_depth'].get('max_depth', 4)
                severity = python_rules['max_nesting_depth'].get('severity', 'high')
                message = python_rules['max_nesting_depth'].get('message', '嵌套层级过深')
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        depth = self._calculate_nesting_depth(node)
                        if depth > max_depth:
                            issues.append({
                                "type": "custom",
                                "rule": "max_nesting_depth",
                                "severity": severity,
                                "message": f"{message}: {node.name} has nesting depth {depth}",
                                "line": node.lineno,
                                "file": file_path
                            })
            
            if python_rules.get('max_line_length', {}).get('enabled', False):
                max_length = python_rules['max_line_length'].get('max_length', 120)
                severity = python_rules['max_line_length'].get('severity', 'low')
                message = python_rules['max_line_length'].get('message', '行长度超过限制')
                
                for i, line in enumerate(lines, 1):
                    if len(line) > max_length:
                        issues.append({
                            "type": "custom",
                            "rule": "max_line_length",
                            "severity": severity,
                            "message": f"{message}: {len(line)} chars",
                            "line": i,
                            "file": file_path
                        })
        
        except Exception as e:
            issues.append({
                "type": "custom",
                "rule": "parse_error",
                "severity": "low",
                "message": f"Failed to parse Python file: {str(e)}",
                "line": 0,
                "file": file_path
            })
        
        return issues
    
    def _calculate_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        max_depth = current_depth
        
        nested_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, nested_nodes):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
            else:
                child_depth = self._calculate_nesting_depth(child, current_depth)
            max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def _check_javascript_rules(self, file_path: str) -> List[Dict[str, Any]]:
        issues = []
        js_rules = self.rules_config.get('custom_rules', {}).get('javascript', {})
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if js_rules.get('max_function_length', {}).get('enabled', False):
                max_lines = js_rules['max_function_length'].get('max_lines', 100)
                severity = js_rules['max_function_length'].get('severity', 'medium')
                message = js_rules['max_function_length'].get('message', '函数体过长')
                
                func_pattern = r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?function|(\w+)\s*:\s*(?:async\s+)?function|(\w+)\s*=\s*(?:async\s+)?\()'
                
                in_function = False
                func_start = 0
                func_name = ""
                brace_count = 0
                
                for i, line in enumerate(lines, 1):
                    match = re.search(func_pattern, line)
                    if match and not in_function:
                        func_name = match.group(1) or match.group(2) or match.group(3) or match.group(4) or "anonymous"
                        in_function = True
                        func_start = i
                        brace_count = line.count('{') - line.count('}')
                    elif in_function:
                        brace_count += line.count('{') - line.count('}')
                        if brace_count <= 0:
                            func_length = i - func_start
                            if func_length > max_lines:
                                issues.append({
                                    "type": "custom",
                                    "rule": "max_function_length",
                                    "severity": severity,
                                    "message": f"{message}: {func_name} has {func_length} lines",
                                    "line": func_start,
                                    "file": file_path
                                })
                            in_function = False
            
            if js_rules.get('no_console_log', {}).get('enabled', False):
                severity = js_rules['no_console_log'].get('severity', 'low')
                message = js_rules['no_console_log'].get('message', '避免使用 console.log')
                
                for i, line in enumerate(lines, 1):
                    if 'console.log' in line:
                        issues.append({
                            "type": "custom",
                            "rule": "no_console_log",
                            "severity": severity,
                            "message": message,
                            "line": i,
                            "file": file_path
                        })
        
        except Exception as e:
            pass
        
        return issues
    
    def _check_security_rules(self, file_path: str) -> List[Dict[str, Any]]:
        issues = []
        security_rules = self.rules_config.get('custom_rules', {}).get('security', {})
        
        if security_rules.get('hardcoded_secrets', {}).get('enabled', False):
            patterns = security_rules['hardcoded_secrets'].get('patterns', [])
            severity = security_rules['hardcoded_secrets'].get('severity', 'critical')
            message = security_rules['hardcoded_secrets'].get('message', '检测到硬编码的敏感信息')
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if re.search(pattern, line):
                            issues.append({
                                "type": "custom",
                                "rule": "hardcoded_secrets",
                                "severity": severity,
                                "message": message,
                                "line": i,
                                "file": file_path
                            })
                            break
            except Exception:
                pass
        
        return issues
    
    def _check_naming_rules(self, file_path: str) -> List[Dict[str, Any]]:
        issues = []
        naming_rules = self.rules_config.get('custom_rules', {}).get('naming', {})
        
        if not file_path.endswith('.py'):
            return issues
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            if naming_rules.get('class_name_pattern', {}).get('enabled', False):
                pattern = naming_rules['class_name_pattern'].get('pattern', '^[A-Z][a-zA-Z0-9]*$')
                severity = naming_rules['class_name_pattern'].get('severity', 'medium')
                message = naming_rules['class_name_pattern'].get('message', '类名应使用大驼峰命名法')
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if not re.match(pattern, node.name):
                            issues.append({
                                "type": "custom",
                                "rule": "class_name_pattern",
                                "severity": severity,
                                "message": f"{message}: {node.name}",
                                "line": node.lineno,
                                "file": file_path
                            })
            
            if naming_rules.get('function_name_pattern', {}).get('enabled', False):
                pattern = naming_rules['function_name_pattern'].get('pattern', '^[a-z_][a-zA-Z0-9_]*$')
                severity = naming_rules['function_name_pattern'].get('severity', 'low')
                message = naming_rules['function_name_pattern'].get('message', '函数名应使用蛇形命名法')
                
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith('_') and not re.match(pattern, node.name):
                            issues.append({
                                "type": "custom",
                                "rule": "function_name_pattern",
                                "severity": severity,
                                "message": f"{message}: {node.name}",
                                "line": node.lineno,
                                "file": file_path
                            })
        
        except Exception:
            pass
        
        return issues
    
    def _summarize_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            severity = issue.get("severity", "low")
            if severity in summary:
                summary[severity] += 1
        summary["total"] = len(issues)
        return summary
    
    def check_directory(self, directory: str) -> Dict[str, Any]:
        all_issues = []
        file_results = []
        
        supported_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx']
        
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in supported_extensions):
                    file_path = os.path.join(root, file)
                    result = self.check_file(file_path)
                    file_results.append(result)
                    all_issues.extend(result["issues"])
        
        summary = self._summarize_issues(all_issues)
        
        return {
            "file_results": file_results,
            "all_issues": all_issues,
            "summary": summary
        }
