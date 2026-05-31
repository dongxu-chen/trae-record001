import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Integer, DECIMAL, Boolean, Float
from sqlalchemy.orm import relationship
from ..database import Base


class ProductAttribute(Base):
    __tablename__ = "product_attributes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False, index=True)
    
    raw_spec_text = Column(Text)
    extracted_attributes = Column(JSON)
    normalized_spec = Column(JSON)
    
    color = Column(String(100))
    size = Column(String(100))
    capacity = Column(String(100))
    weight = Column(DECIMAL(10, 2))
    dimensions = Column(String(200))
    material = Column(String(200))
    
    category_confidence = Column(Float, default=0.0)
    spec_quality_score = Column(Float, default=0.0)
    
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    product = relationship("Product", backref="attributes")


class MLTrainingData(Base):
    __tablename__ = "ml_training_data"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    category = Column(String(100), nullable=False, index=True)
    input_text = Column(Text, nullable=False)
    output_spec = Column(JSON, nullable=False)
    
    source = Column(String(50), default="manual")
    quality_score = Column(Float, default=1.0)
    
    used_for_training = Column(Boolean, default=False)
    last_trained_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpecClassificationModel(Base):
    __tablename__ = "spec_classification_models"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    
    model_type = Column(String(50), default="logistic_regression")
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    
    training_samples = Column(Integer, default=0)
    last_trained_at = Column(DateTime)
    
    is_active = Column(Boolean, default=True)
    model_path = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)
