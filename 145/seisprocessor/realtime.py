import numpy as np
import asyncio
import json
import threading
from collections import deque
from obspy import Stream, Trace, UTCDateTime
from typing import Callable, Dict, List, Optional


class CircularBuffer:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.timestamps = deque(maxlen=max_size)
    
    def push(self, data: np.ndarray, timestamp: Optional[UTCDateTime] = None):
        if timestamp is None:
            timestamp = UTCDateTime()
        
        for i, value in enumerate(data):
            self.buffer.append(value)
            self.timestamps.append(timestamp + i / len(data))
    
    def get_data(self) -> np.ndarray:
        return np.array(self.buffer)
    
    def get_times(self) -> List[UTCDateTime]:
        return list(self.timestamps)
    
    def clear(self):
        self.buffer.clear()
        self.timestamps.clear()
    
    def __len__(self) -> int:
        return len(self.buffer)


class RealTimeProcessor:
    def __init__(self, sampling_rate: float, buffer_size_seconds: float = 30.0):
        self.sampling_rate = sampling_rate
        self.buffer_size = int(buffer_size_seconds * sampling_rate)
        self.buffers: Dict[str, CircularBuffer] = {}
        self.processing_callbacks: List[Callable] = []
        self.is_running = False
        self._lock = threading.Lock()
    
    def add_station(self, station_id: str):
        with self._lock:
            if station_id not in self.buffers:
                self.buffers[station_id] = CircularBuffer(self.buffer_size)
    
    def remove_station(self, station_id: str):
        with self._lock:
            if station_id in self.buffers:
                del self.buffers[station_id]
    
    def add_data(self, station_id: str, data: np.ndarray, 
                 timestamp: Optional[UTCDateTime] = None):
        with self._lock:
            if station_id not in self.buffers:
                self.add_station(station_id)
            
            self.buffers[station_id].push(data, timestamp)
            
            for callback in self.processing_callbacks:
                try:
                    callback(station_id, data, timestamp)
                except Exception as e:
                    print(f"Error in callback: {e}")
    
    def add_callback(self, callback: Callable[[str, np.ndarray, Optional[UTCDateTime]], None]):
        self.processing_callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        if callback in self.processing_callbacks:
            self.processing_callbacks.remove(callback)
    
    def get_trace(self, station_id: str) -> Optional[Trace]:
        with self._lock:
            if station_id not in self.buffers:
                return None
            
            buffer = self.buffers[station_id]
            if len(buffer) == 0:
                return None
            
            data = buffer.get_data()
            start_time = buffer.timestamps[0]
            
            stats = {
                'network': station_id.split('.')[0] if '.' in station_id else 'XX',
                'station': station_id.split('.')[1] if '.' in station_id else station_id,
                'channel': 'HHZ',
                'sampling_rate': self.sampling_rate,
                'starttime': start_time
            }
            
            return Trace(data=data, header=stats)
    
    def get_stream(self) -> Stream:
        stream = Stream()
        with self._lock:
            for station_id in self.buffers:
                trace = self.get_trace(station_id)
                if trace:
                    stream.append(trace)
        return stream
    
    def clear_all(self):
        with self._lock:
            for buffer in self.buffers.values():
                buffer.clear()


class WebSocketSeismicServer:
    def __init__(self, host: str = 'localhost', port: int = 8765, 
                 sampling_rate: float = 100.0):
        self.host = host
        self.port = port
        self.sampling_rate = sampling_rate
        self.processor = RealTimeProcessor(sampling_rate)
        self.connections = set()
        self.server = None
    
    async def _handle_connection(self, websocket):
        self.connections.add(websocket)
        print(f"New connection. Total: {len(self.connections)}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data, websocket)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'error': 'Invalid JSON format'
                    }))
        finally:
            self.connections.remove(websocket)
            print(f"Connection closed. Total: {len(self.connections)}")
    
    async def _process_message(self, data: dict, websocket):
        msg_type = data.get('type', '')
        
        if msg_type == 'waveform_data':
            station_id = data.get('station_id', 'unknown')
            waveform = np.array(data.get('data', []))
            timestamp = UTCDateTime(data.get('timestamp', UTCDateTime()))
            
            self.processor.add_data(station_id, waveform, timestamp)
            
            await self._broadcast_to_clients({
                'type': 'update',
                'station_id': station_id,
                'samples_received': len(waveform),
                'timestamp': str(timestamp)
            })
        
        elif msg_type == 'request_trace':
            station_id = data.get('station_id', '')
            trace = self.processor.get_trace(station_id)
            
            if trace:
                await websocket.send(json.dumps({
                    'type': 'trace_data',
                    'station_id': station_id,
                    'data': trace.data.tolist(),
                    'starttime': str(trace.stats.starttime),
                    'sampling_rate': trace.stats.sampling_rate
                }))
        
        elif msg_type == 'request_stream':
            stream = self.processor.get_stream()
            stream_data = []
            for trace in stream:
                stream_data.append({
                    'station_id': f"{trace.stats.network}.{trace.stats.station}",
                    'data': trace.data.tolist(),
                    'starttime': str(trace.stats.starttime),
                    'sampling_rate': trace.stats.sampling_rate
                })
            
            await websocket.send(json.dumps({
                'type': 'stream_data',
                'traces': stream_data
            }))
    
    async def _broadcast_to_clients(self, message: dict):
        if self.connections:
            message_str = json.dumps(message)
            await asyncio.gather(
                *[ws.send(message_str) for ws in self.connections],
                return_exceptions=True
            )
    
    async def start(self):
        try:
            import websockets
            self.server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port
            )
            print(f"WebSocket server started at ws://{self.host}:{self.port}")
            print(f"Sampling rate: {self.sampling_rate} Hz")
        except ImportError:
            print("Warning: websockets package not installed.")
            print("Install with: pip install websockets")
            raise
    
    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("WebSocket server stopped")
    
    def run_server(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop_loop(loop)
        try:
            loop.run_until_complete(self.start())
            loop.run_forever()
        except KeyboardInterrupt:
            loop.run_until_complete(self.stop())
        finally:
            loop.close()


class WebSocketSeismicClient:
    def __init__(self, server_url: str = 'ws://localhost:8765'):
        self.server_url = server_url
        self.websocket = None
        self.is_connected = False
    
    async def connect(self):
        try:
            import websockets
            self.websocket = await websockets.connect(self.server_url)
            self.is_connected = True
            print(f"Connected to {self.server_url}")
        except ImportError:
            print("Warning: websockets package not installed.")
            raise
    
    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            print("Disconnected")
    
    async def send_waveform(self, station_id: str, data: np.ndarray, 
                            timestamp: Optional[UTCDateTime] = None):
        if not self.is_connected:
            raise RuntimeError("Not connected to server")
        
        if timestamp is None:
            timestamp = UTCDateTime()
        
        message = {
            'type': 'waveform_data',
            'station_id': station_id,
            'data': data.tolist(),
            'timestamp': str(timestamp)
        }
        
        await self.websocket.send(json.dumps(message))
    
    async def request_trace(self, station_id: str) -> Optional[dict]:
        if not self.is_connected:
            raise RuntimeError("Not connected to server")
        
        message = {
            'type': 'request_trace',
            'station_id': station_id
        }
        
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def request_stream(self) -> dict:
        if not self.is_connected:
            raise RuntimeError("Not connected to server")
        
        message = {'type': 'request_stream'}
        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()
        return json.loads(response)


class SimulatedSeismicSource:
    def __init__(self, sampling_rate: float = 100.0, 
                 num_stations: int = 3,
                 p_arrival: float = 5.0,
                 s_arrival: float = 8.0):
        self.sampling_rate = sampling_rate
        self.num_stations = num_stations
        self.p_arrival = p_arrival
        self.s_arrival = s_arrival
        self.current_time = 0.0
        self.station_delays = np.random.uniform(-0.5, 0.5, num_stations)
    
    def generate_chunk(self, duration_seconds: float = 1.0) -> List[np.ndarray]:
        n_samples = int(duration_seconds * self.sampling_rate)
        t = np.linspace(self.current_time, 
                       self.current_time + duration_seconds, 
                       n_samples)
        
        chunks = []
        
        for i in range(self.num_stations):
            noise = np.random.normal(0, 0.1, n_samples)
            
            p_time = self.p_arrival + self.station_delays[i]
            p_wave = np.zeros_like(t)
            p_idx = t >= p_time
            if np.any(p_idx):
                p_t = t[p_idx] - p_time
                p_wave[p_idx] = np.sin(2 * np.pi * 5.0 * p_t) * np.exp(-p_t)
            
            s_time = self.s_arrival + self.station_delays[i]
            s_wave = np.zeros_like(t)
            s_idx = t >= s_time
            if np.any(s_idx):
                s_t = t[s_idx] - s_time
                s_wave[s_idx] = np.sin(2 * np.pi * 2.0 * s_t) * np.exp(-0.5 * s_t)
            
            chunk = noise + p_wave + s_wave
            chunks.append(chunk)
        
        self.current_time += duration_seconds
        
        return chunks
