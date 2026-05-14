from pathlib import Path
from typing import Optional

SUPPORTED_FORMATS = {
    '.azw': 'azw',
    '.azw3': 'azw3',
    '.azw4': 'azw4',
    '.cb7': 'cb7',
    '.cbc': 'cbc',
    '.cbz': 'cbz',
    '.chm': 'chm',
    '.djvu': 'djvu',
    '.docx': 'docx',
    '.epub': 'epub',
    '.fb2': 'fb2',
    '.fbz': 'fbz',
    '.html': 'html',
    '.htmlz': 'htmlz',
    '.lit': 'lit',
    '.lrf': 'lrf',
    '.mobi': 'mobi',
    '.odt': 'odt',
    '.pdf': 'pdf',
    '.pdb': 'pdb',
    '.pml': 'pml',
    '.prc': 'prc',
    '.rb': 'rb',
    '.rtf': 'rtf',
    '.snb': 'snb',
    '.tcr': 'tcr',
    '.txt': 'txt',
    '.txtz': 'txtz'
}


class FormatDetector:
    @staticmethod
    def detect(file_path: str) -> Optional[str]:
        path = Path(file_path)
        if not path.exists():
            return None
        ext = path.suffix.lower()
        return SUPPORTED_FORMATS.get(ext)

    @staticmethod
    def is_supported(file_path: str) -> bool:
        return FormatDetector.detect(file_path) is not None

    @staticmethod
    def get_supported_input_formats() -> list[str]:
        return sorted(set(SUPPORTED_FORMATS.values()))

    @staticmethod
    def get_supported_output_formats() -> list[str]:
        return sorted(set(SUPPORTED_FORMATS.values()))
