import { nanoid } from 'nanoid';
import { PAdESService } from './pades.service.js';
import { XAdESService } from './xades.service.js';
import { CAdESService } from './cades.service.js';
import { CertificateChainService } from './certificate-chain.service.js';
import { TimestampService } from './timestamp.service.js';
import { AntiForgeryService } from './anti-forgery.service.js';
import { calculateHash } from '../core/crypto-utils.js';
import { hasSignatures, extractSignaturePositions } from '../core/pdf-parser.js';
import type {
  VerifyOptions,
  VerifyResponse,
  VerificationResults,
  CertificateChainResult,
  TimestampResult,
  IntegrityResult,
  ComplianceResult,
  FileInfo,
  VerificationRecord,
  SignatureVisualization,
  AntiForgeryResult,
  BatchVerifyResponse,
  BatchFileStatus,
} from '../../../shared';

type SignatureFormat = 'PAdES' | 'XAdES' | 'CAdES' | 'unknown';

interface FormatDetectionResult {
  format: SignatureFormat;
  confidence: number;
}

interface BatchFile {
  id: string;
  fileData: Uint8Array;
  fileName: string;
}

const verificationHistory: Map<string, VerificationRecord> = new Map();
const batchJobs: Map<string, BatchVerifyResponse> = new Map();

export class VerificationService {
  private padesService: PAdESService;
  private xadesService: XAdESService;
  private cadesService: CAdESService;
  private certificateChainService: CertificateChainService;
  private timestampService: TimestampService;
  private antiForgeryService: AntiForgeryService;

  constructor(trustedRootCerts?: string[]) {
    this.padesService = new PAdESService(trustedRootCerts);
    this.xadesService = new XAdESService(trustedRootCerts);
    this.cadesService = new CAdESService(trustedRootCerts);
    this.certificateChainService = new CertificateChainService(trustedRootCerts);
    this.timestampService = new TimestampService(trustedRootCerts);
    this.antiForgeryService = new AntiForgeryService();
  }

  generateVerificationId(): string {
    return nanoid(21);
  }

  async detectSignatureFormat(
    fileData: Uint8Array,
    fileName: string
  ): Promise<FormatDetectionResult> {
    const lowerName = fileName.toLowerCase();
    const detections: { format: SignatureFormat; score: number }[] = [];

    if (lowerName.endsWith('.pdf')) {
      try {
        const hasSig = await hasSignatures(fileData);
        if (hasSig) {
          detections.push({ format: 'PAdES', score: 95 });
        } else {
          detections.push({ format: 'PAdES', score: 50 });
        }
      } catch {
        detections.push({ format: 'PAdES', score: 40 });
      }
    }

    if (lowerName.endsWith('.xml') || lowerName.endsWith('.xades')) {
      try {
        const hasSig = await this.xadesService.detectSignatures(fileData);
        if (hasSig) {
          detections.push({ format: 'XAdES', score: 95 });
        } else {
          detections.push({ format: 'XAdES', score: 50 });
        }
      } catch {
        detections.push({ format: 'XAdES', score: 40 });
      }
    }

    if (
      lowerName.endsWith('.p7s') ||
      lowerName.endsWith('.p7m') ||
      lowerName.endsWith('.cms') ||
      lowerName.endsWith('.der') ||
      lowerName.endsWith('.pem')
    ) {
      try {
        const isPKCS7 = this.cadesService.isPKCS7Format(fileData.buffer);
        if (isPKCS7) {
          detections.push({ format: 'CAdES', score: 95 });
        } else {
          detections.push({ format: 'CAdES', score: 50 });
        }
      } catch {
        detections.push({ format: 'CAdES', score: 40 });
      }
    }

    try {
      const isPKCS7 = this.cadesService.isPKCS7Format(fileData.buffer);
      if (isPKCS7) {
        const existing = detections.find((d) => d.format === 'CAdES');
        if (!existing) {
          detections.push({ format: 'CAdES', score: 80 });
        } else {
          existing.score = Math.max(existing.score, 80);
        }
      }
    } catch {}

    try {
      const hasPAdESSig = await hasSignatures(fileData);
      if (hasPAdESSig) {
        const existing = detections.find((d) => d.format === 'PAdES');
        if (!existing) {
          detections.push({ format: 'PAdES', score: 85 });
        } else {
          existing.score = Math.max(existing.score, 85);
        }
      }
    } catch {}

    try {
      const hasXAdESSig = await this.xadesService.detectSignatures(fileData);
      if (hasXAdESSig) {
        const existing = detections.find((d) => d.format === 'XAdES');
        if (!existing) {
          detections.push({ format: 'XAdES', score: 85 });
        } else {
          existing.score = Math.max(existing.score, 85);
        }
      }
    } catch {}

    if (detections.length === 0) {
      return { format: 'unknown', confidence: 0 };
    }

    detections.sort((a, b) => b.score - a.score);
    return { format: detections[0].format, confidence: detections[0].score };
  }

  calculateOverallResult(results: VerificationResults): {
    overallResult: 'valid' | 'invalid' | 'warning' | 'error';
    score: number;
  } {
    const { certificateChain, timestamp, integrity, compliance, antiForgery } = results;
    let score = 0;
    let hasError = false;
    let hasWarning = false;

    if (certificateChain.isValid) {
      score += 20;
    } else {
      hasError = true;
    }
    if (certificateChain.warnings.length > 0) {
      hasWarning = true;
      score -= certificateChain.warnings.length * 2;
    }

    if (timestamp.hasTimestamp) {
      if (timestamp.isValid) {
        score += 20;
      } else {
        hasError = true;
      }
    } else {
      score += 8;
    }
    if (timestamp.warnings.length > 0) {
      hasWarning = true;
      score -= timestamp.warnings.length * 2;
    }

    if (integrity.isValid) {
      score += 20;
    } else {
      hasError = true;
    }
    if (integrity.warnings.length > 0) {
      hasWarning = true;
      score -= integrity.warnings.length * 2;
    }

    if (compliance.overallCompliance === 'compliant') {
      score += 20;
    } else if (compliance.overallCompliance === 'partially-compliant') {
      score += 12;
      hasWarning = true;
    } else {
      hasError = true;
    }
    if (compliance.checks.some((c) => c.status === 'warning')) {
      hasWarning = true;
    }

    if (antiForgery) {
      if (antiForgery.isAuthentic) {
        score += 20;
      } else {
        hasError = true;
      }
      if (antiForgery.overallRisk === 'medium') {
        hasWarning = true;
      }
      if (antiForgery.warnings.length > 0) {
        hasWarning = true;
        score -= antiForgery.warnings.length;
      }
    } else {
      score += 10;
    }

    score = Math.max(0, Math.min(100, score));

    let overallResult: 'valid' | 'invalid' | 'warning' | 'error';
    if (hasError) {
      overallResult = 'invalid';
    } else if (hasWarning) {
      overallResult = 'warning';
    } else {
      overallResult = 'valid';
    }

    return { overallResult, score };
  }

  async verify(
    fileData: Uint8Array,
    fileName: string,
    options: VerifyOptions
  ): Promise<VerifyResponse> {
    const verificationId = this.generateVerificationId();
    const timestamp = Date.now();

    const fileHash = calculateHash(fileData, 'SHA256');
    const fileInfo: FileInfo = {
      name: fileName,
      size: fileData.length,
      type: fileName.split('.').pop() || '',
      hash: fileHash,
    };

    const formatDetection = await this.detectSignatureFormat(fileData, fileName);
    const signatureFormat = formatDetection.format;

    let verificationResults: VerificationResults;

    try {
      if (options.customTrustCerts) {
        this.padesService = new PAdESService(options.customTrustCerts);
        this.xadesService = new XAdESService(options.customTrustCerts);
        this.cadesService = new CAdESService(options.customTrustCerts);
        this.certificateChainService = new CertificateChainService(options.customTrustCerts);
        this.timestampService = new TimestampService(options.customTrustCerts);
      }

      let visualization: SignatureVisualization | undefined;
      try {
        visualization = await extractSignaturePositions(fileData);
      } catch {}

      if (signatureFormat === 'PAdES') {
        verificationResults = await this.verifyPAdES(fileData, options);
      } else if (signatureFormat === 'XAdES') {
        verificationResults = await this.verifyXAdES(fileData, options);
      } else if (signatureFormat === 'CAdES') {
        verificationResults = await this.verifyCAdES(fileData, options);
      } else {
        verificationResults = this.createEmptyResults('Unsupported or unknown signature format');
      }

      verificationResults.visualization = visualization;

      try {
        const antiForgery = await this.antiForgeryService.detectForgery(
          fileData, fileName, visualization
        );
        verificationResults.antiForgery = antiForgery;
      } catch {}

    } catch (error) {
      verificationResults = this.createEmptyResults(
        `Verification failed: ${error instanceof Error ? error.message : String(error)}`
      );
    }

    const { overallResult, score } = this.calculateOverallResult(verificationResults);

    const response: VerifyResponse = {
      id: verificationId,
      status: 'completed',
      overallResult,
      score,
      fileInfo,
      signatureFormat,
      timestamp,
      results: verificationResults,
    };

    this.saveVerificationRecord(response);

    return response;
  }

  async batchVerify(
    files: BatchFile[],
    options: VerifyOptions
  ): Promise<BatchVerifyResponse> {
    const batchId = nanoid(21);
    const now = Date.now();

    const batchFileStatuses: BatchFileStatus[] = files.map((f) => ({
      fileId: f.id,
      fileName: f.fileName,
      fileSize: f.fileData.length,
      status: 'pending' as const,
      progress: 0,
    }));

    const batchResponse: BatchVerifyResponse = {
      batchId,
      status: 'processing',
      totalFiles: files.length,
      completedFiles: 0,
      failedFiles: 0,
      files: batchFileStatuses,
      createdAt: now,
      updatedAt: now,
    };

    batchJobs.set(batchId, batchResponse);

    this.processBatchFiles(batchId, files, options).catch(() => {
      const job = batchJobs.get(batchId);
      if (job) {
        job.status = 'failed';
        job.updatedAt = Date.now();
      }
    });

    return batchResponse;
  }

  private async processBatchFiles(
    batchId: string,
    files: BatchFile[],
    options: VerifyOptions
  ): Promise<void> {
    const concurrency = 3;
    const results: Promise<void>[] = [];

    for (let i = 0; i < files.length; i += concurrency) {
      const chunk = files.slice(i, i + concurrency);
      const chunkPromises = chunk.map((file) => this.processSingleBatchFile(batchId, file, options));
      results.push(Promise.all(chunkPromises).then(() => {}));
    }

    await Promise.all(results);

    const job = batchJobs.get(batchId);
    if (job) {
      const completed = job.files.filter(f => f.status === 'completed').length;
      const failed = job.files.filter(f => f.status === 'failed').length;
      job.completedFiles = completed;
      job.failedFiles = failed;
      job.status = (completed + failed) === job.totalFiles ? 'completed' : 'failed';
      job.updatedAt = Date.now();
    }
  }

  private async processSingleBatchFile(
    batchId: string,
    file: BatchFile,
    options: VerifyOptions
  ): Promise<void> {
    const job = batchJobs.get(batchId);
    if (!job) return;

    const fileStatus = job.files.find(f => f.fileId === file.id);
    if (!fileStatus) return;

    fileStatus.status = 'processing';
    fileStatus.progress = 10;
    fileStatus.startedAt = Date.now();
    job.updatedAt = Date.now();

    try {
      fileStatus.progress = 30;
      const service = new VerificationService(options.customTrustCerts);
      const result = await service.verify(file.fileData, file.fileName, options);

      fileStatus.status = 'completed';
      fileStatus.progress = 100;
      fileStatus.result = result;
      fileStatus.completedAt = Date.now();
    } catch (error) {
      fileStatus.status = 'failed';
      fileStatus.progress = 0;
      fileStatus.error = error instanceof Error ? error.message : String(error);
      fileStatus.completedAt = Date.now();
    }

    job.updatedAt = Date.now();
  }

  getBatchStatus(batchId: string): BatchVerifyResponse | undefined {
    return batchJobs.get(batchId);
  }

  private async verifyPAdES(
    fileData: Uint8Array,
    options: VerifyOptions
  ): Promise<VerificationResults> {
    const padesResult = await this.padesService.verifyPAdES(fileData, options);

    let certificateChain: CertificateChainResult;
    let timestamp: TimestampResult;
    let integrity: IntegrityResult;

    if (padesResult.signatures.length > 0) {
      const firstSig = padesResult.signatures[0];
      certificateChain = firstSig.certificateChain;
      timestamp = firstSig.timestamp;
      integrity = firstSig.integrity;
    } else {
      certificateChain = {
        isValid: false,
        certificates: [],
        trustPath: [],
        revocationStatus: 'unknown',
        errors: padesResult.errors,
        warnings: padesResult.warnings,
      };
      timestamp = {
        hasTimestamp: false,
        isValid: false,
        timestampTime: '',
        timestampAuthority: '',
        certificateChain: [],
        hashAlgorithm: '',
        messageImprint: '',
        errors: padesResult.errors,
        warnings: [],
      };
      integrity = {
        isValid: false,
        documentHash: '',
        signedHash: '',
        hashMatch: false,
        signatureAlgorithm: '',
        signingTime: '',
        hasModifications: false,
        errors: padesResult.errors,
        warnings: padesResult.warnings,
      };
    }

    const compliance = await this.checkCompliance(
      certificateChain,
      timestamp,
      integrity,
      options
    );

    return {
      certificateChain,
      timestamp,
      integrity,
      compliance,
    };
  }

  private async verifyXAdES(
    fileData: Uint8Array,
    options: VerifyOptions
  ): Promise<VerificationResults> {
    const xadesResult = await this.xadesService.verifyXAdES(fileData, options);

    let certificateChain: CertificateChainResult;
    let timestamp: TimestampResult;
    let integrity: IntegrityResult;

    if (xadesResult.signatures.length > 0) {
      const firstSig = xadesResult.signatures[0];
      certificateChain = firstSig.certificateChain;
      timestamp = firstSig.timestamp;
      integrity = firstSig.integrity;
    } else {
      certificateChain = {
        isValid: false,
        certificates: [],
        trustPath: [],
        revocationStatus: 'unknown',
        errors: xadesResult.errors,
        warnings: xadesResult.warnings,
      };
      timestamp = {
        hasTimestamp: false,
        isValid: false,
        timestampTime: '',
        timestampAuthority: '',
        certificateChain: [],
        hashAlgorithm: '',
        messageImprint: '',
        errors: xadesResult.errors,
        warnings: [],
      };
      integrity = {
        isValid: false,
        documentHash: '',
        signedHash: '',
        hashMatch: false,
        signatureAlgorithm: '',
        signingTime: '',
        hasModifications: false,
        errors: xadesResult.errors,
        warnings: xadesResult.warnings,
      };
    }

    const compliance = await this.checkCompliance(
      certificateChain,
      timestamp,
      integrity,
      options
    );

    return {
      certificateChain,
      timestamp,
      integrity,
      compliance,
    };
  }

  private async verifyCAdES(
    fileData: Uint8Array,
    options: VerifyOptions
  ): Promise<VerificationResults> {
    const cadesResult = await this.cadesService.verifySignature(
      fileData.buffer,
      undefined,
      options
    );

    const certificateChain = cadesResult.certificateChain;
    const timestamp = cadesResult.timestamp;
    const integrity = cadesResult.integrity;

    const compliance = await this.checkCompliance(
      certificateChain,
      timestamp,
      integrity,
      options
    );

    return {
      certificateChain,
      timestamp,
      integrity,
      compliance,
    };
  }

  private async checkCompliance(
    certificateChain: CertificateChainResult,
    timestamp: TimestampResult,
    integrity: IntegrityResult,
    options: VerifyOptions
  ): Promise<ComplianceResult> {
    const { ComplianceService } = await import('./compliance.service');
    const complianceService = new ComplianceService();
    return complianceService.checkCompliance(
      options.complianceStandard,
      {
        certificateChain,
        timestamp,
        integrity,
        options
      }
    );
  }

  private createEmptyResults(errorMessage: string): VerificationResults {
    return {
      certificateChain: {
        isValid: false,
        certificates: [],
        trustPath: [],
        revocationStatus: 'unknown',
        errors: [errorMessage],
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
        errors: [errorMessage],
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
        errors: [errorMessage],
        warnings: [],
      },
      compliance: {
        overallCompliance: 'non-compliant',
        standard: '',
        checks: [],
        score: 0,
      },
    };
  }

  private saveVerificationRecord(response: VerifyResponse): void {
    const record: VerificationRecord = {
      id: response.id,
      fileName: response.fileInfo.name,
      fileHash: response.fileInfo.hash,
      signatureFormat: response.signatureFormat,
      overallResult: response.overallResult,
      score: response.score,
      createdAt: new Date(response.timestamp).toISOString(),
      status: response.status,
      results: response.results,
    };
    verificationHistory.set(record.id, record);
  }

  getVerificationById(id: string): VerificationRecord | undefined {
    return verificationHistory.get(id);
  }

  getAllVerifications(): VerificationRecord[] {
    return Array.from(verificationHistory.values()).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  }

  clearVerificationHistory(): void {
    verificationHistory.clear();
  }
}
