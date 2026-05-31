import * as CryptoJS from 'crypto-js';
import * as asn1js from 'asn1js';
import * as pkijs from 'pkijs';
import type { CertificateInfo } from '../../../shared';

export function calculateHash(data: Uint8Array, algorithm: 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512' = 'SHA256'): string {
  const wordArray = CryptoJS.lib.WordArray.create(data as unknown as number[]);
  const hash = CryptoJS[algorithm.toLowerCase() as 'sha1' | 'sha256' | 'sha384' | 'sha512'](wordArray);
  return hash.toString(CryptoJS.enc.Hex);
}

export function calculateHashFromBuffer(buffer: ArrayBuffer, algorithm: 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512' = 'SHA256'): string {
  return calculateHash(new Uint8Array(buffer), algorithm);
}

export function parsePKCS7(pkcs7Data: Uint8Array): pkijs.SignedData | null {
  try {
    const asn1 = asn1js.fromBER(pkcs7Data.buffer.slice(pkcs7Data.byteOffset, pkcs7Data.byteOffset + pkcs7Data.byteLength));
    const cms = new pkijs.ContentInfo({ schema: asn1.result });
    if (cms.contentType !== '1.2.840.113549.1.7.2') return null;
    return new pkijs.SignedData({ schema: cms.content });
  } catch {
    return null;
  }
}

export function getSignerInfo(signedData: pkijs.SignedData): pkijs.SignerInfo | null {
  if (!signedData.signerInfos || signedData.signerInfos.length === 0) return null;
  return signedData.signerInfos[0];
}

export function parseCertificate(certBuffer: ArrayBuffer): pkijs.Certificate | null {
  try {
    const asn1 = asn1js.fromBER(certBuffer);
    return new pkijs.Certificate({ schema: asn1.result });
  } catch {
    return null;
  }
}

export function getCertificateInfo(certificate: pkijs.Certificate): CertificateInfo {
  const subject = certificate.subject.toString();
  const issuer = certificate.issuer.toString();
  const serialNumber = certificate.serialNumber.toString();
  const validFrom = certificate.notBefore.value.toISOString();
  const validTo = certificate.notAfter.value.toISOString();
  const signatureAlgorithm = certificate.signature.algorithmId;
  
  const rawBuffer = certificate.toSchema().toBER(false);
  const fingerprint = calculateHash(new Uint8Array(rawBuffer), 'SHA1');
  
  const keyUsage: string[] = [];
  const isCA = false;
  const isSelfSigned = subject === issuer;
  const isTrustedRoot = false;
  
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
    isTrustedRoot
  };
}

export function verifySignature(
  signedData: pkijs.SignedData,
  signerIndex: number = 0
): Promise<boolean> {
  return signedData.verify({ signer: signerIndex }).catch(() => false);
}

export function extractSignedDataBytes(pdfData: Uint8Array, byteRange: number[]): Uint8Array {
  const [start1, length1, start2, length2] = byteRange;
  const part1 = pdfData.slice(start1, start1 + length1);
  const part2 = pdfData.slice(start2, start2 + length2);
  const result = new Uint8Array(part1.length + part2.length);
  result.set(part1, 0);
  result.set(part2, part1.length);
  return result;
}

export function getSignatureHashAlgorithm(signerInfo: pkijs.SignerInfo): string {
  const digestOid = signerInfo.digestAlgorithm.algorithmId;
  const oidMap: Record<string, string> = {
    '1.3.14.3.2.26': 'SHA1',
    '2.16.840.1.101.3.4.2.1': 'SHA256',
    '2.16.840.1.101.3.4.2.2': 'SHA384',
    '2.16.840.1.101.3.4.2.3': 'SHA512'
  };
  return oidMap[digestOid] || 'SHA256';
}

export function getSigningTime(signerInfo: pkijs.SignerInfo): string | null {
  if (!signerInfo.signedAttrs) return null;
  const signingTimeAttr = signerInfo.signedAttrs.attributes.find(
    (attr: pkijs.Attribute) => attr.type === '1.2.840.113549.1.9.5'
  );
  if (!signingTimeAttr || signingTimeAttr.values.length === 0) return null;
  const value = signingTimeAttr.values[0];
  if (value instanceof asn1js.UTCTime || value instanceof asn1js.GeneralizedTime) {
    return value.toDate().toISOString();
  }
  return null;
}

export function getMessageDigest(signerInfo: pkijs.SignerInfo): Uint8Array | null {
  if (!signerInfo.signedAttrs) return null;
  const digestAttr = signerInfo.signedAttrs.attributes.find(
    (attr: pkijs.Attribute) => attr.type === '1.2.840.113549.1.9.4'
  );
  if (!digestAttr || digestAttr.values.length === 0) return null;
  const value = digestAttr.values[0];
  if (value instanceof asn1js.OctetString) {
    return new Uint8Array(value.valueBlock.valueHex);
  }
  return null;
}
