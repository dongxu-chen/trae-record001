import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Parenthesis, Function
from sqlparse.tokens import Keyword, DML
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class LineageNode:
    """血缘节点"""
    table_name: str
    columns: List[str] = field(default_factory=list)
    alias: Optional[str] = None


@dataclass
class FieldLineage:
    """字段级血缘"""
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    transformation: str = "direct"
    expression: Optional[str] = None


@dataclass
class LineageResult:
    """血缘分析结果"""
    source_tables: List[str] = field(default_factory=list)
    target_tables: List[str] = field(default_factory=list)
    field_lineages: List[FieldLineage] = field(default_factory=list)
    tables: Dict[str, List[str]] = field(default_factory=dict)  # table -> columns
    ctes: Dict[str, List[str]] = field(default_factory=dict)  # CTE name -> columns
    transformation_types: Set[str] = field(default_factory=set)


class SQLLineageAnalyzer:
    """SQL血缘分析器"""

    def __init__(self):
        self.agg_functions = {'SUM', 'AVG', 'COUNT', 'MIN', 'MAX', 'FIRST', 'LAST', 'STDDEV', 'VARIANCE'}
        self.join_keywords = {'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN'}

    def analyze_sql(self, sql: str, target_table: str = None) -> LineageResult:
        """
        分析SQL语句，提取血缘关系
        """
        result = LineageResult()
        parsed = sqlparse.parse(sql)

        if not parsed:
            return result

        stmt = parsed[0]
        tokens = list(stmt.tokens)

        # 提取CTE (WITH语句)
        self._extract_ctes(stmt, result)

        # 提取源表
        source_tables = self._extract_source_tables(stmt)
        result.source_tables = source_tables

        # 提取目标表（INSERT/UPDATE/SELECT INTO）
        target_tables = self._extract_target_tables(stmt)
        if target_table:
            target_tables.append(target_table)
        result.target_tables = target_tables

        # 提取SELECT子句中的字段映射
        select_columns = self._extract_select_columns(stmt, result)

        # 生成字段级血缘
        if target_tables and select_columns:
            for target_col, sources in select_columns.items():
                for source_info in sources:
                    source_table, source_col = source_info
                    transformation = self._determine_transformation(source_col)
                    result.field_lineages.append(FieldLineage(
                        source_table=source_table,
                        source_column=source_col if transformation == "direct" else None,
                        target_table=target_tables[0],
                        target_column=target_col,
                        transformation=transformation,
                        expression=source_col if transformation != "direct" else None
                    ))
                    result.transformation_types.add(transformation)

        # 记录表和字段信息
        for table in source_tables:
            if table not in result.tables:
                result.tables[table] = []

        return result

    def _extract_ctes(self, stmt, result: LineageResult):
        """提取WITH子句中的CTE"""
        tokens = list(stmt.tokens)
        for i, token in enumerate(tokens):
            if token.ttype is Keyword and token.value.upper() == 'WITH':
                # 查找后续的CTE定义
                j = i + 1
                while j < len(tokens):
                    if tokens[j].ttype is Keyword.DML:
                        break
                    if isinstance(tokens[j], IdentifierList):
                        for identifier in tokens[j].get_identifiers():
                            self._process_cte_identifier(identifier, result)
                    elif isinstance(tokens[j], Identifier):
                        self._process_cte_identifier(tokens[j], result)
                    j += 1
                break

    def _process_cte_identifier(self, identifier, result: LineageResult):
        """处理单个CTE标识符"""
        if hasattr(identifier, 'get_real_name'):
            cte_name = identifier.get_real_name()
            # 简化处理，假设CTE列名需要从子查询提取
            result.ctes[cte_name] = []

    def _extract_source_tables(self, stmt) -> List[str]:
        """提取FROM和JOIN子句中的源表"""
        tables = []
        in_from = False
        in_join = False

        for token in stmt.flatten():
            token_upper = token.value.upper() if token.ttype else ''

            if token.ttype is Keyword and 'FROM' in token_upper:
                in_from = True
                in_join = False
                continue
            elif token.ttype is Keyword and any(join in token_upper for join in self.join_keywords):
                in_join = True
                continue
            elif token.ttype is Keyword and token_upper in {'WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'UNION'}:
                in_from = False
                in_join = False
                continue

            if (in_from or in_join) and token.ttype is None and token.value.strip():
                # 这可能是表名
                table_name = token.value.strip().strip('`"[]')
                if table_name and not table_name.startswith('(') and '.' in table_name or len(table_name) > 1:
                    # 移除别名
                    if ' ' in table_name:
                        table_name = table_name.split()[0]
                    if table_name not in tables:
                        tables.append(table_name)

        return tables

    def _extract_target_tables(self, stmt) -> List[str]:
        """提取INSERT/UPDATE等目标表"""
        tables = []
        tokens = list(stmt.tokens)

        for i, token in enumerate(tokens):
            if token.ttype is DML:
                if token.value.upper() in {'INSERT', 'UPDATE', 'MERGE'}:
                    # 查找目标表
                    j = i + 1
                    while j < len(tokens):
                        if isinstance(tokens[j], Identifier):
                            table_name = tokens[j].get_real_name()
                            if table_name:
                                tables.append(table_name)
                            break
                        elif tokens[j].ttype is Keyword and 'INTO' in tokens[j].value.upper():
                            j += 1
                            continue
                        elif tokens[j].value.strip():
                            break
                        j += 1
                elif token.value.upper() == 'SELECT':
                    # 检查是否有 SELECT INTO
                    j = i + 1
                    while j < len(tokens):
                        if tokens[j].ttype is Keyword and 'INTO' in tokens[j].value.upper():
                            # 查找INTO后面的表名
                            j += 1
                            while j < len(tokens):
                                if isinstance(tokens[j], Identifier):
                                    tables.append(tokens[j].get_real_name())
                                    break
                                j += 1
                            break
                        j += 1

        return tables

    def _extract_select_columns(self, stmt, result: LineageResult) -> Dict[str, List[Tuple[str, str]]]:
        """提取SELECT子句的列映射"""
        column_mapping = {}  # target_col -> [(source_table, source_col)]
        in_select = False
        in_from = False
        select_tokens = []
        table_aliases = {}  # alias -> real_table

        # 第一遍：收集表别名
        tokens = list(stmt.tokens)
        for i, token in enumerate(tokens):
            if token.ttype is Keyword.DML and token.value.upper() == 'SELECT':
                in_select = True
                in_from = False
                continue
            if token.ttype is Keyword and 'FROM' in token.value.upper():
                in_from = True
                in_select = False
                continue
            if token.ttype is Keyword and in_from and token.value.upper() in {'WHERE', 'GROUP', 'ORDER'}:
                in_from = False

            if in_from and isinstance(token, Identifier):
                real_name = token.get_real_name()
                alias = token.get_alias() or real_name
                if real_name:
                    table_aliases[alias] = real_name

        # 第二遍：提取SELECT列
        in_select = False
        for token in stmt.tokens:
            if token.ttype is Keyword.DML and token.value.upper() == 'SELECT':
                in_select = True
                continue
            if token.ttype is Keyword and 'FROM' in token.value.upper():
                in_select = False
                break

            if in_select and isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    self._process_column_identifier(identifier, column_mapping, table_aliases)
            elif in_select and isinstance(token, Identifier):
                self._process_column_identifier(token, column_mapping, table_aliases)

        return column_mapping

    def _process_column_identifier(self, identifier, column_mapping: Dict, table_aliases: Dict):
        """处理列标识符"""
        target_name = identifier.get_alias() or identifier.get_real_name()
        if not target_name:
            return

        # 简化处理：假设列名格式为 table.column 或 column
        column_str = str(identifier)
        if '.' in column_str and not column_str.startswith('('):
            parts = column_str.split('.')
            table_alias = parts[0]
            col_name = parts[1].split()[0] if ' ' in parts[1] else parts[1]
            real_table = table_aliases.get(table_alias, table_alias)
            column_mapping[target_name] = [(real_table, col_name)]
        elif column_str.upper().startswith(tuple(self.agg_functions)):
            # 聚合函数
            column_mapping[target_name] = [('aggregated', column_str)]
        elif column_str.strip() != '*':
            # 假设是直接列引用，可能来自多个表
            # 简化处理：记录未知来源
            column_mapping[target_name] = [('unknown', column_str)]

    def _determine_transformation(self, source_col: str) -> str:
        """判断转换类型"""
        if source_col is None:
            return "direct"

        source_upper = source_col.upper()
        if any(func in source_upper for func in self.agg_functions):
            return "aggregate"
        if 'CASE' in source_upper or 'WHEN' in source_upper or 'THEN' in source_upper:
            return "case_when"
        if '||' in source_upper or 'CONCAT' in source_upper:
            return "concatenation"
        if '+' in source_upper or '-' in source_upper or '*' in source_upper or '/' in source_upper:
            return "arithmetic"
        if 'CAST' in source_upper or '::' in source_upper:
            return "type_cast"

        return "direct"

    def get_field_upstream(self, table_name: str, field_name: str, result: LineageResult) -> List[FieldLineage]:
        """获取指定字段的上游依赖"""
        return [fl for fl in result.field_lineages
                if fl.target_table == table_name and fl.target_column == field_name]

    def get_field_downstream(self, table_name: str, field_name: str, result: LineageResult) -> List[FieldLineage]:
        """获取指定字段的下游依赖"""
        return [fl for fl in result.field_lineages
                if fl.source_table == table_name and fl.source_column == field_name]


def build_lineage_graph(lineage_result: LineageResult) -> Dict:
    """构建血缘图谱用于前端可视化"""
    nodes = []
    edges = []

    # 添加表节点
    all_tables = set(lineage_result.source_tables + lineage_result.target_tables)
    for table in all_tables:
        nodes.append({
            "id": f"table_{table}",
            "type": "table",
            "label": table,
            "columns": lineage_result.tables.get(table, []),
            "is_source": table in lineage_result.source_tables,
            "is_target": table in lineage_result.target_tables
        })

    # 添加字段边
    for fl in lineage_result.field_lineages:
        source_id = f"field_{fl.source_table}_{fl.source_column}" if fl.source_column else f"field_{fl.source_table}_derived"
        target_id = f"field_{fl.target_table}_{fl.target_column}"

        # 添加字段节点（如果不存在）
        if not any(n["id"] == source_id for n in nodes):
            nodes.append({
                "id": source_id,
                "type": "field",
                "table": fl.source_table,
                "label": fl.source_column or "derived",
                "parent": f"table_{fl.source_table}"
            })

        if not any(n["id"] == target_id for n in nodes):
            nodes.append({
                "id": target_id,
                "type": "field",
                "table": fl.target_table,
                "label": fl.target_column,
                "parent": f"table_{fl.target_table}"
            })

        edges.append({
            "source": source_id,
            "target": target_id,
            "transformation": fl.transformation,
            "expression": fl.expression
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "transformation_types": list(lineage_result.transformation_types),
        "summary": {
            "table_count": len(all_tables),
            "field_relationships": len(lineage_result.field_lineages)
        }
    }


# 分析任务配置中的血缘
def analyze_task_lineage(task_config: Dict, pipeline_id: int = None) -> Dict:
    """
    从任务配置中分析血缘
    task_config: 任务节点配置
    """
    task_type = task_config.get("type")
    params = task_config.get("params", {})

    result = LineageResult()

    # 根据任务类型分析
    if task_type in ["extract_sql", "transform_sql", "load_sql"]:
        sql = params.get("sql_query", "")
        target_table = params.get("target_table")
        analyzer = SQLLineageAnalyzer()
        result = analyzer.analyze_sql(sql, target_table)

    elif task_type == "transform_join":
        # Join任务
        result.source_tables = [params.get("left_table"), params.get("right_table")]
        result.target_tables = [params.get("output_table", "joined_result")]

    elif task_type == "transform_select":
        # Select任务
        result.source_tables = [params.get("source_table", "source")]
        result.target_tables = [params.get("output_table", "selected_result")]

    return build_lineage_graph(result)
