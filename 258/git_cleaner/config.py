"""配置模块"""
from dataclasses import dataclass, field
from typing import List, Pattern
import re
import fnmatch

@dataclass
class Config:
    """清理工具配置"""
    large_file_threshold: int = 10 * 1024 * 1024  # 10MB
    stale_branch_days: int = 365  # 1年
    include_remote_branches: bool = True
    respect_gitignore: bool = True
    
    exclude_patterns: List[str] = field(default_factory=lambda: [
        'node_modules/**',
        'dist/**',
        'build/**',
        'target/**',
        '*.class',
        '*.jar',
        '*.war',
        '*.pyc',
        '__pycache__/**',
        '.gradle/**',
        '.idea/**',
        '.vscode/**',
        '*.o',
        '*.obj',
        '*.exe',
        '*.dll',
        '*.so',
        '*.dylib',
    ])
    
    sensitive_patterns: List[Pattern] = field(default_factory=lambda: [
        re.compile(r'AKIA[0-9A-Z]{16}'),
        re.compile(r'ASIA[0-9A-Z]{16}'),
        re.compile(r'(?i)(aws_secret_access_key|aws_access_key_id|aws_session_token)\s*[=:]\s*["\']?[\w/+=]{10,}["\']?'),
        
        re.compile(r'(?i)(pass(?:word)?|pwd|passwd)\s*[=:]\s*["\']?[^"\'\s]{6,}["\']?'),
        re.compile(r'(?i)pass(?:word)?["\']?\s*[=:]\s*["\']?[^"\'\s]{6,}["\']?'),
        re.compile(r'(?i)(?:db|database)_?pass(?:word)?\s*[=:]\s*["\']?[^"\'\s]{6,}["\']?'),
        re.compile(r'(?i)(?:mysql|postgres|mongo|redis)_?pass(?:word)?\s*[=:]\s*["\']?[^"\'\s]{6,}["\']?'),
        re.compile(r'(?i)jdbc:[^:]+:[^@]+@'),
        
        re.compile(r'(?i)(secret|secrete|sec_key)\s*[=:]\s*["\']?[\w-]{10,}["\']?'),
        re.compile(r'(?i)(?:client|app|api)_?secret\s*[=:]\s*["\']?[\w-]{10,}["\']?'),
        re.compile(r'(?i)private_?key\s*[=:]\s*["\']?[\w/+=]{20,}["\']?'),
        
        re.compile(r'(?i)(token|auth_token|access_token|refresh_token|bearer_token|jwt_token)\s*[=:]\s*["\']?[\w._-]{10,}["\']?'),
        re.compile(r'(?i)(?:auth|authentication|authorization)\s*[=:]\s*["\']?[\w._-]{10,}["\']?'),
        re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
        
        re.compile(r'(?i)(api_?key|apikey|access_key|secret_key)\s*[=:]\s*["\']?[\w-]{10,}["\']?'),
        re.compile(r'(?i)(?:stripe|paypal|slack|discord|telegram|twitter|facebook|google)_?(?:api_?key|token|secret)\s*[=:]\s*["\']?[\w-]{10,}["\']?'),
        
        re.compile(r'-----BEGIN (RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----'),
        re.compile(r'ssh-(?:rsa|ed25519|ecdsa-sha2-nistp256|dsa) AAAA[0-9A-Za-z+/]+[=]{0,3}'),
        re.compile(r'PuTTY-User-Key-File-2:'),
        
        re.compile(r'ghp_[A-Za-z0-9]{36}'),
        re.compile(r'gho_[A-Za-z0-9]{36}'),
        re.compile(r'ghu_[A-Za-z0-9]{36}'),
        re.compile(r'ghs_[A-Za-z0-9]{36}'),
        re.compile(r'github_pat_[A-Za-z0-9_]{82}'),
        
        re.compile(r'sk-[A-Za-z0-9]{48}'),
        re.compile(r'pk-[A-Za-z0-9]{48}'),
        
        re.compile(r'AIza[0-9A-Za-z-_]{35}'),
        re.compile(r'ya29\.[A-Za-z0-9_-]+'),
        
        re.compile(r'sq0csp-[A-Za-z0-9_-]{43}'),
        re.compile(r'xox[baprs]-[A-Za-z0-9-]{10,48}'),
    ])
    
    bfg_jar_path: str = "bfg.jar"
    
    def is_path_excluded(self, path: str) -> bool:
        """检查路径是否应该被排除"""
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, f"**/{pattern}"):
                return True
            if '/' in pattern:
                if fnmatch.fnmatch(path, pattern) or path.startswith(pattern.rstrip('*')):
                    return True
        return False
