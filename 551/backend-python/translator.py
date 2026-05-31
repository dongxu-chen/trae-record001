import json
import re
import threading
import time
from collections import OrderedDict

try:
    from googletrans import Translator as GoogleTranslator
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class LRUCache:
    def __init__(self, capacity=500):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = threading.Lock()
    
    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return None
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def put(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)


class TranslationService:
    def __init__(self, source_lang='zh-CN', target_lang='en', service='google'):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.service = service
        self.enabled = False
        self.cache = LRUCache(capacity=500)
        self.translator = None
        self.lock = threading.Lock()
        self.translation_count = 0
        self.cache_hit_count = 0
        
        self.lang_code_map = {
            'zh-CN': 'zh-cn',
            'zh-TW': 'zh-tw',
            'en-US': 'en',
            'en-GB': 'en',
            'ja-JP': 'ja',
            'ko-KR': 'ko',
            'fr-FR': 'fr',
            'de-DE': 'de',
            'es-ES': 'es',
            'ru-RU': 'ru'
        }
        
        self.target_lang_names = {
            'zh-CN': '中文',
            'zh-TW': '繁体中文',
            'en': '英语',
            'ja': '日语',
            'ko': '韩语',
            'fr': '法语',
            'de': '德语',
            'es': '西班牙语',
            'ru': '俄语'
        }
        
        self._init_translator()
    
    def _init_translator(self):
        if GOOGLETRANS_AVAILABLE:
            try:
                self.translator = GoogleTranslator()
                print(f"Translation service initialized (googletrans)")
            except Exception as e:
                print(f"Failed to initialize Google translator: {e}")
                self.translator = None
    
    def translate(self, text, source_lang=None, target_lang=None):
        if not self.enabled or not text or not text.strip():
            return ''
        
        src = source_lang or self.source_lang
        tgt = target_lang or self.target_lang
        
        src_mapped = self.lang_code_map.get(src, src.split('-')[0])
        
        if src_mapped == tgt or src.split('-')[0] == tgt:
            return text
        
        cache_key = f"{src_mapped}:{tgt}:{text}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            self.cache_hit_count += 1
            return cached
        
        cleaned_text = self._clean_text_for_translation(text)
        if not cleaned_text:
            return ''
        
        if self.translator and GOOGLETRANS_AVAILABLE:
            result = self._translate_google(cleaned_text, src_mapped, tgt)
        else:
            result = self._translate_fallback(cleaned_text, src_mapped, tgt)
        
        if result:
            self.cache.put(cache_key, result)
            self.translation_count += 1
        
        return result or ''
    
    def _translate_google(self, text, src_lang, tgt_lang):
        for attempt in range(3):
            try:
                with self.lock:
                    result = self.translator.translate(
                        text,
                        src=src_lang,
                        dest=tgt_lang
                    )
                    return result.text
            except Exception as e:
                if attempt == 2:
                    print(f"Translation failed after 3 attempts: {e}")
                    return ''
                time.sleep(0.5 * (attempt + 1))
        return ''
    
    def _translate_fallback(self, text, src_lang, tgt_lang):
        if REQUESTS_AVAILABLE:
            try:
                url = "https://translate.googleapis.com/translate_a/single"
                params = {
                    'client': 'gtx',
                    'sl': src_lang,
                    'tl': tgt_lang,
                    'dt': 't',
                    'q': text
                }
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    result = response.json()
                    translated = ''.join([item[0] for item in result[0] if item[0]])
                    return translated
            except Exception as e:
                print(f"Fallback translation failed: {e}")
        
        return ''
    
    def _clean_text_for_translation(self, text):
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def translate_batch(self, texts, source_lang=None, target_lang=None):
        results = []
        for text in texts:
            result = self.translate(text, source_lang, target_lang)
            results.append(result)
        return results
    
    def set_source_lang(self, lang):
        self.source_lang = lang
    
    def set_target_lang(self, lang):
        self.target_lang = lang
    
    def set_enabled(self, enabled):
        self.enabled = enabled
        if enabled and self.translator is None:
            self._init_translator()
    
    def get_available_target_langs(self):
        return list(self.target_lang_names.keys())
    
    def get_stats(self):
        return {
            'enabled': self.enabled,
            'source_lang': self.source_lang,
            'target_lang': self.target_lang,
            'translation_count': self.translation_count,
            'cache_hit_count': self.cache_hit_count,
            'cache_size': self.cache.cache.__len__(),
            'service': self.service,
            'translator_available': self.translator is not None
        }
    
    def reset_stats(self):
        self.translation_count = 0
        self.cache_hit_count = 0
