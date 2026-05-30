from typing import Dict, List, Optional, Set, Tuple
from collections import deque
from datetime import datetime

from app.models.lineage_models import (
    ImpactAnalysisResult,
    ImpactNode,
    DataDictionary,
    DataDictionaryTable,
    DataDictionaryColumn,
    LineageDocument,
    Anomaly,
    AnomalyType,
    AnomalySeverity,
    AnomalyDetectionResult,
    TableNode,
    ColumnNode,
    TableLineage,
    ColumnLineage,
)


class ImpactAnalysisService:
    @staticmethod
    def analyze_impact(
        source_table: str,
        tables: List[TableNode],
        columns: List[ColumnNode],
        table_lineages: List[TableLineage],
        column_lineages: List[ColumnLineage],
        max_depth: int = 10
    ) -> ImpactAnalysisResult:
        table_map = {t.full_name: t for t in tables}
        column_map = {c.full_name: c for c in columns}
        
        downstream_tables = ImpactAnalysisService._get_downstream_tables(
            source_table, table_lineages, max_depth
        )
        
        downstream_columns = ImpactAnalysisService._get_downstream_columns(
            source_table, column_lineages, tables, max_depth
        )
        
        total_tables = len(downstream_tables)
        total_columns = len(downstream_columns)
        max_depth_reached = max([n.level for n in downstream_tables], default=0)
        
        impact_summary = {
            "by_table_type": {},
            "by_level": {},
        }
        
        for node in downstream_tables:
            impact_summary["by_table_type"][node.node_type] = (
                impact_summary["by_table_type"].get(node.node_type, 0) + 1
            )
            impact_summary["by_level"][str(node.level)] = (
                impact_summary["by_level"].get(str(node.level), 0) + 1
            )
        
        return ImpactAnalysisResult(
            source_table=source_table,
            downstream_tables=downstream_tables,
            downstream_columns=downstream_columns,
            total_tables_impacted=total_tables,
            total_columns_impacted=total_columns,
            max_impact_depth=max_depth_reached,
            impact_summary=impact_summary,
        )
    
    @staticmethod
    def _get_downstream_tables(
        source_table: str,
        table_lineages: List[TableLineage],
        max_depth: int
    ) -> List[ImpactNode]:
        adjacency = {}
        for lineage in table_lineages:
            src = lineage.source.full_name
            tgt = lineage.target.full_name
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append(tgt)
        
        visited = {}
        queue = deque([(source_table, 0, [source_table])])
        
        while queue:
            current, level, path = queue.popleft()
            
            if current in visited:
                continue
            
            if level > max_depth:
                continue
            
            visited[current] = {
                "level": level,
                "path": path,
            }
            
            if current in adjacency:
                for next_table in adjacency[current]:
                    if next_table not in visited:
                        queue.append((next_table, level + 1, path + [next_table]))
        
        result = []
        for table_name, info in visited.items():
            if table_name == source_table:
                continue
            
            direct_impacts = len(adjacency.get(table_name, []))
            total_impacts = ImpactAnalysisService._count_total_downstream(
                table_name, adjacency, set()
            )
            
            result.append(ImpactNode(
                name=table_name,
                node_type="table",
                level=info["level"],
                direct_impacts=direct_impacts,
                total_impacts=total_impacts,
                impact_path=info["path"],
            ))
        
        return sorted(result, key=lambda x: x.level)
    
    @staticmethod
    def _count_total_downstream(
        table: str,
        adjacency: Dict[str, List[str]],
        visited: Set[str]
    ) -> int:
        if table in visited:
            return 0
        visited.add(table)
        
        count = 0
        for next_table in adjacency.get(table, []):
            count += 1 + ImpactAnalysisService._count_total_downstream(next_table, adjacency, visited)
        return count
    
    @staticmethod
    def _get_downstream_columns(
        source_table: str,
        column_lineages: List[ColumnLineage],
        tables: List[TableNode],
        max_depth: int
    ) -> List[ImpactNode]:
        source_columns = [
            c.full_name for c in tables
            if c.full_name == source_table
        ]
        
        adjacency = {}
        column_table_map = {}
        
        for lineage in column_lineages:
            src = lineage.source.full_name
            tgt = lineage.target.full_name
            column_table_map[src] = lineage.source.table_full_name
            column_table_map[tgt] = lineage.target.table_full_name
            
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append(tgt)
        
        visited = {}
        queue = deque()
        
        for col in column_table_map:
            if column_table_map[col] == source_table:
                queue.append((col, 0, [col]))
        
        while queue:
            current, level, path = queue.popleft()
            
            if current in visited:
                continue
            
            if level > max_depth:
                continue
            
            visited[current] = {
                "level": level,
                "path": path,
            }
            
            if current in adjacency:
                for next_col in adjacency[current]:
                    if next_col not in visited:
                        queue.append((next_col, level + 1, path + [next_col]))
        
        result = []
        for col_name, info in visited.items():
            if column_table_map.get(col_name) == source_table:
                continue
            
            direct_impacts = len(adjacency.get(col_name, []))
            total_impacts = ImpactAnalysisService._count_total_downstream(
                col_name, adjacency, set()
            )
            
            result.append(ImpactNode(
                name=col_name,
                node_type="column",
                level=info["level"],
                direct_impacts=direct_impacts,
                total_impacts=total_impacts,
                impact_path=info["path"],
            ))
        
        return sorted(result, key=lambda x: x.level)


class DocumentGenerationService:
    @staticmethod
    def generate_data_dictionary(
        tables: List[TableNode],
        columns: List[ColumnNode],
        table_lineages: List[TableLineage],
        column_lineages: List[ColumnLineage],
        mapping_chains: List = None
    ) -> DataDictionary:
        table_columns: Dict[str, List[ColumnNode]] = {}
        for col in columns:
            table_name = col.table_full_name
            if table_name not in table_columns:
                table_columns[table_name] = []
            table_columns[table_name].append(col)
        
        table_sources: Dict[str, Set[str]] = {}
        table_targets: Dict[str, Set[str]] = {}
        
        for lineage in table_lineages:
            src = lineage.source.full_name
            tgt = lineage.target.full_name
            
            if tgt not in table_sources:
                table_sources[tgt] = set()
            table_sources[tgt].add(src)
            
            if src not in table_targets:
                table_targets[src] = set()
            table_targets[src].add(tgt)
        
        column_sources: Dict[str, List[str]] = {}
        column_transformations: Dict[str, str] = {}
        column_mappings: Dict[str, str] = {}
        
        for lineage in column_lineages:
            tgt = lineage.target.full_name
            if tgt not in column_sources:
                column_sources[tgt] = []
            column_sources[tgt].append(lineage.source.full_name)
            
            if lineage.transformation:
                column_transformations[tgt] = lineage.transformation
            
            if lineage.mapping_chain:
                column_mappings[tgt] = lineage.mapping_chain.full_chain
        
        dd_tables = []
        total_cols = 0
        
        for table in tables:
            table_name = table.full_name
            cols = table_columns.get(table_name, [])
            total_cols += len(cols)
            
            dd_columns = []
            for col in cols:
                col_full_name = col.full_name
                dd_columns.append(DataDictionaryColumn(
                    name=col.name,
                    source_columns=column_sources.get(col_full_name, []),
                    transformation=column_transformations.get(col_full_name),
                    mapping_chain=column_mappings.get(col_full_name),
                ))
            
            dd_tables.append(DataDictionaryTable(
                name=table.name,
                schema=table.table_schema,
                database=table.database,
                columns=dd_columns,
                node_type=table.node_type.value if hasattr(table.node_type, 'value') else table.node_type,
                source_tables=list(table_sources.get(table_name, set())),
                target_tables=list(table_targets.get(table_name, set())),
            ))
        
        return DataDictionary(
            tables=dd_tables,
            generated_at=datetime.now().isoformat(),
            total_tables=len(dd_tables),
            total_columns=total_cols,
        )
    
    @staticmethod
    def generate_lineage_document(
        title: str,
        tables: List[TableNode],
        columns: List[ColumnNode],
        table_lineages: List[TableLineage],
        column_lineages: List[ColumnLineage],
        mapping_chains: List = None
    ) -> LineageDocument:
        data_dict = DocumentGenerationService.generate_data_dictionary(
            tables, columns, table_lineages, column_lineages, mapping_chains
        )
        
        table_lineage_dicts = []
        for lineage in table_lineages:
            table_lineage_dicts.append({
                "source": lineage.source.full_name,
                "target": lineage.target.full_name,
                "query_type": lineage.query_type,
                "is_direct": lineage.is_direct,
                "intermediate_tables": lineage.intermediate_tables,
            })
        
        column_lineage_dicts = []
        for lineage in column_lineages:
            column_lineage_dicts.append({
                "source": lineage.source.full_name,
                "target": lineage.target.full_name,
                "transformation": lineage.transformation,
                "expression": lineage.expression,
                "is_direct": lineage.is_direct,
            })
        
        key_mappings = []
        if mapping_chains:
            for chain in mapping_chains:
                key_mappings.append({
                    "target": f"{chain.target_table}.{chain.target_column}",
                    "sources": chain.source_columns,
                    "chain": chain.full_chain,
                    "depth": chain.chain_depth,
                })
        
        source_tables = [t.full_name for t in tables if t.node_type.value == 'source']
        target_tables = [t.full_name for t in tables if t.node_type.value == 'target']
        cte_tables = [t.full_name for t in tables if t.node_type.value == 'cte']
        subquery_tables = [t.full_name for t in tables if t.node_type.value == 'subquery']
        
        summary = {
            "total_tables": len(tables),
            "total_columns": len(columns),
            "source_tables_count": len(source_tables),
            "target_tables_count": len(target_tables),
            "cte_tables_count": len(cte_tables),
            "subquery_tables_count": len(subquery_tables),
            "table_lineages_count": len(table_lineages),
            "column_lineages_count": len(column_lineages),
            "mapping_chains_count": len(mapping_chains) if mapping_chains else 0,
            "source_tables": source_tables,
            "target_tables": target_tables,
        }
        
        return LineageDocument(
            title=title,
            generated_at=datetime.now().isoformat(),
            summary=summary,
            data_dictionary=data_dict,
            table_lineage=table_lineage_dicts,
            column_lineage=column_lineage_dicts,
            key_mappings=key_mappings,
        )
    
    @staticmethod
    def export_markdown(document: LineageDocument) -> str:
        lines = []
        
        lines.append(f"# {document.title}")
        lines.append("")
        lines.append(f"**生成时间**: {document.generated_at}")
        lines.append("")
        
        lines.append("## 概览")
        lines.append("")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 总表数 | {document.summary.get('total_tables', 0)} |")
        lines.append(f"| 总字段数 | {document.summary.get('total_columns', 0)} |")
        lines.append(f"| 源表数 | {document.summary.get('source_tables_count', 0)} |")
        lines.append(f"| 目标表数 | {document.summary.get('target_tables_count', 0)} |")
        lines.append(f"| 表血缘关系 | {document.summary.get('table_lineages_count', 0)} |")
        lines.append(f"| 字段血缘关系 | {document.summary.get('column_lineages_count', 0)} |")
        lines.append("")
        
        lines.append("## 数据字典")
        lines.append("")
        
        for table in document.data_dictionary.tables:
            table_full_name = []
            if table.database:
                table_full_name.append(table.database)
            if table.table_schema:
                table_full_name.append(table.table_schema)
            table_full_name.append(table.name)
            full_name = ".".join(table_full_name)
            
            lines.append(f"### {full_name}")
            lines.append("")
            lines.append(f"- **类型**: {table.node_type}")
            if table.source_tables:
                lines.append(f"- **源表**: {', '.join(table.source_tables)}")
            if table.target_tables:
                lines.append(f"- **下游表**: {', '.join(table.target_tables)}")
            lines.append("")
            
            lines.append("| 字段名 | 源字段 | 转换逻辑 |")
            lines.append("|--------|--------|----------|")
            for col in table.columns:
                sources = ", ".join(col.source_columns) if col.source_columns else "-"
                transform = col.transformation or col.mapping_chain or "-"
                lines.append(f"| {col.name} | {sources} | {transform} |")
            lines.append("")
        
        lines.append("## 关键字段映射")
        lines.append("")
        for mapping in document.key_mappings:
            lines.append(f"### {mapping['target']}")
            lines.append(f"- **映射链**: {mapping['chain']}")
            lines.append(f"- **深度**: {mapping['depth']} 层")
            lines.append("")
        
        return "\n".join(lines)


class AnomalyDetectionService:
    @staticmethod
    def detect_anomalies(
        tables: List[TableNode],
        columns: List[ColumnNode],
        table_lineages: List[TableLineage],
        column_lineages: List[ColumnLineage],
    ) -> AnomalyDetectionResult:
        anomalies: List[Anomaly] = []
        
        table_out_degree, table_in_degree = AnomalyDetectionService._get_table_degrees(
            tables, table_lineages
        )
        
        column_out_degree, column_in_degree = AnomalyDetectionService._get_column_degrees(
            columns, column_lineages
        )
        
        isolated_tables = AnomalyDetectionService._find_isolated_tables(
            tables, table_out_degree, table_in_degree
        )
        if isolated_tables:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.ISOLATED_TABLE,
                severity=AnomalySeverity.MEDIUM,
                description=f"发现 {len(isolated_tables)} 个孤立表，没有血缘关系连接",
                affected_objects=isolated_tables,
                recommendation="检查这些表是否被使用，或者是否存在未解析的SQL",
                details={"count": len(isolated_tables)},
            ))
        
        isolated_columns = AnomalyDetectionService._find_isolated_columns(
            columns, column_out_degree, column_in_degree
        )
        if isolated_columns:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.ISOLATED_COLUMN,
                severity=AnomalySeverity.LOW,
                description=f"发现 {len(isolated_columns)} 个孤立字段，没有血缘关系连接",
                affected_objects=isolated_columns[:20],
                recommendation="检查这些字段是否被使用，或者是否存在未解析的SQL",
                details={"count": len(isolated_columns)},
            ))
        
        cycles = AnomalyDetectionService._detect_cycles(tables, table_lineages)
        if cycles:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.CYCLE_DETECTED,
                severity=AnomalySeverity.HIGH,
                description=f"检测到 {len(cycles)} 个循环依赖",
                affected_objects=[f"{' -> '.join(cycle)}" for cycle in cycles],
                recommendation="检查循环依赖并修复，这可能导致数据处理死循环",
                details={"cycles": cycles},
            ))
        
        broken_lineages = AnomalyDetectionService._find_broken_lineages(
            tables, columns, table_lineages, column_lineages
        )
        if broken_lineages:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.BROKEN_LINEAGE,
                severity=AnomalySeverity.HIGH,
                description=f"发现 {len(broken_lineages)} 条断连的血缘链路",
                affected_objects=broken_lineages[:10],
                recommendation="检查源表/字段是否存在，或者是否缺少SQL解析",
                details={"count": len(broken_lineages)},
            ))
        
        unused_tables = AnomalyDetectionService._find_unused_tables(
            tables, table_out_degree, table_in_degree
        )
        if unused_tables:
            anomalies.append(Anomaly(
                anomaly_type=AnomalyType.UNUSED_TABLE,
                severity=AnomalySeverity.LOW,
                description=f"发现 {len(unused_tables)} 个未使用的表",
                affected_objects=unused_tables,
                recommendation="考虑是否可以移除这些未使用的表",
                details={"count": len(unused_tables)},
            ))
        
        by_severity = {}
        by_type = {}
        for anomaly in anomalies:
            sev = anomaly.severity.value
            typ = anomaly.anomaly_type.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_type[typ] = by_type.get(typ, 0) + 1
        
        total = len(anomalies)
        critical = by_severity.get('critical', 0)
        high = by_severity.get('high', 0)
        summary = f"共检测到 {total} 个异常"
        if critical > 0 or high > 0:
            summary += f" (严重: {critical}, 高危: {high})"
        
        return AnomalyDetectionResult(
            anomalies=anomalies,
            total_anomalies=total,
            by_severity=by_severity,
            by_type=by_type,
            summary=summary,
        )
    
    @staticmethod
    def _get_table_degrees(
        tables: List[TableNode],
        lineages: List[TableLineage]
    ) -> Tuple[Dict[str, int], Dict[str, int]]:
        out_degree = {t.full_name: 0 for t in tables}
        in_degree = {t.full_name: 0 for t in tables}
        
        for lineage in lineages:
            src = lineage.source.full_name
            tgt = lineage.target.full_name
            
            if src in out_degree:
                out_degree[src] += 1
            if tgt in in_degree:
                in_degree[tgt] += 1
        
        return out_degree, in_degree
    
    @staticmethod
    def _get_column_degrees(
        columns: List[ColumnNode],
        lineages: List[ColumnLineage]
    ) -> Tuple[Dict[str, int], Dict[str, int]]:
        out_degree = {c.full_name: 0 for c in columns}
        in_degree = {c.full_name: 0 for c in columns}
        
        for lineage in lineages:
            src = lineage.source.full_name
            tgt = lineage.target.full_name
            
            if src in out_degree:
                out_degree[src] += 1
            if tgt in in_degree:
                in_degree[tgt] += 1
        
        return out_degree, in_degree
    
    @staticmethod
    def _find_isolated_tables(
        tables: List[TableNode],
        out_degree: Dict[str, int],
        in_degree: Dict[str, int]
    ) -> List[str]:
        isolated = []
        for table in tables:
            name = table.full_name
            if out_degree.get(name, 0) == 0 and in_degree.get(name, 0) == 0:
                isolated.append(name)
        return isolated
    
    @staticmethod
    def _find_isolated_columns(
        columns: List[ColumnNode],
        out_degree: Dict[str, int],
        in_degree: Dict[str, int]
    ) -> List[str]:
        isolated = []
        for col in columns:
            name = col.full_name
            if out_degree.get(name, 0) == 0 and in_degree.get(name, 0) == 0:
                isolated.append(name)
        return isolated
    
    @staticmethod
    def _detect_cycles(
        tables: List[TableNode],
        lineages: List[TableLineage]
    ) -> List[List[str]]:
        adjacency = {}
        for lineage in lineages:
            src = lineage.source.full_name
            tgt = lineage.target.full_name
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append(tgt)
        
        cycles = []
        visited = set()
        
        def dfs(node, path, visited_in_path):
            if node in visited_in_path:
                idx = path.index(node)
                cycle = path[idx:]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            visited_in_path.add(node)
            path.append(node)
            
            for next_node in adjacency.get(node, []):
                dfs(next_node, path.copy(), visited_in_path.copy())
        
        for table in tables:
            if table.full_name not in visited:
                dfs(table.full_name, [], set())
        
        return cycles
    
    @staticmethod
    def _find_broken_lineages(
        tables: List[TableNode],
        columns: List[ColumnNode],
        table_lineages: List[TableLineage],
        column_lineages: List[ColumnLineage],
    ) -> List[str]:
        table_names = {t.full_name for t in tables}
        column_names = {c.full_name for c in columns}
        
        broken = []
        
        for lineage in table_lineages:
            src = lineage.source.full_name
            tgt = lineage.target.full_name
            if src not in table_names:
                broken.append(f"表血缘源缺失: {src} -> {tgt}")
            if tgt not in table_names:
                broken.append(f"表血缘目标缺失: {src} -> {tgt}")
        
        for lineage in column_lineages:
            src = lineage.source.full_name
            tgt = lineage.target.full_name
            if src not in column_names:
                broken.append(f"字段血缘源缺失: {src} -> {tgt}")
            if tgt not in column_names:
                broken.append(f"字段血缘目标缺失: {src} -> {tgt}")
        
        return broken
    
    @staticmethod
    def _find_unused_tables(
        tables: List[TableNode],
        out_degree: Dict[str, int],
        in_degree: Dict[str, int]
    ) -> List[str]:
        unused = []
        for table in tables:
            name = table.full_name
            node_type = table.node_type.value if hasattr(table.node_type, 'value') else table.node_type
            if node_type == 'target' and out_degree.get(name, 0) == 0:
                continue
            if node_type == 'source' and in_degree.get(name, 0) == 0:
                continue
            if out_degree.get(name, 0) == 0 and in_degree.get(name, 0) > 0:
                pass
        return unused
