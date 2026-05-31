import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from datetime import datetime
import logging

from models import NewsArticle, ClusterTopic, TopicLifeCycle
from news_stream_processor import NewsStreamProcessor, MockNewsGenerator
from websocket_server import ConnectionManager
from neo4j_store import Neo4jStore
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="新闻话题演化追踪系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()

processor = None
mock_generator = MockNewsGenerator()
neo4j_store = Neo4jStore()

@app.on_event("startup")
async def startup_event():
    global processor
    logger.info("Initializing News Stream Processor...")
    try:
        processor = NewsStreamProcessor()
        processor.set_callbacks(
            on_topic_update=manager.broadcast_topic_update,
            on_evolution=manager.broadcast_evolution,
            on_graph_incremental_update=manager.broadcast_graph_incremental_update,
            on_topic_warning=manager.broadcast_topic_warning
        )
        logger.info("News Stream Processor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize processor: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if processor:
        processor.close()
    neo4j_store.close()
    logger.info("Application shutdown complete")

@app.post("/api/news", response_model=Dict)
async def receive_news(article: NewsArticle):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    topic_id = await processor.process_article(article)
    
    await manager.broadcast_new_article({
        "id": article.id,
        "title": article.title,
        "source": article.source,
        "publish_time": article.publish_time.isoformat(),
        "topic_id": topic_id
    })
    
    return {"status": "success", "topic_id": topic_id}

@app.get("/api/topics")
async def get_topics(lifecycle: Optional[str] = None, min_size: Optional[int] = None):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    if lifecycle:
        try:
            lifecycle_enum = TopicLifeCycle(lifecycle)
            topics = neo4j_store.get_topics_by_lifecycle(lifecycle_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid lifecycle value")
    else:
        topics = processor.get_active_topics(min_size)
    
    return {
        "count": len(topics),
        "topics": [t.model_dump() if hasattr(t, 'model_dump') else t for t in topics]
    }

@app.get("/api/topics/{topic_id}")
async def get_topic(topic_id: str):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    topic = processor.get_topic(topic_id)
    if not topic:
        topic_data = neo4j_store.get_topic(topic_id)
        if not topic_data:
            raise HTTPException(status_code=404, detail="Topic not found")
        return {"topic": topic_data}
    
    influence = processor.get_topic_influence(topic_id)
    
    return {
        "topic": topic.model_dump(),
        "influence": influence.model_dump() if influence else None
    }

@app.get("/api/topics/{topic_id}/articles")
async def get_topic_articles(topic_id: str, limit: int = 20):
    articles = neo4j_store.get_topic_articles(topic_id, limit)
    return {"count": len(articles), "articles": articles}

@app.get("/api/evolution/graph")
async def get_evolution_graph():
    if not processor:
        graph_data = neo4j_store.get_evolution_graph()
        return graph_data
    
    graph_data = processor.get_evolution_graph()
    return graph_data

@app.get("/api/evolution/graph/full")
async def get_full_graph_with_versions():
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    graph_data = processor.get_full_graph_with_versions()
    return graph_data

@app.get("/api/evolution/graph/incremental")
async def get_incremental_graph_update():
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    update_data = processor.get_incremental_update()
    return update_data

@app.get("/api/evolution/chain/{topic_id}")
async def get_evolution_chain(topic_id: str):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    chain = processor.get_evolution_chain(topic_id)
    return {"topic_id": topic_id, "chain": chain}

@app.get("/api/bursting")
async def get_bursting_topics():
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    bursting = processor.get_bursting_topics()
    return {
        "count": len(bursting),
        "topics": [t.model_dump() for t in bursting]
    }

@app.get("/api/warnings")
async def get_warnings(min_level: Optional[str] = None, history: bool = False, limit: int = 20):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    if history:
        warnings = processor.get_warning_history(limit)
    else:
        warnings = processor.get_active_warnings(min_level)
    
    return {
        "count": len(warnings),
        "warnings": [w.model_dump() for w in warnings]
    }

@app.post("/api/warnings/{topic_id}/acknowledge")
async def acknowledge_warning(topic_id: str):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    success = processor.acknowledge_warning(topic_id)
    return {"success": success}

@app.get("/api/topics/{topic_id}/propagation")
async def get_topic_propagation(topic_id: str):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    propagation = processor.get_propagation_path(topic_id)
    if not propagation:
        raise HTTPException(status_code=404, detail="Propagation data not found")
    
    return propagation.model_dump()

@app.get("/api/topics/{topic_id}/ignition")
async def get_ignition_articles(topic_id: str):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    articles = processor.get_ignition_articles(topic_id)
    return {
        "count": len(articles),
        "ignition_points": articles
    }

@app.post("/api/comparison")
async def compare_topics(
    topic_ids: List[str] = Body(..., embed=True),
    time_range_hours: Optional[int] = Body(None, embed=True)
):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    if len(topic_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 topic IDs required")
    
    result = processor.compare_topics(topic_ids, time_range_hours)
    if not result:
        raise HTTPException(status_code=404, detail="Not enough data for comparison")
    
    return result.model_dump()

@app.get("/api/comparison/available")
async def get_comparable_topics():
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    topic_ids = processor.get_comparable_topics()
    topics = []
    for tid in topic_ids:
        topic = processor.get_topic(tid)
        if topic:
            topics.append({
                "topic_id": tid,
                "name": topic.name,
                "size": topic.size,
                "lifecycle": topic.lifecycle.value
            })
    
    return {
        "count": len(topics),
        "topics": topics
    }

@app.get("/api/topics/{topic_id}/similar")
async def get_similar_topics(topic_id: str, threshold: float = 0.5):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    similar_ids = processor.find_similar_topics(topic_id, threshold)
    topics = []
    for tid in similar_ids:
        topic = processor.get_topic(tid)
        if topic:
            topics.append({
                "topic_id": tid,
                "name": topic.name,
                "size": topic.size,
                "lifecycle": topic.lifecycle.value
            })
    
    return {
        "count": len(topics),
        "similar_topics": topics
    }

@app.post("/api/mock/generate")
async def generate_mock_news(count: int = 1):
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    results = []
    for _ in range(count):
        article = mock_generator.generate_news()
        topic_id = await processor.process_article(article)
        results.append({
            "article_id": article.id,
            "title": article.title,
            "topic_id": topic_id
        })
    
    return {"generated": len(results), "results": results}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                        websocket
                    )
                elif message.get("type") == "subscribe":
                    topics = message.get("topics", [])
                    if websocket in manager.client_topics:
                        manager.client_topics[websocket].update(topics)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "processor_initialized": processor is not None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.WEBSOCKET_HOST,
        port=settings.WEBSOCKET_PORT,
        reload=True
    )
