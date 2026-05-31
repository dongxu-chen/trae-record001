import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Any
from urllib.parse import urlparse, urljoin
import logging
import uuid
import copy
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Session:
    def __init__(self, session_id: str, headers: Dict[str, str], verify_ssl: bool = False):
        self.session_id = session_id
        self.headers = headers.copy()
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.cookies = {}
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.request_count = 0

    def update_headers(self, headers: Dict[str, str]):
        self.headers.update(headers)

    def get_headers(self) -> Dict[str, str]:
        return self.headers.copy()

    def record_usage(self):
        self.last_used_at = time.time()
        self.request_count += 1

    def __repr__(self):
        return f"Session(id={self.session_id}, requests={self.request_count})"


class RequestEngine:
    def __init__(self, config):
        self.config = config
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self._setup_base_auth()
        self.sessions: Dict[str, Session] = {}
        self.role_sessions: Dict[str, Session] = {}
        self.session_pool: asyncio.Queue = asyncio.Queue()
        self._initialize_sessions()
        self._initialize_role_sessions()

    def _setup_base_auth(self):
        if self.config.auth_type == "bearer" and self.config.auth_token:
            self.base_headers["Authorization"] = f"Bearer {self.config.auth_token}"
        elif self.config.auth_type == "basic" and self.config.auth_token:
            import base64
            encoded = base64.b64encode(self.config.auth_token.encode()).decode()
            self.base_headers["Authorization"] = f"Basic {encoded}"
        elif self.config.auth_type == "custom" and self.config.auth_headers:
            self.base_headers.update(self.config.auth_headers)

    def _initialize_sessions(self):
        if not getattr(self.config, 'enable_session_isolation', True):
            return
        
        for i in range(self.config.concurrency):
            session_id = f"session_{i}_{uuid.uuid4().hex[:8]}"
            session = Session(
                session_id=session_id,
                headers=self.base_headers.copy(),
                verify_ssl=self.config.verify_ssl
            )
            self.sessions[session_id] = session
            self.session_pool.put_nowait(session_id)

    def _initialize_role_sessions(self):
        roles = getattr(self.config, 'roles', None)
        if not roles:
            return
        
        for role in roles:
            role_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            if role.auth_type == "bearer" and role.auth_token:
                role_headers["Authorization"] = f"Bearer {role.auth_token}"
            elif role.auth_type == "basic" and role.auth_token:
                import base64
                encoded = base64.b64encode(role.auth_token.encode()).decode()
                role_headers["Authorization"] = f"Basic {encoded}"
            elif role.auth_type == "custom" and role.auth_headers:
                role_headers.update(role.auth_headers)
            
            session_id = f"role_{role.name}_{uuid.uuid4().hex[:8]}"
            session = Session(
                session_id=session_id,
                headers=role_headers,
                verify_ssl=self.config.verify_ssl
            )
            self.role_sessions[role.name] = session

    async def acquire_session(self) -> str:
        if not getattr(self.config, 'enable_session_isolation', True):
            return "default"
        return await self.session_pool.get()

    async def release_session(self, session_id: str):
        if session_id in self.sessions:
            await self.session_pool.put(session_id)

    def get_session(self, session_id: str = None, role_name: str = None) -> Session:
        if role_name and role_name in self.role_sessions:
            session = self.role_sessions[role_name]
            session.record_usage()
            return session
        
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.record_usage()
            return session
        
        return Session(
            session_id="default",
            headers=self.base_headers.copy(),
            verify_ssl=self.config.verify_ssl
        )

    def get_role_session(self, role_name: str) -> Session:
        return self.get_session(role_name=role_name)

    def get_all_role_names(self) -> List[str]:
        return list(self.role_sessions.keys())

    def _make_request_sync(self, session: Session, method, url, **kwargs):
        headers = kwargs.pop("headers", {})
        request_headers = session.get_headers()
        request_headers.update(headers)
        kwargs["headers"] = request_headers
        kwargs["timeout"] = self.config.timeout
        
        for attempt in range(self.config.max_retries):
            try:
                response = session.session.request(method, url, **kwargs)
                
                session.cookies.update(dict(response.cookies))
                
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text,
                    "response_time": response.elapsed.total_seconds(),
                    "url": response.url,
                    "session_id": session.session_id,
                    "cookies": session.cookies.copy(),
                    "content_length": len(response.text),
                    "content_hash": hash(response.text)
                }
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt+1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return {
                        "error": str(e), 
                        "status_code": 0,
                        "session_id": session.session_id
                    }
                time.sleep(1)
        return {
            "error": "Max retries exceeded", 
            "status_code": 0,
            "session_id": session.session_id
        }

    async def get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None,
                session_id: str = None, role_name: str = None):
        loop = asyncio.get_event_loop()
        session = self.get_session(session_id, role_name)
        
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool, self._make_request_sync, session, "GET", url, {"params": params, "headers": headers}
            )
        return result

    async def post(self, url: str, data: Optional[Any] = None, json: Optional[Dict] = None, 
                  headers: Optional[Dict] = None, session_id: str = None, role_name: str = None):
        loop = asyncio.get_event_loop()
        session = self.get_session(session_id, role_name)
        
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool, self._make_request_sync, session, "POST", url, 
                {"data": data, "json": json, "headers": headers}
            )
        return result

    async def put(self, url: str, data: Optional[Any] = None, json: Optional[Dict] = None,
                 headers: Optional[Dict] = None, session_id: str = None, role_name: str = None):
        loop = asyncio.get_event_loop()
        session = self.get_session(session_id, role_name)
        
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool, self._make_request_sync, session, "PUT", url, 
                {"data": data, "json": json, "headers": headers}
            )
        return result

    async def delete(self, url: str, headers: Optional[Dict] = None,
                    session_id: str = None, role_name: str = None):
        loop = asyncio.get_event_loop()
        session = self.get_session(session_id, role_name)
        
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool, self._make_request_sync, session, "DELETE", url, {"headers": headers}
            )
        return result

    async def request_with_role(self, method: str, url: str, role_name: str, **kwargs) -> Dict[str, Any]:
        method_lower = method.lower()
        if method_lower == "get":
            return await self.get(url, role_name=role_name, **kwargs)
        elif method_lower == "post":
            return await self.post(url, role_name=role_name, **kwargs)
        elif method_lower == "put":
            return await self.put(url, role_name=role_name, **kwargs)
        elif method_lower == "delete":
            return await self.delete(url, role_name=role_name, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

    def compare_responses(self, resp1: Dict[str, Any], resp2: Dict[str, Any], 
                         compare_fields: List[str] = None) -> Dict[str, Any]:
        if compare_fields is None:
            compare_fields = ["status_code", "content_length", "content_hash"]
        
        differences = {}
        similarities = {}
        
        for field in compare_fields:
            val1 = resp1.get(field)
            val2 = resp2.get(field)
            if val1 == val2:
                similarities[field] = val1
            else:
                differences[field] = {"old": val1, "new": val2}
        
        if "content" in resp1 and "content" in resp2:
            content1 = resp1.get("content", "")
            content2 = resp2.get("content", "")
            if content1 == content2:
                similarities["content"] = "identical"
            else:
                similarity = self._calculate_similarity(content1, content2)
                differences["content_similarity"] = similarity
        
        return {
            "similarities": similarities,
            "differences": differences,
            "is_identical": len(differences) == 0,
            "similarity_score": 1 - (len(differences) / max(len(compare_fields), 1))
        }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)

    def build_url(self, base_url: str, path: str) -> str:
        return urljoin(base_url, path)

    def parse_url_params(self, url: str) -> Dict[str, str]:
        parsed = urlparse(url)
        params = {}
        if parsed.query:
            for pair in parsed.query.split("&"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    params[key] = value
        return params

    def get_session_stats(self) -> Dict[str, Any]:
        return {
            "total_sessions": len(self.sessions),
            "role_sessions": list(self.role_sessions.keys()),
            "session_details": {
                sid: {
                    "request_count": sess.request_count,
                    "age": time.time() - sess.created_at,
                    "last_used": time.time() - sess.last_used_at
                }
                for sid, sess in self.sessions.items()
            }
        }
