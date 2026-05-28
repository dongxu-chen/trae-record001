const SESSION_KEY = 'signaturePad_sessionId';
const KEY_SALT = 'signature_pad_salt_v1';

const generateSessionId = (): string => {
  const existing = sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;

  const sessionId = crypto.randomUUID();
  sessionStorage.setItem(SESSION_KEY, sessionId);
  return sessionId;
};

const deriveKeyFromSession = async (sessionId: string): Promise<CryptoKey> => {
  const encoder = new TextEncoder();
  const keyMaterial = encoder.encode(sessionId + KEY_SALT);

  const importedKey = await crypto.subtle.importKey(
    'raw',
    keyMaterial,
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );

  const salt = encoder.encode(KEY_SALT);

  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt,
      iterations: 100000,
      hash: 'SHA-256',
    },
    importedKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  );
};

export const encryptData = async (data: unknown): Promise<string> => {
  try {
    const sessionId = generateSessionId();
    const key = await deriveKeyFromSession(sessionId);

    const encoder = new TextEncoder();
    const dataStr = JSON.stringify(data);
    const dataBuffer = encoder.encode(dataStr);

    const iv = crypto.getRandomValues(new Uint8Array(12));

    const encryptedBuffer = await crypto.subtle.encrypt(
      {
        name: 'AES-GCM',
        iv,
      },
      key,
      dataBuffer
    );

    const combinedBuffer = new Uint8Array(iv.length + encryptedBuffer.byteLength);
    combinedBuffer.set(iv, 0);
    combinedBuffer.set(new Uint8Array(encryptedBuffer), iv.length);

    const binaryStr = Array.from(combinedBuffer)
      .map((byte) => String.fromCharCode(byte))
      .join('');

    return btoa(binaryStr);
  } catch (error) {
    console.error('Encryption failed:', error);
    throw new Error('Failed to encrypt data');
  }
};

export const decryptData = async <T>(encryptedStr: string): Promise<T> => {
  try {
    const sessionId = generateSessionId();
    const key = await deriveKeyFromSession(sessionId);

    const binaryStr = atob(encryptedStr);
    const combinedBuffer = new Uint8Array(
      Array.from(binaryStr).map((char) => char.charCodeAt(0))
    );

    const iv = combinedBuffer.slice(0, 12);
    const encryptedBuffer = combinedBuffer.slice(12);

    const decryptedBuffer = await crypto.subtle.decrypt(
      {
        name: 'AES-GCM',
        iv,
      },
      key,
      encryptedBuffer
    );

    const decoder = new TextDecoder();
    const decryptedStr = decoder.decode(decryptedBuffer);

    return JSON.parse(decryptedStr) as T;
  } catch (error) {
    console.error('Decryption failed:', error);
    throw new Error('Failed to decrypt data');
  }
};

export const isEncryptionSupported = (): boolean => {
  return (
    typeof crypto !== 'undefined' &&
    typeof crypto.subtle !== 'undefined' &&
    typeof crypto.randomUUID !== 'undefined'
  );
};

export const getSessionId = (): string => {
  return generateSessionId();
};

export const clearSession = (): void => {
  sessionStorage.removeItem(SESSION_KEY);
};

export const setEncryptedStorage = async (key: string, data: unknown): Promise<void> => {
  try {
    const encrypted = await encryptData(data);
    localStorage.setItem(key, encrypted);
  } catch (error) {
    console.error('Failed to save encrypted data:', error);
    throw error;
  }
};

export const getEncryptedStorage = async <T>(key: string): Promise<T | null> => {
  try {
    const encrypted = localStorage.getItem(key);
    if (!encrypted) return null;
    return await decryptData<T>(encrypted);
  } catch (error) {
    console.error('Failed to load encrypted data:', error);
    return null;
  }
};

export const removeEncryptedStorage = (key: string): void => {
  localStorage.removeItem(key);
};
