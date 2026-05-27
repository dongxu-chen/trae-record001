"""JavaScript AST解析器"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_parser import (
    ASTNode,
    BaseParser,
    Language,
    SourceSpan,
    Vulnerability,
)


class JavaScriptParser(BaseParser):
    """JavaScript源代码解析器，基于esprima库"""

    language = Language.JAVASCRIPT

    def __init__(self):
        super().__init__()
        self._source_code = ""
        self._lines: List[str] = []

    def parse(self, source_code: str, file_path: str) -> ASTNode:
        self._source_code = source_code
        self._lines = source_code.splitlines()

        try:
            import esprima
            tree = esprima.parseScript(source_code, {"tolerant": True, "loc": True, "range": True})
            return self._convert_node(tree.toDict(), file_path)
        except ImportError:
            return self._fallback_parse(source_code, file_path)
        except Exception as e:
            return self._fallback_parse(source_code, file_path)

    def _fallback_parse(self, source_code: str, file_path: str) -> ASTNode:
        """esprima不可用时的降级解析"""
        root = ASTNode(
            node_type="Program",
            source_span=SourceSpan(file_path, 1, len(self._lines)),
            raw_text=source_code,
        )

        for i, line in enumerate(source_code.splitlines(), 1):
            stripped = line.strip()

            for match in re.finditer(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"", stripped):
                str_node = ASTNode(
                    node_type="Literal",
                    source_span=SourceSpan(file_path, i, i),
                    attributes={"value": match.group(), "is_string": True},
                    raw_text=match.group(),
                )
                root.children.append(str_node)

            if re.search(r'["\'`].*[+].*["\'`]', stripped) or "`" in stripped and "${" in stripped:
                concat_node = ASTNode(
                    node_type="BinaryExpression",
                    source_span=SourceSpan(file_path, i, i),
                    attributes={"is_concatenation": True, "operator": "+"},
                    raw_text=stripped,
                )
                root.children.append(concat_node)

            method_call = re.match(
                r'\s*(?:var|let|const)?\s*\w*\s*=?\s*(\w+)\s*\.\s*(\w+)\s*\((.*)\)', stripped
            )
            if method_call:
                call_node = ASTNode(
                    node_type="CallExpression",
                    source_span=SourceSpan(file_path, i, i),
                    attributes={
                        "function_name": method_call.group(2),
                        "module_name": method_call.group(1),
                        "arguments": method_call.group(3),
                    },
                    raw_text=stripped,
                )
                root.children.append(call_node)

            require_match = re.match(r'\s*.*require\s*\(\s*["\'](.+?)["\']', stripped)
            if require_match:
                imp_node = ASTNode(
                    node_type="ImportDeclaration",
                    source_span=SourceSpan(file_path, i, i),
                    attributes={"imports": [require_match.group(1)]},
                    raw_text=stripped,
                )
                root.children.append(imp_node)

            import_match = re.match(r'\s*import\s+.*from\s+["\'](.+?)["\']', stripped)
            if import_match:
                imp_node = ASTNode(
                    node_type="ImportDeclaration",
                    source_span=SourceSpan(file_path, i, i),
                    attributes={"imports": [import_match.group(1)]},
                    raw_text=stripped,
                )
                root.children.append(imp_node)

        return root

    def _convert_node(self, esprima_node: Dict, file_path: str) -> ASTNode:
        node_type = esprima_node.get("type", "Unknown")

        loc = esprima_node.get("loc", {})
        start = loc.get("start", {})
        end = loc.get("end", {})

        span = SourceSpan(
            file_path=file_path,
            start_line=start.get("line", 0),
            end_line=end.get("line", start.get("line", 0)),
            start_col=start.get("column", 0),
            end_col=end.get("column", 0),
        )

        raw_text = ""
        if span.start_line and span.start_line <= len(self._lines):
            raw_text = self._lines[span.start_line - 1].strip()

        children: List[ASTNode] = []
        attributes: Dict[str, Any] = {}

        for key, value in esprima_node.items():
            if key in ("type", "loc", "range"):
                continue
            if isinstance(value, dict) and "type" in value:
                children.append(self._convert_node(value, file_path))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "type" in item:
                        children.append(self._convert_node(item, file_path))

        if node_type == "CallExpression":
            callee = esprima_node.get("callee", {})
            if callee.get("type") == "MemberExpression":
                prop = callee.get("property", {})
                if prop.get("type") == "Identifier":
                    attributes["function_name"] = prop.get("name", "")
                obj = callee.get("object", {})
                if obj.get("type") == "Identifier":
                    attributes["module_name"] = obj.get("name", "")
            elif callee.get("type") == "Identifier":
                attributes["function_name"] = callee.get("name", "")

        if node_type == "BinaryExpression":
            operator = esprima_node.get("operator", "")
            if operator == "+":
                attributes["is_concatenation"] = True
            attributes["operator"] = operator

        if node_type == "TemplateLiteral":
            attributes["is_concatenation"] = True
            attributes["is_template_literal"] = True

        if node_type == "Literal":
            value = esprima_node.get("value", "")
            attributes["value"] = value
            attributes["is_string"] = isinstance(value, str)

        if node_type == "ImportDeclaration":
            source = esprima_node.get("source", {})
            attributes["imports"] = [source.get("value", "")]

        return ASTNode(
            node_type=node_type,
            source_span=span,
            children=children,
            attributes=attributes,
            raw_text=raw_text,
        )

    def extract_imports(self, ast_root: ASTNode) -> List[str]:
        imports: List[str] = []
        self._collect_imports(ast_root, imports)
        return imports

    def _collect_imports(self, node: ASTNode, imports: List[str]):
        if node.node_type == "ImportDeclaration":
            imports.extend(node.attributes.get("imports", []))
        for child in node.children:
            self._collect_imports(child, imports)

    def find_string_concatenations(self, ast_root: ASTNode) -> List[ASTNode]:
        results: List[ASTNode] = []
        self._find_concatenations(ast_root, results)
        return results

    def _find_concatenations(self, node: ASTNode, results: List[ASTNode]):
        if node.attributes.get("is_concatenation"):
            results.append(node)
        for child in node.children:
            self._find_concatenations(child, results)

    def find_function_calls(self, ast_root: ASTNode, function_names: List[str]) -> List[ASTNode]:
        results: List[ASTNode] = []
        self._find_calls(ast_root, function_names, results)
        return results

    def _find_calls(self, node: ASTNode, function_names: List[str], results: List[ASTNode]):
        if node.node_type == "CallExpression":
            func_name = node.attributes.get("function_name", "")
            if func_name in function_names:
                results.append(node)
        for child in node.children:
            self._find_calls(child, function_names, results)

    def get_node_text(self, node: ASTNode, source_code: str) -> str:
        return node.raw_text

    def modify_source(self, source_code: str, replacements: List[Dict[str, Any]]) -> str:
        lines = source_code.splitlines(keepends=True)
        replacements.sort(key=lambda r: r.get("line", 0), reverse=True)
        for rep in replacements:
            line_no = rep.get("line", 0)
            if 1 <= line_no <= len(lines):
                lines[line_no - 1] = lines[line_no - 1].replace(rep["old"], rep["new"])
        return "".join(lines)
