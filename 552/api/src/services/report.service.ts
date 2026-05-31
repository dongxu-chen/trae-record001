import { jsPDF } from 'jspdf';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import type {
  VerifyResponse,
  FileInfo,
  CertificateChainResult,
  TimestampResult,
  IntegrityResult,
  ComplianceResult,
  CertificateInfo,
  ComplianceCheck
} from '../../../shared';

export class ReportService {
  private verificationId: string;
  private verificationDate: string;

  constructor() {
    this.verificationId = this.generateVerificationId();
    this.verificationDate = new Date().toISOString();
  }

  private generateVerificationId(): string {
    return `VR-${Date.now()}-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return 'N/A';
      const y = date.getUTCFullYear();
      const m = String(date.getUTCMonth() + 1).padStart(2, '0');
      const d = String(date.getUTCDate()).padStart(2, '0');
      const h = String(date.getUTCHours()).padStart(2, '0');
      const min = String(date.getUTCMinutes()).padStart(2, '0');
      const s = String(date.getUTCSeconds()).padStart(2, '0');
      return `${y}-${m}-${d} ${h}:${min}:${s} UTC`;
    } catch {
      return 'N/A';
    }
  }

  private formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }

  private getOverallResultText(result: string): string {
    const map: Record<string, string> = {
      'valid': '签名验证通过，该电子签名可信',
      'invalid': '签名验证未通过，该电子签名不可信',
      'warning': '签名基本可信，但存在需要注意的问题',
      'error': '验证过程出错，无法确认签名有效性'
    };
    return map[result] || result;
  }

  private getOverallResultColor(result: string): string {
    const map: Record<string, string> = {
      'valid': '#28a745',
      'invalid': '#dc3545',
      'warning': '#ffc107',
      'error': '#6c757d'
    };
    return map[result] || '#000000';
  }

  private getComplianceStatusText(status: string): string {
    const map: Record<string, string> = {
      'pass': '符合要求',
      'fail': '不符合要求',
      'warning': '部分符合，需注意',
      'not-applicable': '此项不适用'
    };
    return map[status] || status;
  }

  private getComplianceStatusColor(status: string): string {
    const map: Record<string, string> = {
      'pass': '#28a745',
      'fail': '#dc3545',
      'warning': '#ffc107',
      'not-applicable': '#6c757d'
    };
    return map[status] || '#000000';
  }

  private getCertificateChainDiagram(certificates: CertificateInfo[]): string {
    if (certificates.length === 0) return '';
    const labels = certificates.map((cert, i) => {
      if (i === certificates.length - 1) return '根证书<br>(信任锚点)';
      if (i === 0) return '用户证书<br>(签名者)';
      return `中间CA证书<br>(颁发机构)`;
    });
    const names = certificates.map(cert => {
      const name = cert.subject.split(',').find(p => p.startsWith('CN=')) || cert.subject;
      return name.replace('CN=', '').substring(0, 20);
    });
    const boxes = labels.map((label, i) => `
      <div style="flex:1; text-align:center; padding:10px; border:2px solid #165DFF; border-radius:8px; background:#f0f7ff; margin:5px;">
        <div style="font-weight:bold; color:#165DFF; font-size:12px;">${label}</div>
        <div style="font-size:11px; color:#666; margin-top:5px;">${names[i]}</div>
      </div>
    `);
    const arrows = Array(certificates.length - 1).fill(
      '<div style="display:flex; align-items:center; font-size:24px; color:#165DFF; padding:0 5px;">→</div>'
    );
    let html = '<div style="display:flex; align-items:stretch; justify-content:center; margin:20px 0; padding:15px; background:#fafafa; border-radius:8px;">';
    for (let i = 0; i < certificates.length; i++) {
      html += boxes[i];
      if (i < certificates.length - 1) html += arrows[i];
    }
    html += '</div>';
    return html;
  }

  private getIntegrityExplanation(integrity: IntegrityResult): string {
    if (integrity.hashMatch) {
      return '<div style="background:#d4edda; color:#155724; padding:15px; border-radius:8px; margin:15px 0;"><strong>✓ 文档完整：</strong>文档内容与签名时完全一致，未被任何人修改。就像密封的信封，封口完好无损。</div>';
    } else {
      return '<div style="background:#f8d7da; color:#721c24; padding:15px; border-radius:8px; margin:15px 0;"><strong>✗ 文档已篡改：</strong>文档内容与签名时不一致，可能已被修改。就像信封被拆开过，内容可能已被替换。</div>';
    }
  }

  private getTimestampExplanation(timestamp: TimestampResult): string {
    if (!timestamp.hasTimestamp) {
      return '<div style="background:#e2e3e5; color:#383d41; padding:15px; border-radius:8px; margin:15px 0;"><strong>ℹ 无时间戳：</strong>该签名未包含可信时间戳，无法证明签名的确切时间。</div>';
    }
    if (timestamp.isValid) {
      return `<div style="background:#d4edda; color:#155724; padding:15px; border-radius:8px; margin:15px 0;"><strong>✓ 时间戳有效：</strong>时间戳由可信机构签发，可以证明该签名于 <strong>${this.formatDate(timestamp.timestampTime)}</strong> 之前已存在，无法被事后篡改。</div>`;
    } else {
      return '<div style="background:#f8d7da; color:#721c24; padding:15px; border-radius:8px; margin:15px 0;"><strong>✗ 时间戳无效：</strong>时间戳验证失败，签名的准确时间无法确认。</div>';
    }
  }

  private getComplianceExplanation(compliance: ComplianceResult): string {
    if (compliance.overallCompliance === 'compliant') {
      return '<div style="background:#d4edda; color:#155724; padding:15px; border-radius:8px; margin:15px 0;"><strong>✓ 完全合规：</strong>该电子签名满足相关法律法规对"可靠电子签名"的要求，与手写签名具有同等法律效力。</div>';
    } else if (compliance.overallCompliance === 'partially-compliant') {
      return '<div style="background:#fff3cd; color:#856404; padding:15px; border-radius:8px; margin:15px 0;"><strong>⚠ 部分合规：</strong>该签名基本满足法律要求，但部分条件未完全满足，建议在重要法律场景中谨慎使用。</div>';
    } else {
      return '<div style="background:#f8d7da; color:#721c24; padding:15px; border-radius:8px; margin:15px 0;"><strong>✗ 不合规：</strong>该签名不满足法律法规对可靠电子签名的要求，可能不具备完整的法律效力。</div>';
    }
  }

  generateHTMLReport(verificationResult: VerifyResponse): string {
    const { fileInfo, overallResult, score, signatureFormat, results } = verificationResult;
    const { certificateChain, timestamp, integrity, compliance } = results;

    const overallResultText = this.getOverallResultText(overallResult);
    const overallResultColor = this.getOverallResultColor(overallResult);

    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>电子签名验证报告</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'SimSun', '宋体', 'Microsoft YaHei', sans-serif;
      background: #f5f5f5;
      padding: 40px;
      color: #333;
      line-height: 1.8;
    }
    .report-container {
      max-width: 900px;
      margin: 0 auto;
      background: #fff;
      padding: 60px;
      box-shadow: 0 2px 15px rgba(0,0,0,0.1);
    }
    .report-header {
      text-align: center;
      border-bottom: 3px double #000;
      padding-bottom: 30px;
      margin-bottom: 40px;
    }
    .report-title {
      font-size: 28px;
      font-weight: bold;
      letter-spacing: 4px;
      margin-bottom: 20px;
    }
    .report-subtitle {
      font-size: 14px;
      color: #666;
      margin-bottom: 10px;
    }
    .report-meta {
      font-size: 13px;
      color: #888;
    }
    .verification-conclusion {
      background: #fafafa;
      border: 1px solid #e0e0e0;
      border-left: 4px solid ${overallResultColor};
      padding: 25px 30px;
      margin-bottom: 40px;
    }
    .conclusion-title {
      font-size: 16px;
      font-weight: bold;
      margin-bottom: 15px;
    }
    .conclusion-result {
      font-size: 24px;
      font-weight: bold;
      color: ${overallResultColor};
      margin-bottom: 10px;
    }
    .conclusion-score {
      font-size: 14px;
      color: #666;
    }
    .section {
      margin-bottom: 35px;
    }
    .section-title {
      font-size: 18px;
      font-weight: bold;
      border-bottom: 2px solid #333;
      padding-bottom: 8px;
      margin-bottom: 20px;
    }
    .info-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 15px;
    }
    .info-table td {
      padding: 10px 15px;
      border: 1px solid #e0e0e0;
      font-size: 13px;
    }
    .info-table td:first-child {
      width: 180px;
      background: #f8f9fa;
      font-weight: bold;
    }
    .cert-card {
      border: 1px solid #e0e0e0;
      padding: 20px;
      margin-bottom: 15px;
      background: #fafafa;
    }
    .cert-header {
      font-weight: bold;
      margin-bottom: 15px;
      padding-bottom: 10px;
      border-bottom: 1px dashed #ccc;
    }
    .cert-level {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 3px;
      font-size: 12px;
      margin-right: 10px;
    }
    .cert-level-root { background: #d4edda; color: #155724; }
    .cert-level-intermediate { background: #fff3cd; color: #856404; }
    .cert-level-end-entity { background: #cce5ff; color: #004085; }
    .status-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 4px;
      font-size: 13px;
      font-weight: bold;
    }
    .status-valid { background: #d4edda; color: #155724; }
    .status-invalid { background: #f8d7da; color: #721c24; }
    .status-warning { background: #fff3cd; color: #856404; }
    .status-unknown { background: #e2e3e5; color: #383d41; }
    .compliance-item {
      border: 1px solid #e0e0e0;
      padding: 15px 20px;
      margin-bottom: 10px;
    }
    .compliance-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .compliance-name {
      font-weight: bold;
      font-size: 14px;
    }
    .compliance-description {
      font-size: 13px;
      color: #666;
      margin-bottom: 8px;
    }
    .compliance-evidence {
      font-size: 12px;
      color: #888;
      font-style: italic;
    }
    .error-list, .warning-list {
      margin: 10px 0;
      padding-left: 25px;
    }
    .error-list li {
      color: #dc3545;
      font-size: 13px;
    }
    .warning-list li {
      color: #ffc107;
      font-size: 13px;
    }
    .report-footer {
      margin-top: 60px;
      padding-top: 30px;
      border-top: 1px solid #e0e0e0;
      text-align: center;
      font-size: 12px;
      color: #888;
    }
    .hash-value {
      font-family: 'Courier New', monospace;
      font-size: 12px;
      color: #666;
      word-break: break-all;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 15px;
      margin-bottom: 20px;
    }
    .summary-item {
      text-align: center;
      padding: 20px;
      border: 1px solid #e0e0e0;
      background: #fafafa;
    }
    .summary-item-value {
      font-size: 24px;
      font-weight: bold;
      margin-bottom: 5px;
    }
    .summary-item-label {
      font-size: 12px;
      color: #666;
    }
  </style>
</head>
<body>
  <div class="report-container">
    <div class="report-header">
      <div class="report-title">电子签名验证报告</div>
      <div class="report-subtitle">DIGITAL SIGNATURE VERIFICATION REPORT</div>
      <div class="report-meta">
        验证编号：${this.verificationId} | 验证日期：${this.formatDate(this.verificationDate)}
      </div>
    </div>

    <div class="verification-conclusion">
      <div class="conclusion-title">验证结论</div>
      <div class="conclusion-result">${overallResultText}</div>
      <div class="conclusion-score">综合评分：${score}/100 | 签名格式：${signatureFormat}</div>
      <div style="margin-top:15px; padding-top:15px; border-top:1px dashed #ddd; font-size:13px; color:#666; line-height:1.8;">
        <p><strong>什么是电子签名验证？</strong></p>
        <p>电子签名验证就像验证一封挂号信的真实性：我们检查信封是否完好（文档完整性）、邮戳是否真实（时间戳）、寄件人身份是否可信（证书链），以及是否符合法律规定（合规性检查）。</p>
        <p style="margin-top:8px;">本报告从四个维度进行了专业验证，确保结果准确可靠。</p>
      </div>
    </div>

    <div class="section">
      <div class="section-title">一、文件信息</div>
      <table class="info-table">
        <tr>
          <td>文件名称</td>
          <td>${fileInfo.name}</td>
        </tr>
        <tr>
          <td>文件大小</td>
          <td>${this.formatFileSize(fileInfo.size)}</td>
        </tr>
        <tr>
          <td>文件类型</td>
          <td>${fileInfo.type}</td>
        </tr>
        <tr>
          <td>文件哈希</td>
          <td><span class="hash-value">${fileInfo.hash}</span></td>
        </tr>
      </table>
    </div>

    <div class="section">
      <div class="section-title">二、验证概览</div>
      <div class="summary-grid">
        <div class="summary-item">
          <div class="summary-item-value" style="color: ${certificateChain.isValid ? '#28a745' : '#dc3545'}">
            ${certificateChain.isValid ? '✓' : '✗'}
          </div>
          <div class="summary-item-label">证书链验证</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-value" style="color: ${timestamp.isValid ? '#28a745' : '#dc3545'}">
            ${timestamp.isValid ? '✓' : '✗'}
          </div>
          <div class="summary-item-label">时间戳验证</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-value" style="color: ${integrity.isValid ? '#28a745' : '#dc3545'}">
            ${integrity.isValid ? '✓' : '✗'}
          </div>
          <div class="summary-item-label">完整性验证</div>
        </div>
        <div class="summary-item">
          <div class="summary-item-value" style="color: ${compliance.overallCompliance === 'compliant' ? '#28a745' : '#ffc107'}">
            ${compliance.score}
          </div>
          <div class="summary-item-label">合规性评分</div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">三、证书链详情</div>
      <div style="background:#f0f7ff; border-left:4px solid #165DFF; padding:15px; margin-bottom:20px; border-radius:4px;">
        <p style="color:#004085; font-size:13px; margin:0;">
          <strong>💡 什么是证书链？</strong> 证书链就像"身份证明"的传递链：根证书（公安局）→ 中间CA证书（派出所）→ 用户证书（个人身份证）。每一级都向上一级证明身份，最终追溯到受信任的根证书。
        </p>
      </div>
      ${this.getCertificateChainDiagram(certificateChain.certificates)}
      <table class="info-table">
        <tr>
          <td>验证状态</td>
          <td>
            <span class="status-badge status-${certificateChain.isValid ? 'valid' : 'invalid'}">
              ${certificateChain.isValid ? '有效' : '无效'}
            </span>
          </td>
        </tr>
        <tr>
          <td>证书数量</td>
          <td>${certificateChain.certificates.length} 个</td>
        </tr>
        <tr>
          <td>信任路径</td>
          <td>${certificateChain.trustPath.join(' → ') || 'N/A'}</td>
        </tr>
        <tr>
          <td>吊销状态</td>
          <td>
            <span class="status-badge status-${certificateChain.revocationStatus === 'valid' ? 'valid' : certificateChain.revocationStatus === 'revoked' ? 'invalid' : 'unknown'}">
              ${certificateChain.revocationStatus === 'valid' ? '未吊销' : certificateChain.revocationStatus === 'revoked' ? '已吊销' : '未知'}
            </span>
          </td>
        </tr>
      </table>
      ${certificateChain.certificates.map((cert, index) => this.renderCertificateHTML(cert, index, certificateChain.certificates.length)).join('')}
      ${certificateChain.errors.length > 0 ? `
        <div style="margin-top: 15px;">
          <strong>错误信息：</strong>
          <ul class="error-list">
            ${certificateChain.errors.map(e => `<li>${e}</li>`).join('')}
          </ul>
        </div>
      ` : ''}
      ${certificateChain.warnings.length > 0 ? `
        <div style="margin-top: 15px;">
          <strong>警告信息：</strong>
          <ul class="warning-list">
            ${certificateChain.warnings.map(w => `<li>${w}</li>`).join('')}
          </ul>
        </div>
      ` : ''}
    </div>

    <div class="section">
      <div class="section-title">四、时间戳详情</div>
      ${this.getTimestampExplanation(timestamp)}
      <table class="info-table">
        <tr>
          <td>存在时间戳</td>
          <td>${timestamp.hasTimestamp ? '是' : '否'}</td>
        </tr>
        <tr>
          <td>验证状态</td>
          <td>
            <span class="status-badge status-${timestamp.isValid ? 'valid' : 'invalid'}">
              ${timestamp.isValid ? '有效' : '无效'}
            </span>
          </td>
        </tr>
        <tr>
          <td>时间戳时间</td>
          <td>${this.formatDate(timestamp.timestampTime)}</td>
        </tr>
        <tr>
          <td>时间戳机构</td>
          <td>${timestamp.timestampAuthority || 'N/A'}</td>
        </tr>
        <tr>
          <td>哈希算法</td>
          <td>${timestamp.hashAlgorithm || 'N/A'}</td>
        </tr>
        <tr>
          <td>消息印记</td>
          <td><span class="hash-value">${timestamp.messageImprint || 'N/A'}</span></td>
        </tr>
      </table>
      ${timestamp.certificateChain.length > 0 ? `
        <div style="margin-top: 20px;">
          <strong>时间戳证书链：</strong>
          ${timestamp.certificateChain.map((cert, index) => this.renderCertificateHTML(cert, index, timestamp.certificateChain.length)).join('')}
        </div>
      ` : ''}
      ${timestamp.errors.length > 0 ? `
        <div style="margin-top: 15px;">
          <strong>错误信息：</strong>
          <ul class="error-list">
            ${timestamp.errors.map(e => `<li>${e}</li>`).join('')}
          </ul>
        </div>
      ` : ''}
      ${timestamp.warnings.length > 0 ? `
        <div style="margin-top: 15px;">
          <strong>警告信息：</strong>
          <ul class="warning-list">
            ${timestamp.warnings.map(w => `<li>${w}</li>`).join('')}
          </ul>
        </div>
      ` : ''}
    </div>

    <div class="section">
      <div class="section-title">五、完整性验证结果</div>
      ${this.getIntegrityExplanation(integrity)}
      <table class="info-table">
        <tr>
          <td>验证状态</td>
          <td>
            <span class="status-badge status-${integrity.isValid ? 'valid' : 'invalid'}">
              ${integrity.isValid ? '完整' : '已篡改'}
            </span>
          </td>
        </tr>
        <tr>
          <td>文档哈希</td>
          <td><span class="hash-value">${integrity.documentHash}</span></td>
        </tr>
        <tr>
          <td>签名哈希</td>
          <td><span class="hash-value">${integrity.signedHash}</span></td>
        </tr>
        <tr>
          <td>哈希匹配</td>
          <td>${integrity.hashMatch ? '是' : '否'}</td>
        </tr>
        <tr>
          <td>签名算法</td>
          <td>${integrity.signatureAlgorithm}</td>
        </tr>
        <tr>
          <td>签名时间</td>
          <td>${this.formatDate(integrity.signingTime)}</td>
        </tr>
        <tr>
          <td>是否被篡改</td>
          <td>${integrity.hasModifications ? '是' : '否'}</td>
        </tr>
      </table>
      ${integrity.errors.length > 0 ? `
        <div style="margin-top: 15px;">
          <strong>错误信息：</strong>
          <ul class="error-list">
            ${integrity.errors.map(e => `<li>${e}</li>`).join('')}
          </ul>
        </div>
      ` : ''}
      ${integrity.warnings.length > 0 ? `
        <div style="margin-top: 15px;">
          <strong>警告信息：</strong>
          <ul class="warning-list">
            ${integrity.warnings.map(w => `<li>${w}</li>`).join('')}
          </ul>
        </div>
      ` : ''}
    </div>

    <div class="section">
      <div class="section-title">六、合规性检查结果</div>
      ${this.getComplianceExplanation(compliance)}
      <table class="info-table">
        <tr>
          <td>合规标准</td>
          <td>${compliance.standard}</td>
        </tr>
        <tr>
          <td>整体合规性</td>
          <td>
            <span class="status-badge status-${compliance.overallCompliance === 'compliant' ? 'valid' : compliance.overallCompliance === 'partially-compliant' ? 'warning' : 'invalid'}">
              ${compliance.overallCompliance === 'compliant' ? '合规' : compliance.overallCompliance === 'partially-compliant' ? '部分合规' : '不合规'}
            </span>
          </td>
        </tr>
        <tr>
          <td>合规评分</td>
          <td>${compliance.score}/100</td>
        </tr>
      </table>
      <div style="margin-top: 20px;">
        ${compliance.checks.map(check => this.renderComplianceCheckHTML(check)).join('')}
      </div>
    </div>

    <div class="report-footer">
      <p>📌 本报告由电子签名验证工具自动生成，验证结果仅代表对上传文件在验证时刻的技术检测结论。</p>
      <p style="margin-top: 5px;">本报告不构成法律意见，如有法律争议请咨询专业法律人士。</p>
      <p style="margin-top: 5px;">报告编号：${this.verificationId} | 生成时间：${this.formatDate(this.verificationDate)}</p>
    </div>
  </div>
</body>
</html>`;
  }

  private renderCertificateHTML(cert: CertificateInfo, index: number, total: number): string {
    let levelClass = 'cert-level-end-entity';
    let levelText = '实体证书';
    if (index === total - 1) {
      levelClass = 'cert-level-root';
      levelText = '根证书';
    } else if (index < total - 1) {
      levelClass = 'cert-level-intermediate';
      levelText = '中间证书';
    }

    return `
      <div class="cert-card">
        <div class="cert-header">
          <span class="cert-level ${levelClass}">${levelText}</span>
          证书 ${index + 1}/${total}：${cert.subject}
        </div>
        <table class="info-table">
          <tr>
            <td>主题</td>
            <td>${cert.subject}</td>
          </tr>
          <tr>
            <td>颁发者</td>
            <td>${cert.issuer}</td>
          </tr>
          <tr>
            <td>序列号</td>
            <td><span class="hash-value">${cert.serialNumber}</span></td>
          </tr>
          <tr>
            <td>有效期</td>
            <td>${this.formatDate(cert.validFrom)} 至 ${this.formatDate(cert.validTo)}</td>
          </tr>
          <tr>
            <td>指纹</td>
            <td><span class="hash-value">${cert.fingerprint}</span></td>
          </tr>
          <tr>
            <td>签名算法</td>
            <td>${cert.signatureAlgorithm}</td>
          </tr>
          <tr>
            <td>密钥用途</td>
            <td>${cert.keyUsage.join(', ') || 'N/A'}</td>
          </tr>
          <tr>
            <td>证书类型</td>
            <td>${cert.isCA ? 'CA证书' : '实体证书'} ${cert.isSelfSigned ? '(自签名)' : ''} ${cert.isTrustedRoot ? '(受信任根)' : ''}</td>
          </tr>
        </table>
      </div>
    `;
  }

  private renderComplianceCheckHTML(check: ComplianceCheck): string {
    const statusColor = this.getComplianceStatusColor(check.status);
    const statusText = this.getComplianceStatusText(check.status);

    return `
      <div class="compliance-item">
        <div class="compliance-header">
          <span class="compliance-name">${check.name}</span>
          <span class="status-badge" style="background: ${statusColor}20; color: ${statusColor}">${statusText}</span>
        </div>
        <div class="compliance-description">${check.description}</div>
        <div class="compliance-description">法规依据：${check.regulation}</div>
        ${check.evidence ? `<div class="compliance-evidence">证据：${check.evidence}</div>` : ''}
      </div>
    `;
  }

  async generatePDFReport(verificationResult: VerifyResponse): Promise<Uint8Array> {
    const { fileInfo, overallResult, score, signatureFormat, results } = verificationResult;
    const { certificateChain, timestamp, integrity, compliance } = results;

    const doc = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    });

    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    let y = margin;

    const addText = (text: string, x: number, yPos: number, options: { fontSize?: number; bold?: boolean; color?: string; align?: string } = {}) => {
      const { fontSize = 12, bold = false, color = '#000000', align = 'left' } = options;
      doc.setFontSize(fontSize);
      doc.setFont('helvetica', bold ? 'bold' : 'normal');
      doc.setTextColor(color);
      doc.text(text, x, yPos, { align: align as 'center' | 'left' | 'right' | 'justify' });
    };

    const addSection = (title: string, yPos: number): number => {
      doc.setDrawColor('#000000');
      doc.setLineWidth(0.5);
      doc.line(margin, yPos - 5, pageWidth - margin, yPos - 5);
      addText(title, margin, yPos, { fontSize: 14, bold: true });
      return yPos + 8;
    };

    const addTableRow = (label: string, value: string, yPos: number, isHash = false): number => {
      addText(label, margin + 2, yPos, { fontSize: 10, bold: true });
      const maxWidth = pageWidth - margin - 85;
      const textOptions = { fontSize: 10 };
      
      if (isHash) {
        doc.setFont('courier', 'normal');
        doc.setFontSize(9);
        doc.setTextColor('#666666');
      }
      
      const lines = doc.splitTextToSize(value, maxWidth);
      doc.text(lines, 85, yPos);
      
      if (isHash) {
        doc.setFont('helvetica', 'normal');
      }
      
      return yPos + Math.max(6, lines.length * 5);
    };

    const addStatusBadge = (text: string, x: number, yPos: number, color: string) => {
      doc.setFillColor(color);
      doc.roundedRect(x - 2, yPos - 4, doc.getTextWidth(text) + 8, 6, 1, 1, 'F');
      doc.setTextColor('#ffffff');
      addText(text, x + 2, yPos, { fontSize: 9, bold: true });
      doc.setTextColor('#000000');
    };

    const checkNewPage = (yPos: number, needed: number): number => {
      if (yPos + needed > pageHeight - margin) {
        doc.addPage();
        return margin;
      }
      return yPos;
    };

    addText('电子签名验证报告', pageWidth / 2, y, { fontSize: 22, bold: true, align: 'center' });
    y += 8;
    addText('DIGITAL SIGNATURE VERIFICATION REPORT', pageWidth / 2, y, { fontSize: 10, color: '#666666', align: 'center' });
    y += 6;
    addText(`验证编号：${this.verificationId} | 验证日期：${this.formatDate(this.verificationDate)}`, pageWidth / 2, y, { fontSize: 9, color: '#888888', align: 'center' });
    y += 8;
    doc.setDrawColor('#000000');
    doc.setLineWidth(1);
    doc.line(margin, y, pageWidth - margin, y);
    y += 10;

    const overallResultText = this.getOverallResultText(overallResult);
    const overallResultColor = this.getOverallResultColor(overallResult);

    doc.setFillColor('#f5f5f5');
    doc.roundedRect(margin, y - 5, pageWidth - 2 * margin, 25, 2, 2, 'F');
    doc.setFillColor(overallResultColor);
    doc.rect(margin, y - 5, 3, 25, 'F');
    addText('验证结论', margin + 8, y, { fontSize: 12, bold: true });
    y += 6;
    addText(overallResultText, margin + 8, y, { fontSize: 18, bold: true, color: overallResultColor });
    y += 6;
    addText(`综合评分：${score}/100 | 签名格式：${signatureFormat}`, margin + 8, y, { fontSize: 10, color: '#666666' });
    y += 10;
    doc.setDrawColor('#dddddd');
    doc.setLineWidth(0.2);
    doc.line(margin + 8, y, pageWidth - margin - 8, y);
    y += 6;
    addText('什么是电子签名验证？', margin + 8, y, { fontSize: 10, bold: true, color: '#333333' });
    y += 5;
    const explainLines = doc.splitTextToSize('电子签名验证就像验证一封挂号信的真实性：我们检查信封是否完好（文档完整性）、邮戳是否真实（时间戳）、寄件人身份是否可信（证书链），以及是否符合法律规定（合规性检查）。', pageWidth - 2 * margin - 16);
    doc.setFontSize(9);
    doc.setTextColor('#666666');
    doc.text(explainLines, margin + 8, y);
    y += explainLines.length * 4.5 + 8;

    y = addSection('一、文件信息', y);
    y = addTableRow('文件名称', fileInfo.name, y);
    y = addTableRow('文件大小', this.formatFileSize(fileInfo.size), y);
    y = addTableRow('文件类型', fileInfo.type, y);
    y = addTableRow('文件哈希', fileInfo.hash, y, true);
    y += 5;

    y = checkNewPage(y, 40);
    y = addSection('二、验证概览', y);
    const summaryY = y;
    const summaryWidth = (pageWidth - 2 * margin - 15) / 4;
    
    const summaryItems = [
      { label: '证书链验证', value: certificateChain.isValid ? '✓' : '✗', color: certificateChain.isValid ? '#28a745' : '#dc3545' },
      { label: '时间戳验证', value: timestamp.isValid ? '✓' : '✗', color: timestamp.isValid ? '#28a745' : '#dc3545' },
      { label: '完整性验证', value: integrity.isValid ? '✓' : '✗', color: integrity.isValid ? '#28a745' : '#dc3545' },
      { label: '合规性评分', value: compliance.score.toString(), color: compliance.overallCompliance === 'compliant' ? '#28a745' : '#ffc107' }
    ];

    summaryItems.forEach((item, index) => {
      const x = margin + index * (summaryWidth + 5);
      doc.setFillColor('#f5f5f5');
      doc.roundedRect(x, y, summaryWidth, 20, 2, 2, 'F');
      addText(item.value, x + summaryWidth / 2, y + 8, { fontSize: 16, bold: true, color: item.color, align: 'center' });
      addText(item.label, x + summaryWidth / 2, y + 14, { fontSize: 8, color: '#666666', align: 'center' });
    });
    y += 25;

    y = checkNewPage(y, 100);
    y = addSection('三、证书链详情', y);
    doc.setFillColor('#f0f7ff');
    doc.roundedRect(margin, y - 2, pageWidth - 2 * margin, 12, 1, 1, 'F');
    doc.setFillColor('#165DFF');
    doc.rect(margin, y - 2, 1.5, 12, 'F');
    addText('什么是证书链？就像身份证明的传递链：根证书(公安局) → 中间CA(派出所) → 用户证书(个人身份证)', margin + 5, y + 5, { fontSize: 9, color: '#004085' });
    y += 16;
    if (certificateChain.certificates.length > 0) {
      const certNames = certificateChain.certificates.map((cert, i) => {
        const name = cert.subject.split(',').find((p: string) => p.startsWith('CN=')) || cert.subject;
        return name.replace('CN=', '').substring(0, 12);
      });
      const diagramText = certNames.join(' → ');
      addText(`证书链: ${diagramText}`, margin, y, { fontSize: 9, color: '#165DFF', bold: true });
      y += 6;
    }
    y = addTableRow('验证状态', certificateChain.isValid ? '有效' : '无效', y);
    y = addTableRow('证书数量', `${certificateChain.certificates.length} 个`, y);
    y = addTableRow('信任路径', certificateChain.trustPath.join(' → ') || 'N/A', y);
    const revStatus = certificateChain.revocationStatus === 'valid' ? '未吊销' : certificateChain.revocationStatus === 'revoked' ? '已吊销' : '未知';
    y = addTableRow('吊销状态', revStatus, y);
    y += 3;

    for (let i = 0; i < certificateChain.certificates.length; i++) {
      const cert = certificateChain.certificates[i];
      const total = certificateChain.certificates.length;
      y = checkNewPage(y, 50);
      
      let levelText = '实体证书';
      if (i === total - 1) levelText = '根证书';
      else if (i < total - 1) levelText = '中间证书';
      
      doc.setFillColor('#f5f5f5');
      doc.roundedRect(margin, y - 3, pageWidth - 2 * margin, 40, 1, 1, 'F');
      addText(`[${levelText}] 证书 ${i + 1}/${total}：${cert.subject}`, margin + 3, y, { fontSize: 10, bold: true });
      y += 6;
      y = addTableRow('主题', cert.subject, y);
      y = addTableRow('颁发者', cert.issuer, y);
      y = addTableRow('序列号', cert.serialNumber, y, true);
      y = addTableRow('有效期', `${this.formatDate(cert.validFrom)} 至 ${this.formatDate(cert.validTo)}`, y);
      y = addTableRow('指纹', cert.fingerprint, y, true);
      y = addTableRow('签名算法', cert.signatureAlgorithm, y);
      y = addTableRow('密钥用途', cert.keyUsage.join(', ') || 'N/A', y);
      const certType = `${cert.isCA ? 'CA证书' : '实体证书'}${cert.isSelfSigned ? ' (自签名)' : ''}${cert.isTrustedRoot ? ' (受信任根)' : ''}`;
      y = addTableRow('证书类型', certType, y);
      y += 5;
    }

    if (certificateChain.errors.length > 0) {
      y = checkNewPage(y, 15 + certificateChain.errors.length * 5);
      addText('错误信息：', margin, y, { fontSize: 10, bold: true, color: '#dc3545' });
      y += 5;
      certificateChain.errors.forEach(e => {
        addText(`• ${e}`, margin + 3, y, { fontSize: 9, color: '#dc3545' });
        y += 4;
      });
    }
    if (certificateChain.warnings.length > 0) {
      y = checkNewPage(y, 15 + certificateChain.warnings.length * 5);
      addText('警告信息：', margin, y, { fontSize: 10, bold: true, color: '#ffc107' });
      y += 5;
      certificateChain.warnings.forEach(w => {
        addText(`• ${w}`, margin + 3, y, { fontSize: 9, color: '#ffc107' });
        y += 4;
      });
    }
    y += 5;

    y = checkNewPage(y, 80);
    y = addSection('四、时间戳详情', y);
    const tsExplain = timestamp.hasTimestamp
      ? (timestamp.isValid
        ? `✓ 时间戳有效：时间戳由可信机构签发，证明该签名于 ${this.formatDate(timestamp.timestampTime)} 之前已存在`
        : '✗ 时间戳无效：时间戳验证失败，签名的准确时间无法确认')
      : 'ℹ 无时间戳：无法证明签名的确切时间';
    const tsColor = timestamp.hasTimestamp ? (timestamp.isValid ? '#28a745' : '#dc3545') : '#6c757d';
    doc.setFillColor(tsColor + '20');
    doc.roundedRect(margin, y - 2, pageWidth - 2 * margin, 10, 1, 1, 'F');
    addText(tsExplain, margin + 3, y + 4, { fontSize: 9, color: tsColor });
    y += 14;
    y = addTableRow('存在时间戳', timestamp.hasTimestamp ? '是' : '否', y);
    y = addTableRow('验证状态', timestamp.isValid ? '有效' : '无效', y);
    y = addTableRow('时间戳时间', this.formatDate(timestamp.timestampTime), y);
    y = addTableRow('时间戳机构', timestamp.timestampAuthority || 'N/A', y);
    y = addTableRow('哈希算法', timestamp.hashAlgorithm || 'N/A', y);
    y = addTableRow('消息印记', timestamp.messageImprint || 'N/A', y, true);

    if (timestamp.certificateChain.length > 0) {
      y += 5;
      addText('时间戳证书链：', margin, y, { fontSize: 10, bold: true });
      y += 5;
      for (let i = 0; i < timestamp.certificateChain.length; i++) {
        const cert = timestamp.certificateChain[i];
        y = checkNewPage(y, 35);
        doc.setFillColor('#f5f5f5');
        doc.roundedRect(margin, y - 2, pageWidth - 2 * margin, 30, 1, 1, 'F');
        addText(`证书 ${i + 1}：${cert.subject}`, margin + 3, y, { fontSize: 9, bold: true });
        y += 5;
        y = addTableRow('有效期', `${this.formatDate(cert.validFrom)} 至 ${this.formatDate(cert.validTo)}`, y);
        y = addTableRow('指纹', cert.fingerprint, y, true);
        y += 3;
      }
    }

    if (timestamp.errors.length > 0) {
      y = checkNewPage(y, 15 + timestamp.errors.length * 5);
      addText('错误信息：', margin, y, { fontSize: 10, bold: true, color: '#dc3545' });
      y += 5;
      timestamp.errors.forEach(e => {
        addText(`• ${e}`, margin + 3, y, { fontSize: 9, color: '#dc3545' });
        y += 4;
      });
    }
    if (timestamp.warnings.length > 0) {
      y = checkNewPage(y, 15 + timestamp.warnings.length * 5);
      addText('警告信息：', margin, y, { fontSize: 10, bold: true, color: '#ffc107' });
      y += 5;
      timestamp.warnings.forEach(w => {
        addText(`• ${w}`, margin + 3, y, { fontSize: 9, color: '#ffc107' });
        y += 4;
      });
    }
    y += 5;

    y = checkNewPage(y, 80);
    y = addSection('五、完整性验证结果', y);
    const intExplain = integrity.hashMatch
      ? '✓ 文档完整：文档内容与签名时完全一致，就像密封的信封，封口完好无损'
      : '✗ 文档已篡改：文档内容与签名时不一致，可能已被修改，就像信封被拆开过';
    const intColor = integrity.hashMatch ? '#28a745' : '#dc3545';
    doc.setFillColor(intColor + '20');
    doc.roundedRect(margin, y - 2, pageWidth - 2 * margin, 10, 1, 1, 'F');
    addText(intExplain, margin + 3, y + 4, { fontSize: 9, color: intColor });
    y += 14;
    y = addTableRow('验证状态', integrity.isValid ? '完整' : '已篡改', y);
    y = addTableRow('文档哈希', integrity.documentHash, y, true);
    y = addTableRow('签名哈希', integrity.signedHash, y, true);
    y = addTableRow('哈希匹配', integrity.hashMatch ? '是' : '否', y);
    y = addTableRow('签名算法', integrity.signatureAlgorithm, y);
    y = addTableRow('签名时间', this.formatDate(integrity.signingTime), y);
    y = addTableRow('是否被篡改', integrity.hasModifications ? '是' : '否', y);

    if (integrity.errors.length > 0) {
      y = checkNewPage(y, 15 + integrity.errors.length * 5);
      addText('错误信息：', margin, y, { fontSize: 10, bold: true, color: '#dc3545' });
      y += 5;
      integrity.errors.forEach(e => {
        addText(`• ${e}`, margin + 3, y, { fontSize: 9, color: '#dc3545' });
        y += 4;
      });
    }
    if (integrity.warnings.length > 0) {
      y = checkNewPage(y, 15 + integrity.warnings.length * 5);
      addText('警告信息：', margin, y, { fontSize: 10, bold: true, color: '#ffc107' });
      y += 5;
      integrity.warnings.forEach(w => {
        addText(`• ${w}`, margin + 3, y, { fontSize: 9, color: '#ffc107' });
        y += 4;
      });
    }
    y += 5;

    y = checkNewPage(y, 80);
    y = addSection('六、合规性检查结果', y);
    const complianceStatus = compliance.overallCompliance === 'compliant' ? '合规' : compliance.overallCompliance === 'partially-compliant' ? '部分合规' : '不合规';
    let compExplain = '';
    let compColor = '#6c757d';
    if (compliance.overallCompliance === 'compliant') {
      compExplain = '✓ 完全合规：该电子签名满足法律法规对"可靠电子签名"的要求，与手写签名具有同等法律效力';
      compColor = '#28a745';
    } else if (compliance.overallCompliance === 'partially-compliant') {
      compExplain = '⚠ 部分合规：基本满足法律要求，但部分条件未完全满足，重要法律场景请谨慎使用';
      compColor = '#ffc107';
    } else {
      compExplain = '✗ 不合规：不满足法律法规对可靠电子签名的要求，可能不具备完整法律效力';
      compColor = '#dc3545';
    }
    doc.setFillColor(compColor + '20');
    doc.roundedRect(margin, y - 2, pageWidth - 2 * margin, 10, 1, 1, 'F');
    addText(compExplain, margin + 3, y + 4, { fontSize: 9, color: compColor });
    y += 14;
    y = addTableRow('合规标准', compliance.standard, y);
    y = addTableRow('整体合规性', complianceStatus, y);
    y = addTableRow('合规评分', `${compliance.score}/100`, y);
    y += 5;

    for (const check of compliance.checks) {
      y = checkNewPage(y, 25);
      const statusColor = this.getComplianceStatusColor(check.status);
      const statusText = this.getComplianceStatusText(check.status);
      
      doc.setFillColor('#f5f5f5');
      doc.roundedRect(margin, y - 3, pageWidth - 2 * margin, 18, 1, 1, 'F');
      
      addText(check.name, margin + 3, y, { fontSize: 10, bold: true });
      const statusX = pageWidth - margin - doc.getTextWidth(statusText) - 6;
      doc.setFillColor(statusColor);
      doc.roundedRect(statusX - 2, y - 4, doc.getTextWidth(statusText) + 8, 6, 1, 1, 'F');
      doc.setTextColor('#ffffff');
      addText(statusText, statusX + 2, y, { fontSize: 9, bold: true });
      doc.setTextColor('#000000');
      
      y += 5;
      addText(check.description, margin + 5, y, { fontSize: 9, color: '#666666' });
      y += 4;
      addText(`法规依据：${check.regulation}`, margin + 5, y, { fontSize: 9, color: '#666666' });
      y += 4;
      if (check.evidence) {
        doc.setFontStyle('italic');
        addText(`证据：${check.evidence}`, margin + 5, y, { fontSize: 8, color: '#888888' });
        doc.setFontStyle('normal');
        y += 4;
      }
      y += 3;
    }

    y = checkNewPage(y, 30);
    doc.setDrawColor('#e0e0e0');
    doc.setLineWidth(0.3);
    doc.line(margin, y, pageWidth - margin, y);
    y += 8;
    addText('📌 本报告由电子签名验证工具自动生成，验证结果仅代表对上传文件在验证时刻的技术检测结论。', pageWidth / 2, y, { fontSize: 9, color: '#888888', align: 'center' });
    y += 5;
    addText('本报告不构成法律意见，如有法律争议请咨询专业法律人士。', pageWidth / 2, y, { fontSize: 9, color: '#888888', align: 'center' });
    y += 5;
    addText(`报告编号：${this.verificationId} | 生成时间：${this.formatDate(this.verificationDate)}`, pageWidth / 2, y, { fontSize: 9, color: '#888888', align: 'center' });

    return new Uint8Array(doc.output('arraybuffer'));
  }

  async saveReportToFile(content: string | Uint8Array, format: 'html' | 'pdf'): Promise<string> {
    const tempDir = os.tmpdir();
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    const fileName = `verification-report-${timestamp}-${random}.${format}`;
    const filePath = path.join(tempDir, fileName);

    if (format === 'html') {
      await fs.promises.writeFile(filePath, content as string, 'utf-8');
    } else {
      await fs.promises.writeFile(filePath, Buffer.from(content as Uint8Array));
    }

    return filePath;
  }
}
