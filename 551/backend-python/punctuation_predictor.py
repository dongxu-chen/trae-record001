import re
import threading
import numpy as np

try:
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForTokenClassification,
        pipeline
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class BERTPunctuationPredictor:
    def __init__(self, language='zh-CN', device='cpu'):
        self.language = language
        self.device = device
        self.model = None
        self.tokenizer = None
        self.nlp_pipeline = None
        self.model_lock = threading.Lock()
        self.model_loaded = False
        self.loading_thread = None
        
        self.punctuation_map = {
            'zh': {
                'O': '',
                'PERIOD': '。',
                'COMMA': '，',
                'QUESTION': '？',
                'EXCLAMATION': '！',
                'PAUSE': '、',
                'COLON': '：',
                'SEMICOLON': '；'
            },
            'en': {
                'O': '',
                'PERIOD': '.',
                'COMMA': ',',
                'QUESTION': '?',
                'EXCLAMATION': '!',
                'COLON': ':',
                'SEMICOLON': ';',
                'HYPHEN': '-'
            }
        }
        
        self.fallback_predictor = FallbackPunctuationPredictor(language)
        
        self._start_loading_model()
    
    def _start_loading_model(self):
        self.loading_thread = threading.Thread(
            target=self._load_model,
            daemon=True
        )
        self.loading_thread.start()
    
    def _load_model(self):
        if not TRANSFORMERS_AVAILABLE:
            print("Warning: transformers/torch not available, using fallback punctuation predictor")
            return
        
        try:
            print("Loading BERT punctuation model...")
            
            lang_prefix = self.language.split('-')[0]
            
            if lang_prefix == 'zh':
                model_name = "ckiplab/albert-tiny-chinese-ws"
            else:
                model_name = "oliverguhr/fullstop-punctuation-multilang-large"
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(model_name)
            
            self.model.to(self.device)
            self.model.eval()
            
            self.nlp_pipeline = pipeline(
                "token-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == 'cuda' else -1,
                aggregation_strategy="simple"
            )
            
            self.model_loaded = True
            print(f"BERT punctuation model loaded successfully on {self.device}")
            
        except Exception as e:
            print(f"Failed to load BERT model: {e}")
            print("Using fallback punctuation predictor instead")
            self.model_loaded = False
    
    def _wait_for_model(self, timeout=30):
        if self.loading_thread and self.loading_thread.is_alive():
            print("Waiting for BERT model to finish loading...")
            self.loading_thread.join(timeout=timeout)
    
    def predict(self, text, is_final=True):
        if not text:
            return text
        
        self._wait_for_model()
        
        if self.model_loaded and TRANSFORMERS_AVAILABLE:
            try:
                return self._predict_with_bert(text, is_final)
            except Exception as e:
                print(f"BERT prediction failed, using fallback: {e}")
        
        return self.fallback_predictor.predict(text, is_final)
    
    def _predict_with_bert(self, text, is_final=True):
        lang_prefix = self.language.split('-')[0]
        punc_map = self.punctuation_map.get(lang_prefix, self.punctuation_map['en'])
        
        if lang_prefix == 'zh':
            return self._predict_chinese_bert(text, is_final, punc_map)
        else:
            return self._predict_english_bert(text, is_final, punc_map)
    
    def _predict_chinese_bert(self, text, is_final, punc_map):
        text = re.sub(r'\s+', '', text)
        
        if len(text) > 510:
            chunks = self._split_chinese_text(text, 500)
            result = []
            for chunk in chunks:
                result.append(self._process_chinese_chunk(chunk, punc_map))
            processed = ''.join(result)
        else:
            processed = self._process_chinese_chunk(text, punc_map)
        
        if is_final and processed and processed[-1] not in ['。', '！', '？', '；']:
            has_question = any(q in processed for q in ['什么', '怎么', '为什么', '如何', '哪', '谁', '何时', '何地', '多少', '吗', '呢'])
            if has_question:
                processed += '？'
            else:
                processed += '。'
        
        return processed
    
    def _process_chinese_chunk(self, text, punc_map):
        with self.model_lock:
            with torch.no_grad():
                inputs = self.tokenizer(
                    list(text),
                    return_tensors="pt",
                    is_split_into_words=True,
                    truncation=True,
                    max_length=512
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                outputs = self.model(**inputs)
                predictions = torch.argmax(outputs.logits, dim=2)[0].cpu().numpy()
                
                tokens = self.tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
                
                result = []
                for i, (token, pred) in enumerate(zip(tokens, predictions)):
                    if token in ['[CLS]', '[SEP]', '[PAD]']:
                        continue
                    
                    if token.startswith('##'):
                        token = token[2:]
                    
                    label = self.model.config.id2label.get(pred, 'O')
                    
                    for key in punc_map:
                        if key in label.upper():
                            punc = punc_map[key]
                            if punc:
                                result.append(token)
                                result.append(punc)
                            else:
                                result.append(token)
                            break
                    else:
                        result.append(token)
                
                processed = ''.join(result)
                processed = re.sub(r'([，。！？、；：])\1+', r'\1', processed)
                processed = re.sub(r'[，、]。', '。', processed)
                
                return processed
    
    def _split_chinese_text(self, text, max_len):
        chunks = []
        for i in range(0, len(text), max_len):
            chunks.append(text[i:i + max_len])
        return chunks
    
    def _predict_english_bert(self, text, is_final, punc_map):
        words = text.split()
        
        with self.model_lock:
            with torch.no_grad():
                inputs = self.tokenizer(
                    words,
                    return_tensors="pt",
                    is_split_into_words=True,
                    truncation=True,
                    max_length=512
                )
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                outputs = self.model(**inputs)
                predictions = torch.argmax(outputs.logits, dim=2)[0].cpu().numpy()
                
                word_ids = inputs['input_ids'][0].cpu().numpy()
                tokens = self.tokenizer.convert_ids_to_tokens(word_ids)
                
                result = []
                current_word = []
                
                for i, (token, pred) in enumerate(zip(tokens, predictions)):
                    if token in ['[CLS]', '[SEP]', '[PAD]']:
                        continue
                    
                    if token.startswith('##'):
                        current_word.append(token[2:])
                    else:
                        if current_word:
                            result.append(''.join(current_word))
                            current_word = [token]
                        else:
                            current_word = [token]
                    
                    label = self.model.config.id2label.get(pred, 'O')
                    punc = None
                    for key in punc_map:
                        if key in label.upper():
                            punc = punc_map[key]
                            break
                    
                    if punc:
                        if current_word:
                            result.append(''.join(current_word))
                            result.append(punc)
                            current_word = []
                
                if current_word:
                    result.append(''.join(current_word))
                
                processed = ' '.join(result)
                processed = re.sub(r'\s+([.,!?;:])', r'\1', processed)
                processed = re.sub(r'([.,!?;:])\1+', r'\1', processed)
                
                if is_final and processed and processed[-1] not in ['.', '!', '?', ';']:
                    lower_text = processed.lower()
                    if lower_text.startswith(('what', 'how', 'why', 'where', 'when', 'who', 'which', 'is', 'are', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should')):
                        processed += '?'
                    else:
                        processed += '.'
                
                return processed
    
    def set_language(self, language):
        self.language = language
        self.fallback_predictor.set_language(language)
        
        if self.model_loaded:
            new_lang_prefix = language.split('-')[0]
            current_lang_prefix = self.language.split('-')[0]
            if new_lang_prefix != current_lang_prefix:
                print(f"Language changed to {language}, reloading model...")
                self.model_loaded = False
                self._start_loading_model()


class FallbackPunctuationPredictor:
    def __init__(self, language='zh-CN'):
        self.language = language
        self.zh_pause_patterns = [
            (r'([，。！？；：])\1+', r'\1'),
        ]
        self.en_pause_words = {
            'and': ', and',
            'but': ', but',
            'so': ', so',
            'because': ', because',
            'however': ', however',
            'therefore': ', therefore',
        }
        self.zh_sentence_end_words = ['了', '吗', '呢', '吧', '啊', '呀', '哦', '嗯']
        self.question_words = ['什么', '怎么', '为什么', '如何', '哪', '谁', '何时', '何地', '多少', '吗', '呢']
        
    def predict(self, text, is_final=True):
        if not text:
            return text
            
        if self.language.startswith('zh'):
            return self._predict_chinese(text, is_final)
        elif self.language.startswith('en'):
            return self._predict_english(text, is_final)
        else:
            return text if not is_final else text + '.'
    
    def _predict_chinese(self, text, is_final):
        text = text.strip()
        
        for pattern, replacement in self.zh_pause_patterns:
            text = re.sub(pattern, replacement, text)
        
        text = re.sub(r'([。！？；：])\1+', r'\1', text)
        
        if is_final and text:
            last_char = text[-1]
            if last_char not in ['。', '！', '？', '；', '：', '，']:
                has_question = any(q in text for q in self.question_words)
                if has_question and last_char in self.zh_sentence_end_words:
                    text += '？'
                else:
                    text += '。'
        
        return text
    
    def _predict_english(self, text, is_final):
        text = text.strip()
        
        words = text.split()
        result_words = []
        for i, word in enumerate(words):
            lower_word = word.lower()
            if i > 0 and lower_word in self.en_pause_words:
                result_words.append(self.en_pause_words[lower_word])
            else:
                result_words.append(word)
        
        text = ' '.join(result_words)
        
        if is_final and text:
            last_char = text[-1]
            if last_char not in ['.', '!', '?', ';', ':']:
                lower_text = text.lower()
                if lower_text.startswith(('what', 'how', 'why', 'where', 'when', 'who', 'which', 'is', 'are', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should')):
                    text += '?'
                else:
                    text += '.'
        
        return text
    
    def set_language(self, language):
        self.language = language
