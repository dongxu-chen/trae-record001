import * as pkijs from 'pkijs';
import * as asn1js from 'asn1js';
import {
  parseCMS,
  extractSignerInfo,
  verifySignatureValue,
  extractTimestampFromSignedData,
  extractCertificateInfo,
  parseCertificate,
  bufferToHex,
} from '../core/pki-engine';
import { calculateHash, calculateHashFromBuffer } from '../core/crypto-utils';
import { CertificateChainService } from './certificate-chain.service';
import { TimestampService } from './timestamp.service';
import {
  verifyIntegrityFromParsedData,
  extractSignedHash,
  extractSignatureAlgorithm,
  extractSigningTime,
} from './integrity.service';
import type {
  CertificateChainResult,
  TimestampResult,
  IntegrityResult,
  CertificateInfo,
  VerifyOptions,
} from '../../../shared';

const OID_SIGNED_DATA = '1.2.840.113549.1.7.2';
const OID_CONTENT_TYPE = '1.2.840.113549.1.9.3';
const OID_MESSAGE_DIGEST = '1.2.840.113549.1.9.4';
const OID_SIGNING_TIME = '1.2.840.113549.1.9.5';
const OID_TIMESTAMP_TOKEN = '1.2.840.113549.1.9.16.1.4';
const OID_SIGNATURE_POLICY_ID = '1.2.840.113549.1.9.16.2.15';
const OID_SIGNATURE_TIMESTAMP = '1.2.840.113549.1.9.16.2.14';
const OID_OCSP_RESPONSES = '1.2.840.113549.1.9.16.2.24';
const OID_CERTIFICATE_REFS = '1.2.840.113549.1.9.16.2.21';
const OID_REVOCATION_REFS = '1.2.840.113549.1.9.16.2.22';

export type CAdESLevel = 'CAdES-BES' | 'CAdES-EPES' | 'CAdES-LTV' | 'CAdES-T';

export interface CAdESSignatureInfo {
  format: 'CAdES';
  level: CAdESLevel;
  signerCertificate?: CertificateInfo;
  signerCertificatePem?: string;
  signatureAlgorithm: string;
  signatureValue: Uint8Array;
  signingTime?: string;
  messageDigest?: string;
  signedData?: Uint8Array;
  certificateChain: CertificateInfo[];
  hasSignedAttributes: boolean;
  hasUnsignedAttributes: boolean;
  hasTimestamp: boolean;
  hasOCSPResponses: boolean;
  hasCertificateRefs: boolean;
  hasRevocationRefs: boolean;
  hasSignaturePolicy: boolean;
}

export interface CAdESVerifyResult {
  isValid: boolean;
  signatureInfo: CAdESSignatureInfo;
  certificateChain: CertificateChainResult;
  timestamp: TimestampResult;
  integrity: IntegrityResult;
  cadesLevel: CAdESLevel;
  errors: string[];
  warnings: string[];
}

export class CAdESService {
  private certificateChainService: CertificateChainService;
  private timestampService: TimestampService;

  constructor(trustedRootCerts?: string[]) {
    this.certificateChainService = new CertificateChainService(trustedRootCerts);
    this.timestampService = new TimestampService(trustedRootCerts);
  }

  isPKCS7Format(data: ArrayBuffer): boolean {
    try {
      const asn1 = asn1js.fromBER(data);
      if (asn1.offset === -1) return false;
      const contentInfo = new pkijs.ContentInfo({ schema: asn1.result });
      return contentInfo.contentType === OID_SIGNED_DATA;
    } catch {
      return false;
    }
  }

  detectCAdESLevel(signedData: pkijs.SignedData): CAdESLevel {
    let hasSignatureTimestamp = false;
    let hasOCSP = false;
    let hasCertRefs = false;
    let hasRevocationRefs = false;
    let hasSignaturePolicy = false;
    let hasSigningTime = false;

    for (const signer of signedData.signerInfos) {
      if (signer.signedAttrs) {
        for (const attr of signer.signedAttrs.attributes) {
          if (attr.type === OID_SIGNING_TIME) hasSigningTime = true;
          if (attr.type === OID_SIGNATURE_POLICY_ID) hasSignaturePolicy = true;
        }
      }
      if (signer.unsignedAttrs) {
        for (const attr of signer.unsignedAttrs.attributes) {
          if (attr.type === OID_SIGNATURE_TIMESTAMP || attr.type === OID_TIMESTAMP_TOKEN) hasSignatureTimestamp = true;
          if (attr.type === OID_OCSP_RESPONSES) hasOCSP = true;
          if (attr.type === OID_CERTIFICATE_REFS) hasCertRefs = true;
          if (attr.type === OID_REVOCATION_REFS) hasRevocationRefs = true;
        }
      }
    }

    if (hasOCSP && hasCertRefs && hasRevocationRefs) {
      return 'CAdES-LTV';
    }
    if (hasSignatureTimestamp) {
      return 'CAdES-T';
    }
    if (hasSignaturePolicy) {
      return 'CAdES-EPES';
    }
    return 'CAdES-BES';
  }

  async extractSignatureInfo(signatureData: ArrayBuffer): Promise<CAdESSignatureInfo | null> {
    try {
      if (!this.isPKCS7Format(signatureData)) {
        return null;
      }

      const signedData = parseCMS(signatureData);
      const signerInfos = await extractSignerInfo(signedData);

      if (signerInfos.length === 0) {
        return null;
      }

      const signerInfo = signerInfos[0];
      const signer = signedData.signerInfos[0];

      let signedDataBytes: Uint8Array | undefined;
      if (signedData.encapContentInfo.eContent) {
        const eContent = signedData.encapContentInfo.eContent;
        signedDataBytes = new Uint8Array(eContent.valueBlock.valueHexView);
      }

      let hasSignedAttributes = false;
      let hasUnsignedAttributes = false;
      let hasTimestamp = false;
      let hasOCSPResponses = false;
      let hasCertificateRefs = false;
      let hasRevocationRefs = false;
      let hasSignaturePolicy = false;

      if (signer.signedAttrs) {
        hasSignedAttributes = true;
        for (const attr of signer.signedAttrs.attributes) {
          if (attr.type === OID_SIGNATURE_POLICY_ID) hasSignaturePolicy = true;
        }
      }

      if (signer.unsignedAttrs) {
        hasUnsignedAttributes = true;
        for (const attr of signer.unsignedAttrs.attributes) {
          if (attr.type === OID_TIMESTAMP_TOKEN || attr.type === OID_SIGNATURE_TIMESTAMP) hasTimestamp = true;
          if (attr.type === OID_OCSP_RESPONSES) hasOCSPResponses = true;
          if (attr.type === OID_CERTIFICATE_REFS) hasCertificateRefs = true;
          if (attr.type === OID_REVOCATION_REFS) hasRevocationRefs = true;
        }
      }

      const level = this.detectCAdESLevel(signedData);
      let signerCertPem: string | undefined;

      if (signedData.certificates && signer.sid instanceof pkijs.IssuerAndSerialNumber) {
        for (const cert of signedData.certificates) {
          if (cert instanceof pkijs.Certificate) {
            const certIssuer = this.getNameString(cert.issuer);
            const certSerial = bufferToHex(cert.serialNumber.valueBlock.valueHexView);
            const issuer = this.getNameString(signer.sid.issuer);
            const serial = bufferToHex(signer.sid.serialNumber.valueBlock.valueHexView);

            if (certIssuer === issuer && certSerial === serial) {
              const pem = this.certificateToPem(cert);
              signerCertPem = pem;
              break;
            }
          }
        }
      }

      return {
        format: 'CAdES',
        level,
        signerCertificate: signerInfo.signerCertificate,
        signerCertificatePem: signerCertPem,
        signatureAlgorithm: signerInfo.signatureAlgorithm,
        signatureValue: signerInfo.signature,
        signingTime: signerInfo.signingTime,
        messageDigest: signerInfo.messageDigest,
        signedData: signedDataBytes,
        certificateChain: signerInfo.certificateChain,
        hasSignedAttributes,
        hasUnsignedAttributes,
        hasTimestamp,
        hasOCSPResponses,
        hasCertificateRefs,
        hasRevocationRefs,
        hasSignaturePolicy,
      };
    } catch {
      return null;
    }
  }

  async verifySignature(
    signatureData: ArrayBuffer,
    originalData?: ArrayBuffer,
    options?: Partial<VerifyOptions>
  ): Promise<CAdESVerifyResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    const verifyOptions: VerifyOptions = {
      verifyLevel: options?.verifyLevel || 'standard',
      customTrustCerts: options?.customTrustCerts,
      complianceStandard: options?.complianceStandard || 'cn-es',
      checkRevocation: options?.checkRevocation ?? true,
      checkTimestamp: options?.checkTimestamp ?? true,
    };

    if (verifyOptions.customTrustCerts) {
      this.certificateChainService = new CertificateChainService(verifyOptions.customTrustCerts);
      this.timestampService = new TimestampService(verifyOptions.customTrustCerts);
    }

    if (!this.isPKCS7Format(signatureData)) {
      return {
        isValid: false,
        signatureInfo: {} as CAdESSignatureInfo,
        certificateChain: {
          isValid: false,
          certificates: [],
          trustPath: [],
          revocationStatus: 'unknown',
          errors: ['Not a valid PKCS#7/CMS format'],
          warnings: [],
        },
        timestamp: {
          hasTimestamp: false,
          isValid: false,
          timestampTime: '',
          timestampAuthority: '',
          certificateChain: [],
          hashAlgorithm: '',
          messageImprint: '',
          errors: ['Not a valid PKCS#7/CMS format'],
          warnings: [],
        },
        integrity: {
          isValid: false,
          documentHash: '',
          signedHash: '',
          hashMatch: false,
          signatureAlgorithm: '',
          signingTime: '',
          hasModifications: false,
          errors: ['Not a valid PKCS#7/CMS format'],
          warnings: [],
        },
        cadesLevel: 'CAdES-BES',
        errors: ['Not a valid PKCS#7/CMS format'],
        warnings: [],
      };
    }

    let signedData: pkijs.SignedData;
    try {
      signedData = parseCMS(signatureData);
    } catch (e) {
      errors.push('Failed to parse CMS signed data');
      return {
        isValid: false,
        signatureInfo: {} as CAdESSignatureInfo,
        certificateChain: this.createEmptyChainResult(errors),
        timestamp: this.createEmptyTimestampResult(errors),
        integrity: this.createEmptyIntegrityResult(errors),
        cadesLevel: 'CAdES-BES',
        errors,
        warnings: [],
      };
    }

    const signatureInfo = await this.extractSignatureInfo(signatureData);
    if (!signatureInfo) {
      errors.push('Failed to extract signature information');
      return {
        isValid: false,
        signatureInfo: {} as CAdESSignatureInfo,
        certificateChain: this.createEmptyChainResult(errors),
        timestamp: this.createEmptyTimestampResult(errors),
        integrity: this.createEmptyIntegrityResult(errors),
        cadesLevel: 'CAdES-BES',
        errors,
        warnings: [],
      };
    }

    const cadesLevel = this.detectCAdESLevel(signedData);

    const signatureValid = await verifySignatureValue(signedData.signerInfos[0], signedData);
    if (!signatureValid) {
      errors.push('Signature value verification failed');
    }

    if (!signatureInfo.hasSignedAttributes) {
      warnings.push('No signed attributes found - signature may be deprecated');
    }

    if (!signatureInfo.messageDigest) {
      errors.push('No message digest found in signed attributes');
    }

    let documentHash = '';
    if (originalData) {
      const algorithm = signatureInfo.signatureAlgorithm.includes('SHA256') ? 'SHA256' :
                       signatureInfo.signatureAlgorithm.includes('SHA384') ? 'SHA384' :
                       signatureInfo.signatureAlgorithm.includes('SHA512') ? 'SHA512' :
                       signatureInfo.signatureAlgorithm.includes('SHA1') ? 'SHA1' : 'SHA256';
      documentHash = calculateHashFromBuffer(originalData, algorithm as 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512');
    } else if (signatureInfo.signedData) {
      const algorithm = signatureInfo.signatureAlgorithm.includes('SHA256') ? 'SHA256' :
                       signatureInfo.signatureAlgorithm.includes('SHA384') ? 'SHA384' :
                       signatureInfo.signatureAlgorithm.includes('SHA512') ? 'SHA512' :
                       signatureInfo.signatureAlgorithm.includes('SHA1') ? 'SHA1' : 'SHA256';
      documentHash = calculateHash(signatureInfo.signedData, algorithm as 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512');
    }

    const signatureDataUint8 = new Uint8Array(signatureData);
    const byteRange = [0, signatureDataUint8.length, 0, 0];
    const hashAlgorithm = signatureInfo.signatureAlgorithm.includes('SHA256') ? 'SHA256' :
                         signatureInfo.signatureAlgorithm.includes('SHA384') ? 'SHA384' :
                         signatureInfo.signatureAlgorithm.includes('SHA512') ? 'SHA512' :
                         signatureInfo.signatureAlgorithm.includes('SHA1') ? 'SHA1' : 'SHA256';

    let originalDataForIntegrity = new Uint8Array();
    if (originalData) {
      originalDataForIntegrity = new Uint8Array(originalData);
    } else if (signatureInfo.signedData) {
      originalDataForIntegrity = signatureInfo.signedData;
    }

    const integrityResult = await verifyIntegrityFromParsedData(
      originalDataForIntegrity,
      signatureDataUint8,
      byteRange,
      hashAlgorithm as 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512'
    );

    if (signatureInfo.messageDigest && documentHash) {
      const normalizedDigest = signatureInfo.messageDigest.replace(/:/g, '').toUpperCase();
      const normalizedDocHash = documentHash.toUpperCase();
      if (normalizedDigest !== normalizedDocHash) {
        errors.push('Message digest does not match document hash');
      }
    }

    let chainResult: CertificateChainResult;
    if (signatureInfo.signerCertificatePem) {
      const intermediateCerts = signatureInfo.certificateChain
        .slice(1)
        .map(c => c.pem || '')
        .filter(pem => pem.length > 0);

      chainResult = await this.certificateChainService.buildAndVerifyChain(
        signatureInfo.signerCertificatePem,
        intermediateCerts,
        verifyOptions.checkRevocation
      );

      if (!chainResult.isValid) {
        errors.push(...chainResult.errors);
      }
      warnings.push(...chainResult.warnings);
    } else {
      errors.push('Signer certificate not found in signature');
      chainResult = {
        isValid: false,
        certificates: signatureInfo.certificateChain,
        trustPath: [],
        revocationStatus: 'unknown',
        errors: ['Signer certificate not found in signature'],
        warnings: [],
      };
    }

    let timestampResult: TimestampResult;
    if (verifyOptions.checkTimestamp && signatureInfo.hasTimestamp) {
      const timestampData = await extractTimestampFromSignedData(signedData);
      if (timestampData && timestampData.hasTimestamp) {
        timestampResult = await this.timestampService.verifyTimestampToken(
          new Uint8Array(signatureInfo.signatureValue).buffer,
          documentHash,
          signatureInfo.certificateChain,
          verifyOptions.customTrustCerts
        );

        if (!timestampResult.isValid) {
          errors.push(...timestampResult.errors);
        }
        warnings.push(...timestampResult.warnings);
      } else {
        timestampResult = {
          hasTimestamp: false,
          isValid: false,
          timestampTime: '',
          timestampAuthority: '',
          certificateChain: [],
          hashAlgorithm: '',
          messageImprint: '',
          errors: ['Failed to parse timestamp token'],
          warnings: [],
        };
        warnings.push('Timestamp exists but could not be verified');
      }
    } else if (verifyOptions.checkTimestamp && !signatureInfo.hasTimestamp) {
      timestampResult = {
        hasTimestamp: false,
        isValid: false,
        timestampTime: '',
        timestampAuthority: '',
        certificateChain: [],
        hashAlgorithm: '',
        messageImprint: '',
        errors: [],
        warnings: ['No timestamp found in signature'],
      };
      if (verifyOptions.verifyLevel === 'strict') {
        errors.push('Timestamp is required for strict verification level');
      } else {
        warnings.push('No timestamp found - signature time cannot be verified');
      }
    } else {
      timestampResult = {
        hasTimestamp: false,
        isValid: false,
        timestampTime: '',
        timestampAuthority: '',
        certificateChain: [],
        hashAlgorithm: '',
        messageImprint: '',
        errors: [],
        warnings: [],
      };
    }

    if (cadesLevel === 'CAdES-LTV') {
      if (!signatureInfo.hasOCSPResponses) {
        warnings.push('CAdES-LTV level declared but no OCSP responses found');
      }
      if (!signatureInfo.hasCertificateRefs) {
        warnings.push('CAdES-LTV level declared but no certificate references found');
      }
      if (!signatureInfo.hasRevocationRefs) {
        warnings.push('CAdES-LTV level declared but no revocation references found');
      }
    }

    if (cadesLevel === 'CAdES-EPES' && !signatureInfo.hasSignaturePolicy) {
      warnings.push('CAdES-EPES level declared but no signature policy found');
    }

    if (signatureInfo.signatureAlgorithm.includes('SHA1') && verifyOptions.verifyLevel !== 'basic') {
      warnings.push('SHA1 algorithm is considered weak, consider using SHA256 or stronger');
    }

    const isValid = errors.length === 0 && chainResult.isValid && integrityResult.isValid && signatureValid;

    return {
      isValid,
      signatureInfo,
      certificateChain: chainResult,
      timestamp: timestampResult,
      integrity: integrityResult,
      cadesLevel,
      errors,
      warnings,
    };
  }

  async verifyMultipleSignatures(
    signatureData: ArrayBuffer,
    originalData?: ArrayBuffer,
    options?: Partial<VerifyOptions>
  ): Promise<CAdESVerifyResult[]> {
    const results: CAdESVerifyResult[] = [];

    if (!this.isPKCS7Format(signatureData)) {
      return results;
    }

    try {
      const signedData = parseCMS(signatureData);
      const signerCount = signedData.signerInfos.length;

      for (let i = 0; i < signerCount; i++) {
        const singleSignerData = this.extractSingleSignerData(signedData, i);
        if (singleSignerData) {
          const result = await this.verifySignature(singleSignerData, originalData, options);
          results.push(result);
        }
      }
    } catch {
    }

    return results;
  }

  private extractSingleSignerData(signedData: pkijs.SignedData, signerIndex: number): ArrayBuffer | null {
    try {
      const singleSignedData = new pkijs.SignedData({
        version: signedData.version,
        encapContentInfo: signedData.encapContentInfo,
        certificates: signedData.certificates,
        crls: signedData.crls,
        signerInfos: [signedData.signerInfos[signerIndex]],
      });

      const contentInfo = new pkijs.ContentInfo({
        contentType: OID_SIGNED_DATA,
        content: singleSignedData.toSchema(),
      });

      return contentInfo.toSchema().toBER();
    } catch {
      return null;
    }
  }

  private getNameString(name: pkijs.RelativeDistinguishedNames): string {
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

  private certificateToPem(cert: pkijs.Certificate): string {
    const ber = cert.toSchema().toBER();
    const base64 = this.arrayBufferToBase64(ber);
    const lines: string[] = [];
    for (let i = 0; i < base64.length; i += 64) {
      lines.push(base64.slice(i, i + 64));
    }
    return `-----BEGIN CERTIFICATE-----\n${lines.join('\n')}\n-----END CERTIFICATE-----`;
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private createEmptyChainResult(errors: string[]): CertificateChainResult {
    return {
      isValid: false,
      certificates: [],
      trustPath: [],
      revocationStatus: 'unknown',
      errors,
      warnings: [],
    };
  }

  private createEmptyTimestampResult(errors: string[]): TimestampResult {
    return {
      hasTimestamp: false,
      isValid: false,
      timestampTime: '',
      timestampAuthority: '',
      certificateChain: [],
      hashAlgorithm: '',
      messageImprint: '',
      errors,
      warnings: [],
    };
  }

  private createEmptyIntegrityResult(errors: string[]): IntegrityResult {
    return {
      isValid: false,
      documentHash: '',
      signedHash: '',
      hashMatch: false,
      signatureAlgorithm: '',
      signingTime: '',
      hasModifications: false,
      errors,
      warnings: [],
    };
  }
}
