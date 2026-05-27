import type {
  DatasetStats,
  ColumnStats,
  ColumnType,
  DataQualityMetrics,
  ColumnQualityReport,
  DatasetQualityReport,
  QualityIssue,
  QualityIssueSeverity,
  QualityIssueType,
} from '../types';
import { detectColumnType, getNumericValues, detectOutliersIQR } from './statistics';

function calculateCompleteness(columnStats: ColumnStats): number {
  return 100 - columnStats.missingPercent;
}

function calculateConsistency(
  values: any[],
  columnType: ColumnType,
  columnStats: ColumnStats
): number {
  if (values.length === 0) return 100;

  let typeConsistency = 100;
  let formatConsistency = 100;

  if (columnType === 'numeric') {
    const validNumericCount = values.filter((v) => {
      if (v === null || v === undefined || v === '') return true;
      const num = Number(v);
      return !isNaN(num) && isFinite(num);
    }).length;
    typeConsistency = (validNumericCount / values.length) * 100;
  } else if (columnType === 'date') {
    const validDateCount = values.filter((v) => {
      if (v === null || v === undefined || v === '') return true;
      const date = new Date(String(v));
      return !isNaN(date.getTime());
    }).length;
    typeConsistency = (validDateCount / values.length) * 100;
  } else if (columnType === 'boolean') {
    const validBoolCount = values.filter((v) => {
      if (v === null || v === undefined || v === '') return true;
      const str = String(v).toLowerCase();
      return ['true', 'false', '1', '0', 'yes', 'no', '是', '否'].includes(str);
    }).length;
    typeConsistency = (validBoolCount / values.length) * 100;
  }

  if (columnStats.uniqueCount > 0) {
    const uniqueRatio = columnStats.uniqueCount / (values.length - columnStats.missingCount);
    if (uniqueRatio > 0.95 && columnType !== 'string') {
      formatConsistency = 80;
    } else if (uniqueRatio < 0.01 && columnType === 'numeric') {
      formatConsistency = 90;
    }
  }

  return (typeConsistency * 0.6 + formatConsistency * 0.4);
}

function calculateAccuracy(
  values: any[],
  columnType: ColumnType,
  columnStats: ColumnStats
): number {
  if (values.length === 0) return 100;

  let outlierScore = 100;
  let valueRangeScore = 100;

  if (columnType === 'numeric' && columnStats.outlierCount !== undefined) {
    const validValues = values.filter(
      (v) => v !== null && v !== undefined && v !== ''
    );
    if (validValues.length > 0) {
      const outlierPercent = (columnStats.outlierCount / validValues.length) * 100;
      if (outlierPercent === 0) {
        outlierScore = 100;
      } else if (outlierPercent < 5) {
        outlierScore = 90;
      } else if (outlierPercent < 15) {
        outlierScore = 70;
      } else if (outlierPercent < 30) {
        outlierScore = 50;
      } else {
        outlierScore = 30;
      }

      if (columnStats.min !== undefined && columnStats.max !== undefined) {
        const numericValues = getNumericValues(validValues);
        if (numericValues.length > 0) {
          const range = columnStats.max - columnStats.min;
          if (range === 0) {
            valueRangeScore = 100;
          } else {
            const mean = columnStats.mean || 0;
            const std = columnStats.std || 1;
            const coefficientOfVariation = std / Math.abs(mean || 1);
            if (coefficientOfVariation < 0.1) {
              valueRangeScore = 100;
            } else if (coefficientOfVariation < 0.5) {
              valueRangeScore = 90;
            } else if (coefficientOfVariation < 1) {
              valueRangeScore = 80;
            } else {
              valueRangeScore = 70;
            }
          }
        }
      }
    }
  }

  return (outlierScore * 0.6 + valueRangeScore * 0.4);
}

function detectColumnIssues(
  columnStats: ColumnStats,
  rowCount: number,
  values: any[]
): QualityIssue[] {
  const issues: QualityIssue[] = [];
  const { missingPercent, outlierCount, uniqueCount, type } = columnStats;
  const validRowCount = rowCount - columnStats.missingCount;

  if (missingPercent > 0) {
    const severity: QualityIssueSeverity =
      missingPercent > 50 ? 'critical' : missingPercent > 20 ? 'warning' : 'info';
    issues.push({
      type: 'missing_values',
      severity,
      message: `存在 ${columnStats.missingCount} 个缺失值 (${missingPercent.toFixed(2)}%)`,
      columnName: columnStats.name,
      value: missingPercent,
      threshold: severity === 'critical' ? 50 : severity === 'warning' ? 20 : 0,
    });

    if (missingPercent > 50) {
      issues.push({
        type: 'high_missing_rate',
        severity: 'critical',
        message: `缺失率超过50%，建议删除该列或采用插值方法`,
        columnName: columnStats.name,
        value: missingPercent,
        threshold: 50,
      });
    }
  }

  if (type === 'numeric' && outlierCount !== undefined && outlierCount > 0) {
    const outlierPercent = (outlierCount / Math.max(validRowCount, 1)) * 100;
    const severity: QualityIssueSeverity =
      outlierPercent > 20 ? 'critical' : outlierPercent > 10 ? 'warning' : 'info';
    issues.push({
      type: 'outliers',
      severity,
      message: `检测到 ${outlierCount} 个异常值 (${outlierPercent.toFixed(2)}%)`,
      columnName: columnStats.name,
      value: outlierPercent,
      threshold: severity === 'critical' ? 20 : severity === 'warning' ? 10 : 0,
    });

    if (outlierPercent > 15) {
      issues.push({
        type: 'high_outlier_rate',
        severity: 'warning',
        message: `异常值占比较高，建议采用盖帽法而非直接删除`,
        columnName: columnStats.name,
        value: outlierPercent,
        threshold: 15,
      });
    }
  }

  if (validRowCount > 0) {
    const uniqueRatio = uniqueCount / validRowCount;

    if (uniqueRatio === 1 && type !== 'string') {
      issues.push({
        type: 'potential_id_column',
        severity: 'info',
        message: `该列所有值唯一，可能是ID列`,
        columnName: columnStats.name,
        value: uniqueRatio,
        threshold: 1,
      });
    }

    if (uniqueRatio === 0 && validRowCount > 1) {
      issues.push({
        type: 'constant_column',
        severity: 'warning',
        message: `该列为常数列，所有值相同`,
        columnName: columnStats.name,
        value: 0,
        threshold: 0,
      });
    }

    if (uniqueRatio < 0.01 && validRowCount > 100) {
      issues.push({
        type: 'low_cardinality',
        severity: 'info',
        message: `基数较低 (${uniqueCount}个唯一值)，可能是分类变量`,
        columnName: columnStats.name,
        value: uniqueRatio,
        threshold: 0.01,
      });
    }

    if (uniqueRatio > 0.9 && type === 'string') {
      issues.push({
        type: 'high_cardinality',
        severity: 'info',
        message: `基数较高，可能存在数据不一致或为自由文本`,
        columnName: columnStats.name,
        value: uniqueRatio,
        threshold: 0.9,
      });
    }
  }

  if (columnStats.duplicateCount > 0 && type !== 'numeric') {
    const duplicatePercent = (columnStats.duplicateCount / validRowCount) * 100;
    if (duplicatePercent > 50) {
      issues.push({
        type: 'duplicate_values',
        severity: 'info',
        message: `存在大量重复值 (${duplicatePercent.toFixed(2)}%)`,
        columnName: columnStats.name,
        value: duplicatePercent,
        threshold: 50,
      });
    }
  }

  if (type === 'date') {
    const dateValues = values
      .filter((v) => v !== null && v !== undefined && v !== '')
      .map((v) => new Date(String(v)).getTime());
    if (dateValues.length > 1) {
      const sortedDates = [...dateValues].sort((a, b) => a - b);
      for (let i = 1; i < sortedDates.length; i++) {
        if (sortedDates[i] < sortedDates[i - 1]) {
          issues.push({
            type: 'date_inconsistency',
            severity: 'warning',
            message: `日期列可能存在顺序不一致`,
            columnName: columnStats.name,
          });
          break;
        }
      }
    }
  }

  return issues;
}

function calculateOverallMetrics(
  columnReports: ColumnQualityReport[]
): DataQualityMetrics {
  if (columnReports.length === 0) {
    return { completeness: 100, consistency: 100, accuracy: 100, overall: 100 };
  }

  const completeness =
    columnReports.reduce((sum, c) => sum + c.metrics.completeness, 0) /
    columnReports.length;
  const consistency =
    columnReports.reduce((sum, c) => sum + c.metrics.consistency, 0) /
    columnReports.length;
  const accuracy =
    columnReports.reduce((sum, c) => sum + c.metrics.accuracy, 0) /
    columnReports.length;
  const overall = completeness * 0.4 + consistency * 0.3 + accuracy * 0.3;

  return { completeness, consistency, accuracy, overall };
}

export function evaluateColumnQuality(
  columnStats: ColumnStats,
  data: any[][],
  columnIndex: number,
  rowCount: number
): ColumnQualityReport {
  const values = data.map((row) => row[columnIndex]);
  const columnType = columnStats.type;

  const completeness = calculateCompleteness(columnStats);
  const consistency = calculateConsistency(values, columnType, columnStats);
  const accuracy = calculateAccuracy(values, columnType, columnStats);
  const overall = completeness * 0.4 + consistency * 0.3 + accuracy * 0.3;

  const issues = detectColumnIssues(columnStats, rowCount, values);

  const validRowCount = rowCount - columnStats.missingCount;
  const uniqueRatio = validRowCount > 0 ? columnStats.uniqueCount / validRowCount : 0;

  const outlierCount = columnStats.outlierCount || 0;
  const outlierPercent = validRowCount > 0 ? (outlierCount / validRowCount) * 100 : 0;

  return {
    columnName: columnStats.name,
    columnType,
    metrics: { completeness, consistency, accuracy, overall },
    issues,
    details: {
      completeness: {
        nonNullCount: rowCount - columnStats.missingCount,
        nullCount: columnStats.missingCount,
        nullPercent: columnStats.missingPercent,
      },
      consistency: {
        typeConsistency: consistency,
        formatConsistency: consistency > 90 ? 95 : 80,
        uniqueRatio,
      },
      accuracy: {
        outlierCount,
        outlierPercent,
        valueRangeScore: accuracy > 80 ? 90 : 75,
      },
    },
  };
}

export function evaluateDatasetQuality(
  datasetStats: DatasetStats,
  data: any[][],
  columns: string[]
): DatasetQualityReport {
  const columnReports: ColumnQualityReport[] = datasetStats.columns.map(
    (colStats, idx) =>
      evaluateColumnQuality(colStats, data, idx, datasetStats.rowCount)
  );

  const overallMetrics = calculateOverallMetrics(columnReports);

  const allIssues = columnReports.flatMap((c) => c.issues);
  const severityBreakdown = {
    critical: allIssues.filter((i) => i.severity === 'critical').length,
    warning: allIssues.filter((i) => i.severity === 'warning').length,
    info: allIssues.filter((i) => i.severity === 'info').length,
  };

  return {
    overallMetrics,
    columnReports,
    totalIssues: allIssues.length,
    severityBreakdown,
  };
}

export function getQualityScoreColor(score: number): string {
  if (score >= 90) return 'text-success-400';
  if (score >= 70) return 'text-warning-400';
  if (score >= 50) return 'text-orange-400';
  return 'text-danger-400';
}

export function getQualityScoreBgColor(score: number): string {
  if (score >= 90) return 'bg-success-500';
  if (score >= 70) return 'bg-warning-500';
  if (score >= 50) return 'bg-orange-500';
  return 'bg-danger-500';
}

export function getQualityLabel(score: number): string {
  if (score >= 90) return '优秀';
  if (score >= 80) return '良好';
  if (score >= 70) return '中等';
  if (score >= 60) return '及格';
  if (score >= 50) return '较差';
  return '很差';
}
