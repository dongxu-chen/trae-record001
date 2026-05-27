"""Python AST解析器"""

import ast
import astor
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_parser import (
    ASTNode,
    BaseParser,
    Language,
    SourceSpan,
    Vulnerability,
)


class PythonParser(BaseParser):
    """Python源代码解析器，基于内置ast模块"""

    language = Language.PYTHON

    def __init__(self):
        super().__init__()
        self._source_code = ""
        self._lines: List[str] = []

    def parse(self, source_code: str, file_path: str) -> ASTNode:
        self._source_code = source_code
        self._lines = source_code.splitlines()

        try:
            py_ast = ast.parse(source_code)
            return self._convert_node(py_ast, file_path)
        except SyntaxError as e:
            span = SourceSpan(
                file_path=file_path,
                start_line=e.lineno or 1,
                end_line=e.lineno or 1,
                start_col=e.offset or 0,
                end_col=e.offset or 0,
            )
            raise ValueError(f"Python语法错误: {e.msg} at {file_path}:{e.lineno}")

    def _convert_node(self, node: ast.AST, file_path: str) -> ASTNode:
        if node is None:
            return ASTNode(node_type="None", source_span=SourceSpan(file_path, 0, 0))

        lineno = getattr(node, "lineno", 0)
        end_lineno = getattr(node, "end_lineno", lineno)
        col_offset = getattr(node, "col_offset", 0)
        end_col_offset = getattr(node, "end_col_offset", 0)

        span = SourceSpan(
            file_path=file_path,
            start_line=lineno,
            end_line=end_lineno or lineno,
            start_col=col_offset,
            end_col=end_col_offset,
        )

        node_type = type(node).__name__
        raw_text = self._get_source_segment(lineno, col_offset, end_lineno, end_col_offset)

        children: List[ASTNode] = []
        for child in ast.iter_child_nodes(node):
            children.append(self._convert_node(child, file_path))

        attributes: Dict[str, Any] = {}

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                attributes["function_name"] = node.func.id
            elif isinstance(node.func, ast.Attribute):
                attributes["function_name"] = node.func.attr
                if isinstance(node.func.value, ast.Name):
                    attributes["module_name"] = node.func.value.id
            attributes["arg_count"] = len(node.args)
            for i, arg in enumerate(node.args):
                if isinstance(arg, ast.Constant):
                    attributes[f"arg_{i}_is_string"] = isinstance(arg.value, str)
                    attributes[f"arg_{i}_value"] = str(arg.value)
                elif isinstance(arg, ast.Name):
                    attributes[f"arg_{i}_is_variable"] = True
                    attributes[f"arg_{i}_name"] = arg.id

        if isinstance(node, ast.Constant):
            attributes["value"] = node.value
            attributes["is_string"] = isinstance(node.value, str)

        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
            attributes["is_concatenation"] = True
            attributes["operator"] = type(node.op).__name__

        if isinstance(node, ast.JoinedStr):
            attributes["is_f_string"] = True

        if isinstance(node, ast.Name):
            attributes["name"] = node.id

        if isinstance(node, ast.Import):
            attributes["imports"] = [alias.name for alias in node.names]

        if isinstance(node, ast.ImportFrom):
            attributes["module"] = node.module
            attributes["imports"] = [alias.name for alias in node.names]

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            attributes["function_name"] = node.name

        if isinstance(node, ast.Attribute):
            attributes["attr"] = node.attr

        return ASTNode(
            node_type=node_type,
            source_span=span,
            children=children,
            attributes=attributes,
            raw_text=raw_text,
        )

    def _get_source_segment(self, start_line, start_col, end_line, end_col):
        if not self._lines or start_line == 0:
            return ""
        if start_line > len(self._lines):
            return ""
        line_text = self._lines[start_line - 1]
        if end_line and end_line != start_line:
            return line_text[start_col:] if start_col else line_text
        if end_col:
            return line_text[start_col:end_col]
        return line_text[start_col:] if start_col else line_text

    def extract_imports(self, ast_root: ASTNode) -> List[str]:
        imports: List[str] = []
        self._collect_imports(ast_root, imports)
        return imports

    def _collect_imports(self, node: ASTNode, imports: List[str]):
        if node.node_type in ("Import", "ImportFrom"):
            for imp in node.attributes.get("imports", []):
                imports.append(imp)
        for child in node.children:
            self._collect_imports(child, imports)

    def find_string_concatenations(self, ast_root: ASTNode) -> List[ASTNode]:
        results: List[ASTNode] = []
        self._find_concatenations(ast_root, results)
        return results

    def _find_concatenations(self, node: ASTNode, results: List[ASTNode]):
        if node.attributes.get("is_concatenation") or node.attributes.get("is_f_string"):
            results.append(node)
        for child in node.children:
            self._find_concatenations(child, results)

    def find_function_calls(self, ast_root: ASTNode, function_names: List[str]) -> List[ASTNode]:
        results: List[ASTNode] = []
        self._find_calls(ast_root, function_names, results)
        return results

    def _find_calls(self, node: ASTNode, function_names: List[str], results: List[ASTNode]):
        if node.node_type == "Call":
            func_name = node.attributes.get("function_name", "")
            if func_name in function_names:
                results.append(node)
        for child in node.children:
            self._find_calls(child, function_names, results)

    def get_node_text(self, node: ASTNode, source_code: str) -> str:
        return node.raw_text

    def node_to_source(self, node: ast.AST) -> str:
        """将Python AST节点转换回源代码"""
        return astor.to_source(node).strip()

    def get_original_python_ast(self, source_code: str) -> ast.AST:
        """获取原始Python AST（用于修复时的精确操作）"""
        return ast.parse(source_code)

    def modify_source(self, source_code: str, replacements: List[Dict[str, Any]]) -> str:
        """
        根据替换列表修改源代码
        replacements: [{"old": str, "new": str, "line": int}]
        """
        lines = source_code.splitlines(keepends=True)
        replacements.sort(key=lambda r: r.get("line", 0), reverse=True)
        for rep in replacements:
            line_no = rep.get("line", 0)
            if 1 <= line_no <= len(lines):
                lines[line_no - 1] = lines[line_no - 1].replace(rep["old"], rep["new"])
        return "".join(lines)
