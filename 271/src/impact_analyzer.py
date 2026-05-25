import os
import ast
import re
from typing import Dict, List, Any, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    name: str
    file: str
    start_line: int
    end_line: int
    calls: Set[str] = field(default_factory=set)
    called_by: Set[str] = field(default_factory=set)
    is_changed: bool = False
    complexity: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "file": self.file,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "calls": list(self.calls),
            "called_by": list(self.called_by),
            "is_changed": self.is_changed,
            "complexity": self.complexity
        }


@dataclass
class ImpactChain:
    source_func: str
    target_func: str
    path: List[str]
    depth: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_func,
            "target": self.target_func,
            "path": self.path,
            "depth": self.depth
        }


class ImpactAnalyzer:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.functions: Dict[str, FunctionInfo] = {}
        self.max_impact_depth = self.config.get('impact_analysis', {}).get('max_depth', 5)
        
    def analyze_directory(self, directory: str, changed_files: List[str] = None) -> Dict[str, Any]:
        self.functions = {}
        
        supported_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx']
        
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in supported_extensions):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, directory)
                    
                    is_changed = False
                    if changed_files:
                        is_changed = any(cf in file_path or cf in rel_path for cf in changed_files)
                    
                    if file_path.endswith('.py'):
                        self._analyze_python_file(file_path, rel_path, is_changed)
                    elif any(file.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx']):
                        self._analyze_javascript_file(file_path, rel_path, is_changed)
        
        self._build_call_graph()
        impact_chains = self._find_impact_chains()
        
        return {
            "functions": {name: func.to_dict() for name, func in self.functions.items()},
            "changed_functions": self._get_changed_functions(),
            "impact_chains": [chain.to_dict() for chain in impact_chains],
            "impact_summary": self._generate_impact_summary(impact_chains),
            "risk_assessment": self._assess_impact_risk(impact_chains)
        }
    
    def _analyze_python_file(self, file_path: str, rel_path: str, is_changed: bool):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_name = f"{rel_path}::{node.name}"
                    func_info = FunctionInfo(
                        name=func_name,
                        file=rel_path,
                        start_line=node.lineno,
                        end_line=node.end_line or node.lineno,
                        is_changed=is_changed
                    )
                    
                    func_info.calls = self._extract_python_calls(node)
                    func_info.complexity = self._calculate_function_complexity(node)
                    
                    self.functions[func_name] = func_info
        except Exception as e:
            pass
    
    def _extract_python_calls(self, node: ast.FunctionDef) -> Set[str]:
        calls = set()
        
        class CallVisitor(ast.NodeVisitor):
            def visit_Call(v_self, call_node):
                if isinstance(call_node.func, ast.Name):
                    calls.add(call_node.func.id)
                elif isinstance(call_node.func, ast.Attribute):
                    calls.add(call_node.func.attr)
                v_self.generic_visit(call_node)
        
        CallVisitor().visit(node)
        return calls
    
    def _calculate_function_complexity(self, node: ast.AST) -> int:
        complexity = 1
        decision_nodes = (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.IfExp, ast.Try)
        
        for child in ast.walk(node):
            if isinstance(child, decision_nodes):
                complexity += 1
        
        return complexity
    
    def _analyze_javascript_file(self, file_path: str, rel_path: str, is_changed: bool):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            func_patterns = [
                r'function\s+(\w+)\s*\([^)]*\)\s*\{',
                r'const\s+(\w+)\s*=\s*(?:async\s+)?function\s*\([^)]*\)\s*\{',
                r'const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*\{',
                r'(\w+)\s*:\s*(?:async\s+)?function\s*\([^)]*\)\s*\{',
                r'(\w+)\s*\([^)]*\)\s*:\s*[^{]+?\{'
            ]
            
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                for pattern in func_patterns:
                    match = re.search(pattern, line)
                    if match:
                        func_name = match.group(1)
                        if func_name in ['if', 'for', 'while', 'switch', 'catch']:
                            continue
                        
                        full_func_name = f"{rel_path}::{func_name}"
                        end_line = self._find_js_function_end(lines, i)
                        
                        func_body = '\n'.join(lines[i:end_line])
                        calls = self._extract_javascript_calls(func_body)
                        
                        func_info = FunctionInfo(
                            name=full_func_name,
                            file=rel_path,
                            start_line=i + 1,
                            end_line=end_line + 1,
                            is_changed=is_changed
                        )
                        func_info.calls = calls
                        func_info.complexity = self._calculate_js_complexity(func_body)
                        
                        self.functions[full_func_name] = func_info
                        break
        except Exception as e:
            pass
    
    def _find_js_function_end(self, lines: List[str], start_idx: int) -> int:
        brace_count = 0
        in_string = False
        string_char = ''
        
        for i in range(start_idx, len(lines)):
            line = lines[i]
            for char in line:
                if char in '"\'':
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                elif not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return i
        return len(lines) - 1
    
    def _extract_javascript_calls(self, func_body: str) -> Set[str]:
        calls = set()
        
        call_pattern = r'(\w+)\s*\('
        matches = re.findall(call_pattern, func_body)
        
        ignore_keywords = {'if', 'for', 'while', 'switch', 'catch', 'typeof', 
                          'instanceof', 'new', 'return', 'throw', 'await', 'async'}
        
        for match in matches:
            if match not in ignore_keywords:
                calls.add(match)
        
        return calls
    
    def _calculate_js_complexity(self, func_body: str) -> int:
        complexity = 1
        
        decision_patterns = [
            r'\bif\s*\(',
            r'\bfor\s*\(',
            r'\bwhile\s*\(',
            r'\bswitch\s*\(',
            r'\?\s*[^:]+:',
            r'\&\&',
            r'\|\|'
        ]
        
        for pattern in decision_patterns:
            complexity += len(re.findall(pattern, func_body))
        
        return complexity
    
    def _build_call_graph(self):
        for func_name, func_info in self.functions.items():
            for called_name in func_info.calls:
                for other_name in self.functions:
                    if called_name in other_name.split('::')[-1]:
                        if func_name != other_name:
                            self.functions[other_name].called_by.add(func_name)
    
    def _get_changed_functions(self) -> List[str]:
        return [name for name, func in self.functions.items() if func.is_changed]
    
    def _find_impact_chains(self) -> List[ImpactChain]:
        chains = []
        changed_funcs = self._get_changed_functions()
        
        for changed_func in changed_funcs:
            visited = set()
            self._trace_impact(changed_func, changed_func, [], 0, visited, chains)
        
        return chains
    
    def _trace_impact(self, source_func: str, current_func: str, path: List[str], 
                      depth: int, visited: Set[str], chains: List[ImpactChain]):
        if depth > self.max_impact_depth:
            return
        
        if current_func in visited:
            return
        
        visited.add(current_func)
        new_path = path + [current_func]
        
        if depth > 0:
            chains.append(ImpactChain(
                source_func=source_func,
                target_func=current_func,
                path=new_path,
                depth=depth
            ))
        
        func_info = self.functions.get(current_func)
        if func_info:
            for caller in func_info.called_by:
                self._trace_impact(source_func, caller, new_path, depth + 1, visited.copy(), chains)
    
    def _generate_impact_summary(self, chains: List[ImpactChain]) -> Dict[str, Any]:
        if not chains:
            return {
                "total_impacted_functions": 0,
                "max_impact_depth": 0,
                "average_impact_depth": 0,
                "impacted_files": []
            }
        
        impacted_funcs = set(chain.target_func for chain in chains)
        impacted_files = set()
        
        for func_name in impacted_funcs:
            func_info = self.functions.get(func_name)
            if func_info:
                impacted_files.add(func_info.file)
        
        depths = [chain.depth for chain in chains]
        
        return {
            "total_impacted_functions": len(impacted_funcs),
            "max_impact_depth": max(depths) if depths else 0,
            "average_impact_depth": round(sum(depths) / len(depths), 2) if depths else 0,
            "impacted_files": sorted(list(impacted_files)),
            "impacted_function_count": len(impacted_funcs),
            "chain_count": len(chains)
        }
    
    def _assess_impact_risk(self, chains: List[ImpactChain]) -> Dict[str, Any]:
        if not chains:
            return {
                "level": "low",
                "score": 0,
                "factors": {}
            }
        
        impacted_funcs = set(chain.target_func for chain in chains)
        max_depth = max(chain.depth for chain in chains) if chains else 0
        
        high_complexity_count = 0
        for func_name in impacted_funcs:
            func_info = self.functions.get(func_name)
            if func_info and func_info.complexity >= 10:
                high_complexity_count += 1
        
        score = 0
        score += len(impacted_funcs) * 2
        score += max_depth * 5
        score += high_complexity_count * 3
        
        if score >= 30:
            risk_level = "critical"
        elif score >= 15:
            risk_level = "high"
        elif score >= 5:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "level": risk_level,
            "score": score,
            "factors": {
                "impacted_functions": len(impacted_funcs),
                "max_impact_depth": max_depth,
                "high_complexity_functions": high_complexity_count
            }
        }
    
    def get_change_summary(self, directory: str, changed_files: List[str]) -> Dict[str, Any]:
        result = self.analyze_directory(directory, changed_files)
        
        return {
            "changed_files_count": len(changed_files),
            "changed_functions": result["changed_functions"],
            "impacted_functions_count": result["impact_summary"]["total_impacted_functions"],
            "impacted_files": result["impact_summary"]["impacted_files"],
            "risk_level": result["risk_assessment"]["level"],
            "impact_score": result["risk_assessment"]["score"]
        }
