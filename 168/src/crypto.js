import crypto from 'crypto';

class ConfigCrypto {
  constructor(options = {}) {
    this.algorithm = options.algorithm || 'aes-256-gcm';
    this.key = this.deriveKey(options.secretKey || process.env.CONFIG_ENCRYPTION_KEY || 'default-secret-key-change-me');
    this.authTagLength = 16;
    this.encryptedPrefix = '__ENC__';
  }

  deriveKey(secret) {
    return crypto.scryptSync(secret, 'config-salt', 32);
  }

  encrypt(value) {
    if (typeof value !== 'string') {
      value = JSON.stringify(value);
    }

    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipheriv(this.algorithm, this.key, iv);
    
    const encrypted = Buffer.concat([
      cipher.update(value, 'utf8'),
      cipher.final()
    ]);
    
    const authTag = cipher.getAuthTag();
    
    const result = {
      iv: iv.toString('base64'),
      value: encrypted.toString('base64'),
      authTag: authTag.toString('base64'),
      algorithm: this.algorithm
    };

    return this.encryptedPrefix + JSON.stringify(result);
  }

  decrypt(encryptedValue) {
    if (!this.isEncrypted(encryptedValue)) {
      return encryptedValue;
    }

    try {
      const data = JSON.parse(encryptedValue.slice(this.encryptedPrefix.length));
      
      const iv = Buffer.from(data.iv, 'base64');
      const encrypted = Buffer.from(data.value, 'base64');
      const authTag = Buffer.from(data.authTag, 'base64');

      const decipher = crypto.createDecipheriv(data.algorithm || this.algorithm, this.key, iv);
      decipher.setAuthTag(authTag);

      const decrypted = Buffer.concat([
        decipher.update(encrypted),
        decipher.final()
      ]);

      const result = decrypted.toString('utf8');
      
      try {
        return JSON.parse(result);
      } catch {
        return result;
      }
    } catch (error) {
      throw new Error(`解密失败: ${error.message}`);
    }
  }

  isEncrypted(value) {
    return typeof value === 'string' && value.startsWith(this.encryptedPrefix);
  }

  encryptObject(obj, paths = []) {
    if (!obj || typeof obj !== 'object') {
      return obj;
    }

    const result = Array.isArray(obj) ? [...obj] : { ...obj };

    const shouldEncrypt = (path) => {
      if (paths.length === 0) return false;
      return paths.some(p => path === p || path.endsWith('.' + p) || path.includes('.' + p + '.'));
    };

    const traverse = (node, currentPath = '') => {
      if (!node || typeof node !== 'object') return;

      for (const [key, value] of Object.entries(node)) {
        const path = currentPath ? `${currentPath}.${key}` : key;

        if (value !== null && typeof value === 'object') {
          traverse(value, path);
        } else if (shouldEncrypt(path)) {
          node[key] = this.encrypt(value);
        }
      }
    };

    traverse(result);
    return result;
  }

  decryptObject(obj) {
    if (!obj || typeof obj !== 'object') {
      return this.isEncrypted(obj) ? this.decrypt(obj) : obj;
    }

    const result = Array.isArray(obj) ? [...obj] : { ...obj };

    const traverse = (node) => {
      if (!node || typeof node !== 'object') return;

      for (const [key, value] of Object.entries(node)) {
        if (this.isEncrypted(value)) {
          node[key] = this.decrypt(value);
        } else if (value !== null && typeof value === 'object') {
          traverse(value);
        }
      }
    };

    traverse(result);
    return result;
  }

  generateKey() {
    return crypto.randomBytes(32).toString('base64');
  }
}

export default ConfigCrypto;
