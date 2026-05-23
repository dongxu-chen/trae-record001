import os
import io
import logging
import hashlib
import gnupg
from typing import Optional, Tuple
from pathlib import Path


class Encryptor:
    def __init__(
        self,
        gpg_home: str = None,
        passphrase_env: str = "BACKUP_ENCRYPTION_KEY",
        logger: Optional[logging.Logger] = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.passphrase = os.environ.get(passphrase_env)
        
        if not self.passphrase:
            self.logger.warning(f"环境变量 {passphrase_env} 未设置，加密功能将不可用")
        
        gpg_home = gpg_home or os.path.join(str(Path.home()), ".gnupg")
        self.gpg = gnupg.GPG(gnupghome=gpg_home)

    def is_available(self) -> bool:
        return self.passphrase is not None

    def encrypt_file(self, input_file: str, output_file: str = None) -> str:
        if not self.is_available():
            raise ValueError("加密密钥未设置，请设置 BACKUP_ENCRYPTION_KEY 环境变量")

        if output_file is None:
            output_file = input_file + ".gpg"

        self.logger.info(f"开始加密文件: {input_file} -> {output_file}")

        with open(input_file, 'rb') as f:
            encrypted_data = self.gpg.encrypt(
                f.read(),
                recipients=None,
                symmetric=True,
                passphrase=self.passphrase,
                armor=False
            )

            if not encrypted_data.ok:
                raise RuntimeError(f"加密失败: {encrypted_data.stderr}")

            with open(output_file, 'wb') as out_f:
                out_f.write(encrypted_data.data)

        original_size = os.path.getsize(input_file)
        encrypted_size = os.path.getsize(output_file)
        self.logger.info(f"加密完成: 原始大小 {original_size/(1024*1024):.2f} MB -> 加密后 {encrypted_size/(1024*1024):.2f} MB")

        return output_file

    def encrypt_stream(self, input_stream: io.BytesIO) -> io.BytesIO:
        if not self.is_available():
            raise ValueError("加密密钥未设置，请设置 BACKUP_ENCRYPTION_KEY 环境变量")

        self.logger.info("开始流式加密")
        input_stream.seek(0)
        
        encrypted_data = self.gpg.encrypt(
            input_stream.read(),
            recipients=None,
            symmetric=True,
            passphrase=self.passphrase,
            armor=False
        )

        if not encrypted_data.ok:
            raise RuntimeError(f"加密失败: {encrypted_data.stderr}")

        output_stream = io.BytesIO(encrypted_data.data)
        output_stream.seek(0)
        
        self.logger.info(f"流式加密完成，加密后大小: {len(encrypted_data.data)/(1024*1024):.2f} MB")
        return output_stream

    def decrypt_file(self, input_file: str, output_file: str = None) -> str:
        if not self.is_available():
            raise ValueError("加密密钥未设置，请设置 BACKUP_ENCRYPTION_KEY 环境变量")

        if output_file is None:
            if input_file.endswith('.gpg'):
                output_file = input_file[:-4]
            else:
                output_file = input_file + ".decrypted"

        self.logger.info(f"开始解密文件: {input_file} -> {output_file}")

        with open(input_file, 'rb') as f:
            decrypted_data = self.gpg.decrypt(
                f.read(),
                passphrase=self.passphrase
            )

            if not decrypted_data.ok:
                raise RuntimeError(f"解密失败: {decrypted_data.stderr}")

            with open(output_file, 'wb') as out_f:
                out_f.write(decrypted_data.data)

        self.logger.info(f"解密完成: {output_file}")
        return output_file

    def calculate_md5(self, file_path: str) -> str:
        self.logger.debug(f"计算MD5: {file_path}")
        md5_hash = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5_hash.update(chunk)
        
        md5_hex = md5_hash.hexdigest()
        self.logger.debug(f"MD5计算完成: {md5_hex}")
        return md5_hex

    def calculate_stream_md5(self, stream: io.BytesIO) -> Tuple[str, int]:
        stream.seek(0)
        md5_hash = hashlib.md5()
        size = 0
        
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            md5_hash.update(chunk)
            size += len(chunk)
        
        md5_hex = md5_hash.hexdigest()
        stream.seek(0)
        return md5_hex, size
