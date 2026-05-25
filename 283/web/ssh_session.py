import threading
import paramiko
import time
import uuid
from typing import Dict, Optional, Callable
from queue import Queue, Empty
from core.host_manager import Host, HostManager
from config import SSH_TIMEOUT


class SSHSession:
    def __init__(self, host: Host, output_callback: Optional[Callable] = None):
        self.host = host
        self.output_callback = output_callback
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.shell: Optional[paramiko.Channel] = None
        self.session_id = str(uuid.uuid4())
        self.is_connected = False
        self._read_thread: Optional[threading.Thread] = None
        self._write_queue: Queue = Queue()
        self._write_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def connect(self, term: str = 'xterm', cols: int = 80, rows: int = 24) -> bool:
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.host.ip,
                'port': self.host.port,
                'username': self.host.username,
                'timeout': SSH_TIMEOUT,
                'banner_timeout': SSH_TIMEOUT
            }
            
            if self.host.private_key:
                import io
                private_key = paramiko.RSAKey.from_private_key(
                    io.StringIO(self.host.private_key)
                )
                connect_kwargs['pkey'] = private_key
            elif self.host.password:
                connect_kwargs['password'] = self.host.password
            
            self.ssh_client.connect(**connect_kwargs)
            
            self.shell = self.ssh_client.invoke_shell(
                term=term,
                width=cols,
                height=rows
            )
            self.shell.setblocking(0)
            
            self.is_connected = True
            
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            
            self._write_thread = threading.Thread(target=self._write_loop, daemon=True)
            self._write_thread.start()
            
            return True
        except Exception as e:
            self._cleanup()
            raise e

    def _read_loop(self):
        while not self._stop_event.is_set() and self.is_connected:
            try:
                if self.shell and self.shell.recv_ready():
                    data = self.shell.recv(4096)
                    if data:
                        decoded_data = data.decode('utf-8', errors='replace')
                        if self.output_callback:
                            self.output_callback(decoded_data)
                time.sleep(0.01)
            except Exception as e:
                if self.output_callback:
                    self.output_callback(f"\r\n\x1b[31mConnection error: {e}\x1b[0m\r\n")
                break

    def _write_loop(self):
        while not self._stop_event.is_set() and self.is_connected:
            try:
                data = self._write_queue.get(timeout=0.1)
                if self.shell and self.shell.send_ready():
                    self.shell.send(data)
            except Empty:
                continue
            except Exception as e:
                break

    def send(self, data: str):
        if self.is_connected:
            self._write_queue.put(data)

    def resize(self, cols: int, rows: int):
        if self.shell:
            try:
                self.shell.resize_pty(width=cols, height=rows)
            except Exception:
                pass

    def _cleanup(self):
        self.is_connected = False
        self._stop_event.set()
        
        if self.shell:
            try:
                self.shell.close()
            except:
                pass
            self.shell = None
        
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except:
                pass
            self.ssh_client = None

    def close(self):
        self._cleanup()
        if self._read_thread:
            self._read_thread.join(timeout=1)
        if self._write_thread:
            self._write_thread.join(timeout=1)

    def __del__(self):
        self.close()


class SSHSessionManager:
    def __init__(self):
        self.sessions: Dict[str, SSHSession] = {}
        self._lock = threading.Lock()
        self.host_manager = HostManager()

    def create_session(self, hostname: str, output_callback: Optional[Callable] = None) -> Optional[SSHSession]:
        host = self.host_manager.get_host(hostname)
        if not host:
            return None
        
        session = SSHSession(host, output_callback)
        with self._lock:
            self.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[SSHSession]:
        with self._lock:
            return self.sessions.get(session_id)

    def close_session(self, session_id: str):
        with self._lock:
            session = self.sessions.pop(session_id, None)
            if session:
                session.close()

    def cleanup_idle(self, idle_timeout: int = 300):
        pass
