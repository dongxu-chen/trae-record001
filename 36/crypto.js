const CryptoManager = {
  DEFAULT_KEY_SIZE: 256,
  KEY_ALGORITHM: 'AES-GCM',
  IV_LENGTH: 12,
  SALT_LENGTH: 16,
  ITERATIONS: 100000,

  async generateKey() {
    const key = await crypto.subtle.generateKey(
      {
        name: this.KEY_ALGORITHM,
        length: this.DEFAULT_KEY_SIZE,
      },
      true,
      ['encrypt', 'decrypt']
    );
    return key;
  },

  async exportKey(key) {
    const exported = await crypto.subtle.exportKey('raw', key);
    return this.arrayBufferToBase64(exported);
  },

  async importKey(keyString) {
    const keyData = this.base64ToArrayBuffer(keyString);
    return crypto.subtle.importKey(
      'raw',
      keyData,
      { name: this.KEY_ALGORITHM },
      true,
      ['encrypt', 'decrypt']
    );
  },

  async deriveKeyFromPassword(password, salt = null) {
    if (!salt) {
      salt = crypto.getRandomValues(new Uint8Array(this.SALT_LENGTH));
    }

    const encoder = new TextEncoder();
    const passwordKey = await crypto.subtle.importKey(
      'raw',
      encoder.encode(password),
      { name: 'PBKDF2' },
      false,
      ['deriveKey']
    );

    const derivedKey = await crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: salt,
        iterations: this.ITERATIONS,
        hash: 'SHA-256',
      },
      passwordKey,
      {
        name: this.KEY_ALGORITHM,
        length: this.DEFAULT_KEY_SIZE,
      },
      true,
      ['encrypt', 'decrypt']
    );

    return {
      key: derivedKey,
      salt: this.arrayBufferToBase64(salt),
    };
  },

  async encrypt(data, key) {
    const iv = crypto.getRandomValues(new Uint8Array(this.IV_LENGTH));
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(JSON.stringify(data));

    const encryptedBuffer = await crypto.subtle.encrypt(
      {
        name: this.KEY_ALGORITHM,
        iv: iv,
      },
      key,
      dataBuffer
    );

    return {
      iv: this.arrayBufferToBase64(iv),
      data: this.arrayBufferToBase64(encryptedBuffer),
    };
  },

  async decrypt(encrypted, key) {
    try {
      const iv = this.base64ToArrayBuffer(encrypted.iv);
      const dataBuffer = this.base64ToArrayBuffer(encrypted.data);

      const decryptedBuffer = await crypto.subtle.decrypt(
        {
          name: this.KEY_ALGORITHM,
          iv: iv,
        },
        key,
        dataBuffer
      );

      const decoder = new TextDecoder();
      return JSON.parse(decoder.decode(decryptedBuffer));
    } catch (error) {
      console.error('[Crypto] 解密失败:', error);
      throw new Error('解密失败，可能是密钥错误');
    }
  },

  async encryptString(text, key) {
    const result = await this.encrypt({ content: text }, key);
    return JSON.stringify(result);
  },

  async decryptString(encryptedString, key) {
    const encrypted = JSON.parse(encryptedString);
    const result = await this.decrypt(encrypted, key);
    return result.content;
  },

  async encryptDiary(diary, key) {
    const fieldsToEncrypt = ['title', 'content'];
    const encryptedDiary = { ...diary };

    for (const field of fieldsToEncrypt) {
      if (diary[field]) {
        const encrypted = await this.encryptString(diary[field], key);
        encryptedDiary[field] = encrypted;
        encryptedDiary[`${field}_encrypted`] = true;
      }
    }

    encryptedDiary.encrypted = true;
    return encryptedDiary;
  },

  async decryptDiary(encryptedDiary, key) {
    if (!encryptedDiary.encrypted) {
      return encryptedDiary;
    }

    const decryptedDiary = { ...encryptedDiary };
    const fieldsToDecrypt = ['title', 'content'];

    for (const field of fieldsToDecrypt) {
      if (encryptedDiary[`${field}_encrypted`] && encryptedDiary[field]) {
        try {
          decryptedDiary[field] = await this.decryptString(
            encryptedDiary[field],
            key
          );
        } catch (error) {
          console.warn(`[Crypto] 字段 ${field} 解密失败，使用加密原文`);
        }
      }
    }

    decryptedDiary.encrypted = false;
    return decryptedDiary;
  },

  async hashPassword(password, salt = null) {
    if (!salt) {
      salt = crypto.getRandomValues(new Uint8Array(this.SALT_LENGTH));
    }

    const encoder = new TextEncoder();
    const passwordBuffer = encoder.encode(password);
    
    const hashBuffer = await crypto.subtle.digest('SHA-256', passwordBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    return {
      hash: hashHex,
      salt: this.arrayBufferToBase64(salt),
    };
  },

  arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  },

  base64ToArrayBuffer(base64) {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  },

  stringToArrayBuffer(str) {
    const encoder = new TextEncoder();
    return encoder.encode(str);
  },

  arrayBufferToString(buffer) {
    const decoder = new TextDecoder();
    return decoder.decode(buffer);
  },

  async generateHash(data) {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(JSON.stringify(data));
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }
};

window.CryptoManager = CryptoManager;
