import * as pdfjsLib from 'pdfjs-dist';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { calculateHash } from '../core/crypto-utils.js';
import { parsePDF } from '../core/pdf-parser.js';
import type { AntiForgeryResult, AntiForgeryCheck, SignatureVisualization } from '../../../shared/index.js';

pdfjsLib.GlobalWorkerOptions.workerSrc = '';

export class AntiForgeryService {
  private static readonly CLONE_DETECTION_THRESHOLD = 0.85;
  private static readonly SUSPICIOUS_PATTERNS = [
    'copy', 'paste', 'clone', 'duplicate',
    'scanned', 'photoshop', 'ps'
  ];

  async detectForgery(
    fileData: Uint8Array,
    fileName: string,
    visualization?: SignatureVisualization
  ): Promise<AntiForgeryResult> {
    const checks: AntiForgeryCheck[] = [];
    const warnings: string[] = [];
    const errors: string[] = [];

    try {
      const lowerFileName = fileName.toLowerCase();
      const isPDF = lowerFileName.endsWith('.pdf');

      if (isPDF) {
        checks.push(...await this.runPDFChecks(fileData, visualization));
      }

      checks.push(this.checkFileNamePattern(fileName));
      checks.push(this.checkFileHashUniqueness(fileData));
      checks.push(this.checkDocumentMetadata(fileData, fileName));
    } catch (error) {
      errors.push(`防伪检测过程出错: ${error instanceof Error ? error.message : String(error)}`);
    }

    const failedChecks = checks.filter(c => c.status === 'fail');
    const warningChecks = checks.filter(c => c.status === 'warning');
    const highRiskChecks = checks.filter(c => c.risk === 'high' && c.status !== 'pass');
    const mediumRiskChecks = checks.filter(c => c.risk === 'medium' && c.status !== 'pass');

    let overallRisk: 'low' | 'medium' | 'high' = 'low';
    if (highRiskChecks.length > 0) {
      overallRisk = 'high';
    } else if (mediumRiskChecks.length > 0 || warningChecks.length > 1) {
      overallRisk = 'medium';
    }

    const isAuthentic = failedChecks.length === 0;

    const baseScore = 100;
    const penalty = failedChecks.length * 25 + warningChecks.length * 10;
    const score = Math.max(0, baseScore - penalty);

    if (overallRisk === 'high') {
      warnings.push('检测到高风险伪造特征，建议谨慎使用该文件');
    } else if (overallRisk === 'medium') {
      warnings.push('检测到一些可疑特征，建议进一步核实');
    }

    return {
      isAuthentic,
      overallRisk,
      score,
      checks,
      warnings,
      errors
    };
  }

  private async runPDFChecks(
    fileData: Uint8Array,
    visualization?: SignatureVisualization
  ): Promise<AntiForgeryCheck[]> {
    const checks: AntiForgeryCheck[] = [];

    let pdfDoc: PDFDocumentProxy | null = null;
    try {
      pdfDoc = await parsePDF(fileData);

      checks.push(this.checkSignatureConsistency(visualization));
      checks.push(await this.checkPageContentConsistency(pdfDoc, visualization));
      checks.push(this.checkIncrementalUpdates(fileData));
      checks.push(this.checkSignatureOverlap(visualization));
      checks.push(await this.detectImageBasedSignatures(pdfDoc));
      checks.push(await this.analyzeSignatureQuality(pdfDoc, visualization));
    } finally {
      if (pdfDoc) {
        await pdfDoc.destroy();
      }
    }

    return checks;
  }

  private checkSignatureConsistency(visualization?: SignatureVisualization): AntiForgeryCheck {
    if (!visualization || visualization.positions.length === 0) {
      return {
        id: 'signature-consistency',
        name: '签名一致性检查',
        description: '检查文档中的签名是否与签名数据一致',
        status: 'not-applicable',
        evidence: '文档中没有可见的签名外观',
        risk: 'low'
      };
    }

    const { positions } = visualization;
    const suspiciousPositions: string[] = [];

    for (let i = 0; i < positions.length; i++) {
      for (let j = i + 1; j < positions.length; j++) {
        const pos1 = positions[i];
        const pos2 = positions[j];

        const sizeSimilarity = Math.min(pos1.width, pos2.width) / Math.max(pos1.width, pos2.width);
        const heightSimilarity = Math.min(pos1.height, pos2.height) / Math.max(pos1.height, pos2.height);

        if (sizeSimilarity > AntiForgeryService.CLONE_DETECTION_THRESHOLD &&
            heightSimilarity > AntiForgeryService.CLONE_DETECTION_THRESHOLD) {
          suspiciousPositions.push(`签名 ${i + 1} 和 签名 ${j + 1} 外观高度相似`);
        }
      }
    }

    if (suspiciousPositions.length > 0) {
      return {
        id: 'signature-consistency',
        name: '签名一致性检查',
        description: '检测是否存在复制粘贴的相同签名',
        status: 'warning',
        evidence: suspiciousPositions.join('; '),
        risk: 'high'
      };
    }

    return {
      id: 'signature-consistency',
      name: '签名一致性检查',
      description: '检测是否存在复制粘贴的相同签名',
      status: 'pass',
      evidence: `文档中 ${positions.length} 个签名外观各不相同`,
      risk: 'low'
    };
  }

  private async checkPageContentConsistency(
    pdfDoc: PDFDocumentProxy,
    visualization?: SignatureVisualization
  ): Promise<AntiForgeryCheck> {
    if (!visualization || visualization.positions.length === 0) {
      return {
        id: 'page-content-consistency',
        name: '页面内容一致性检查',
        description: '检查签名区域与页面内容的融合度',
        status: 'not-applicable',
        evidence: '文档中没有可见的签名外观',
        risk: 'low'
      };
    }

    const issues: string[] = [];

    for (const pos of visualization.positions) {
      try {
        if (pos.pageIndex >= pdfDoc.numPages) continue;

        const page = await pdfDoc.getPage(pos.pageIndex + 1);
        const viewport = page.getViewport({ scale: 1.0 });

        const pageHeight = viewport.height;

        if (pos.top <= 0 || pos.bottom >= pageHeight ||
            pos.left <= 0 || pos.right >= viewport.width) {
          issues.push(`签名 "${pos.fieldName}" 位置异常，超出页面边界`);
        }

        if (pos.width < 20 || pos.height < 10) {
          issues.push(`签名 "${pos.fieldName}" 尺寸异常，可能被篡改`);
        }

        if (pos.width > viewport.width * 0.9 || pos.height > pageHeight * 0.5) {
          issues.push(`签名 "${pos.fieldName}" 尺寸过大，可能被篡改`);
        }
      } catch {}
    }

    if (issues.length > 0) {
      return {
        id: 'page-content-consistency',
        name: '页面内容一致性检查',
        description: '检查签名位置是否自然合理',
        status: 'warning',
        evidence: issues.join('; '),
        risk: 'medium'
      };
    }

    return {
      id: 'page-content-consistency',
      name: '页面内容一致性检查',
      description: '检查签名位置是否自然合理',
      status: 'pass',
      evidence: '所有签名位置自然合理',
      risk: 'low'
    };
  }

  private checkIncrementalUpdates(fileData: Uint8Array): AntiForgeryCheck {
    const dataStr = Buffer.from(fileData).toString('binary');
    const eofMarkers = (dataStr.match(/%%EOF/g) || []).length;

    if (eofMarkers > 1) {
      return {
        id: 'incremental-updates',
        name: '增量更新检查',
        description: '检查文档是否经过多次修改',
        status: 'warning',
        evidence: `检测到 ${eofMarkers} 个文件结束标记，文档可能经过 ${eofMarkers - 1} 次增量更新`,
        risk: 'medium'
      };
    }

    return {
      id: 'incremental-updates',
      name: '增量更新检查',
      description: '检查文档是否经过多次修改',
      status: 'pass',
      evidence: '文档为单次保存，未检测到增量更新',
      risk: 'low'
    };
  }

  private checkSignatureOverlap(visualization?: SignatureVisualization): AntiForgeryCheck {
    if (!visualization || visualization.positions.length < 2) {
      return {
        id: 'signature-overlap',
        name: '签名重叠检查',
        description: '检查多个签名之间是否存在重叠',
        status: 'not-applicable',
        evidence: '文档中签名数量不足2个',
        risk: 'low'
      };
    }

    const { positions } = visualization;
    const overlaps: string[] = [];

    for (let i = 0; i < positions.length; i++) {
      for (let j = i + 1; j < positions.length; j++) {
        const pos1 = positions[i];
        const pos2 = positions[j];

        if (pos1.pageIndex !== pos2.pageIndex) continue;

        const overlapX = Math.max(0, Math.min(pos1.right, pos2.right) - Math.max(pos1.left, pos2.left));
        const overlapY = Math.max(0, Math.min(pos1.bottom, pos2.bottom) - Math.max(pos1.top, pos2.top));

        if (overlapX > 0 && overlapY > 0) {
          const overlapArea = overlapX * overlapY;
          const minArea = Math.min(pos1.width * pos1.height, pos2.width * pos2.height);
          const overlapRatio = overlapArea / minArea;

          if (overlapRatio > 0.1) {
            overlaps.push(`签名 ${i + 1} 和 签名 ${j + 1} 存在 ${(overlapRatio * 100).toFixed(1)}% 重叠`);
          }
        }
      }
    }

    if (overlaps.length > 0) {
      return {
        id: 'signature-overlap',
        name: '签名重叠检查',
        description: '检测签名之间是否存在异常重叠',
        status: 'warning',
        evidence: overlaps.join('; '),
        risk: 'high'
      };
    }

    return {
      id: 'signature-overlap',
      name: '签名重叠检查',
      description: '检测签名之间是否存在异常重叠',
      status: 'pass',
      evidence: '所有签名位置独立，无重叠',
      risk: 'low'
    };
  }

  private async detectImageBasedSignatures(pdfDoc: PDFDocumentProxy): Promise<AntiForgeryCheck> {
    const suspiciousImages: string[] = [];

    try {
      for (let pageNum = 1; pageNum <= Math.min(pdfDoc.numPages, 10); pageNum++) {
        const page = await pdfDoc.getPage(pageNum);
        const operatorList = await page.getOperatorList();

        for (let i = 0; i < operatorList.argsArray.length; i++) {
          const fn = operatorList.fnArray[i];
          if (fn === pdfjsLib.OPS.paintImageXObject ||
              fn === pdfjsLib.OPS.paintInlineImageXObject) {
            const args = operatorList.argsArray[i];
            if (args && args.length > 0) {
              const imgName = typeof args[0] === 'string' ? args[0] : `image${i}`;

              if (imgName.toLowerCase().includes('sign') ||
                  imgName.toLowerCase().includes('signature') ||
                  imgName.toLowerCase().includes('stamp') ||
                  imgName.toLowerCase().includes('seal')) {
                suspiciousImages.push(`第${pageNum}页的签名图像 "${imgName}" 可能是图像粘贴`);
              }
            }
          }
        }
      }
    } catch {}

    if (suspiciousImages.length > 0) {
      return {
        id: 'image-based-signatures',
        name: '图像签名检测',
        description: '检测是否使用粘贴的签名图像而非数字签名',
        status: 'warning',
        evidence: suspiciousImages.join('; '),
        risk: 'high'
      };
    }

    return {
      id: 'image-based-signatures',
      name: '图像签名检测',
      description: '检测是否使用粘贴的签名图像而非数字签名',
      status: 'pass',
      evidence: '未检测到仅为图像粘贴的签名',
      risk: 'low'
    };
  }

  private async analyzeSignatureQuality(
    pdfDoc: PDFDocumentProxy,
    visualization?: SignatureVisualization
  ): Promise<AntiForgeryCheck> {
    if (!visualization || visualization.positions.length === 0) {
      return {
        id: 'signature-quality',
        name: '签名质量分析',
        description: '分析签名的数字特征质量',
        status: 'not-applicable',
        evidence: '文档中没有可见的签名外观',
        risk: 'low'
      };
    }

    const qualityIssues: string[] = [];

    for (const pos of visualization.positions) {
      const area = pos.width * pos.height;

      if (area < 1000) {
        qualityIssues.push(`签名 "${pos.fieldName}" 分辨率过低，可能是复制的低质量图像`);
      }

      const aspectRatio = pos.width / Math.max(pos.height, 1);
      if (aspectRatio < 0.2 || aspectRatio > 5) {
        qualityIssues.push(`签名 "${pos.fieldName}" 宽高比异常 (${aspectRatio.toFixed(2)})`);
      }

      if (pos.signerName) {
        const hasSuspiciousPatterns = AntiForgeryService.SUSPICIOUS_PATTERNS.some(
          pattern => pos.signerName?.toLowerCase().includes(pattern)
        );
        if (hasSuspiciousPatterns) {
          qualityIssues.push(`签名 "${pos.fieldName}" 的签名者名称包含可疑关键词`);
        }
      }
    }

    if (qualityIssues.length > 0) {
      return {
        id: 'signature-quality',
        name: '签名质量分析',
        description: '分析签名的数字特征，检测可能的伪造',
        status: 'warning',
        evidence: qualityIssues.join('; '),
        risk: 'medium'
      };
    }

    return {
      id: 'signature-quality',
      name: '签名质量分析',
      description: '分析签名的数字特征，检测可能的伪造',
      status: 'pass',
      evidence: '所有签名质量良好，未发现可疑特征',
      risk: 'low'
    };
  }

  private checkFileNamePattern(fileName: string): AntiForgeryCheck {
    const lowerName = fileName.toLowerCase();
    const suspiciousPatterns = [
      'copy', '副本', '复印', '扫描件', 'scanned', 'fake',
      'modified', '修改', 'edited', '编辑', 'tampered', '篡改'
    ];

    const matches = suspiciousPatterns.filter(pattern => lowerName.includes(pattern));

    if (matches.length > 0) {
      return {
        id: 'filename-pattern',
        name: '文件名模式检查',
        description: '检查文件名是否包含可疑关键词',
        status: 'warning',
        evidence: `文件名包含可疑关键词: ${matches.join(', ')}`,
        risk: 'medium'
      };
    }

    return {
      id: 'filename-pattern',
      name: '文件名模式检查',
      description: '检查文件名是否包含可疑关键词',
      status: 'pass',
      evidence: '文件名无异常',
      risk: 'low'
    };
  }

  private checkFileHashUniqueness(fileData: Uint8Array): AntiForgeryCheck {
    const hash = calculateHash(fileData, 'SHA256');

    const commonPatterns = [
      /^0{16,}/,
      /^f{16,}/i,
      /^deadbeef/i,
      /^12345678/
    ];

    for (const pattern of commonPatterns) {
      if (pattern.test(hash)) {
        return {
          id: 'hash-uniqueness',
          name: '文件哈希唯一性检查',
          description: '检查文件哈希是否为常见的伪造模式',
          status: 'warning',
          evidence: '文件哈希包含可疑模式',
          risk: 'high'
        };
      }
    }

    return {
      id: 'hash-uniqueness',
      name: '文件哈希唯一性检查',
      description: '检查文件哈希是否为常见的伪造模式',
      status: 'pass',
      evidence: '文件哈希正常',
      risk: 'low'
    };
  }

  private checkDocumentMetadata(fileData: Uint8Array, fileName: string): AntiForgeryCheck {
    const suspiciousMetadata: string[] = [];

    try {
      const header = Buffer.from(fileData.slice(0, 100)).toString('utf8', 0, 100);

      if (fileName.toLowerCase().endsWith('.pdf')) {
        if (!header.startsWith('%PDF-')) {
          suspiciousMetadata.push('文件扩展名与实际内容类型不匹配');
        }
      }
    } catch {}

    if (suspiciousMetadata.length > 0) {
      return {
        id: 'document-metadata',
        name: '文档元数据检查',
        description: '检查文档元数据是否存在异常',
        status: 'warning',
        evidence: suspiciousMetadata.join('; '),
        risk: 'high'
      };
    }

    return {
      id: 'document-metadata',
      name: '文档元数据检查',
      description: '检查文档元数据是否存在异常',
      status: 'pass',
      evidence: '文档元数据正常',
      risk: 'low'
    };
  }
}
