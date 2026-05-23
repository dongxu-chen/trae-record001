import os
import gzip
import tarfile
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class Compressor:
    def __init__(self, config):
        self.enabled = config.get('enabled', True)
        self.algorithm = config.get('algorithm', 'gzip')
        self.level = config.get('level', 6)

    def compress(self, input_path, output_path):
        if not self.enabled:
            import shutil
            shutil.copy2(input_path, output_path)
            return True, "Copy completed (no compression)"

        if self.algorithm == 'gzip':
            return self._gzip_compress(input_path, output_path)
        elif self.algorithm == 'tar':
            return self._tar_compress(input_path, output_path)
        else:
            return False, f"Unsupported compression algorithm: {self.algorithm}"

    def decompress(self, input_path, output_path):
        if not self.enabled:
            import shutil
            shutil.copy2(input_path, output_path)
            return True, "Copy completed (no decompression)"

        if self.algorithm == 'gzip':
            return self._gzip_decompress(input_path, output_path)
        elif self.algorithm == 'tar':
            return self._tar_decompress(input_path, output_path)
        else:
            return False, f"Unsupported compression algorithm: {self.algorithm}"

    def _gzip_compress(self, input_path, output_path):
        try:
            with open(input_path, 'rb') as f_in:
                with gzip.open(output_path, 'wb', compresslevel=self.level) as f_out:
                    f_out.writelines(f_in)
            return True, "Gzip compression completed"
        except Exception as e:
            return False, str(e)

    def _gzip_decompress(self, input_path, output_path):
        try:
            with gzip.open(input_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            return True, "Gzip decompression completed"
        except Exception as e:
            return False, str(e)

    def _tar_compress(self, input_path, output_path):
        try:
            with tarfile.open(output_path, 'w:gz') as tar:
                tar.add(input_path, arcname=os.path.basename(input_path))
            return True, "Tar compression completed"
        except Exception as e:
            return False, str(e)

    def _tar_decompress(self, input_path, output_path):
        try:
            with tarfile.open(input_path, 'r:gz') as tar:
                tar.extractall(path=os.path.dirname(output_path))
            return True, "Tar decompression completed"
        except Exception as e:
            return False, str(e)


class Encryptor:
    def __init__(self, config):
        self.enabled = config.get('enabled', True)
        self.algorithm = config.get('algorithm', 'AES-256-CBC')
        self.key = config.get('key', '')
        
        if self.enabled and len(self.key) < 32:
            raise ValueError("Encryption key must be at least 32 characters")
        
        self.fernet = self._init_fernet() if self.enabled else None

    def _init_fernet(self):
        salt = b'static_salt_for_backup_tool'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key_bytes = self.key.encode('utf-8')[:32]
        derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        return Fernet(derived_key)

    def encrypt(self, input_path, output_path):
        if not self.enabled:
            import shutil
            shutil.copy2(input_path, output_path)
            return True, "Copy completed (no encryption)"

        try:
            with open(input_path, 'rb') as f:
                data = f.read()
            
            encrypted_data = self.fernet.encrypt(data)
            
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            return True, "Encryption completed"
        except Exception as e:
            return False, str(e)

    def decrypt(self, input_path, output_path):
        if not self.enabled:
            import shutil
            shutil.copy2(input_path, output_path)
            return True, "Copy completed (no decryption)"

        try:
            with open(input_path, 'rb') as f:
                encrypted_data = f.read()
            
            data = self.fernet.decrypt(encrypted_data)
            
            with open(output_path, 'wb') as f:
                f.write(data)
            
            return True, "Decryption completed"
        except Exception as e:
            return False, str(e)

    def encrypt_bytes(self, data):
        if not self.enabled:
            return data
        return self.fernet.encrypt(data)

    def decrypt_bytes(self, encrypted_data):
        if not self.enabled:
            return encrypted_data
        return self.fernet.decrypt(encrypted_data)
