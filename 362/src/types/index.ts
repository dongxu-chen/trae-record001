export type FillMethod = 'mean' | 'median' | 'mode' | 'interpolate' | 'constant' | 'ffill' | 'bfill';

export type OutlierMethod = 'zscore' | 'iqr';

export type NormalizeMethod = 'minmax' | 'zscore' | 'robust';

export type ColumnType = 'numeric' | 'string' | 'boolean' | 'date' | 'mixed';

export interface CleaningRules {
  removeDuplicates: {
    enabled: boolean;
    columns?: string[];
    keep: 'first' | 'last' | false;
  };
  handleMissing: {
    enabled: boolean;
    columns: {
      [columnName: string]: {
        method: FillMethod;
        value?: number | string;
      };
    };
    defaultMethod: FillMethod;
  };
  detectOutliers: {
    enabled: boolean;
    columns: {
      [columnName: string]: {
        method: OutlierMethod;
        threshold: number;
        action: 'remove' | 'cap' | 'mark';
      };
    };
    defaultMethod: OutlierMethod;
    defaultThreshold: number;
  };
  normalize: {
    enabled: boolean;
    columns: {
      [columnName: string]: {
        method: NormalizeMethod;
      };
    };
    defaultMethod: NormalizeMethod;
  };
}

export interface ColumnStats {
  name: string;
  type: ColumnType;
  count: number;
  missingCount: number;
  missingPercent: number;
  uniqueCount: number;
  duplicateCount: number;
  min?: number;
  max?: number;
  mean?: number;
  median?: number;
  mode?: number | string;
  std?: number;
  outlierCount?: number;
  outliers?: number[];
  histogram?: { bins: number[]; counts: number[] };
}

export interface DatasetStats {
  rowCount: number;
  columnCount: number;
  columns: ColumnStats[];
  totalMissing: number;
  totalDuplicates: number;
  memorySize: string;
}

export interface CleaningChanges {
  rowsRemoved: number;
  rowsAdded: number;
  valuesFilled: number;
  outliersHandled: number;
  duplicatesRemoved: number;
}

export interface CleaningResult {
  success: boolean;
  data: any[][];
  columns: string[];
  stats: DatasetStats;
  beforeStats: DatasetStats;
  changes: CleaningChanges;
  script: string;
  logs: string[];
  duration: number;
}

export type WorkerMessage =
  | { type: 'INIT'; payload: { data: any[][]; columns: string[] } }
  | { type: 'CLEAN'; payload: { rules: CleaningRules } }
  | { type: 'CANCEL' }
  | { type: 'GET_STATS' };

export type WorkerResponse =
  | { type: 'PROGRESS'; payload: { step: string; progress: number; message?: string } }
  | { type: 'STATS'; payload: DatasetStats }
  | { type: 'COMPLETE'; payload: CleaningResult }
  | { type: 'ERROR'; payload: string };

export type FileInfo = {
  name: string;
  size: number;
  type: string;
  rows: number;
  columns: number;
};

export type UploadedData = {
  data: any[][];
  columns: string[];
  fileInfo: FileInfo;
  stats: DatasetStats;
};

export type CleaningStep = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  icon: string;
};

export const CLEANING_STEPS: CleaningStep[] = [
  { id: 'duplicates', name: '重复值处理', description: '删除数据中的重复行', enabled: true, icon: 'copy' },
  { id: 'missing', name: '缺失值填充', description: '填充或删除缺失值', enabled: true, icon: 'circle-dot' },
  { id: 'outliers', name: '异常值检测', description: '检测并处理异常值', enabled: true, icon: 'alert-triangle' },
  { id: 'normalize', name: '数据标准化', description: '将数据缩放到指定范围', enabled: true, icon: 'sliders' },
];

export const FILL_METHODS: { value: FillMethod; label: string; description: string }[] = [
  { value: 'mean', label: '均值填充', description: '使用该列的平均值填充' },
  { value: 'median', label: '中位数填充', description: '使用该列的中位数填充' },
  { value: 'mode', label: '众数填充', description: '使用该列出现频率最高的值填充' },
  { value: 'interpolate', label: '线性插值', description: '使用线性插值法填充' },
  { value: 'ffill', label: '前向填充', description: '使用前一个有效值填充' },
  { value: 'bfill', label: '后向填充', description: '使用后一个有效值填充' },
  { value: 'constant', label: '固定值', description: '使用指定的固定值填充' },
];

export const OUTLIER_METHODS: { value: OutlierMethod; label: string; description: string }[] = [
  { value: 'zscore', label: 'Z-score 方法', description: '基于标准差检测，默认阈值3' },
  { value: 'iqr', label: 'IQR 方法', description: '基于四分位距检测，默认阈值1.5' },
];

export const NORMALIZE_METHODS: { value: NormalizeMethod; label: string; description: string }[] = [
  { value: 'minmax', label: 'Min-Max 归一化', description: '缩放到 [0, 1] 区间' },
  { value: 'zscore', label: 'Z-score 标准化', description: '均值为0，标准差为1' },
  { value: 'robust', label: 'Robust 标准化', description: '使用中位数和四分位距，对异常值不敏感' },
];

export interface DataQualityMetrics {
  completeness: number;
  consistency: number;
  accuracy: number;
  overall: number;
}

export interface ColumnQualityReport {
  columnName: string;
  columnType: ColumnType;
  metrics: DataQualityMetrics;
  issues: QualityIssue[];
  details: {
    completeness: {
      nonNullCount: number;
      nullCount: number;
      nullPercent: number;
    };
    consistency: {
      typeConsistency: number;
      formatConsistency: number;
      uniqueRatio: number;
    };
    accuracy: {
      outlierCount: number;
      outlierPercent: number;
      valueRangeScore: number;
    };
  };
}

export interface DatasetQualityReport {
  overallMetrics: DataQualityMetrics;
  columnReports: ColumnQualityReport[];
  totalIssues: number;
  severityBreakdown: {
    critical: number;
    warning: number;
    info: number;
  };
}

export type QualityIssueSeverity = 'critical' | 'warning' | 'info';

export type QualityIssueType =
  | 'missing_values'
  | 'high_missing_rate'
  | 'type_inconsistency'
  | 'outliers'
  | 'high_outlier_rate'
  | 'low_cardinality'
  | 'high_cardinality'
  | 'constant_column'
  | 'duplicate_values'
  | 'invalid_format'
  | 'potential_id_column'
  | 'date_inconsistency';

export interface QualityIssue {
  type: QualityIssueType;
  severity: QualityIssueSeverity;
  message: string;
  columnName: string;
  value?: number;
  threshold?: number;
}

export type RecommendationActionType =
  | 'remove_duplicates'
  | 'fill_missing'
  | 'remove_outliers'
  | 'cap_outliers'
  | 'normalize'
  | 'remove_column'
  | 'convert_type'
  | 'rename_column';

export interface RuleRecommendation {
  id: string;
  columnName: string;
  action: RecommendationActionType;
  priority: 'high' | 'medium' | 'low';
  confidence: number;
  reason: string;
  suggestedConfig?: any;
  applied: boolean;
}

export type CleaningStepType = 'duplicates' | 'missing' | 'outliers' | 'normalize' | 'custom';

export interface WorkflowStep {
  id: string;
  type: CleaningStepType;
  name: string;
  description: string;
  enabled: boolean;
  order: number;
  config?: any;
  targetColumns?: string[];
}

export interface CleaningWorkflow {
  id: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  createdAt: Date;
  updatedAt: Date;
}

export const WORKFLOW_PRESETS: Omit<CleaningWorkflow, 'id' | 'createdAt' | 'updatedAt'>[] = [
  {
    name: '标准数据清洗',
    description: '适用于大多数结构化数据集的标准清洗流程',
    steps: [
      { id: '1', type: 'duplicates', name: '删除重复值', description: '移除完全重复的行', enabled: true, order: 0 },
      { id: '2', type: 'missing', name: '填充缺失值', description: '使用统计方法填充缺失值', enabled: true, order: 1 },
      { id: '3', type: 'outliers', name: '处理异常值', description: '检测并处理异常值', enabled: true, order: 2 },
    ],
  },
  {
    name: '机器学习数据准备',
    description: '为机器学习模型准备训练数据',
    steps: [
      { id: '1', type: 'duplicates', name: '删除重复值', description: '移除完全重复的行', enabled: true, order: 0 },
      { id: '2', type: 'missing', name: '填充缺失值', description: '使用统计方法填充缺失值', enabled: true, order: 1 },
      { id: '3', type: 'outliers', name: '盖帽处理异常值', description: '使用盖帽法处理异常值', enabled: true, order: 2, targetColumns: [], config: { action: 'cap' } },
      { id: '4', type: 'normalize', name: '数据标准化', description: '对数值列进行标准化', enabled: true, order: 3 },
    ],
  },
  {
    name: '数据分析预处理',
    description: '为数据分析和可视化准备数据',
    steps: [
      { id: '1', type: 'duplicates', name: '删除重复值', description: '移除完全重复的行', enabled: true, order: 0 },
      { id: '2', type: 'missing', name: '插值填充', description: '使用插值法填充缺失值', enabled: true, order: 1, config: { method: 'interpolate' } },
      { id: '3', type: 'outliers', name: '标记异常值', description: '标记但不删除异常值', enabled: true, order: 2, config: { action: 'mark' } },
    ],
  },
];
