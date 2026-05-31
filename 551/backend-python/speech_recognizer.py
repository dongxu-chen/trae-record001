import asyncio
import json
import threading
import time
import queue
import numpy as np
import websockets
import speech_recognition as sr
from config import load_config
from punctuation_predictor import BERTPunctuationPredictor
from hotword_optimizer import HotwordOptimizer
from speaker_diarizer import SpeakerDiarizer
from translator import TranslationService

class StreamingSpeechToTextService:
    def __init__(self):
        self.config = load_config()
        self.language = self.config['language']
        self.hotwords = self.config['hotwords']
        self.ws_host = self.config['websocket']['host']
        self.ws_port = self.config['websocket']['port']
        
        self.recognizer = sr.Recognizer()
        self.audio_config = self.config['audio']
        self.recognizer.energy_threshold = self.audio_config['energy_threshold']
        self.recognizer.dynamic_energy_threshold = self.audio_config['dynamic_energy_threshold']
        self.recognizer.pause_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.2
        
        device = 'cuda' if self._check_cuda() else 'cpu'
        self.punctuation_predictor = BERTPunctuationPredictor(self.language, device=device)
        self.hotword_optimizer = HotwordOptimizer(self.hotwords, self.language)
        
        diarization_config = self.config.get('diarization', {})
        self.diarizer = SpeakerDiarizer(
            max_speakers=diarization_config.get('max_speakers', 6),
            min_speakers=diarization_config.get('min_speakers', 2),
            sample_rate=self.audio_config['sample_rate']
        )
        self.diarization_enabled = diarization_config.get('enabled', True)
        
        translation_config = self.config.get('translation', {})
        self.translator = TranslationService(
            source_lang=self.language,
            target_lang=translation_config.get('target_lang', 'en'),
            service=translation_config.get('service', 'google')
        )
        self.translation_enabled = translation_config.get('enabled', False)
        self.translator.set_enabled(self.translation_enabled)
        
        self.clients = set()
        self.is_running = False
        self.partial_text = ''
        self.last_partial_time = 0
        self.partial_send_interval = 0.3
        self.final_texts = []
        self.max_history = 100
        
        self.audio_queue = queue.Queue(maxsize=100)
        self.recognition_queue = queue.Queue(maxsize=50)
        self.raw_audio_buffer = []
        
        self.streaming_buffer = []
        self.streaming_threshold = 0.5
        self.last_send_time = 0
        self.min_send_interval = 0.5
        
    def _check_cuda(self):
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False
    
    async def register_client(self, websocket):
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")
        
        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def handle_client_message(self, websocket, message):
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'set_language':
                lang_code = data.get('language')
                if lang_code in self.config['supported_languages']:
                    self.language = lang_code
                    self.punctuation_predictor.set_language(lang_code)
                    self.hotword_optimizer.set_language(lang_code)
                    self.translator.set_source_lang(lang_code)
                    await self.broadcast({
                        'type': 'language_changed',
                        'language': lang_code
                    })
                    print(f"Language changed to: {lang_code}")
            
            elif action == 'add_hotword':
                word = data.get('word')
                if word and word not in self.hotwords:
                    self.hotwords.append(word)
                    self.hotword_optimizer.add_hotword(word)
                    await self.broadcast({
                        'type': 'hotword_added',
                        'word': word,
                        'hotwords': self.hotwords,
                        'hotword_stats': self.hotword_optimizer.get_hotword_list()
                    })
            
            elif action == 'remove_hotword':
                word = data.get('word')
                if word in self.hotwords:
                    self.hotwords.remove(word)
                    self.hotword_optimizer.remove_hotword(word)
                    await self.broadcast({
                        'type': 'hotword_removed',
                        'word': word,
                        'hotwords': self.hotwords,
                        'hotword_stats': self.hotword_optimizer.get_hotword_list()
                    })
            
            elif action == 'toggle_diarization':
                self.diarization_enabled = data.get('enabled', True)
                await self.broadcast({
                    'type': 'diarization_toggled',
                    'enabled': self.diarization_enabled
                })
            
            elif action == 'set_speaker_name':
                speaker_id = data.get('speaker_id')
                name = data.get('name')
                if speaker_id and name:
                    self.diarizer.set_speaker_name(speaker_id, name)
                    await self.broadcast({
                        'type': 'speaker_name_changed',
                        'speakers': self.diarizer.get_all_speakers()
                    })
            
            elif action == 'reset_speakers':
                self.diarizer.reset()
                await self.broadcast({
                    'type': 'speakers_reset',
                    'speakers': self.diarizer.get_all_speakers()
                })
            
            elif action == 'toggle_translation':
                self.translation_enabled = data.get('enabled', False)
                self.translator.set_enabled(self.translation_enabled)
                await self.broadcast({
                    'type': 'translation_toggled',
                    'enabled': self.translation_enabled
                })
            
            elif action == 'set_target_lang':
                target_lang = data.get('target_lang')
                if target_lang:
                    self.translator.set_target_lang(target_lang)
                    await self.broadcast({
                        'type': 'target_lang_changed',
                        'target_lang': target_lang
                    })
            
            elif action == 'get_config':
                await websocket.send(json.dumps({
                    'type': 'config',
                    'language': self.language,
                    'supported_languages': self.config['supported_languages'],
                    'hotwords': self.hotwords,
                    'hotword_stats': self.hotword_optimizer.get_hotword_list(),
                    'device': 'cuda' if self._check_cuda() else 'cpu',
                    'diarization_enabled': self.diarization_enabled,
                    'speakers': self.diarizer.get_all_speakers(),
                    'translation_enabled': self.translation_enabled,
                    'target_lang': self.translator.target_lang,
                    'translation_stats': self.translator.get_stats(),
                    'available_target_langs': self.translator.get_available_target_langs()
                }))
                
        except json.JSONDecodeError:
            pass
    
    async def broadcast(self, data):
        if self.clients:
            message = json.dumps(data, ensure_ascii=False)
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
    
    def audio_capture_thread(self):
        print(f"Starting streaming audio capture with language: {self.language}")
        print("Streaming mode enabled - latency target: <500ms")
        if self.diarization_enabled:
            print("Speaker diarization enabled")
        if self.translation_enabled:
            print(f"Translation enabled: {self.language} -> {self.translator.target_lang}")
        print("Please speak into the microphone...")
        
        try:
            with sr.Microphone(sample_rate=self.audio_config['sample_rate'], chunk_size=512) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                audio_buffer = []
                buffer_start_time = None
                is_speaking = False
                silence_counter = 0
                max_silence_frames = 10
                
                while self.is_running:
                    try:
                        chunk = source.stream.read(512, exception_on_overflow=False)
                        audio_buffer.append(chunk)
                        
                        if buffer_start_time is None:
                            buffer_start_time = time.time()
                        
                        audio_data = np.frombuffer(chunk, dtype=np.int16)
                        energy = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                        
                        energy_threshold = self.recognizer.energy_threshold * 0.5
                        
                        if energy > energy_threshold:
                            is_speaking = True
                            silence_counter = 0
                        else:
                            silence_counter += 1
                        
                        buffer_duration = time.time() - buffer_start_time
                        
                        if is_speaking and (buffer_duration >= 0.3 or silence_counter >= max_silence_frames):
                            if len(audio_buffer) > 5:
                                try:
                                    raw_data = b''.join(audio_buffer)
                                    audio = sr.AudioData(
                                        raw_data,
                                        source.SAMPLE_RATE,
                                        source.SAMPLE_WIDTH
                                    )
                                    
                                    np_audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
                                    
                                    self.audio_queue.put(
                                        (audio, time.time(), np_audio),
                                        timeout=0.1
                                    )
                                    
                                except queue.Full:
                                    pass
                                
                                audio_buffer = audio_buffer[-3:]
                                buffer_start_time = time.time()
                                
                                if silence_counter >= max_silence_frames:
                                    is_speaking = False
                                    silence_counter = 0
                        
                        if buffer_duration > 10:
                            audio_buffer = audio_buffer[-20:]
                            buffer_start_time = time.time()
                        
                    except Exception as e:
                        print(f"Audio capture error: {e}")
                        time.sleep(0.01)
                        continue
                        
        except Exception as e:
            print(f"Microphone error: {e}")
            print("Please check if your microphone is properly connected")
    
    def recognition_thread(self, loop):
        print("Recognition thread started")
        
        while self.is_running:
            try:
                audio, capture_time, np_audio = self.audio_queue.get(timeout=0.5)
                
                current_time = time.time()
                latency = current_time - capture_time
                
                try:
                    text = self.recognizer.recognize_google(
                        audio,
                        language=self.language,
                        show_all=False
                    )
                    
                    if text and text.strip():
                        processing_start = time.time()
                        
                        optimized_text = self.hotword_optimizer.optimize(text)
                        
                        is_final = latency > 0.5
                        text_with_punctuation = self.punctuation_predictor.predict(
                            optimized_text,
                            is_final=is_final
                        )
                        
                        speaker_id = None
                        speaker_name = None
                        speaker_color = None
                        speaker_confidence = 0.0
                        
                        if self.diarization_enabled:
                            speaker_id, speaker_confidence = self.diarizer.process_audio_segment(
                                np_audio,
                                timestamp=capture_time
                            )
                            if speaker_id:
                                speaker_info = self.diarizer.get_speaker_info(speaker_id)
                                speaker_name = speaker_info['name']
                                speaker_color = speaker_info['color']
                        
                        translation = ''
                        if self.translation_enabled and is_final:
                            translation = self.translator.translate(
                                text_with_punctuation,
                                source_lang=self.language
                            )
                        
                        processing_time = time.time() - processing_start
                        total_latency = time.time() - capture_time
                        
                        if is_final:
                            self.final_texts.append({
                                'text': text_with_punctuation,
                                'timestamp': time.time(),
                                'language': self.language,
                                'latency': total_latency,
                                'speaker_id': speaker_id,
                                'speaker_name': speaker_name,
                                'translation': translation
                            })
                            
                            if len(self.final_texts) > self.max_history:
                                self.final_texts.pop(0)
                        
                        broadcast_data = {
                            'type': 'transcription',
                            'text': text_with_punctuation,
                            'partial': not is_final,
                            'language': self.language,
                            'timestamp': time.time(),
                            'latency': total_latency,
                            'capture_latency': latency,
                            'processing_time': processing_time,
                            'speaker_id': speaker_id,
                            'speaker_name': speaker_name,
                            'speaker_color': speaker_color,
                            'speaker_confidence': speaker_confidence,
                            'translation': translation,
                            'translation_enabled': self.translation_enabled,
                            'target_lang': self.translator.target_lang if self.translation_enabled else None
                        }
                        
                        if is_final and self.diarization_enabled:
                            broadcast_data['speakers'] = self.diarizer.get_all_speakers()
                        
                        asyncio.run_coroutine_threadsafe(
                            self.broadcast(broadcast_data),
                            loop
                        )
                        
                        speaker_str = f"[{speaker_name}]" if speaker_name else ""
                        translation_str = f" -> {translation}" if translation else ""
                        if total_latency < 0.5:
                            status = "✓"
                        else:
                            status = "⚠"
                        print(f"[{status}] {speaker_str}{text_with_punctuation[:40]}{translation_str} (latency: {total_latency*1000:.0f}ms)")
                    
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    print(f"Google API error: {e}")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"Recognition error: {e}")
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Recognition thread error: {e}")
                time.sleep(0.1)
    
    def partial_flush_thread(self, loop):
        print("Partial flush thread started")
        
        while self.is_running:
            time.sleep(0.1)
            
            current_time = time.time()
            if current_time - self.last_partial_time >= self.partial_send_interval:
                if self.partial_text:
                    asyncio.run_coroutine_threadsafe(
                        self.broadcast({
                            'type': 'partial_update',
                            'text': self.partial_text,
                            'timestamp': current_time
                        }),
                        loop
                    )
                    self.last_partial_time = current_time
    
    async def start(self):
        self.is_running = True
        
        loop = asyncio.get_running_loop()
        
        audio_thread = threading.Thread(
            target=self.audio_capture_thread,
            daemon=True
        )
        audio_thread.start()
        
        recognition_thread = threading.Thread(
            target=self.recognition_thread,
            args=(loop,),
            daemon=True
        )
        recognition_thread.start()
        
        partial_thread = threading.Thread(
            target=self.partial_flush_thread,
            args=(loop,),
            daemon=True
        )
        partial_thread.start()
        
        async with websockets.serve(
            self.register_client,
            self.ws_host,
            self.ws_port
        ):
            print(f"WebSocket server started on ws://{self.ws_host}:{self.ws_port}")
            print(f"Streaming mode active - targeting <500ms latency")
            await asyncio.Future()
    
    def stop(self):
        self.is_running = False

async def main():
    service = StreamingSpeechToTextService()
    try:
        await service.start()
    except KeyboardInterrupt:
        print("\nStopping speech recognition service...")
        service.stop()

if __name__ == '__main__':
    asyncio.run(main())
