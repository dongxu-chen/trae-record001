from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime

from ..database import get_db
from ..models import ProductAttribute, MLTrainingData, SpecClassificationModel
from ..services.attribute_extractor import AttributeExtractor, SpecNormalizer
from ..services.spec_classifier import SpecClassifier

router = APIRouter(prefix="/attributes", tags=["属性提取与规格归一化"])

attribute_extractor = AttributeExtractor()
spec_normalizer = SpecNormalizer()


class ExtractAttributeRequest(BaseModel):
    product_name: Optional[str] = None
    description: Optional[str] = None
    spec_text: str
    category: Optional[str] = None
    raw_specs: Optional[Dict[str, Any]] = None


class ClassifySpecRequest(BaseModel):
    product_name: str
    description: Optional[str] = None
    raw_specs: Optional[Dict[str, Any]] = None
    category: Optional[str] = None


class NormalizeSpecRequest(BaseModel):
    name: str
    description: Optional[str] = None
    spec_text: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    category: Optional[str] = None


class AddTrainingDataRequest(BaseModel):
    category: str
    input_text: str
    output_spec: Dict[str, Any]
    source: str = "manual"
    quality_score: float = 1.0


class TrainModelRequest(BaseModel):
    category: str
    model_type: str = "logistic_regression"
    test_size: float = 0.2


class SaveAttributeRequest(BaseModel):
    product_id: str
    platform: str
    raw_spec_text: Optional[str] = None
    extracted_attributes: Optional[Dict[str, Any]] = None
    normalized_spec: Optional[Dict[str, Any]] = None
    color: Optional[str] = None
    size: Optional[str] = None
    capacity: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[str] = None
    material: Optional[str] = None


@router.post("/extract", summary="提取商品属性")
async def extract_attributes(request: ExtractAttributeRequest):
    result = attribute_extractor.extract(
        raw_text=request.spec_text,
        product_name=request.product_name,
        description=request.description,
        category=request.category
    )
    
    return {
        "success": True,
        "data": {
            "raw_text": result.raw_text,
            "extracted_attributes": result.extracted_attributes,
            "normalized_spec": result.normalized_spec,
            "quality_score": result.quality_score,
            "extraction_method": result.extraction_method,
        }
    }


@router.post("/classify", summary="ML规格分类")
async def classify_spec(request: ClassifySpecRequest, db: Session = Depends(get_db)):
    classifier = SpecClassifier(db=db)
    result = classifier.classify(
        product_name=request.product_name,
        description=request.description or "",
        raw_specs=request.raw_specs,
        category=request.category
    )
    
    return {
        "success": True,
        "data": {
            "predicted_category": result.predicted_category,
            "confidence": result.confidence,
            "all_probabilities": result.all_probabilities,
            "used_model": result.used_model,
            "model_version": result.model_version,
            "extracted_features": {
                "token_count": result.extracted_features.get("token_count"),
                "top_tokens": result.extracted_features.get("top_tokens"),
                "has_number": result.extracted_features.get("has_number"),
                "numeric_attributes": result.extracted_features.get("numeric_attributes"),
                "color_matches": result.extracted_features.get("color_matches"),
                "version_matches": result.extracted_features.get("version_matches"),
            },
            "top_attributes": result.top_attributes,
        }
    }


@router.post("/normalize", summary="规格归一化")
async def normalize_spec(request: NormalizeSpecRequest):
    result = spec_normalizer.normalize_product_specs({
        "name": request.name,
        "description": request.description,
        "spec_text": request.spec_text,
        "specs": request.specs,
        "category": request.category,
    })
    
    return {
        "success": True,
        "data": result
    }


@router.post("/batch-normalize", summary="批量规格归一化")
async def batch_normalize_specs(sources: List[NormalizeSpecRequest]):
    sources_data = [
        {
            "name": s.name,
            "description": s.description,
            "spec_text": s.spec_text,
            "specs": s.specs,
            "category": s.category,
        }
        for s in sources
    ]
    
    result = spec_normalizer.merge_specs_from_sources(sources_data)
    
    return {
        "success": True,
        "data": result
    }


@router.get("/product/{product_id}", summary="获取商品属性")
async def get_product_attributes(product_id: str, db: Session = Depends(get_db)):
    attributes = db.query(ProductAttribute).filter(
        ProductAttribute.product_id == product_id
    ).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": attr.id,
                "platform": attr.platform,
                "raw_spec_text": attr.raw_spec_text,
                "extracted_attributes": attr.extracted_attributes,
                "normalized_spec": attr.normalized_spec,
                "color": attr.color,
                "size": attr.size,
                "capacity": attr.capacity,
                "weight": float(attr.weight) if attr.weight else None,
                "dimensions": attr.dimensions,
                "material": attr.material,
                "category_confidence": attr.category_confidence,
                "spec_quality_score": attr.spec_quality_score,
                "is_verified": attr.is_verified,
                "created_at": attr.created_at.isoformat(),
                "updated_at": attr.updated_at.isoformat(),
            }
            for attr in attributes
        ]
    }


@router.post("/product/{product_id}", summary="保存商品属性")
async def save_product_attributes(product_id: str, request: SaveAttributeRequest,
                                   db: Session = Depends(get_db)):
    existing = db.query(ProductAttribute).filter(
        ProductAttribute.product_id == product_id,
        ProductAttribute.platform == request.platform
    ).first()
    
    if existing:
        existing.raw_spec_text = request.raw_spec_text or existing.raw_spec_text
        existing.extracted_attributes = request.extracted_attributes or existing.extracted_attributes
        existing.normalized_spec = request.normalized_spec or existing.normalized_spec
        existing.color = request.color or existing.color
        existing.size = request.size or existing.size
        existing.capacity = request.capacity or existing.capacity
        existing.weight = request.weight or existing.weight
        existing.dimensions = request.dimensions or existing.dimensions
        existing.material = request.material or existing.material
        existing.updated_at = datetime.utcnow()
        attr = existing
    else:
        attr = ProductAttribute(
            product_id=product_id,
            platform=request.platform,
            raw_spec_text=request.raw_spec_text,
            extracted_attributes=request.extracted_attributes,
            normalized_spec=request.normalized_spec,
            color=request.color,
            size=request.size,
            capacity=request.capacity,
            weight=request.weight,
            dimensions=request.dimensions,
            material=request.material,
        )
        db.add(attr)
    
    db.commit()
    db.refresh(attr)
    
    return {
        "success": True,
        "message": "属性保存成功",
        "data": {"id": attr.id}
    }


@router.post("/training-data", summary="添加训练数据")
async def add_training_data(request: AddTrainingDataRequest, db: Session = Depends(get_db)):
    classifier = SpecClassifier(db=db)
    result = classifier.add_training_data(
        category=request.category,
        input_text=request.input_text,
        output_spec=request.output_spec,
        source=request.source,
        quality_score=request.quality_score
    )
    
    if not result:
        raise HTTPException(status_code=500, detail="添加训练数据失败")
    
    return {
        "success": True,
        "message": "训练数据添加成功",
        "data": {
            "id": result.id,
            "category": result.category,
            "quality_score": result.quality_score
        }
    }


@router.get("/training-data", summary="获取训练数据列表")
async def get_training_data(
    category: Optional[str] = None,
    source: Optional[str] = None,
    min_quality: Optional[float] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(MLTrainingData)
    
    if category:
        query = query.filter(MLTrainingData.category == category)
    if source:
        query = query.filter(MLTrainingData.source == source)
    if min_quality:
        query = query.filter(MLTrainingData.quality_score >= min_quality)
    
    total = query.count()
    data = query.order_by(MLTrainingData.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": d.id,
                "category": d.category,
                "input_text": d.input_text,
                "output_spec": d.output_spec,
                "source": d.source,
                "quality_score": d.quality_score,
                "used_for_training": d.used_for_training,
                "last_trained_at": d.last_trained_at.isoformat() if d.last_trained_at else None,
                "created_at": d.created_at.isoformat(),
            }
            for d in data
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/train", summary="训练规格分类模型")
async def train_model(request: TrainModelRequest, db: Session = Depends(get_db)):
    classifier = SpecClassifier(db=db)
    result = classifier.train_model(
        category=request.category,
        model_type=request.model_type,
        test_size=request.test_size
    )
    
    if not result:
        raise HTTPException(status_code=400, detail="训练失败，请检查是否有足够的训练数据")
    
    return {
        "success": True,
        "message": "模型训练完成",
        "data": {
            "model_name": result.model_name,
            "model_version": result.model_version,
            "category": result.category,
            "metrics": {
                "accuracy": result.accuracy,
                "precision": result.precision,
                "recall": result.recall,
                "f1_score": result.f1_score,
            },
            "training_samples": result.training_samples,
            "test_samples": result.test_samples,
            "training_time_seconds": result.training_time,
        }
    }


@router.get("/models", summary="获取模型列表")
async def get_models(category: Optional[str] = None, db: Session = Depends(get_db)):
    classifier = SpecClassifier(db=db)
    stats = classifier.get_model_stats(category)
    
    return {
        "success": True,
        "data": stats
    }


@router.post("/models/{model_id}/activate", summary="激活模型")
async def activate_model(model_id: str, db: Session = Depends(get_db)):
    model = db.query(SpecClassificationModel).filter(
        SpecClassificationModel.id == model_id
    ).first()
    
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    old_models = db.query(SpecClassificationModel).filter(
        SpecClassificationModel.category == model.category
    ).all()
    
    for m in old_models:
        m.is_active = False
    
    model.is_active = True
    db.commit()
    
    return {
        "success": True,
        "message": f"模型 {model.model_name} 已激活"
    }


@router.delete("/training-data/{data_id}", summary="删除训练数据")
async def delete_training_data(data_id: str, db: Session = Depends(get_db)):
    data = db.query(MLTrainingData).filter(MLTrainingData.id == data_id).first()
    
    if not data:
        raise HTTPException(status_code=404, detail="训练数据不存在")
    
    db.delete(data)
    db.commit()
    
    return {
        "success": True,
        "message": "训练数据已删除"
    }
