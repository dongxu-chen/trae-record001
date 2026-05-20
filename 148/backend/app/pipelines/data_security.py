from typing import Dict, Any, List, Optional, Callable
import hashlib
import hmac
import base64
import re
from dataclasses import dataclass, field
from enum import Enum
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import pandas as pd

logger = logging.getLogger(__name__)


class MaskingType(Enum):
    """脱敏类型"""
    FULL = "full"              # 全掩码: ********
    PARTIAL = "partial"        # 部分掩码: 138****1234
    HASH = "hash"              # 哈希值: sha256
    HMAC = "hmac"              # HMAC哈希: 需要密钥
    TRUNCATE = "truncate"      # 截断: 只保留前N位
    REPLACE = "replace"        # 固定值替换
    SHUFFLE = "shuffle"        # 随机打乱: 保持格式
    FORMAT_PRESERVING = "fp"   # 格式保留加密


class EncryptionAlgorithm(Enum):
    """加密算法"""
    FERNET = "fernet"          # AES-128-CBC + HMAC-SHA256
    AES256 = "aes256"          # AES-256


@dataclass
class FieldSecurityConfig:
    """字段安全配置"""
    field_name: str
    masking_type: Optional[MaskingType] = None
    encrypt: bool = False
    encrypt_algorithm: EncryptionAlgorithm = EncryptionAlgorithm.FERNET
    masking_params: Dict[str, Any] = field(default_factory=dict)
    keep_length: bool = True   # 保持长度不变


class DataSecurityManager:
    """数据安全管理器 - 加密和脱敏"""

    def __init__(self, encryption_key: str = None):
        self.encryption_key = encryption_key or self._generate_key()
        self.fernet = Fernet(self.encryption_key)
        self._init_masking_functions()

    @staticmethod
    def _generate_key() -> bytes:
        """生成加密密钥"""
        import os
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(b"default_password"))
        return key

    def _init_masking_functions(self):
        """初始化脱敏函数"""
        self.masking_functions = {
            MaskingType.FULL: self._full_mask,
            MaskingType.PARTIAL: self._partial_mask,
            MaskingType.HASH: self._hash_mask,
            MaskingType.HMAC: self._hmac_mask,
            MaskingType.TRUNCATE: self._truncate_mask,
            MaskingType.REPLACE: self._replace_mask,
            MaskingType.SHUFFLE: self._shuffle_mask,
        }

    def _full_mask(self, value: str, **kwargs) -> str:
        """全掩码"""
        if not value:
            return value
        length = len(str(value)) if kwargs.get('keep_length', True) else 8
        return '*' * length

    def _partial_mask(self, value: str, **kwargs) -> str:
        """部分掩码"""
        if not value:
            return value

        value_str = str(value)
        start = kwargs.get('start_chars', 3)
        end = kwargs.get('end_chars', 4)
        mask_char = kwargs.get('mask_char', '*')

        if len(value_str) <= start + end:
            # 太短，中间部分掩码
            mid = len(value_str) // 2
            return value_str[:mid] + mask_char * (len(value_str) - mid)

        return value_str[:start] + mask_char * (len(value_str) - start - end) + value_str[-end:]

    def _hash_mask(self, value: str, **kwargs) -> str:
        """SHA256哈希"""
        if not value:
            return value
        algorithm = kwargs.get('algorithm', 'sha256')
        h = hashlib.new(algorithm)
        h.update(str(value).encode('utf-8'))
        return h.hexdigest()

    def _hmac_mask(self, value: str, **kwargs) -> str:
        """HMAC哈希"""
        if not value:
            return value
        key = kwargs.get('key', b'secret_key')
        if isinstance(key, str):
            key = key.encode('utf-8')
        algorithm = kwargs.get('algorithm', 'sha256')
        return hmac.new(key, str(value).encode('utf-8'), algorithm).hexdigest()

    def _truncate_mask(self, value: str, **kwargs) -> str:
        """截断"""
        if not value:
            return value
        max_length = kwargs.get('max_length', 10)
        suffix = kwargs.get('suffix', '...')
        value_str = str(value)
        if len(value_str) <= max_length:
            return value_str
        return value_str[:max_length] + suffix

    def _replace_mask(self, value: str, **kwargs) -> str:
        """固定值替换"""
        return kwargs.get('replacement', '***')

    def _shuffle_mask(self, value: str, **kwargs) -> str:
        """随机打乱"""
        if not value:
            return value
        import random
        chars = list(str(value))
        random.shuffle(chars)
        return ''.join(chars)

    def encrypt_value(self, value: str) -> str:
        """加密值"""
        if value is None:
            return None
        encoded = str(value).encode()
        encrypted = self.fernet.encrypt(encoded)
        return encrypted.decode('utf-8')

    def decrypt_value(self, encrypted_value: str) -> str:
        """解密值"""
        if encrypted_value is None:
            return None
        try:
            decoded = encrypted_value.encode('utf-8')
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_value

    def mask_value(self, value: Any, config: FieldSecurityConfig) -> Any:
        """对单个值应用脱敏"""
        if value is None:
            return None

        # 如果需要加密
        if config.encrypt:
            return self.encrypt_value(str(value))

        # 如果需要脱敏
        if config.masking_type and config.masking_type in self.masking_functions:
            masking_func = self.masking_functions[config.masking_type]
            return masking_func(value, **config.masking_params, keep_length=config.keep_length)

        return value

    def process_dataframe(self, df: pd.DataFrame, configs: List[FieldSecurityConfig]) -> pd.DataFrame:
        """处理整个DataFrame"""
        result_df = df.copy()

        for config in configs:
            if config.field_name in result_df.columns:
                result_df[config.field_name] = result_df[config.field_name].apply(
                    lambda x: self.mask_value(x, config)
                )

        return result_df

    def process_dict(self, data: Dict[str, Any], configs: List[FieldSecurityConfig]) -> Dict[str, Any]:
        """处理字典数据"""
        result = data.copy()

        for config in configs:
            if config.field_name in result:
                result[config.field_name] = self.mask_value(result[config.field_name], config)

        return result


class PIIMasker:
    """PII (Personally Identifiable Information) 识别和脱敏器"""

    # 常用PII正则模式
    PII_PATTERNS = {
        'phone': re.compile(r'1[3-9]\d{9}'),
        'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        'id_card': re.compile(r'\d{17}[\dXx]|\d{15}'),
        'bank_card': re.compile(r'\d{16,19}'),
        'ipv4': re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'),
    }

    def __init__(self, security_manager: DataSecurityManager = None):
        self.security_manager = security_manager or DataSecurityManager()

    def detect_and_mask_text(self, text: str, pii_types: List[str] = None) -> str:
        """检测并脱敏文本中的PII"""
        if not text:
            return text

        result = str(text)
        types_to_check = pii_types or list(self.PII_PATTERNS.keys())

        for pii_type in types_to_check:
            pattern = self.PII_PATTERNS.get(pii_type)
            if pattern:
                matches = pattern.findall(result)
                for match in matches:
                    config = FieldSecurityConfig(
                        field_name="",
                        masking_type=MaskingType.PARTIAL,
                        masking_params={'start_chars': 3, 'end_chars': 4} if pii_type == 'phone' else {}
                    )
                    masked = self.security_manager.mask_value(match, config)
                    result = result.replace(match, masked)

        return result

    def mask_dataframe_pii(self, df: pd.DataFrame, columns: List[str] = None) -> pd.DataFrame:
        """脱敏DataFrame中的PII"""
        result_df = df.copy()
        cols_to_process = columns or df.columns.tolist()

        for col in cols_to_process:
            if col in result_df.columns and pd.api.types.is_string_dtype(result_df[col]):
                result_df[col] = result_df[col].apply(self.detect_and_mask_text)

        return result_df


# 便捷函数
def create_security_config(
    field_name: str,
    masking_type: str = None,
    encrypt: bool = False,
    **kwargs
) -> FieldSecurityConfig:
    """创建安全配置的便捷函数"""
    return FieldSecurityConfig(
        field_name=field_name,
        masking_type=MaskingType(masking_type) if masking_type else None,
        encrypt=encrypt,
        masking_params=kwargs
    )


def apply_security_to_data(
    data: List[Dict[str, Any]],
    security_configs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    应用安全配置到数据
    security_configs 示例:
    [
        {"field_name": "phone", "masking_type": "partial", "start_chars": 3, "end_chars": 4},
        {"field_name": "email", "masking_type": "hash"},
        {"field_name": "id_card", "encrypt": True}
    ]
    """
    security_manager = DataSecurityManager()
    configs = [
        FieldSecurityConfig(
            field_name=cfg["field_name"],
            masking_type=MaskingType(cfg["masking_type"]) if cfg.get("masking_type") else None,
            encrypt=cfg.get("encrypt", False),
            masking_params={k: v for k, v in cfg.items() if k not in ["field_name", "masking_type", "encrypt"]}
        )
        for cfg in security_configs
    ]

    return [security_manager.process_dict(row, configs) for row in data]


def generate_security_report(data: List[Dict[str, Any]], security_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成数据安全处理报告"""
    total_records = len(data)
    affected_fields = set()

    for cfg in security_configs:
        affected_fields.add(cfg["field_name"])

    return {
        "total_records": total_records,
        "affected_fields": list(affected_fields),
        "security_configs_applied": len(security_configs),
        "operations": [
            {
                "field": cfg["field_name"],
                "operation": "encrypt" if cfg.get("encrypt") else f"mask:{cfg.get('masking_type')}"
            }
            for cfg in security_configs
        ]
    }
