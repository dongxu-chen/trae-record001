export type NamingStyle = 'camelCase' | 'snake_case' | 'PascalCase' | 'kebab-case' | 'SCREAMING_SNAKE_CASE';

export type Language = 'zh' | 'en' | 'ja' | 'ko' | 'other';

export type VariableType = 'variable' | 'function' | 'class' | 'constant' | 'boolean';

export interface Recommendation {
  id: string;
  name: string;
  style: NamingStyle;
  confidence: number;
  type: VariableType;
  description: string;
}

export interface NamingRequest {
  input: string;
  inputType: 'description' | 'code';
  targetStyle?: NamingStyle;
  variableType?: VariableType;
  context?: string;
}

export interface TypeInferenceResult {
  type: VariableType;
  confidence: number;
  hints: string[];
  originalContext: string;
}

export interface NamingResponse {
  success: boolean;
  recommendations: Recommendation[];
  detectedLanguage: Language;
  detectedType: VariableType;
  processingTime: number;
  typeInference?: TypeInferenceResult;
}

export interface HistoryItem {
  id: string;
  input: string;
  selectedName: string;
  style: NamingStyle;
  timestamp: number;
  isFavorite: boolean;
  feedback?: 'like' | 'dislike';
}

export interface UserSettings {
  defaultStyle: NamingStyle;
  preferredLanguage: Language;
  autoDetectLanguage: boolean;
  showConfidence: boolean;
  maxRecommendations: number;
}

export interface ConvertRequest {
  name: string;
  targetStyle: NamingStyle;
}

export interface ConvertResponse {
  success: boolean;
  result: string;
}

export interface LearningData {
  stylePreferences: Record<NamingStyle, number>;
  wordFrequency: Record<string, number>;
  patternFrequency: Record<string, number>;
  nameFrequency: Record<string, number>;
  totalUsage: number;
  minFrequencyThreshold: number;
}

export interface TeamNamingRule {
  id: string;
  name: string;
  description: string;
  type: 'prefix' | 'suffix' | 'pattern' | 'forbidden' | 'required';
  value: string;
  variableTypes: VariableType[];
  enabled: boolean;
  priority: number;
  createdAt: number;
}

export interface TeamNamingConfig {
  teamName: string;
  rules: TeamNamingRule[];
  defaultStyle: NamingStyle;
  enforcedStyles: Record<VariableType, NamingStyle>;
  forbiddenWords: string[];
  preferredAbbreviations: Record<string, string>;
  lastSyncTime: number;
}

export interface BatchRenameItem {
  id: string;
  oldName: string;
  newName: string;
  type: VariableType;
  occurrences: number;
  status: 'pending' | 'renamed' | 'conflict' | 'skipped';
  conflictMessage?: string;
}

export interface BatchRenameRequest {
  code: string;
  language: 'javascript' | 'typescript' | 'python' | 'java' | 'go';
  items: BatchRenameItem[];
  dryRun?: boolean;
}

export interface BatchRenameResult {
  success: boolean;
  modifiedCode: string;
  results: Array<{
    oldName: string;
    newName: string;
    renamed: boolean;
    occurrences: number;
    error?: string;
  }>;
  totalRenamed: number;
  totalSkipped: number;
}

export interface ConflictInfo {
  name: string;
  type: 'variable' | 'function' | 'class' | 'import' | 'keyword';
  scope: string;
  lineNumber?: number;
  suggestion?: string;
}

export interface ConflictDetectionRequest {
  name: string;
  code: string;
  scope?: string;
}

export interface ConflictDetectionResult {
  hasConflict: boolean;
  conflicts: ConflictInfo[];
  suggestions: string[];
}
