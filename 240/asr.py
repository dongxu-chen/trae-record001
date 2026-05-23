import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from config import ASRConfig, HotwordConfig
from hotword_trie import HotwordEnhancer
import re


class Wav2Vec2ASR:
    def __init__(self, asr_config: ASRConfig, hotword_config: HotwordConfig):
        self.asr_config = asr_config
        self.hotword_config = hotword_config
        self.device = torch.device(asr_config.device)
        
        print(f"Loading model: {asr_config.model_name}")
        self.processor = Wav2Vec2Processor.from_pretrained(asr_config.model_name)
        self.model = Wav2Vec2ForCTC.from_pretrained(asr_config.model_name)
        self.model.to(self.device)
        self.model.eval()
        
        self.vocab = self.processor.tokenizer.get_vocab()
        self.id_to_token = {v: k for k, v in self.vocab.items()}
        
        self.hotword_enhancer = HotwordEnhancer(hotword_config.boost_factor)
        self.hotword_enhancer.set_tokenizer(self.processor.tokenizer)
        
        if hotword_config.use_hotwords and hotword_config.hotwords:
            self.hotword_enhancer.set_hotwords(hotword_config.hotwords)
            print(f"Prepared {len(hotword_config.hotwords)} hotwords loaded into weighted trie")
        
        print("Model loaded successfully")
    
    def _apply_hotword_boost(self, logits: torch.Tensor, partial_text: str = "") -> torch.Tensor:
        if not self.hotword_config.use_hotwords:
            return logits
        
        return self.hotword_enhancer.enhance_logits(logits, partial_text)
    
    def _compute_confidence(self, logits: torch.Tensor, predicted_ids: torch.Tensor) -> float:
        probabilities = torch.softmax(logits, dim=-1)
        
        seq_length = predicted_ids.shape[1]
        confidences = []
        
        for batch_idx in range(predicted_ids.shape[0]):
            batch_confidences = []
            for time_idx in range(seq_length):
                token_id = predicted_ids[batch_idx, time_idx].item()
                if token_id != -100:
                    prob = probabilities[batch_idx, time_idx, token_id].item()
                    batch_confidences.append(prob)
            
            if batch_confidences:
                confidences.append(np.mean(batch_confidences))
        
        return np.mean(confidences) if confidences else 0.0
    
    def transcribe(self, audio: np.ndarray, partial_hint: str = "") -> Dict:
        audio = audio.squeeze()
        
        inputs = self.processor(
            audio,
            sampling_rate=self.asr_config.sample_rate,
            return_tensors="pt",
            padding=True
        )
        
        input_values = inputs.input_values.to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_values)
            logits = outputs.logits
            
            predicted_ids_initial = torch.argmax(logits, dim=-1)
            partial_text = self.processor.batch_decode(predicted_ids_initial)[0]
            partial_text = self._post_process(partial_text)
            
            combined_hint = partial_hint + partial_text
            logits = self._apply_hotword_boost(logits, combined_hint)
            
            predicted_ids = torch.argmax(logits, dim=-1)
            confidence = self._compute_confidence(logits, predicted_ids)
            
            transcription = self.processor.batch_decode(predicted_ids)[0]
            transcription = self._post_process(transcription)
            
            matched_hotwords = self.hotword_enhancer.find_matched_hotwords(transcription)
        
        return {
            'text': transcription,
            'confidence': confidence,
            'duration': len(audio) / self.asr_config.sample_rate,
            'matched_hotwords': matched_hotwords
        }
    
    def _post_process(self, text: str) -> str:
        text = re.sub(r'\s+', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()
    
    def update_hotwords(self, hotwords: List[str]):
        self.hotword_config.hotwords = hotwords
        self.hotword_enhancer.set_hotwords(hotwords)
        print(f"Updated {len(hotwords)} hotwords loaded into weighted trie")
    
    def get_hotwords(self) -> List[str]:
        return self.hotword_enhancer.get_hotwords()
    
    def transcribe_stream(self, audio_chunks: List[np.ndarray]) -> List[Dict]:
        results = []
        accumulated_text = ""
        
        for chunk in audio_chunks:
            result = self.transcribe(chunk, accumulated_text)
            results.append(result)
            accumulated_text += result['text']
        
        return results
