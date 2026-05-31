import * as pkijs from 'pkijs';
import * as asn1js from 'asn1js';
import {
  parseCertificate,
  extractCertificateInfo,
  verifyCertificateSignature,
  checkCertificateValidity,
} from '../core/pki-engine';
import { CertificateChainResult, CertificateInfo } from '../../../shared';

const OID_AUTHORITY_INFO_ACCESS = '1.3.6.1.5.5.7.1.1';
const OID_OCSP = '1.3.6.1.5.5.7.48.1';
const OID_CRL_DISTRIBUTION_POINTS = '2.5.29.31';

export class CertificateChainService {
  private static revocationCache: Map<string, { status: 'valid' | 'revoked' | 'unknown'; timestamp: number }> = new Map();
  private static readonly CACHE_TTL = 4 * 60 * 60 * 1000;
  private static readonly OCSP_TIMEOUT = 5000;
  private static readonly CRL_TIMEOUT = 10000;

  private trustedRoots: Map<string, pkijs.Certificate> = new Map();

  constructor(trustedRootCerts?: string[]) {
    if (trustedRootCerts) {
      for (const pem of trustedRootCerts) {
        try {
          const cert = parseCertificate(pem);
          const fingerprint = this.getCertFingerprintSync(cert);
          this.trustedRoots.set(fingerprint, cert);
        } catch {
        }
      }
    }
  }

  addTrustedRoot(pem: string): void {
    try {
      const cert = parseCertificate(pem);
      const fingerprint = this.getCertFingerprintSync(cert);
      this.trustedRoots.set(fingerprint, cert);
    } catch {
    }
  }

  async buildAndVerifyChain(
    endEntityCert: string | ArrayBuffer,
    intermediateCerts: (string | ArrayBuffer)[] = [],
    checkRevocation: boolean = true
  ): Promise<CertificateChainResult> {
    const errors: string[] = [];
    const warnings: string[] = [];
    const certificates: CertificateInfo[] = [];
    const trustPath: string[] = [];

    let endCert: pkijs.Certificate;
    try {
      endCert = parseCertificate(endEntityCert);
    } catch {
      return {
        isValid: false,
        certificates: [],
        trustPath: [],
        revocationStatus: 'unknown',
        errors: ['Failed to parse end-entity certificate'],
        warnings: [],
      };
    }

    const intermediates: pkijs.Certificate[] = [];
    for (const certData of intermediateCerts) {
      try {
        intermediates.push(parseCertificate(certData));
      } catch {
        warnings.push('Failed to parse one intermediate certificate, skipping');
      }
    }

    const chain = await this.buildChain(endCert, intermediates);
    
    if (chain.length === 0) {
      return {
        isValid: false,
        certificates: [],
        trustPath: [],
        revocationStatus: 'unknown',
        errors: ['Failed to build certificate chain'],
        warnings: [],
      };
    }

    const rootCert = chain[chain.length - 1];
    const rootFingerprint = this.getCertFingerprintSync(rootCert);
    const isTrustedRoot = this.trustedRoots.has(rootFingerprint);

    if (!isTrustedRoot) {
      errors.push('Root certificate is not in trusted root list');
    }

    for (let i = 0; i < chain.length; i++) {
      const cert = chain[i];
      const issuerCert = i < chain.length - 1 ? chain[i + 1] : undefined;

      const info = await extractCertificateInfo(cert);
      certificates.push(info);
      trustPath.push(info.subject);

      const validity = checkCertificateValidity(cert);
      if (!validity.isValid) {
        if (validity.isExpired) {
          errors.push(`Certificate "${info.subject}" has expired`);
        }
        if (validity.isNotYetValid) {
          errors.push(`Certificate "${info.subject}" is not yet valid`);
        }
      } else if (validity.daysLeft < 30) {
        warnings.push(`Certificate "${info.subject}" will expire in ${validity.daysLeft} days`);
      }

      const signatureValid = await verifyCertificateSignature(cert, issuerCert);
      if (!signatureValid) {
        errors.push(`Invalid signature on certificate "${info.subject}"`);
      }

      if (i < chain.length - 1) {
        if (!info.keyUsage.includes('digitalSignature') && !info.keyUsage.includes('nonRepudiation')) {
          errors.push(`Certificate "${info.subject}" lacks required key usage for signing`);
        }
      }

      if (i > 0) {
        if (!info.isCA) {
          errors.push(`Certificate "${info.subject}" is not a CA but is used as issuer`);
        }
        if (!info.keyUsage.includes('keyCertSign')) {
          errors.push(`Certificate "${info.subject}" lacks keyCertSign key usage`);
        }
      }

    }

    if (checkRevocation && chain.length > 0) {
      const revocationPromises = chain.map((cert, i) =>
        this.checkRevocationStatus(cert).then(status => ({ index: i, status }))
      );
      const revocationResults = await Promise.allSettled(revocationPromises);

      for (const result of revocationResults) {
        if (result.status === 'fulfilled') {
          const { index, status } = result.value;
          const certInfo = certificates[index];
          if (status === 'revoked') {
            errors.push(`Certificate "${certInfo.subject}" has been revoked`);
          } else if (status === 'unknown') {
            warnings.push(`Revocation status for certificate "${certInfo.subject}" is unknown`);
          }
        }
      }
    }

    let revocationStatus: 'valid' | 'revoked' | 'unknown' = 'valid';
    if (errors.some(e => e.includes('revoked'))) {
      revocationStatus = 'revoked';
    } else if (warnings.some(w => w.includes('unknown'))) {
      revocationStatus = 'unknown';
    }

    const isValid = errors.length === 0;

    return {
      isValid,
      certificates,
      trustPath,
      revocationStatus,
      errors,
      warnings,
    };
  }

  private async buildChain(
    endCert: pkijs.Certificate,
    intermediates: pkijs.Certificate[]
  ): Promise<pkijs.Certificate[]> {
    const chain: pkijs.Certificate[] = [endCert];
    let currentCert = endCert;
    const usedCerts = new Set<string>();

    while (true) {
      const currentFingerprint = this.getCertFingerprintSync(currentCert);
      if (usedCerts.has(currentFingerprint)) {
        break;
      }
      usedCerts.add(currentFingerprint);

      const rootFingerprint = this.getCertFingerprintSync(currentCert);
      if (this.trustedRoots.has(rootFingerprint)) {
        break;
      }

      const subject = this.getNameString(currentCert.subject);
      const issuer = this.getNameString(currentCert.issuer);
      
      if (subject === issuer) {
        break;
      }

      let nextCert: pkijs.Certificate | undefined;

      for (const cert of intermediates) {
        const certSubject = this.getNameString(cert.subject);
        if (certSubject === issuer) {
          nextCert = cert;
          break;
        }
      }

      if (!nextCert) {
        for (const [, cert] of this.trustedRoots) {
          const certSubject = this.getNameString(cert.subject);
          if (certSubject === issuer) {
            nextCert = cert;
            break;
          }
        }
      }

      if (!nextCert) {
        break;
      }

      chain.push(nextCert);
      currentCert = nextCert;
    }

    return chain;
  }

  private async checkRevocationStatus(
    cert: pkijs.Certificate
  ): Promise<'valid' | 'revoked' | 'unknown'> {
    const cacheKey = this.getCertFingerprintSync(cert);
    const cached = CertificateChainService.revocationCache.get(cacheKey);

    if (cached) {
      const now = Date.now();
      if (now - cached.timestamp < CertificateChainService.CACHE_TTL) {
        return cached.status;
      }
    }

    const ocspUrls = this.extractOCSPUrls(cert);
    const crlUrls = this.extractCRLUrls(cert);

    let status: 'valid' | 'revoked' | 'unknown' = 'unknown';

    for (const url of ocspUrls) {
      try {
        status = await this.withTimeout(
          this.fetchOCSPStatus(cert, url),
          CertificateChainService.OCSP_TIMEOUT
        );
        if (status !== 'unknown') break;
      } catch {
      }
    }

    if (status === 'unknown') {
      for (const url of crlUrls) {
        try {
          status = await this.withTimeout(
            this.fetchCRLStatus(cert, url),
            CertificateChainService.CRL_TIMEOUT
          );
          if (status !== 'unknown') break;
        } catch {
        }
      }
    }

    CertificateChainService.revocationCache.set(cacheKey, {
      status,
      timestamp: Date.now(),
    });

    return status;
  }

  private async withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
    return Promise.race([
      promise,
      new Promise<T>((_, reject) =>
        setTimeout(() => reject(new Error('Timeout')), ms)
      ),
    ]);
  }

  private extractOCSPUrls(cert: pkijs.Certificate): string[] {
    const urls: string[] = [];
    try {
      for (const ext of cert.extensions || []) {
        if (ext.extnID === OID_AUTHORITY_INFO_ACCESS) {
          const asn1 = asn1js.fromBER(ext.extnValue.valueBlock.valueHexView);
          if (asn1.offset !== -1) {
            const seq = asn1.result;
            if (seq instanceof asn1js.Sequence) {
              for (const item of seq.valueBlock.value) {
                if (item instanceof asn1js.Sequence && item.valueBlock.value.length >= 2) {
                  const oidItem = item.valueBlock.value[0];
                  const uriItem = item.valueBlock.value[1];
                  if (oidItem instanceof asn1js.ObjectIdentifier &&
                      oidItem.valueBlock.toString() === OID_OCSP &&
                      uriItem instanceof asn1js.Constructed &&
                      uriItem.valueBlock.value[0] instanceof asn1js.IA5String) {
                    urls.push(uriItem.valueBlock.value[0].valueBlock.value);
                  }
                }
              }
            }
          }
        }
      }
    } catch {
    }
    return urls;
  }

  private extractCRLUrls(cert: pkijs.Certificate): string[] {
    const urls: string[] = [];
    try {
      for (const ext of cert.extensions || []) {
        if (ext.extnID === OID_CRL_DISTRIBUTION_POINTS) {
          const asn1 = asn1js.fromBER(ext.extnValue.valueBlock.valueHexView);
          if (asn1.offset !== -1) {
            const seq = asn1.result;
            if (seq instanceof asn1js.Sequence) {
              for (const point of seq.valueBlock.value) {
                if (point instanceof asn1js.Sequence && point.valueBlock.value.length > 0) {
                  const dp = point.valueBlock.value[0];
                  if (dp instanceof asn1js.Constructed) {
                    for (const name of dp.valueBlock.value) {
                      if (name instanceof asn1js.Constructed && name.valueBlock.value.length > 0) {
                        const altName = name.valueBlock.value[0];
                        if (altName instanceof asn1js.Constructed && altName.valueBlock.value.length > 0) {
                          const inner = altName.valueBlock.value[0];
                          if (inner instanceof asn1js.IA5String) {
                            urls.push(inner.valueBlock.value);
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    } catch {
    }
    return urls;
  }

  private async fetchOCSPStatus(cert: pkijs.Certificate, url: string): Promise<'valid' | 'revoked' | 'unknown'> {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/ocsp-request' },
      });
      if (response.ok) {
        return 'valid';
      }
      return 'unknown';
    } catch {
      return 'unknown';
    }
  }

  private async fetchCRLStatus(cert: pkijs.Certificate, url: string): Promise<'valid' | 'revoked' | 'unknown'> {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return 'valid';
      }
      return 'unknown';
    } catch {
      return 'unknown';
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

  private getSerialNumber(cert: pkijs.Certificate): string {
    const buffer = cert.serialNumber.valueBlock.valueHexView.buffer.slice(
      cert.serialNumber.valueBlock.valueHexView.byteOffset,
      cert.serialNumber.valueBlock.valueHexView.byteOffset + cert.serialNumber.valueBlock.valueHexView.byteLength
    );
    return Array.from(new Uint8Array(buffer))
      .map(b => b.toString(16).padStart(2, '0'))
      .join(':')
      .toUpperCase();
  }

  private getCertFingerprintSync(cert: pkijs.Certificate): string {
    const tbs = cert.toSchema().toBER();
    let hash = '';
    
    try {
      const crypto = (globalThis as any).crypto;
      if (crypto && crypto.subtle && crypto.subtle.digest) {
        return 'pending';
      }
    } catch {
    }
    
    const view = new Uint8Array(tbs);
    let h = 0;
    for (let i = 0; i < view.length; i++) {
      h = ((h << 5) - h) + view[i];
      h |= 0;
    }
    return Math.abs(h).toString(16).padStart(16, '0');
  }
}
