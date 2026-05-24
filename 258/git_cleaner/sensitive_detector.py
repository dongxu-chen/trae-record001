"""敏感信息检测模块"""
from typing import List, Dict
from git import Repo, Blob
from .config import Config

class SensitiveInfoDetector:
    """检测Git历史中的敏感信息"""
    
    def __init__(self, repo: Repo, config: Config):
        self.repo = repo
        self.config = config
    
    def scan(self) -> List[Dict]:
        """扫描仓库历史中的敏感信息"""
        findings = []
        scanned_blobs = set()
        
        for commit in self.repo.iter_commits():
            try:
                for blob in commit.tree.traverse():
                    if not isinstance(blob, Blob):
                        continue
                    
                    blob_id = blob.hexsha
                    if blob_id in scanned_blobs:
                        continue
                    
                    scanned_blobs.add(blob_id)
                    
                    if blob.size > 10 * 1024 * 1024:  # 跳过10MB以上的文件
                        continue
                    
                    try:
                        content = blob.data_stream.read().decode('utf-8', errors='ignore')
                        self._scan_content(content, blob, commit, findings)
                    except Exception:
                        continue
            except Exception:
                continue
        
        return findings
    
    def _scan_content(self, content: str, blob: Blob, commit, findings: List[Dict]):
        """扫描文件内容中的敏感信息"""
        for pattern in self.config.sensitive_patterns:
            for match in pattern.finditer(content):
                line_num = self._get_line_number(content, match.start())
                findings.append({
                    'type': self._get_match_type(pattern.pattern),
                    'path': blob.path,
                    'match': match.group(0)[:50] + '...' if len(match.group(0)) > 50 else match.group(0),
                    'line': line_num,
                    'blob_id': blob.hexsha,
                    'commit': commit.hexsha,
                    'commit_date': commit.committed_datetime.isoformat(),
                })
    
    def _get_line_number(self, content: str, pos: int) -> int:
        """获取匹配位置的行号"""
        return content.count('\n', 0, pos) + 1
    
    def _get_match_type(self, pattern: str) -> str:
        """根据正则模式返回匹配类型"""
        if 'AKIA' in pattern:
            return 'AWS Access Key'
        elif 'aws' in pattern.lower():
            return 'AWS Credential'
        elif 'private key' in pattern.lower():
            return 'Private Key'
        elif 'ssh-rsa' in pattern:
            return 'SSH Key'
        elif 'ghp_' in pattern:
            return 'GitHub Token'
        elif 'sk-' in pattern:
            return 'API Key'
        elif 'password' in pattern.lower():
            return 'Password'
        elif 'token' in pattern.lower():
            return 'Token'
        elif 'secret' in pattern.lower():
            return 'Secret'
        elif 'api_key' in pattern.lower():
            return 'API Key'
        return 'Sensitive Data'
    
    def group_by_type(self, findings: List[Dict]) -> Dict[str, List[Dict]]:
        """按类型分组敏感信息发现"""
        grouped = {}
        for f in findings:
            t = f['type']
            if t not in grouped:
                grouped[t] = []
            grouped[t].append(f)
        return grouped
