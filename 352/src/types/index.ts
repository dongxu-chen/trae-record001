export type FieldType = 'string' | 'number' | 'date' | 'boolean';

export interface SourceField {
  id: string;
  name: string;
  type: FieldType;
  sampleValues: string[];
}

export interface TargetField {
  id: string;
  name: string;
  type: FieldType;
  required: boolean;
  description?: string;
}

export type TransformType = 
  | 'concat' 
  | 'split' 
  | 'format' 
  | 'lookup' 
  | 'trim' 
  | 'uppercase' 
  | 'lowercase'
  | 'prefix'
  | 'suffix'
  | 'replace';

export interface BaseTransform {
  id: string;
  type: TransformType;
}

export interface ConcatTransform extends BaseTransform {
  type: 'concat';
  separator: string;
  fields: string[];
}

export interface SplitTransform extends BaseTransform {
  type: 'split';
  separator: string;
  index: number;
}

export interface FormatTransform extends BaseTransform {
  type: 'format';
  pattern: string;
}

export interface LookupTransform extends BaseTransform {
  type: 'lookup';
  mapping: Record<string, string>;
  defaultValue: string;
}

export interface TrimTransform extends BaseTransform {
  type: 'trim';
}

export interface UppercaseTransform extends BaseTransform {
  type: 'uppercase';
}

export interface LowercaseTransform extends BaseTransform {
  type: 'lowercase';
}

export interface PrefixTransform extends BaseTransform {
  type: 'prefix';
  value: string;
}

export interface SuffixTransform extends BaseTransform {
  type: 'suffix';
  value: string;
}

export interface ReplaceTransform extends BaseTransform {
  type: 'replace';
  search: string;
  replace: string;
  global: boolean;
}

export type TransformFunction = 
  | ConcatTransform 
  | SplitTransform 
  | FormatTransform 
  | LookupTransform 
  | TrimTransform 
  | UppercaseTransform 
  | LowercaseTransform
  | PrefixTransform
  | SuffixTransform
  | ReplaceTransform;

export interface Mapping {
  id: string;
  sourceFieldId: string | null;
  targetFieldId: string;
  outputType: FieldType | null;
  transforms: TransformFunction[];
}

export type DataRow = Record<string, any>;

export interface ExportConfig {
  format: 'xlsx' | 'csv' | 'json';
  filename: string;
  includeHeaders: boolean;
}

export interface FlowNodeData {
  label: string;
  type: FieldType;
  isSource: boolean;
  fieldId: string;
}

export interface MappingTemplate {
  id?: number;
  name: string;
  description: string;
  category: string;
  targetFields: TargetField[];
  fieldMappings: Array<{
    sourceFieldName: string;
    targetFieldName: string;
    outputType: FieldType | null;
    transforms: TransformFunction[];
  }>;
  createdAt: number;
  updatedAt: number;
}

export type QualitySeverity = 'error' | 'warning' | 'info';

export interface QualityIssue {
  id: string;
  type: 'missing_mapping' | 'type_mismatch' | 'missing_transform' | 'empty_mapping';
  severity: QualitySeverity;
  message: string;
  targetFieldId?: string;
  sourceFieldId?: string;
  mappingId?: string;
}

export interface QualityReport {
  issues: QualityIssue[];
  score: number;
  totalFields: number;
  mappedFields: number;
  missingFields: number;
  typeWarnings: number;
}

export interface MappingStep {
  id: string;
  name: string;
  stepNumber: number;
  description: string;
  mappings: Mapping[];
  targetFields: TargetField[];
  enabled: boolean;
}

export interface PipelineResult {
  stepId: string;
  stepName: string;
  data: DataRow[];
  duration: number;
}

export interface AppState {
  projectId: number | null;
  sourceFileName: string | null;
  sourceFields: SourceField[];
  sourceData: DataRow[];
  targetFields: TargetField[];
  mappings: Mapping[];
  selectedMapping: string | null;
  previewPage: number;
  previewPageSize: number;
  dataPreviewPage: number;
  dataPageSize: number;
  isLoading: boolean;
  lastSaved: number | null;
  templates: MappingTemplate[];
  mappingSteps: MappingStep[];
  currentStepId: string | null;
  qualityReport: QualityReport | null;
  showQualityPanel: boolean;
  pipelineResults: PipelineResult[];
  setProjectId: (id: number | null) => void;
  setSourceData: (fileName: string, fields: SourceField[], data: DataRow[]) => void;
  setTargetFields: (fields: TargetField[]) => void;
  addMapping: (mapping: Mapping) => void;
  updateMapping: (id: string, updates: Partial<Mapping>) => void;
  removeMapping: (id: string) => void;
  setSelectedMapping: (id: string | null) => void;
  setPreviewPage: (page: number) => void;
  setDataPreviewPage: (page: number) => void;
  addTransform: (mappingId: string, transform: TransformFunction) => void;
  updateTransform: (mappingId: string, transformId: string, updates: Partial<TransformFunction>) => void;
  removeTransform: (mappingId: string, transformId: string) => void;
  setLoading: (loading: boolean) => void;
  setLastSaved: (timestamp: number | null) => void;
  restoreProject: (data: Partial<AppState>) => void;
  saveAsTemplate: (name: string, description: string, category: string) => Promise<number>;
  loadTemplate: (templateId: number) => void;
  deleteTemplate: (templateId: number) => Promise<void>;
  refreshTemplates: () => Promise<void>;
  addMappingStep: (name: string, description: string) => void;
  updateMappingStep: (stepId: string, updates: Partial<MappingStep>) => void;
  removeMappingStep: (stepId: string) => void;
  setCurrentStepId: (stepId: string | null) => void;
  reorderMappingSteps: (stepIds: string[]) => void;
  runPipeline: () => Promise<PipelineResult[]>;
  evaluateQuality: () => QualityReport;
  setShowQualityPanel: (show: boolean) => void;
  clearAll: () => void;
}
