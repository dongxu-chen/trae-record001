export interface VerifyOptions {
  verifyLevel: 'basic' | 'standard' | 'strict';
  customTrustCerts?: string[];
  complianceStandard: 'cn-es' | 'eu-eidas' | 'us-esign';
  checkRevocation: boolean;
  checkTimestamp: boolean;
}

export interface VerifyRequest {
  file: File;
  options: VerifyOptions;
}

export interface FileInfo {
  name: string;
  size: number;
  type: string;
  hash: string;
  lastModified?: number;
}

export interface CertificateInfo {
  subject: string;
  issuer: string;
  serialNumber: string;
  validFrom: string;
  validTo: string;
  fingerprint: string;
  signatureAlgorithm: string;
  keyUsage: string[];
  isCA: boolean;
  isSelfSigned: boolean;
  isTrustedRoot: boolean;
  pem?: string;
}

export interface CertificateChainResult {
  isValid: boolean;
  certificates: CertificateInfo[];
  trustPath: string[];
  revocationStatus: 'valid' | 'revoked' | 'unknown';
  errors: string[];
  warnings: string[];
}

export interface TimestampResult {
  hasTimestamp: boolean;
  isValid: boolean;
  timestampTime: string;
  timestampAuthority: string;
  certificateChain: CertificateInfo[];
  hashAlgorithm: string;
  messageImprint: string;
  errors: string[];
  warnings: string[];
}

export interface IntegrityResult {
  isValid: boolean;
  documentHash: string;
  signedHash: string;
  hashMatch: boolean;
  signatureAlgorithm: string;
  signingTime: string;
  hasModifications: boolean;
  errors: string[];
  warnings: string[];
}

export interface ComplianceCheck {
  id: string;
  name: string;
  description: string;
  status: 'pass' | 'fail' | 'warning' | 'not-applicable';
  regulation: string;
  evidence: string;
}

export interface ComplianceResult {
  overallCompliance: 'compliant' | 'partially-compliant' | 'non-compliant';
  standard: string;
  checks: ComplianceCheck[];
  score: number;
}

export interface VerificationResults {
  certificateChain: CertificateChainResult;
  timestamp: TimestampResult;
  integrity: IntegrityResult;
  compliance: ComplianceResult;
  antiForgery?: AntiForgeryResult;
  visualization?: SignatureVisualization;
}

export interface VerifyResponse {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  overallResult: 'valid' | 'invalid' | 'warning' | 'error';
  score: number;
  fileInfo: FileInfo;
  signatureFormat: 'PAdES' | 'XAdES' | 'CAdES' | 'unknown';
  timestamp: number;
  results: VerificationResults;
}

export interface VerificationRecord {
  id: string;
  fileName: string;
  fileHash: string;
  signatureFormat: string;
  overallResult: string;
  score: number;
  createdAt: string;
  status: string;
  results: VerificationResults;
}

export interface SupportedFormat {
  id: string;
  name: string;
  description: string;
  extensions: string[];
}

export interface TrustedCertificate {
  id: string;
  subject: string;
  issuer: string;
  fingerprint: string;
  certificatePem: string;
  source: string;
  isActive: boolean;
}

export interface SignaturePosition {
  pageIndex: number;
  pageHeight: number;
  pageWidth: number;
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
  fieldName: string;
  signerName?: string;
  signingDate?: string;
}

export interface SignatureVisualization {
  hasVisualRepresentation: boolean;
  positions: SignaturePosition[];
  pageCount: number;
}

export interface AntiForgeryCheck {
  id: string;
  name: string;
  description: string;
  status: 'pass' | 'fail' | 'warning' | 'not-applicable';
  evidence: string;
  risk: 'low' | 'medium' | 'high';
}

export interface AntiForgeryResult {
  isAuthentic: boolean;
  overallRisk: 'low' | 'medium' | 'high';
  score: number;
  checks: AntiForgeryCheck[];
  warnings: string[];
  errors: string[];
}

export interface BatchFileStatus {
  fileId: string;
  fileName: string;
  fileSize: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  result?: VerifyResponse;
  error?: string;
  startedAt?: number;
  completedAt?: number;
}

export interface BatchVerifyResponse {
  batchId: string;
  status: 'processing' | 'completed' | 'failed';
  totalFiles: number;
  completedFiles: number;
  failedFiles: number;
  files: BatchFileStatus[];
  createdAt: number;
  updatedAt: number;
}
