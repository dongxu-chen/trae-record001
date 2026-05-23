import os
import io
import tarfile
import gzip
import logging
from pathlib import Path
from typing import List, Optional, Generator, Tuple
import fnmatch


class StreamCompressor:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._buffer = io.BytesIO()

    def _should_exclude(self, file_path: str, exclude_patterns: List[str]) -> bool:
        file_name = os.path.basename(file_path)
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern):
                return True
        return False

    def _collect_files(
        self,
        source_dir: str,
        files_to_include: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[Tuple[str, str]]:
        exclude_patterns = exclude_patterns or []
        source_path = Path(source_dir)
        files = []

        if files_to_include:
            for file_path in files_to_include:
                if self._should_exclude(file_path, exclude_patterns):
                    continue
                full_path = Path(file_path)
                if full_path.exists() and full_path.is_file():
                    arcname = str(full_path.relative_to(source_path.parent))
                    files.append((str(full_path), arcname))
        else:
            for root, dirs, filenames in os.walk(source_dir):
                dirs[:] = [d for d in dirs if not self._should_exclude(os.path.join(root, d), exclude_patterns)]
                
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if self._should_exclude(file_path, exclude_patterns):
                        continue
                    full_path = Path(file_path)
                    arcname = str(full_path.relative_to(source_path.parent))
                    files.append((str(full_path), arcname))

        return files

    def stream_compress(
        self,
        source_dir: str,
        files_to_include: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        chunk_size: int = 1024 * 1024
    ) -> Generator[bytes, None, int]:
        files = self._collect_files(source_dir, files_to_include, exclude_patterns)
        self.logger.info(f"开始流式压缩，共 {len(files)} 个文件")

        buffer = io.BytesIO()
        
        with tarfile.open(fileobj=buffer, mode='w|') as tar:
            for file_path, arcname in files:
                try:
                    tar.add(file_path, arcname=arcname)
                    
                    buffer.seek(0)
                    while True:
                        chunk = buffer.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
                    buffer.seek(0)
                    buffer.truncate()
                except Exception as e:
                    self.logger.warning(f"添加文件失败 {file_path}: {e}")

        buffer.seek(0)
        while True:
            chunk = buffer.read(chunk_size)
            if not chunk:
                break
            yield chunk

        total_size = sum(os.path.getsize(f[0]) for f in files if os.path.exists(f[0]))
        self.logger.info(f"流式压缩完成，原始文件总大小: {total_size / (1024*1024):.2f} MB")
        return total_size


class Compressor:
    def __init__(self, temp_dir: str = "./temp", logger: Optional[logging.Logger] = None):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)
        self.stream_compressor = StreamCompressor(logger)

    def _should_exclude(self, file_path: str, exclude_patterns: List[str]) -> bool:
        return self.stream_compressor._should_exclude(file_path, exclude_patterns)

    def create_tar_gz(
        self,
        source_dir: str,
        output_filename: str,
        files_to_include: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> str:
        exclude_patterns = exclude_patterns or []
        output_path = self.temp_dir / f"{output_filename}.tar.gz"

        source_path = Path(source_dir)
        if not source_path.exists():
            raise FileNotFoundError(f"源目录不存在: {source_dir}")

        self.logger.info(f"开始压缩: {source_dir} -> {output_path}")

        with tarfile.open(output_path, "w:gz") as tar:
            if files_to_include:
                for file_path in files_to_include:
                    if self._should_exclude(file_path, exclude_patterns):
                        continue
                    full_path = Path(file_path)
                    if full_path.exists():
                        arcname = full_path.relative_to(source_path.parent)
                        tar.add(full_path, arcname=arcname)
                        self.logger.debug(f"添加文件: {file_path}")
            else:
                for root, dirs, files in os.walk(source_dir):
                    dirs[:] = [d for d in dirs if not self._should_exclude(os.path.join(root, d), exclude_patterns)]
                    
                    for file in files:
                        file_path = os.path.join(root, file)
                        if self._should_exclude(file_path, exclude_patterns):
                            continue
                        
                        full_path = Path(file_path)
                        arcname = full_path.relative_to(source_path.parent)
                        tar.add(full_path, arcname=arcname)
                        self.logger.debug(f"添加文件: {file_path}")

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        self.logger.info(f"压缩完成: {output_path}, 大小: {file_size:.2f} MB")

        return str(output_path)

    def stream_compress_and_upload(
        self,
        source_dir: str,
        files_to_include: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
        upload_callback,
        chunk_size: int = 1024 * 1024
    ) -> Tuple[int, int]:
        exclude_patterns = exclude_patterns or []
        files = self.stream_compressor._collect_files(source_dir, files_to_include, exclude_patterns)
        
        total_raw_size = sum(os.path.getsize(f[0]) for f in files if os.path.exists(f[0]))
        self.logger.info(f"开始流式压缩并上传，共 {len(files)} 个文件，原始大小: {total_raw_size / (1024*1024):.2f} MB")

        compressed_data = io.BytesIO()
        
        with tarfile.open(fileobj=compressed_data, mode='w:gz') as tar:
            for file_path, arcname in files:
                try:
                    tar.add(file_path, arcname=arcname)
                    self.logger.debug(f"添加文件到压缩流: {file_path}")
                except Exception as e:
                    self.logger.warning(f"添加文件失败 {file_path}: {e}")

        compressed_size = compressed_data.tell()
        compressed_data.seek(0)
        
        self.logger.info(f"压缩完成，压缩后大小: {compressed_size / (1024*1024):.2f} MB")
        
        upload_callback(compressed_data, compressed_size)
        
        return len(files), compressed_size

    def cleanup(self, file_path: str) -> None:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"清理临时文件: {file_path}")
        except Exception as e:
            self.logger.warning(f"清理临时文件失败 {file_path}: {e}")
