import numpy as np
from threading import Thread, Lock
from typing import Optional, Callable
from dataclasses import dataclass

try:
    from pylsl import StreamInlet, StreamOutlet, StreamInfo, resolve_stream, local_clock
    LSL_AVAILABLE = True
except ImportError:
    LSL_AVAILABLE = False
    print("pylsl 未安装，LSL功能将不可用")


@dataclass
class LSLStreamInfo:
    name: str
    type: str
    channel_count: int
    sampling_rate: float
    channel_format: str
    source_id: str = ""


class LSLInput:
    def __init__(self):
        self.inlet: Optional[StreamInlet] = None
        self._is_running = False
        self._thread: Optional[Thread] = None
        self._lock = Lock()
        self._callbacks: list[Callable[[np.ndarray, float], None]] = []
        
    def connect(self, stream_type: str = "EEG", timeout: float = 5.0) -> bool:
        if not LSL_AVAILABLE:
            return False
            
        try:
            streams = resolve_stream('type', stream_type, timeout)
            if len(streams) == 0:
                return False
                
            self.inlet = StreamInlet(streams[0])
            self._is_running = True
            
            self._thread = Thread(target=self._receive_loop, daemon=True)
            self._thread.start()
            
            return True
        except Exception as e:
            print(f"LSL 连接错误: {e}")
            return False
            
    def _receive_loop(self):
        while self._is_running and self.inlet:
            try:
                sample, timestamp = self.inlet.pull_sample(timeout=0.1)
                if sample is not None:
                    with self._lock:
                        for callback in self._callbacks:
                            callback(np.array(sample), timestamp)
            except Exception as e:
                print(f"LSL 接收错误: {e}")
                break
                
    def add_callback(self, callback: Callable[[np.ndarray, float], None]):
        with self._lock:
            self._callbacks.append(callback)
            
    def disconnect(self):
        self._is_running = False
        
        if self._thread:
            self._thread.join(timeout=2.0)
            
        if self.inlet:
            self.inlet.close_stream()
            self.inlet = None
            
    def get_info(self) -> Optional[LSLStreamInfo]:
        if not self.inlet:
            return None
            
        info = self.inlet.info()
        return LSLStreamInfo(
            name=info.name(),
            type=info.type(),
            channel_count=info.channel_count(),
            sampling_rate=info.nominal_srate(),
            channel_format=info.channel_format()
        )


class LSLOutput:
    def __init__(self, stream_info: LSLStreamInfo):
        self.stream_info = stream_info
        self.outlet: Optional[StreamOutlet] = None
        self._lock = Lock()
        
    def create_stream(self) -> bool:
        if not LSL_AVAILABLE:
            return False
            
        try:
            info = StreamInfo(
                name=self.stream_info.name,
                type=self.stream_info.type,
                channel_count=self.stream_info.channel_count,
                nominal_srate=self.stream_info.sampling_rate,
                channel_format=self.stream_info.channel_format,
                source_id=self.stream_info.source_id
            )
            
            channels = info.desc().append_child("channels")
            for i in range(self.stream_info.channel_count):
                ch = channels.append_child("channel")
                ch.append_child_value("label", f"EEG{i+1}")
                ch.append_child_value("unit", "microvolts")
                ch.append_child_value("type", "EEG")
                
            self.outlet = StreamOutlet(info)
            return True
        except Exception as e:
            print(f"创建LSL输出流错误: {e}")
            return False
            
    def push_sample(self, data: np.ndarray, timestamp: Optional[float] = None):
        if not self.outlet:
            return
            
        with self._lock:
            if timestamp is None:
                timestamp = local_clock()
            self.outlet.push_sample(data.tolist(), timestamp)
            
    def push_chunk(self, data: np.ndarray, timestamps: Optional[np.ndarray] = None):
        if not self.outlet:
            return
            
        with self._lock:
            if timestamps is None:
                self.outlet.push_chunk(data.tolist())
            else:
                self.outlet.push_chunk(data.tolist(), timestamps.tolist())
                
    def close(self):
        with self._lock:
            if self.outlet:
                self.outlet = None


class BandPowerLSLOutput:
    def __init__(self, source_id: str = "bandpower"):
        self.band_names = ['delta', 'theta', 'alpha', 'beta', 'gamma']
        stream_info = LSLStreamInfo(
            name="EEG_BandPower",
            type="BandPower",
            channel_count=5,
            sampling_rate=10.0,
            channel_format="float32",
            source_id=source_id
        )
        self.lsl_output = LSLOutput(stream_info)
        self._initialized = False
        
    def initialize(self) -> bool:
        self._initialized = self.lsl_output.create_stream()
        return self._initialized
        
    def push_band_powers(self, band_powers: dict):
        if not self._initialized:
            return
            
        power_values = [band_powers.get(band, 0.0) for band in self.band_names]
        self.lsl_output.push_sample(np.array(power_values))
        
    def close(self):
        self.lsl_output.close()
