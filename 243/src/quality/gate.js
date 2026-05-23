const fs = require('fs-extra');
const path = require('path');

class QualityGate {
  constructor({ logger, config }) {
    this.logger = logger;
    this.config = config;
    this.parsers = this.setupParsers();
  }

  setupParsers() {
    return {
      'istanbul-json': this.parseIstanbulJson.bind(this),
      'jacoco-csv': this.parseJacocoCsv.bind(this),
      'cobertura-xml': this.parseCoberturaXml.bind(this),
      'golang-cover': this.parseGoCover.bind(this),
      'pytest-cov': this.parsePytestCov.bind(this)
    };
  }

  async checkQualityGate(stageConfig, workspace, context) {
    const qualityGate = stageConfig.qualityGate;
    if (!qualityGate) {
      return { passed: true, skipped: true, message: '未配置质量红线' };
    }

    this.logger.info('开始检查质量红线', { 
      stage: stageConfig.name,
      threshold: qualityGate.coverageThreshold 
    });

    try {
      const coverageFile = qualityGate.coverageFile;
      const filePath = path.join(workspace, coverageFile || '');
      
      if (!await fs.pathExists(filePath)) {
        return {
          passed: false,
          error: `覆盖率文件不存在: ${coverageFile}`,
          suggestions: [
            '检查测试命令是否生成了覆盖率报告',
            '确认coverageFile路径配置是否正确',
            '查看测试阶段日志确认执行情况'
          ]
        };
      }

      const coverage = await this.parseCoverageFile(filePath, qualityGate.format, qualityGate.coverageFile);
      const threshold = qualityGate.coverageThreshold || this.config.qualityGate?.defaultThreshold || 80;
      const passed = coverage.total >= threshold;

      const result = {
        passed,
        coverage,
        threshold,
        metrics: {
          total: coverage.total,
          lines: coverage.lines,
          statements: coverage.statements,
          functions: coverage.functions,
          branches: coverage.branches
        }
      };

      if (!passed) {
        result.error = `测试覆盖率不达标: ${coverage.total.toFixed(2)}% < ${threshold}%`;
        result.failedChecks = this.getFailedChecks(coverage, qualityGate);
      }

      if (qualityGate.blockDeployment && !passed) {
        result.blockDeployment = true;
        this.logger.warn('质量红线不通过，将阻断部署', {
          stage: stageConfig.name,
          coverage: coverage.total,
          threshold
        });
      }

      this.logger.info('质量红线检查完成', {
        stage: stageConfig.name,
        passed,
        coverage: coverage.total.toFixed(2) + '%',
        threshold: threshold + '%'
      });

      return result;
    } catch (err) {
      this.logger.error('质量红线检查失败', { 
        stage: stageConfig.name, 
        error: err.message 
      });
      return {
        passed: false,
        error: `质量红线检查异常: ${err.message}`
      };
    }
  }

  getFailedChecks(coverage, qualityGate) {
    const failed = [];
    const threshold = qualityGate.coverageThreshold;

    if (coverage.lines !== undefined && coverage.lines < threshold) {
      failed.push({
        metric: '行覆盖率',
        actual: coverage.lines,
        threshold
      });
    }
    if (coverage.statements !== undefined && coverage.statements < threshold) {
      failed.push({
        metric: '语句覆盖率',
        actual: coverage.statements,
        threshold
      });
    }
    if (coverage.functions !== undefined && coverage.functions < threshold) {
      failed.push({
        metric: '函数覆盖率',
        actual: coverage.functions,
        threshold
      });
    }
    if (coverage.branches !== undefined && coverage.branches < threshold) {
      failed.push({
        metric: '分支覆盖率',
        actual: coverage.branches,
        threshold
      });
    }

    return failed;
  }

  async parseCoverageFile(filePath, format, fileName) {
    const detectedFormat = format || this.detectFormat(fileName || filePath);
    const parser = this.parsers[detectedFormat];

    if (!parser) {
      throw new Error(`不支持的覆盖率文件格式: ${detectedFormat}`);
    }

    return parser(filePath);
  }

  detectFormat(fileName) {
    if (fileName.includes('istanbul') || fileName.includes('coverage-final') || fileName.endsWith('coverage-summary.json')) {
      return 'istanbul-json';
    }
    if (fileName.endsWith('jacoco.csv')) {
      return 'jacoco-csv';
    }
    if (fileName.endsWith('.xml') && fileName.includes('cobertura')) {
      return 'cobertura-xml';
    }
    if (fileName.endsWith('.out') || fileName.includes('go-cover')) {
      return 'golang-cover';
    }
    if (fileName.includes('pytest') || fileName.includes('htmlcov')) {
      return 'pytest-cov';
    }
    return 'istanbul-json';
  }

  async parseIstanbulJson(filePath) {
    const content = await fs.readJson(filePath);
    const totals = content.total || this.calculateIstanbulTotals(content);

    return {
      total: this.getPercentage(totals.lines || totals.statements),
      lines: this.getPercentage(totals.lines),
      statements: this.getPercentage(totals.statements),
      functions: this.getPercentage(totals.functions),
      branches: this.getPercentage(totals.branches),
      raw: totals
    };
  }

  calculateIstanbulTotals(content) {
    const totals = {
      lines: { total: 0, covered: 0 },
      statements: { total: 0, covered: 0 },
      functions: { total: 0, covered: 0 },
      branches: { total: 0, covered: 0 }
    };

    Object.values(content).forEach(file => {
      if (file.l) totals.lines.covered += Object.values(file.l).filter(v => v > 0).length;
      if (file.s) totals.statements.covered += Object.values(file.s).filter(v => v > 0).length;
      if (file.f) totals.functions.covered += Object.values(file.f).filter(v => v > 0).length;
      if (file.b) totals.branches.covered += Object.values(file.b).filter(v => v > 0).length;
    });

    return totals;
  }

  async parseJacocoCsv(filePath) {
    const content = await fs.readFile(filePath, 'utf-8');
    const lines = content.split('\n').slice(1);
    
    let missedInstructions = 0;
    let coveredInstructions = 0;
    let missedBranches = 0;
    let coveredBranches = 0;
    let missedLines = 0;
    let coveredLines = 0;
    let missedMethods = 0;
    let coveredMethods = 0;

    lines.forEach(line => {
      const parts = line.split(',');
      if (parts.length >= 8) {
        missedInstructions += parseInt(parts[3]) || 0;
        coveredInstructions += parseInt(parts[4]) || 0;
        missedBranches += parseInt(parts[5]) || 0;
        coveredBranches += parseInt(parts[6]) || 0;
        missedLines += parseInt(parts[7]) || 0;
        coveredLines += parseInt(parts[8]) || 0;
        missedMethods += parseInt(parts[9]) || 0;
        coveredMethods += parseInt(parts[10]) || 0;
      }
    });

    const totalInstructions = missedInstructions + coveredInstructions;
    const totalBranches = missedBranches + coveredBranches;
    const totalLines = missedLines + coveredLines;
    const totalMethods = missedMethods + coveredMethods;

    const instructionCoverage = totalInstructions > 0 ? (coveredInstructions / totalInstructions) * 100 : 100;
    const lineCoverage = totalLines > 0 ? (coveredLines / totalLines) * 100 : 100;
    const branchCoverage = totalBranches > 0 ? (coveredBranches / totalBranches) * 100 : 100;
    const methodCoverage = totalMethods > 0 ? (coveredMethods / totalMethods) * 100 : 100;

    return {
      total: instructionCoverage,
      lines: lineCoverage,
      statements: instructionCoverage,
      functions: methodCoverage,
      branches: branchCoverage
    };
  }

  async parseCoberturaXml(filePath) {
    const content = await fs.readFile(filePath, 'utf-8');
    
    const lineRateMatch = content.match(/line-rate="([\d.]+)"/);
    const branchRateMatch = content.match(/branch-rate="([\d.]+)"/);
    
    const lineRate = lineRateMatch ? parseFloat(lineRateMatch[1]) * 100 : 0;
    const branchRate = branchRateMatch ? parseFloat(branchRateMatch[1]) * 100 : 0;

    return {
      total: lineRate,
      lines: lineRate,
      statements: lineRate,
      functions: null,
      branches: branchRate
    };
  }

  async parseGoCover(filePath) {
    const content = await fs.readFile(filePath, 'utf-8');
    const lines = content.split('\n');
    
    let totalStatements = 0;
    let coveredStatements = 0;

    lines.forEach(line => {
      const match = line.match(/(\d+)\s+(\d+)\s+(\d+)$/);
      if (match) {
        const count = parseInt(match[2]);
        const covered = parseInt(match[3]);
        totalStatements += count;
        if (covered > 0) {
          coveredStatements += count;
        }
      }
    });

    const coverage = totalStatements > 0 ? (coveredStatements / totalStatements) * 100 : 100;

    return {
      total: coverage,
      lines: coverage,
      statements: coverage,
      functions: null,
      branches: null
    };
  }

  async parsePytestCov(filePath) {
    try {
      const jsonPath = path.join(path.dirname(filePath), 'coverage.json');
      if (await fs.pathExists(jsonPath)) {
        return this.parseIstanbulJson(jsonPath);
      }
    } catch (e) {
    }

    const htmlPath = filePath.endsWith('.html') ? filePath : path.join(filePath, 'index.html');
    if (await fs.pathExists(htmlPath)) {
      const content = await fs.readFile(htmlPath, 'utf-8');
      const totalMatch = content.match(/<span[^>]*>(\d+)%<\/span>/);
      const coverage = totalMatch ? parseFloat(totalMatch[1]) : 0;

      return {
        total: coverage,
        lines: coverage,
        statements: coverage,
        functions: null,
        branches: null
      };
    }

    throw new Error('无法解析pytest覆盖率报告');
  }

  getPercentage(data) {
    if (!data) return 0;
    if (typeof data === 'number') return data;
    if (data.total && data.covered !== undefined) {
      return data.total > 0 ? (data.covered / data.total) * 100 : 100;
    }
    if (data.pct !== undefined) return parseFloat(data.pct);
    return 0;
  }

  async generateQualityReport(pipelineId, qualityResults) {
    const report = {
      pipelineId,
      generatedAt: new Date().toISOString(),
      results: qualityResults,
      summary: {
        totalChecks: qualityResults.length,
        passedChecks: qualityResults.filter(r => r.passed).length,
        failedChecks: qualityResults.filter(r => !r.passed).length,
        overallPassed: qualityResults.every(r => r.passed)
      }
    };

    return report;
  }
}

module.exports = QualityGate;
