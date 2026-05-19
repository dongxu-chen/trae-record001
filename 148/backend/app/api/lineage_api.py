from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime
import json

from app.core.database import get_db
from app.models.lineage import DataSource, DataSet, LineageEdge, LineageFieldEdge
from app.pipelines.lineage_analyzer import SQLLineageAnalyzer, build_lineage_graph, analyze_task_lineage

router = APIRouter(prefix="/api/lineage", tags=["data-lineage"])


@router.post("/analyze-sql")
def analyze_sql_lineage(sql: str, target_table: str = None):
    """分析SQL语句的数据血缘"""
    analyzer = SQLLineageAnalyzer()
    result = analyzer.analyze_sql(sql, target_table)
    graph = build_lineage_graph(result)

    # 提取字段级血缘
    field_lineages = []
    for fl in result.field_lineages:
        field_lineages.append({
            "source_table": fl.source_table,
            "source_column": fl.source_column,
            "target_table": fl.target_table,
            "target_column": fl.target_column,
            "transformation": fl.transformation,
            "expression": fl.expression
        })

    return {
        "tables": {
            "source": result.source_tables,
            "target": result.target_tables,
            "all": list(set(result.source_tables + result.target_tables))
        },
        "field_lineages": field_lineages,
        "graph": graph,
        "transformation_types": list(result.transformation_types)
    }


@router.post("/analyze-task")
def analyze_task_lineage_endpoint(task_config: Dict[str, Any]):
    """分析任务配置的血缘"""
    return analyze_task_lineage(task_config)


@router.get("/sources")
def list_data_sources(db: Session = Depends(get_db)):
    """获取所有数据源"""
    sources = db.query(DataSource).all()
    return [{
        "id": s.id,
        "name": s.name,
        "type": s.type,
        "description": s.description,
        "created_at": s.created_at.isoformat()
    } for s in sources]


@router.post("/sources")
def create_data_source(data: Dict[str, Any], db: Session = Depends(get_db)):
    """创建数据源"""
    source = DataSource(
        name=data["name"],
        type=data["type"],
        connection_config=data.get("connection_config", {}),
        description=data.get("description")
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return {"id": source.id, "name": source.name}


@router.get("/datasets")
def list_datasets(source_id: int = None, db: Session = Depends(get_db)):
    """获取数据集列表"""
    query = db.query(DataSet)
    if source_id:
        query = query.filter(DataSet.data_source_id == source_id)
    datasets = query.all()
    return [{
        "id": d.id,
        "name": d.name,
        "schema_name": d.schema_name,
        "data_source_id": d.data_source_id,
        "metadata": d.metadata
    } for d in datasets]


@router.get("/graph")
def get_lineage_graph(pipeline_id: int = None, depth: int = 3, db: Session = Depends(get_db)):
    """获取完整血缘图谱"""
    edges = db.query(LineageEdge)
    if pipeline_id:
        edges = edges.filter(LineageEdge.pipeline_id == pipeline_id)
    edges = edges.all()

    nodes = {}
    graph_edges = []

    for edge in edges:
        # 添加源节点
        if edge.upstream_set_id not in nodes:
            ds = db.query(DataSet).filter(DataSet.id == edge.upstream_set_id).first()
            if ds:
                nodes[edge.upstream_set_id] = {
                    "id": f"dataset_{ds.id}",
                    "type": "dataset",
                    "name": ds.name,
                    "full_name": f"{ds.schema_name}.{ds.name}" if ds.schema_name else ds.name
                }

        # 添加目标节点
        if edge.downstream_set_id not in nodes:
            ds = db.query(DataSet).filter(DataSet.id == edge.downstream_set_id).first()
            if ds:
                nodes[edge.downstream_set_id] = {
                    "id": f"dataset_{ds.id}",
                    "type": "dataset",
                    "name": ds.name,
                    "full_name": f"{ds.schema_name}.{ds.name}" if ds.schema_name else ds.name
                }

        # 添加边
        graph_edges.append({
            "source": f"dataset_{edge.upstream_set_id}",
            "target": f"dataset_{edge.downstream_set_id}",
            "transformation_type": edge.transformation_type,
            "pipeline_id": edge.pipeline_id
        })

    # 获取字段级血缘
    field_edges = db.query(LineageFieldEdge).all()
    field_lineages = []
    for fe in field_edges:
        field_lineages.append({
            "source_field": fe.upstream_field_id,
            "target_field": fe.downstream_field_id,
            "transformation": fe.transformation_type,
            "expression": fe.transformation_expression
        })

    return {
        "nodes": list(nodes.values()),
        "edges": graph_edges,
        "field_lineages": field_lineages,
        "summary": {
            "total_nodes": len(nodes),
            "total_edges": len(graph_edges),
            "total_field_edges": len(field_lineages)
        }
    }


@router.get("/upstream/{dataset_id}")
def get_upstream_lineage(dataset_id: int, depth: int = 3, db: Session = Depends(get_db)):
    """获取指定数据集的上游血缘"""
    visited = set()
    upstream = []

    def dfs(current_id, current_depth):
        if current_id in visited or current_depth > depth:
            return
        visited.add(current_id)

        edges = db.query(LineageEdge).filter(LineageEdge.downstream_set_id == current_id).all()
        for edge in edges:
            ds = db.query(DataSet).filter(DataSet.id == edge.upstream_set_id).first()
            if ds:
                upstream.append({
                    "dataset_id": ds.id,
                    "name": ds.name,
                    "distance": current_depth,
                    "transformation_type": edge.transformation_type
                })
                dfs(ds.id, current_depth + 1)

    dfs(dataset_id, 1)
    return {"dataset_id": dataset_id, "upstream": upstream, "total": len(upstream)}


@router.get("/downstream/{dataset_id}")
def get_downstream_lineage(dataset_id: int, depth: int = 3, db: Session = Depends(get_db)):
    """获取指定数据集的下游血缘"""
    visited = set()
    downstream = []

    def dfs(current_id, current_depth):
        if current_id in visited or current_depth > depth:
            return
        visited.add(current_id)

        edges = db.query(LineageEdge).filter(LineageEdge.upstream_set_id == current_id).all()
        for edge in edges:
            ds = db.query(DataSet).filter(DataSet.id == edge.downstream_set_id).first()
            if ds:
                downstream.append({
                    "dataset_id": ds.id,
                    "name": ds.name,
                    "distance": current_depth,
                    "transformation_type": edge.transformation_type
                })
                dfs(ds.id, current_depth + 1)

    dfs(dataset_id, 1)
    return {"dataset_id": dataset_id, "downstream": downstream, "total": len(downstream)}


@router.post("/record")
def record_lineage(data: Dict[str, Any], db: Session = Depends(get_db)):
    """记录血缘关系"""
    edge = LineageEdge(
        pipeline_id=data.get("pipeline_id"),
        execution_id=data.get("execution_id"),
        upstream_set_id=data["upstream_set_id"],
        downstream_set_id=data["downstream_set_id"],
        transformation_type=data.get("transformation_type"),
        transformation_logic=data.get("transformation_logic"),
        metadata=data.get("metadata", {})
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)

    # 记录字段级血缘
    if "field_lineages" in data:
        for fl in data["field_lineages"]:
            field_edge = LineageFieldEdge(
                lineage_edge_id=edge.id,
                upstream_field_id=fl.get("upstream_field_id"),
                downstream_field_id=fl.get("downstream_field_id"),
                transformation_type=fl.get("transformation_type"),
                transformation_expression=fl.get("expression")
            )
            db.add(field_edge)
        db.commit()

    return {"id": edge.id, "message": "Lineage recorded successfully"}
