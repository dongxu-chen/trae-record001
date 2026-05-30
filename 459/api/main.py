from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os

from config.settings import settings
from services.qa_service import QAService

app = FastAPI(
    title="知识图谱问答系统 API",
    description="基于医疗领域知识图谱的智能问答系统 v3.0 — 支持可视化、主动澄清、增量学习",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

qa_service = None

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class QuestionRequest(BaseModel):
    question: str
    use_bert: Optional[bool] = False
    use_seq2seq: Optional[bool] = True
    skip_clarification: Optional[bool] = False


class FeedbackRequest(BaseModel):
    question: str
    rating: int
    given_answer: Optional[str] = None
    given_intent: Optional[str] = None
    correct_intent: Optional[str] = None
    correct_answer: Optional[str] = None
    correct_entity: Optional[str] = None
    original_entity: Optional[str] = None
    correction: Optional[Dict[str, Any]] = None


class VisualizationRequest(BaseModel):
    center_entity: str
    depth: Optional[int] = 2
    question: Optional[str] = None


class FullGraphRequest(BaseModel):
    limit: Optional[int] = 200


class NeighborhoodRequest(BaseModel):
    entity_name: str
    relation_filter: Optional[str] = None
    direction: Optional[str] = "both"


class EntityDetailRequest(BaseModel):
    entity_name: str


class PathQueryRequest(BaseModel):
    entity1: str
    entity2: str
    max_hops: Optional[int] = 5


class PathCompletionRequest(BaseModel):
    entity1: str
    entity2: str
    known_intermediates: Optional[List[str]] = None
    max_hops: Optional[int] = 5


class MissingNodeHopRequest(BaseModel):
    start_entity: str
    target_relation: Optional[str] = None
    target_entity_type: Optional[str] = None
    max_hops: Optional[int] = 4


class FuzzyMatchDetailRequest(BaseModel):
    text: str


class TrainSeq2SeqRequest(BaseModel):
    epochs: Optional[int] = 30
    batch_size: Optional[int] = 4


class ClarifiedQuestionRequest(BaseModel):
    question: str
    clarified_intent: Optional[str] = None
    clarified_entity: Optional[str] = None
    filter_type: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    global qa_service
    try:
        qa_service = QAService(use_bert=False, use_seq2seq=True)
        print("QA服务初始化成功 (v3.0 - 可视化/主动澄清/增量学习)")
    except Exception as e:
        print(f"QA服务初始化失败: {e}")
        qa_service = None


@app.on_event("shutdown")
async def shutdown_event():
    if qa_service:
        qa_service.close()


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>知识图谱问答系统 v3.0</h1><p>前端页面未找到，请使用 API 文档: /docs</p>"


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "qa_service_available": qa_service is not None,
        "version": "3.0.0"
    }


@app.post("/api/qa")
async def answer_question(request: QuestionRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        result = qa_service.answer(
            request.question,
            skip_clarification=request.skip_clarification
        )

        if result.get("has_answer") and result.get("entities"):
            center = result["entities"][0].get("canonical_name", "")
            if center:
                try:
                    vis = qa_service.get_visualization(center, depth=2, answer_result=result)
                    result["visualization"] = vis
                except Exception:
                    pass

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理问题时出错: {str(e)}")


@app.post("/api/qa/clarified")
async def answer_clarified_question(request: ClarifiedQuestionRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        result = qa_service.answer(request.question, skip_clarification=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理问题时出错: {str(e)}")


@app.post("/api/feedback")
async def submit_feedback(request: FeedbackRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        feedback = request.dict()
        result = qa_service.submit_feedback(feedback)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交反馈时出错: {str(e)}")


@app.get("/api/feedback/stats")
async def get_feedback_stats():
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        return qa_service.get_learning_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计时出错: {str(e)}")


@app.post("/api/feedback/batch-process")
async def batch_process_feedback():
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        return qa_service.batch_process_feedback()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量处理反馈时出错: {str(e)}")


@app.post("/api/visualization/subgraph")
async def get_subgraph_visualization(request: VisualizationRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        if request.question:
            answer_result = qa_service.answer(request.question, skip_clarification=True)
            return qa_service.get_visualization(
                request.center_entity,
                depth=request.depth,
                answer_result=answer_result
            )
        return qa_service.get_visualization(request.center_entity, depth=request.depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取可视化数据时出错: {str(e)}")


@app.post("/api/visualization/full")
async def get_full_graph_visualization(request: FullGraphRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        return qa_service.get_full_graph_visualization(limit=request.limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取全图可视化时出错: {str(e)}")


@app.post("/api/visualization/neighborhood")
async def get_neighborhood_visualization(request: NeighborhoodRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        return qa_service.get_entity_neighborhood_vis(
            request.entity_name,
            relation_filter=request.relation_filter,
            direction=request.direction
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取邻域可视化时出错: {str(e)}")


@app.post("/api/entity/detail")
async def get_entity_detail(request: EntityDetailRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        return qa_service.get_entity_details(request.entity_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询实体详情时出错: {str(e)}")


@app.post("/api/path")
async def find_path_between_entities(request: PathQueryRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        return qa_service.get_path_between_entities(
            entity1=request.entity1,
            entity2=request.entity2,
            max_hops=request.max_hops
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询路径时出错: {str(e)}")


@app.post("/api/path/completion")
async def path_completion_query(request: PathCompletionRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        return qa_service.path_completion_query(
            entity1=request.entity1,
            entity2=request.entity2,
            known_intermediates=request.known_intermediates,
            max_hops=request.max_hops
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"路径补全查询出错: {str(e)}")


@app.post("/api/path/missing-hop")
async def missing_node_hop_query(request: MissingNodeHopRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        return qa_service.missing_node_hop(
            start_entity=request.start_entity,
            target_relation=request.target_relation,
            target_entity_type=request.target_entity_type,
            max_hops=request.max_hops
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"缺失节点跳跃查询出错: {str(e)}")


@app.post("/api/fuzzy-match/detail")
async def fuzzy_match_detail(request: FuzzyMatchDetailRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        return qa_service.fuzzy_match_detail(request.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模糊匹配详情查询出错: {str(e)}")


@app.post("/api/seq2seq/train")
async def train_seq2seq_model(request: TrainSeq2SeqRequest):
    if not qa_service:
        raise HTTPException(status_code=503, detail="QA服务未初始化")

    try:
        qa_service.cypher_generator.train_seq2seq(
            epochs=request.epochs,
            batch_size=request.batch_size
        )
        return {"status": "training_completed", "epochs": request.epochs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"训练Seq2Seq模型出错: {str(e)}")


@app.get("/api/schema")
async def get_schema():
    from kg.schema import ENTITY_TYPES, RELATION_TYPES, INTENT_TYPES
    return {
        "entity_types": ENTITY_TYPES,
        "relation_types": RELATION_TYPES,
        "intent_types": INTENT_TYPES
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
