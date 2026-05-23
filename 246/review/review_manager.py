import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from mq.rabbitmq_client import mq_client

class ReviewStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"

class ReviewPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class ReviewManager:
    def __init__(self):
        self.pending_reviews = {}
    
    def create_review_task(
        self,
        image_id: str,
        audit_result: Dict,
        priority: str = ReviewPriority.MEDIUM,
        source: str = "auto",
        assigned_to: Optional[str] = None
    ) -> Dict:
        review_id = str(uuid.uuid4())
        
        review_task = {
            "review_id": review_id,
            "image_id": image_id,
            "audit_result": audit_result,
            "status": ReviewStatus.PENDING,
            "priority": priority,
            "source": source,
            "assigned_to": assigned_to,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "reviewer_notes": None,
            "final_decision": None
        }
        
        success = mq_client.publish_review_task(review_task)
        
        if success:
            self.pending_reviews[review_id] = review_task
        
        return review_task
    
    def auto_submit_for_review(
        self,
        image_id: str,
        audit_result: Dict
    ) -> Optional[Dict]:
        risk_level = audit_result.get("risk_level")
        confidence = audit_result.get("confidence", 0)
        
        should_review = False
        priority = ReviewPriority.MEDIUM
        
        if risk_level == "high_risk":
            should_review = True
            priority = ReviewPriority.URGENT if confidence > 0.9 else ReviewPriority.HIGH
        elif risk_level == "low_risk" and confidence < 0.6:
            should_review = True
            priority = ReviewPriority.LOW
        
        if should_review:
            return self.create_review_task(
                image_id=image_id,
                audit_result=audit_result,
                priority=priority,
                source="auto"
            )
        
        return None
    
    def get_pending_reviews(self, limit: int = 100) -> List[Dict]:
        return list(self.pending_reviews.values())[:limit]
    
    def update_review_status(
        self,
        review_id: str,
        status: str,
        reviewer: str,
        notes: Optional[str] = None,
        final_decision: Optional[str] = None
    ) -> Optional[Dict]:
        if review_id in self.pending_reviews:
            review = self.pending_reviews[review_id]
            review["status"] = status
            review["updated_at"] = datetime.utcnow().isoformat()
            review["reviewer"] = reviewer
            review["reviewer_notes"] = notes
            review["final_decision"] = final_decision
            
            if status in [ReviewStatus.APPROVED, ReviewStatus.REJECTED]:
                del self.pending_reviews[review_id]
            
            return review
        return None
    
    def get_review_stats(self) -> Dict:
        status_counts = {}
        priority_counts = {}
        
        for review in self.pending_reviews.values():
            status = review["status"]
            priority = review["priority"]
            
            status_counts[status] = status_counts.get(status, 0) + 1
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        return {
            "total_pending": len(self.pending_reviews),
            "by_status": status_counts,
            "by_priority": priority_counts,
            "queue_size": mq_client.get_review_queue_size()
        }
    
    def batch_submit_for_review(
        self,
        image_results: List[Dict]
    ) -> List[Dict]:
        review_tasks = []
        for result in image_results:
            image_id = result.get("image_id", str(uuid.uuid4()))
            review_task = self.auto_submit_for_review(image_id, result)
            if review_task:
                review_tasks.append(review_task)
        
        return review_tasks

review_manager = ReviewManager()
