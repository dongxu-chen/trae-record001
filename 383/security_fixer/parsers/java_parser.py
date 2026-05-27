"""Java AST解析器"""

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


class JavaParser(BaseParser):
    """Java源代码解析器，基于javalang库"""

    language = Language.JAVA

    def __init__(self):
        super().__init__()
        self._source_code = ""
        self._lines: List[str] = []

    def parse(self, source_code: str, file_path: str) -> ASTNode:
        self._source_code = source_code
        self._lines = source_code.splitlines()

        try:
            import javalang
            tree = javalang.parse.parse(source_code)
            return self._convert_node(tree, file_path)
        except ImportError:
            return self._fallback_parse(source_code, file_path)
        except Exception as e:
            raise ValueError(f"Java解析错误: {e}")

    def _fallback_parse(self, source_code: str, file_path: str) -> ASTNode:
        """javalang不可用时的降级解析，基于正则表达式"""
        root = ASTNode(
            node_type="CompilationUnit",
            source_span=SourceSpan(file_path, 1, len(self._lines)),
            raw_text=source_code,
        )

        for i, line in enumerate(source_code.splitlines(), 1):
            stripped = line.strip()

            string_patterns = re.findall(r'"([^"\\]|\\.)*"', stripped)
            for match in string_patterns:
                str_node = ASTNode(
                    node_type="StringLiteral",
                    source_span=SourceSpan(file_path, i, i),
                    attributes={"value": match, "is_string": True},
                    raw_text=f'"{match}"',
                )
                root.children.append(str_node)

            if re.search(r'(String|StringBuilder|StringBuffer)\s+\w+\s*[+=]', stripped):
                concat_node = ASTNode(
                    node_type="BinaryOperation",
                    source_span=SourceSpan(file_path, i, i),
                    attributes={"is_concatenation": True, "operator": "+"},
                    raw_text=stripped,
                )
                root.children.append(concat_node)

            method_call = re.match(
                r'\s*(\w+)\s*\.\s*(\w+)\s*\((.*)\)', stripped
            )
            if method_call:
                call_node = ASTNode(
                    node_type="MethodInvocation",
                    source_span=SourceSpan(file_path, i, i),
                    attributes={
                        "function_name": method_call.group(2),
                        "module_name": method_call.group(1),
                        "arguments": method_call.group(3),
                    },
                    raw_text=stripped,
                )
                root.children.append(call_node)

            import_match = re.match(r'\s*import\s+(.+?);', stripped)
            if import_match:
                imp_node = ASTNode(
                    node_type="Import",
                    source_span=SourceSpan(file_path, i, i),
                    attributes={"imports": [import_match.group(1)]},
                    raw_text=stripped,
                )
                root.children.append(imp_node)

        return root

    def _convert_node(self, javalang_node, file_path: str) -> ASTNode:
        node_type = type(javalang_node).__name__

        position = getattr(javalang_node, "position", None)
        if position:
            lineno = position.line
            col = position.column
        else:
            lineno = 0
            col = 0

        span = SourceSpan(
            file_path=file_path,
            start_line=lineno,
            end_line=lineno,
            start_col=col,
            end_col=col,
        )

        raw_text = ""
        if lineno and lineno <= len(self._lines):
            raw_text = self._lines[lineno - 1].strip()

        children: List[ASTNode] = []
        attributes: Dict[str, Any] = {}

        try:
            for child_name, child_value in self._iter_javalang_children(javalang_node):
                if isinstance(child_value, list):
                    for item in child_value:
                        if hasattr(item, "position"):
                            children.append(self._convert_node(item, file_path))
                elif hasattr(child_value, "position"):
                    children.append(self._convert_node(child_value, file_path))
        except Exception:
            pass

        if node_type == "MethodInvocation":
            attributes["function_name"] = getattr(javalang_node, "member", "")
            if hasattr(javalang_node, "qualifier") and javalang_node.qualifier:
                attributes["module_name"] = javalang_node.qualifier

        if node_type == "BinaryOperation":
            operator = getattr(javalang_node, "operator", "")
            if operator == "+":
                attributes["is_concatenation"] = True
            attributes["operator"] = operator

        if node_type == "Literal":
            value = getattr(javalang_node, "value", "")
            attributes["value"] = value
            if isinstance(value, str) and value.startswith('"'):
                attributes["is_string"] = True

        if node_type == "Import":
            path = getattr(javalang_node, "path", "")
            attributes["imports"] = [path]

        return ASTNode(
            node_type=node_type,
            source_span=span,
            children=children,
            attributes=attributes,
            raw_text=raw_text,
        )

    def _iter_javalang_children(self, node):
        for attr_name in vars(node):
            if not attr_name.startswith("_"):
                yield attr_name, getattr(node, attr_name)

    def extract_imports(self, ast_root: ASTNode) -> List[str]:
        imports: List[str] = []
        self._collect_imports(ast_root, imports)
        return imports

    def _collect_imports(self, node: ASTNode, imports: List[str]):
        if node.node_type == "Import":
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
        if node.node_type == "MethodInvocation":
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
