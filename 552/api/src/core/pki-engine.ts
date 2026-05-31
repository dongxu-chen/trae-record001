import * as pkijs from 'pkijs';
import * as asn1js from 'asn1js';
import { CertificateInfo } from '../../../shared';

const OID_KEY_USAGE = '2.5.29.15';
const OID_BASIC_CONSTRAINTS = '2.5.29.19';
const OID_SIGNING_TIME = '1.2.840.113549.1.9.5';
const OID_MESSAGE_DIGEST = '1.2.840.113549.1.9.4';
const OID_TIMESTAMP_TOKEN = '1.2.840.113549.1.9.16.1.4';
const OID_SIGNED_DATA = '1.2.840.113549.1.7.2';

function pemToBuffer(pem: string): ArrayBuffer {
  const base64 = pem
    .replace(/-----BEGIN [A-Z0-9 ]+-----/g, '')
    .replace(/-----END [A-Z0-9 ]+-----/g, '')
    .replace(/\s+/g, '');
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

function bufferToHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join(':')
    .toUpperCase();
}

function parsePEMOrDER(data: string | ArrayBuffer): ArrayBuffer {
  if (typeof data === 'string') {
    if (data.includes('-----BEGIN')) {
      return pemToBuffer(data);
    }
    const binaryString = atob(data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }
  return data;
}

function getNameString(name: pkijs.RelativeDistinguishedNames): string {
  const parts: string[] = [];
  const types: Record<string, string> = {
    '2.5.4.6': 'C',
    '2.5.4.10': 'O',
    '2.5.4.11': 'OU',
    '2.5.4.3': 'CN',
    '2.5.4.7': 'L',
    '2.5.4.8': 'ST',
    '2.5.4.12': 'T',
    '2.5.4.42': 'GN',
    '2.5.4.43': 'I',
    '2.5.4.4': 'SN',
    '1.2.840.113549.1.9.1': 'E',
    '0.9.2342.19200300.100.1.25': 'DC',
    '0.9.2342.19200300.100.1.1': 'UID',
  };
  
  for (const rdn of name.typesAndValues) {
    const type = types[rdn.type] || rdn.type;
    const value = rdn.value.getValue();
    parts.push(`${type}=${value}`);
  }
  
  return parts.join(', ');
}

function getKeyUsage(extValue: asn1js.BitString): string[] {
  const usages: string[] = [];
  const flags = [
    'digitalSignature',
    'nonRepudiation',
    'keyEncipherment',
    'dataEncipherment',
    'keyAgreement',
    'keyCertSign',
    'cRLSign',
    'encipherOnly',
    'decipherOnly',
  ];
  
  const valueView = extValue.valueBlock.valueHexView;
  const unusedBits = extValue.valueBlock.unusedBits;
  
  for (let i = 0; i < flags.length; i++) {
    const byteIndex = Math.floor(i / 8);
    const bitIndex = 7 - (i % 8);
    
    if (byteIndex < valueView.length) {
      const byte = valueView[byteIndex];
      const bitMask = 1 << bitIndex;
      
      if (i >= flags.length - unusedBits) {
        continue;
      }
      
      if ((byte & bitMask) !== 0) {
        usages.push(flags[i]);
      }
    }
  }
  
  return usages;
}

function getAlgorithmName(oid: string): string {
  const algorithms: Record<string, string> = {
    '1.2.840.113549.1.1.1': 'RSA',
    '1.2.840.113549.1.1.2': 'MD2withRSA',
    '1.2.840.113549.1.1.3': 'MD4withRSA',
    '1.2.840.113549.1.1.4': 'MD5withRSA',
    '1.2.840.113549.1.1.5': 'SHA1withRSA',
    '1.2.840.113549.1.1.11': 'SHA256withRSA',
    '1.2.840.113549.1.1.12': 'SHA384withRSA',
    '1.2.840.113549.1.1.13': 'SHA512withRSA',
    '1.2.840.113549.1.1.14': 'SHA224withRSA',
    '1.2.840.10045.2.1': 'EC',
    '1.2.840.10045.4.1': 'SHA1withECDSA',
    '1.2.840.10045.4.3.2': 'SHA256withECDSA',
    '1.2.840.10045.4.3.3': 'SHA384withECDSA',
    '1.2.840.10045.4.3.4': 'SHA512withECDSA',
    '1.2.840.10045.4.3.1': 'SHA224withECDSA',
    '1.3.14.3.2.29': 'SHA1withRSA',
    '1.3.14.3.2.26': 'SHA1',
    '2.16.840.1.101.3.4.2.1': 'SHA256',
    '2.16.840.1.101.3.4.2.2': 'SHA384',
    '2.16.840.1.101.3.4.2.3': 'SHA512',
    '2.16.840.1.101.3.4.2.4': 'SHA224',
    '1.2.840.113549.2.2': 'MD2',
    '1.2.840.113549.2.4': 'MD4',
    '1.2.840.113549.2.5': 'MD5',
  };
  return algorithms[oid] || oid;
}

async function getFingerprint(cert: pkijs.Certificate): Promise<string> {
  const tbs = cert.toSchema().toBER();
  const hash = await crypto.subtle.digest('SHA-256', tbs);
  return bufferToHex(hash);
}

export function parseCertificate(data: string | ArrayBuffer): pkijs.Certificate {
  const buffer = parsePEMOrDER(data);
  const asn1 = asn1js.fromBER(buffer);
  if (asn1.offset === -1) {
    throw new Error('Failed to parse certificate ASN.1 data');
  }
  return new pkijs.Certificate({ schema: asn1.result });
}

export async function extractCertificateInfo(
  cert: pkijs.Certificate,
  pem?: string
): Promise<CertificateInfo> {
  const subject = getNameString(cert.subject);
  const issuer = getNameString(cert.issuer);
  
  const serialNumberBuffer = cert.serialNumber.valueBlock.valueHexView.buffer.slice(
    cert.serialNumber.valueBlock.valueHexView.byteOffset,
    cert.serialNumber.valueBlock.valueHexView.byteOffset + cert.serialNumber.valueBlock.valueHexView.byteLength
  );
  const serialNumber = bufferToHex(serialNumberBuffer);
  
  const validFrom = cert.notBefore.value.toISOString();
  const validTo = cert.notAfter.value.toISOString();
  
  const fingerprint = await getFingerprint(cert);
  const signatureAlgorithm = getAlgorithmName(cert.signature.algorithmId);
  
  let keyUsage: string[] = [];
  let isCA = false;
  const isSelfSigned = subject === issuer;
  
  if (cert.extensions) {
    for (const ext of cert.extensions) {
      if (ext.extnID === OID_KEY_USAGE && ext.parsedValue) {
        const keyUsageExt = ext.parsedValue as asn1js.BitString;
        keyUsage = getKeyUsage(keyUsageExt);
      }
      if (ext.extnID === OID_BASIC_CONSTRAINTS && ext.parsedValue) {
        const basicConstraints = ext.parsedValue as pkijs.BasicConstraints;
        isCA = basicConstraints.cA || false;
      }
    }
  }
  
  return {
    subject,
    issuer,
    serialNumber,
    validFrom,
    validTo,
    fingerprint,
    signatureAlgorithm,
    keyUsage,
    isCA,
    isSelfSigned,
    isTrustedRoot: isCA && isSelfSigned,
    pem,
  };
}

export async function verifyCertificateSignature(
  cert: pkijs.Certificate,
  issuerCert?: pkijs.Certificate
): Promise<boolean> {
  try {
    const cryptoEngine = pkijs.getCrypto();
    if (!cryptoEngine) {
      throw new Error('No crypto engine available');
    }
    
    const signerCert = issuerCert || cert;
    const publicKeyInfo = signerCert.subjectPublicKeyInfo;
    
    const hashAlgorithm = getAlgorithmName(cert.signature.algorithmId);
    let hashName = 'SHA-256';
    if (hashAlgorithm.includes('SHA1')) hashName = 'SHA-1';
    else if (hashAlgorithm.includes('SHA256')) hashName = 'SHA-256';
    else if (hashAlgorithm.includes('SHA384')) hashName = 'SHA-384';
    else if (hashAlgorithm.includes('SHA512')) hashName = 'SHA-512';
    else if (hashAlgorithm.includes('SHA224')) hashName = 'SHA-224';
    
    const algorithm = {
      name: 'RSASSA-PKCS1-v1_5',
      hash: { name: hashName },
    };
    
    const publicKey = await cryptoEngine.importKey(
      'spki',
      publicKeyInfo.subjectPublicKey.valueBlock.valueHexView,
      algorithm,
      false,
      ['verify']
    );
    
    const tbs = cert.encodeTBS().toBER();
    const signature = cert.signatureValue.valueBlock.valueHexView;
    
    return await cryptoEngine.verify(
      algorithm,
      publicKey,
      signature,
      tbs
    );
  } catch {
    return false;
  }
}

export function checkCertificateValidity(cert: pkijs.Certificate): {
  isValid: boolean;
  daysLeft: number;
  isExpired: boolean;
  isNotYetValid: boolean;
} {
  const now = new Date();
  const notBefore = cert.notBefore.value;
  const notAfter = cert.notAfter.value;
  
  const isNotYetValid = now < notBefore;
  const isExpired = now > notAfter;
  const isValid = !isNotYetValid && !isExpired;
  
  const daysLeft = Math.ceil((notAfter.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  
  return {
    isValid,
    daysLeft,
    isExpired,
    isNotYetValid,
  };
}

export function parseCMS(data: ArrayBuffer): pkijs.SignedData {
  const asn1 = asn1js.fromBER(data);
  if (asn1.offset === -1) {
    throw new Error('Failed to parse CMS ASN.1 data');
  }
  
  const cmsContent = new pkijs.ContentInfo({ schema: asn1.result });
  if (cmsContent.contentType !== OID_SIGNED_DATA) {
    throw new Error('Not a signed data CMS content');
  }
  
  return new pkijs.SignedData({ schema: cmsContent.content });
}

export interface SignerInfoResult {
  signerCertificate?: CertificateInfo;
  signatureAlgorithm: string;
  signingTime?: string;
  messageDigest?: string;
  signature: Uint8Array;
  certificateChain: CertificateInfo[];
}

export async function extractSignerInfo(
  signedData: pkijs.SignedData
): Promise<SignerInfoResult[]> {
  const results: SignerInfoResult[] = [];
  const certs: CertificateInfo[] = [];
  
  if (signedData.certificates) {
    for (const cert of signedData.certificates) {
      if (cert instanceof pkijs.Certificate) {
        const info = await extractCertificateInfo(cert);
        certs.push(info);
      }
    }
  }
  
  for (const signer of signedData.signerInfos) {
    let signingTime: string | undefined;
    let messageDigest: string | undefined;
    
    if (signer.signedAttrs) {
      for (const attr of signer.signedAttrs.attributes) {
        if (attr.type === OID_SIGNING_TIME && attr.values.length > 0) {
          const timeValue = attr.values[0];
          if (timeValue instanceof asn1js.UTCTime || timeValue instanceof asn1js.GeneralizedTime) {
            signingTime = timeValue.toDate().toISOString();
          }
        }
        if (attr.type === OID_MESSAGE_DIGEST && attr.values.length > 0) {
          const digestValue = attr.values[0] as asn1js.OctetString;
          messageDigest = bufferToHex(digestValue.valueBlock.valueHexView);
        }
      }
    }
    
    const signatureAlgorithm = getAlgorithmName(signer.signatureAlgorithm.algorithmId);
    const signature = signer.signature.valueBlock.valueHexView;
    
    let signerCertificate: CertificateInfo | undefined;
    const signerChain: CertificateInfo[] = [];
    
    if (signedData.certificates) {
      const issuer = signer.sid instanceof pkijs.IssuerAndSerialNumber
        ? getNameString(signer.sid.issuer)
        : undefined;
      const serial = signer.sid instanceof pkijs.IssuerAndSerialNumber
        ? bufferToHex(signer.sid.serialNumber.valueBlock.valueHexView)
        : undefined;
      
      for (let i = 0; i < signedData.certificates.length; i++) {
        const cert = signedData.certificates[i];
        if (cert instanceof pkijs.Certificate) {
          const certIssuer = getNameString(cert.issuer);
          const certSerial = bufferToHex(cert.serialNumber.valueBlock.valueHexView);
          
          if (issuer && serial && certIssuer === issuer && certSerial === serial) {
            signerCertificate = certs[i];
          }
          
          if (certs[i]) {
            signerChain.push(certs[i]);
          }
        }
      }
    }
    
    results.push({
      signerCertificate,
      signatureAlgorithm,
      signingTime,
      messageDigest,
      signature: new Uint8Array(signature.buffer, signature.byteOffset, signature.byteLength),
      certificateChain: signerChain,
    });
  }
  
  return results;
}

export async function verifySignatureValue(
  signerInfo: pkijs.SignerInfo,
  signedData: pkijs.SignedData
): Promise<boolean> {
  try {
    const cryptoEngine = pkijs.getCrypto();
    if (!cryptoEngine) {
      throw new Error('No crypto engine available');
    }
    
    let signerCert: pkijs.Certificate | undefined;
    if (signedData.certificates && signerInfo.sid instanceof pkijs.IssuerAndSerialNumber) {
      for (const cert of signedData.certificates) {
        if (cert instanceof pkijs.Certificate) {
          const certIssuer = getNameString(cert.issuer);
          const certSerial = bufferToHex(cert.serialNumber.valueBlock.valueHexView);
          const issuer = getNameString(signerInfo.sid.issuer);
          const serial = bufferToHex(signerInfo.sid.serialNumber.valueBlock.valueHexView);
          
          if (certIssuer === issuer && certSerial === serial) {
            signerCert = cert;
            break;
          }
        }
      }
    }
    
    if (!signerCert) {
      return false;
    }
    
    const signatureAlgorithm = getAlgorithmName(signerInfo.signatureAlgorithm.algorithmId);
    let hashName = 'SHA-256';
    if (signatureAlgorithm.includes('SHA1')) hashName = 'SHA-1';
    else if (signatureAlgorithm.includes('SHA256')) hashName = 'SHA-256';
    else if (signatureAlgorithm.includes('SHA384')) hashName = 'SHA-384';
    else if (signatureAlgorithm.includes('SHA512')) hashName = 'SHA-512';
    else if (signatureAlgorithm.includes('SHA224')) hashName = 'SHA-224';
    
    const algorithm = {
      name: 'RSASSA-PKCS1-v1_5',
      hash: { name: hashName },
    };
    
    const publicKeyInfo = signerCert.subjectPublicKeyInfo;
    const publicKey = await cryptoEngine.importKey(
      'spki',
      publicKeyInfo.subjectPublicKey.valueBlock.valueHexView,
      algorithm,
      false,
      ['verify']
    );
    
    let signedAttrsBuffer: ArrayBuffer;
    if (signerInfo.signedAttrs) {
      const signedAttrs = signerInfo.signedAttrs;
      const encoded = signedAttrs.toSchema().toBER();
      signedAttrsBuffer = encoded;
    } else {
      signedAttrsBuffer = signedData.encapContentInfo.eContent?.valueBlock.valueHexView || new ArrayBuffer(0);
    }
    
    const signature = signerInfo.signature.valueBlock.valueHexView;
    
    return await cryptoEngine.verify(
      algorithm,
      publicKey,
      signature,
      signedAttrsBuffer
    );
  } catch {
    return false;
  }
}

export interface TimestampTokenResult {
  hasTimestamp: boolean;
  isValid: boolean;
  timestampTime?: string;
  timestampAuthority?: string;
  hashAlgorithm?: string;
  messageImprint?: string;
  serialNumber?: string;
  certificateChain: CertificateInfo[];
}

export async function parseTimestampToken(
  data: ArrayBuffer
): Promise<TimestampTokenResult> {
  try {
    const asn1 = asn1js.fromBER(data);
    if (asn1.offset === -1) {
      return {
        hasTimestamp: false,
        isValid: false,
        certificateChain: [],
      };
    }
    
    const contentInfo = new pkijs.ContentInfo({ schema: asn1.result });
    if (contentInfo.contentType !== OID_SIGNED_DATA) {
      return {
        hasTimestamp: false,
        isValid: false,
        certificateChain: [],
      };
    }
    
    const signedData = new pkijs.SignedData({ schema: contentInfo.content });
    
    const eContent = signedData.encapContentInfo.eContent;
    if (!eContent) {
      return {
        hasTimestamp: false,
        isValid: false,
        certificateChain: [],
      };
    }
    
    const tstInfoAsn1 = asn1js.fromBER(eContent.valueBlock.valueHexView);
    if (tstInfoAsn1.offset === -1) {
      return {
        hasTimestamp: false,
        isValid: false,
        certificateChain: [],
      };
    }
    
    const tstInfo = new pkijs.TSTInfo({ schema: tstInfoAsn1.result });
    
    const timestampTime = tstInfo.genTime.toISOString();
    const hashAlgorithm = getAlgorithmName(tstInfo.messageImprint.hashAlgorithm.algorithmId);
    const messageImprint = bufferToHex(tstInfo.messageImprint.hashedMessage.valueBlock.valueHexView);
    const serialNumber = bufferToHex(tstInfo.serialNumber.valueBlock.valueHexView);
    
    const certs: CertificateInfo[] = [];
    let timestampAuthority: string | undefined;
    
    if (signedData.certificates) {
      for (const cert of signedData.certificates) {
        if (cert instanceof pkijs.Certificate) {
          const info = await extractCertificateInfo(cert);
          certs.push(info);
          if (!timestampAuthority) {
            timestampAuthority = info.subject;
          }
        }
      }
    }
    
    let isValid = true;
    if (signedData.signerInfos.length > 0) {
      isValid = await verifySignatureValue(signedData.signerInfos[0], signedData);
    }
    
    return {
      hasTimestamp: true,
      isValid,
      timestampTime,
      timestampAuthority,
      hashAlgorithm,
      messageImprint,
      serialNumber,
      certificateChain: certs,
    };
  } catch {
    return {
      hasTimestamp: false,
      isValid: false,
      certificateChain: [],
    };
  }
}

export async function extractTimestampFromSignedData(
  signedData: pkijs.SignedData
): Promise<TimestampTokenResult | null> {
  for (const signer of signedData.signerInfos) {
    if (signer.unsignedAttrs) {
      for (const attr of signer.unsignedAttrs.attributes) {
        if (attr.type === OID_TIMESTAMP_TOKEN && attr.values.length > 0) {
          const tsValue = attr.values[0] as asn1js.OctetString;
          return await parseTimestampToken(tsValue.valueBlock.valueHexView);
        }
      }
    }
  }
  return null;
}

export { bufferToHex };
