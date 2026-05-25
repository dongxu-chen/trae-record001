import os
import re
import ast
from typing import Dict, List, Any, Optional, Callable, Tuple


class Rule:
    def __init__(self, name: str, severity: str, message: str):
        self.name = name
        self.severity = severity
        self.message = message
        self.conditions: List[Dict] = []
        self.targets: List[str] = []
        
    def add_condition(self, condition_type: str, params: Dict[str, Any]):
        self.conditions.append({"type": condition_type, "params": params})
        
    def add_target(self, target: str):
        self.targets.append(target)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity,
            "message": self.message,
            "targets": self.targets,
            "conditions": self.conditions
        }


class DSLEngine:
    def __init__(self):
        self.rules: List[Rule] = []
        self._init_keyword_mappings()
        
    def _init_keyword_mappings(self):
        self.severity_keywords = {
            '致命': 'critical', '严重': 'critical', 'critical': 'critical',
            '高': 'high', '较高': 'high', 'high': 'high',
            '中': 'medium', '中等': 'medium', 'medium': 'medium',
            '低': 'low', '较低': 'low', '轻微': 'low', 'low': 'low'
        }
        
        self.target_keywords = {
            '函数': 'function', '方法': 'function', 'function': 'function',
            '类': 'class', 'class': 'class',
            '变量': 'variable', 'variable': 'variable',
            '文件': 'file', 'file': 'file',
            '模块': 'module', 'module': 'module',
            '行': 'line', 'line': 'line'
        }
        
        self.condition_patterns = [
            (r'(?:参数|arguments?)\s*(?:个数|数量|不能超过|应小于|最多)?\s*(\d+)\s*(?:个|)?', 'max_args'),
            (r'(?:行数|长度|lines?)\s*(?:不能超过|应小于|最多|不超过)?\s*(\d+)\s*(?:行|)?', 'max_lines'),
            (r'(?:复杂度|ccn|cyclomatic)\s*(?:不能超过|应小于|最多|不超过)?\s*(\d+)', 'max_complexity'),
            (r'(?:嵌套|nesting)\s*(?:深度|层数)?\s*(?:不能超过|应小于|最多|不超过)?\s*(\d+)\s*(?:层|)?', 'max_nesting'),
            (r'名字?\s*(?:应该|必须|需|要)?\s*(?:匹配|符合|满足|遵循)\s*[:：]?\s*["\'/](.+)["\'/]', 'name_pattern'),
            (r'不能?\s*包含?|禁止|不允许|禁止使用\s*[:：]?\s*(.+)', 'forbidden_content'),
            (r'必须?\s*包含?|应该有|需要有\s*[:：]?\s*(.+)', 'required_content'),
            (r'(?:长度|length)\s*(?:不能超过|应小于|最多|不超过)?\s*(\d+)\s*(?:字符|)?', 'max_length'),
            (r'(?:检测|检查|查找)\s*(硬编码|明文)\s*(密码|密钥|secret|password)', 'hardcoded_secrets'),
            (r'不允许?使用\s*(?:console\.log|print)\s*语句?', 'no_print_or_log')
        ]
        
    def parse_dsl_file(self, file_path: str) -> List[Rule]:
        if not os.path.exists(file_path):
            return []
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return self.parse_dsl_content(content)
    
    def parse_dsl_content(self, content: str) -> List[Rule]:
        self.rules = []
        current_rule = None
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line or line.startswith('#') or line.startswith('//'):
                i += 1
                continue
                
            rule_match = re.match(
                r'(?:规则|rule)\s+["\']([^"\']+)["\']\s*[：:,]?\s*(?:严重程度|severity|级别)?\s*[:：]?\s*(\w+)?',
                line, re.IGNORECASE
            )
            
            if rule_match:
                rule_name = rule_match.group(1)
                severity_str = rule_match.group(2) or 'medium'
                severity = self.severity_keywords.get(severity_str.lower(), 'medium')
                
                current_rule = Rule(rule_name, severity, rule_name)
                self.rules.append(current_rule)
                
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line.startswith(('规则', 'rule', '---', '===')):
                        break
                    if not next_line or next_line.startswith('#') or next_line.startswith('//'):
                        i += 1
                        continue
                        
                    self._parse_rule_line(current_rule, next_line)
                    i += 1
            else:
                i += 1
                
        return self.rules
    
    def _parse_rule_line(self, rule: Rule, line: str):
        target_match = re.search(
            r'(?:针对|应用于|作用于|检查|target|check)\s*[:：]?\s*(.+)',
            line, re.IGNORECASE
        )
        if target_match:
            targets_str = target_match.group(1)
            for keyword, target_type in self.target_keywords.items():
                if keyword in targets_str:
                    rule.add_target(target_type)
            return
            
        message_match = re.search(
            r'(?:提示|消息|message|提示信息)\s*[:：]\s*(.+)',
            line, re.IGNORECASE
        )
        if message_match:
            rule.message = message_match.group(1).strip().strip('"\'')
            return
            
        for pattern, cond_type in self.condition_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                params = self._extract_condition_params(cond_type, match)
                rule.add_condition(cond_type, params)
                return
            
        if re.search(r'(当|如果|if|when)\s*(.+)', line, re.IGNORECASE):
            rule.add_condition('custom', {'expression': line})
    
    def _extract_condition_params(self, cond_type: str, match) -> Dict[str, Any]:
        params = {}
        
        if cond_type in ['max_args', 'max_lines', 'max_complexity', 'max_nesting', 'max_length']:
            params['value'] = int(match.group(1))
            
        elif cond_type == 'name_pattern':
            params['pattern'] = match.group(1)
            
        elif cond_type in ['forbidden_content', 'required_content']:
            content = match.group(1).strip()
            if content.startswith(('"', "'")):
                content = content[1:-1]
            params['content'] = content
            
        elif cond_type == 'hardcoded_secrets':
            params['enabled'] = True
            
        elif cond_type == 'no_print_or_log':
            params['enabled'] = True
            
        return params


class RuleChecker:
    def __init__(self, rules: List[Rule] = None):
        self.rules = rules or []
        self.violations = []
        
    def check_file(self, file_path: str) -> List[Dict[str, Any]]:
        self.violations = []
        
        if file_path.endswith('.py'):
            self._check_python_file(file_path)
        elif any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx']):
            self._check_javascript_file(file_path)
            
        return self.violations
    
    def _check_python_file(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            tree = ast.parse(content)
            
            for rule in self.rules:
                targets = rule.targets or ['function']
                
                for target in targets:
                    if target == 'function':
                        self._check_python_functions(tree, rule, file_path, lines)
                    elif target == 'class':
                        self._check_python_classes(tree, rule, file_path)
                    elif target == 'file':
                        self._check_file_content(content, rule, file_path, lines)
                    elif target == 'line':
                        self._check_lines(lines, rule, file_path)
        except Exception as e:
            pass
    
    def _check_python_functions(self, tree: ast.AST, rule: Rule, file_path: str, lines: List[str]):
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self._check_function_conditions(node, rule, file_path, lines):
                    self._add_violation(rule, file_path, node.lineno, node.name)
    
    def _check_function_conditions(self, node: ast.FunctionDef, rule: Rule, 
                                     file_path: str, lines: List[str]) -> bool:
        for condition in rule.conditions:
            cond_type = condition['type']
            params = condition['params']
            
            if cond_type == 'max_args':
                if len(node.args.args) > params['value']:
                    return True
                    
            elif cond_type == 'max_lines':
                func_lines = (node.end_line or node.lineno) - node.lineno + 1
                if func_lines > params['value']:
                    return True
                    
            elif cond_type == 'name_pattern':
                pattern = params['pattern']
                if not re.match(pattern, node.name):
                    return True
                    
            elif cond_type == 'max_nesting':
                depth = self._calculate_nesting_depth(node)
                if depth > params['value']:
                    return True
                    
            elif cond_type == 'hardcoded_secrets':
                func_source = ast.get_source_segment('\n'.join(lines), node) or ''
                if self._detect_hardcoded_secrets(func_source):
                    return True
                    
            elif cond_type == 'no_print_or_log':
                func_source = ast.get_source_segment('\n'.join(lines), node) or ''
                if re.search(r'\bprint\s*\(', func_source):
                    return True
                    
        return False
    
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
    
    def _check_python_classes(self, tree: ast.AST, rule: Rule, file_path: str):
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for condition in rule.conditions:
                    if condition['type'] == 'name_pattern':
                        pattern = condition['params']['pattern']
                        if not re.match(pattern, node.name):
                            self._add_violation(rule, file_path, node.lineno, node.name)
                            break
    
    def _check_file_content(self, content: str, rule: Rule, file_path: str, lines: List[str]):
        for condition in rule.conditions:
            cond_type = condition['type']
            params = condition['params']
            
            if cond_type == 'hardcoded_secrets':
                for i, line in enumerate(lines, 1):
                    if self._detect_hardcoded_secrets_in_line(line):
                        self._add_violation(rule, file_path, i, '硬编码敏感信息')
                        
            elif cond_type == 'forbidden_content':
                for i, line in enumerate(lines, 1):
                    if params['content'] in line:
                        self._add_violation(rule, file_path, i, f"包含禁止内容: {params['content']}")
                        
            elif cond_type == 'no_print_or_log':
                for i, line in enumerate(lines, 1):
                    if 'print(' in line:
                        self._add_violation(rule, file_path, i, '使用了print语句')
    
    def _check_lines(self, lines: List[str], rule: Rule, file_path: str):
        for condition in rule.conditions:
            if condition['type'] == 'max_length':
                max_len = condition['params']['value']
                for i, line in enumerate(lines, 1):
                    if len(line) > max_len:
                        self._add_violation(rule, file_path, i, f"行长度 {len(line)} > {max_len}")
    
    def _detect_hardcoded_secrets_in_line(self, line: str) -> bool:
        patterns = [
            r'password\s*[=:]\s*["\'][^"\']+["\']',
            r'secret\s*[=:]\s*["\'][^"\']+["\']',
            r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']',
            r'token\s*[=:]\s*["\'][^"\']+["\']',
            r'private[_-]?key\s*[=:]\s*["\'][^"\']+["\']'
        ]
        
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def _detect_hardcoded_secrets(self, content: str) -> bool:
        return self._detect_hardcoded_secrets_in_line(content)
    
    def _check_javascript_file(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for rule in self.rules:
                for condition in rule.conditions:
                    cond_type = condition['type']
                    params = condition['params']
                    
                    if cond_type == 'no_print_or_log':
                        for i, line in enumerate(lines, 1):
                            if 'console.log' in line:
                                self._add_violation(rule, file_path, i, '使用了console.log')
                    elif cond_type == 'hardcoded_secrets':
                        for i, line in enumerate(lines, 1):
                            if self._detect_hardcoded_secrets_in_line(line):
                                self._add_violation(rule, file_path, i, '硬编码敏感信息')
        except Exception as e:
            pass
    
    def _add_violation(self, rule: Rule, file_path: str, line: int, context: str = ''):
        self.violations.append({
            "type": "dsl_rule",
            "rule_name": rule.name,
            "severity": rule.severity,
            "message": rule.message,
            "file": file_path,
            "line": line,
            "context": context
        })
    
    def check_directory(self, directory: str) -> Dict[str, Any]:
        all_violations = []
        file_results = []
        
        supported_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx']
        
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in supported_extensions):
                    file_path = os.path.join(root, file)
                    violations = self.check_file(file_path)
                    if violations:
                        file_results.append({
                            "file": file_path,
                            "violations": violations
                        })
                        all_violations.extend(violations)
        
        summary = self._summarize_violations(all_violations)
        
        return {
            "file_results": file_results,
            "all_violations": all_violations,
            "summary": summary
        }
    
    def _summarize_violations(self, violations: List[Dict]) -> Dict[str, int]:
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for violation in violations:
            severity = violation.get("severity", "low")
            if severity in summary:
                summary[severity] += 1
        summary["total"] = len(violations)
        return summary
