import type {
  DatasetQualityReport,
  ColumnQualityReport,
  RuleRecommendation,
  RecommendationActionType,
  DatasetStats,
  ColumnStats,
} from '../types';

const PRIORITY_WEIGHTS = {
  high: 3,
  medium: 2,
  low: 1,
};

function generateRecommendationId(): string {
  return `rec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function analyzeMissingValues(
  colStats: ColumnStats,
  colQuality: ColumnQualityReport
): RuleRecommendation | null {
  const missingPercent = colStats.missingPercent;

  if (missingPercent === 0) return null;

  let action: RecommendationActionType = 'fill_missing';
  let priority: 'high' | 'medium' | 'low' = 'medium';
  let confidence = 0.7;
  let reason = '';
  let suggestedConfig: any = {};

  if (missingPercent > 50) {
    action = 'remove_column';
    priority = 'high';
    confidence = 0.85;
    reason = `缺失率高达${missingPercent.toFixed(1)}%，超过50%的阈值，建议删除该列`;
  } else if (missingPercent > 20) {
    priority = 'high';
    confidence = 0.8;
    if (colQuality.columnType === 'numeric') {
      suggestedConfig = { method: 'median' };
      reason = `缺失率${missingPercent.toFixed(1)}%较高，建议使用中位数填充（对异常值不敏感）`;
    } else if (colQuality.columnType === 'date') {
      suggestedConfig = { method: 'interpolate' };
      reason = `日期列缺失率${missingPercent.toFixed(1)}%，建议使用时间插值法填充`;
    } else {
      suggestedConfig = { method: 'mode' };
      reason = `缺失率${missingPercent.toFixed(1)}%，建议使用众数填充`;
    }
  } else if (missingPercent > 5) {
    priority = 'medium';
    confidence = 0.75;
    if (colQuality.columnType === 'numeric') {
      suggestedConfig = { method: 'mean' };
      reason = `缺失率${missingPercent.toFixed(1)}%，建议使用均值填充`;
    } else if (colQuality.columnType === 'date') {
      suggestedConfig = { method: 'ffill' };
      reason = `日期列缺失率${missingPercent.toFixed(1)}%，建议使用前向填充`;
    } else {
      suggestedConfig = { method: 'mode' };
      reason = `缺失率${missingPercent.toFixed(1)}%，建议使用众数填充`;
    }
  } else {
    priority = 'low';
    confidence = 0.6;
    suggestedConfig = { method: 'mean' };
    reason = `缺失率较低(${missingPercent.toFixed(1)}%)，可选择填充或保留`;
  }

  return {
    id: generateRecommendationId(),
    columnName: colStats.name,
    action,
    priority,
    confidence,
    reason,
    suggestedConfig,
    applied: false,
  };
}

function analyzeOutliers(
  colStats: ColumnStats,
  colQuality: ColumnQualityReport
): RuleRecommendation | null {
  if (colQuality.columnType !== 'numeric') return null;

  const outlierCount = colStats.outlierCount || 0;
  const validCount = colStats.count - colStats.missingCount;
  const outlierPercent = validCount > 0 ? (outlierCount / validCount) * 100 : 0;

  if (outlierCount === 0) return null;

  let action: RecommendationActionType = 'remove_outliers';
  let priority: 'high' | 'medium' | 'low' = 'medium';
  let confidence = 0.7;
  let reason = '';
  let suggestedConfig: any = {};

  if (outlierPercent > 20) {
    action = 'cap_outliers';
    priority = 'high';
    confidence = 0.85;
    suggestedConfig = { method: 'iqr', threshold: 1.5, action: 'cap' };
    reason = `异常值占比${outlierPercent.toFixed(1)}%过高，建议使用盖帽法(IQR)处理而非直接删除`;
  } else if (outlierPercent > 10) {
    action = 'cap_outliers';
    priority = 'medium';
    confidence = 0.75;
    suggestedConfig = { method: 'zscore', threshold: 3, action: 'cap' };
    reason = `异常值占比${outlierPercent.toFixed(1)}%，建议使用Z-score盖帽法处理`;
  } else if (outlierPercent > 5) {
    priority = 'medium';
    confidence = 0.7;
    suggestedConfig = { method: 'zscore', threshold: 3, action: 'remove' };
    reason = `异常值占比${outlierPercent.toFixed(1)}%，建议使用Z-score方法检测并删除`;
  } else {
    priority = 'low';
    confidence = 0.6;
    suggestedConfig = { method: 'iqr', threshold: 1.5, action: 'remove' };
    reason = `存在少量异常值(${outlierPercent.toFixed(1)}%)，可选择删除或标记`;
  }

  return {
    id: generateRecommendationId(),
    columnName: colStats.name,
    action,
    priority,
    confidence,
    reason,
    suggestedConfig,
    applied: false,
  };
}

function analyzeNormalizationNeed(
  colStats: ColumnStats,
  colQuality: ColumnQualityReport
): RuleRecommendation | null {
  if (colQuality.columnType !== 'numeric') return null;

  const validCount = colStats.count - colStats.missingCount;
  if (validCount < 10) return null;

  const mean = colStats.mean || 0;
  const std = colStats.std || 0;
  const min = colStats.min || 0;
  const max = colStats.max || 0;

  const range = max - min;
  const coefficientOfVariation = std / Math.abs(mean || 1);

  let shouldNormalize = false;
  let reason = '';
  let suggestedConfig: any = {};

  if (range > 1000 && coefficientOfVariation > 0.5) {
    shouldNormalize = true;
    suggestedConfig = { method: 'minmax' };
    reason = `数值范围较大(${min.toFixed(2)} ~ ${max.toFixed(2)})，建议进行Min-Max归一化`;
  } else if (coefficientOfVariation > 1) {
    shouldNormalize = true;
    suggestedConfig = { method: 'robust' };
    reason = `变异系数较高(${coefficientOfVariation.toFixed(2)})，建议使用Robust标准化（对异常值不敏感）`;
  } else if (Math.abs(mean) > 100 || std > 50) {
    shouldNormalize = true;
    suggestedConfig = { method: 'zscore' };
    reason = `数据量级较大，建议进行Z-score标准化`;
  }

  if (!shouldNormalize) return null;

  return {
    id: generateRecommendationId(),
    columnName: colStats.name,
    action: 'normalize',
    priority: 'low',
    confidence: 0.65,
    reason,
    suggestedConfig,
    applied: false,
  };
}

function analyzeDuplicates(
  datasetStats: DatasetStats
): RuleRecommendation | null {
  if (datasetStats.totalDuplicates === 0) return null;

  const duplicatePercent =
    (datasetStats.totalDuplicates / datasetStats.rowCount) * 100;
  let priority: 'high' | 'medium' | 'low' = 'medium';
  let confidence = 0.8;
  let reason = '';

  if (duplicatePercent > 10) {
    priority = 'high';
    confidence = 0.9;
    reason = `存在${datasetStats.totalDuplicates}条重复数据(${duplicatePercent.toFixed(1)}%)，建议优先删除`;
  } else if (duplicatePercent > 5) {
    priority = 'medium';
    confidence = 0.8;
    reason = `存在${datasetStats.totalDuplicates}条重复数据(${duplicatePercent.toFixed(1)}%)，建议删除`;
  } else {
    priority = 'low';
    confidence = 0.7;
    reason = `存在${datasetStats.totalDuplicates}条重复数据(${duplicatePercent.toFixed(1)}%)，可选择删除`;
  }

  return {
    id: generateRecommendationId(),
    columnName: '__dataset__',
    action: 'remove_duplicates',
    priority,
    confidence,
    reason,
    suggestedConfig: { keep: 'first' },
    applied: false,
  };
}

function analyzeColumnType(
  colStats: ColumnStats,
  data: any[][],
  columnIndex: number
): RuleRecommendation | null {
  const values = data.map((row) => row[columnIndex]);
  const validValues = values.filter(
    (v) => v !== null && v !== undefined && v !== ''
  );

  if (validValues.length === 0) return null;

  const numericCount = validValues.filter((v) => {
    const num = Number(v);
    return !isNaN(num) && isFinite(num);
  }).length;

  const dateCount = validValues.filter((v) => {
    const date = new Date(String(v));
    return !isNaN(date.getTime());
  }).length;

  const numericRatio = numericCount / validValues.length;
  const dateRatio = dateCount / validValues.length;

  if (colStats.type === 'string' && numericRatio > 0.9) {
    return {
      id: generateRecommendationId(),
      columnName: colStats.name,
      action: 'convert_type',
      priority: 'medium',
      confidence: 0.8,
      reason: `该列${(numericRatio * 100).toFixed(0)}%的值为数字，建议转换为数值类型`,
      suggestedConfig: { targetType: 'numeric' },
      applied: false,
    };
  }

  if (colStats.type === 'string' && dateRatio > 0.9) {
    return {
      id: generateRecommendationId(),
      columnName: colStats.name,
      action: 'convert_type',
      priority: 'medium',
      confidence: 0.8,
      reason: `该列${(dateRatio * 100).toFixed(0)}%的值为日期，建议转换为日期类型`,
      suggestedConfig: { targetType: 'date' },
      applied: false,
    };
  }

  if (colStats.type === 'mixed' && numericRatio > 0.8) {
    return {
      id: generateRecommendationId(),
      columnName: colStats.name,
      action: 'convert_type',
      priority: 'high',
      confidence: 0.75,
      reason: `混合类型列中${(numericRatio * 100).toFixed(0)}%为数字，建议统一转换为数值类型`,
      suggestedConfig: { targetType: 'numeric' },
      applied: false,
    };
  }

  return null;
}

export function generateRecommendations(
  qualityReport: DatasetQualityReport,
  datasetStats: DatasetStats,
  data: any[][]
): RuleRecommendation[] {
  const recommendations: RuleRecommendation[] = [];

  const duplicatesRec = analyzeDuplicates(datasetStats);
  if (duplicatesRec) {
    recommendations.push(duplicatesRec);
  }

  datasetStats.columns.forEach((colStats, idx) => {
    const colQuality = qualityReport.columnReports[idx];
    if (!colQuality) return;

    const missingRec = analyzeMissingValues(colStats, colQuality);
    if (missingRec) recommendations.push(missingRec);

    const outlierRec = analyzeOutliers(colStats, colQuality);
    if (outlierRec) recommendations.push(outlierRec);

    const normRec = analyzeNormalizationNeed(colStats, colQuality);
    if (normRec) recommendations.push(normRec);

    const typeRec = analyzeColumnType(colStats, data, idx);
    if (typeRec) recommendations.push(typeRec);
  });

  recommendations.sort((a, b) => {
    const priorityDiff = PRIORITY_WEIGHTS[b.priority] - PRIORITY_WEIGHTS[a.priority];
    if (priorityDiff !== 0) return priorityDiff;
    return b.confidence - a.confidence;
  });

  return recommendations;
}

export function getActionLabel(action: RecommendationActionType): string {
  const labels: Record<RecommendationActionType, string> = {
    remove_duplicates: '删除重复值',
    fill_missing: '填充缺失值',
    remove_outliers: '删除异常值',
    cap_outliers: '盖帽处理异常值',
    normalize: '数据标准化',
    remove_column: '删除列',
    convert_type: '转换数据类型',
    rename_column: '重命名列',
  };
  return labels[action];
}

export function getActionIcon(action: RecommendationActionType): string {
  const icons: Record<RecommendationActionType, string> = {
    remove_duplicates: 'copy',
    fill_missing: 'circle-dot',
    remove_outliers: 'trash-2',
    cap_outliers: 'scissors',
    normalize: 'sliders',
    remove_column: 'x-circle',
    convert_type: 'refresh-cw',
    rename_column: 'edit-3',
  };
  return icons[action];
}
