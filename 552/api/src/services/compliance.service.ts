import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import type {
  ComplianceResult,
  ComplianceCheck,
  CertificateChainResult,
  TimestampResult,
  IntegrityResult,
  VerifyOptions
} from '../../../shared';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

interface ComplianceRule {
  id: string;
  name: string;
  description: string;
  regulation: string;
  category: string;
  weight: number;
}

interface StandardRules {
  name: string;
  description: string;
  version: string;
  rules: ComplianceRule[];
}

interface ComplianceRulesData {
  'cn-es': StandardRules;
  'eu-eidas': StandardRules;
  'us-esign': StandardRules;
}

export type ComplianceStandard = 'cn-es' | 'eu-eidas' | 'us-esign';

interface CheckInput {
  certificateChain: CertificateChainResult;
  timestamp: TimestampResult;
  integrity: IntegrityResult;
  options: VerifyOptions;
}

export class ComplianceService {
  private rulesData: ComplianceRulesData;
  private readonly RULES_PATH: string;

  constructor() {
    this.RULES_PATH = path.join(__dirname, '../data/compliance-rules.json');
    this.rulesData = this.loadRules();
  }

  private loadRules(): ComplianceRulesData {
    try {
      const rawData = fs.readFileSync(this.RULES_PATH, 'utf-8');
      return JSON.parse(rawData) as ComplianceRulesData;
    } catch {
      return this.getDefaultRules();
    }
  }

  private getDefaultRules(): ComplianceRulesData {
    return {
      'cn-es': {
        name: '中华人民共和国电子签名法',
        description: '中国电子签名法规定的可靠电子签名合规要求',
        version: '2019-04-23',
        rules: []
      },
      'eu-eidas': {
        name: 'eIDAS Regulation (EU 910/2014)',
        description: '欧盟电子身份认证和信任服务法规',
        version: '2014-07-23',
        rules: []
      },
      'us-esign': {
        name: 'ESIGN Act (15 U.S.C. § 7001 et seq.)',
        description: '美国全球和全国商务电子签名法',
        version: '2000-06-30',
        rules: []
      }
    };
  }

  async checkCompliance(
    standard: ComplianceStandard,
    input: CheckInput
  ): Promise<ComplianceResult> {
    const standardRules = this.rulesData[standard];
    if (!standardRules || standardRules.rules.length === 0) {
      return {
        overallCompliance: 'non-compliant',
        standard,
        checks: [],
        score: 0
      };
    }

    const checks: ComplianceCheck[] = [];
    let totalWeight = 0;
    let earnedScore = 0;

    for (const rule of standardRules.rules) {
      const check = this.evaluateRule(rule, input);
      checks.push(check);
      totalWeight += rule.weight;

      if (check.status === 'pass') {
        earnedScore += rule.weight;
      } else if (check.status === 'warning') {
        earnedScore += rule.weight * 0.5;
      }
    }

    const score = totalWeight > 0 ? Math.round((earnedScore / totalWeight) * 100) : 0;

    let overallCompliance: 'compliant' | 'partially-compliant' | 'non-compliant';
    if (score >= 80) {
      overallCompliance = 'compliant';
    } else if (score >= 50) {
      overallCompliance = 'partially-compliant';
    } else {
      overallCompliance = 'non-compliant';
    }

    return {
      overallCompliance,
      standard: standardRules.name,
      checks,
      score
    };
  }

  private evaluateRule(rule: ComplianceRule, input: CheckInput): ComplianceCheck {
    const { certificateChain, timestamp, integrity, options } = input;
    let status: 'pass' | 'fail' | 'warning' | 'not-applicable' = 'not-applicable';
    let evidence = '';

    switch (rule.category) {
      case 'reliable-signature':
        ({ status, evidence } = this.evaluateReliableSignature(rule, certificateChain, integrity));
        break;
      case 'certificate-validity':
        ({ status, evidence } = this.evaluateCertificateValidity(rule, certificateChain, options));
        break;
      case 'timestamp':
        ({ status, evidence } = this.evaluateTimestamp(rule, timestamp, options));
        break;
      case 'integrity':
        ({ status, evidence } = this.evaluateIntegrity(rule, integrity));
        break;
      case 'identity-verification':
        ({ status, evidence } = this.evaluateIdentityVerification(rule, certificateChain));
        break;
      default:
        status = 'not-applicable';
        evidence = '规则类别未定义';
    }

    return {
      id: rule.id,
      name: rule.name,
      description: rule.description,
      status,
      regulation: rule.regulation,
      evidence
    };
  }

  private evaluateReliableSignature(
    rule: ComplianceRule,
    certificateChain: CertificateChainResult,
    integrity: IntegrityResult
  ): { status: 'pass' | 'fail' | 'warning' | 'not-applicable'; evidence: string } {
    const hasSignerCert = certificateChain.certificates.length > 0;
    const isSelfSigned = certificateChain.certificates[0]?.isSelfSigned;
    const integrityValid = integrity.isValid;
    const hasTrustPath = certificateChain.trustPath.length > 0;

    if (rule.id.includes('001') || rule.id.includes('002')) {
      if (hasSignerCert && !isSelfSigned && hasTrustPath) {
        return { status: 'pass', evidence: '签名证书由可信CA签发，链接到签名人身份' };
      }
      if (hasSignerCert && isSelfSigned) {
        return { status: 'warning', evidence: '使用自签名证书，专有性和控制力无法可靠验证' };
      }
      return { status: 'fail', evidence: '缺少签名人证书，无法验证签名专有性' };
    }

    if (rule.id.includes('003') || rule.id === 'EU-EIDAS-003' || rule.id === 'US-ESIGN-002') {
      if (integrityValid && hasTrustPath) {
        return { status: 'pass', evidence: '签名有效且证书链完整，签名不可否认' };
      }
      if (integrityValid && !hasTrustPath) {
        return { status: 'warning', evidence: '签名有效但证书链不完整，无法完全保证不可否认性' };
      }
      return { status: 'fail', evidence: '签名完整性验证失败' };
    }

    if (rule.id === 'US-ESIGN-001') {
      if (integrity.signingTime && hasSignerCert) {
        return { status: 'pass', evidence: '签名时间和签名人身份可验证，表明签署意图' };
      }
      return { status: 'warning', evidence: '缺少签名时间或签名人信息，意图验证受限' };
    }

    if (rule.id === 'US-ESIGN-003') {
      if (integrityValid && !isSelfSigned && hasTrustPath) {
        return { status: 'pass', evidence: '签名有效且由可信CA签发，不可否认性成立' };
      }
      if (integrityValid && (isSelfSigned || !hasTrustPath)) {
        return { status: 'warning', evidence: '签名有效但证书信任链不完整，不可否认性受限' };
      }
      return { status: 'fail', evidence: '签名无效，无法建立不可否认性' };
    }

    return { status: 'not-applicable', evidence: '未匹配到具体规则逻辑' };
  }

  private evaluateCertificateValidity(
    rule: ComplianceRule,
    certificateChain: CertificateChainResult,
    options: VerifyOptions
  ): { status: 'pass' | 'fail' | 'warning' | 'not-applicable'; evidence: string } {
    const certs = certificateChain.certificates;
    const signerCert = certs[0];
    const hasTrustedRoot = certs.some(c => c.isTrustedRoot);
    const revocationStatus = certificateChain.revocationStatus;
    const checkRevocation = options.checkRevocation;

    if (!signerCert) {
      return { status: 'fail', evidence: '没有找到签名人证书' };
    }

    const now = new Date();
    const validFrom = new Date(signerCert.validFrom);
    const validTo = new Date(signerCert.validTo);
    const isInValidityPeriod = now >= validFrom && now <= validTo;

    if (rule.id === 'CN-ES-005' || rule.id === 'EU-EIDAS-004' || rule.id === 'EU-EIDAS-006') {
      if (hasTrustedRoot && !signerCert.isSelfSigned) {
        return { status: 'pass', evidence: '证书由可信根证书颁发机构签发' };
      }
      if (signerCert.isSelfSigned) {
        return { status: 'fail', evidence: '自签名证书不符合法定认证服务机构要求' };
      }
      return { status: 'warning', evidence: '证书链未链接到可信根，颁发机构资质无法验证' };
    }

    if (rule.id === 'CN-ES-006' || rule.id === 'EU-EIDAS-005') {
      if (!isInValidityPeriod) {
        return { status: 'fail', evidence: `证书已过期或尚未生效，有效期: ${signerCert.validFrom} 至 ${signerCert.validTo}` };
      }
      if (checkRevocation) {
        if (revocationStatus === 'valid') {
          return { status: 'pass', evidence: '证书在有效期内且未被吊销' };
        }
        if (revocationStatus === 'revoked') {
          return { status: 'fail', evidence: '证书已被吊销' };
        }
        return { status: 'warning', evidence: '证书有效期内但吊销状态无法确认' };
      }
      return { status: 'warning', evidence: '证书在有效期内，但吊销检查未执行' };
    }

    if (rule.id === 'US-ESIGN-007') {
      if (signerCert && !signerCert.isSelfSigned && hasTrustedRoot) {
        return { status: 'pass', evidence: '使用可信数字证书验证签名身份' };
      }
      if (signerCert && signerCert.isSelfSigned) {
        return { status: 'warning', evidence: '使用自签名证书，身份验证强度不足' };
      }
      return { status: 'warning', evidence: '未使用数字证书进行身份验证' };
    }

    return { status: 'not-applicable', evidence: '未匹配到具体规则逻辑' };
  }

  private evaluateTimestamp(
    rule: ComplianceRule,
    timestamp: TimestampResult,
    options: VerifyOptions
  ): { status: 'pass' | 'fail' | 'warning' | 'not-applicable'; evidence: string } {
    if (!options.checkTimestamp) {
      return { status: 'warning', evidence: '时间戳验证未启用' };
    }

    if (timestamp.hasTimestamp) {
      if (timestamp.isValid) {
        return { status: 'pass', evidence: `有效时间戳: ${timestamp.timestampTime}, 由 ${timestamp.timestampAuthority} 签发` };
      }
      return { status: 'fail', evidence: '时间戳存在但验证失败' };
    }

    return { status: 'fail', evidence: '签名中未包含可信时间戳' };
  }

  private evaluateIntegrity(
    rule: ComplianceRule,
    integrity: IntegrityResult
  ): { status: 'pass' | 'fail' | 'warning' | 'not-applicable'; evidence: string } {
    const hashMatch = integrity.hashMatch;
    const hasModifications = integrity.hasModifications;
    const algorithm = integrity.signatureAlgorithm.toUpperCase();
    const weakAlgorithm = algorithm.includes('SHA1') || algorithm.includes('MD5');

    if (hashMatch && !hasModifications) {
      if (weakAlgorithm) {
        return { status: 'warning', evidence: `完整性验证通过，但使用了弱哈希算法: ${algorithm}` };
      }
      return { status: 'pass', evidence: `文档和签名完整性验证通过，使用算法: ${algorithm}` };
    }

    if (!hashMatch) {
      return { status: 'fail', evidence: '签名哈希与文档哈希不匹配，签名已被篡改' };
    }

    if (hasModifications) {
      return { status: 'fail', evidence: '文档在签名后被修改' };
    }

    return { status: 'fail', evidence: '完整性验证失败' };
  }

  private evaluateIdentityVerification(
    rule: ComplianceRule,
    certificateChain: CertificateChainResult
  ): { status: 'pass' | 'fail' | 'warning' | 'not-applicable'; evidence: string } {
    const signerCert = certificateChain.certificates[0];
    const hasTrustedRoot = certificateChain.certificates.some(c => c.isTrustedRoot);
    const trustPathLength = certificateChain.trustPath.length;

    if (!signerCert) {
      return { status: 'fail', evidence: '没有签名人证书，无法进行身份验证' };
    }

    if (rule.id === 'CN-ES-007' || rule.id === 'EU-EIDAS-009') {
      if (hasTrustedRoot && trustPathLength > 1 && !signerCert.isSelfSigned) {
        return { status: 'pass', evidence: `签名人身份已通过可信证书链验证: ${signerCert.subject}` };
      }
      if (!signerCert.isSelfSigned && trustPathLength === 1) {
        return { status: 'warning', evidence: `签名人身份信息存在: ${signerCert.subject}，但证书链未链接到可信根` };
      }
      if (signerCert.isSelfSigned) {
        return { status: 'fail', evidence: '自签名证书，身份未经第三方认证服务提供者核实' };
      }
      return { status: 'warning', evidence: `签名人信息: ${signerCert.subject}，但身份验证不完整` };
    }

    if (rule.id === 'US-ESIGN-004') {
      if (signerCert.subject && hasTrustedRoot) {
        return { status: 'pass', evidence: `签名人身份可验证: ${signerCert.subject}，表明电子记录使用同意` };
      }
      if (signerCert.subject && !hasTrustedRoot) {
        return { status: 'warning', evidence: `签名人信息存在: ${signerCert.subject}，但缺少可信第三方验证` };
      }
      return { status: 'warning', evidence: '消费者同意记录不完整，建议保留明确同意证据' };
    }

    return { status: 'not-applicable', evidence: '未匹配到具体规则逻辑' };
  }

  getSupportedStandards(): { id: ComplianceStandard; name: string; description: string }[] {
    return Object.entries(this.rulesData).map(([id, data]) => ({
      id: id as ComplianceStandard,
      name: data.name,
      description: data.description
    }));
  }

  getStandardRules(standard: ComplianceStandard): StandardRules | null {
    return this.rulesData[standard] || null;
  }
}
