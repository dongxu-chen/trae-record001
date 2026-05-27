"""SQL注入检测规则"""

import re
from typing import Any, Dict, List, Optional, Set

from ..parsers.base_parser import (
    ASTNode,
    Language,
    Severity,
    SourceSpan,
    Vulnerability,
    VulnerabilityType,
)
from .rule_engine import BaseRule


SQL_KEYWORDS = [
    "SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
    "ALTER", "EXEC", "EXECUTE", "UNION", "WHERE", "FROM", "TABLE",
    "INTO", "VALUES", "SET", "AND", "OR", "NOT", "NULL", "LIKE",
    "BETWEEN", "IN", "IS", "ORDER", "GROUP", "BY", "HAVING", "LIMIT",
    "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE", "COMMIT",
    "ROLLBACK", "SAVEPOINT",
]


SQL_FUNCTIONS = [
    "execute", "executeQuery", "executeUpdate", "query", "rawQuery",
    "executemany", "callproc", "prepareStatement", "createStatement",
    "run", "all", "fetch", "fetchone", "fetchall",
]


DANGEROUS_DB_APIS = {
    "python": ["execute", "executemany", "executescript", "raw", "raw_query"],
    "java": ["executeQuery", "executeUpdate", "execute", "executeBatch", "prepareStatement", "createStatement", "addBatch"],
    "javascript": ["query", "execute", "run", "all", "get", "prepare", "exec"],
}


TABLE_NAME_PATTERN = re.compile(
    r'(?:FROM|INTO|UPDATE|TABLE|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)',
    re.IGNORECASE,
)


DYNAMIC_TABLE_PATTERN = re.compile(
    r'(?:FROM|INTO|UPDATE|TABLE|JOIN)\s*[\+\%\{\}\$]',
    re.IGNORECASE,
)


DEFAULT_TABLE_WHITELIST: Set[str] = {
    "users", "user", "products", "product", "orders", "order",
    "posts", "post", "comments", "comment", "categories", "category",
    "tags", "tag", "sessions", "session", "tokens", "token",
    "files", "file", "images", "image", "documents", "document",
    "logs", "log", "config", "settings", "roles", "role",
    "permissions", "permission", "invoices", "invoice", "items", "item",
    "cart", "carts", "addresses", "address", "profiles", "profile",
    "reviews", "review", "ratings", "rating", "favorites", "favorite",
    "notifications", "notification", "messages", "message",
    "activities", "activity", "events", "event", "audit", "audits",
}


class SQLInjectionRule(BaseRule):
    """检测SQL注入漏洞"""

    rule_name = "sql_injection"
    description = "检测SQL语句中的字符串拼接，可能导致SQL注入漏洞"
    vuln_type = VulnerabilityType.SQL_INJECTION
    severity = Severity.CRITICAL
    supported_languages = [Language.PYTHON, Language.JAVA, Language.JAVASCRIPT]

    def __init__(self, table_whitelist: Optional[Set[str]] = None):
        super().__init__()
        self.table_whitelist = table_whitelist or DEFAULT_TABLE_WHITELIST

    def update_table_whitelist(self, tables: List[str]):
        """更新表名白名单"""
        self.table_whitelist.update(tables)

    def detect(self, ast_root: ASTNode, source_code: str, file_path: str) -> List[Vulnerability]:
        vulnerabilities: List[Vulnerability] = []
        self._detect_in_call_nodes(ast_root, source_code, file_path, vulnerabilities)
        self._detect_in_concatenations(ast_root, source_code, file_path, vulnerabilities)
        self._detect_by_source_analysis(source_code, file_path, vulnerabilities)
        self._detect_dynamic_table_names(source_code, file_path, vulnerabilities)
        return vulnerabilities

    def _detect_in_call_nodes(self, ast_root, source_code, file_path, vulns):
        language = self._infer_language_from_path(file_path)
        dangerous_funcs = DANGEROUS_DB_APIS.get(language, [])

        call_nodes = self._find_all_nodes_by_type(ast_root, ["Call", "MethodInvocation", "CallExpression"])

        for call_node in call_nodes:
            func_name = call_node.attributes.get("function_name", "")
            if func_name.lower() not in [f.lower() for f in dangerous_funcs]:
                continue

            for key, value in call_node.attributes.items():
                if key.startswith("arg_") and key.endswith("_is_string") and value:
                    arg_idx = key.split("_")[1]
                    arg_val = call_node.attributes.get(f"arg_{arg_idx}_value", "")
                    if self._contains_sql_pattern(arg_val):
                        if self._has_user_input(call_node, ast_root):
                            span = call_node.source_span
                            auto_fixable = not self._has_dynamic_table(arg_val)
                            fix = self._suggest_fix(call_node, source_code, language, auto_fixable)
                            vulns.append(
                                self._create_vulnerability(
                                    f"SQL注入风险: 在{func_name}()调用中使用了字符串拼接SQL查询",
                                    span,
                                    {"function": func_name, "query": arg_val[:200]},
                                    fix,
                                    confidence=0.9,
                                    auto_fixable=auto_fixable,
                                )
                            )

    def _detect_in_concatenations(self, ast_root, source_code, file_path, vulns):
        concat_nodes = self._find_all_nodes_by_type(ast_root, ["BinOp", "BinaryOperation", "BinaryExpression"])

        for concat_node in concat_nodes:
            if not concat_node.attributes.get("is_concatenation"):
                continue

            raw = concat_node.raw_text.upper()
            if not self._contains_sql_pattern(raw):
                continue

            if self._has_user_input(concat_node, ast_root):
                span = concat_node.source_span
                auto_fixable = not self._has_dynamic_table(concat_node.raw_text)
                fix = self._suggest_fix(
                    concat_node, source_code, self._infer_language_from_path(file_path), auto_fixable
                )
                vulns.append(
                    self._create_vulnerability(
                        "SQL注入风险: SQL语句使用了字符串拼接而非参数化查询",
                        span,
                        {"raw_code": raw[:200]},
                        fix,
                        confidence=0.85,
                        auto_fixable=auto_fixable,
                    )
                )

    def _detect_by_source_analysis(self, source_code, file_path, vulns):
        lines = source_code.splitlines()
        sql_pattern = re.compile(
            r"(?:execute|executeQuery|executeUpdate|query|run)\s*\([^)]*['\"](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)",
            re.IGNORECASE,
        )

        for i, line in enumerate(lines, 1):
            if sql_pattern.search(line):
                if re.search(r'\$\{|\+|%|\.format|string\.format', line):
                    span = SourceSpan(file_path, i, i)
                    auto_fixable = not self._has_dynamic_table(line)
                    fix = self._suggest_fix_by_line(line, self._infer_language_from_path(file_path), auto_fixable)
                    vulns.append(
                        self._create_vulnerability(
                            "SQL注入风险: 检测到动态SQL拼接",
                            span,
                            {"line": line.strip()[:200]},
                            fix,
                            confidence=0.8,
                            auto_fixable=auto_fixable,
                        )
                    )

    def _detect_dynamic_table_names(self, source_code, file_path, vulns):
        """检测动态表名使用"""
        lines = source_code.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            dynamic_matches = DYNAMIC_TABLE_PATTERN.findall(stripped)
            if not dynamic_matches:
                continue

            used_tables = TABLE_NAME_PATTERN.findall(stripped)
            unlisted_tables = []
            for tbl in used_tables:
                if tbl.lower() not in [t.lower() for t in self.table_whitelist]:
                    unlisted_tables.append(tbl)

            span = SourceSpan(file_path, i, i)

            if unlisted_tables:
                vulns.append(
                    self._create_vulnerability(
                        f"SQL注入高风险: 动态表名使用了不在白名单中的表: {', '.join(unlisted_tables)}。"
                        f"此漏洞无法自动修复，需人工处理。",
                        span,
                        {
                            "line": stripped[:200],
                            "dynamic_tables": unlisted_tables,
                            "whitelist": sorted(list(self.table_whitelist)),
                        },
                        self._suggest_dynamic_table_fix(unlisted_tables),
                        confidence=0.95,
                        auto_fixable=False,
                    )
                )
            else:
                vulns.append(
                    self._create_vulnerability(
                        "SQL注入警告: 使用了动态表名，虽然表名在白名单中，但仍需注意验证。",
                        span,
                        {"line": stripped[:200], "used_tables": used_tables},
                        self._suggest_dynamic_table_best_practice(),
                        confidence=0.7,
                        auto_fixable=False,
                    )
                )

    def _has_dynamic_table(self, query: str) -> bool:
        """检查查询中是否包含动态表名"""
        return bool(DYNAMIC_TABLE_PATTERN.search(query))

    def _contains_sql_pattern(self, text: str) -> bool:
        text_upper = text.upper()
        for kw in SQL_KEYWORDS:
            if re.search(r'\b' + kw + r'\b', text_upper):
                return True
        return False

    def _has_user_input(self, node: ASTNode, ast_root: ASTNode) -> bool:
        for key, value in node.attributes.items():
            if key.startswith("arg_") and key.endswith("_is_variable") and value:
                return True

        if re.search(r'\$\{', node.raw_text):
            return True
        if re.search(r'\{.*?}', node.raw_text) and "SELECT" in node.raw_text.upper():
            return True
        if '+' in node.raw_text and ('"' in node.raw_text or "'" in node.raw_text):
            return True

        return False

    def _find_all_nodes_by_type(self, node: ASTNode, types: List[str]) -> List[ASTNode]:
        results: List[ASTNode] = []
        if node.node_type in types:
            results.append(node)
        for child in node.children:
            results.extend(self._find_all_nodes_by_type(child, types))
        return results

    def _infer_language_from_path(self, file_path: str) -> str:
        ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
        ext_map = {"py": "python", "java": "java", "js": "javascript", "jsx": "javascript", "ts": "javascript", "tsx": "javascript"}
        return ext_map.get(ext.lower(), "python")

    def _suggest_fix(self, node: ASTNode, source_code: str, language: str, auto_fixable: bool = True) -> str:
        if not auto_fixable:
            return self._suggest_non_auto_fix()

        raw = node.raw_text
        if language == "python":
            return (
                "使用参数化查询替代字符串拼接:\n"
                "  cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))\n"
                "  或使用命名参数: cursor.execute('SELECT * FROM users WHERE id = :id', {'id': user_id})"
            )
        elif language == "java":
            return (
                "使用PreparedStatement替代Statement:\n"
                "  PreparedStatement stmt = conn.prepareStatement('SELECT * FROM users WHERE id = ?');\n"
                "  stmt.setInt(1, userId);\n"
                "  ResultSet rs = stmt.executeQuery();"
            )
        else:
            return (
                "使用参数化查询替代字符串拼接:\n"
                "  db.query('SELECT * FROM users WHERE id = ?', [userId])"
            )

    def _suggest_fix_by_line(self, line: str, language: str, auto_fixable: bool = True) -> str:
        return self._suggest_fix(
            ASTNode(node_type="", source_span=SourceSpan("", 0, 0), raw_text=line),
            "",
            language,
            auto_fixable,
        )

    def _suggest_non_auto_fix(self) -> str:
        return (
            "🔴 此漏洞无法自动修复，需要人工处理:\n"
            "  1. 将表名/列名限制在白名单内验证\n"
            "  2. 避免使用字符串拼接动态表名\n"
            "  3. 使用ORM框架的安全API操作数据库\n"
            "  4. 如需动态表名，使用严格的白名单验证: if table_name in ALLOWED_TABLES:"
        )

    def _suggest_dynamic_table_fix(self, unlisted_tables: List[str]) -> str:
        return (
            f"🔴 检测到动态表名使用了不在白名单中的表: {', '.join(unlisted_tables)}\n"
            "  需要人工处理:\n"
            "  1. 确认这些表名是否合法\n"
            "  2. 将合法表名添加到白名单配置\n"
            "  3. 使用白名单验证动态表名: if table_name in ALLOWED_TABLES:\n"
            "  4. 避免直接拼接用户输入到表名位置"
        )

    def _suggest_dynamic_table_best_practice(self) -> str:
        return (
            "⚠️  动态表名最佳实践:\n"
            "  1. 始终使用白名单验证表名\n"
            "  2. 示例: ALLOWED_TABLES = {'users', 'orders', 'products'}\n"
            "  3. 验证: if table_name not in ALLOWED_TABLES: raise ValueError('Invalid table')\n"
            "  4. 考虑使用ORM框架替代动态SQL"
        )
