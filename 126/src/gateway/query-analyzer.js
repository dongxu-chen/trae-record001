import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class QueryAnalyzer {
  constructor(options = {}) {
    this.slowQueryThreshold = options.slowQueryThreshold || 1000;
    this.complexityThreshold = options.complexityThreshold || 100;
    this.logFilePath = options.logFilePath || path.join(__dirname, '../../logs/slow-queries.json');
    this.maxLogEntries = options.maxLogEntries || 1000;
    this.queryLogs = [];
    this.stats = {
      totalQueries: 0,
      slowQueries: 0,
      highComplexityQueries: 0,
      avgExecutionTime: 0,
      avgComplexity: 0,
    };
    this.fieldWeights = options.fieldWeights || {
      default: 1,
      list: 5,
      nested: 3,
    };
    this.typeDepths = new Map();
  }

  calculateComplexity(ast, variables = {}) {
    let totalComplexity = 0;
    let totalFields = 0;
    let maxDepth = 0;
    const fieldBreakdown = [];

    const traverse = (node, depth = 0, parentType = 'Query') => {
      maxDepth = Math.max(maxDepth, depth);
      
      if (node.selectionSet) {
        for (const selection of node.selectionSet.selections) {
          if (selection.kind === 'Field') {
            totalFields++;
            const fieldName = selection.name.value;
            let weight = this.fieldWeights.default;
            
            if (selection.selectionSet) {
              weight = this.fieldWeights.nested;
              const isList = this.isListField(parentType, fieldName);
              if (isList) {
                weight = this.fieldWeights.list;
              }
            }
            
            const complexity = weight * (1 + depth * 0.1);
            totalComplexity += complexity;
            
            fieldBreakdown.push({
              field: fieldName,
              depth,
              complexity,
              parentType,
            });
            
            if (selection.selectionSet) {
              traverse(selection, depth + 1, fieldName);
            }
          }
        }
      }
    };

    if (ast.definitions) {
      for (const definition of ast.definitions) {
        traverse(definition);
      }
    }

    return {
      totalComplexity: Math.round(totalComplexity),
      totalFields,
      maxDepth,
      fieldBreakdown,
      isHighComplexity: totalComplexity > this.complexityThreshold,
    };
  }

  isListField(parentType, fieldName) {
    const listFields = {
      Query: ['getUsers', 'getPosts', 'getComments', 'searchUsers', 'searchPosts'],
      User: ['posts', 'comments'],
      Post: ['comments'],
    };
    return listFields[parentType]?.includes(fieldName) || false;
  }

  analyzeQuery(queryInfo, ast, variables) {
    const startTime = Date.now();
    const complexity = this.calculateComplexity(ast, variables);
    
    return {
      ...queryInfo,
      ...complexity,
      startTime,
    };
  }

  completeQuery(analysis, result) {
    const executionTime = Date.now() - analysis.startTime;
    const isSlow = executionTime > this.slowQueryThreshold;
    
    const completedAnalysis = {
      ...analysis,
      executionTime,
      isSlow,
      hasErrors: result.errors?.length > 0,
      errorCount: result.errors?.length || 0,
      completedAt: new Date().toISOString(),
    };

    this.updateStats(completedAnalysis);

    if (isSlow || completedAnalysis.isHighComplexity) {
      this.logSlowQuery(completedAnalysis);
    }

    return completedAnalysis;
  }

  updateStats(analysis) {
    this.stats.totalQueries++;
    
    if (analysis.isSlow) this.stats.slowQueries++;
    if (analysis.isHighComplexity) this.stats.highComplexityQueries++;
    
    const totalTime = this.stats.avgExecutionTime * (this.stats.totalQueries - 1) + analysis.executionTime;
    this.stats.avgExecutionTime = totalTime / this.stats.totalQueries;
    
    const totalComplexity = this.stats.avgComplexity * (this.stats.totalQueries - 1) + analysis.totalComplexity;
    this.stats.avgComplexity = totalComplexity / this.stats.totalQueries;
  }

  logSlowQuery(analysis) {
    const logEntry = {
      id: this.generateId(),
      timestamp: new Date().toISOString(),
      queryHash: this.hashQuery(analysis.query),
      queryPreview: analysis.query.substring(0, 200),
      operationName: analysis.operationName,
      executionTime: analysis.executionTime,
      totalComplexity: analysis.totalComplexity,
      totalFields: analysis.totalFields,
      maxDepth: analysis.maxDepth,
      isSlow: analysis.isSlow,
      isHighComplexity: analysis.isHighComplexity,
      hasErrors: analysis.hasErrors,
      errorCount: analysis.errorCount,
      userId: analysis.userId,
      ip: analysis.ip,
      userAgent: analysis.userAgent,
    };

    this.queryLogs.push(logEntry);
    
    if (this.queryLogs.length > this.maxLogEntries) {
      this.queryLogs = this.queryLogs.slice(-this.maxLogEntries);
    }

    if (analysis.isSlow) {
      console.warn(`🐢 Slow Query detected: ${analysis.executionTime}ms (threshold: ${this.slowQueryThreshold}ms)`);
    }
    if (analysis.isHighComplexity) {
      console.warn(`⚠️ High Complexity Query: ${analysis.totalComplexity} (threshold: ${this.complexityThreshold})`);
    }
  }

  async saveLogsToFile() {
    try {
      await fs.mkdir(path.dirname(this.logFilePath), { recursive: true });
      const data = {
        exportedAt: new Date().toISOString(),
        stats: this.stats,
        logs: this.queryLogs,
      };
      await fs.writeFile(this.logFilePath, JSON.stringify(data, null, 2));
      console.log(`📝 Slow query logs saved to: ${this.logFilePath}`);
      return true;
    } catch (error) {
      console.error('Failed to save slow query logs:', error);
      return false;
    }
  }

  async loadLogsFromFile() {
    try {
      const data = await fs.readFile(this.logFilePath, 'utf8');
      const parsed = JSON.parse(data);
      this.queryLogs = parsed.logs || [];
      return parsed;
    } catch (error) {
      if (error.code !== 'ENOENT') {
        console.error('Failed to load slow query logs:', error);
      }
      return null;
    }
  }

  getSlowQueries(limit = 100) {
    return this.queryLogs
      .filter(log => log.isSlow)
      .sort((a, b) => b.executionTime - a.executionTime)
      .slice(0, limit);
  }

  getHighComplexityQueries(limit = 100) {
    return this.queryLogs
      .filter(log => log.isHighComplexity)
      .sort((a, b) => b.totalComplexity - a.totalComplexity)
      .slice(0, limit);
  }

  getStats() {
    return {
      ...this.stats,
      slowQueryRate: this.stats.totalQueries > 0 
        ? (this.stats.slowQueries / this.stats.totalQueries * 100).toFixed(2) + '%' 
        : '0%',
      highComplexityRate: this.stats.totalQueries > 0 
        ? (this.stats.highComplexityQueries / this.stats.totalQueries * 100).toFixed(2) + '%' 
        : '0%',
      loggedQueries: this.queryLogs.length,
    };
  }

  getReports(options = {}) {
    const { 
      includeSlow = true, 
      includeHighComplexity = true,
      includeStats = true,
      limit = 50 
    } = options;

    const report = {
      generatedAt: new Date().toISOString(),
      thresholds: {
        slowQuery: this.slowQueryThreshold,
        highComplexity: this.complexityThreshold,
      },
    };

    if (includeStats) {
      report.stats = this.getStats();
    }

    if (includeSlow) {
      report.slowQueries = this.getSlowQueries(limit);
    }

    if (includeHighComplexity) {
      report.highComplexityQueries = this.getHighComplexityQueries(limit);
    }

    return report;
  }

  generateReport(format = 'json') {
    const report = this.getReports();
    
    if (format === 'text') {
      return this.formatTextReport(report);
    }
    
    return JSON.stringify(report, null, 2);
  }

  formatTextReport(report) {
    let text = `\n📊 Query Analysis Report\n${'='.repeat(50)}\n`;
    text += `Generated at: ${report.generatedAt}\n\n`;
    
    text += `📈 Statistics:\n${'-'.repeat(30)}\n`;
    if (report.stats) {
      Object.entries(report.stats).forEach(([key, value]) => {
        text += `  ${key}: ${value}\n`;
      });
    }
    
    if (report.slowQueries?.length > 0) {
      text += `\n🐢 Slow Queries (${report.slowQueries.length}):\n${'-'.repeat(30)}\n`;
      report.slowQueries.slice(0, 10).forEach((q, i) => {
        text += `  ${i + 1}. ${q.executionTime}ms - ${q.operationName || 'anonymous'}\n`;
      });
    }
    
    if (report.highComplexityQueries?.length > 0) {
      text += `\n⚠️ High Complexity Queries (${report.highComplexityQueries.length}):\n${'-'.repeat(30)}\n`;
      report.highComplexityQueries.slice(0, 10).forEach((q, i) => {
        text += `  ${i + 1}. Complexity: ${q.totalComplexity} - ${q.operationName || 'anonymous'}\n`;
      });
    }
    
    return text;
  }

  clearLogs() {
    this.queryLogs = [];
    this.stats = {
      totalQueries: 0,
      slowQueries: 0,
      highComplexityQueries: 0,
      avgExecutionTime: 0,
      avgComplexity: 0,
    };
  }

  generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  hashQuery(query) {
    let hash = 0;
    for (let i = 0; i < query.length; i++) {
      const char = query.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash).toString(16);
  }
}

export const queryAnalyzer = new QueryAnalyzer({
  slowQueryThreshold: 1000,
  complexityThreshold: 100,
  maxLogEntries: 1000,
});

export default QueryAnalyzer;
