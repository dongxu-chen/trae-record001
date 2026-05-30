import os
import zipfile
import tarfile
import io
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

from git_scanner import LargeFileInfo


EXTENSION_CATEGORIES = {
    'image': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.svg', '.webp', '.ico', '.heic'},
    'video': {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'},
    'audio': {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'},
    'archive': {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz', '.tbz2'},
    'document': {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods'},
    'database': {'.db', '.sqlite', '.sql', '.mdb', '.accdb', '.dbf'},
    'executable': {'.exe', '.dll', '.so', '.dylib', '.app', '.apk', '.ipa'},
    'font': {'.ttf', '.otf', '.woff', '.woff2', '.eot'},
    'log': {'.log'},
    'backup': {'.bak', '.backup', '.old'},
    'data': {'.csv', '.json', '.xml', '.yaml', '.yml', '.parquet', '.feather'},
    'model': {'.pkl', '.pt', '.pth', '.h5', '.hdf5', '.pb', '.onnx', '.safetensors', '.bin'},
    'image_raw': {'.raw', '.cr2', '.nef', '.arw', '.dng'},
}

MIME_CATEGORY_MAP = {
    'image': 'image',
    'video': 'video',
    'audio': 'audio',
    'application/zip': 'archive',
    'application/x-tar': 'archive',
    'application/gzip': 'archive',
    'application/x-bzip2': 'archive',
    'application/x-xz': 'archive',
    'application/x-7z-compressed': 'archive',
    'application/x-rar-compressed': 'archive',
    'application/pdf': 'document',
    'application/msword': 'document',
    'application/vnd': 'document',
    'application/x-sqlite3': 'database',
    'application/x-executable': 'executable',
    'application/octet-stream': 'model',
    'font': 'font',
    'text': 'data',
}


class ArchiveContentInfo:
    __slots__ = ('name', 'size', 'compressed_size', 'is_dir')

    def __init__(self, name: str, size: int, compressed_size: int, is_dir: bool):
        self.name = name
        self.size = size
        self.compressed_size = compressed_size
        self.is_dir = is_dir


class FileTypeAnalyzer:
    @staticmethod
    def get_file_extension(file_path: str) -> str:
        return os.path.splitext(file_path)[1].lower()

    @staticmethod
    def categorize_by_extension(file_path: str) -> str:
        ext = FileTypeAnalyzer.get_file_extension(file_path)
        for category, extensions in EXTENSION_CATEGORIES.items():
            if ext in extensions:
                return category
        return 'other'

    @staticmethod
    def detect_mime_type(file_path: str, blob_data: bytes = None) -> str:
        if not MAGIC_AVAILABLE:
            return 'unknown'
        try:
            if blob_data is not None:
                mime = magic.from_buffer(blob_data, mime=True)
            else:
                mime = magic.from_file(file_path, mime=True)
            return mime
        except (FileNotFoundError, IOError, TypeError):
            return 'unknown'

    @staticmethod
    def categorize_by_mime(mime_type: str) -> str:
        if not mime_type or mime_type == 'unknown':
            return 'unknown'
        for mime_prefix, category in MIME_CATEGORY_MAP.items():
            if mime_type.startswith(mime_prefix):
                return category
        return 'other'

    @staticmethod
    def analyze_file_type(file_path: str, blob_data: bytes = None) -> str:
        ext_category = FileTypeAnalyzer.categorize_by_extension(file_path)

        if MAGIC_AVAILABLE and blob_data is not None:
            mime_type = FileTypeAnalyzer.detect_mime_type(file_path, blob_data)
            mime_category = FileTypeAnalyzer.categorize_by_mime(mime_type)

            if ext_category != 'other' and mime_category != 'other':
                if ext_category == mime_category:
                    return ext_category
                return f"{ext_category}/{mime_category}"
            elif ext_category != 'other':
                return ext_category
            elif mime_category != 'other':
                return mime_category
            return 'other'

        return ext_category

    @staticmethod
    def scan_archive_contents(blob_data: bytes, file_path: str) -> List[ArchiveContentInfo]:
        ext = FileTypeAnalyzer.get_file_extension(file_path)
        contents: List[ArchiveContentInfo] = []

        if ext in {'.zip', '.jar', '.war', '.egg', '.whl'}:
            contents = ArchiveScanner.scan_zip(blob_data)
        elif ext in {'.tar'}:
            contents = ArchiveScanner.scan_tar(blob_data)
        elif ext in {'.gz', '.tgz'}:
            contents = ArchiveScanner.scan_tar(blob_data, mode='r:gz')
        elif ext in {'.bz2', '.tbz2'}:
            contents = ArchiveScanner.scan_tar(blob_data, mode='r:bz2')
        elif ext in {'.xz'}:
            contents = ArchiveScanner.scan_tar(blob_data, mode='r:xz')

        return contents


class ArchiveScanner:
    @staticmethod
    def scan_zip(data: bytes) -> List[ArchiveContentInfo]:
        contents = []
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                for info in zf.infolist():
                    contents.append(ArchiveContentInfo(
                        name=info.filename,
                        size=info.file_size,
                        compressed_size=info.compress_size,
                        is_dir=info.is_dir()
                    ))
        except (zipfile.BadZipFile, IOError):
            pass
        return contents

    @staticmethod
    def scan_tar(data: bytes, mode: str = 'r:') -> List[ArchiveContentInfo]:
        contents = []
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode=mode) as tf:
                for member in tf.getmembers():
                    contents.append(ArchiveContentInfo(
                        name=member.name,
                        size=member.size,
                        compressed_size=member.size,
                        is_dir=member.isdir()
                    ))
        except (tarfile.TarError, IOError, EOFError):
            pass
        return contents

    @staticmethod
    def summarize_archive(contents: List[ArchiveContentInfo]) -> dict:
        if not contents:
            return {'file_count': 0, 'total_size': 0, 'total_compressed': 0, 'top_files': []}

        files = [c for c in contents if not c.is_dir]
        total_size = sum(f.size for f in files)
        total_compressed = sum(f.compressed_size for f in files)

        sorted_files = sorted(files, key=lambda x: x.size, reverse=True)
        top_files = [(f.name, f.size, f.compressed_size) for f in sorted_files[:10]]

        file_types = defaultdict(int)
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            file_types[ext if ext else '(no ext)'] += 1

        return {
            'file_count': len(files),
            'total_size': total_size,
            'total_compressed': total_compressed,
            'top_files': top_files,
            'file_type_distribution': dict(file_types)
        }


class LargeFileAnalyzer:
    def __init__(self, large_files: Dict[str, LargeFileInfo], scanner=None):
        self.large_files = large_files
        self.scanner = scanner
        self.archive_reports: Dict[str, dict] = {}
        self.file_types = self._classify_file_types()

    def _classify_file_types(self) -> Dict[str, List[LargeFileInfo]]:
        type_groups = defaultdict(list)
        for file_path, info in self.large_files.items():
            blob_data = self._try_get_blob_data(info)
            file_type = FileTypeAnalyzer.analyze_file_type(file_path, blob_data)
            info.file_type = file_type
            type_groups[file_type].append(info)

            if FileTypeAnalyzer.categorize_by_extension(file_path) == 'archive' and blob_data:
                contents = FileTypeAnalyzer.scan_archive_contents(blob_data, file_path)
                if contents:
                    self.archive_reports[file_path] = ArchiveScanner.summarize_archive(contents)

        return dict(type_groups)

    def _try_get_blob_data(self, info: LargeFileInfo) -> Optional[bytes]:
        if self.scanner is None:
            return None
        try:
            for blob_id in info.blob_ids:
                blob = self.scanner.repo.rev_parse(blob_id)
                return blob.data_stream.read()
        except Exception:
            return None

    def get_archive_reports(self) -> Dict[str, dict]:
        return self.archive_reports

    def get_summary_by_type(self) -> Dict[str, dict]:
        summary = {}
        for file_type, files in self.file_types.items():
            total_size = sum(f.max_size for f in files)
            total_commits = sum(f.commit_count for f in files)
            summary[file_type] = {
                'count': len(files),
                'total_size': total_size,
                'total_commits': total_commits,
                'avg_size': total_size // len(files) if files else 0
            }
        return summary

    def get_top_largest_files(self, limit: int = 10) -> List[LargeFileInfo]:
        sorted_files = sorted(
            self.large_files.values(),
            key=lambda x: x.max_size,
            reverse=True
        )
        return sorted_files[:limit]

    def get_most_frequently_modified(self, limit: int = 10) -> List[LargeFileInfo]:
        sorted_files = sorted(
            self.large_files.values(),
            key=lambda x: x.commit_count,
            reverse=True
        )
        return sorted_files[:limit]

    def get_oldest_files(self, limit: int = 10) -> List[LargeFileInfo]:
        sorted_files = sorted(
            self.large_files.values(),
            key=lambda x: x.first_introduced
        )
        return sorted_files[:limit]
