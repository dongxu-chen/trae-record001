import uuid
from typing import Dict, List, Optional, Callable
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from webhook_manager import WebhookManager, WebhookEventType

from .models import Base, OptimizationRequest, ApprovalLog, ResourceData


class DatabaseManager:
    def __init__(self, db_path: str = 'sqlite:///cloud_cost_optimizer.db', 
                 webhook_config: Dict = None):
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.webhook_manager = WebhookManager(webhook_config)
        self._execute_callback = None

    def create_optimization_request(self, resource_type: str, resource_id: str,
                                    resource_name: str, action: str,
                                    monthly_savings: float, reason: str = '',
                                    details: str = '') -> str:
        request_id = f"opt-{uuid.uuid4().hex[:12]}"
        request = OptimizationRequest(
            request_id=request_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            action=action,
            monthly_savings=monthly_savings,
            reason=reason,
            details=details,
            status='pending'
        )
        self.session.add(request)
        self.session.commit()
        return request_id

    def batch_create_requests(self, recommendations: pd.DataFrame) -> List[str]:
        request_ids = []
        for _, rec in recommendations.iterrows():
            req_id = self.create_optimization_request(
                resource_type=rec.get('resource_type', ''),
                resource_id=rec.get('resource_id', ''),
                resource_name=rec.get('resource_name', ''),
                action=rec.get('action', ''),
                monthly_savings=rec.get('monthly_savings', 0),
                reason=rec.get('reason', ''),
                details=rec.get('details', '')
            )
            request_ids.append(req_id)
        return request_ids

    def get_request(self, request_id: str) -> Optional[OptimizationRequest]:
        return self.session.query(OptimizationRequest).filter_by(request_id=request_id).first()

    def get_all_requests(self, status: str = None) -> List[OptimizationRequest]:
        query = self.session.query(OptimizationRequest)
        if status:
            query = query.filter_by(status=status)
        return query.order_by(OptimizationRequest.created_at.desc()).all()

    def set_execute_callback(self, callback: Callable):
        self._execute_callback = callback

    def approve_request(self, request_id: str, approver: str = 'system',
                        auto_execute: bool = None) -> bool:
        request = self.get_request(request_id)
        if request and request.status == 'pending':
            request.status = 'approved'
            request.approved_at = datetime.now()
            request.approver = approver
            
            log = ApprovalLog(
                request_id=request_id,
                action='approve',
                approver=approver
            )
            self.session.add(log)
            self.session.commit()
            
            request_data = request.to_dict()
            
            if auto_execute is None:
                auto_execute = self.webhook_manager.auto_execute_on_approve
            
            if auto_execute and self._execute_callback:
                try:
                    self._execute_callback(request_id)
                except Exception as e:
                    print(f"Auto-execute callback failed: {e}")
            
            self.webhook_manager.trigger_event(
                WebhookEventType.REQUEST_APPROVED,
                request_data
            )
            
            return True
        return False

    def reject_request(self, request_id: str, approver: str = 'system',
                       reason: str = '') -> bool:
        request = self.get_request(request_id)
        if request and request.status == 'pending':
            request.status = 'rejected'
            request.rejected_at = datetime.now()
            request.approver = approver
            request.reject_reason = reason
            
            log = ApprovalLog(
                request_id=request_id,
                action='reject',
                approver=approver,
                comment=reason
            )
            self.session.add(log)
            self.session.commit()
            
            self.webhook_manager.trigger_event(
                WebhookEventType.REQUEST_REJECTED,
                request.to_dict()
            )
            
            return True
        return False

    def execute_request(self, request_id: str, result: str = 'success') -> bool:
        request = self.get_request(request_id)
        if request and request.status == 'approved':
            request.status = 'executed'
            request.executed_at = datetime.now()
            request.execution_result = result
            
            log = ApprovalLog(
                request_id=request_id,
                action='execute',
                comment=result
            )
            self.session.add(log)
            self.session.commit()
            
            self.webhook_manager.trigger_event(
                WebhookEventType.REQUEST_EXECUTED,
                {**request.to_dict(), 'execution_result': result}
            )
            
            return True
        return False

    def create_optimization_request(self, resource_type: str, resource_id: str,
                                    resource_name: str, action: str,
                                    monthly_savings: float, reason: str = '',
                                    details: str = '') -> str:
        request_id = f"opt-{uuid.uuid4().hex[:12]}"
        request = OptimizationRequest(
            request_id=request_id,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            action=action,
            monthly_savings=monthly_savings,
            reason=reason,
            details=details,
            status='pending'
        )
        self.session.add(request)
        self.session.commit()
        
        self.webhook_manager.trigger_event(
            WebhookEventType.REQUEST_CREATED,
            request.to_dict()
        )
        
        return request_id

    def add_webhook(self, url: str, events: List[str] = None, 
                    secret: str = None, method: str = 'POST'):
        return self.webhook_manager.add_webhook(url, events, secret, method)

    def remove_webhook(self, url: str):
        self.webhook_manager.remove_webhook(url)

    def test_webhook(self, url: str, method: str = 'POST') -> Dict:
        return self.webhook_manager.test_webhook(url, method)

    def auto_approve_low_savings(self, threshold: float = 100.0) -> int:
        pending_requests = self.session.query(OptimizationRequest).filter_by(
            status='pending'
        ).filter(OptimizationRequest.monthly_savings < threshold).all()
        
        count = 0
        for req in pending_requests:
            if self.approve_request(req.request_id, 'auto-approve'):
                count += 1
        return count

    def get_requests_dataframe(self, status: str = None) -> pd.DataFrame:
        requests = self.get_all_requests(status)
        if not requests:
            return pd.DataFrame()
        
        return pd.DataFrame([req.to_dict() for req in requests])

    def save_resource_metrics(self, metrics_df: pd.DataFrame) -> None:
        for _, row in metrics_df.iterrows():
            record = ResourceData(
                resource_id=row.get('instance_id', ''),
                resource_type='ECS',
                data_type=row.get('metric_name', ''),
                value=row.get('value', 0),
                timestamp=row.get('timestamp')
            )
            self.session.add(record)
        self.session.commit()

    def get_optimization_summary(self) -> Dict:
        total_requests = self.session.query(OptimizationRequest).count()
        pending_count = self.session.query(OptimizationRequest).filter_by(status='pending').count()
        approved_count = self.session.query(OptimizationRequest).filter_by(status='approved').count()
        executed_count = self.session.query(OptimizationRequest).filter_by(status='executed').count()
        rejected_count = self.session.query(OptimizationRequest).filter_by(status='rejected').count()
        
        total_savings = self.session.query(OptimizationRequest).filter_by(
            status='executed'
        ).with_entities(OptimizationRequest.monthly_savings).all()
        
        total_monthly_savings = sum(s[0] for s in total_savings) if total_savings else 0
        
        return {
            'total_requests': total_requests,
            'pending': pending_count,
            'approved': approved_count,
            'executed': executed_count,
            'rejected': rejected_count,
            'total_monthly_savings': total_monthly_savings,
            'total_annual_savings': total_monthly_savings * 12
        }

    def close(self):
        self.session.close()
