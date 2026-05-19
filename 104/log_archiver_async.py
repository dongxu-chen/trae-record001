#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import json
import asyncio
import tarfile
import argparse
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class ArchiveResult:
    def __init__(self, source_dir: str):
        self.source_dir = source_dir
        self.target_dir: Optional[str] = None
        self.success = False
        self.files_found = 0
        self.files_archived = 0
        self.files_deleted = 0
        self.archive_path: Optional[str] = None
        self.error: Optional[str] = None
        self.filtered_by_content = 0
        self.skipped_incremental = 0


class IncrementalState:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.last_archive_time: Dict[str, str] = {}
        self.archived_files: Dict[str, Set[str]] = {}
        self._load()

    def _load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_archive_time = data.get('last_archive_time', {})
                    self.archived_files = {
                        k: set(v) for k, v in data.get('archived_files', {}).items()
                    }
            except Exception:
                pass

    def save(self):
        data = {
            'last_archive_time': self.last_archive_time,
            'archived_files': {k: list(v) for k, v in self.archived_files.items()},
            'updated_at': datetime.now().isoformat()
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def is_archived(self, source_dir: str, filename: str) -> bool:
        return filename in self.archived_files.get(source_dir, set())

    def mark_archived(self, source_dir: str, filenames: List[str]):
        if source_dir not in self.archived_files:
            self.archived_files[source_dir] = set()
        self.archived_files[source_dir].update(filenames)
        self.last_archive_time[source_dir] = datetime.now().isoformat()


class AsyncLogArchiver:
    def __init__(
        self,
        source_dir: str,
        target_dir: str,
        retention_days: int = 7,
        compress_level: int = 6,
        content_filter: Optional[str] = None,
        case_sensitive: bool = False,
        incremental_state: Optional[IncrementalState] = None,
        use_system_gzip: bool = True
    ):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.retention_days = max(1, retention_days)
        self.compress_level = max(1, min(9, compress_level))
        self.cutoff_date = datetime.now() - timedelta(days=retention_days)
        self.log_pattern = re.compile(r'.*-(\d{4}-\d{2}-\d{2})\.log$')
        self.content_filter = content_filter
        self.case_sensitive = case_sensitive
        self.incremental_state = incremental_state
        self.use_system_gzip = use_system_gzip
        self.result = ArchiveResult(str(source_dir))
        self.result.target_dir = str(target_dir)

    async def ensure_target_dir(self):
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def parse_log_date(self, filename: str) -> Optional[datetime]:
        match = self.log_pattern.match(filename)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                return None
        return None

    async def check_content_match(self, file_path: Path) -> bool:
        if not self.content_filter:
            return True
        
        flags = 0 if self.case_sensitive else re.IGNORECASE
        pattern = re.compile(self.content_filter, flags)
        
        try:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    async for line in f:
                        if pattern.search(line):
                            return True
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        if pattern.search(line):
                            return True
        except Exception:
            pass
        return False

    async def scan_files(self, queue: asyncio.Queue):
        if not self.source_dir.exists():
            return

        with os.scandir(self.source_dir) as entries:
            for entry in entries:
                if not entry.is_file(follow_symlinks=False):
                    continue
                
                log_date = self.parse_log_date(entry.name)
                if not log_date or log_date > self.cutoff_date:
                    continue
                
                self.result.files_found += 1
                
                if self.incremental_state and self.incremental_state.is_archived(
                    str(self.source_dir), entry.name
                ):
                    self.result.skipped_incremental += 1
                    continue
                
                file_path = Path(entry.path)
                if await self.check_content_match(file_path):
                    await queue.put(file_path)
                else:
                    self.result.filtered_by_content += 1

    async def verify_archive(self, archive_path: Path, expected_files: List[Path]) -> bool:
        try:
            def _check():
                with tarfile.open(archive_path, 'r:gz') as tar:
                    members = tar.getmembers()
                    member_names = {m.name for m in members}
                    
                    for log_file in expected_files:
                        if log_file.name not in member_names:
                            return False
                    
                    for member in members:
                        try:
                            tar.extractfile(member)
                        except Exception:
                            return False
                    return True
            
            return await asyncio.to_thread(_check)
        except Exception:
            return False

    async def compress_with_system_gzip(
        self,
        temp_tar_path: Path,
        final_archive_path: Path
    ) -> bool:
        try:
            gzip_path = temp_tar_path.with_suffix('.tar.gz')
            
            proc = await asyncio.create_subprocess_exec(
                'gzip',
                f'-{self.compress_level}',
                '-c',
                str(temp_tar_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return False
            
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(gzip_path, 'wb') as f:
                    await f.write(stdout)
            else:
                with open(gzip_path, 'wb') as f:
                    f.write(stdout)
            
            await asyncio.to_thread(gzip_path.rename, final_archive_path)
            return True
            
        except Exception:
            return False

    async def create_tar_archive(
        self,
        files: List[Path],
        temp_tar_path: Path
    ) -> bool:
        try:
            def _create():
                with tarfile.open(temp_tar_path, 'w') as tar:
                    for file_path in files:
                        tar.add(file_path, arcname=file_path.name)
                return True
            
            return await asyncio.to_thread(_create)
        except Exception:
            return False

    async def compress_with_python(
        self,
        files: List[Path],
        final_archive_path: Path
    ) -> bool:
        try:
            def _compress():
                with tarfile.open(final_archive_path, f'w:gz', compresslevel=self.compress_level) as tar:
                    for file_path in files:
                        tar.add(file_path, arcname=file_path.name)
                return True
            
            return await asyncio.to_thread(_compress)
        except Exception:
            return False

    async def compress_files(self, files: List[Path]) -> Optional[Path]:
        if not files:
            return None

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_name = f'logs_archive_{timestamp}.tar.gz'
        final_archive_path = self.target_dir / archive_name

        fd, temp_path = tempfile.mkstemp(suffix='.tar', dir=self.target_dir)
        os.close(fd)
        temp_tar_path = Path(temp_path)

        try:
            if self.use_system_gzip:
                if not await self.create_tar_archive(files, temp_tar_path):
                    raise RuntimeError('Failed to create tar archive')
                
                if not await self.compress_with_system_gzip(temp_tar_path, final_archive_path):
                    if temp_tar_path.exists():
                        temp_tar_path.unlink()
                    raise RuntimeError('System gzip failed, falling back to Python')
            else:
                if not await self.compress_with_python(files, final_archive_path):
                    raise RuntimeError('Python compression failed')

            if not await self.verify_archive(final_archive_path, files):
                if final_archive_path.exists():
                    final_archive_path.unlink()
                raise RuntimeError('Archive verification failed')

            return final_archive_path

        except Exception as e:
            if temp_tar_path.exists():
                temp_tar_path.unlink()
            raise RuntimeError(f'Compression failed: {str(e)}')

    async def delete_files(self, files: List[Path]) -> int:
        deleted_count = 0
        for file_path in files:
            try:
                await asyncio.to_thread(file_path.unlink)
                deleted_count += 1
            except Exception:
                pass
        return deleted_count

    async def run_consumer(self, queue: asyncio.Queue, batch_size: int = 50):
        batch = []
        
        while True:
            try:
                file_path = await queue.get()
                
                if file_path is None:
                    if batch:
                        await self.process_batch(batch)
                    queue.task_done()
                    break
                
                batch.append(file_path)
                
                if len(batch) >= batch_size:
                    await self.process_batch(batch)
                    batch = []
                
                queue.task_done()
                
            except Exception as e:
                self.result.error = str(e)
                break

    async def process_batch(self, files: List[Path]):
        try:
            archive_path = await self.compress_files(files)
            if archive_path:
                self.result.archive_path = str(archive_path)
                self.result.files_archived += len(files)
                
                deleted = await self.delete_files(files)
                self.result.files_deleted += deleted
                
                if self.incremental_state:
                    self.incremental_state.mark_archived(
                        str(self.source_dir),
                        [f.name for f in files]
                    )
        except Exception as e:
            self.result.error = str(e)
            raise

    async def run(self, batch_size: int = 50) -> ArchiveResult:
        try:
            await self.ensure_target_dir()
            
            queue: asyncio.Queue[Optional[Path]] = asyncio.Queue(maxsize=100)
            
            producer = asyncio.create_task(self.scan_files(queue))
            consumer = asyncio.create_task(self.run_consumer(queue, batch_size))
            
            await producer
            await queue.put(None)
            await consumer
            
            self.result.success = self.result.error is None
            
        except Exception as e:
            self.result.error = str(e)
            self.result.success = False
        
        return self.result


def load_yaml_config(config_file: Path) -> Optional[Dict]:
    if not YAML_AVAILABLE:
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def load_ini_config(config_file: Path) -> Dict:
    import configparser
    config = configparser.ConfigParser()
    
    settings = {
        'global': {
            'retention_days': 7,
            'compress_level': 6,
            'content_filter': None,
            'case_sensitive': False,
            'incremental': True,
            'use_system_gzip': True
        },
        'directories': [{'source': '.', 'target': './archive'}],
        'email': None
    }
    
    try:
        if not config_file.exists():
            return settings

        config.read(config_file)
        
        if 'Settings' in config:
            s = config['Settings']
            try:
                settings['global']['retention_days'] = max(1, s.getint('retention_days', 7))
            except (ValueError, TypeError):
                pass
            try:
                settings['global']['compress_level'] = max(1, min(9, s.getint('compress_level', 6)))
            except (ValueError, TypeError):
                pass
            settings['global']['content_filter'] = s.get('content_filter', None) or None
            settings['global']['case_sensitive'] = s.getboolean('case_sensitive', False)
            settings['global']['incremental'] = s.getboolean('incremental', True)
            settings['global']['use_system_gzip'] = s.getboolean('use_system_gzip', True)
            
            source = s.get('log_dir', '.')
            target = s.get('archive_dir', './archive')
            settings['directories'] = [{'source': source, 'target': target}]
        
        if 'Email' in config:
            e = config['Email']
            settings['email'] = {
                'smtp_host': e.get('smtp_host', ''),
                'smtp_port': e.getint('smtp_port', 465),
                'smtp_user': e.get('smtp_user', ''),
                'smtp_password': e.get('smtp_password', ''),
                'from_addr': e.get('from_addr', ''),
                'to_addrs': [addr.strip() for addr in e.get('to_addrs', '').split(',') if addr.strip()],
                'use_tls': e.getboolean('use_tls', True)
            }
    
    except Exception:
        pass
    
    return settings


def load_config(config_file: str) -> Optional[Dict]:
    if not config_file:
        return None
    
    config_path = Path(config_file)
    if not config_path.exists():
        return None
    
    if config_file.endswith(('.yaml', '.yml')):
        yaml_config = load_yaml_config(config_path)
        if yaml_config:
            return parse_yaml_config(yaml_config)
    
    return load_ini_config(config_path)


def parse_yaml_config(yaml_config: Dict) -> Dict:
    settings = {
        'global': {
            'retention_days': 7,
            'compress_level': 6,
            'content_filter': None,
            'case_sensitive': False,
            'incremental': True,
            'use_system_gzip': True
        },
        'directories': [],
        'email': None
    }
    
    if 'global' in yaml_config:
        g = yaml_config['global']
        settings['global']['retention_days'] = max(1, g.get('retention_days', 7))
        settings['global']['compress_level'] = max(1, min(9, g.get('compress_level', 6)))
        settings['global']['content_filter'] = g.get('content_filter')
        settings['global']['case_sensitive'] = g.get('case_sensitive', False)
        settings['global']['incremental'] = g.get('incremental', True)
        settings['global']['use_system_gzip'] = g.get('use_system_gzip', True)
    
    if 'directories' in yaml_config and isinstance(yaml_config['directories'], list):
        for dir_pair in yaml_config['directories']:
            if isinstance(dir_pair, dict) and 'source' in dir_pair and 'target' in dir_pair:
                settings['directories'].append({
                    'source': dir_pair['source'],
                    'target': dir_pair['target'],
                    'retention_days': dir_pair.get('retention_days'),
                    'compress_level': dir_pair.get('compress_level'),
                    'content_filter': dir_pair.get('content_filter')
                })
    
    if not settings['directories']:
        settings['directories'] = [{'source': '.', 'target': './archive'}]
    
    if 'email' in yaml_config:
        e = yaml_config['email']
        settings['email'] = {
            'smtp_host': e.get('smtp_host', ''),
            'smtp_port': e.get('smtp_port', 465),
            'smtp_user': e.get('smtp_user', ''),
            'smtp_password': e.get('smtp_password', ''),
            'from_addr': e.get('from_addr', ''),
            'to_addrs': e.get('to_addrs', []),
            'use_tls': e.get('use_tls', True)
        }
    
    return settings


async def main_async():
    parser = argparse.ArgumentParser(description='Async Server Log Auto Archiver')
    parser.add_argument('--config', '-c', help='Path to configuration file (INI or YAML)')
    parser.add_argument('--log-dir', '-l', help='Directory containing log files')
    parser.add_argument('--archive-dir', '-a', help='Directory to store archived files')
    parser.add_argument('--retention-days', '-d', type=int, help='Number of days to retain logs')
    parser.add_argument('--compress-level', '-z', type=int, choices=range(1, 10), default=6,
                        help='GZIP compression level (1-9, default: 6)')
    parser.add_argument('--content-filter', '-f', help='Regex pattern to filter log content')
    parser.add_argument('--case-sensitive', action='store_true',
                        help='Make content filter case-sensitive')
    parser.add_argument('--no-incremental', action='store_true',
                        help='Disable incremental backup')
    parser.add_argument('--no-system-gzip', action='store_true',
                        help='Use Python gzip instead of system gzip command')
    parser.add_argument('--batch-size', '-b', type=int, default=50,
                        help='Batch size for compression (default: 50)')
    parser.add_argument('--state-file', default='./.archive_state.json',
                        help='Path to incremental state file (default: ./.archive_state.json)')

    args = parser.parse_args()

    config = load_config(args.config) or {}
    global_config = config.get('global', {})
    directories = config.get('directories', [])

    if args.log_dir and args.archive_dir:
        directories = [{
            'source': args.log_dir,
            'target': args.archive_dir,
            'retention_days': args.retention_days,
            'compress_level': args.compress_level,
            'content_filter': args.content_filter
        }]
    elif not directories:
        directories = [{
            'source': args.log_dir or '.',
            'target': args.archive_dir or './archive',
            'retention_days': args.retention_days or 7,
            'compress_level': args.compress_level or 6,
            'content_filter': args.content_filter
        }]

    incremental_state = None
    if not args.no_incremental and global_config.get('incremental', True):
        incremental_state = IncrementalState(Path(args.state_file))

    use_system_gzip = not args.no_system_gzip and global_config.get('use_system_gzip', True)

    results = []
    tasks = []
    
    for dir_pair in directories:
        retention_days = dir_pair.get('retention_days') or global_config.get('retention_days', 7)
        compress_level = dir_pair.get('compress_level') or global_config.get('compress_level', 6)
        content_filter = dir_pair.get('content_filter') or args.content_filter or global_config.get('content_filter')
        case_sensitive = args.case_sensitive or global_config.get('case_sensitive', False)

        archiver = AsyncLogArchiver(
            source_dir=dir_pair['source'],
            target_dir=dir_pair['target'],
            retention_days=retention_days,
            compress_level=compress_level,
            content_filter=content_filter,
            case_sensitive=case_sensitive,
            incremental_state=incremental_state,
            use_system_gzip=use_system_gzip
        )
        
        tasks.append(archiver.run(batch_size=args.batch_size))
        print(f'Queued: {dir_pair["source"]} → {dir_pair["target"]}')

    print(f'\nStarting concurrent processing of {len(tasks)} directories...\n')
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            dir_name = directories[i]['source']
            error_result = ArchiveResult(dir_name)
            error_result.error = str(result)
            error_result.success = False
            processed_results.append(error_result)
            print(f'✗ [{dir_name}] FAILED: {result}')
        else:
            processed_results.append(result)
            if result.success:
                print(f'✓ [{result.source_dir}] '
                      f'Found: {result.files_found}, '
                      f'Archived: {result.files_archived}, '
                      f'Deleted: {result.files_deleted}')
                if result.skipped_incremental:
                    print(f'  Skipped (incremental): {result.skipped_incremental}')
                if result.filtered_by_content:
                    print(f'  Filtered out: {result.filtered_by_content}')
            else:
                print(f'✗ [{result.source_dir}] FAILED: {result.error}')

    if incremental_state:
        incremental_state.save()
        print(f'\nIncremental state saved to {args.state_file}')

    success_count = sum(1 for r in processed_results if r.success)
    print(f'\n{"="*60}')
    print(f'All tasks completed: {success_count}/{len(processed_results)} succeeded')
    print(f'{"="*60}')


def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main_async())


if __name__ == '__main__':
    main()
