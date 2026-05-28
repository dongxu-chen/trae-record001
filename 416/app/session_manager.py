import uuid
from datetime import datetime
from typing import List, Optional, Dict
from app.config import get_settings
from app.schemas import ChatMessage, SessionInfo


class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_active = datetime.now()
        self.messages: List[ChatMessage] = []
        self.document_ids: List[str] = []

    def add_message(self, role: str, content: str):
        settings = get_settings()
        self.messages.append(ChatMessage(role=role, content=content))
        self.last_active = datetime.now()
        
        if len(self.messages) > settings.MAX_SESSION_HISTORY * 2:
            self.messages = self.messages[-settings.MAX_SESSION_HISTORY * 2 :]

    def get_history(self, limit: Optional[int] = None) -> List[ChatMessage]:
        settings = get_settings()
        limit = limit or settings.MAX_SESSION_HISTORY
        return self.messages[-limit * 2 :]

    def add_document(self, document_id: str):
        if document_id not in self.document_ids:
            self.document_ids.append(document_id)

    def to_info(self) -> SessionInfo:
        return SessionInfo(
            session_id=self.session_id,
            created_at=self.created_at,
            last_active=self.last_active,
            message_count=len(self.messages),
            document_ids=self.document_ids.copy(),
        )


class SessionManager:
    _instance = None
    _sessions: Dict[str, Session] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def create_session(self, session_id: Optional[str] = None) -> Session:
        session_id = session_id or str(uuid.uuid4())
        if session_id in self._sessions:
            return self._sessions[session_id]
        
        session = Session(session_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        return self.create_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> List[SessionInfo]:
        return [session.to_info() for session in self._sessions.values()]

    def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> Optional[Session]:
        session = self.get_session(session_id)
        if session:
            session.add_message(role, content)
            return session
        return None

    def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[ChatMessage]:
        session = self.get_session(session_id)
        if session:
            return session.get_history(limit)
        return []


def get_session_manager() -> SessionManager:
    return SessionManager()
