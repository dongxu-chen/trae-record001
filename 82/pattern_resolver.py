import re
import unicodedata
from typing import Dict, List

WINDOWS_RESERVED = set(r'<>:"/\|?*') + set(chr(i) for i in range(32))
CONTROL_CHARS = re.compile(r'[\x00-\x1f\x7f]')
TRAILING_SPECIAL = re.compile(r'[ ._]+$')
LEADING_SPECIAL = re.compile(r'^[ ._]+')
MULTI_SPACE = re.compile(r'[_\s]+')

DEFAULT_FALLBACK = 'Unknown'


class PatternResolver:
    VALID_PLACEHOLDERS = {'artist', 'title', 'album', 'track', 'year', 'genre'}

    def __init__(self, pattern: str, fallback: str = DEFAULT_FALLBACK):
        self.pattern = pattern
        self.fallback = fallback
        self._validate_pattern()

    def _validate_pattern(self):
        placeholders = re.findall(r'\{(\w+)\}', self.pattern)
        for ph in placeholders:
            if ph not in self.VALID_PLACEHOLDERS:
                raise ValueError(
                    f"Invalid placeholder '{ph}'. Valid placeholders: {', '.join(self.VALID_PLACEHOLDERS)}"
                )

    def _sanitize(self, value: str) -> str:
        value = unicodedata.normalize('NFKC', value)
        value = CONTROL_CHARS.sub('', value)
        cleaned = []
        for ch in value:
            if ch in WINDOWS_RESERVED:
                continue
            cleaned.append(ch)
        value = ''.join(cleaned)
        value = LEADING_SPECIAL.sub('', value)
        value = TRAILING_SPECIAL.sub('', value)
        value = MULTI_SPACE.sub(' ', value)
        return value.strip()

    def resolve(self, tags: Dict[str, str]) -> str:
        resolved = self.pattern
        placeholders = re.findall(r'\{(\w+)\}', resolved)

        for ph in placeholders:
            value = tags.get(ph, self.fallback)
            sanitized_value = self._sanitize(str(value)) if value else self.fallback
            if not sanitized_value:
                sanitized_value = self.fallback
            resolved = resolved.replace(f'{{{ph}}}', sanitized_value)

        result = self._sanitize(resolved)
        return result if result else self.fallback

    @classmethod
    def list_placeholders(cls) -> List[str]:
        return sorted(cls.VALID_PLACEHOLDERS)
