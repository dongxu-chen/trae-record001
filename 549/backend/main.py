from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from neo4j_db import Neo4jDatabase
from intent_recognition import IntentRecognizer
from qa_engine import QAEngine
from skin_analyzer import SkinImageAnalyzer
from drug_interaction import DrugInteractionChecker
from emergency_detector import EmergencyDetector

app = FastAPI(title="医疗知识问答系统", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

neo4j_db = Neo4jDatabase()
intent_recognizer = IntentRecognizer()
qa_engine = QAEngine(neo4j_db, intent_recognizer)
skin_analyzer = SkinImageAnalyzer()
drug_checker = DrugInteractionChecker()
emergency_detector = EmergencyDetector()

class QuestionRequest(BaseModel):
    question: str
    user_id: Optional[str] = None

class DrugInteractionRequest(BaseModel):
    drugs: List[str]

class ParagraphLocation(BaseModel):
    paragraph_index: int
    section: str

class Evidence(BaseModel):
    source: str
    content: str
    confidence: float
    node_type: Optional[str] = None
    is_rare: Optional[bool] = False
    paragraph_location: Optional[ParagraphLocation] = None
    highlighted_text: Optional[str] = None
    original_text: Optional[str] = None

class EntityInfo(BaseModel):
    text: str
    canonical: Optional[str] = None
    type: str
    is_rare: Optional[bool] = False
    match_method: Optional[str] = "exact"
    fuzzy_score: Optional[float] = None

class EmergencyAlert(BaseModel):
    condition: str
    level: str
    matched_symptoms: List[str]
    action: str
    departments: List[str]
    possible_causes: List[str]

class EmergencyInfo(BaseModel):
    is_emergency: bool
    level: str
    alerts: List[EmergencyAlert]
    emergency_advice: Optional[str] = None

class QAResponse(BaseModel):
    question: str
    intent: str
    intent_confidence: float
    answer: str
    evidence: List[Evidence]
    disclaimer: str
    entities: List[EntityInfo]
    emergency: EmergencyInfo

class SkinAnalysisResponse(BaseModel):
    success: bool
    primary_condition: Optional[Dict[str, Any]] = None
    differential: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    visual_features: Optional[List[str]] = None
    department: Optional[str] = None
    severity: Optional[str] = None
    advice: Optional[str] = None
    emergency: Optional[bool] = None
    emergency_alert: Optional[Dict[str, Any]] = None
    answer: Optional[str] = None
    error: Optional[str] = None

class DrugInteractionResponse(BaseModel):
    drugs: List[str]
    resolved_drugs: List[str]
    interactions: List[Dict[str, Any]]
    interaction_count: int
    overall_risk: Dict[str, Any]
    summary: str
    recommendation: str

@app.on_event("startup")
async def startup_event():
    try:
        neo4j_db.connect()
        intent_recognizer.load_model()
        skin_analyzer.load_model()
        print("系统启动成功！")
    except Exception as e:
        print(f"系统启动失败: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    neo4j_db.close()

@app.post("/api/qa", response_model=QAResponse)
async def answer_question(request: QuestionRequest):
    try:
        result = qa_engine.answer(request.question)
        
        emergency = emergency_detector.detect_emergency(
            request.question, result["entities"]
        )
        
        answer_text = result["answer"]
        if emergency["is_emergency"]:
            answer_text = emergency["emergency_advice"] + "\n\n---\n\n" + answer_text
        
        return QAResponse(
            question=request.question,
            intent=result["intent"],
            intent_confidence=result["intent_confidence"],
            answer=answer_text,
            evidence=[Evidence(**e) for e in result["evidence"]],
            disclaimer=settings.DISCLOSURE_TEXT.strip(),
            entities=[EntityInfo(**e) for e in result["entities"]],
            emergency=EmergencyInfo(**emergency)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/skin-analyze", response_model=SkinAnalysisResponse)
async def analyze_skin_image(file: UploadFile = File(...)):
    try:
        image_data = await file.read()
        
        if len(image_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="图片大小不能超过10MB")
        
        allowed_types = ["image/jpeg", "image/png", "image/webp", "image/bmp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的图片格式: {file.content_type}，请上传 JPG/PNG/WebP/BMP 格式"
            )
        
        result = skin_analyzer.analyze_image(image_data)
        return SkinAnalysisResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drug-interaction", response_model=DrugInteractionResponse)
async def check_drug_interaction(request: DrugInteractionRequest):
    try:
        if len(request.drugs) < 2:
            raise HTTPException(status_code=400, detail="请输入至少两种药物进行相互作用查询")
        
        if len(request.drugs) > 10:
            raise HTTPException(status_code=400, detail="一次最多查询10种药物的相互作用")
        
        result = drug_checker.check_interaction(request.drugs)
        return DrugInteractionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "neo4j_connected": neo4j_db.driver is not None}

@app.get("/api/disclaimer")
async def get_disclaimer():
    return {"disclaimer": settings.DISCLOSURE_TEXT.strip()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
