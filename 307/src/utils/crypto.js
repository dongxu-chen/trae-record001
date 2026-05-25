const ALGORITHM = 'AES-GCM';
const KEY_LENGTH = 256;
const ITERATIONS = 1000000;
const SALT_LENGTH = 16;
const IV_LENGTH = 12;
const TAG_LENGTH = 128;

export class CryptoService {
  constructor() {
    this.masterKey = null;
    this.encryptionKey = null;
  }

  async init(masterPassword, salt = null) {
    if (!salt) {
      salt = this.generateSalt();
    }
    
    this.masterKey = await this.deriveMasterKey(masterPassword, salt);
    this.encryptionKey = await this.deriveEncryptionKey(this.masterKey);
    
    return { salt };
  }

  isInitialized() {
    return this.masterKey !== null && this.encryptionKey !== null;
  }

  generateSalt() {
    const saltBuffer = crypto.getRandomValues(new Uint8Array(SALT_LENGTH));
    return this.bufferToBase64(saltBuffer);
  }

  generateIV() {
    return crypto.getRandomValues(new Uint8Array(IV_LENGTH));
  }

  async deriveMasterKey(password, salt) {
    const passwordBuffer = this.stringToBuffer(password);
    const saltBuffer = this.base64ToBuffer(salt);

    const keyMaterial = await crypto.subtle.importKey(
      'raw',
      passwordBuffer,
      { name: 'PBKDF2' },
      false,
      ['deriveKey']
    );

    return crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: saltBuffer,
        iterations: ITERATIONS,
        hash: 'SHA-256'
      },
      keyMaterial,
      { name: ALGORITHM, length: KEY_LENGTH },
      false,
      ['deriveKey']
    );
  }

  async deriveEncryptionKey(masterKey) {
    const info = this.stringToBuffer('encryption-key');
    
    return crypto.subtle.deriveKey(
      {
        name: 'HKDF',
        hash: 'SHA-256',
        salt: new Uint8Array(32),
        info: info
      },
      masterKey,
      { name: ALGORITHM, length: KEY_LENGTH },
      false,
      ['encrypt', 'decrypt']
    );
  }

  async encrypt(data) {
    if (!this.encryptionKey) {
      throw new Error('Crypto service not initialized');
    }

    const iv = this.generateIV();
    const dataBuffer = this.stringToBuffer(JSON.stringify(data));

    const encryptedBuffer = await crypto.subtle.encrypt(
      {
        name: ALGORITHM,
        iv: iv,
        tagLength: TAG_LENGTH
      },
      this.encryptionKey,
      dataBuffer
    );

    const combined = new Uint8Array(iv.length + encryptedBuffer.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(encryptedBuffer), iv.length);

    return this.bufferToBase64(combined);
  }

  async decrypt(encryptedData) {
    if (!this.encryptionKey) {
      throw new Error('Crypto service not initialized');
    }

    const combined = this.base64ToBuffer(encryptedData);
    const iv = combined.slice(0, IV_LENGTH);
    const ciphertext = combined.slice(IV_LENGTH);

    try {
      const decryptedBuffer = await crypto.subtle.decrypt(
        {
          name: ALGORITHM,
          iv: iv,
          tagLength: TAG_LENGTH
        },
        this.encryptionKey,
        ciphertext
      );

      const decryptedString = this.bufferToString(decryptedBuffer);
      return JSON.parse(decryptedString);
    } catch (error) {
      throw new Error('Decryption failed. Wrong master password or corrupted data.');
    }
  }

  async hashPassword(password) {
    const buffer = this.stringToBuffer(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
    return this.bufferToBase64(hashBuffer);
  }

  async generateShareKey() {
    const keyPair = await crypto.subtle.generateKey(
      {
        name: 'RSA-OAEP',
        modulusLength: 2048,
        publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
        hash: 'SHA-256'
      },
      true,
      ['encrypt', 'decrypt']
    );

    const publicKey = await crypto.subtle.exportKey('jwk', keyPair.publicKey);
    const privateKey = await crypto.subtle.exportKey('jwk', keyPair.privateKey);

    return { publicKey, privateKey, keyPair };
  }

  async encryptWithPublicKey(data, publicKeyJwk) {
    const publicKey = await crypto.subtle.importKey(
      'jwk',
      publicKeyJwk,
      { name: 'RSA-OAEP', hash: 'SHA-256' },
      false,
      ['encrypt']
    );

    const dataBuffer = this.stringToBuffer(JSON.stringify(data));
    const encryptedBuffer = await crypto.subtle.encrypt(
      { name: 'RSA-OAEP' },
      publicKey,
      dataBuffer
    );

    return this.bufferToBase64(encryptedBuffer);
  }

  async decryptWithPrivateKey(encryptedData, privateKeyJwk) {
    const privateKey = await crypto.subtle.importKey(
      'jwk',
      privateKeyJwk,
      { name: 'RSA-OAEP', hash: 'SHA-256' },
      false,
      ['decrypt']
    );

    const encryptedBuffer = this.base64ToBuffer(encryptedData);
    const decryptedBuffer = await crypto.subtle.decrypt(
      { name: 'RSA-OAEP' },
      privateKey,
      encryptedBuffer
    );

    const decryptedString = this.bufferToString(decryptedBuffer);
    return JSON.parse(decryptedString);
  }

  async generateSyncKey() {
    const key = await crypto.subtle.generateKey(
      { name: ALGORITHM, length: KEY_LENGTH },
      true,
      ['encrypt', 'decrypt']
    );
    
    const exportedKey = await crypto.subtle.exportKey('raw', key);
    return this.bufferToBase64(exportedKey);
  }

  async importSyncKey(syncKeyBase64) {
    const keyBuffer = this.base64ToBuffer(syncKeyBase64);
    return crypto.subtle.importKey(
      'raw',
      keyBuffer,
      { name: ALGORITHM, length: KEY_LENGTH },
      true,
      ['encrypt', 'decrypt']
    );
  }

  async encryptForSync(data, syncKey) {
    const iv = this.generateIV();
    const dataBuffer = this.stringToBuffer(JSON.stringify(data));

    const encryptedBuffer = await crypto.subtle.encrypt(
      {
        name: ALGORITHM,
        iv: iv,
        tagLength: TAG_LENGTH
      },
      syncKey,
      dataBuffer
    );

    const combined = new Uint8Array(iv.length + encryptedBuffer.byteLength);
    combined.set(iv, 0);
    combined.set(new Uint8Array(encryptedBuffer), iv.length);

    return this.bufferToBase64(combined);
  }

  async decryptFromSync(encryptedData, syncKey) {
    const combined = this.base64ToBuffer(encryptedData);
    const iv = combined.slice(0, IV_LENGTH);
    const ciphertext = combined.slice(IV_LENGTH);

    const decryptedBuffer = await crypto.subtle.decrypt(
      {
        name: ALGORITHM,
        iv: iv,
        tagLength: TAG_LENGTH
      },
      syncKey,
      ciphertext
    );

    const decryptedString = this.bufferToString(decryptedBuffer);
    return JSON.parse(decryptedString);
  }

  stringToBuffer(str) {
    return new TextEncoder().encode(str);
  }

  bufferToString(buffer) {
    return new TextDecoder().decode(buffer);
  }

  bufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  base64ToBuffer(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
  }

  clearKeys() {
    this.masterKey = null;
    this.encryptionKey = null;
  }
}

export const cryptoService = new CryptoService();
