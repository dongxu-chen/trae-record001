export type DataSourceType = 'mysql' | 'hive';

export type NodeType = 'field' | 'table' | 'etl' | 'report';

export type EdgeType = 'direct' | 'transform' | 'aggregate';

export type ReportType = 'dashboard' | 'report' | 'chart';

export interface DataSource {
  id: string;
  name: string;
  type: DataSourceType;
  host: string;
  port: number;
  database: string;
  username?: string;
  password?: string;
  status: 'connected' | 'disconnected' | 'connecting';
}

export interface FieldNode {
  id: string;
  name: string;
  table: string;
  database: string;
  datasource: string;
  type: NodeType;
  description?: string;
  createdAt?: string;
  depth?: number;
  hasChildren?: boolean;
  isExpanded?: boolean;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface LineageEdge {
  id: string;
  source: string;
  target: string;
  type: EdgeType;
  transformation?: string;
  etlTask?: string;
}

export interface LineageGraph {
  nodes: FieldNode[];
  edges: LineageEdge[];
}

export interface ETLTask {
  id: string;
  name: string;
  script: string;
  schedule: string;
  owner: string;
  lastRun: string;
  status: 'success' | 'failed' | 'running';
}

export interface Report {
  id: string;
  name: string;
  type: ReportType;
  url?: string;
  owner: string;
  updatedAt: string;
}

export interface TableInfo {
  id: string;
  name: string;
  database: string;
  datasource: string;
  fieldCount: number;
}

export interface DownstreamByDepth {
  depth: number;
  nodes: FieldNode[];
}

export interface AnalysisResult {
  fieldId: string;
  fieldName: string;
  graph: LineageGraph;
  statistics: {
    totalDownstreamNodes: number;
    etlTasks: number;
    reports: number;
    tables: number;
    maxDepth: number;
  };
  downstreamList: {
    etlTasks: ETLTask[];
    reports: Report[];
    tables: TableInfo[];
  };
  downstreamByDepth: DownstreamByDepth[];
}

export type ChangeType = 'rename' | 'delete' | 'type_change' | 'constraint_change' | 'default_change';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface ChangeRiskAssessment {
  fieldId: string;
  fieldName: string;
  changeType: ChangeType;
  riskLevel: RiskLevel;
  riskScore: number;
  impactScope: {
    affectedETLTasks: number;
    affectedReports: number;
    affectedTables: number;
    affectedOwners: number;
    maxDepth: number;
  };
  riskFactors: RiskFactor[];
  recommendations: string[];
  estimatedRecoveryTime: string;
  requiresDowntime: boolean;
}

export interface RiskFactor {
  id: string;
  category: 'data_loss' | 'logic_break' | 'performance' | 'compatibility';
  description: string;
  severity: RiskLevel;
  affectedItems: string[];
}

export interface FieldDictionary {
  fieldId: string;
  fieldName: string;
  table: string;
  database: string;
  dataType: string;
  nullable: boolean;
  defaultValue?: string;
  description: string;
  businessMeaning: string;
  enumValues?: EnumValue[];
  sampleValues: string[];
  valueRange?: { min?: number; max?: number };
  patterns: string[];
  relatedFields: string[];
  lastUpdated: string;
  updatedBy: string;
}

export interface EnumValue {
  value: string;
  label: string;
  description?: string;
  frequency?: number;
}

export interface ChangeSubscription {
  id: string;
  fieldId: string;
  fieldName: string;
  subscriberEmail: string;
  subscriberName: string;
  changeTypes: ChangeType[];
  notifyOnRiskLevel: RiskLevel[];
  isActive: boolean;
  createdAt: string;
  lastNotifiedAt?: string;
}

export interface ChangeNotification {
  id: string;
  subscriptionId: string;
  fieldId: string;
  fieldName: string;
  changeType: ChangeType;
  changeDescription: string;
  riskLevel: RiskLevel;
  notifiedEmails: string[];
  notifiedAt: string;
  status: 'sent' | 'pending' | 'failed';
}

export interface SearchHistory {
  id: string;
  fieldId: string;
  fieldName: string;
  timestamp: string;
  datasources: string[];
}
