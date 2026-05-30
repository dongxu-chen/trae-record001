import sqlglot
from sqlglot import exp, parse_one
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

from app.models.lineage_models import (
    ColumnNode,
    TableNode,
    ColumnLineage,
    TableLineage,
    LineageResult,
    MappingLink,
    MappingChain,
    AggregatedLineage,
    NodeType,
)


@dataclass
class TableAlias:
    alias: str
    real_name: str
    table_schema: Optional[str] = None
    database: Optional[str] = None
    is_cte: bool = False
    is_subquery: bool = False
    is_intermediate: bool = False
    alias_chain: List[str] = field(default_factory=list)


@dataclass
class ColumnSource:
    table_alias: str
    column_name: str
    alias: Optional[str] = None
    expression: Optional[str] = None
    level: int = 0
    source_chain: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class ColumnContext:
    name: str
    table_alias: Optional[str] = None
    expression: Optional[str] = None
    sources: List[ColumnSource] = field(default_factory=list)
    mapping_links: List[MappingLink] = field(default_factory=list)
    is_intermediate: bool = False


@dataclass
class CTEContext:
    name: str
    columns: List[ColumnContext]
    table_aliases: Dict[str, TableAlias]
    level: int = 0
    processed: bool = False


class SQLLineageParser:
    def __init__(self, default_database: Optional[str] = None, default_schema: Optional[str] = None):
        self.default_database = default_database
        self.default_schema = default_schema
        self.cte_definitions: Dict[str, CTEContext] = {}
        self.table_aliases: Dict[str, TableAlias] = {}
        self.column_lineages: List[ColumnLineage] = []
        self.table_lineages: List[TableLineage] = []
        self.tables: Dict[str, TableNode] = {}
        self.columns: Dict[str, ColumnNode] = {}
        self.cte_names: Set[str] = set()
        self.subquery_names: Set[str] = set()
        self.intermediate_tables: Set[str] = set()
        self.mapping_chains: List[MappingChain] = []
        self.target_table: Optional[str] = None
        self.source_tables: Set[str] = set()
        self.processing_stack: List[str] = field(default_factory=list)

    def parse(self, sql: str) -> LineageResult:
        self._reset()
        parsed = parse_one(sql, dialect="spark")
        
        self._extract_ctes_recursive(parsed)
        self._process_statement(parsed)
        self._build_mapping_chains()
        self._aggregate_lineage()
        
        return LineageResult(
            tables=list(self.tables.values()),
            columns=list(self.columns.values()),
            table_lineage=self.table_lineages,
            column_lineage=self.column_lineages,
            cte_tables=list(self.cte_names),
            subquery_tables=list(self.subquery_names),
            intermediate_tables=list(self.intermediate_tables),
            mapping_chains=self.mapping_chains,
            aggregated_lineage=self._get_aggregated_lineage(),
        )

    def _reset(self):
        self.cte_definitions = {}
        self.table_aliases = {}
        self.column_lineages = []
        self.table_lineages = []
        self.tables = {}
        self.columns = {}
        self.cte_names = set()
        self.subquery_names = set()
        self.intermediate_tables = set()
        self.mapping_chains = []
        self.target_table = None
        self.source_tables = set()
        self.processing_stack = []

    def _extract_ctes_recursive(self, parsed: exp.Expression, level: int = 0):
        with_cte = parsed.find(exp.With)
        if with_cte:
            for cte in with_cte.expressions:
                cte_name = cte.alias_or_name
                self.cte_names.add(cte_name)
                self.intermediate_tables.add(cte_name)
                
                inner_with = cte.this.find(exp.With)
                if inner_with:
                    self._extract_ctes_recursive(cte.this, level + 1)
                
                table_aliases = {}
                cte_columns = self._extract_select_columns(cte.this, table_aliases, level + 1)
                
                self.cte_definitions[cte_name] = CTEContext(
                    name=cte_name,
                    columns=cte_columns,
                    table_aliases=table_aliases,
                    level=level,
                    processed=False,
                )
                
                cte_table_alias = TableAlias(
                    alias=cte_name,
                    real_name=cte_name,
                    is_cte=True,
                    is_intermediate=True,
                    alias_chain=[cte_name],
                )
                self.table_aliases[cte_name] = cte_table_alias

    def _process_statement(self, parsed: exp.Expression):
        if isinstance(parsed, exp.Insert):
            self._process_insert(parsed)
        elif isinstance(parsed, exp.Create):
            self._process_create(parsed)
        elif isinstance(parsed, exp.Select):
            self._process_select(parsed, is_target=False)
        elif isinstance(parsed, exp.With):
            if parsed.this:
                self._process_statement(parsed.this)

    def _process_insert(self, insert: exp.Insert):
        target_table = self._parse_table_name(insert.this, is_target=True)
        self.target_table = target_table.full_name
        self._add_table(target_table)
        
        table_aliases = {}
        source_columns = self._extract_select_columns(insert.expression, table_aliases)
        
        target_cols = []
        if insert.expressions:
            target_cols = [col.name for col in insert.expressions]
        else:
            target_cols = [ctx.name for ctx in source_columns]
        
        for i, source_ctx in enumerate(source_columns):
            if i < len(target_cols):
                target_col_name = target_cols[i]
                target_col = ColumnNode(
                    name=target_col_name,
                    table=target_table.name,
                    schema=target_table.table_schema,
                    database=target_table.database,
                    node_type=NodeType.TARGET,
                    is_intermediate=False,
                )
                self._add_column(target_col)
                self._create_column_lineages_recursive(
                    source_ctx, target_col, table_aliases, level=0
                )
        
        for alias, table_alias in table_aliases.items():
            self._process_source_table(table_alias, target_table, "INSERT", table_aliases)

    def _process_create(self, create: exp.Create):
        if isinstance(create.this, exp.Table):
            target_table = self._parse_table_name(create.this, is_target=True)
            self.target_table = target_table.full_name
            self._add_table(target_table)
            
            if create.expression and isinstance(create.expression, exp.Select):
                table_aliases = {}
                source_columns = self._extract_select_columns(create.expression, table_aliases)
                
                for source_ctx in source_columns:
                    target_col = ColumnNode(
                        name=source_ctx.name,
                        table=target_table.name,
                        schema=target_table.table_schema,
                        database=target_table.database,
                        node_type=NodeType.TARGET,
                        is_intermediate=False,
                    )
                    self._add_column(target_col)
                    self._create_column_lineages_recursive(
                        source_ctx, target_col, table_aliases, level=0
                    )
                
                for alias, table_alias in table_aliases.items():
                    self._process_source_table(
                        table_alias, target_table, "CREATE_AS_SELECT", table_aliases
                    )

    def _process_select(self, select: exp.Select, is_target: bool = False):
        table_aliases = {}
        columns = self._extract_select_columns(select, table_aliases)
        return columns

    def _process_source_table(
        self,
        table_alias: TableAlias,
        target_table: TableNode,
        query_type: str,
        all_aliases: Dict[str, TableAlias],
    ):
        if table_alias.real_name in self.cte_definitions:
            cte_ctx = self.cte_definitions[table_alias.real_name]
            cte_table = TableNode(
                name=cte_ctx.name,
                node_type=NodeType.CTE,
                is_intermediate=True,
                alias_chain=[cte_ctx.name],
            )
            self._add_table(cte_table)
            self._add_table_lineage(
                cte_table, target_table, query_type, is_direct=False,
                intermediate_tables=[cte_ctx.name]
            )
            
            for inner_alias, inner_table in cte_ctx.table_aliases.items():
                if not inner_table.is_cte and not inner_table.is_subquery:
                    source_table = TableNode(
                        name=inner_table.real_name,
                        schema=inner_table.table_schema,
                        database=inner_table.database,
                        node_type=NodeType.SOURCE,
                        is_intermediate=False,
                    )
                    self.source_tables.add(source_table.full_name)
                    self._add_table(source_table)
                    self._add_table_lineage(
                        source_table, cte_table, f"{query_type}_CTE_SOURCE",
                        is_direct=True
                    )
                    
        elif table_alias.is_subquery:
            subquery_table = TableNode(
                name=table_alias.real_name,
                node_type=NodeType.SUBQUERY,
                is_intermediate=True,
                alias_chain=table_alias.alias_chain,
            )
            self._add_table(subquery_table)
            self._add_table_lineage(
                subquery_table, target_table, query_type, is_direct=False,
                intermediate_tables=[table_alias.real_name]
            )
            
        elif table_alias.real_name not in self.cte_names:
            source_table = TableNode(
                name=table_alias.real_name,
                schema=table_alias.table_schema,
                database=table_alias.database,
                node_type=NodeType.SOURCE,
                is_intermediate=False,
            )
            self.source_tables.add(source_table.full_name)
            self._add_table(source_table)
            self._add_table_lineage(source_table, target_table, query_type, is_direct=True)

    def _extract_select_columns(
        self,
        select: exp.Select,
        table_aliases: Dict[str, TableAlias],
        level: int = 0,
    ) -> List[ColumnContext]:
        result = []
        
        self._extract_table_aliases(select, table_aliases, level)
        
        from_clause = select.args.get("from")
        if from_clause:
            self._extract_from_table(from_clause, table_aliases, level)
        
        for col_expr in select.expressions:
            ctx = self._parse_column_expression(col_expr, table_aliases, level)
            if ctx:
                result.append(ctx)
        
        union = select.args.get("union")
        if union:
            union_columns = self._extract_select_columns(union, table_aliases, level)
            for i, ctx in enumerate(union_columns):
                if i < len(result):
                    for source in ctx.sources:
                        source.level = level
                        result[i].sources.append(source)
                    result[i].mapping_links.extend(ctx.mapping_links)
        
        return result

    def _extract_table_aliases(
        self,
        select: exp.Select,
        table_aliases: Dict[str, TableAlias],
        level: int = 0,
    ):
        for node in select.walk():
            if isinstance(node, exp.Table):
                alias = node.alias_or_name
                table_parts = self._parse_table_parts(node)
                is_cte = table_parts["name"] in self.cte_names
                
                existing_chain = []
                if is_cte and table_parts["name"] in self.table_aliases:
                    existing_chain = self.table_aliases[table_parts["name"]].alias_chain.copy()
                
                new_chain = [alias] + existing_chain
                
                table_aliases[alias] = TableAlias(
                    alias=alias,
                    real_name=table_parts["name"],
                    table_schema=table_parts["schema"],
                    database=table_parts["database"],
                    is_cte=is_cte,
                    is_intermediate=is_cte,
                    alias_chain=new_chain,
                )
            
            elif isinstance(node, exp.Subquery) and node.alias:
                alias = node.alias
                subquery_name = f"subquery_{alias}"
                self.subquery_names.add(subquery_name)
                self.intermediate_tables.add(subquery_name)
                
                inner_aliases = {}
                self._extract_select_columns(node.this, inner_aliases, level + 1)
                
                alias_chain = [alias, subquery_name]
                for inner_alias, inner_table in inner_aliases.items():
                    if inner_table.alias_chain:
                        alias_chain.extend(inner_table.alias_chain)
                
                table_aliases[alias] = TableAlias(
                    alias=alias,
                    real_name=subquery_name,
                    is_subquery=True,
                    is_intermediate=True,
                    alias_chain=alias_chain,
                )

    def _extract_from_table(
        self,
        from_expr: exp.Expression,
        table_aliases: Dict[str, TableAlias],
        level: int = 0,
    ):
        if isinstance(from_expr, exp.Table):
            alias = from_expr.alias_or_name
            table_parts = self._parse_table_parts(from_expr)
            is_cte = table_parts["name"] in self.cte_names
            
            existing_chain = []
            if is_cte and table_parts["name"] in self.table_aliases:
                existing_chain = self.table_aliases[table_parts["name"]].alias_chain.copy()
            
            new_chain = [alias] + existing_chain
            
            table_aliases[alias] = TableAlias(
                alias=alias,
                real_name=table_parts["name"],
                table_schema=table_parts["schema"],
                database=table_parts["database"],
                is_cte=is_cte,
                is_intermediate=is_cte,
                alias_chain=new_chain,
            )
        elif isinstance(from_expr, exp.Join):
            self._extract_from_table(from_expr.this, table_aliases, level)
            if from_expr.expression:
                self._extract_from_table(from_expr.expression, table_aliases, level)
        elif isinstance(from_expr, exp.Subquery) and from_expr.alias:
            alias = from_expr.alias
            subquery_name = f"subquery_{alias}"
            self.subquery_names.add(subquery_name)
            self.intermediate_tables.add(subquery_name)
            
            inner_aliases = {}
            self._extract_select_columns(from_expr.this, inner_aliases, level + 1)
            
            alias_chain = [alias, subquery_name]
            for inner_alias, inner_table in inner_aliases.items():
                if inner_table.alias_chain:
                    alias_chain.extend(inner_table.alias_chain)
            
            table_aliases[alias] = TableAlias(
                alias=alias,
                real_name=subquery_name,
                is_subquery=True,
                is_intermediate=True,
                alias_chain=alias_chain,
            )

    def _parse_column_expression(
        self,
        col_expr: exp.Expression,
        table_aliases: Dict[str, TableAlias],
        level: int = 0,
    ) -> Optional[ColumnContext]:
        ctx = ColumnContext(
            name=col_expr.alias_or_name,
            expression=str(col_expr),
            is_intermediate=level > 0,
        )
        
        col_alias = col_expr.alias_or_name
        
        if isinstance(col_expr, exp.Column):
            table_name = col_expr.table
            col_name = col_expr.name
            
            if table_name:
                source = ColumnSource(
                    table_alias=table_name,
                    column_name=col_name,
                    alias=col_alias,
                    expression=str(col_expr),
                    level=level,
                )
                source.source_chain = [(table_name, col_name)]
                ctx.sources.append(source)
                
                mapping_link = MappingLink(
                    alias=col_alias,
                    original_name=col_name,
                    table_alias=table_name,
                    expression=str(col_expr),
                    level=level,
                )
                ctx.mapping_links.append(mapping_link)
            else:
                for alias, tbl in table_aliases.items():
                    source = ColumnSource(
                        table_alias=alias,
                        column_name=col_name,
                        alias=col_alias,
                        expression=str(col_expr),
                        level=level,
                    )
                    source.source_chain = [(alias, col_name)]
                    ctx.sources.append(source)
                    
                    mapping_link = MappingLink(
                        alias=col_alias,
                        original_name=col_name,
                        table_alias=alias,
                        expression=str(col_expr),
                        level=level,
                    )
                    ctx.mapping_links.append(mapping_link)
        
        elif isinstance(col_expr, exp.Star):
            for alias, tbl in table_aliases.items():
                source = ColumnSource(
                    table_alias=alias,
                    column_name="*",
                    alias=col_alias,
                    expression=str(col_expr),
                    level=level,
                )
                source.source_chain = [(alias, "*")]
                ctx.sources.append(source)
                
                mapping_link = MappingLink(
                    alias=col_alias,
                    original_name="*",
                    table_alias=alias,
                    expression=str(col_expr),
                    level=level,
                )
                ctx.mapping_links.append(mapping_link)
        
        else:
            for node in col_expr.walk():
                if isinstance(node, exp.Column) and node is not col_expr:
                    table_name = node.table
                    col_name = node.name
                    
                    if table_name:
                        source = ColumnSource(
                            table_alias=table_name,
                            column_name=col_name,
                            alias=col_alias,
                            expression=str(col_expr),
                            level=level,
                        )
                        source.source_chain = [(table_name, col_name)]
                        ctx.sources.append(source)
                        
                        mapping_link = MappingLink(
                            alias=col_alias,
                            original_name=col_name,
                            table_alias=table_name,
                            expression=str(col_expr),
                            level=level,
                        )
                        ctx.mapping_links.append(mapping_link)
                    else:
                        for alias, tbl in table_aliases.items():
                            source = ColumnSource(
                                table_alias=alias,
                                column_name=col_name,
                                alias=col_alias,
                                expression=str(col_expr),
                                level=level,
                            )
                            source.source_chain = [(alias, col_name)]
                            ctx.sources.append(source)
                            
                            mapping_link = MappingLink(
                                alias=col_alias,
                                original_name=col_name,
                                table_alias=alias,
                                expression=str(col_expr),
                                level=level,
                            )
                            ctx.mapping_links.append(mapping_link)
        
        return ctx

    def _create_column_lineages_recursive(
        self,
        source_ctx: ColumnContext,
        target_col: ColumnNode,
        table_aliases: Dict[str, TableAlias],
        level: int,
        current_chain: Optional[List[MappingLink]] = None,
        visited_ctes: Optional[Set[str]] = None,
    ):
        if current_chain is None:
            current_chain = []
        if visited_ctes is None:
            visited_ctes = set()
        
        extended_chain = current_chain + source_ctx.mapping_links
        
        for source in source_ctx.sources:
            table_info = table_aliases.get(source.table_alias)
            
            if table_info and table_info.real_name in self.cte_definitions:
                cte_name = table_info.real_name
                if cte_name in visited_ctes:
                    continue
                
                visited_ctes.add(cte_name)
                self.processing_stack.append(cte_name)
                
                cte_ctx = self.cte_definitions[cte_name]
                cte_col = next(
                    (c for c in cte_ctx.columns if c.name == source.column_name),
                    None
                )
                
                if cte_col:
                    cte_column_node = ColumnNode(
                        name=source.column_name,
                        table=cte_name,
                        node_type=NodeType.CTE,
                        is_intermediate=True,
                    )
                    self._add_column(cte_column_node)
                    
                    intermediate_nodes = [cte_column_node.full_name]
                    
                    self._add_column_lineage(
                        cte_column_node, target_col,
                        expression=source.expression,
                        mapping_chain=None,
                        is_direct=False,
                        intermediate_nodes=intermediate_nodes,
                    )
                    
                    self._create_column_lineages_recursive(
                        cte_col, cte_column_node,
                        {**table_aliases, **cte_ctx.table_aliases},
                        level + 1,
                        extended_chain,
                        visited_ctes.copy(),
                    )
                
                self.processing_stack.pop()
                visited_ctes.remove(cte_name)
            
            elif table_info and table_info.is_subquery:
                subquery_col = ColumnNode(
                    name=source.column_name,
                    table=table_info.real_name,
                    node_type=NodeType.SUBQUERY,
                    is_intermediate=True,
                )
                self._add_column(subquery_col)
                
                self._add_column_lineage(
                    subquery_col, target_col,
                    expression=source.expression,
                    mapping_chain=None,
                    is_direct=False,
                    intermediate_nodes=[subquery_col.full_name],
                )
            
            elif table_info:
                source_col_name = source.column_name
                if source_col_name == "*":
                    continue
                
                source_col = ColumnNode(
                    name=source_col_name,
                    table=table_info.real_name,
                    schema=table_info.table_schema,
                    database=table_info.database,
                    node_type=NodeType.SOURCE,
                    is_intermediate=False,
                )
                self._add_column(source_col)
                
                mapping_chain = MappingChain(
                    target_column=target_col.name,
                    target_table=target_col.table_full_name,
                    links=extended_chain,
                    source_columns=[source_col_name],
                    source_tables=[table_info.real_name],
                )
                
                self._add_column_lineage(
                    source_col, target_col,
                    expression=source.expression,
                    mapping_chain=mapping_chain,
                    is_direct=len(extended_chain) <= 1,
                    intermediate_nodes=[],
                )

    def _build_mapping_chains(self):
        for lineage in self.column_lineages:
            if lineage.mapping_chain:
                self.mapping_chains.append(lineage.mapping_chain)

    def _aggregate_lineage(self):
        pass

    def _get_aggregated_lineage(self) -> List[AggregatedLineage]:
        aggregated = []
        seen_pairs = set()
        
        for lineage in self.column_lineages:
            if not lineage.is_direct and lineage.intermediate_nodes:
                pair = (lineage.source.full_name, lineage.target.full_name)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    aggregated.append(AggregatedLineage(
                        source=lineage.source.full_name,
                        target=lineage.target.full_name,
                        intermediate_count=len(lineage.intermediate_nodes),
                        intermediate_nodes=lineage.intermediate_nodes.copy(),
                        expression=lineage.expression,
                        is_collapsed=True,
                    ))
        
        return aggregated

    def _parse_table_name(self, table_expr: exp.Table, is_target: bool = False) -> TableNode:
        parts = self._parse_table_parts(table_expr)
        return TableNode(
            name=parts["name"],
            schema=parts["schema"],
            database=parts["database"],
            node_type=NodeType.TARGET if is_target else NodeType.INTERMEDIATE,
            is_intermediate=False,
        )

    def _parse_table_parts(self, table_expr: exp.Table) -> Dict[str, Optional[str]]:
        name = table_expr.name
        schema = None
        database = None
        
        if table_expr.db:
            schema = table_expr.db
        if table_expr.catalog:
            database = table_expr.catalog
        
        if not schema and self.default_schema:
            schema = self.default_schema
        if not database and self.default_database:
            database = self.default_database
        
        return {"name": name, "schema": schema, "database": database}

    def _add_table(self, table: TableNode):
        key = table.full_name
        if key not in self.tables:
            self.tables[key] = table
        else:
            existing = self.tables[key]
            if existing.node_type == NodeType.INTERMEDIATE and table.node_type != NodeType.INTERMEDIATE:
                existing.node_type = table.node_type
                existing.is_intermediate = table.is_intermediate

    def _add_column(self, column: ColumnNode):
        key = column.full_name
        if key not in self.columns:
            self.columns[key] = column
        else:
            existing = self.columns[key]
            if existing.node_type == NodeType.INTERMEDIATE and column.node_type != NodeType.INTERMEDIATE:
                existing.node_type = column.node_type
                existing.is_intermediate = column.is_intermediate

    def _add_table_lineage(
        self,
        source: TableNode,
        target: TableNode,
        query_type: str,
        is_direct: bool = True,
        intermediate_tables: Optional[List[str]] = None,
    ):
        lineage = TableLineage(
            source=source,
            target=target,
            query_type=query_type,
            is_direct=is_direct,
            intermediate_tables=intermediate_tables or [],
        )
        
        exists = any(
            l.source.full_name == lineage.source.full_name and
            l.target.full_name == lineage.target.full_name
            for l in self.table_lineages
        )
        if not exists:
            self.table_lineages.append(lineage)

    def _add_column_lineage(
        self,
        source: ColumnNode,
        target: ColumnNode,
        expression: Optional[str] = None,
        mapping_chain: Optional[MappingChain] = None,
        is_direct: bool = True,
        intermediate_nodes: Optional[List[str]] = None,
    ):
        lineage = ColumnLineage(
            source=source,
            target=target,
            expression=expression,
            mapping_chain=mapping_chain,
            is_direct=is_direct,
            intermediate_nodes=intermediate_nodes or [],
        )
        
        exists = any(
            l.source.full_name == lineage.source.full_name and
            l.target.full_name == lineage.target.full_name
            for l in self.column_lineages
        )
        if not exists:
            self.column_lineages.append(lineage)
