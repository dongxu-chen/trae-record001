import { type Request, type Response, type NextFunction, Router } from 'express';
import { CertificateChainService } from '../services/certificate-chain.service.js';
import type { TrustedCertificate } from '../../../shared/index.js';

const router = Router();
const certificateChainService = new CertificateChainService();

const trustedCertificates: TrustedCertificate[] = [
  {
    id: 'root-cn-1',
    subject: 'CN=China Electronic Certification Root CA, O=China Financial Certification Authority, C=CN',
    issuer: 'CN=China Electronic Certification Root CA, O=China Financial Certification Authority, C=CN',
    fingerprint: 'A1:B2:C3:D4:E5:F6:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:AB',
    certificatePem: '-----BEGIN CERTIFICATE-----\nMII...\n-----END CERTIFICATE-----',
    source: 'CFCA',
    isActive: true,
  },
  {
    id: 'root-cn-2',
    subject: 'CN=WoSign Root CA, O=WoSign CA Limited, C=CN',
    issuer: 'CN=WoSign Root CA, O=WoSign CA Limited, C=CN',
    fingerprint: '11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44',
    certificatePem: '-----BEGIN CERTIFICATE-----\nMII...\n-----END CERTIFICATE-----',
    source: 'WoSign',
    isActive: true,
  },
  {
    id: 'root-eu-1',
    subject: 'CN=EU Trusted List Root CA, O=European Commission, C=EU',
    issuer: 'CN=EU Trusted List Root CA, O=European Commission, C=EU',
    fingerprint: 'AA:BB:CC:DD:EE:FF:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE',
    certificatePem: '-----BEGIN CERTIFICATE-----\nMII...\n-----END CERTIFICATE-----',
    source: 'EU Trusted List',
    isActive: true,
  },
  {
    id: 'root-us-1',
    subject: 'CN=DigiCert Global Root CA, O=DigiCert Inc, C=US',
    issuer: 'CN=DigiCert Global Root CA, O=DigiCert Inc, C=US',
    fingerprint: '01:02:03:04:05:06:07:08:09:0A:0B:0C:0D:0E:0F:10:11:12:13:14',
    certificatePem: '-----BEGIN CERTIFICATE-----\nMII...\n-----END CERTIFICATE-----',
    source: 'DigiCert',
    isActive: true,
  },
];

export const getTrustedCertificates = (
  req: Request,
  res: Response,
  next: NextFunction,
): void => {
  try {
    const activeOnly = req.query.active !== 'false';
    const certificates = activeOnly
      ? trustedCertificates.filter((cert) => cert.isActive)
      : trustedCertificates;

    res.status(200).json({
      success: true,
      data: certificates,
    });
  } catch (error) {
    next(error);
  }
};

export default router;
