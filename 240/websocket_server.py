import asyncio
import websockets
import json
import numpy as np
import threading
import queue
from typing import Set, Dict, Any, Optional
from config import (
    WebSocketConfig, VADConfig, NoiseSuppressionConfig,
    WakeWordConfig, SpeakerDiarizationConfig
)
from vad import DoubleBufferVAD, AudioSegment
from asr import Wav2Vec2ASR
from noise_suppression import NoiseSuppressor
from keyword_spotter import WakeWordDetector
from speaker_diarization import RealTimeSpeakerDiarizer, SpeakerSegment


class ClientASRProcessor:
    def __init__(
        self,
        vad_config: VADConfig,
        asr_model: Wav2Vec2ASR,
        websocket: websockets.WebSocketServerProtocol,
        noise_config: Optional[NoiseSuppressionConfig] = None,
        wakeword_config: Optional[WakeWordConfig] = None,
        speaker_config: Optional[SpeakerDiarizationConfig] = None
    ):
        self.vad = DoubleBufferVAD(vad_config)
        self.asr_model = asr_model
        self.websocket = websocket
        self.frame_buffer = b''
        self.accumulated_text = ""
        self.last_partial_text = ""
        
        self.noise_suppressor: Optional[NoiseSuppressor] = None
        if noise_config and noise_config.enable:
            self.noise_suppressor = NoiseSuppressor(
                sample_rate=noise_config.sample_rate,
                enable=noise_config.enable
            )
        
        self.wakeword_detector: Optional[WakeWordDetector] = None
        if wakeword_config and wakeword_config.enable:
            self.wakeword_detector = WakeWordDetector(
                wake_words=wakeword_config.wake_words,
                sample_rate=wakeword_config.sample_rate,
                threshold=wakeword_config.threshold,
                auto_start=wakeword_config.auto_start
            )
            self.wakeword_detector.awake_duration = wakeword_config.awake_duration
        
        self.speaker_diarizer: Optional[RealTimeSpeakerDiarizer] = None
        if speaker_config and speaker_config.enable:
            self.speaker_diarizer = RealTimeSpeakerDiarizer(
                n_speakers=speaker_config.n_speakers,
                sample_rate=speaker_config.sample_rate,
                enable=speaker_config.enable
            )
            self.speaker_diarizer.diarizer.set_speaker_names(speaker_config.speaker_names)
        
        self.speaker_texts: dict = {}
        
        self.result_queue: queue.Queue = queue.Queue(maxsize=100)
        self.event_queue: queue.Queue = queue.Queue(maxsize=50)
        self.is_running = False
        self.recognition_thread: Optional[threading.Thread] = None
        self.event_thread: Optional[threading.Thread] = None
        
    def start(self):
        self.is_running = True
        self.vad.start(
            recognition_callback=self._on_complete_segment,
            partial_callback=self._on_partial_segment
        )
        
        if self.wakeword_detector:
            self.wakeword_detector.set_wake_callback(self._on_wakeword)
        
        if self.speaker_diarizer:
            self.speaker_diarizer.set_speaker_change_callback(self._on_speaker_change)
        
        self.recognition_thread = threading.Thread(target=self._result_sender_loop, daemon=True)
        self.recognition_thread.start()
        
        self.event_thread = threading.Thread(target=self._event_sender_loop, daemon=True)
        self.event_thread.start()
        
    def stop(self):
        self.is_running = False
        self.vad.stop()
        
        if self.noise_suppressor:
            self.noise_suppressor.reset()
        
        if self.recognition_thread:
            self.recognition_thread.join(timeout=1.0)
        
        if self.event_thread:
            self.event_thread.join(timeout=1.0)
            
    def process_audio(self, audio_data: bytes):
        frame_bytes = self.vad.frame_size * 2
        self.frame_buffer += audio_data
        
        while len(self.frame_buffer) >= frame_bytes:
            frame = self.frame_buffer[:frame_bytes]
            self.frame_buffer = self.frame_buffer[frame_bytes:]
            
            audio_float = DoubleBufferVAD.pcm16_to_float(frame)
            
            if self.noise_suppressor:
                audio_float = self.noise_suppressor.process(audio_float)
                frame = DoubleBufferVAD.float_to_pcm16(audio_float)
            
            if self.wakeword_detector:
                self.wakeword_detector.process(audio_float)
            
            if self.speaker_diarizer:
                self.speaker_diarizer.process(audio_float)
            
            if self.wakeword_detector and not self.wakeword_detector.is_awake:
                continue
            
            self.vad.put_audio_frame(frame)
    
    def _on_wakeword(self, keyword: str):
        event = {
            'type': 'wakeword',
            'keyword': keyword,
            'timestamp': asyncio.get_event_loop().time()
        }
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            pass
    
    def _on_speaker_change(self, speaker_id: int, segment: SpeakerSegment):
        speaker_name = self.speaker_diarizer.diarizer.get_speaker_name(speaker_id)
        event = {
            'type': 'speaker_change',
            'speaker_id': speaker_id,
            'speaker_name': speaker_name,
            'timestamp': asyncio.get_event_loop().time()
        }
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            pass
            
    def _on_complete_segment(self, segment: AudioSegment):
        try:
            audio_float = DoubleBufferVAD.pcm16_to_float(segment.audio_bytes)
            
            if len(audio_float) < 1600:
                return
            
            result = self.asr_model.transcribe(audio_float, self.accumulated_text)
            
            self.accumulated_text += result['text']
            self.last_partial_text = ""
            
            speaker_id = None
            speaker_name = None
            
            if self.speaker_diarizer:
                speaker_id = self.speaker_diarizer.get_current_speaker()
                speaker_name = self.speaker_diarizer.get_speaker_name(speaker_id)
                
                if speaker_id not in self.speaker_texts:
                    self.speaker_texts[speaker_id] = ""
                self.speaker_texts[speaker_id] += result['text']
                
                self.speaker_diarizer.add_transcription(result['text'], speaker_id)
            
            response = {
                'type': 'final',
                'text': result['text'],
                'full_text': self.accumulated_text,
                'confidence': result['confidence'],
                'duration': result['duration'],
                'timestamp': segment.timestamp,
                'matched_hotwords': result.get('matched_hotwords', [])
            }
            
            if speaker_id is not None:
                response['speaker_id'] = speaker_id
                response['speaker_name'] = speaker_name
                response['speaker_text'] = self.speaker_texts.get(speaker_id, "")
            
            self.result_queue.put(response)
            
        except Exception as e:
            print(f"[ASR] 处理完整语音段错误: {e}")
            
    def _on_partial_segment(self, segment: AudioSegment):
        try:
            audio_float = DoubleBufferVAD.pcm16_to_float(segment.audio_bytes)
            
            if len(audio_float) < 1600:
                return
            
            result = self.asr_model.transcribe(audio_float, self.accumulated_text)
            
            if result['text'] and result['text'] != self.last_partial_text:
                self.last_partial_text = result['text']
                
                speaker_id = None
                speaker_name = None
                
                if self.speaker_diarizer:
                    speaker_id = self.speaker_diarizer.get_current_speaker()
                    speaker_name = self.speaker_diarizer.get_speaker_name(speaker_id)
                
                response = {
                    'type': 'partial',
                    'text': result['text'],
                    'full_text': self.accumulated_text + result['text'],
                    'confidence': result['confidence'],
                    'duration': result['duration'],
                    'timestamp': segment.timestamp,
                    'matched_hotwords': result.get('matched_hotwords', [])
                }
                
                if speaker_id is not None:
                    response['speaker_id'] = speaker_id
                    response['speaker_name'] = speaker_name
                
                self.result_queue.put(response)
                
        except Exception as e:
            print(f"[ASR] 处理部分语音段错误: {e}")
            
    def _result_sender_loop(self):
        while self.is_running:
            try:
                response = self.result_queue.get(timeout=0.1)
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps(response, ensure_ascii=False)),
                    asyncio.get_event_loop_policy().get_event_loop()
                )
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ASR] 发送结果错误: {e}")
    
    def _event_sender_loop(self):
        while self.is_running:
            try:
                event = self.event_queue.get(timeout=0.1)
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps(event, ensure_ascii=False)),
                    asyncio.get_event_loop_policy().get_event_loop()
                )
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ASR] 发送事件错误: {e}")


class ASRWebSocketServer:
    def __init__(
        self,
        ws_config: WebSocketConfig,
        vad_config: VADConfig,
        asr_model: Wav2Vec2ASR,
        noise_config: Optional[NoiseSuppressionConfig] = None,
        wakeword_config: Optional[WakeWordConfig] = None,
        speaker_config: Optional[SpeakerDiarizationConfig] = None
    ):
        self.ws_config = ws_config
        self.vad_config = vad_config
        self.asr_model = asr_model
        self.noise_config = noise_config
        self.wakeword_config = wakeword_config
        self.speaker_config = speaker_config
        
        self.connections: Set[websockets.WebSocketServerProtocol] = set()
        self.client_processors: Dict[websockets.WebSocketServerProtocol, ClientASRProcessor] = {}
        
    async def register(self, websocket: websockets.WebSocketServerProtocol) -> bool:
        if len(self.connections) >= self.ws_config.max_connections:
            await websocket.close(1013, "Server is at maximum capacity")
            return False
        
        self.connections.add(websocket)
        processor = ClientASRProcessor(
            self.vad_config, self.asr_model, websocket,
            self.noise_config, self.wakeword_config, self.speaker_config
        )
        processor.start()
        self.client_processors[websocket] = processor
        
        print(f"[WS] 新客户端连接. 当前连接数: {len(self.connections)}")
        return True
    
    async def unregister(self, websocket: websockets.WebSocketServerProtocol):
        if websocket in self.connections:
            self.connections.remove(websocket)
            processor = self.client_processors.pop(websocket, None)
            if processor:
                processor.stop()
            print(f"[WS] 客户端断开. 当前连接数: {len(self.connections)}")
    
    async def handle_message(self, websocket: websockets.WebSocketServerProtocol, message: str):
        try:
            data = json.loads(message)
            message_type = data.get('type', '')
            
            if message_type == 'config':
                await self._handle_config(websocket, data)
            elif message_type == 'hotwords':
                await self._handle_hotwords(websocket, data)
            elif message_type == 'info':
                await self._handle_info(websocket)
            elif message_type == 'reset':
                await self._handle_reset(websocket)
            elif message_type == 'wake':
                await self._handle_force_wake(websocket)
            elif message_type == 'set_wake_words':
                await self._handle_set_wake_words(websocket, data)
                
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON format")
    
    async def handle_audio(self, websocket: websockets.WebSocketServerProtocol, audio_data: bytes):
        processor = self.client_processors.get(websocket)
        if processor:
            processor.process_audio(audio_data)
    
    async def _handle_config(self, websocket: websockets.WebSocketServerProtocol, data: Dict):
        try:
            hotwords = data.get('hotwords', [])
            if hotwords:
                self.asr_model.update_hotwords(hotwords)
            
            response = {
                'type': 'config_ack',
                'status': 'success',
                'hotwords': self.asr_model.get_hotwords()
            }
            await websocket.send(json.dumps(response, ensure_ascii=False))
            
        except Exception as e:
            await self._send_error(websocket, f"Config error: {str(e)}")
    
    async def _handle_hotwords(self, websocket: websockets.WebSocketServerProtocol, data: Dict):
        try:
            hotwords = data.get('hotwords', [])
            self.asr_model.update_hotwords(hotwords)
            
            response = {
                'type': 'hotwords_ack',
                'status': 'success',
                'hotwords': hotwords
            }
            await websocket.send(json.dumps(response, ensure_ascii=False))
            
        except Exception as e:
            await self._send_error(websocket, f"Hotwords error: {str(e)}")
    
    async def _handle_force_wake(self, websocket: websockets.WebSocketServerProtocol):
        try:
            processor = self.client_processors.get(websocket)
            if processor and processor.wakeword_detector:
                processor.wakeword_detector.force_wake()
            
            response = {
                'type': 'wake_ack',
                'status': 'success'
            }
            await websocket.send(json.dumps(response, ensure_ascii=False))
            
        except Exception as e:
            await self._send_error(websocket, f"Wake error: {str(e)}")
    
    async def _handle_set_wake_words(self, websocket: websockets.WebSocketServerProtocol, data: Dict):
        try:
            wake_words = data.get('wake_words', [])
            processor = self.client_processors.get(websocket)
            if processor and processor.wakeword_detector:
                processor.wakeword_detector.set_wake_words(wake_words)
            
            response = {
                'type': 'set_wake_words_ack',
                'status': 'success',
                'wake_words': wake_words
            }
            await websocket.send(json.dumps(response, ensure_ascii=False))
            
        except Exception as e:
            await self._send_error(websocket, f"Set wake words error: {str(e)}")
    
    async def _handle_reset(self, websocket: websockets.WebSocketServerProtocol):
        try:
            processor = self.client_processors.get(websocket)
            if processor:
                processor.accumulated_text = ""
                processor.last_partial_text = ""
                processor.speaker_texts = {}
                processor.vad.reset()
                
                if processor.noise_suppressor:
                    processor.noise_suppressor.reset()
                
                if processor.speaker_diarizer:
                    processor.speaker_diarizer.reset()
            
            response = {
                'type': 'reset_ack',
                'status': 'success'
            }
            await websocket.send(json.dumps(response, ensure_ascii=False))
            
        except Exception as e:
            await self._send_error(websocket, f"Reset error: {str(e)}")
    
    async def _handle_info(self, websocket: websockets.WebSocketServerProtocol):
        info = {
            'type': 'info',
            'model': self.asr_model.asr_config.model_name,
            'sample_rate': self.asr_model.asr_config.sample_rate,
            'hotwords': self.asr_model.get_hotwords(),
            'connections': len(self.connections),
            'noise_suppression': self.noise_config.enable if self.noise_config else False,
            'wake_word_detection': self.wakeword_config.enable if self.wakeword_config else False,
            'speaker_diarization': self.speaker_config.enable if self.speaker_config else False
        }
        await websocket.send(json.dumps(info, ensure_ascii=False))
    
    async def _send_error(self, websocket: websockets.WebSocketServerProtocol, message: str):
        error = {
            'type': 'error',
            'message': message
        }
        await websocket.send(json.dumps(error, ensure_ascii=False))
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol):
        try:
            registered = await self.register(websocket)
            if not registered:
                return
            
            async for message in websocket:
                if isinstance(message, bytes):
                    await self.handle_audio(websocket, message)
                elif isinstance(message, str):
                    await self.handle_message(websocket, message)
                    
        except websockets.exceptions.ConnectionClosed:
            print("[WS] 客户端连接关闭")
        except Exception as e:
            print(f"[WS] 处理客户端错误: {e}")
        finally:
            await self.unregister(websocket)
    
    async def start(self):
        print(f"[WS] 启动WebSocket服务: {self.ws_config.host}:{self.ws_config.port}")
        
        async with websockets.serve(
            self.handle_client,
            self.ws_config.host,
            self.ws_config.port,
            ping_timeout=self.ws_config.timeout
        ):
            print("[WS] 服务已启动，等待连接...")
            await asyncio.Future()
