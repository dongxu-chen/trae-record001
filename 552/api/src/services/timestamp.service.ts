import { parseTimestampToken, extractTimestampFromSignedData, parseCMS } from '../core/pki-engine';
import { CertificateChainService } from '../services/certificate-chain.service';
import { TimestampResult, CertificateInfo } from '../../../shared';
import * as pkijs from 'pkijs';

export class TimestampService {
  private certificateChainService: CertificateChainService;

  constructor(trustedRootCerts?: string[]) {
    this.certificateChainService = new CertificateChainService(trustedRootCerts);
  }

  async verifyTimestampFromSignature(
    signatureData: ArrayBuffer,
    documentHash: string,
    trustedRootCerts?: string[]
  ): Promise<TimestampResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (trustedRootCerts) {
      this.certificateChainService = new CertificateChainService(trustedRootCerts);
    }

    let signedData: pkijs.SignedData;
    try {
      signedData = parseCMS(signatureData);
    } catch {
      return {
        hasTimestamp: false,
        isValid: false,
        timestampTime: '',
        timestampAuthority: '',
        certificateChain: [],
        hashAlgorithm: '',
        messageImprint: '',
        errors: ['Failed to parse signature data'],
        warnings: [],
      };
    }

    let timestampTokenData: ArrayBuffer | null = null;
    const OID_TIMESTAMP_TOKEN = '1.2.840.113549.1.9.16.1.4';
    
    for (const signer of signedData.signerInfos) {
      if (signer.unsignedAttrs) {
        for (const attr of signer.unsignedAttrs.attributes) {
          if (attr.type === OID_TIMESTAMP_TOKEN && attr.values.length > 0) {
            const tsValue = attr.values[0] as any;
            timestampTokenData = tsValue.valueBlock.valueHexView;
            break;
          }
        }
      }
    }

    if (!timestampTokenData) {
      return {
        hasTimestamp: false,
        isValid: false,
        timestampTime: '',
        timestampAuthority: '',
        certificateChain: [],
        hashAlgorithm: '',
        messageImprint: '',
        errors: ['No timestamp token found in signature'],
        warnings: [],
      };
    }

    return this.verifyTimestampToken(timestampTokenData, documentHash, [], trustedRootCerts);
  }

  async verifyTimestampToken(
    timestampTokenData: ArrayBuffer,
    documentHash: string,
    additionalCerts: CertificateInfo[] = [],
    trustedRootCerts?: string[]
  ): Promise<TimestampResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (trustedRootCerts) {
      this.certificateChainService = new CertificateChainService(trustedRootCerts);
    }

    const timestampResult = await parseTimestampToken(timestampTokenData);

    if (!timestampResult.hasTimestamp) {
      return {
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
    }

    if (!timestampResult.isValid) {
      errors.push('Timestamp token signature verification failed');
    }

    if (timestampResult.messageImprint && documentHash) {
      const normalizedImprint = timestampResult.messageImprint.replace(/:/g, '').toUpperCase();
      const normalizedDocumentHash = documentHash.replace(/:/g, '').toUpperCase();
      if (normalizedImprint !== normalizedDocumentHash) {
        errors.push('Message imprint does not match document hash');
      }
    } else if (!timestampResult.messageImprint) {
      errors.push('No message imprint found in timestamp token');
    }

    if (timestampResult.timestampTime) {
      const timestampDate = new Date(timestampResult.timestampTime);
      const nowUTC = new Date();
      if (timestampDate.getTime() > nowUTC.getTime()) {
        errors.push('Timestamp time is in the future');
      }
    }

    let certificateChain: CertificateInfo[] = timestampResult.certificateChain;
    if (certificateChain.length === 0 && additionalCerts.length > 0) {
      certificateChain = additionalCerts;
    }

    if (certificateChain.length > 0) {
      const endEntityCert = certificateChain[0];
      const intermediateCerts = certificateChain.slice(1).map(c => c.pem || '');
      
      if (endEntityCert.pem) {
        const chainResult = await this.certificateChainService.buildAndVerifyChain(
          endEntityCert.pem,
          intermediateCerts,
          false
        );

        if (!chainResult.isValid) {
          errors.push(...chainResult.errors);
        }
        warnings.push(...chainResult.warnings);
      }
    } else {
      warnings.push('No certificates found in timestamp token for chain verification');
    }

    const isValid = errors.length === 0 && timestampResult.isValid;

    return {
      hasTimestamp: true,
      isValid,
      timestampTime: timestampResult.timestampTime || '',
      timestampAuthority: timestampResult.timestampAuthority || '',
      certificateChain,
      hashAlgorithm: timestampResult.hashAlgorithm || '',
      messageImprint: timestampResult.messageImprint || '',
      errors,
      warnings,
    };
  }

  async extractTimestampInfo(
    timestampTokenData: ArrayBuffer
  ): Promise<TimestampResult> {
    const timestampResult = await parseTimestampToken(timestampTokenData);

    if (!timestampResult.hasTimestamp) {
      return {
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
    }

    return {
      hasTimestamp: true,
      isValid: timestampResult.isValid,
      timestampTime: timestampResult.timestampTime || '',
      timestampAuthority: timestampResult.timestampAuthority || '',
      certificateChain: timestampResult.certificateChain,
      hashAlgorithm: timestampResult.hashAlgorithm || '',
      messageImprint: timestampResult.messageImprint || '',
      errors: [],
      warnings: [],
    };
  }
}
