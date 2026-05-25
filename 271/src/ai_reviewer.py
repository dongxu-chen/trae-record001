import os
import re
import ast
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ReviewComment:
    file: str
    line: int
    severity: str
    category: str
    title: str
    message: str
    suggestion: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "suggestion": self.suggestion,
            "confidence": self.confidence
        }


@dataclass
class ReviewPattern:
    id: str
    name: str
    category: str
    severity: str
    description: str
    patterns: List[str]
    suggestion: str
    examples: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.8


class AIReviewer:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.patterns: List[ReviewPattern] = []
        self._init_common_patterns()
        self._load_patterns_from_config()
        
    def _init_common_patterns(self):
        self.patterns.extend([
            ReviewPattern(
                id="null_check_missing",
                name="缺少空值检查",
                category="best_practice",
                severity="medium",
                description="函数参数或返回值缺少空值/None检查",
                patterns=[
                    r'def\s+\w+\s*\([^)]*\)\s*:[^{]*{?(?:\n(?!\s*if\s+.*?(?:is\s+None|==\s*None|not\s+))',
                ],
                suggestion="建议添加对None值的检查，使用`if x is None:`进行判断",
                examples={
                    "bad": "def process(data):\n    return data.value",
                    "good": "def process(data):\n    if data is None:\n        return None\n    return data.value"
                },
                confidence=0.75
            ),
            
            ReviewPattern(
                id="magic_numbers",
                name="魔术数字",
                category="code_quality",
                severity="low",
                description="代码中使用了未定义的魔术数字",
                patterns=[
                    r'(?:if|for|while|return|==|!=|>|<|>=|<=)\s*(?:[a-zA-Z_]\w*\s*[+\-*/%]?\s*)*\b(?!0\b|1\b|2\b)[3-9]\d*\b',
                ],
                suggestion="建议将数字定义为常量，使用有意义的命名",
                examples={
                    "bad": "if status == 3:",
                    "good": "STATUS_COMPLETED = 3\nif status == STATUS_COMPLETED:"
                },
                confidence=0.8
            ),
            
            ReviewPattern(
                id="try_catch_too_broad",
                name="异常捕获过宽",
                category="error_handling",
                severity="high",
                description="使用了过于宽泛的异常捕获",
                patterns=[
                    r'except\s*(?:Exception|BaseException|:)',
                    r'except\s*:',
                ],
                suggestion="建议捕获具体的异常类型，而不是使用宽泛的Exception",
                examples={
                    "bad": "try:\n    risky()\nexcept:\n    pass",
                    "good": "try:\n    risky()\nexcept ValueError as e:\n    logger.error(f\"Invalid value: {e}\")"
                },
                confidence=0.9
            ),
            
            ReviewPattern(
                id="unused_import",
                name="未使用的导入",
                category="code_quality",
                severity="low",
                description="存在未使用的导入语句",
                patterns=[],
                suggestion="移除未使用的导入，保持代码整洁",
                confidence=0.95
            ),
            
            ReviewPattern(
                id="hardcoded_secrets",
                name="硬编码敏感信息",
                category="security",
                severity="critical",
                description="检测到硬编码的密码、密钥等敏感信息",
                patterns=[
                    r'(?:password|passwd|pwd|secret|api_?key|token|private_?key)\s*[=:]\s*["\'][^"\']+["\']',
                ],
                suggestion="请使用环境变量或配置文件存储敏感信息，不要硬编码",
                confidence=0.9
            ),
            
            ReviewPattern(
                id="insecure_random",
                name="不安全的随机数",
                category="security",
                severity="high",
                description="在安全敏感场景使用了伪随机数",
                patterns=[
                    r'import\s+random\b',
                    r'random\.(?:random|randint|choice|shuffle)',
                ],
                suggestion="在安全场景下请使用secrets模块而非random模块",
                examples={
                    "bad": "import random\ntoken = random.randint(1000, 9999)",
                    "good": "import secrets\ntoken = secrets.randbelow(9000) + 1000"
                },
                confidence=0.85
            ),
            
            ReviewPattern(
                id="sql_injection_risk",
                name="SQL注入风险",
                category="security",
                severity="critical",
                description="存在SQL注入风险的字符串拼接",
                patterns=[
                    r'execute\s*\(\s*f["\']',
                    r'execute\s*\(\s*["\'][^"\']*%\s*\+?\s*\w+',
                    r'(?:sql|query)\s*[=:]\s*f["\']',
                ],
                suggestion="请使用参数化查询而非字符串拼接",
                examples={
                    "bad": f"query = f\"SELECT * FROM users WHERE id = {user_id}\"\ncursor.execute(query)",
                    "good": "query = \"SELECT * FROM users WHERE id = ?\"\ncursor.execute(query, (user_id,))"
                },
                confidence=0.8
            ),
            
            ReviewPattern(
                id="missing_docstring",
                name="缺少文档字符串",
                category="documentation",
                severity="low",
                description="公共函数/类缺少文档字符串",
                patterns=[],
                suggestion="建议为公共API添加文档字符串，说明参数、返回值和用途",
                confidence=0.7
            ),
            
            ReviewPattern(
                id="print_statement",
                name="调试打印语句",
                category="best_practice",
                severity="low",
                description="代码中包含print调试语句",
                patterns=[
                    r'\bprint\s*\(',
                ],
                suggestion="建议使用logging模块替代print，或在提交前删除调试语句",
                confidence=0.9
            ),
            
            ReviewPattern(
                id="todo_comment",
                name="待办事项",
                category="task",
                severity="info",
                description="代码中存在TODO注释",
                patterns=[
                    r'#\s*(?:TODO|FIXME|XXX|BUG|HACK)\b',
                ],
                suggestion="建议在合并前完成或记录这些待办事项",
                confidence=1.0
            ),
            
            ReviewPattern(
                id="nested_too_deep",
                name="嵌套过深",
                category="code_quality",
                severity="medium",
                description="代码嵌套层级过深",
                patterns=[],
                suggestion="考虑提取子函数或使用提前返回来降低嵌套深度",
                confidence=0.8
            ),
            
            ReviewPattern(
                id="function_too_long",
                name="函数过长",
                category="code_quality",
                severity="medium",
                description="函数体过长",
                patterns=[],
                suggestion="考虑将长函数拆分为多个小函数，每个函数只做一件事",
                confidence=0.85
            ),
            
            ReviewPattern(
                id="too_many_args",
                name="参数过多",
                category="code_quality",
                severity="medium",
                description="函数参数数量过多",
                patterns=[],
                suggestion="考虑将相关参数封装为数据类或字典",
                confidence=0.8
            ),
            
            ReviewPattern(
                id="inconsistent_naming",
                name="命名不一致",
                category="convention",
                severity="low",
                description="命名风格不一致",
                patterns=[],
                suggestion="建议遵循项目命名规范，Python使用snake_case",
                confidence=0.7
            ),
            
            ReviewPattern(
                id="race_condition_risk",
                name="竞态条件风险",
                category="concurrency",
                severity="high",
                description="并发场景下可能存在竞态条件",
                patterns=[
                    r'global\s+\w+.*\n.*=',
                    r'(?:\+=|-=|\*=|\/=)\s*\w+',
                ],
                suggestion="多线程/多进程共享状态时请使用锁机制",
                confidence=0.6
            ),
            
            ReviewPattern(
                id="resource_leak_risk",
                name="资源泄漏风险",
                category="resource_management",
                severity="medium",
                description="可能存在资源未正确释放的问题",
                patterns=[
                    r'open\s*\([^)]*\)\s*(?!\s*as\s+)',
                ],
                suggestion="建议使用with语句来管理文件等资源",
                examples={
                    "bad": "f = open('file.txt')\ndata = f.read()",
                    "good": "with open('file.txt') as f:\n    data = f.read()"
                },
                confidence=0.85
            ),
            
            ReviewPattern(
                id="inefficient_loop",
                name="低效循环",
                category="performance",
                severity="low",
                description="可能存在性能改进空间的循环",
                patterns=[
                    r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(',
                ],
                suggestion="考虑使用enumerate或更Pythonic的迭代方式",
                examples={
                    "bad": "for i in range(len(items)):\n    print(items[i])",
                    "good": "for item in items:\n    print(item)"
                },
                confidence=0.8
            ),
            
            ReviewPattern(
                id="bare_except_pass",
                name="静默忽略异常",
                category="error_handling",
                severity="high",
                description="捕获异常后直接pass，未做任何处理",
                patterns=[
                    r'except[^:]*:\s*\n\s*pass\b',
                ],
                suggestion="至少应该记录日志，不要静默吞掉异常",
                examples={
                    "bad": "try:\n    risky()\nexcept:\n    pass",
                    "good": "try:\n    risky()\nexcept Error as e:\n    logger.warning(f\"Operation failed: {e}\")"
                },
                confidence=0.95
            ),
            
            ReviewPattern(
                id="mutable_default_arg",
                name="可变默认参数",
                category="best_practice",
                severity="high",
                description="函数使用了可变对象作为默认参数",
                patterns=[
                    r'def\s+\w+\s*\([^)]*=\s*(?:\{\}|\[\])',
                ],
                suggestion="可变默认参数会在函数调用间共享，使用None作为默认值",
                examples={
                    "bad": "def add_item(item, items=[]):\n    items.append(item)\n    return items",
                    "good": "def add_item(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)\n    return items"
                },
                confidence=0.95
            ),
        ])
    
    def _load_patterns_from_config(self):
        custom_patterns = self.config.get('ai_review', {}).get('custom_patterns', [])
        for pattern_config in custom_patterns:
            self.patterns.append(ReviewPattern(
                id=pattern_config.get('id', 'custom'),
                name=pattern_config.get('name', 'Custom Pattern'),
                category=pattern_config.get('category', 'custom'),
                severity=pattern_config.get('severity', 'medium'),
                description=pattern_config.get('description', ''),
                patterns=pattern_config.get('patterns', []),
                suggestion=pattern_config.get('suggestion', ''),
                confidence=pattern_config.get('confidence', 0.7)
            ))
    
    def review_file(self, file_path: str, analysis_results: Dict[str, Any] = None) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        if not os.path.exists(file_path):
            return comments
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception:
            return comments
        
        rel_path = os.path.basename(file_path)
        
        if file_path.endswith('.py'):
            comments.extend(self._review_python_file(file_path, rel_path, content, lines, analysis_results))
        elif any(file_path.endswith(ext) for ext in ['.js', '.jsx', '.ts', '.tsx']):
            comments.extend(self._review_javascript_file(file_path, rel_path, content, lines))
        
        comments.extend(self._apply_regex_patterns(file_path, rel_path, content, lines))
        comments.extend(self._analyze_context_issues(file_path, rel_path, lines, analysis_results))
        
        return self._deduplicate_comments(comments)
    
    def _review_python_file(self, file_path: str, rel_path: str, content: str, 
                            lines: List[str], analysis_results: Dict[str, Any] = None) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        try:
            tree = ast.parse(content)
        except Exception:
            return comments
        
        comments.extend(self._check_docstrings(rel_path, tree))
        comments.extend(self._check_function_length(rel_path, tree, lines))
        comments.extend(self._check_nesting_depth(rel_path, tree))
        comments.extend(self._check_mutable_default_args(rel_path, tree))
        comments.extend(self._check_unused_imports(rel_path, content, lines))
        
        return comments
    
    def _check_docstrings(self, file_path: str, tree: ast.AST) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith('_'):
                    continue
                
                docstring = ast.get_docstring(node)
                if not docstring:
                    comments.append(ReviewComment(
                        file=file_path,
                        line=node.lineno,
                        severity="low",
                        category="documentation",
                        title="缺少文档字符串",
                        message=f"{node.name} 缺少文档字符串",
                        suggestion="建议添加Google风格或NumPy风格的文档字符串",
                        confidence=0.7
                    ))
        
        return comments
    
    def _check_function_length(self, file_path: str, tree: ast.AST, lines: List[str]) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = (node.end_line or node.lineno) - node.lineno + 1
                if func_lines > 50:
                    comments.append(ReviewComment(
                        file=file_path,
                        line=node.lineno,
                        severity="medium",
                        category="code_quality",
                        title="函数过长",
                        message=f"函数 {node.name} 有 {func_lines} 行，超过建议的50行",
                        suggestion="考虑将函数拆分为多个更小的函数",
                        confidence=0.85
                    ))
        
        return comments
    
    def _check_nesting_depth(self, file_path: str, tree: ast.AST) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        def check_nesting(node: ast.AST, depth: int = 0, max_depth: List[int] = None) -> int:
            if max_depth is None:
                max_depth = [0]
            
            max_depth[0] = max(max_depth[0], depth)
            
            nested_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try)
            
            for child in ast.iter_child_nodes(node):
                if isinstance(child, nested_nodes):
                    check_nesting(child, depth + 1, max_depth)
                else:
                    check_nesting(child, depth, max_depth)
            
            return max_depth[0]
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                max_depth = check_nesting(node)
                if max_depth > 4:
                    comments.append(ReviewComment(
                        file=file_path,
                        line=node.lineno,
                        severity="medium",
                        category="code_quality",
                        title="嵌套过深",
                        message=f"函数 {node.name} 最大嵌套深度为 {max_depth}",
                        suggestion="考虑使用提前返回或提取子函数来降低嵌套",
                        confidence=0.8
                    ))
        
        return comments
    
    def _check_mutable_default_args(self, file_path: str, tree: ast.AST) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        comments.append(ReviewComment(
                            file=file_path,
                            line=node.lineno,
                            severity="high",
                            category="best_practice",
                            title="可变默认参数",
                            message=f"函数 {node.name} 使用了可变对象作为默认参数",
                            suggestion="使用 None 作为默认值，在函数内部初始化可变对象",
                            confidence=0.95
                        ))
        
        return comments
    
    def _check_unused_imports(self, file_path: str, content: str, lines: List[str]) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        try:
            tree = ast.parse(content)
            
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add((alias.name.split('.')[0], node.lineno))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add((node.module.split('.')[0], node.lineno))
            
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
            
            for import_name, line_no in imports:
                if import_name not in used_names:
                    comments.append(ReviewComment(
                        file=file_path,
                        line=line_no,
                        severity="low",
                        category="code_quality",
                        title="未使用的导入",
                        message=f"导入的 {import_name} 未被使用",
                        suggestion="移除未使用的导入以保持代码整洁",
                        confidence=0.9
                    ))
        except Exception:
            pass
        
        return comments
    
    def _review_javascript_file(self, file_path: str, rel_path: str, content: str, 
                                 lines: List[str]) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        for i, line in enumerate(lines, 1):
            if 'console.log' in line and not line.strip().startswith('//'):
                comments.append(ReviewComment(
                    file=rel_path,
                    line=i,
                    severity="low",
                    category="best_practice",
                    title="调试打印语句",
                    message="代码中包含 console.log 调试语句",
                    suggestion="生产环境应使用适当的日志库",
                    confidence=0.9
                ))
            
            if 'eval(' in line:
                comments.append(ReviewComment(
                    file=rel_path,
                    line=i,
                    severity="critical",
                    category="security",
                    title="不安全的eval使用",
                    message="检测到 eval() 的使用",
                    suggestion="避免使用 eval()，可能存在代码注入风险",
                    confidence=0.95
                ))
        
        return comments
    
    def _apply_regex_patterns(self, file_path: str, rel_path: str, content: str, 
                               lines: List[str]) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        for pattern in self.patterns:
            if not pattern.patterns:
                continue
            
            for regex in pattern.patterns:
                for i, line in enumerate(lines, 1):
                    if re.search(regex, line, re.IGNORECASE):
                        comments.append(ReviewComment(
                            file=rel_path,
                            line=i,
                            severity=pattern.severity,
                            category=pattern.category,
                            title=pattern.name,
                            message=pattern.description,
                            suggestion=pattern.suggestion,
                            confidence=pattern.confidence
                        ))
        
        return comments
    
    def _analyze_context_issues(self, file_path: str, rel_path: str, lines: List[str],
                                  analysis_results: Dict[str, Any] = None) -> List[ReviewComment]:
        comments: List[ReviewComment] = []
        
        if analysis_results:
            complexity_data = analysis_results.get('complexity', {})
            for func in complexity_data.get('high_risk_functions', []):
                if func.get('ccn', 0) > 15:
                    comments.append(ReviewComment(
                        file=rel_path,
                        line=func.get('start_line', 0),
                        severity="high",
                        category="complexity",
                        title="高复杂度函数",
                        message=f"函数 {func.get('name')} 圈复杂度为 {func.get('ccn')}",
                        suggestion="强烈建议重构此函数，拆分复杂逻辑",
                        confidence=0.9
                    ))
        
        return comments
    
    def _deduplicate_comments(self, comments: List[ReviewComment]) -> List[ReviewComment]:
        seen = set()
        unique = []
        
        for comment in comments:
            key = (comment.file, comment.line, comment.title)
            if key not in seen:
                seen.add(key)
                unique.append(comment)
        
        return sorted(unique, key=lambda c: (c.severity == 'critical', c.severity == 'high', 
                                              c.severity == 'medium', c.severity == 'low'),
                      reverse=True)
    
    def review_directory(self, directory: str, analysis_results: Dict[str, Any] = None) -> Dict[str, Any]:
        all_comments: List[ReviewComment] = []
        file_comments: Dict[str, List[ReviewComment]] = {}
        
        supported_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx']
        
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in supported_extensions):
                    file_path = os.path.join(root, file)
                    comments = self.review_file(file_path, analysis_results)
                    if comments:
                        file_comments[file_path] = comments
                        all_comments.extend(comments)
        
        summary = self._generate_review_summary(all_comments)
        
        return {
            "all_comments": [c.to_dict() for c in all_comments],
            "file_comments": {k: [c.to_dict() for c in v] for k, v in file_comments.items()},
            "summary": summary,
            "patterns_used": [p.name for p in self.patterns]
        }
    
    def _generate_review_summary(self, comments: List[ReviewComment]) -> Dict[str, Any]:
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        by_category: Dict[str, int] = {}
        
        for comment in comments:
            severity = comment.severity
            if severity in by_severity:
                by_severity[severity] += 1
            
            category = comment.category
            by_category[category] = by_category.get(category, 0) + 1
        
        total = len(comments)
        score = (by_severity['critical'] * 10 + by_severity['high'] * 5 + 
                 by_severity['medium'] * 2 + by_severity['low'] * 1)
        
        if score >= 30:
            overall_grade = "F"
        elif score >= 20:
            overall_grade = "D"
        elif score >= 10:
            overall_grade = "C"
        elif score >= 5:
            overall_grade = "B"
        else:
            overall_grade = "A"
        
        return {
            "total_comments": total,
            "by_severity": by_severity,
            "by_category": by_category,
            "risk_score": score,
            "overall_grade": overall_grade
        }
    
    def get_suggested_fixes(self, comment: ReviewComment) -> Dict[str, Any]:
        fixes = []
        
        for pattern in self.patterns:
            if pattern.name == comment.title and pattern.examples:
                fixes.append({
                    "before": pattern.examples.get("bad", ""),
                    "after": pattern.examples.get("good", ""),
                    "description": pattern.suggestion
                })
        
        return {
            "comment": comment.to_dict(),
            "suggested_fixes": fixes
        }
