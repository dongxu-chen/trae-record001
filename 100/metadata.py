import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

_ENCODINGS_TO_TRY = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'utf-16-le', 'cp936']


@dataclass
class BookMetadata:
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    publisher: Optional[str] = None
    pubdate: Optional[str] = None
    language: Optional[str] = None
    isbn: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    series: Optional[str] = None
    series_index: Optional[str] = None
    rating: Optional[float] = None
    comments: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class MetadataManager:
    def __init__(self, calibre_path: Optional[str] = None):
        self.calibre_path = calibre_path

    def _get_ebook_meta_path(self) -> str:
        if self.calibre_path:
            return str(Path(self.calibre_path) / 'ebook-meta')
        return 'ebook-meta'

    def read(self, file_path: str) -> BookMetadata:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f'File not found: {file_path}')

        cmd = [self._get_ebook_meta_path(), str(path)]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=False,
                check=True
            )
            stdout_str = self._decode_bytes(result.stdout)
            return self._parse_metadata(stdout_str)
        except subprocess.CalledProcessError as e:
            stderr_str = self._decode_bytes(e.stderr) if e.stderr else str(e)
            raise RuntimeError(f'Failed to read metadata: {stderr_str}') from e

    def _decode_bytes(self, data: bytes) -> str:
        for encoding in _ENCODINGS_TO_TRY:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode('utf-8', errors='replace')

    def _parse_metadata(self, output: str) -> BookMetadata:
        meta = BookMetadata()
        lines = output.split('\n')

        for line in lines:
            line = line.strip()
            if not line or ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()

            if not value:
                continue

            if key == 'title':
                meta.title = value
            elif key == 'authors':
                meta.authors = [a.strip() for a in value.split(',')]
            elif key == 'publisher':
                meta.publisher = value
            elif key == 'published':
                meta.pubdate = value
            elif key == 'language':
                meta.language = value
            elif key == 'isbn':
                meta.isbn = value
            elif key == 'tags':
                meta.tags = [t.strip() for t in value.split(',')]
            elif key == 'series':
                meta.series = value
            elif key == 'series index':
                meta.series_index = value
            elif key == 'rating':
                try:
                    meta.rating = float(value)
                except ValueError:
                    pass
            elif key == 'comments':
                meta.comments = value

        return meta

    def write(self, file_path: str, metadata: BookMetadata) -> None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f'File not found: {file_path}')

        cmd = [self._get_ebook_meta_path(), str(path)]
        meta_dict = metadata.to_dict()

        for key, value in meta_dict.items():
            cmd_arg = f'--{key.replace("_", "-")}'
            if isinstance(value, list):
                cmd.append(f'{cmd_arg}={",".join(value)}')
            else:
                cmd.append(f'{cmd_arg}={value}')

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=False,
                check=True
            )
        except subprocess.CalledProcessError as e:
            stderr_str = self._decode_bytes(e.stderr) if e.stderr else str(e)
            raise RuntimeError(f'Failed to write metadata: {stderr_str}') from e

    def to_json(self, metadata: BookMetadata) -> str:
        return json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2)

    def from_json(self, json_str: str) -> BookMetadata:
        data = json.loads(json_str)
        return BookMetadata(**data)
