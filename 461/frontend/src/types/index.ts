export type ApiVersionStatus = 'DRAFT' | 'ACTIVE' | 'DEPRECATED' | 'RETIRED';

export interface ApiVersion {
  id: string;
  name: string;
  version: string;
  status: ApiVersionStatus;
  description: string;
  basePath: string;
  openApiSpec: string;
  createdAt: string;
  updatedAt: string;
  deprecatedAt?: string;
  retireAt?: string;
}

export type RoutingStrategy = 'PATH' | 'HEADER' | 'QUERY' | 'WEIGHTED';

export type GrayStrategyType = 'USER_ID' | 'IP' | 'WEIGHT' | 'CUSTOM';

export type HeaderParseStrategy = 'DIRECT' | 'REGEX' | 'PREFIX' | 'DELIMITER' | 'SEMVER';

export interface HeaderParseRule {
  id?: string;
  headerName: string;
  parseStrategy: HeaderParseStrategy;
  pattern?: string;
  defaultValue?: string;
  priority?: number;
}

export interface GrayStrategy {
  type: GrayStrategyType;
  includeList?: string[];
  excludeList?: string[];
  weight?: number;
  customRule?: string;
}

export interface RoutingRule {
  id: string;
  apiName: string;
  versionWeights: Record<string, number>;
  strategy: RoutingStrategy;
  matchExpression?: string;
  headerParseRules?: HeaderParseRule[];
  grayStrategy?: GrayStrategy;
  createdAt: string;
  enabled?: boolean;
}

export type ChangeType = 'ADD' | 'REMOVE' | 'MODIFY';

export type ChangeLevel = 'ERROR' | 'WARNING' | 'INFO';

export interface Change {
  type: ChangeType;
  path: string;
  field: string;
  oldValue?: string;
  newValue?: string;
  description: string;
  level: ChangeLevel;
}

export interface VersionDiff {
  baseVersion: string;
  targetVersion: string;
  breakingChanges: Change[];
  nonBreakingChanges: Change[];
  deprecatedChanges: Change[];
  responseChanges?: Change[];
}

export interface CompatibilityReport {
  isCompatible: boolean;
  breakingChangeCount: number;
  warningCount: number;
  details: string[];
  recommendations: string[];
  backwardCompatibilityScore?: number;
  backwardCompatibilityLevel?: 'EXCELLENT' | 'GOOD' | 'MODERATE' | 'POOR' | 'CRITICAL';
  backwardCompatibilityAnalysis?: string;
  migrationComplexity?: number;
  rateLimitingRecommendation?: string;
  backwardCompatibleChanges?: Change[];
}

export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export interface PageResult<T> {
  list: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface RoutingMetric {
  apiName: string;
  totalRequests: number;
  v1Requests: number;
  v2Requests: number;
  successRate: number;
  avgResponseTime: number;
}

export interface DiffRequest {
  baseVersionId: string;
  targetVersionId: string;
}

export interface DiffResult {
  id: string;
  baseVersionId: string;
  targetVersionId: string;
  diffContent: VersionDiff;
  breakingChanges: number;
  warningChanges: number;
  isCompatible: boolean;
  createdAt: string;
}

export type MockType = 'SUCCESS' | 'DELAY' | 'ERROR' | 'CUSTOM';

export interface MockVersionConfig {
  id?: string;
  versionId: string;
  path: string;
  method: string;
  mockType: MockType;
  delayMs?: number;
  errorCode?: number;
  errorMessage?: string;
  customResponse?: string;
  enabled?: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface VersionCallStat {
  serviceName: string;
  version: string;
  callCount: number;
  successCount: number;
  failCount: number;
  avgResponseTime: number;
  percentage?: number;
}

export interface VersionStatsData {
  versions: VersionCallStat[];
  totalCalls: number;
  trendData: {
    dates: string[];
    versions: Record<string, number[]>;
  };
}

export interface DeprecatedVersionSchedule {
  id: string;
  serviceName: string;
  version: string;
  status: string;
  deprecateTime?: string;
  plannedRetireTime?: string;
  deprecationMessage?: string;
  daysRemaining?: number;
}
