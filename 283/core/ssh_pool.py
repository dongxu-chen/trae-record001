import threading
import time
from typing import Dict, Optional, List
from collections import deque
from .host_manager import Host
from .ssh_client import SSHClient
from config import CONCURRENT_LIMIT, SSH_TIMEOUT


class SSHConnectionPool:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._pools: Dict[str, deque] = {}
        self._pool_locks: Dict[str, threading.Lock] = {}
        self._active_connections: Dict[str, int] = {}
        self._max_pool_size = CONCURRENT_LIMIT
        self._idle_timeout = 300
        self._cleanup_thread = threading.Thread(target=self._cleanup_idle, daemon=True)
        self._cleanup_thread.start()

    def _get_pool_key(self, host: Host) -> str:
        return f"{host.username}@{host.ip}:{host.port}"

    def _ensure_pool(self, host: Host):
        key = self._get_pool_key(host)
        if key not in self._pools:
            self._pools[key] = deque()
            self._pool_locks[key] = threading.Lock()
            self._active_connections[key] = 0

    def get_connection(self, host: Host) -> Optional[SSHClient]:
        key = self._get_pool_key(host)
        self._ensure_pool(host)

        with self._pool_locks[key]:
            while self._pools[key]:
                client, last_used = self._pools[key].popleft()
                if time.time() - last_used < self._idle_timeout:
                    try:
                        if self._test_connection(client):
                            self._active_connections[key] += 1
                            return client
                    except:
                        try:
                            client.close()
                        except:
                            pass
                else:
                    try:
                        client.close()
                    except:
                        pass

            if self._active_connections[key] < self._max_pool_size:
                try:
                    client = SSHClient(host)
                    client.connect()
                    self._active_connections[key] += 1
                    return client
                except Exception as e:
                    raise e

        return None

    def _test_connection(self, client: SSHClient) -> bool:
        try:
            transport = client.client.get_transport()
            if transport and transport.is_active():
                transport.send_ignore()
                return True
        except:
            pass
        return False

    def release_connection(self, host: Host, client: SSHClient):
        key = self._get_pool_key(host)
        self._ensure_pool(host)

        with self._pool_locks[key]:
            self._active_connections[key] -= 1
            if len(self._pools[key]) < self._max_pool_size:
                self._pools[key].append((client, time.time()))
            else:
                try:
                    client.close()
                except:
                    pass

    def _cleanup_idle(self):
        while True:
            time.sleep(60)
            for key in list(self._pools.keys()):
                with self._pool_locks[key]:
                    while self._pools[key]:
                        client, last_used = self._pools[key][0]
                        if time.time() - last_used >= self._idle_timeout:
                            self._pools[key].popleft()
                            try:
                                client.close()
                            except:
                                pass
                        else:
                            break

    def close_all(self):
        for key in list(self._pools.keys()):
            with self._pool_locks[key]:
                while self._pools[key]:
                    client, _ = self._pools[key].popleft()
                    try:
                        client.close()
                    except:
                        pass

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        stats = {}
        for key in self._pools.keys():
            with self._pool_locks[key]:
                stats[key] = {
                    'idle': len(self._pools[key]),
                    'active': self._active_connections.get(key, 0)
                }
        return stats


class PooledSSHClient:
    def __init__(self, host: Host, pool: Optional[SSHConnectionPool] = None):
        self.host = host
        self.pool = pool or SSHConnectionPool()
        self.client = None

    def __enter__(self):
        self.client = self.pool.get_connection(self.host)
        if not self.client:
            raise Exception("Failed to get SSH connection from pool")
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.pool.release_connection(self.host, self.client)


def get_pooled_client(host: Host) -> PooledSSHClient:
    return PooledSSHClient(host)
