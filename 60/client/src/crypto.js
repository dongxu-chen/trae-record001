const generateKeyPair = async () => {
  return await crypto.subtle.generateKey(
    {
      name: 'ECDH',
      namedCurve: 'P-256'
    },
    true,
    ['deriveKey']
  );
};

const exportPublicKey = async (publicKey) => {
  const exported = await crypto.subtle.exportKey('raw', publicKey);
  return btoa(String.fromCharCode(...new Uint8Array(exported)));
};

const importPublicKey = async (publicKeyString) => {
  const binaryString = atob(publicKeyString);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  
  if (bytes.length !== 65 && bytes.length !== 33) {
    throw new Error('Invalid public key length');
  }
  
  if (bytes.length === 65 && bytes[0] !== 0x04) {
    throw new Error('Invalid uncompressed public key format');
  }
  
  if (bytes.length === 33 && (bytes[0] !== 0x02 && bytes[0] !== 0x03)) {
    throw new Error('Invalid compressed public key format');
  }
  
  return await crypto.subtle.importKey(
    'raw',
    bytes,
    {
      name: 'ECDH',
      namedCurve: 'P-256'
    },
    true,
    []
  );
};

const deriveSharedKey = async (privateKey, peerPublicKey) => {
  if (!privateKey || !peerPublicKey) {
    throw new Error('Missing keys for derivation');
  }
  
  if (privateKey.algorithm.name !== 'ECDH' || peerPublicKey.algorithm.name !== 'ECDH') {
    throw new Error('Invalid key type for ECDH');
  }
  
  const derived = await crypto.subtle.deriveKey(
    {
      name: 'ECDH',
      public: peerPublicKey
    },
    privateKey,
    {
      name: 'AES-GCM',
      length: 256
    },
    false,
    ['encrypt', 'decrypt']
  );
  
  return derived;
};

const encryptMessage = async (message, sharedKey) => {
  if (!sharedKey) {
    throw new Error('Shared key is required for encryption');
  }
  
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encoded = new TextEncoder().encode(message);
  
  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: iv
    },
    sharedKey,
    encoded
  );
  
  const combined = new Uint8Array(iv.length + encrypted.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(encrypted), iv.length);
  
  return btoa(String.fromCharCode(...combined));
};

const decryptMessage = async (encryptedMessage, sharedKey) => {
  if (!sharedKey) {
    throw new Error('Shared key is required for decryption');
  }
  
  const binaryString = atob(encryptedMessage);
  const combined = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    combined[i] = binaryString.charCodeAt(i);
  }
  
  if (combined.length <= 12) {
    throw new Error('Invalid encrypted message: too short');
  }
  
  const iv = combined.slice(0, 12);
  const encryptedData = combined.slice(12);
  
  const decrypted = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: iv
    },
    sharedKey,
    encryptedData
  );
  
  return new TextDecoder().decode(decrypted);
};

const generateKeyFingerprint = async (publicKeyString) => {
  const encoder = new TextEncoder();
  const data = encoder.encode(publicKeyString);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
};

const verifyKeyExchange = async (publicKeyString, receivedFingerprint) => {
  try {
    const computedFingerprint = await generateKeyFingerprint(publicKeyString);
    return computedFingerprint === receivedFingerprint;
  } catch (error) {
    console.error('Key verification failed:', error);
    return false;
  }
};

const validatePublicKey = async (publicKeyString) => {
  try {
    await importPublicKey(publicKeyString);
    return true;
  } catch (error) {
    console.error('Public key validation failed:', error);
    return false;
  }
};

const generateAnonymousId = () => {
  const array = new Uint32Array(4);
  crypto.getRandomValues(array);
  return Array.from(array, num => num.toString(16).padStart(8, '0')).join('-');
};

const encryptForOffline = async (message, peerPublicKeyString) => {
  const tempKeyPair = await crypto.subtle.generateKey(
    {
      name: 'ECDH',
      namedCurve: 'P-256'
    },
    true,
    ['deriveKey']
  );
  
  const peerPublicKey = await importPublicKey(peerPublicKeyString);
  const tempSharedKey = await crypto.subtle.deriveKey(
    {
      name: 'ECDH',
      public: peerPublicKey
    },
    tempKeyPair.privateKey,
    {
      name: 'AES-GCM',
      length: 256
    },
    false,
    ['encrypt']
  );
  
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encoded = new TextEncoder().encode(message);
  
  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: iv
    },
    tempSharedKey,
    encoded
  );
  
  const tempPublicKeyExported = await exportPublicKey(tempKeyPair.publicKey);
  
  const combined = new Uint8Array(12 + encrypted.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(encrypted), 12);
  
  return {
    ephemeralPublicKey: tempPublicKeyExported,
    encryptedData: btoa(String.fromCharCode(...combined)),
    timestamp: Date.now()
  };
};

const decryptFromOffline = async (offlineMessage, privateKey) => {
  const { ephemeralPublicKey, encryptedData } = offlineMessage;
  
  if (!ephemeralPublicKey || !encryptedData) {
    throw new Error('Invalid offline message format');
  }
  
  const ephemeralKey = await importPublicKey(ephemeralPublicKey);
  
  const tempSharedKey = await crypto.subtle.deriveKey(
    {
      name: 'ECDH',
      public: ephemeralKey
    },
    privateKey,
    {
      name: 'AES-GCM',
      length: 256
    },
    false,
    ['decrypt']
  );
  
  const binaryString = atob(encryptedData);
  const combined = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    combined[i] = binaryString.charCodeAt(i);
  }
  
  if (combined.length <= 12) {
    throw new Error('Invalid encrypted offline message');
  }
  
  const iv = combined.slice(0, 12);
  const encryptedBytes = combined.slice(12);
  
  const decrypted = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: iv
    },
    tempSharedKey,
    encryptedBytes
  );
  
  return new TextDecoder().decode(decrypted);
};

const encryptHistoryMessage = async (message, roomKey) => {
  if (!roomKey) {
    throw new Error('Room key is required for history encryption');
  }
  
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encoded = new TextEncoder().encode(JSON.stringify(message));
  
  const encrypted = await crypto.subtle.encrypt(
    {
      name: 'AES-GCM',
      iv: iv
    },
    roomKey,
    encoded
  );
  
  const combined = new Uint8Array(iv.length + encrypted.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(encrypted), iv.length);
  
  return {
    encrypted: btoa(String.fromCharCode(...combined)),
    timestamp: Date.now()
  };
};

const decryptHistoryMessage = async (encryptedMessage, roomKey) => {
  if (!roomKey) {
    throw new Error('Room key is required for history decryption');
  }
  
  const { encrypted } = encryptedMessage;
  if (!encrypted) {
    throw new Error('Invalid history message format');
  }
  
  const binaryString = atob(encrypted);
  const combined = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    combined[i] = binaryString.charCodeAt(i);
  }
  
  if (combined.length <= 12) {
    throw new Error('Invalid encrypted history message');
  }
  
  const iv = combined.slice(0, 12);
  const encryptedBytes = combined.slice(12);
  
  const decrypted = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: iv
    },
    roomKey,
    encryptedBytes
  );
  
  return JSON.parse(new TextDecoder().decode(decrypted));
};

const deriveRoomKey = async (sharedKeys) => {
  if (!sharedKeys || sharedKeys.length === 0) {
    return null;
  }
  
  const keyMaterials = [];
  for (const sharedKey of sharedKeys) {
    const exported = await crypto.subtle.exportKey('raw', sharedKey);
    keyMaterials.push(new Uint8Array(exported));
  }
  
  const combinedLength = keyMaterials.reduce((sum, k) => sum + k.length, 0);
  const combined = new Uint8Array(combinedLength);
  let offset = 0;
  for (const key of keyMaterials) {
    combined.set(key, offset);
    offset += key.length;
  }
  
  const hash = await crypto.subtle.digest('SHA-256', combined);
  
  return await crypto.subtle.importKey(
    'raw',
    hash,
    {
      name: 'AES-GCM',
      length: 256
    },
    false,
    ['encrypt', 'decrypt']
  );
};

const exportPrivateKey = async (privateKey) => {
  const exported = await crypto.subtle.exportKey('pkcs8', privateKey);
  return btoa(String.fromCharCode(...new Uint8Array(exported)));
};

const importPrivateKey = async (privateKeyString) => {
  const binaryString = atob(privateKeyString);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  
  return await crypto.subtle.importKey(
    'pkcs8',
    bytes,
    {
      name: 'ECDH',
      namedCurve: 'P-256'
    },
    false,
    ['deriveKey']
  );
};

export {
  generateKeyPair,
  exportPublicKey,
  importPublicKey,
  deriveSharedKey,
  encryptMessage,
  decryptMessage,
  generateKeyFingerprint,
  verifyKeyExchange,
  validatePublicKey,
  generateAnonymousId,
  encryptForOffline,
  decryptFromOffline,
  encryptHistoryMessage,
  decryptHistoryMessage,
  deriveRoomKey,
  exportPrivateKey,
  importPrivateKey
};
