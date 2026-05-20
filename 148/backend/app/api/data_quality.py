from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.pipeline import DataQualityRule, DataQualityResult
from app.models.schemas import (
    DataQualityRuleCreate, DataQualityRuleResponse,
    DataQualityResultResponse
)

router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])


@router.get("/rules", response_model=List[DataQualityRuleResponse])
def list_rules(pipeline_id: int = None, db: Session = Depends(get_db)):
    query = db.query(DataQualityRule)
    if pipeline_id:
        query = query.filter(DataQualityRule.pipeline_id == pipeline_id)
    return query.order_by(DataQualityRule.created_at.desc()).all()


@router.get("/rules/{rule_id}", response_model=DataQualityRuleResponse)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(DataQualityRule).filter(DataQualityRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.post("/rules", response_model=DataQualityRuleResponse)
def create_rule(rule: DataQualityRuleCreate, db: Session = Depends(get_db)):
    db_rule = DataQualityRule(
        name=rule.name,
        rule_type=rule.rule_type,
        config=rule.config,
        pipeline_id=rule.pipeline_id
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(DataQualityRule).filter(DataQualityRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    return {"message": "Rule deleted successfully"}


@router.get("/results", response_model=List[DataQualityResultResponse])
def list_results(execution_id: int = None, db: Session = Depends(get_db)):
    query = db.query(DataQualityResult)
    if execution_id:
        query = query.filter(DataQualityResult.execution_id == execution_id)
    return query.order_by(DataQualityResult.executed_at.desc()).all()
