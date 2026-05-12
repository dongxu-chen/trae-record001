
import hashlib
import string
import re
import time
from datetime import datetime

from sqlalchemy.orm import Session
from db import URL

BASE62 = string.digits + string.ascii_letters
MAX_RETRIES = 100
SHORT_CODE_MIN_LENGTH = 3
SHORT_CODE_MAX_LENGTH = 32
SHORT_CODE_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")


def is_valid_custom_code(custom_code: str) -> bool:
    if not custom_code:
        return False
    if len(custom_code) < SHORT_CODE_MIN_LENGTH or len(custom_code) > SHORT_CODE_MAX_LENGTH:
        return False
    return bool(SHORT_CODE_PATTERN.match(custom_code))


def base62_encode(number: int) -> str:
    if number == 0:
        return BASE62[0]
    digits = []
    while number > 0:
        number, rem = divmod(number, 62)
        digits.append(BASE62[rem])
    return ''.join(reversed(digits))


def generate_short_code(original_url: str, counter: int = 0) -> str:
    if counter == 0:
        seed = original_url
    else:
        seed = f"{original_url}{counter}{time.time()}"
    hash_object = hashlib.sha256(seed.encode())
    hash_int = int.from_bytes(hash_object.digest(), 'big')
    return base62_encode(hash_int)[:8]


def create_short_url(db: Session, original_url: str, custom_code: str = None, expires_at: datetime = None) -> URL:
    if custom_code:
        if not is_valid_custom_code(custom_code):
            raise ValueError("Invalid custom short code")
        existing = db.query(URL).filter(URL.short_code == custom_code).first()
        if existing:
            raise ValueError(f"Custom code '{custom_code}' is already taken")
        db_url = URL(
            original_url=original_url,
            short_code=custom_code,
            expires_at=expires_at
        )
        db.add(db_url)
        db.commit()
        db.refresh(db_url)
        return db_url

    existing = db.query(URL).filter(URL.original_url == original_url).first()
    if existing:
        return existing

    for counter in range(MAX_RETRIES):
        short_code = generate_short_code(original_url, counter)
        existing_code = db.query(URL).filter(URL.short_code == short_code).first()
        if not existing_code:
            db_url = URL(
                original_url=original_url,
                short_code=short_code,
                expires_at=expires_at
            )
            db.add(db_url)
            db.commit()
            db.refresh(db_url)
            return db_url

    raise RuntimeError("Failed to generate unique short code after maximum retries")


def get_original_url(db: Session, short_code: str) -> URL:
    return db.query(URL).filter(URL.short_code == short_code).first()


def delete_short_url(db: Session, short_code: str) -> bool:
    db_url = db.query(URL).filter(URL.short_code == short_code).first()
    if db_url:
        db.delete(db_url)
        db.commit()
        return True
    return False


def increment_click_count(db: Session, db_url: URL):
    db_url.click_count += 1
    db.commit()
