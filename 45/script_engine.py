import threading
import time
import re
import math

HAS_LUA = False
try:
    import lupa
    HAS_LUA = True
except ImportError:
    try:
        import lua as lunatic
        import lua_python
        HAS_LUA = True
    except ImportError:
        pass


class ScriptEngine:
    def __init__(self, serial_worker=None, on_data=None, on_log=None, on_error=None):
        self.serial_worker = serial_worker
        self.on_data = on_data
        self.on_log = on_log
        self.on_error = on_error

        self._thread = None
        self._running = False
        self._stop_event = threading.Event()
        self._rx_buffer = bytearray()
        self._rx_lock = threading.Lock()

        self._variables = {}
        self._rx_callbacks = []

    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)

    def _err(self, msg):
        if self.on_error:
            self.on_error(msg)

    def _emit(self, key, value):
        if self.on_data:
            self.on_data(key, value)
        if self.serial_worker:
            self.serial_worker.post_script_data(key, value)

    def feed_rx(self, data):
        with self._rx_lock:
            self._rx_buffer.extend(data)

    def _create_lua_runtime(self):
        if not HAS_LUA:
            return None
        try:
            lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        except Exception:
            try:
                lua = lunatic.lua()
            except Exception:
                return None

        lua.globals().send = self._lua_send
        lua.globals().send_hex = self._lua_send_hex
        lua.globals().read = self._lua_read
        lua.globals().read_line = self._lua_read_line
        lua.globals().sleep = self._lua_sleep
        lua.globals().emit = self._lua_emit
        lua.globals().log = self._lua_log
        lua.globals().clear_rx = self._lua_clear_rx
        lua.globals().available = self._lua_available
        lua.globals().match = self._lua_match
        lua.globals().parse_number = self._lua_parse_number
        lua.globals().wait_for = self._lua_wait_for
        return lua

    def _lua_send(self, text):
        if self.serial_worker:
            self.serial_worker.send_data(text, tag='script')

    def _lua_send_hex(self, hex_str):
        if self.serial_worker:
            self.serial_worker.send_data(hex_str, is_hex=True, tag='script')

    def _lua_read(self, n=None):
        start = time.time()
        timeout = 5.0
        while self._running:
            with self._rx_lock:
                if n is None and len(self._rx_buffer) > 0:
                    n = len(self._rx_buffer)
                if n is not None and len(self._rx_buffer) >= n:
                    data = bytes(self._rx_buffer[:n])
                    del self._rx_buffer[:n]
                    return data.decode('utf-8', errors='replace')
            if time.time() - start > timeout:
                break
            time.sleep(0.01)
        return ''

    def _lua_read_line(self, delimiter='\n'):
        delimiter_bytes = delimiter.encode('utf-8') if isinstance(delimiter, str) else bytes(delimiter)
        start = time.time()
        timeout = 5.0
        while self._running:
            with self._rx_lock:
                idx = self._rx_buffer.find(delimiter_bytes)
                if idx >= 0:
                    line = bytes(self._rx_buffer[:idx])
                    del self._rx_buffer[:idx + len(delimiter_bytes)]
                    return line.decode('utf-8', errors='replace')
            if time.time() - start > timeout:
                break
            time.sleep(0.01)
        return ''

    def _lua_sleep(self, ms):
        t = max(0.001, float(ms) / 1000.0)
        end = time.time() + t
        while self._running and time.time() < end:
            time.sleep(min(0.01, end - time.time()))

    def _lua_emit(self, key, value):
        self._emit(key, float(value))

    def _lua_log(self, msg):
        self._log(str(msg))

    def _lua_clear_rx(self):
        with self._rx_lock:
            self._rx_buffer.clear()

    def _lua_available(self):
        with self._rx_lock:
            return len(self._rx_buffer)

    def _lua_match(self, pattern, text=None):
        if text is None:
            text = self._lua_read_line()
        if not text:
            return None
        m = re.search(pattern, text)
        if not m:
            return None
        if m.lastindex and m.lastindex > 0:
            return m.groups()
        return m.group(0)

    def _lua_parse_number(self, s):
        try:
            return float(s)
        except Exception:
            return None

    def _lua_wait_for(self, text, timeout_ms=5000):
        pattern_bytes = text.encode('utf-8') if isinstance(text, str) else bytes(text)
        end = time.time() + (timeout_ms / 1000.0)
        while self._running and time.time() < end:
            with self._rx_lock:
                idx = self._rx_buffer.find(pattern_bytes)
                if idx >= 0:
                    return True
            time.sleep(0.01)
        return False

    def run(self, code):
        self.stop()
        self._stop_event.clear()
        self._running = True

        def _task():
            try:
                if HAS_LUA:
                    self._run_lua(code)
                else:
                    self._run_python_sandbox(code)
            except Exception as e:
                self._err(f'脚本执行错误: {e}')
            finally:
                self._running = False

        self._thread = threading.Thread(target=_task, daemon=True)
        self._thread.start()

    def _run_lua(self, code):
        lua = self._create_lua_runtime()
        if lua is None:
            self._err('未找到 Lua 运行时，请安装 lupa')
            return
        lua.execute(code)

    def _run_python_sandbox(self, code):
        self._log('警告: 未找到 Lua 运行时，使用 Python 沙盒模式执行')

        env = {
            'send': self._lua_send,
            'send_hex': self._lua_send_hex,
            'read': self._lua_read,
            'read_line': self._lua_read_line,
            'sleep': self._lua_sleep,
            'emit': self._lua_emit,
            'log': self._lua_log,
            'clear_rx': self._lua_clear_rx,
            'available': self._lua_available,
            'match': self._lua_match,
            'parse_number': self._lua_parse_number,
            'wait_for': self._lua_wait_for,
            'math': math,
            'time': time,
        }

        try:
            compiled = compile(code, '<script>', 'exec')
            exec(compiled, {'__builtins__': {}}, env)
        except Exception as e:
            raise

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def is_running(self):
        return self._running

    def register_rx_callback(self, callback):
        self._rx_callbacks.append(callback)
        return callback

    def unregister_rx_callback(self, callback):
        if callback in self._rx_callbacks:
            self._rx_callbacks.remove(callback)
