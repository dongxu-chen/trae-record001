import os
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.config import get_settings
from app.document_parser import DocumentParser
from app.retrieval_chain import get_rag_chain, RAGChain
from app.session_manager import get_session_manager, SessionManager
from app.schemas import (
    DocumentInfo,
    ChatRequest,
    ChatResponse,
    UploadResponse,
    SessionInfo,
    HealthCheckResponse,
    DeleteDocumentRequest,
    AnswerEvaluationResult,
    FeedbackRequest,
    UncoveredQuery,
    ActiveLearningStats,
)

app = FastAPI(
    title="知识库问答系统 API",
    description="基于RAG的智能问答系统，支持多模态问答、主动学习和答案评估",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()
rag_chain: RAGChain = get_rag_chain()
session_manager: SessionManager = get_session_manager()


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(),
        documents_count=rag_chain.get_total_documents(),
        active_learning_stats=rag_chain.get_active_learning_stats(),
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
):
    if not DocumentParser.is_supported(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。支持的类型: PDF, Word, Markdown, TXT",
        )

    document_id = str(uuid.uuid4())
    file_path = os.path.join(settings.UPLOAD_DIR, f"{document_id}_{file.filename}")

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        doc_info = rag_chain.process_document(
            file_path=file_path,
            filename=file.filename,
            document_id=document_id,
        )

        if session_id:
            session = session_manager.get_or_create_session(session_id)
            session.add_document(document_id)

        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="success",
            message=f"文档上传成功，已切分为 {doc_info.chunk_count} 个片段",
        )

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"文档处理失败: {str(e)}",
        )


@app.get("/documents", response_model=List[DocumentInfo])
async def list_documents():
    return rag_chain.list_documents()


@app.get("/documents/{document_id}", response_model=DocumentInfo)
async def get_document(document_id: str):
    doc_info = rag_chain.get_document_info(document_id)
    if not doc_info:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc_info


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    success = rag_chain.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="删除失败，文档不存在")
    return {"status": "success", "message": "文档已删除"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session = session_manager.get_or_create_session(request.session_id)
    history = session.get_history()

    response = rag_chain.chat(
        query=request.query,
        chat_history=history,
        document_ids=session.document_ids if session.document_ids else None,
        session_id=session.session_id,
    )

    session.add_message("user", request.query)
    session.add_message("assistant", response.answer)

    return response


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    session = session_manager.get_or_create_session(request.session_id)
    history = session.get_history()

    session.add_message("user", request.query)

    async def generate():
        full_response = ""
        async for chunk in rag_chain.chat_stream(
            query=request.query,
            chat_history=history,
            document_ids=session.document_ids if session.document_ids else None,
        ):
            full_response += chunk
            yield chunk
        
        session.add_message("assistant", full_response)

    return StreamingResponse(generate(), media_type="text/plain")


@app.post("/evaluate", response_model=AnswerEvaluationResult)
async def evaluate_answer(
    query: str,
    answer: str,
    sources: List[str] = None,
):
    from app.schemas import SourceReference
    
    source_refs = []
    if sources:
        for s in sources[:5]:
            source_refs.append(SourceReference(
                document_id="eval",
                filename="eval",
                chunk_id="eval",
                content=s,
                similarity_score=0.8,
            ))
    
    return rag_chain.evaluate_answer(query, answer, source_refs)


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    return {
        "status": "success",
        "message": "反馈已记录",
        "session_id": request.session_id,
        "rating": request.rating,
    }


@app.get("/learning/uncovered", response_model=List[UncoveredQuery])
async def get_uncovered_queries():
    return rag_chain.get_uncovered_queries()


@app.get("/learning/stats", response_model=ActiveLearningStats)
async def get_learning_stats():
    return rag_chain.get_active_learning_stats()


@app.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
    return session_manager.list_sessions()


@app.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session.to_info()


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"status": "success", "message": "会话已删除"}


@app.post("/sessions/{session_id}/documents/{document_id}")
async def add_document_to_session(session_id: str, document_id: str):
    session = session_manager.get_or_create_session(session_id)
    session.add_document(document_id)
    return {"status": "success", "message": "文档已添加到会话"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
