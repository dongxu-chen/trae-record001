from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from nlp_processor import NLPProcessor
from es_searcher import ElasticSearcher
from knowledge_graph import KnowledgeGraph
from similarity_calculator import SimilarityCalculator
from law_sync_service import law_sync_service
from judgment_predictor import JudgmentPredictor
from dispute_analyzer import DisputeFocusAnalyzer
from document_generator import DocumentGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = AsyncIOScheduler()


class CaseQuery(BaseModel):
    description: str
    top_k: Optional[int] = settings.TOP_K_SIMILAR_CASES
    case_type: Optional[str] = None

class DocumentGenerateRequest(BaseModel):
    description: str
    doc_type: str = "民事起诉状"
    top_k: Optional[int] = 5
    case_type: Optional[str] = None

class SimilarCaseResult(BaseModel):
    case_id: str
    case_title: str
    case_type: str
    similarity_score: float
    summary: str
    key_points: List[str]
    legal_entities: Dict[str, List[str]]
    sentencing_factors: Dict[str, Any] = {}
    sentencing_summary: Dict[str, Any] = {}
    difference_analysis: Dict[str, Any]
    recommended_laws: List[Dict[str, str]]

class SearchResponse(BaseModel):
    success: bool
    query_analysis: Dict[str, Any]
    similar_cases: List[SimilarCaseResult]
    recommended_law_articles: List[Dict[str, str]]
    judgment_prediction: Dict[str, Any] = {}
    dispute_analysis: Dict[str, Any] = {}

class LawArticleInput(BaseModel):
    law_id: str
    content: str
    source: str = ""
    chapter: str = ""
    effective_date: str = ""
    status: str = "有效"

nlp_processor = NLPProcessor()
es_searcher = ElasticSearcher()
knowledge_graph = KnowledgeGraph()
similarity_calculator = SimilarityCalculator()
judgment_predictor = JudgmentPredictor()
dispute_analyzer = DisputeFocusAnalyzer()
document_generator = DocumentGenerator()


async def scheduled_law_sync():
    if law_sync_service.needs_sync():
        logger.info("定时法条同步任务启动...")
        result = law_sync_service.sync_from_official()
        logger.info(f"法条同步完成: {result}")
        knowledge_graph.rebuild_graph()


@app.on_event("startup")
async def startup_event():
    logger.info("初始化法律文书检索系统 v3.0...")
    try:
        es_searcher.create_index_if_not_exists()
        logger.info("Elasticsearch索引初始化完成")
    except Exception as e:
        logger.warning(f"Elasticsearch连接失败: {e}，将使用模拟数据模式")

    try:
        scheduler.add_job(scheduled_law_sync, 'interval', days=settings.LAW_SYNC_INTERVAL_DAYS, id='law_sync')
        scheduler.add_job(scheduled_law_sync, 'cron', day_of_week='mon', hour=2, minute=0, id='law_sync_weekly')
        scheduler.start()
        logger.info(f"法条定时同步任务已启动 (每{settings.LAW_SYNC_INTERVAL_DAYS}天)")
    except Exception as e:
        logger.warning(f"定时任务启动失败: {e}")

    if law_sync_service.needs_sync():
        try:
            result = law_sync_service.sync_from_official()
            logger.info(f"初始法条同步: {result}")
            knowledge_graph.rebuild_graph()
        except Exception as e:
            logger.warning(f"初始法条同步失败: {e}")

    logger.info("系统初始化完成")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()


@app.get("/")
async def root():
    return {"message": settings.PROJECT_NAME, "version": settings.VERSION}


@app.post("/api/search", response_model=SearchResponse)
async def search_similar_cases(query: CaseQuery):
    try:
        logger.info(f"收到检索请求: {query.description[:50]}...")

        query_analysis = nlp_processor.analyze_case_description(query.description)
        query_embedding = nlp_processor.get_embedding(query.description)

        candidate_cases = es_searcher.search_similar_cases(
            query_embedding, query.top_k, query.case_type
        )

        ranked_cases = similarity_calculator.rank_cases(
            query.description, query_analysis, candidate_cases
        )

        recommended_laws = knowledge_graph.recommend_law_articles(
            query_analysis.get("legal_entities", {}),
            query_analysis.get("key_points", []),
            query_analysis.get("case_type")
        )

        judgment_pred = judgment_predictor.predict(query_analysis, ranked_cases)

        dispute_analysis = dispute_analyzer.analyze(query.description, query_analysis)

        similar_cases = []
        for case in ranked_cases:
            diff_analysis = similarity_calculator.analyze_differences(query_analysis, case)
            case_recommended_laws = knowledge_graph.recommend_law_articles(
                case.get("legal_entities", {}),
                case.get("key_points", [])
            )
            similar_cases.append(SimilarCaseResult(
                case_id=case.get("case_id", ""),
                case_title=case.get("case_title", ""),
                case_type=case.get("case_type", ""),
                similarity_score=round(case.get("similarity_score", 0), 4),
                summary=case.get("summary", ""),
                key_points=case.get("key_points", []),
                legal_entities=case.get("legal_entities", {}),
                sentencing_factors=case.get("sentencing_factors", {}),
                sentencing_summary=case.get("sentencing_summary", {}),
                difference_analysis=diff_analysis,
                recommended_laws=case_recommended_laws
            ))

        return SearchResponse(
            success=True,
            query_analysis=query_analysis,
            similar_cases=similar_cases,
            recommended_law_articles=recommended_laws,
            judgment_prediction=judgment_pred,
            dispute_analysis=dispute_analysis,
        )

    except Exception as e:
        logger.error(f"检索失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@app.post("/api/analyze")
async def analyze_case(description: str):
    try:
        analysis = nlp_processor.analyze_case_description(description)
        return {"success": True, "analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predict")
async def predict_judgment(query: CaseQuery):
    try:
        query_analysis = nlp_processor.analyze_case_description(query.description)
        query_embedding = nlp_processor.get_embedding(query.description)
        candidate_cases = es_searcher.search_similar_cases(query_embedding, query.top_k, query.case_type)
        ranked_cases = similarity_calculator.rank_cases(query.description, query_analysis, candidate_cases)
        prediction = judgment_predictor.predict(query_analysis, ranked_cases)
        return {"success": True, "prediction": prediction}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dispute-analysis")
async def analyze_dispute(description: str):
    try:
        query_analysis = nlp_processor.analyze_case_description(description)
        dispute = dispute_analyzer.analyze(description, query_analysis)
        return {"success": True, "dispute_analysis": dispute}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-document")
async def generate_document(request: DocumentGenerateRequest):
    try:
        query_analysis = nlp_processor.analyze_case_description(request.description)
        query_embedding = nlp_processor.get_embedding(request.description)
        candidate_cases = es_searcher.search_similar_cases(query_embedding, request.top_k, request.case_type)
        ranked_cases = similarity_calculator.rank_cases(request.description, query_analysis, candidate_cases)
        recommended_laws = knowledge_graph.recommend_law_articles(
            query_analysis.get("legal_entities", {}),
            query_analysis.get("key_points", []),
            query_analysis.get("case_type")
        )
        dispute = dispute_analyzer.analyze(request.description, query_analysis)
        prediction = judgment_predictor.predict(query_analysis, ranked_cases)

        result = document_generator.generate(
            doc_type=request.doc_type,
            query_analysis=query_analysis,
            similar_cases=ranked_cases,
            recommended_laws=recommended_laws,
            dispute_analysis=dispute,
            judgment_prediction=prediction,
        )
        return {"success": True, "document": result}
    except Exception as e:
        logger.error(f"文书生成失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cases/{case_id}")
async def get_case_detail(case_id: str):
    try:
        case = es_searcher.get_case_by_id(case_id)
        if case:
            return {"success": True, "case": case}
        return {"success": False, "message": "案例未找到"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/laws/sync-status")
async def get_law_sync_status():
    return law_sync_service.get_sync_status()


@app.post("/api/laws/sync")
async def trigger_law_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(_sync_laws_background)
    return {"success": True, "message": "法条同步任务已启动"}


async def _sync_laws_background():
    result = law_sync_service.sync_from_official()
    knowledge_graph.rebuild_graph()
    logger.info(f"法条同步完成: {result}")


@app.post("/api/laws/force-sync")
async def force_law_sync():
    try:
        result = law_sync_service.force_sync()
        knowledge_graph.rebuild_graph()
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/laws/add")
async def add_law_article(law: LawArticleInput):
    try:
        changed = law_sync_service.add_or_update_law(
            law_id=law.law_id, content=law.content, source=law.source,
            chapter=law.chapter, effective_date=law.effective_date, status=law.status,
        )
        if changed:
            knowledge_graph.rebuild_graph()
        return {"success": True, "changed": changed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/laws/search")
async def search_laws(keyword: str, source: Optional[str] = None):
    try:
        results = law_sync_service.search_laws(keyword, source)
        return {"success": True, "results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/laws")
async def get_all_laws(source: Optional[str] = None):
    try:
        if source:
            laws = law_sync_service.get_laws_by_source(source)
        else:
            laws = law_sync_service.get_all_laws()
        return {"success": True, "laws": laws, "total": len(laws)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "elasticsearch": es_searcher.check_connection(),
        "nlp_model": "ready",
        "law_db": {
            "total_laws": len(law_sync_service.get_all_laws()),
            "last_sync": law_sync_service.get_sync_status().get("last_sync"),
            "needs_sync": law_sync_service.needs_sync(),
        },
        "knowledge_graph": knowledge_graph.get_graph_statistics(),
        "features": ["search", "predict", "dispute_analysis", "document_generation"],
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
