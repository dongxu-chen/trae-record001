import asyncio
import json
from datetime import datetime
from typing import Set, Dict
from fastapi import WebSocket, WebSocketDisconnect
from models import ClusterTopic, TopicEvolution, WebSocketMessage, TopicWarning

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.client_topics: Dict[WebSocket, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.client_topics[websocket] = set()
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket in self.client_topics:
            del self.client_topics[websocket]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass
    
    async def broadcast_topic_update(self, topic: ClusterTopic):
        message = WebSocketMessage(
            type="topic_update",
            data={
                "topic_id": topic.topic_id,
                "name": topic.name,
                "keywords": topic.keywords,
                "size": topic.size,
                "lifecycle": topic.lifecycle.value,
                "influence_score": topic.influence_score,
                "trend_score": topic.trend_score,
                "updated_at": topic.updated_at.isoformat()
            },
            timestamp=datetime.now()
        )
        await self.broadcast(message.model_dump())
    
    async def broadcast_evolution(self, evolution: TopicEvolution):
        message = WebSocketMessage(
            type="evolution",
            data={
                "from_topic": evolution.from_topic,
                "to_topic": evolution.to_topic,
                "evolution_type": evolution.evolution_type,
                "similarity": evolution.similarity,
                "common_keywords": evolution.common_keywords,
                "timestamp": evolution.timestamp.isoformat()
            },
            timestamp=datetime.now()
        )
        await self.broadcast(message.model_dump())
    
    async def broadcast_new_article(self, article_data: dict):
        message = WebSocketMessage(
            type="new_article",
            data=article_data,
            timestamp=datetime.now()
        )
        await self.broadcast(message.model_dump())
    
    async def broadcast_graph_incremental_update(self, update_data: dict):
        message = WebSocketMessage(
            type="graph_incremental_update",
            data=update_data,
            timestamp=datetime.now()
        )
        await self.broadcast(message.model_dump())
    
    async def broadcast_topic_warning(self, warning: TopicWarning):
        message = WebSocketMessage(
            type="topic_warning",
            data={
                "warning_id": warning.warning_id,
                "topic_id": warning.topic_id,
                "topic_name": warning.topic_name,
                "warning_level": warning.warning_level,
                "warning_type": warning.warning_type,
                "confidence": warning.confidence,
                "predicted_burst_time": warning.predicted_burst_time.isoformat() if warning.predicted_burst_time else None,
                "message": warning.message,
                "created_at": warning.created_at.isoformat()
            },
            timestamp=datetime.now()
        )
        await self.broadcast(message.model_dump())
