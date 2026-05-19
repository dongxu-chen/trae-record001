from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import re
import jieba
from typing import Tuple, Optional
from .config import settings

SENSITIVE_PATTERNS = [
    (r'1[3-9]\d{9}', '[电话]'),
    (r'\d{17}[\dXx]', '[身份证]'),
    (r'\d{11,12}', '[学号]'),
    (r'[\u4e00-\u9fa5]{2,4}(?:同学|老师|医生)', '[姓名]'),
    (r'\d{4}-\d{2}-\d{2}', '[日期]'),
    (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[邮箱]'),
    (r'(?:微信号|微信|QQ|q号)[:：]\s*[a-zA-Z0-9_-]+', '[社交账号]'),
    (r'(?:地址|住址|学校|学院|专业)[:：][^\n,，。；;]+', '[地址]'),
]

CRISIS_KEYWORDS = {
    '紧急': ['自杀', '想死', '不想活', '结束生命', '活不下去', '跳楼', '割腕', '自杀计划', '告别', '遗书'],
    '警告': ['抑郁', '绝望', '无助', '痛苦', '崩溃', '想死', '焦虑', '失眠', '暴食', '厌食', '自残', '自伤'],
    '关注': ['压力大', '不开心', '难过', '悲伤', '郁闷', '孤独', '寂寞', '迷茫', '困惑', '自卑']
}


def get_encryption_key() -> bytes:
    password = settings.SECRET_KEY.encode()
    salt = settings.ENCRYPTION_SALT
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_content(content: str) -> str:
    key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(content.encode('utf-8'))
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')


def decrypt_content(encrypted_content: str) -> str:
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted = base64.urlsafe_b64decode(encrypted_content.encode('utf-8'))
        decrypted = f.decrypt(encrypted)
        return decrypted.decode('utf-8')
    except Exception:
        return '[内容无法解密]'


def desensitize_text(text: str) -> str:
    if not text:
        return text
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = re.sub(pattern, replacement, result)
    return result


def analyze_crisis_level(content: str) -> Tuple[str, Optional[str]]:
    words = jieba.lcut(content)
    
    for level, keywords in CRISIS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in content:
                return level, keyword
    
    word_count = len([w for w in words if len(w.strip()) > 0])
    negative_words = ['不', '没', '无', '难', '累', '苦', '痛', '哭']
    negative_count = sum(1 for w in words if w in negative_words)
    
    if word_count > 50 and negative_count / word_count > 0.1:
        return '关注', '情绪表达较多'
    
    return '正常', None
