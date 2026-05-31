import { calculateHash, parsePKCS7, getSignerInfo, getSignatureHashAlgorithm, getSigningTime, getMessageDigest, extractSignedDataBytes } from '../core/crypto-utils';
import { verifySignatureValue } from '../core/pki-engine';
import { extractSignatureFields, calculateDocumentHash, getSignatureContent, getByteRange } from '../core/pdf-parser';
import type { IntegrityResult } from '../../../shared';

export async function calculateDocumentOriginalHash(
  pdfData: Uint8Array,
  signatureFormat: 'PAdES' | 'XAdES' | 'CAdES' = 'PAdES'
): Promise<{ hash: string; algorithm: string; byteRange: number[] }> {
  if (signatureFormat === 'PAdES') {
    const signatureFields = await extractSignatureFields(pdfData);
    if (signatureFields.length === 0) {
      const hash = calculateHash(pdfData, 'SHA256');
      return { hash, algorithm: 'SHA256', byteRange: [0, pdfData.length, 0, 0] };
    }
    const field = signatureFields[0];
    const byteRange = getByteRange(field);
    const algorithm = field.hashAlgorithm as 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512';
    const hash = calculateDocumentHash(pdfData, byteRange, algorithm);
    return { hash, algorithm: field.hashAlgorithm, byteRange };
  }
  const hash = calculateHash(pdfData, 'SHA256');
  return { hash, algorithm: 'SHA256', byteRange: [0, pdfData.length, 0, 0] };
}

export function extractSignedHash(signatureData: Uint8Array): string {
  const pkcs7Data = parsePKCS7(signatureData);
  if (!pkcs7Data) return '';
  const signerInfo = getSignerInfo(pkcs7Data);
  if (!signerInfo) return '';
  const messageDigest = getMessageDigest(signerInfo);
  if (!messageDigest) return '';
  return Buffer.from(messageDigest).toString('hex');
}

export function compareHashes(originalHash: string, signedHash: string): boolean {
  return originalHash.toLowerCase() === signedHash.toLowerCase();
}

export async function verifySignatureValidity(
  signatureData: Uint8Array,
  signedDataBytes: Uint8Array
): Promise<boolean> {
  try {
    const pkcs7Data = parsePKCS7(signatureData);
    if (!pkcs7Data) return false;
    const signerInfo = getSignerInfo(pkcs7Data);
    if (!signerInfo) return false;
    return await verifySignatureValue(signerInfo, pkcs7Data);
  } catch {
    return false;
  }
}

export function detectDocumentTampering(
  pdfData: Uint8Array,
  byteRange: number[],
  signedHash: string,
  algorithm: 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512'
): boolean {
  const signedDataBytes = extractSignedDataBytes(pdfData, byteRange);
  const calculatedHash = calculateHash(signedDataBytes, algorithm);
  return !compareHashes(calculatedHash, signedHash);
}

export function extractSignatureAlgorithm(signatureData: Uint8Array): string {
  const pkcs7Data = parsePKCS7(signatureData);
  if (!pkcs7Data) return 'SHA256';
  const signerInfo = getSignerInfo(pkcs7Data);
  if (!signerInfo) return 'SHA256';
  return getSignatureHashAlgorithm(signerInfo);
}

export function extractSigningTime(signatureData: Uint8Array): string {
  const pkcs7Data = parsePKCS7(signatureData);
  if (!pkcs7Data) return '';
  const signerInfo = getSignerInfo(pkcs7Data);
  if (!signerInfo) return '';
  return getSigningTime(signerInfo) || '';
}

export async function verifyDocumentIntegrity(
  pdfData: Uint8Array,
  signatureFormat: 'PAdES' | 'XAdES' | 'CAdES' = 'PAdES'
): Promise<IntegrityResult[]> {
  const results: IntegrityResult[] = [];
  const signatureFields = await extractSignatureFields(pdfData);

  if (signatureFields.length === 0) {
    const originalHash = calculateHash(pdfData, 'SHA256');
    results.push({
      isValid: false,
      documentHash: originalHash,
      signedHash: '',
      hashMatch: false,
      signatureAlgorithm: 'SHA256',
      signingTime: '',
      hasModifications: false,
      errors: ['No signature found in document'],
      warnings: []
    });
    return results;
  }

  for (const field of signatureFields) {
    const signatureData = getSignatureContent(field);
    const byteRange = getByteRange(field);
    const algorithm = field.hashAlgorithm as 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512';

    const originalHashResult = await calculateDocumentOriginalHash(pdfData, signatureFormat);
    const signedHash = extractSignedHash(signatureData);
    const hashMatch = compareHashes(originalHashResult.hash, signedHash);
    const signatureAlgorithm = extractSignatureAlgorithm(signatureData);
    const signingTime = extractSigningTime(signatureData);
    const hasModifications = detectDocumentTampering(pdfData, byteRange, signedHash, algorithm);
    const signatureValid = await verifySignatureValidity(signatureData, field.signedDataBytes);

    const errors: string[] = [];
    const warnings: string[] = [];

    if (!hashMatch) {
      errors.push('Document hash does not match signed hash');
    }
    if (!signatureValid) {
      errors.push('Signature value verification failed');
    }
    if (hasModifications) {
      errors.push('Document has been modified since signing');
    }
    if (algorithm === 'SHA1') {
      warnings.push('SHA1 algorithm is considered weak, consider using SHA256 or stronger');
    }

    results.push({
      isValid: hashMatch && signatureValid && !hasModifications,
      documentHash: originalHashResult.hash,
      signedHash,
      hashMatch,
      signatureAlgorithm,
      signingTime,
      hasModifications,
      errors,
      warnings
    });
  }

  return results;
}

export async function verifyIntegrityFromParsedData(
  pdfData: Uint8Array,
  signatureData: Uint8Array,
  byteRange: number[],
  algorithm: 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512'
): Promise<IntegrityResult> {
  const signedDataBytes = extractSignedDataBytes(pdfData, byteRange);
  const documentHash = calculateHash(signedDataBytes, algorithm);
  const signedHash = extractSignedHash(signatureData);
  const hashMatch = compareHashes(documentHash, signedHash);
  const signatureAlgorithm = extractSignatureAlgorithm(signatureData);
  const signingTime = extractSigningTime(signatureData);
  const hasModifications = !hashMatch;
  const signatureValid = await verifySignatureValidity(signatureData, signedDataBytes);

  const errors: string[] = [];
  const warnings: string[] = [];

  if (!hashMatch) {
    errors.push('Document hash does not match signed hash');
  }
  if (!signatureValid) {
    errors.push('Signature value verification failed');
  }
  if (hasModifications) {
    errors.push('Document has been modified since signing');
  }
  if (algorithm === 'SHA1') {
    warnings.push('SHA1 algorithm is considered weak, consider using SHA256 or stronger');
  }

  return {
    isValid: hashMatch && signatureValid && !hasModifications,
    documentHash,
    signedHash,
    hashMatch,
    signatureAlgorithm,
    signingTime,
    hasModifications,
    errors,
    warnings
  };
}
