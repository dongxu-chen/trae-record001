export async function generateKeyPair() {
  const keyPair = await window.crypto.subtle.generateKey(
    {
      name: 'RSASSA-PKCS1-v1_5',
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: { name: 'SHA-256' },
    },
    true,
    ['sign', 'verify']
  );
  
  const publicKey = await window.crypto.subtle.exportKey('jwk', keyPair.publicKey);
  const privateKey = await window.crypto.subtle.exportKey('jwk', keyPair.privateKey);
  
  return { publicKey, privateKey };
}

export async function signData(data, privateKeyJwk) {
  const privateKey = await window.crypto.subtle.importKey(
    'jwk',
    privateKeyJwk,
    {
      name: 'RSASSA-PKCS1-v1_5',
      hash: { name: 'SHA-256' },
    },
    false,
    ['sign']
  );
  
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(typeof data === 'string' ? data : JSON.stringify(data));
  
  const signature = await window.crypto.subtle.sign(
    'RSASSA-PKCS1-v1_5',
    privateKey,
    dataBuffer
  );
  
  return arrayBufferToBase64(signature);
}

export async function verifySignature(data, signature, publicKeyJwk) {
  try {
    const publicKey = await window.crypto.subtle.importKey(
      'jwk',
      publicKeyJwk,
      {
        name: 'RSASSA-PKCS1-v1_5',
        hash: { name: 'SHA-256' },
      },
      false,
      ['verify']
    );
    
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(typeof data === 'string' ? data : JSON.stringify(data));
    const signatureBuffer = base64ToArrayBuffer(signature);
    
    const isValid = await window.crypto.subtle.verify(
      'RSASSA-PKCS1-v1_5',
      publicKey,
      signatureBuffer,
      dataBuffer
    );
    
    return isValid;
  } catch (error) {
    console.error('验证签名失败:', error);
    return false;
  }
}

export async function generateHash(data) {
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(typeof data === 'string' ? data : JSON.stringify(data));
  
  const hashBuffer = await window.crypto.subtle.digest('SHA-256', dataBuffer);
  return arrayBufferToBase64(hashBuffer);
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

function base64ToArrayBuffer(base64) {
  const binaryString = window.atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

export function saveKeyPair(keyPair, name = 'default') {
  localStorage.setItem(`signature_key_${name}_public`, JSON.stringify(keyPair.publicKey));
  localStorage.setItem(`signature_key_${name}_private`, JSON.stringify(keyPair.privateKey));
}

export function loadKeyPair(name = 'default') {
  const publicKey = localStorage.getItem(`signature_key_${name}_public`);
  const privateKey = localStorage.getItem(`signature_key_${name}_private`);
  
  if (publicKey && privateKey) {
    return {
      publicKey: JSON.parse(publicKey),
      privateKey: JSON.parse(privateKey)
    };
  }
  return null;
}

export function createSignatureMetadata(signerName, reason = '') {
  return {
    signerName,
    reason,
    timestamp: new Date().toISOString(),
    location: navigator.language
  };
}

export async function signPDFDocument(pdfData, signerName, reason = '', keyPair) {
  const metadata = createSignatureMetadata(signerName, reason);
  const hash = await generateHash(pdfData);
  const signature = await signData(hash + JSON.stringify(metadata), keyPair.privateKey);
  
  return {
    signature,
    metadata,
    hash,
    publicKey: keyPair.publicKey
  };
}

export async function verifyPDFSignature(pdfData, signatureInfo) {
  const hash = await generateHash(pdfData);
  
  if (hash !== signatureInfo.hash) {
    return {
      valid: false,
      message: '文档内容已被篡改',
      integrity: false
    };
  }
  
  const isValid = await verifySignature(
    hash + JSON.stringify(signatureInfo.metadata),
    signatureInfo.signature,
    signatureInfo.publicKey
  );
  
  return {
    valid: isValid,
    message: isValid ? '签名有效，文档完整' : '签名无效',
    integrity: hash === signatureInfo.hash
  };
}
