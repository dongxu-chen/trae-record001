import logging
import hashlib
import hmac
import os
import struct
from typing import Tuple, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class CryptoVerifier:
    SUPPORTED_ALGORITHMS = ['AES-256-CBC', 'AES-128-CBC', 'AES-256-GCM', 'AES-128-GCM']
    HASH_ALGORITHMS = ['SHA256', 'SHA512', 'MD5']

    def __init__(self, key: str, algorithm: str = "AES-256-CBC", hash_algorithm: str = "SHA256"):
        self.key = key.encode('utf-8') if isinstance(key, str) else key
        self.algorithm = algorithm.upper()
        self.hash_algorithm = hash_algorithm.upper()

        if self.algorithm not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}. Supported: {self.SUPPORTED_ALGORITHMS}")

        if self.hash_algorithm not in self.HASH_ALGORITHMS:
            raise ValueError(f"Unsupported hash algorithm: {self.hash_algorithm}. Supported: {self.HASH_ALGORITHMS}")

        self._derive_key_iv()

    def _derive_key_iv(self):
        if '256' in self.algorithm:
            key_len = 32
        elif '128' in self.algorithm:
            key_len = 16
        else:
            key_len = 32

        iv_len = 16

        derived = hashlib.pbkdf2_hmac(
            'sha256',
            self.key,
            salt=b'backup_verification_salt',
            iterations=100000,
            dklen=key_len + iv_len
        )

        self._derived_key = derived[:key_len]
        self._iv = derived[key_len:key_len + iv_len]

    def calculate_file_hash(self, file_path: str, hash_algorithm: str = None) -> str:
        algo = hash_algorithm or self.hash_algorithm
        if algo == 'SHA256':
            h = hashlib.sha256()
        elif algo == 'SHA512':
            h = hashlib.sha512()
        elif algo == 'MD5':
            h = hashlib.md5()
        else:
            h = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)

        return h.hexdigest()

    def calculate_hmac(self, data: bytes) -> str:
        if self.hash_algorithm == 'SHA256':
            return hmac.new(self._derived_key, data, hashlib.sha256).hexdigest()
        elif self.hash_algorithm == 'SHA512':
            return hmac.new(self._derived_key, data, hashlib.sha512).hexdigest()
        else:
            return hmac.new(self._derived_key, data, hashlib.sha256).hexdigest()

    def verify_file_integrity(self, file_path: str) -> Tuple[bool, Optional[str]]:
        original_hash = self.calculate_file_hash(file_path)
        hmac_file = file_path + ".hmac"

        if not os.path.exists(hmac_file):
            logger.warning(f"HMAC file not found: {hmac_file}, skipping HMAC verification")
            return True, original_hash

        try:
            with open(hmac_file, 'r') as f:
                stored_hmac = f.read().strip()

            with open(file_path, 'rb') as f:
                file_data = f.read()

            computed_hmac = self.calculate_hmac(file_data)

            if hmac.compare_digest(computed_hmac, stored_hmac):
                logger.info("File integrity verified successfully (HMAC match)")
                return True, original_hash
            else:
                logger.error("File integrity verification failed (HMAC mismatch)")
                return False, original_hash

        except Exception as e:
            logger.error(f"Integrity verification error: {e}")
            return False, original_hash

    def encrypt_file(self, input_path: str, output_path: str) -> Tuple[bool, str]:
        try:
            with open(input_path, 'rb') as f:
                data = f.read()

            original_hash = self.calculate_file_hash(input_path)

            if 'CBC' in self.algorithm:
                cipher = Cipher(algorithms.AES(self._derived_key), modes.CBC(self._iv), backend=default_backend())
                encryptor = cipher.encryptor()

                padder = padding.PKCS7(128).padder()
                padded_data = padder.update(data) + padder.finalize()

                encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

                with open(output_path, 'wb') as f:
                    f.write(self._iv + encrypted_data)

            elif 'GCM' in self.algorithm:
                cipher = Cipher(algorithms.AES(self._derived_key), modes.GCM(self._iv), backend=default_backend())
                encryptor = cipher.encryptor()
                encrypted_data = encryptor.update(data) + encryptor.finalize()

                with open(output_path, 'wb') as f:
                    f.write(encryptor.tag + self._iv + encrypted_data)

            with open(output_path, 'rb') as f:
                file_content = f.read()
            hmac_val = self.calculate_hmac(file_content)
            with open(output_path + ".hmac", 'w') as f:
                f.write(hmac_val)

            with open(output_path + ".orig_hash", 'w') as f:
                f.write(original_hash)

            logger.info(f"File encrypted successfully: {output_path}")
            return True, original_hash

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return False, ""

    def decrypt_file(self, input_path: str, output_path: str) -> bool:
        try:
            with open(input_path, 'rb') as f:
                iv = f.read(16)
                encrypted_data = f.read()

            if 'CBC' in self.algorithm:
                cipher = Cipher(algorithms.AES(self._derived_key), modes.CBC(iv), backend=default_backend())
                decryptor = cipher.decryptor()

                padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

                unpadder = padding.PKCS7(128).unpadder()
                data = unpadder.update(padded_data) + unpadder.finalize()

            elif 'GCM' in self.algorithm:
                tag = encrypted_data[:16]
                ciphertext = encrypted_data[16:]

                cipher = Cipher(algorithms.AES(self._derived_key), modes.GCM(iv, tag), backend=default_backend())
                decryptor = cipher.decryptor()
                data = decryptor.update(ciphertext) + decryptor.finalize()

            with open(output_path, 'wb') as f:
                f.write(data)

            logger.info(f"File decrypted successfully: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return False

    def verify_encryption(self, encrypted_path: str, original_path: str) -> Tuple[bool, str]:
        try:
            if not os.path.exists(encrypted_path):
                return False, "Encrypted file not found"

            if os.path.exists(encrypted_path + ".orig_hash"):
                with open(encrypted_path + ".orig_hash", 'r') as f:
                    stored_hash = f.read().strip()

                current_hash = self.calculate_file_hash(original_path)
                if stored_hash == current_hash:
                    return True, "Encryption verified - hashes match"
                else:
                    return False, f"Hash mismatch: stored={stored_hash[:16]}..., current={current_hash[:16]}..."

            decrypted_path = encrypted_path + ".verify"
            if self.decrypt_file(encrypted_path, decrypted_path):
                decrypted_hash = self.calculate_file_hash(decrypted_path)
                original_hash = self.calculate_file_hash(original_path)

                os.remove(decrypted_path)

                if decrypted_hash == original_hash:
                    return True, "Encryption verified - decrypted content matches original"
                else:
                    return False, "Content mismatch after decryption"

            return False, "Decryption failed"

        except Exception as e:
            return False, str(e)
