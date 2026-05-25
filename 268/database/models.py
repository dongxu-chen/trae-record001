from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class OptimizationRequest(Base):
    __tablename__ = 'optimization_requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), unique=True, nullable=False)
    resource_type = Column(String(32), nullable=False)
    resource_id = Column(String(128), nullable=False)
    resource_name = Column(String(256))
    action = Column(String(32), nullable=False)
    monthly_savings = Column(Float, default=0)
    reason = Column(Text)
    details = Column(Text)
    status = Column(String(32), default='pending')
    created_at = Column(DateTime, default=datetime.now)
    approved_at = Column(DateTime)
    executed_at = Column(DateTime)
    rejected_at = Column(DateTime)
    approver = Column(String(128))
    reject_reason = Column(Text)
    execution_result = Column(Text)

    def to_dict(self):
        return {
            'id': self.id,
            'request_id': self.request_id,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'action': self.action,
            'monthly_savings': self.monthly_savings,
            'reason': self.reason,
            'details': self.details,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'approver': self.approver
        }


class ApprovalLog(Base):
    __tablename__ = 'approval_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), nullable=False)
    action = Column(String(32), nullable=False)
    approver = Column(String(128))
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class ResourceData(Base):
    __tablename__ = 'resource_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_id = Column(String(128), nullable=False)
    resource_type = Column(String(32), nullable=False)
    provider = Column(String(32))
    region = Column(String(32))
    data_type = Column(String(32))
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)
    meta_info = Column(Text)


db = {
    'Base': Base,
    'OptimizationRequest': OptimizationRequest,
    'ApprovalLog': ApprovalLog,
    'ResourceData': ResourceData
}
