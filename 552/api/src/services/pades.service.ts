import { extractSignatureFields, getSignatureContent, getByteRange, hasSignatures } from '../core/pdf-parser';
import { parsePKCS7, getSignerInfo, parseCertificate } from '../core/crypto-utils';
import { extractCertificateInfo } from '../core/pki-engine';
import * as pkijs from 'pkijs';
import { CertificateChainService } from './certificate-chain.service';
import { TimestampService } from './timestamp.service';
import { verifyIntegrityFromParsedData } from './integrity.service';
import type {
  CertificateChainResult,
  TimestampResult,
  IntegrityResult,
  CertificateInfo,
  VerifyOptions
} from '../../../shared';

export type PAdESLevel = 'PAdES-BES' | 'PAdES-EPES' | 'PAdES-LTV';

export interface PAdESSignatureInfo {
  signatureIndex: number;
  fieldName: string;
  padesLevel: PAdESLevel;
  byteRange: number[];
  signatureData: ArrayBuffer;
  signerCertificate: CertificateInfo | null;
  certificateChain: CertificateInfo[];
  signingTime: string;
  hashAlgorithm: string;
}

export interface PAdESVerificationResult {
  hasSignature: boolean;
  signatureCount: number;
  signatures: PAdESSignatureResult[];
  overallValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface PAdESSignatureResult {
  signatureInfo: PAdESSignatureInfo;
  certificateChain: CertificateChainResult;
  timestamp: TimestampResult;
  integrity: IntegrityResult;
  padesLevel: PAdESLevel;
  levelRequirements: PAdESLevelRequirements;
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface PAdESLevelRequirements {
  level: PAdESLevel;
  meetsRequirements: boolean;
  missingFeatures: string[];
  foundFeatures: string[];
}

const OID_SIGNATURE_POLICY_ID = '1.2.840.113549.1.9.16.2.15';
const OID_SIGNATURE_TIMESTAMP = '1.2.840.113549.1.9.16.1.4';
const OID_CERTIFICATE_VALUES = '1.2.840.113549.1.9.16.2.23';
const OID_REVOCATION_VALUES = '1.2.840.113549.1.9.16.2.24';
const OID_COMPLETE_CERTIFICATE_REFS = '1.2.840.113549.1.9.16.2.21';
const OID_COMPLETE_REVOCATION_REFS = '1.2.840.113549.1.9.16.2.22';

export class PAdESService {
  private certificateChainService: CertificateChainService;
  private timestampService: TimestampService;

  constructor(trustedRootCerts?: string[]) {
    this.certificateChainService = new CertificateChainService(trustedRootCerts);
    this.timestampService = new TimestampService(trustedRootCerts);
  }

  async detectSignatures(pdfData: Uint8Array): Promise<boolean> {
    return hasSignatures(pdfData);
  }

  async extractPAdESSignatures(pdfData: Uint8Array): Promise<PAdESSignatureInfo[]> {
    const signatureFields = await extractSignatureFields(pdfData);
    const results: PAdESSignatureInfo[] = [];

    for (let i = 0; i < signatureFields.length; i++) {
      const field = signatureFields[i];
      const signatureData = getSignatureContent(field);
      const pkcs7Data = parsePKCS7(signatureData);

      if (!pkcs7Data) {
        continue;
      }

      const signerInfo = getSignerInfo(pkcs7Data);
      if (!signerInfo) {
        continue;
      }

      const padesLevel = this.detectPAdESLevel(pkcs7Data);
      const certificateChain = await this.extractCertificatesFromPKCS7(pkcs7Data);
      const signerCert = certificateChain.length > 0 ? certificateChain[0] : null;
      const signingTime = this.extractSigningTime(pkcs7Data);
      const hashAlgorithm = this.extractHashAlgorithm(pkcs7Data);

      results.push({
        signatureIndex: i,
        fieldName: field.name,
        padesLevel,
        byteRange: getByteRange(field),
        signatureData: signatureData.buffer.slice(
          signatureData.byteOffset,
          signatureData.byteOffset + signatureData.byteLength
        ),
        signerCertificate: signerCert,
        certificateChain,
        signingTime,
        hashAlgorithm
      });
    }

    return results;
  }

  async verifyPAdES(
    pdfData: Uint8Array,
    options: VerifyOptions
  ): Promise<PAdESVerificationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    const hasSig = await this.detectSignatures(pdfData);
    if (!hasSig) {
      return {
        hasSignature: false,
        signatureCount: 0,
        signatures: [],
        overallValid: false,
        errors: ['No digital signatures found in PDF document'],
        warnings: []
      };
    }

    if (options.customTrustCerts) {
      this.certificateChainService = new CertificateChainService(options.customTrustCerts);
      this.timestampService = new TimestampService(options.customTrustCerts);
    }

    const signatures = await this.extractPAdESSignatures(pdfData);
    const signatureResults: PAdESSignatureResult[] = [];

    for (const sigInfo of signatures) {
      const sigResult = await this.verifySingleSignature(
        pdfData,
        sigInfo,
        options
      );
      signatureResults.push(sigResult);
    }

    const overallValid = signatureResults.length > 0 && 
      signatureResults.every(r => r.isValid);

    return {
      hasSignature: true,
      signatureCount: signatures.length,
      signatures: signatureResults,
      overallValid,
      errors,
      warnings
    };
  }

  private async verifySingleSignature(
    pdfData: Uint8Array,
    sigInfo: PAdESSignatureInfo,
    options: VerifyOptions
  ): Promise<PAdESSignatureResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    const signatureData = new Uint8Array(sigInfo.signatureData);
    const algorithm = sigInfo.hashAlgorithm as 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512';

    const integrityResult = await verifyIntegrityFromParsedData(
      pdfData,
      signatureData,
      sigInfo.byteRange,
      algorithm
    );

    let certChainResult: CertificateChainResult;
    if (sigInfo.signerCertificate && sigInfo.signerCertificate.pem) {
      const intermediateCerts = sigInfo.certificateChain
        .slice(1)
        .map(c => c.pem || '')
        .filter(p => p);
      
      certChainResult = await this.certificateChainService.buildAndVerifyChain(
        sigInfo.signerCertificate.pem,
        intermediateCerts,
        options.checkRevocation
      );
    } else {
      certChainResult = {
        isValid: false,
        certificates: [],
        trustPath: [],
        revocationStatus: 'unknown',
        errors: ['No signer certificate available for chain verification'],
        warnings: []
      };
    }

    let timestampResult: TimestampResult;
    if (options.checkTimestamp) {
      try {
        timestampResult = await this.timestampService.verifyTimestampFromSignature(
          sigInfo.signatureData,
          integrityResult.documentHash,
          options.customTrustCerts
        );
      } catch {
        timestampResult = {
          hasTimestamp: false,
          isValid: false,
          timestampTime: '',
          timestampAuthority: '',
          certificateChain: [],
          hashAlgorithm: '',
          messageImprint: '',
          errors: ['Timestamp verification failed'],
          warnings: []
        };
      }
    } else {
      timestampResult = {
        hasTimestamp: false,
        isValid: true,
        timestampTime: '',
        timestampAuthority: '',
        certificateChain: [],
        hashAlgorithm: '',
        messageImprint: '',
        errors: [],
        warnings: ['Timestamp verification skipped per options']
      };
    }

    const levelRequirements = this.checkLevelRequirements(
      sigInfo,
      timestampResult,
      certChainResult
    );

    if (!integrityResult.isValid) {
      errors.push(...integrityResult.errors);
    }
    if (!certChainResult.isValid) {
      errors.push(...certChainResult.errors);
    }
    if (options.checkTimestamp && !timestampResult.isValid && timestampResult.hasTimestamp) {
      errors.push(...timestampResult.errors);
    }

    warnings.push(...integrityResult.warnings);
    warnings.push(...certChainResult.warnings);
    warnings.push(...timestampResult.warnings);

    if (!levelRequirements.meetsRequirements) {
      warnings.push(`Signature does not fully meet ${sigInfo.padesLevel} requirements: ${levelRequirements.missingFeatures.join(', ')}`);
    }

    const isValid = errors.length === 0;

    return {
      signatureInfo: sigInfo,
      certificateChain: certChainResult,
      timestamp: timestampResult,
      integrity: integrityResult,
      padesLevel: sigInfo.padesLevel,
      levelRequirements,
      isValid,
      errors,
      warnings
    };
  }

  private detectPAdESLevel(signedData: pkijs.SignedData): PAdESLevel {
    const hasSignedAttrs = signedData.signerInfos?.[0]?.signedAttrs?.attributes || [];
    const hasUnsignedAttrs = signedData.signerInfos?.[0]?.unsignedAttrs?.attributes || [];

    const hasSignaturePolicy = hasSignedAttrs.some((attr: pkijs.Attribute) => attr.type === OID_SIGNATURE_POLICY_ID);
    const hasSignatureTimestamp = hasUnsignedAttrs.some((attr: pkijs.Attribute) => attr.type === OID_SIGNATURE_TIMESTAMP);
    const hasCertificateValues = hasUnsignedAttrs.some((attr: pkijs.Attribute) => attr.type === OID_CERTIFICATE_VALUES);
    const hasRevocationValues = hasUnsignedAttrs.some((attr: pkijs.Attribute) => attr.type === OID_REVOCATION_VALUES);
    const hasCompleteCertRefs = hasUnsignedAttrs.some((attr: pkijs.Attribute) => attr.type === OID_COMPLETE_CERTIFICATE_REFS);
    const hasCompleteRevocationRefs = hasUnsignedAttrs.some((attr: pkijs.Attribute) => attr.type === OID_COMPLETE_REVOCATION_REFS);

    const hasLTVFeatures = hasCertificateValues || hasRevocationValues || hasCompleteCertRefs || hasCompleteRevocationRefs;

    if (hasLTVFeatures) {
      return 'PAdES-LTV';
    }
    if (hasSignatureTimestamp) {
      return 'PAdES-EPES';
    }
    if (hasSignaturePolicy) {
      return 'PAdES-EPES';
    }
    return 'PAdES-BES';
  }

  private checkLevelRequirements(
    sigInfo: PAdESSignatureInfo,
    timestampResult: TimestampResult,
    certChainResult: CertificateChainResult
  ): PAdESLevelRequirements {
    const foundFeatures: string[] = [];
    const missingFeatures: string[] = [];

    foundFeatures.push('PKCS#7 signature container');
    foundFeatures.push('ByteRange defined');
    
    if (sigInfo.signerCertificate) {
      foundFeatures.push('Signer certificate embedded');
    } else {
      missingFeatures.push('Signer certificate not embedded');
    }

    if (sigInfo.certificateChain.length > 1) {
      foundFeatures.push('Certificate chain embedded');
    }

    if (sigInfo.signingTime) {
      foundFeatures.push('Signing time attribute present');
    } else {
      missingFeatures.push('Signing time attribute missing');
    }

    const signedData = parsePKCS7(new Uint8Array(sigInfo.signatureData));
    if (signedData) {
      const signer = signedData.signerInfos?.[0];
      if (signer?.signedAttrs) {
        foundFeatures.push('Signed attributes present');
      } else {
        missingFeatures.push('Signed attributes missing');
      }
    }

    switch (sigInfo.padesLevel) {
      case 'PAdES-BES': {
        if (!sigInfo.signerCertificate) {
          missingFeatures.push('BES requires signer certificate');
        }
        break;
      }
      
      case 'PAdES-EPES': {
        foundFeatures.push('EPES enhancements present');
        if (!timestampResult.hasTimestamp) {
          const hasPolicy = this.hasSignaturePolicyAttribute(signedData);
          if (!hasPolicy) {
            missingFeatures.push('EPES requires either signature policy or timestamp');
          } else {
            foundFeatures.push('Signature policy identifier present');
          }
        } else {
          foundFeatures.push('Signature timestamp present');
        }
        break;
      }
      
      case 'PAdES-LTV': {
        foundFeatures.push('LTV enhancements present');
        const hasLTVData = this.hasLTVAttributes(signedData);
        if (!hasLTVData) {
          missingFeatures.push('LTV requires certificate and revocation validation data');
        } else {
          foundFeatures.push('Certificate validation data embedded');
        }
        if (certChainResult.revocationStatus === 'unknown') {
          missingFeatures.push('Revocation status check unavailable');
        } else if (certChainResult.revocationStatus === 'valid') {
          foundFeatures.push('Revocation status validated');
        }
        break;
      }
    }

    const meetsRequirements = missingFeatures.length === 0;

    return {
      level: sigInfo.padesLevel,
      meetsRequirements,
      missingFeatures,
      foundFeatures
    };
  }

  private hasSignaturePolicyAttribute(signedData: pkijs.SignedData | null): boolean {
    const signedAttrs = signedData?.signerInfos?.[0]?.signedAttrs?.attributes || [];
    return signedAttrs.some((attr: pkijs.Attribute) => attr.type === OID_SIGNATURE_POLICY_ID);
  }

  private hasLTVAttributes(signedData: pkijs.SignedData | null): boolean {
    const unsignedAttrs = signedData?.signerInfos?.[0]?.unsignedAttrs?.attributes || [];
    return unsignedAttrs.some((attr: pkijs.Attribute) => 
      attr.type === OID_CERTIFICATE_VALUES ||
      attr.type === OID_REVOCATION_VALUES ||
      attr.type === OID_COMPLETE_CERTIFICATE_REFS ||
      attr.type === OID_COMPLETE_REVOCATION_REFS
    );
  }

  private async extractCertificatesFromPKCS7(signedData: pkijs.SignedData): Promise<CertificateInfo[]> {
    const certificates: CertificateInfo[] = [];
    
    if (!signedData.certificates) {
      return certificates;
    }

    for (let i = 0; i < signedData.certificates.length; i++) {
      const cert = signedData.certificates[i];
      if (cert instanceof pkijs.Certificate) {
        try {
          const certBuffer = cert.toSchema().toBER(false);
          const parsedCert = parseCertificate(certBuffer);
          if (parsedCert) {
            const pem = this.certificateToPEM(certBuffer);
            const info = await extractCertificateInfo(parsedCert, pem);
            certificates.push(info);
          }
        } catch {
          // ignore parsing errors
        }
      }
    }

    return certificates;
  }

  private extractSigningTime(signedData: pkijs.SignedData): string {
    const signerInfo = signedData.signerInfos?.[0];
    if (!signerInfo?.signedAttrs) return '';

    for (const attr of signerInfo.signedAttrs.attributes) {
      if (attr.type === '1.2.840.113549.1.9.5' && attr.values.length > 0) {
        const value = attr.values[0];
        if (value?.toDate) {
          return value.toDate().toISOString();
        }
      }
    }
    return '';
  }

  private extractHashAlgorithm(signedData: pkijs.SignedData): string {
    const signerInfo = signedData.signerInfos?.[0];
    if (!signerInfo?.digestAlgorithm) return 'SHA256';

    const oidMap: Record<string, string> = {
      '1.3.14.3.2.26': 'SHA1',
      '2.16.840.1.101.3.4.2.1': 'SHA256',
      '2.16.840.1.101.3.4.2.2': 'SHA384',
      '2.16.840.1.101.3.4.2.3': 'SHA512'
    };

    return oidMap[signerInfo.digestAlgorithm.algorithmId] || 'SHA256';
  }

  private certificateToPEM(certBuffer: ArrayBuffer): string {
    const base64 = Buffer.from(certBuffer).toString('base64');
    const lines = base64.match(/.{1,64}/g)?.join('\n') || base64;
    return `-----BEGIN CERTIFICATE-----\n${lines}\n-----END CERTIFICATE-----`;
  }

  async getSignatureSummary(pdfData: Uint8Array): Promise<{
    hasSignature: boolean;
    signatureCount: number;
    levels: PAdESLevel[];
    signers: string[];
  }> {
    const signatures = await this.extractPAdESSignatures(pdfData);
    const levels = [...new Set(signatures.map(s => s.padesLevel))];
    const signers = signatures
      .map(s => s.signerCertificate?.subject || 'Unknown')
      .filter(s => s !== 'Unknown');

    return {
      hasSignature: signatures.length > 0,
      signatureCount: signatures.length,
      levels,
      signers
    };
  }
}
