import asyncio
import re
import os
import tarfile
import tempfile
import logging
import yaml
import fnmatch
import mimetypes
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SensitiveFinding:
    file_path: str
    pattern_name: str
    severity: str
    description: str
    line_number: int
    match: str
    category: str
    detection_type: str

class ContentKeywordMatcher:
    def __init__(self, keyword_configs: List[Dict]):
        self.keyword_configs = []
        for config in keyword_configs:
            self.keyword_configs.append({
                'name': config['name'],
                'keywords': [kw.lower() for kw in config['keywords']],
                'severity': config.get('severity', 'medium'),
                'description': config.get('description', ''),
                'category': config.get('category', 'content_analysis')
            })

    def scan_content(self, content: str, file_path: str) -> List[Dict]:
        findings = []
        content_lower = content.lower()
        lines = content.split('\n')

        for config in self.keyword_configs:
            for keyword in config['keywords']:
                if keyword in content_lower:
                    for line_num, line in enumerate(lines, 1):
                        if keyword in line.lower():
                            findings.append({
                                "file_path": file_path,
                                "pattern_name": config['name'],
                                "severity": config['severity'].upper(),
                                "description": config['description'],
                                "line_number": line_num,
                                "match": self._extract_context(line, keyword),
                                "category": config['category'],
                                "detection_type": "keyword",
                                "keyword": keyword
                            })
                            break

        return findings

    def _extract_context(self, line: str, keyword: str, context_chars: int = 30) -> str:
        line = line.strip()
        if len(line) <= context_chars * 2:
            return self._mask_sensitive_data(line)
        
        pos = line.lower().find(keyword.lower())
        if pos == -1:
            return self._mask_sensitive_data(line[:context_chars * 2])
        
        start = max(0, pos - context_chars)
        end = min(len(line), pos + len(keyword) + context_chars)
        context = line[start:end]
        
        if start > 0:
            context = "..." + context
        if end < len(line):
            context = context + "..."
        
        return self._mask_sensitive_data(context)

    def _mask_sensitive_data(self, text: str) -> str:
        if len(text) <= 8:
            return "*" * len(text)
        return text[:4] + "*" * (len(text) - 8) + text[-4:]

class SuspiciousFileDetector:
    def __init__(self, file_patterns: List[Dict]):
        self.file_patterns = file_patterns

    def check_file(self, file_path: str, file_size: int = 0) -> List[Dict]:
        findings = []
        file_path_lower = file_path.lower()
        file_name = os.path.basename(file_path)

        for pattern_config in self.file_patterns:
            for pattern in pattern_config['patterns']:
                pattern_lower = pattern.lower()
                
                if pattern_lower in file_path_lower or \
                   fnmatch.fnmatch(file_name.lower(), f"*{pattern_lower}*") or \
                   fnmatch.fnmatch(file_path_lower, f"*{pattern_lower}*"):
                    
                    findings.append({
                        "file_path": file_path,
                        "pattern_name": pattern_config['name'],
                        "severity": pattern_config['severity'].upper(),
                        "description": pattern_config['description'],
                        "line_number": 0,
                        "match": pattern,
                        "category": pattern_config.get('category', 'file_based'),
                        "detection_type": "file_name",
                        "file_size": file_size
                    })
                    break

        return findings

class SensitiveDataScanner:
    def __init__(self, patterns_file: str):
        self.patterns_file = patterns_file
        self.patterns = []
        self.compiled_patterns = []
        self.content_keyword_matcher: Optional[ContentKeywordMatcher] = None
        self.suspicious_file_detector: Optional[SuspiciousFileDetector] = None
        self._load_patterns()

    def _load_patterns(self):
        try:
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.patterns = config.get('patterns', [])
                
                for pattern in self.patterns:
                    try:
                        compiled = re.compile(pattern['pattern'], re.IGNORECASE | re.MULTILINE)
                        self.compiled_patterns.append({
                            'name': pattern['name'],
                            'severity': pattern.get('severity', 'medium'),
                            'description': pattern.get('description', ''),
                            'pattern': compiled,
                            'file_types': pattern.get('file_types'),
                            'category': pattern.get('category', 'unknown')
                        })
                    except re.error as e:
                        logger.warning(f"Failed to compile pattern {pattern['name']}: {e}")

                content_keywords = config.get('content_keywords', [])
                if content_keywords:
                    self.content_keyword_matcher = ContentKeywordMatcher(content_keywords)
                    logger.info(f"Loaded {len(content_keywords)} content keyword matchers")

                suspicious_files = config.get('suspicious_files', [])
                if suspicious_files:
                    self.suspicious_file_detector = SuspiciousFileDetector(suspicious_files)
                    logger.info(f"Loaded {len(suspicious_files)} suspicious file detectors")
                    
        except Exception as e:
            logger.error(f"Failed to load patterns: {e}")

    async def scan_image(self, image_name: str, docker_client) -> Dict[str, Any]:
        findings = []
        
        try:
            container = None
            temp_dir = tempfile.mkdtemp(prefix='image_scan_')
            
            try:
                container = docker_client.containers.create(
                    image_name,
                    command="sleep infinity"
                )
                
                tar_path = os.path.join(temp_dir, 'image_files.tar')
                with open(tar_path, 'wb') as f:
                    bits, stat = container.get_archive('/')
                    for chunk in bits:
                        f.write(chunk)
                
                total_files = 0
                scanned_files = 0
                
                with tarfile.open(tar_path, 'r') as tar:
                    members = tar.getmembers()
                    total_files = len([m for m in members if m.isfile()])
                    
                    for member in members:
                        if not member.isfile():
                            continue
                        
                        if self._should_skip_file(member.name):
                            continue
                        
                        scanned_files += 1
                        
                        file_findings = self._scan_file_member(tar, member)
                        findings.extend(file_findings)
                            
            finally:
                if container:
                    try:
                        container.remove(force=True)
                    except Exception as e:
                        logger.debug(f"Error removing container: {e}")
                
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.debug(f"Error cleaning up temp dir: {e}")

        except Exception as e:
            logger.error(f"Error scanning image for sensitive data: {e}")
            raise

        summary = self._count_by_severity(findings)

        return {
            "findings": findings,
            "summary": {
                "total_findings": len(findings),
                "total_files_scanned": scanned_files,
                "total_files": total_files,
                "by_severity": summary,
                "by_detection_type": self._count_by_detection_type(findings),
                "by_category": self._count_by_category(findings)
            }
        }

    def _scan_file_member(self, tar: tarfile.TarFile, member: tarfile.TarInfo) -> List[Dict]:
        findings = []
        file_path = member.name
        file_size = member.size

        try:
            if self.suspicious_file_detector:
                file_findings = self.suspicious_file_detector.check_file(file_path, file_size)
                findings.extend(file_findings)

            if file_size > 50 * 1024 * 1024:
                logger.debug(f"Skipping large file {file_path} ({file_size} bytes)")
                return findings

            if file_size > 0:
                f = tar.extractfile(member)
                if f:
                    content = f.read()
                    
                    is_text = self._is_text_content(content[:4096])
                    
                    if is_text:
                        try:
                            text_content = content.decode('utf-8', errors='ignore')
                        except Exception:
                            text_content = content.decode('latin-1', errors='ignore')

                        pattern_findings = self._scan_patterns(text_content, file_path)
                        findings.extend(pattern_findings)

                        if self.content_keyword_matcher:
                            keyword_findings = self.content_keyword_matcher.scan_content(
                                text_content, 
                                file_path
                            )
                            findings.extend(keyword_findings)
                        
        except Exception as e:
            logger.debug(f"Error processing {file_path}: {e}")
        
        return findings

    def _is_text_content(self, sample: bytes) -> bool:
        if not sample:
            return True
        
        text_chars = bytes([7, 8, 9, 10, 12, 13, 27]) + bytes(range(0x20, 0x7f)) + bytes(range(0x80, 0x100))
        
        non_text = sum(1 for byte in sample if byte not in text_chars)
        non_text_ratio = non_text / len(sample)
        
        return non_text_ratio < 0.3

    def _should_skip_file(self, file_path: str) -> bool:
        skip_dirs = ['/proc/', '/sys/', '/dev/', '/tmp/', '/run/', '/var/run/']
        skip_extensions = [
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', 
            '.gz', '.zip', '.tar', '.bz2', '.xz', '.7z',
            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
            '.bin', '.exe', '.dll', '.so', '.o', '.a',
            '.ttf', '.woff', '.woff2', '.eot',
            '.pyc', '.class', '.jar', '.war'
        ]
        skip_files = ['/etc/ld.so.cache', '/var/cache/', '.git/objects/']
        
        for skip_dir in skip_dirs:
            if file_path.startswith(skip_dir):
                return True
        
        for skip_file in skip_files:
            if skip_file in file_path:
                return True
        
        file_lower = file_path.lower()
        for ext in skip_extensions:
            if file_lower.endswith(ext):
                return True
        
        return False

    def _scan_patterns(self, content: str, file_path: str) -> List[Dict]:
        findings = []
        
        for pattern_info in self.compiled_patterns:
            if pattern_info['file_types']:
                file_match = False
                for ft in pattern_info['file_types']:
                    if fnmatch.fnmatch(os.path.basename(file_path), ft):
                        file_match = True
                        break
                if not file_match:
                    continue
            
            matches = list(pattern_info['pattern'].finditer(content))
            
            for match in matches[:20]:
                line_num = content[:match.start()].count('\n') + 1
                
                findings.append({
                    "file_path": file_path,
                    "pattern_name": pattern_info['name'],
                    "severity": pattern_info['severity'].upper(),
                    "description": pattern_info['description'],
                    "line_number": line_num,
                    "match": self._mask_match(match.group()),
                    "category": pattern_info.get('category', 'unknown'),
                    "detection_type": "pattern"
                })
        
        return findings

    def _mask_match(self, match: str) -> str:
        if len(match) <= 4:
            return "*" * len(match)
        return match[:2] + "*" * (len(match) - 4) + match[-2:]

    def _count_by_severity(self, findings: List[Dict]) -> Dict[str, int]:
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for finding in findings:
            sev = finding['severity'].upper()
            if sev in counts:
                counts[sev] += 1
            else:
                counts["LOW"] += 1
        return counts

    def _count_by_detection_type(self, findings: List[Dict]) -> Dict[str, int]:
        counts = {"pattern": 0, "keyword": 0, "file_name": 0}
        for finding in findings:
            dtype = finding.get('detection_type', 'unknown')
            counts[dtype] = counts.get(dtype, 0) + 1
        return counts

    def _count_by_category(self, findings: List[Dict]) -> Dict[str, int]:
        counts = {}
        for finding in findings:
            cat = finding.get('category', 'unknown')
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def get_scanner_stats(self) -> Dict[str, Any]:
        return {
            "total_patterns": len(self.compiled_patterns),
            "keyword_matchers": len(self.content_keyword_matcher.keyword_configs) if self.content_keyword_matcher else 0,
            "file_detectors": len(self.suspicious_file_detector.file_patterns) if self.suspicious_file_detector else 0
        }
