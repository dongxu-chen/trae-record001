import * as pdfjsLib from 'pdfjs-dist';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import {
  calculateHash,
  calculateHashFromBuffer,
  parsePKCS7,
  getSignerInfo,
  getCertificateInfo,
  extractSignedDataBytes,
  getSignatureHashAlgorithm,
  getSigningTime,
  getMessageDigest,
  parseCertificate
} from '../core/crypto-utils.js';
import type { CertificateInfo, IntegrityResult, SignatureVisualization, SignaturePosition } from '../../../shared/index.js';

export interface SignatureField {
  name: string;
  byteRange: number[];
  signatureContents: Uint8Array;
  signedDataBytes: Uint8Array;
  documentHash: string;
  hashAlgorithm: string;
  signingTime: string | null;
  signerInfo: CertificateInfo | null;
  isModified: boolean;
  isValid: boolean;
}

pdfjsLib.GlobalWorkerOptions.workerSrc = '';

export async function parsePDF(data: Uint8Array): Promise<PDFDocumentProxy> {
  const arrayBuffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
  const loadingTask = pdfjsLib.getDocument({ data: arrayBuffer });
  return loadingTask.promise;
}

export async function extractSignatureFields(data: Uint8Array): Promise<SignatureField[]> {
  const pdfDoc = await parsePDF(data);
  const fields: SignatureField[] = [];
  const acroForm = await pdfDoc.catalog.getAcroForm();
  
  if (!acroForm) {
    await pdfDoc.destroy();
    return fields;
  }
  
  const fieldNames = Object.keys(acroForm);
  
  for (const fieldName of fieldNames) {
    const field = acroForm[fieldName];
    if (field.fieldType === 'Sig') {
      const signatureField = await processSignatureField(data, field, fieldName);
      if (signatureField) {
        fields.push(signatureField);
      }
    }
  }
  
  await pdfDoc.destroy();
  return fields;
}

async function processSignatureField(
  pdfData: Uint8Array,
  field: any,
  fieldName: string
): Promise<SignatureField | null> {
  try {
    const byteRange = field.byteRange;
    const contents = field.signatureContents;
    
    if (!byteRange || !contents) {
      return null;
    }
    
    const byteRangeArray = Array.isArray(byteRange) ? byteRange : [0, 0, 0, 0];
    
    const signatureContents = getSignatureContents(contents);
    const signedDataBytes = extractSignedDataBytes(pdfData, byteRangeArray);
    const pkcs7Data = parsePKCS7(signatureContents);
    
    if (!pkcs7Data) {
      return {
        name: fieldName,
        byteRange: byteRangeArray,
        signatureContents,
        signedDataBytes,
        documentHash: '',
        hashAlgorithm: 'SHA256',
        signingTime: null,
        signerInfo: null,
        isModified: true,
        isValid: false
      };
    }
    
    const signerInfo = getSignerInfo(pkcs7Data);
    const hashAlgorithm = signerInfo ? getSignatureHashAlgorithm(signerInfo) : 'SHA256';
    const documentHash = calculateHash(signedDataBytes, hashAlgorithm as 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512');
    
    const signingTime = signerInfo ? getSigningTime(signerInfo) : null;
    const signedDigest = signerInfo ? getMessageDigest(signerInfo) : null;
    
    let signerCertInfo: CertificateInfo | null = null;
    if (pkcs7Data.certificates && pkcs7Data.certificates.length > 0) {
      const cert = pkcs7Data.certificates[0];
      if (cert) {
        const certBuffer = cert.toSchema().toBER(false);
        const parsedCert = parseCertificate(certBuffer);
        if (parsedCert) {
          signerCertInfo = getCertificateInfo(parsedCert);
        }
      }
    }
    
    let isModified = true;
    if (signedDigest) {
      const signedDigestHex = Buffer.from(signedDigest).toString('hex');
      isModified = documentHash.toLowerCase() !== signedDigestHex.toLowerCase();
    }
    
    return {
      name: fieldName,
      byteRange: byteRangeArray,
      signatureContents,
      signedDataBytes,
      documentHash,
      hashAlgorithm,
      signingTime,
      signerInfo: signerCertInfo,
      isModified,
      isValid: !isModified
    };
  } catch {
    return null;
  }
}

function getSignatureContents(contents: any): Uint8Array {
  if (contents instanceof Uint8Array) {
    return contents;
  }
  if (contents instanceof ArrayBuffer) {
    return new Uint8Array(contents);
  }
  if (typeof contents === 'string') {
    return new Uint8Array(Buffer.from(contents, 'hex'));
  }
  if (Array.isArray(contents)) {
    return new Uint8Array(contents);
  }
  return new Uint8Array();
}

export function getSignatureContent(signatureField: SignatureField): Uint8Array {
  return signatureField.signatureContents;
}

export function getByteRange(signatureField: SignatureField): number[] {
  return signatureField.byteRange;
}

export function calculateDocumentHash(
  pdfData: Uint8Array,
  byteRange: number[],
  algorithm: 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512' = 'SHA256'
): string {
  const signedDataBytes = extractSignedDataBytes(pdfData, byteRange);
  return calculateHash(signedDataBytes, algorithm);
}

export function getSignerInformation(signatureField: SignatureField): CertificateInfo | null {
  return signatureField.signerInfo;
}

export function detectTampering(signatureField: SignatureField): boolean {
  return signatureField.isModified;
}

export async function verifyPDFIntegrity(
  pdfData: Uint8Array
): Promise<IntegrityResult[]> {
  const signatureFields = await extractSignatureFields(pdfData);
  const results: IntegrityResult[] = [];
  
  for (const field of signatureFields) {
    const signedDigest = getSignedDigestFromPKCS7(field.signatureContents);
    const hashMatch = field.documentHash.toLowerCase() === signedDigest.toLowerCase();
    
    results.push({
      isValid: field.isValid,
      documentHash: field.documentHash,
      signedHash: signedDigest,
      hashMatch,
      signatureAlgorithm: field.hashAlgorithm,
      signingTime: field.signingTime || '',
      hasModifications: field.isModified,
      errors: field.isModified ? ['Document has been modified since signing'] : [],
      warnings: []
    });
  }
  
  return results;
}

function getSignedDigestFromPKCS7(signatureContents: Uint8Array): string {
  const pkcs7Data = parsePKCS7(signatureContents);
  if (!pkcs7Data) return '';
  
  const signerInfo = getSignerInfo(pkcs7Data);
  if (!signerInfo) return '';
  
  const messageDigest = getMessageDigest(signerInfo);
  if (!messageDigest) return '';
  
  return Buffer.from(messageDigest).toString('hex');
}

export async function getPDFInfo(data: Uint8Array): Promise<{
  pageCount: number;
  title: string;
  author: string;
  subject: string;
  keywords: string;
  creationDate: string;
  modificationDate: string;
}> {
  const pdfDoc = await parsePDF(data);
  const metadata = await pdfDoc.getMetadata();
  
  const info = metadata.info || {};
  
  await pdfDoc.destroy();
  
  return {
    pageCount: pdfDoc.numPages,
    title: (info as any).Title || '',
    author: (info as any).Author || '',
    subject: (info as any).Subject || '',
    keywords: (info as any).Keywords || '',
    creationDate: (info as any).CreationDate || '',
    modificationDate: (info as any).ModDate || ''
  };
}

export async function getAllSignatures(data: Uint8Array): Promise<SignatureField[]> {
  return extractSignatureFields(data);
}

export async function hasSignatures(data: Uint8Array): Promise<boolean> {
  const signatures = await extractSignatureFields(data);
  return signatures.length > 0;
}

export function verifyDocumentHash(
  pdfData: Uint8Array,
  byteRange: number[],
  expectedHash: string,
  algorithm: 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512' = 'SHA256'
): boolean {
  const actualHash = calculateDocumentHash(pdfData, byteRange, algorithm);
  return actualHash.toLowerCase() === expectedHash.toLowerCase();
}

export function getRawSignatureData(pdfData: Uint8Array, byteRange: number[]): Uint8Array {
  return extractSignedDataBytes(pdfData, byteRange);
}

export async function getSignerCertificate(
  signatureField: SignatureField
): Promise<CertificateInfo | null> {
  return signatureField.signerInfo;
}

export async function extractSignaturePositions(
  data: Uint8Array
): Promise<SignatureVisualization> {
  const pdfDoc = await parsePDF(data);
  const positions: SignaturePosition[] = [];

  try {
    const acroForm = await (pdfDoc as any).catalog?.getAcroForm?.();

    if (acroForm) {
      const fieldNames = Object.keys(acroForm);

      for (const fieldName of fieldNames) {
        const field = acroForm[fieldName];
        if (field.fieldType === 'Sig') {
          try {
            const widget = field.widgets && field.widgets[0];
            if (widget && widget.rect) {
              const pageIndex = widget.page?.pageIndex ?? 0;
              const page = await pdfDoc.getPage(pageIndex + 1);
              const viewport = page.getViewport({ scale: 1.0 });

              const rect = widget.rect;
              const left = rect[0];
              const bottom = rect[1];
              const right = rect[2];
              const top = rect[3];

              const pageHeight = viewport.height;
              const position: SignaturePosition = {
                pageIndex,
                pageHeight,
                pageWidth: viewport.width,
                left,
                top: pageHeight - top,
                right,
                bottom: pageHeight - bottom,
                width: right - left,
                height: top - bottom,
                fieldName,
                signerName: field.signerName || undefined,
                signingDate: field.signingDate || undefined
              };

              positions.push(position);
            }
          } catch {}
        }
      }
    }
  } catch {}

  const pageCount = pdfDoc.numPages;
  await pdfDoc.destroy();

  return {
    hasVisualRepresentation: positions.length > 0,
    positions,
    pageCount
  };
}
