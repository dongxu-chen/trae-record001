import os
import ast
from typing import Dict, List, Any, Optional, Tuple


class FunctionScope:
    def __init__(self, name: str, start_line: int, end_line: int = 0, parent: Optional['FunctionScope'] = None):
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.parent = parent
        self.children: List['FunctionScope'] = []
        self.nloc = 0
        self.ccn = 1
        self.token_count = 0
        self.parameter_count = 0
        self.decision_points = []
        self.entry_complexity = 1
        self.scope_depth = 0 if parent is None else parent.scope_depth + 1
        
    def add_child(self, child: 'FunctionScope'):
        self.children.append(child)
        
    def get_full_name(self) -> str:
        if self.parent:
            return f"{self.parent.get_full_name()}.{self.name}"
        return self.name
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "full_name": self.get_full_name(),
            "start_line": self.start_line,
            "end_line": self.end_line,
            "nloc": self.nloc,
            "ccn": self.ccn,
            "entry_complexity": self.entry_complexity,
            "token_count": self.token_count,
            "parameter_count": self.parameter_count,
            "scope_depth": self.scope_depth,
            "decision_points": self.decision_points,
            "children": [child.to_dict() for child in self.children]
        }


class ComplexityAnalyzer:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        complexity_config = self.config.get('complexity', {})
        self.max_ccn = complexity_config.get('max_ccn', 10)
        self.max_function_length = complexity_config.get('max_function_length', 50)
        self.max_nesting_depth = complexity_config.get('max_nesting_depth', 4)
        self.include_inner_functions = complexity_config.get('include_inner_functions', True)
        self.separate_entry_complexity = complexity_config.get('separate_entry_complexity', True)
        
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        if not file_path.endswith('.py'):
            return self._analyze_with_lizard(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
                lines = source.split('\n')
            
            tree = ast.parse(source)
            
            scopes = self._extract_scopes(tree)
            self._calculate_complexity(tree, lines, scopes)
            
            functions = []
            high_risk_functions = []
            
            for scope in scopes:
                self._flatten_scopes(scope, functions, high_risk_functions, file_path)
            
            all_ccn = [f["ccn"] for f in functions]
            all_entry_ccn = [f["entry_complexity"] for f in functions]
            
            return {
                "file": file_path,
                "nloc": sum(1 for line in lines if line.strip() and not line.strip().startswith('#')),
                "function_count": len(functions),
                "average_ccn": sum(all_ccn) / len(all_ccn) if all_ccn else 0,
                "max_ccn": max(all_ccn) if all_ccn else 0,
                "average_entry_complexity": sum(all_entry_ccn) / len(all_entry_ccn) if all_entry_ccn else 0,
                "max_entry_complexity": max(all_entry_ccn) if all_entry_ccn else 0,
                "functions": functions,
                "high_risk_functions": high_risk_functions,
                "scope_hierarchy": [scope.to_dict() for scope in scopes]
            }
            
        except Exception as e:
            return {
                "file": file_path,
                "error": str(e),
                "nloc": 0,
                "function_count": 0,
                "average_ccn": 0,
                "max_ccn": 0,
                "functions": [],
                "high_risk_functions": [],
                "scope_hierarchy": []
            }
    
    def _extract_scopes(self, tree: ast.AST) -> List[FunctionScope]:
        scopes = []
        scope_stack = []
        
        class ScopeVisitor(ast.NodeVisitor):
            def visit_FunctionDef(visitor_self, node):
                scope = FunctionScope(node.name, node.lineno, parent=scope_stack[-1] if scope_stack else None)
                scope.parameter_count = len(node.args.args)
                
                if scope_stack:
                    scope_stack[-1].add_child(scope)
                else:
                    scopes.append(scope)
                
                scope_stack.append(scope)
                visitor_self.generic_visit(node)
                scope_stack.pop()
                scope.end_line = node.end_line or node.lineno
            
            def visit_AsyncFunctionDef(visitor_self, node):
                visitor_self.visit_FunctionDef(node)
            
            def visit_ClassDef(visitor_self, node):
                scope_stack.append(None)
                visitor_self.generic_visit(node)
                if scope_stack:
                    scope_stack.pop()
        
        ScopeVisitor().visit(tree)
        return scopes
    
    def _calculate_complexity(self, tree: ast.AST, lines: List[str], scopes: List[FunctionScope]):
        def find_scope(line: int) -> Optional[FunctionScope]:
            def search_scopes(scope_list: List[FunctionScope]) -> Optional[FunctionScope]:
                for scope in scope_list:
                    if scope.start_line <= line <= scope.end_line:
                        child_result = search_scopes(scope.children)
                        return child_result or scope
                return None
            return search_scopes(scopes)
        
        decision_nodes = (
            ast.If, ast.For, ast.While, ast.And, ast.Or,
            ast.IfExp, ast.Try, ast.ExceptHandler
        )
        
        class ComplexityVisitor(ast.NodeVisitor):
            def generic_visit(visitor_self, node):
                if isinstance(node, decision_nodes) and hasattr(node, 'lineno'):
                    scope = find_scope(node.lineno)
                    if scope:
                        scope.ccn += 1
                        scope.decision_points.append({
                            "type": type(node).__name__,
                            "line": node.lineno
                        })
                
                for child in ast.iter_child_nodes(node):
                    visitor_self.visit(child)
        
        ComplexityVisitor().visit(tree)
        
        for scope in scopes:
            self._calculate_scope_metrics(scope, lines)
    
    def _calculate_scope_metrics(self, scope: FunctionScope, lines: List[str]):
        func_lines = lines[scope.start_line - 1:scope.end_line]
        
        child_start_lines = {child.start_line for child in scope.children}
        child_end_lines = {child.end_line for child in scope.children}
        
        exclusive_lines = []
        in_child = False
        child_end = 0
        
        for i, line in enumerate(func_lines, start=scope.start_line):
            if i in child_start_lines:
                in_child = True
            if i > child_end and in_child:
                in_child = False
            for child in scope.children:
                if i == child.end_line:
                    child_end = child.end_line
            
            if not in_child and line.strip() and not line.strip().startswith('#'):
                exclusive_lines.append(line)
        
        scope.nloc = len(exclusive_lines)
        scope.token_count = sum(len(line.split()) for line in exclusive_lines)
        
        if self.separate_entry_complexity:
            scope.entry_complexity = scope.ccn
        
        for child in scope.children:
            self._calculate_scope_metrics(child, lines)
    
    def _flatten_scopes(self, scope: FunctionScope, functions: List[Dict], 
                         high_risk: List[Dict], file_path: str):
        func_data = {
            "name": scope.name,
            "long_name": scope.get_full_name(),
            "start_line": scope.start_line,
            "end_line": scope.end_line,
            "nloc": scope.nloc,
            "ccn": scope.ccn,
            "entry_complexity": scope.entry_complexity,
            "token_count": scope.token_count,
            "parameter_count": scope.parameter_count,
            "scope_depth": scope.scope_depth,
            "filename": file_path,
            "is_inner_function": scope.parent is not None,
            "parent_function": scope.parent.get_full_name() if scope.parent else None
        }
        
        functions.append(func_data)
        
        issues = self._identify_issues(scope)
        if issues:
            risk_level = self._determine_risk_level(scope)
            high_risk.append({
                **func_data,
                "risk_level": risk_level,
                "issues": issues
            })
        
        if self.include_inner_functions:
            for child in scope.children:
                self._flatten_scopes(child, functions, high_risk, file_path)
    
    def _identify_issues(self, scope: FunctionScope) -> List[str]:
        issues = []
        if scope.ccn > self.max_ccn:
            issues.append(f"圈复杂度过高 ({scope.ccn} > {self.max_ccn})")
        if scope.entry_complexity > self.max_ccn and self.separate_entry_complexity:
            issues.append(f"入口复杂度过高 ({scope.entry_complexity} > {self.max_ccn})")
        if scope.nloc > self.max_function_length:
            issues.append(f"函数行数过多 ({scope.nloc} > {self.max_function_length})")
        if scope.scope_depth > self.max_nesting_depth:
            issues.append(f"嵌套过深 ({scope.scope_depth} > {self.max_nesting_depth})")
        if scope.parameter_count > 5:
            issues.append(f"参数过多 ({scope.parameter_count} 个参数)")
        return issues
    
    def _determine_risk_level(self, scope: FunctionScope) -> str:
        if scope.ccn > self.max_ccn * 1.5 or scope.scope_depth > self.max_nesting_depth:
            return "high"
        elif scope.ccn > self.max_ccn or scope.nloc > self.max_function_length:
            return "medium"
        return "low"
    
    def _analyze_with_lizard(self, file_path: str) -> Dict[str, Any]:
        import lizard
        try:
            analysis = lizard.analyze_file(file_path)
            functions = []
            high_risk = []
            
            for func in analysis.function_list:
                func_data = {
                    "name": func.name,
                    "long_name": func.long_name,
                    "start_line": func.start_line,
                    "end_line": func.end_line,
                    "nloc": func.nloc,
                    "ccn": func.cyclomatic_complexity,
                    "entry_complexity": func.cyclomatic_complexity,
                    "token_count": func.token_count,
                    "parameter_count": len(func.parameters),
                    "scope_depth": 0,
                    "filename": file_path,
                    "is_inner_function": False,
                    "parent_function": None
                }
                functions.append(func_data)
                
                if func.cyclomatic_complexity > self.max_ccn:
                    high_risk.append({
                        **func_data,
                        "risk_level": "high" if func.cyclomatic_complexity > self.max_ccn * 1.5 else "medium",
                        "issues": [f"圈复杂度过高 ({func.cyclomatic_complexity} > {self.max_ccn})"]
                    })
            
            return {
                "file": file_path,
                "nloc": analysis.nloc,
                "token_count": analysis.token_count,
                "function_count": len(functions),
                "average_ccn": sum(f["ccn"] for f in functions) / len(functions) if functions else 0,
                "max_ccn": max((f["ccn"] for f in functions), default=0),
                "functions": functions,
                "high_risk_functions": high_risk
            }
        except Exception as e:
            return {
                "file": file_path,
                "error": str(e),
                "nloc": 0,
                "function_count": 0,
                "average_ccn": 0,
                "functions": [],
                "high_risk_functions": []
            }
    
    def analyze_directory(self, directory: str) -> Dict[str, Any]:
        all_results = []
        total_nloc = 0
        total_functions = 0
        all_high_risk = []
        ccn_values = []
        entry_ccn_values = []
        
        supported_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.cs']
        
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in supported_extensions):
                    file_path = os.path.join(root, file)
                    result = self.analyze_file(file_path)
                    all_results.append(result)
                    
                    total_nloc += result.get("nloc", 0)
                    total_functions += result.get("function_count", 0)
                    all_high_risk.extend(result.get("high_risk_functions", []))
                    
                    for func in result.get("functions", []):
                        ccn_values.append(func["ccn"])
                        entry_ccn_values.append(func.get("entry_complexity", func["ccn"]))
        
        avg_ccn = sum(ccn_values) / len(ccn_values) if ccn_values else 0
        max_ccn = max(ccn_values) if ccn_values else 0
        avg_entry_ccn = sum(entry_ccn_values) / len(entry_ccn_values) if entry_ccn_values else 0
        
        summary = {
            "total_files": len(all_results),
            "total_nloc": total_nloc,
            "total_functions": total_functions,
            "average_ccn": round(avg_ccn, 2),
            "max_ccn": max_ccn,
            "average_entry_complexity": round(avg_entry_ccn, 2),
            "high_risk_count": len(all_high_risk),
            "risk_level": self._calculate_risk_level(len(all_high_risk), total_functions),
            "separate_entry_complexity": self.separate_entry_complexity,
            "include_inner_functions": self.include_inner_functions
        }
        
        return {
            "summary": summary,
            "file_results": all_results,
            "high_risk_functions": all_high_risk
        }
    
    def _calculate_risk_level(self, high_risk_count: int, total_functions: int) -> str:
        if total_functions == 0:
            return "low"
        
        risk_ratio = high_risk_count / total_functions
        
        if risk_ratio > 0.3:
            return "critical"
        elif risk_ratio > 0.15:
            return "high"
        elif risk_ratio > 0.05:
            return "medium"
        else:
            return "low"
