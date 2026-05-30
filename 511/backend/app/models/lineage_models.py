from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class NodeType(str, Enum):
    SOURCE = "source"
    INTERMEDIATE = "intermediate"
    TARGET = "target"
    CTE = "cte"
    SUBQUERY = "subquery"


class BaseLineageModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ColumnNode(BaseLineageModel):
    name: str
    table: str
    table_schema: Optional[str] = Field(None, alias="schema")
    database: Optional[str] = None
    node_type: NodeType = NodeType.INTERMEDIATE
    is_intermediate: bool = False
    alias_chain: List[str] = Field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        parts = []
        if self.database:
            parts.append(self.database)
        if self.table_schema:
            parts.append(self.table_schema)
        parts.append(self.table)
        parts.append(self.name)
        return '.'.join(parts)
    
    @property
    def table_full_name(self) -> str:
        parts = []
        if self.database:
            parts.append(self.database)
        if self.table_schema:
            parts.append(self.table_schema)
        parts.append(self.table)
        return '.'.join(parts)


class TableNode(BaseLineageModel):
    name: str
    table_schema: Optional[str] = Field(None, alias="schema")
    database: Optional[str] = None
    columns: List[str] = Field(default_factory=list)
    node_type: NodeType = NodeType.INTERMEDIATE
    is_intermediate: bool = False
    alias_chain: List[str] = Field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        parts = []
        if self.database:
            parts.append(self.database)
        if self.table_schema:
            parts.append(self.table_schema)
        parts.append(self.name)
        return '.'.join(parts)


class MappingLink(BaseLineageModel):
    alias: str
    original_name: str
    table_alias: Optional[str] = None
    expression: Optional[str] = None
    level: int = 0
    
    @property
    def display_name(self) -> str:
        if self.alias == self.original_name:
            return self.alias
        return f"{self.alias} ← {self.original_name}"


class MappingChain(BaseLineageModel):
    target_column: str
    target_table: str
    links: List[MappingLink] = Field(default_factory=list)
    source_columns: List[str] = Field(default_factory=list)
    source_tables: List[str] = Field(default_factory=list)
    
    @property
    def full_chain(self) -> str:
        parts = [self.target_column]
        for link in self.links:
            parts.append(link.original_name)
        return " → ".join(parts)
    
    @property
    def chain_depth(self) -> int:
        return len(self.links)


class ColumnLineage(BaseLineageModel):
    source: ColumnNode
    target: ColumnNode
    transformation: Optional[str] = None
    expression: Optional[str] = None
    mapping_chain: Optional[MappingChain] = None
    is_direct: bool = True
    intermediate_nodes: List[str] = Field(default_factory=list)


class TableLineage(BaseLineageModel):
    source: TableNode
    target: TableNode
    query_type: str
    is_direct: bool = True
    intermediate_tables: List[str] = Field(default_factory=list)


class AggregatedLineage(BaseLineageModel):
    source: str
    target: str
    intermediate_count: int
    intermediate_nodes: List[str] = Field(default_factory=list)
    expression: Optional[str] = None
    is_collapsed: bool = True


class LineageResult(BaseLineageModel):
    tables: List[TableNode] = Field(default_factory=list)
    columns: List[ColumnNode] = Field(default_factory=list)
    table_lineage: List[TableLineage] = Field(default_factory=list)
    column_lineage: List[ColumnLineage] = Field(default_factory=list)
    cte_tables: List[str] = Field(default_factory=list)
    subquery_tables: List[str] = Field(default_factory=list)
    intermediate_tables: List[str] = Field(default_factory=list)
    mapping_chains: List[MappingChain] = Field(default_factory=list)
    aggregated_lineage: List[AggregatedLineage] = Field(default_factory=list)


class SQLParseRequest(BaseLineageModel):
    sql: str
    database: Optional[str] = None
    table_schema: Optional[str] = Field(None, alias="schema")


class ImpactNode(BaseLineageModel):
    name: str
    node_type: str
    level: int
    direct_impacts: int
    total_impacts: int
    impact_path: List[str]


class ImpactAnalysisResult(BaseLineageModel):
    source_table: str
    downstream_tables: List[ImpactNode] = Field(default_factory=list)
    downstream_columns: List[ImpactNode] = Field(default_factory=list)
    total_tables_impacted: int = 0
    total_columns_impacted: int = 0
    max_impact_depth: int = 0
    impact_summary: Dict[str, Any] = Field(default_factory=dict)


class DataDictionaryColumn(BaseLineageModel):
    name: str
    data_type: Optional[str] = None
    description: Optional[str] = None
    is_nullable: bool = True
    default_value: Optional[str] = None
    source_columns: List[str] = Field(default_factory=list)
    transformation: Optional[str] = None
    mapping_chain: Optional[str] = None


class DataDictionaryTable(BaseLineageModel):
    name: str
    table_schema: Optional[str] = Field(None, alias="schema")
    database: Optional[str] = None
    description: Optional[str] = None
    columns: List[DataDictionaryColumn] = Field(default_factory=list)
    node_type: str = "intermediate"
    source_tables: List[str] = Field(default_factory=list)
    target_tables: List[str] = Field(default_factory=list)


class DataDictionary(BaseLineageModel):
    tables: List[DataDictionaryTable] = Field(default_factory=list)
    generated_at: str = ""
    total_tables: int = 0
    total_columns: int = 0


class LineageDocument(BaseLineageModel):
    title: str
    generated_at: str
    summary: Dict[str, Any] = Field(default_factory=dict)
    data_dictionary: DataDictionary
    table_lineage: List[Dict[str, Any]] = Field(default_factory=list)
    column_lineage: List[Dict[str, Any]] = Field(default_factory=list)
    key_mappings: List[Dict[str, Any]] = Field(default_factory=list)


class AnomalyType(str, Enum):
    ISOLATED_TABLE = "isolated_table"
    ISOLATED_COLUMN = "isolated_column"
    BROKEN_LINEAGE = "broken_lineage"
    CYCLE_DETECTED = "cycle_detected"
    UNUSED_TABLE = "unused_table"
    UNUSED_COLUMN = "unused_column"
    DUPLICATE_MAPPING = "duplicate_mapping"


class AnomalySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Anomaly(BaseLineageModel):
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    description: str
    affected_objects: List[str] = Field(default_factory=list)
    recommendation: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AnomalyDetectionResult(BaseLineageModel):
    anomalies: List[Anomaly] = Field(default_factory=list)
    total_anomalies: int = 0
    by_severity: Dict[str, int] = Field(default_factory=dict)
    by_type: Dict[str, int] = Field(default_factory=dict)
    summary: str = ""
