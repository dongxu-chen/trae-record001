import base64
import os
import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

logger = logging.getLogger(__name__)


class AESCrypto:
    def __init__(self, key=None):
        if key:
            self.key = self._pad_key(key)
        else:
            env_key = os.environ.get('BACKUP_AES_KEY', 'backup_default_key_2024')
            self.key = self._pad_key(env_key)

    def _pad_key(self, key):
        key_bytes = key.encode('utf-8')
        if len(key_bytes) >= 32:
            return key_bytes[:32]
        return key_bytes.ljust(32, b'\x00')

    def encrypt(self, plaintext):
        try:
            iv = os.urandom(16)
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()

            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            result = base64.b64encode(iv + ciphertext).decode('utf-8')
            logger.info("密码加密成功")
            return f"ENC:{result}"
        except Exception as e:
            logger.error(f"密码加密失败: {str(e)}")
            return plaintext

    def decrypt(self, ciphertext):
        try:
            if not ciphertext.startswith("ENC:"):
                logger.warning("检测到明文密码，建议使用加密模式")
                return ciphertext

            encrypted_data = base64.b64decode(ciphertext[4:])
            iv = encrypted_data[:16]
            ciphertext_bytes = encrypted_data[16:]

            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()

            padded_plaintext = decryptor.update(ciphertext_bytes) + decryptor.finalize()

            unpadder = padding.PKCS7(128).unpadder()
            plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()

            result = plaintext_bytes.decode('utf-8')
            logger.info("密码解密成功")
            return result
        except Exception as e:
            logger.error(f"密码解密失败: {str(e)}")
            return ciphertext


def encrypt_password(password, key=None):
    crypto = AESCrypto(key)
    return crypto.encrypt(password)


def decrypt_password(encrypted_password, key=None):
    crypto = AESCrypto(key)
    return crypto.decrypt(encrypted_password)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法: python crypto_utils.py <密码> [密钥]")
        sys.exit(1)

    password = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else None

    encrypted = encrypt_password(password, key)
    print(f"原始密码: {password}")
    print(f"加密后: {encrypted}")

    decrypted = decrypt_password(encrypted, key)
    print(f"解密后: {decrypted}")
