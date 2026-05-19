from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class DataSource(Base):
    """数据源信息"""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # mysql, postgresql, csv, kafka, etc.
    connection_config = Column(JSON, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tables = relationship("DataSet", back_populates="data_source", cascade="all, delete-orphan")


class DataSet(Base):
    """数据集/表信息"""
    __tablename__ = "data_sets"

    id = Column(Integer, primary_key=True, index=True)
    data_source_id = Column(Integer, ForeignKey("data_sources.id"))
    name = Column(String(255), nullable=False)  # 表名或文件名
    schema_name = Column(String(255))  # schema/database名
    description = Column(Text)
    metadata = Column(JSON)  # 存储表属性、行数等信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    data_source = relationship("DataSource", back_populates="tables")
    fields = relationship("DataField", back_populates="data_set", cascade="all, delete-orphan")
    upstream_edges = relationship("LineageEdge", back_populates="upstream_set",
                                  foreign_keys="LineageEdge.upstream_set_id")
    downstream_edges = relationship("LineageEdge", back_populates="downstream_set",
                                    foreign_keys="LineageEdge.downstream_set_id")


class DataField(Base):
    """字段信息"""
    __tablename__ = "data_fields"

    id = Column(Integer, primary_key=True, index=True)
    data_set_id = Column(Integer, ForeignKey("data_sets.id"))
    name = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)
    description = Column(Text)
    is_nullable = Column(Integer, default=1)
    is_primary_key = Column(Integer, default=0)
    position = Column(Integer)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    data_set = relationship("DataSet", back_populates="fields")
    upstream_field_edges = relationship("LineageFieldEdge", back_populates="upstream_field",
                                        foreign_keys="LineageFieldEdge.upstream_field_id")
    downstream_field_edges = relationship("LineageFieldEdge", back_populates="downstream_field",
                                          foreign_keys="LineageFieldEdge.downstream_field_id")


class LineageEdge(Base):
    """表级血缘关系"""
    __tablename__ = "lineage_edges"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id"), nullable=True)
    execution_id = Column(Integer, ForeignKey("pipeline_executions.id"), nullable=True)
    upstream_set_id = Column(Integer, ForeignKey("data_sets.id"), nullable=False)
    downstream_set_id = Column(Integer, ForeignKey("data_sets.id"), nullable=False)
    transformation_type = Column(String(100))  # select, join, filter, aggregate, etc.
    transformation_logic = Column(Text)  # 转换逻辑描述或SQL
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    upstream_set = relationship("DataSet", foreign_keys=[upstream_set_id],
                                back_populates="downstream_edges")
    downstream_set = relationship("DataSet", foreign_keys=[downstream_set_id],
                                  back_populates="upstream_edges")
    field_edges = relationship("LineageFieldEdge", back_populates="lineage_edge",
                               cascade="all, delete-orphan")


class LineageFieldEdge(Base):
    """字段级血缘关系"""
    __tablename__ = "lineage_field_edges"

    id = Column(Integer, primary_key=True, index=True)
    lineage_edge_id = Column(Integer, ForeignKey("lineage_edges.id"))
    upstream_field_id = Column(Integer, ForeignKey("data_fields.id"))
    downstream_field_id = Column(Integer, ForeignKey("data_fields.id"))
    transformation_type = Column(String(100))  # direct, expression, aggregate, join, etc.
    transformation_expression = Column(Text)  # 转换表达式
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    lineage_edge = relationship("LineageEdge", back_populates="field_edges")
    upstream_field = relationship("DataField", foreign_keys=[upstream_field_id],
                                  back_populates="downstream_field_edges")
    downstream_field = relationship("DataField", foreign_keys=[downstream_field_id],
                                    back_populates="upstream_field_edges")
