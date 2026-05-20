import numpy as np
import time
from threading import Thread, Lock
from collections import deque
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass
from enum import Enum

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, LogLevels


class DeviceType(Enum):
    OPENBCI_CYTON = "openbci_cyton"
    OPENBCI_GANGLION = "openbci_ganglion"
    NEUROSKY_MINDWAVE = "neurosky_mindwave"
    MUSE = "muse"
    SYNTHETIC = "synthetic"


DEVICE_CONFIG = {
    DeviceType.OPENBCI_CYTON: {
        "board_id": BoardIds.CYTON_BOARD.value,
        "eeg_channels": list(range(1, 9)),
        "sampling_rate": 250,
        "name": "OpenBCI Cyton (8通道)"
    },
    DeviceType.OPENBCI_GANGLION: {
        "board_id": BoardIds.GANGLION_BOARD.value,
        "eeg_channels": list(range(1, 5)),
        "sampling_rate": 200,
        "name": "OpenBCI Ganglion (4通道)"
    },
    DeviceType.NEUROSKY_MINDWAVE: {
        "board_id": BoardIds.NEUROSKY_MINDWAVE_BOARD.value,
        "eeg_channels": [1],
        "sampling_rate": 512,
        "name": "NeuroSky MindWave"
    },
    DeviceType.MUSE: {
        "board_id": BoardIds.MUSE_2016_BOARD.value,
        "eeg_channels": list(range(1, 5)),
        "sampling_rate": 256,
        "name": "Muse 头环"
    },
    DeviceType.SYNTHETIC: {
        "board_id": BoardIds.SYNTHETIC_BOARD.value,
        "eeg_channels": list(range(1, 17)),
        "sampling_rate": 250,
        "name": "模拟设备 (测试用)"
    }
}


@dataclass
class EEGData:
    timestamp: float
    eeg_data: np.ndarray
    aux_data: Optional[np.ndarray] = None


class DataAcquisition:
    def __init__(self, device_type: DeviceType = DeviceType.SYNTHETIC):
        self.device_type = device_type
        self.config = DEVICE_CONFIG[device_type]
        
        self.board: Optional[BoardShim] = None
        self.params = BrainFlowInputParams()
        
        self._is_running = False
        self._is_streaming = False
        self._lock = Lock()
        
        self._buffer_size = 10000
        self._eeg_buffer = deque(maxlen=self._buffer_size)
        self._time_buffer = deque(maxlen=self._buffer_size)
        
        self._callbacks: List[Callable[[EEGData], None]] = []
        
        self._acquisition_thread: Optional[Thread] = None
        
        BoardShim.enable_dev_board_logger()
        
    def connect(self, serial_port: str = "", ip_address: str = "", ip_port: int = 0) -> bool:
        try:
            self.params.serial_port = serial_port
            self.params.ip_address = ip_address
            self.params.ip_port = ip_port
            
            self.board = BoardShim(self.config["board_id"], self.params)
            self.board.prepare_session()
            
            self._is_running = True
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
            
    def start_stream(self, buffer_size: int = 450000):
        if not self._is_running or self.board is None:
            return False
            
        try:
            self.board.start_stream(buffer_size)
            self._is_streaming = True
            
            self._acquisition_thread = Thread(target=self._data_loop, daemon=True)
            self._acquisition_thread.start()
            
            return True
        except Exception as e:
            print(f"启动流失败: {e}")
            return False
            
    def _data_loop(self):
        sampling_rate = self.config["sampling_rate"]
        eeg_channels = self.config["eeg_channels"]
        num_channels = len(eeg_channels)
        
        while self._is_streaming and self._is_running:
            try:
                data = self.board.get_current_board_data(10)
                
                if data.shape[1] > 0:
                    eeg_data = data[eeg_channels, :]
                    timestamps = data[-1, :]
                    
                    with self._lock:
                        for i in range(data.shape[1]):
                            self._eeg_buffer.append(eeg_data[:, i])
                            self._time_buffer.append(timestamps[i])
                            
                            eeg_sample = EEGData(
                                timestamp=timestamps[i],
                                eeg_data=eeg_data[:, i]
                            )
                            
                            for callback in self._callbacks:
                                callback(eeg_sample)
                                
                time.sleep(1.0 / sampling_rate * 5)
                
            except Exception as e:
                print(f"数据采集错误: {e}")
                break
                
    def get_latest_data(self, num_samples: int = 1000) -> tuple:
        with self._lock:
            if len(self._eeg_buffer) < num_samples:
                num_samples = len(self._eeg_buffer)
                
            eeg_data = np.array(list(self._eeg_buffer)[-num_samples:]).T
            times = np.array(list(self._time_buffer)[-num_samples:])
            
        return eeg_data, times
        
    def add_callback(self, callback: Callable[[EEGData], None]):
        self._callbacks.append(callback)
        
    def remove_callback(self, callback: Callable[[EEGData], None]):
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            
    def stop_stream(self):
        self._is_streaming = False
        
        if self._acquisition_thread:
            self._acquisition_thread.join(timeout=2.0)
            
    def disconnect(self):
        self.stop_stream()
        
        if self.board:
            try:
                self.board.stop_stream()
                self.board.release_session()
            except:
                pass
                
        self._is_running = False
        
    def get_sampling_rate(self) -> int:
        return self.config["sampling_rate"]
        
    def get_num_channels(self) -> int:
        return len(self.config["eeg_channels"])
        
    def get_channel_names(self) -> List[str]:
        num_channels = self.get_num_channels()
        return [f"EEG{i:02d}" for i in range(1, num_channels + 1)]
        
    @staticmethod
    def get_available_devices() -> Dict[str, str]:
        return {dev.value: DEVICE_CONFIG[dev]["name"] for dev in DeviceType}
