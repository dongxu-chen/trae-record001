from langdetect import detect, LangDetectException
from typing import Tuple


LANGUAGE_MAP = {
    'en': 'English',
    'zh': 'Chinese',
    'zh-cn': 'Chinese',
    'zh-tw': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'fr': 'French',
    'de': 'German',
    'es': 'Spanish',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'id': 'Indonesian'
}


class LanguageDetector:
    @staticmethod
    def detect_language(text: str) -> Tuple[str, str]:
        try:
            lang_code = detect(text)
            lang_name = LANGUAGE_MAP.get(lang_code, lang_code)
            return lang_code, lang_name
        except LangDetectException:
            return 'en', 'English'
    
    @staticmethod
    def is_supported_language(lang_code: str) -> bool:
        return lang_code in LANGUAGE_MAP
    
    @staticmethod
    def get_language_name(lang_code: str) -> str:
        return LANGUAGE_MAP.get(lang_code, lang_code)
