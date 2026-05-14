self.onmessage = async (event) => {
  const { type, payload } = event.data;
  
  try {
    switch (type) {
      case 'decryptBatch':
        await handleDecryptBatch(payload);
        break;
      case 'decryptOffline':
        await handleDecryptOffline(payload);
        break;
      case 'decryptHistory':
        await handleDecryptHistory(payload);
        break;
      case 'verifyKeys':
        await handleVerifyKeys(payload);
        break;
      default:
        self.postMessage({
          type: 'error',
          error: 'Unknown message type: ' + type
        });
    }
  } catch (error) {
    self.postMessage({
      type: 'error',
      error: error.message
    });
  }
};

const handleDecryptBatch = async (payload) => {
  const { messages, sharedKey, total } = payload;
  const results = [];
  
  for (let i = 0; i < messages.length; i++) {
    try {
      const decrypted = await decryptSingle(messages[i].encrypted, sharedKey);
      results.push({
        index: i,
        success: true,
        data: JSON.parse(decrypted),
        original: messages[i]
      });
    } catch (error) {
      results.push({
        index: i,
        success: false,
        error: error.message,
        original: messages[i]
      });
    }
    
    if ((i + 1) % 10 === 0 || i === messages.length - 1) {
      self.postMessage({
        type: 'progress',
        current: i + 1,
        total: total
      });
    }
  }
  
  self.postMessage({
    type: 'batchComplete',
    results
  });
};

const handleDecryptOffline = async (payload) => {
  const { messages, privateKeyString } = payload;
  const privateKey = await importPrivateKeyFromString(privateKeyString);
  const results = [];
  
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    try {
      const decrypted = await decryptFromOfflineWorker(msg, privateKey);
      results.push({
        index: i,
        success: true,
        data: JSON.parse(decrypted),
        original: msg
      });
    } catch (error) {
      results.push({
        index: i,
        success: false,
        error: error.message,
        original: msg
      });
    }
    
    self.postMessage({
      type: 'progress',
      current: i + 1,
      total: messages.length
    });
  }
  
  self.postMessage({
    type: 'offlineComplete',
    results
  });
};

const handleDecryptHistory = async (payload) => {
  const { messages, roomKeyMaterial } = payload;
  const roomKey = await importKeyFromMaterial(roomKeyMaterial);
  const results = [];
  
  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    try {
      const decrypted = await decryptHistoryWorker(msg, roomKey);
      results.push({
        index: i,
        success: true,
        data: decrypted,
        original: msg
      });
    } catch (error) {
      results.push({
        index: i,
        success: false,
        error: error.message,
        original: msg
      });
    }
    
    if ((i + 1) % 5 === 0 || i === messages.length - 1) {
      self.postMessage({
        type: 'progress',
        current: i + 1,
        total: messages.length
      });
    }
  }
  
  self.postMessage({
    type: 'historyComplete',
    results
  });
};

const handleVerifyKeys = async (payload) => {
  const { keys } = payload;
  const results = [];
  
  for (const key of keys) {
    const isValid = await verifyKeyExchangeWorker(key.publicKey, key.fingerprint);
    results.push({
      ...key,
      isValid
    });
  }
  
  self.postMessage({
    type: 'verifyComplete',
    results
  });
};

const decryptSingle = async (encryptedMessage, sharedKeyMaterial) => {
  const sharedKey = await importKeyFromMaterial(sharedKeyMaterial);
  
  const binaryString = atob(encryptedMessage);
  const combined = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    combined[i] = binaryString.charCodeAt(i);
  }
  
  if (combined.length <= 12) {
    throw new Error('Invalid encrypted message');
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

const decryptFromOfflineWorker = async (offlineMessage, privateKey) => {
  const { ephemeralPublicKey, encryptedData } = offlineMessage;
  
  if (!ephemeralPublicKey || !encryptedData) {
    throw new Error('Invalid offline message format');
  }
  
  const ephemeralKey = await importPublicKeyFromString(ephemeralPublicKey);
  
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

const decryptHistoryWorker = async (encryptedMessage, roomKey) => {
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

const verifyKeyExchangeWorker = async (publicKeyString, receivedFingerprint) => {
  try {
    const computedFingerprint = await generateFingerprint(publicKeyString);
    return computedFingerprint === receivedFingerprint;
  } catch (error) {
    return false;
  }
};

const generateFingerprint = async (publicKeyString) => {
  const encoder = new TextEncoder();
  const data = encoder.encode(publicKeyString);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
};

const importKeyFromMaterial = async (material) => {
  const bytes = new Uint8Array(material);
  return await crypto.subtle.importKey(
    'raw',
    bytes,
    {
      name: 'AES-GCM',
      length: 256
    },
    false,
    ['decrypt']
  );
};

const importPublicKeyFromString = async (publicKeyString) => {
  const binaryString = atob(publicKeyString);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
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

const importPrivateKeyFromString = async (privateKeyString) => {
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
