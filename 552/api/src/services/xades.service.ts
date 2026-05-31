import { calculateHash, parseCertificate } from '../core/crypto-utils';
import { extractCertificateInfo, parseCMS, extractSignerInfo, extractTimestampFromSignedData, verifySignatureValue } from '../core/pki-engine';
import { CertificateChainService } from './certificate-chain.service';
import { TimestampService } from './timestamp.service';
import type {
  CertificateChainResult,
  TimestampResult,
  IntegrityResult,
  CertificateInfo,
  VerifyOptions,
} from '../../../shared';

export type XAdESLevel = 'XAdES-BES' | 'XAdES-EPES' | 'XAdES-LTV';

export interface XAdESSignatureInfo {
  signatureIndex: number;
  signatureId: string;
  xadesLevel: XAdESLevel;
  signatureData: ArrayBuffer;
  signerCertificate: CertificateInfo | null;
  certificateChain: CertificateInfo[];
  signingTime: string;
  hashAlgorithm: string;
  signatureValue: string;
  references: XAdESReference[];
  qualifyingProperties: XAdESQualifyingProperties | null;
}

export interface XAdESReference {
  uri: string;
  digestMethod: string;
  digestValue: string;
  transforms: string[];
}

export interface XAdESQualifyingProperties {
  target: string;
  signedProperties: XAdESSignedProperties | null;
  unsignedProperties: XAdESUnsignedProperties | null;
}

export interface XAdESSignedProperties {
  signingTime?: string;
  signingCertificate?: XAdESSigningCertificate;
  signaturePolicyIdentifier?: XAdESSignaturePolicyIdentifier;
  commitmentTypeIndication?: string[];
  signerRole?: string[];
}

export interface XAdESSigningCertificate {
  certificates: XAdESSigningCertificateRef[];
}

export interface XAdESSigningCertificateRef {
  issuerName: string;
  serialNumber: string;
  digest: string;
  digestMethod: string;
}

export interface XAdESSignaturePolicyIdentifier {
  policyId: string;
  policyHash: string;
  policyHashAlgorithm: string;
}

export interface XAdESUnsignedProperties {
  signatureTimeStamp?: XAdESTimestamp[];
  completeCertificateRefs?: XAdESCertificateRef[];
  completeRevocationRefs?: XAdESRevocationRef[];
  certificateValues?: XAdESCertificateValue[];
  revocationValues?: XAdESRevocationValue[];
}

export interface XAdESTimestamp {
  timestampData: ArrayBuffer;
  hashAlgorithm: string;
  messageImprint: string;
}

export interface XAdESCertificateRef {
  issuerName: string;
  serialNumber: string;
  digest: string;
  digestMethod: string;
}

export interface XAdESRevocationRef {
  type: 'CRL' | 'OCSP';
  issuerName: string;
  serialNumber?: string;
  digest: string;
  digestMethod: string;
}

export interface XAdESCertificateValue {
  certificateData: ArrayBuffer;
  certificateInfo: CertificateInfo | null;
}

export interface XAdESRevocationValue {
  type: 'CRL' | 'OCSP';
  revocationData: ArrayBuffer;
}

export interface XAdESVerificationResult {
  hasSignature: boolean;
  signatureCount: number;
  signatures: XAdESSignatureResult[];
  overallValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface XAdESSignatureResult {
  signatureInfo: XAdESSignatureInfo;
  certificateChain: CertificateChainResult;
  timestamp: TimestampResult;
  integrity: IntegrityResult;
  xadesLevel: XAdESLevel;
  levelRequirements: XAdESLevelRequirements;
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface XAdESLevelRequirements {
  level: XAdESLevel;
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

const DS_NAMESPACE = 'http://www.w3.org/2000/09/xmldsig#';
const XADES_NAMESPACE = 'http://uri.etsi.org/01903/v1.3.2#';

export class XAdESService {
  private certificateChainService: CertificateChainService;
  private timestampService: TimestampService;

  constructor(trustedRootCerts?: string[]) {
    this.certificateChainService = new CertificateChainService(trustedRootCerts);
    this.timestampService = new TimestampService(trustedRootCerts);
  }

  async detectSignatures(xmlData: Uint8Array): Promise<boolean> {
    try {
      const parser = new DOMParser();
      const xmlString = new TextDecoder().decode(xmlData);
      const doc = parser.parseFromString(xmlString, 'application/xml');
      const signatures = doc.getElementsByTagNameNS(DS_NAMESPACE, 'Signature');
      return signatures.length > 0;
    } catch {
      return false;
    }
  }

  async extractXAdESSignatures(xmlData: Uint8Array): Promise<XAdESSignatureInfo[]> {
    const results: XAdESSignatureInfo[] = [];

    try {
      const parser = new DOMParser();
      const xmlString = new TextDecoder().decode(xmlData);
      const doc = parser.parseFromString(xmlString, 'application/xml');
      const signatures = doc.getElementsByTagNameNS(DS_NAMESPACE, 'Signature');

      for (let i = 0; i < signatures.length; i++) {
        const signature = signatures[i];
        const signatureId = signature.getAttribute('Id') || `signature-${i}`;

        const signatureInfo = await this.parseSignatureElement(signature, xmlData, i);
        if (signatureInfo) {
          results.push(signatureInfo);
        }
      }
    } catch {
    }

    return results;
  }

  private async parseSignatureElement(
    signatureElement: Element,
    xmlData: Uint8Array,
    index: number
  ): Promise<XAdESSignatureInfo | null> {
    try {
      const references = this.extractReferences(signatureElement);
      const signatureValue = this.extractSignatureValue(signatureElement);
      const keyInfo = this.extractKeyInfo(signatureElement);
      const qualifyingProperties = await this.extractQualifyingProperties(signatureElement);
      const hashAlgorithm = this.extractHashAlgorithm(signatureElement);
      const signingTime = this.extractSigningTime(signatureElement, qualifyingProperties);

      const { signerCertificate, certificateChain, signatureData } = await this.extractCertificates(
        signatureElement,
        keyInfo
      );

      const xadesLevel = this.detectXAdESLevel(signatureElement, qualifyingProperties);

      return {
        signatureIndex: index,
        signatureId: signatureElement.getAttribute('Id') || `signature-${index}`,
        xadesLevel,
        signatureData,
        signerCertificate,
        certificateChain,
        signingTime,
        hashAlgorithm,
        signatureValue,
        references,
        qualifyingProperties,
      };
    } catch {
      return null;
    }
  }

  private extractReferences(signatureElement: Element): XAdESReference[] {
    const references: XAdESReference[] = [];
    const signedInfo = signatureElement.getElementsByTagNameNS(DS_NAMESPACE, 'SignedInfo')[0];
    if (!signedInfo) return references;

    const refElements = signedInfo.getElementsByTagNameNS(DS_NAMESPACE, 'Reference');
    for (let i = 0; i < refElements.length; i++) {
      const ref = refElements[i];
      const uri = ref.getAttribute('URI') || '';
      const transforms: string[] = [];

      const transformElements = ref.getElementsByTagNameNS(DS_NAMESPACE, 'Transform');
      for (let j = 0; j < transformElements.length; j++) {
        const algorithm = transformElements[j].getAttribute('Algorithm') || '';
        transforms.push(algorithm);
      }

      const digestMethod = ref.getElementsByTagNameNS(DS_NAMESPACE, 'DigestMethod')[0]?.getAttribute('Algorithm') || '';
      const digestValue = ref.getElementsByTagNameNS(DS_NAMESPACE, 'DigestValue')[0]?.textContent || '';

      references.push({
        uri,
        digestMethod,
        digestValue,
        transforms,
      });
    }

    return references;
  }

  private extractSignatureValue(signatureElement: Element): string {
    return signatureElement.getElementsByTagNameNS(DS_NAMESPACE, 'SignatureValue')[0]?.textContent || '';
  }

  private extractKeyInfo(signatureElement: Element): Element | null {
    return signatureElement.getElementsByTagNameNS(DS_NAMESPACE, 'KeyInfo')[0] || null;
  }

  private async extractQualifyingProperties(signatureElement: Element): Promise<XAdESQualifyingProperties | null> {
    const qualifyingProperties = signatureElement.getElementsByTagNameNS(XADES_NAMESPACE, 'QualifyingProperties')[0];
    if (!qualifyingProperties) return null;

    const target = qualifyingProperties.getAttribute('Target') || '';
    const signedProperties = this.extractSignedProperties(qualifyingProperties);
    const unsignedProperties = await this.extractUnsignedProperties(qualifyingProperties);

    return {
      target,
      signedProperties,
      unsignedProperties,
    };
  }

  private extractSignedProperties(qualifyingProperties: Element): XAdESSignedProperties | null {
    const signedProperties = qualifyingProperties.getElementsByTagNameNS(XADES_NAMESPACE, 'SignedProperties')[0];
    if (!signedProperties) return null;

    const result: XAdESSignedProperties = {};

    const signingTime = signedProperties.getElementsByTagNameNS(XADES_NAMESPACE, 'SigningTime')[0];
    if (signingTime && signingTime.textContent) {
      result.signingTime = new Date(signingTime.textContent).toISOString();
    }

    const signingCertificate = this.extractSigningCertificate(signedProperties);
    if (signingCertificate) {
      result.signingCertificate = signingCertificate;
    }

    const signaturePolicy = this.extractSignaturePolicyIdentifier(signedProperties);
    if (signaturePolicy) {
      result.signaturePolicyIdentifier = signaturePolicy;
    }

    return Object.keys(result).length > 0 ? result : null;
  }

  private extractSigningCertificate(signedProperties: Element): XAdESSigningCertificate | null {
    const signingCertificate = signedProperties.getElementsByTagNameNS(XADES_NAMESPACE, 'SigningCertificate')[0];
    if (!signingCertificate) return null;

    const certs: XAdESSigningCertificateRef[] = [];
    const certElements = signingCertificate.getElementsByTagNameNS(XADES_NAMESPACE, 'Cert');

    for (let i = 0; i < certElements.length; i++) {
      const cert = certElements[i];
      const issuerName = cert.getElementsByTagNameNS(XADES_NAMESPACE, 'X509IssuerName')[0]?.textContent || '';
      const serialNumber = cert.getElementsByTagNameNS(XADES_NAMESPACE, 'X509SerialNumber')[0]?.textContent || '';
      const digest = cert.getElementsByTagNameNS(XADES_NAMESPACE, 'DigestValue')[0]?.textContent || '';
      const digestMethod = cert.getElementsByTagNameNS(DS_NAMESPACE, 'DigestMethod')[0]?.getAttribute('Algorithm') || '';

      certs.push({
        issuerName,
        serialNumber,
        digest,
        digestMethod,
      });
    }

    return certs.length > 0 ? { certificates: certs } : null;
  }

  private extractSignaturePolicyIdentifier(signedProperties: Element): XAdESSignaturePolicyIdentifier | null {
    const signaturePolicyId = signedProperties.getElementsByTagNameNS(
      XADES_NAMESPACE,
      'SignaturePolicyIdentifier'
    )[0];
    if (!signaturePolicyId) return null;

    const policyId = signaturePolicyId.getElementsByTagNameNS(XADES_NAMESPACE, 'Identifier')[0]?.textContent || '';
    const policyHash = signaturePolicyId.getElementsByTagNameNS(XADES_NAMESPACE, 'DigestValue')[0]?.textContent || '';
    const policyHashAlgorithm =
      signaturePolicyId.getElementsByTagNameNS(DS_NAMESPACE, 'DigestMethod')[0]?.getAttribute('Algorithm') || '';

    return {
      policyId,
      policyHash,
      policyHashAlgorithm,
    };
  }

  private async extractUnsignedProperties(qualifyingProperties: Element): Promise<XAdESUnsignedProperties | null> {
    const unsignedProperties = qualifyingProperties.getElementsByTagNameNS(XADES_NAMESPACE, 'UnsignedProperties')[0];
    if (!unsignedProperties) return null;

    const result: XAdESUnsignedProperties = {};

    const timestamps = this.extractSignatureTimestamps(unsignedProperties);
    if (timestamps.length > 0) {
      result.signatureTimeStamp = timestamps;
    }

    const certValues = await this.extractCertificateValues(unsignedProperties);
    if (certValues.length > 0) {
      result.certificateValues = certValues;
    }

    return Object.keys(result).length > 0 ? result : null;
  }

  private extractSignatureTimestamps(unsignedProperties: Element): XAdESTimestamp[] {
    const timestamps: XAdESTimestamp[] = [];
    const timestampElements = unsignedProperties.getElementsByTagNameNS(XADES_NAMESPACE, 'SignatureTimeStamp');

    for (let i = 0; i < timestampElements.length; i++) {
      const ts = timestampElements[i];
      const encapTs = ts.getElementsByTagNameNS(XADES_NAMESPACE, 'EncapsulatedTimeStamp')[0];
      if (encapTs && encapTs.textContent) {
        try {
          const binaryData = Uint8Array.from(atob(encapTs.textContent), (c) => c.charCodeAt(0));
          const hashAlgorithm = ts.getElementsByTagNameNS(DS_NAMESPACE, 'DigestMethod')[0]?.getAttribute('Algorithm') || '';
          const messageImprint = ts.getElementsByTagNameNS(DS_NAMESPACE, 'DigestValue')[0]?.textContent || '';

          timestamps.push({
            timestampData: binaryData.buffer,
            hashAlgorithm,
            messageImprint,
          });
        } catch {
        }
      }
    }

    return timestamps;
  }

  private async extractCertificateValues(unsignedProperties: Element): Promise<XAdESCertificateValue[]> {
    const certValues: XAdESCertificateValue[] = [];
    const certificateValues = unsignedProperties.getElementsByTagNameNS(XADES_NAMESPACE, 'CertificateValues')[0];
    if (!certificateValues) return certValues;

    const encapCerts = certificateValues.getElementsByTagNameNS(XADES_NAMESPACE, 'EncapsulatedX509Certificate');
    for (let i = 0; i < encapCerts.length; i++) {
      const encapCert = encapCerts[i];
      if (encapCert.textContent) {
        try {
          const binaryData = Uint8Array.from(atob(encapCert.textContent), (c) => c.charCodeAt(0));
          const parsedCert = parseCertificate(binaryData.buffer);
          let certInfo: CertificateInfo | null = null;

          if (parsedCert) {
            const pem = this.certificateToPEM(binaryData.buffer);
            certInfo = await extractCertificateInfo(parsedCert, pem);
          }

          certValues.push({
            certificateData: binaryData.buffer,
            certificateInfo: certInfo,
          });
        } catch {
        }
      }
    }

    return certValues;
  }

  private extractHashAlgorithm(signatureElement: Element): string {
    const signedInfo = signatureElement.getElementsByTagNameNS(DS_NAMESPACE, 'SignedInfo')[0];
    if (!signedInfo) return 'SHA256';

    const reference = signedInfo.getElementsByTagNameNS(DS_NAMESPACE, 'Reference')[0];
    if (!reference) return 'SHA256';

    const digestMethod = reference.getElementsByTagNameNS(DS_NAMESPACE, 'DigestMethod')[0];
    if (!digestMethod) return 'SHA256';

    const algorithm = digestMethod.getAttribute('Algorithm') || '';
    const oidMap: Record<string, string> = {
      'http://www.w3.org/2000/09/xmldsig#sha1': 'SHA1',
      'http://www.w3.org/2001/04/xmlenc#sha256': 'SHA256',
      'http://www.w3.org/2001/04/xmldsig-more#sha384': 'SHA384',
      'http://www.w3.org/2001/04/xmlenc#sha512': 'SHA512',
    };

    return oidMap[algorithm] || 'SHA256';
  }

  private extractSigningTime(
    signatureElement: Element,
    qualifyingProperties: XAdESQualifyingProperties | null
  ): string {
    if (qualifyingProperties?.signedProperties?.signingTime) {
      return qualifyingProperties.signedProperties.signingTime;
    }
    return '';
  }

  private async extractCertificates(
    signatureElement: Element,
    keyInfo: Element | null
  ): Promise<{
    signerCertificate: CertificateInfo | null;
    certificateChain: CertificateInfo[];
    signatureData: ArrayBuffer;
  }> {
    const certificates: CertificateInfo[] = [];
    let signerCertificate: CertificateInfo | null = null;
    let signatureData = new ArrayBuffer(0);

    if (keyInfo) {
      const x509Data = keyInfo.getElementsByTagNameNS(DS_NAMESPACE, 'X509Data')[0];
      if (x509Data) {
        const x509Certificates = x509Data.getElementsByTagNameNS(DS_NAMESPACE, 'X509Certificate');
        for (let i = 0; i < x509Certificates.length; i++) {
          const certElement = x509Certificates[i];
          if (certElement.textContent) {
            try {
              const binaryData = Uint8Array.from(atob(certElement.textContent), (c) => c.charCodeAt(0));
              const parsedCert = parseCertificate(binaryData.buffer);
              if (parsedCert) {
                const pem = this.certificateToPEM(binaryData.buffer);
                const info = await extractCertificateInfo(parsedCert, pem);
                certificates.push(info);

                if (i === 0) {
                  signerCertificate = info;
                }
              }
            } catch {
            }
          }
        }
      }
    }

    try {
      const signatureValue = this.extractSignatureValue(signatureElement);
      if (signatureValue) {
        signatureData = Uint8Array.from(atob(signatureValue), (c) => c.charCodeAt(0)).buffer;
      }
    } catch {
    }

    return {
      signerCertificate,
      certificateChain: certificates,
      signatureData,
    };
  }

  private detectXAdESLevel(
    signatureElement: Element,
    qualifyingProperties: XAdESQualifyingProperties | null
  ): XAdESLevel {
    if (!qualifyingProperties) {
      return 'XAdES-BES';
    }

    const signedProps = qualifyingProperties.signedProperties;
    const unsignedProps = qualifyingProperties.unsignedProperties;

    const hasSignaturePolicy = !!signedProps?.signaturePolicyIdentifier;
    const hasSignatureTimestamp = !!unsignedProps?.signatureTimeStamp && unsignedProps.signatureTimeStamp.length > 0;
    const hasCertificateValues = !!unsignedProps?.certificateValues && unsignedProps.certificateValues.length > 0;
    const hasRevocationValues = !!unsignedProps?.revocationValues && unsignedProps.revocationValues.length > 0;
    const hasCompleteCertRefs = !!unsignedProps?.completeCertificateRefs && unsignedProps.completeCertificateRefs.length > 0;
    const hasCompleteRevocationRefs =
      !!unsignedProps?.completeRevocationRefs && unsignedProps.completeRevocationRefs.length > 0;

    const hasLTVFeatures =
      hasCertificateValues || hasRevocationValues || hasCompleteCertRefs || hasCompleteRevocationRefs;

    if (hasLTVFeatures) {
      return 'XAdES-LTV';
    }
    if (hasSignatureTimestamp || hasSignaturePolicy) {
      return 'XAdES-EPES';
    }
    return 'XAdES-BES';
  }

  async verifyXAdES(
    xmlData: Uint8Array,
    options: VerifyOptions
  ): Promise<XAdESVerificationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    const hasSig = await this.detectSignatures(xmlData);
    if (!hasSig) {
      return {
        hasSignature: false,
        signatureCount: 0,
        signatures: [],
        overallValid: false,
        errors: ['No digital signatures found in XML document'],
        warnings: [],
      };
    }

    if (options.customTrustCerts) {
      this.certificateChainService = new CertificateChainService(options.customTrustCerts);
      this.timestampService = new TimestampService(options.customTrustCerts);
    }

    const signatures = await this.extractXAdESSignatures(xmlData);
    const signatureResults: XAdESSignatureResult[] = [];

    for (const sigInfo of signatures) {
      const sigResult = await this.verifySingleSignature(xmlData, sigInfo, options);
      signatureResults.push(sigResult);
    }

    const overallValid = signatureResults.length > 0 && signatureResults.every((r) => r.isValid);

    return {
      hasSignature: true,
      signatureCount: signatures.length,
      signatures: signatureResults,
      overallValid,
      errors,
      warnings,
    };
  }

  private async verifySingleSignature(
    xmlData: Uint8Array,
    sigInfo: XAdESSignatureInfo,
    options: VerifyOptions
  ): Promise<XAdESSignatureResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    const integrityResult = await this.verifyDocumentIntegrity(xmlData, sigInfo);

    let certChainResult: CertificateChainResult;
    if (sigInfo.signerCertificate && sigInfo.signerCertificate.pem) {
      const intermediateCerts = sigInfo.certificateChain
        .slice(1)
        .map((c) => c.pem || '')
        .filter((p) => p);

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
        warnings: [],
      };
    }

    let timestampResult: TimestampResult;
    if (options.checkTimestamp) {
      try {
        const timestampData = sigInfo.qualifyingProperties?.unsignedProperties?.signatureTimeStamp?.[0]?.timestampData;
        if (timestampData) {
          timestampResult = await this.timestampService.verifyTimestampToken(
            timestampData,
            integrityResult.documentHash,
            sigInfo.certificateChain,
            options.customTrustCerts
          );
        } else {
          timestampResult = await this.timestampService.verifyTimestampFromSignature(
            sigInfo.signatureData,
            integrityResult.documentHash,
            options.customTrustCerts
          );
        }
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
          warnings: [],
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
        warnings: ['Timestamp verification skipped per options'],
      };
    }

    const levelRequirements = this.checkLevelRequirements(
      sigInfo,
      timestampResult,
      certChainResult,
      integrityResult
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
      warnings.push(
        `Signature does not fully meet ${sigInfo.xadesLevel} requirements: ${levelRequirements.missingFeatures.join(', ')}`
      );
    }

    const isValid = errors.length === 0;

    return {
      signatureInfo: sigInfo,
      certificateChain: certChainResult,
      timestamp: timestampResult,
      integrity: integrityResult,
      xadesLevel: sigInfo.xadesLevel,
      levelRequirements,
      isValid,
      errors,
      warnings,
    };
  }

  private async verifyDocumentIntegrity(
    xmlData: Uint8Array,
    sigInfo: XAdESSignatureInfo
  ): Promise<IntegrityResult> {
    const errors: string[] = [];
    const warnings: string[] = [];
    let documentHash = '';
    let signedHash = '';
    let hashMatch = false;
    let hasModifications = false;

    try {
      const algorithm = sigInfo.hashAlgorithm as 'SHA1' | 'SHA256' | 'SHA384' | 'SHA512';
      const reference = sigInfo.references[0];

      if (reference) {
        const referencedData = await this.getReferencedData(xmlData, reference);
        documentHash = calculateHash(referencedData, algorithm);
        signedHash = this.base64ToHex(reference.digestValue);
        hashMatch = documentHash.toLowerCase() === signedHash.toLowerCase();
        hasModifications = !hashMatch;
      } else {
        documentHash = calculateHash(xmlData, algorithm);
        signedHash = '';
        hashMatch = false;
        hasModifications = false;
        errors.push('No reference found in signature');
      }

      let signatureValid = false;
      try {
        const signedData = parseCMS(sigInfo.signatureData);
        const signerInfos = await extractSignerInfo(signedData);
        if (signerInfos.length > 0 && signedData.signerInfos.length > 0) {
          signatureValid = await verifySignatureValue(signedData.signerInfos[0], signedData);
        }
      } catch {
        try {
          const timestampData = sigInfo.qualifyingProperties?.unsignedProperties?.signatureTimeStamp?.[0]?.timestampData;
          if (timestampData) {
            const signedData = parseCMS(timestampData);
            if (signedData.signerInfos.length > 0) {
              signatureValid = await verifySignatureValue(signedData.signerInfos[0], signedData);
            }
          }
        } catch {
        }
      }

      if (!signatureValid) {
        errors.push('Signature value verification failed');
      }

      if (algorithm === 'SHA1') {
        warnings.push('SHA1 algorithm is considered weak, consider using SHA256 or stronger');
      }
    } catch (e) {
      errors.push(`Integrity verification failed: ${e}`);
    }

    return {
      isValid: hashMatch && errors.length === 0,
      documentHash,
      signedHash,
      hashMatch,
      signatureAlgorithm: sigInfo.hashAlgorithm,
      signingTime: sigInfo.signingTime,
      hasModifications,
      errors,
      warnings,
    };
  }

  private async getReferencedData(xmlData: Uint8Array, reference: XAdESReference): Promise<Uint8Array> {
    if (reference.uri === '' || reference.uri === '#xpointer(/)') {
      return xmlData;
    }

    if (reference.uri.startsWith('#')) {
      const elementId = reference.uri.substring(1);
      const parser = new DOMParser();
      const xmlString = new TextDecoder().decode(xmlData);
      const doc = parser.parseFromString(xmlString, 'application/xml');
      const element = doc.getElementById(elementId) || doc.querySelector(`[Id="${elementId}"]`);

      if (element) {
        const serializer = new XMLSerializer();
        const elementXml = serializer.serializeToString(element);
        return new TextEncoder().encode(elementXml);
      }
    }

    return xmlData;
  }

  private base64ToHex(base64: string): string {
    try {
      const binaryString = atob(base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      return Array.from(bytes)
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('');
    } catch {
      return '';
    }
  }

  private checkLevelRequirements(
    sigInfo: XAdESSignatureInfo,
    timestampResult: TimestampResult,
    certChainResult: CertificateChainResult,
    integrityResult: IntegrityResult
  ): XAdESLevelRequirements {
    const foundFeatures: string[] = [];
    const missingFeatures: string[] = [];

    foundFeatures.push('XML DSIG signature container');
    foundFeatures.push('References defined');

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

    if (sigInfo.qualifyingProperties) {
      foundFeatures.push('XAdES QualifyingProperties present');
    } else {
      missingFeatures.push('XAdES QualifyingProperties missing');
    }

    switch (sigInfo.xadesLevel) {
      case 'XAdES-BES':
        if (!sigInfo.signerCertificate) {
          missingFeatures.push('BES requires signer certificate');
        }
        if (!sigInfo.qualifyingProperties?.signedProperties) {
          missingFeatures.push('BES requires SignedProperties');
        }
        break;

      case 'XAdES-EPES':
        foundFeatures.push('EPES enhancements present');
        if (!timestampResult.hasTimestamp) {
          const hasPolicy = !!sigInfo.qualifyingProperties?.signedProperties?.signaturePolicyIdentifier;
          if (!hasPolicy) {
            missingFeatures.push('EPES requires either signature policy or timestamp');
          } else {
            foundFeatures.push('Signature policy identifier present');
          }
        } else {
          foundFeatures.push('Signature timestamp present');
        }
        break;

      case 'XAdES-LTV':
        foundFeatures.push('LTV enhancements present');
        const hasLTVData = this.hasLTVAttributes(sigInfo.qualifyingProperties);
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

    const meetsRequirements = missingFeatures.length === 0;

    return {
      level: sigInfo.xadesLevel,
      meetsRequirements,
      missingFeatures,
      foundFeatures,
    };
  }

  private hasLTVAttributes(qualifyingProperties: XAdESQualifyingProperties | null): boolean {
    if (!qualifyingProperties?.unsignedProperties) return false;

    const unsignedProps = qualifyingProperties.unsignedProperties;
    return (
      (unsignedProps.certificateValues && unsignedProps.certificateValues.length > 0) ||
      (unsignedProps.revocationValues && unsignedProps.revocationValues.length > 0) ||
      (unsignedProps.completeCertificateRefs && unsignedProps.completeCertificateRefs.length > 0) ||
      (unsignedProps.completeRevocationRefs && unsignedProps.completeRevocationRefs.length > 0)
    );
  }

  private certificateToPEM(certBuffer: ArrayBuffer): string {
    const base64 = Buffer.from(certBuffer).toString('base64');
    const lines = base64.match(/.{1,64}/g)?.join('\n') || base64;
    return `-----BEGIN CERTIFICATE-----\n${lines}\n-----END CERTIFICATE-----`;
  }

  async getSignatureSummary(xmlData: Uint8Array): Promise<{
    hasSignature: boolean;
    signatureCount: number;
    levels: XAdESLevel[];
    signers: string[];
  }> {
    const signatures = await this.extractXAdESSignatures(xmlData);
    const levels = [...new Set(signatures.map((s) => s.xadesLevel))];
    const signers = signatures
      .map((s) => s.signerCertificate?.subject || 'Unknown')
      .filter((s) => s !== 'Unknown');

    return {
      hasSignature: signatures.length > 0,
      signatureCount: signatures.length,
      levels,
      signers,
    };
  }
}
