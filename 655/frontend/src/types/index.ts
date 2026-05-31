export interface RoutingRule {
  id: string;
  name: string;
  namespace: string;
  type: 'weight' | 'header' | 'mirror' | 'fault';
  serviceName: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface SubsetWeight {
  subsetName: string;
  weight: number;
  version: string;
}

export interface WeightRouting extends RoutingRule {
  subsets: SubsetWeight[];
}

export interface HeaderMatch {
  headerName: string;
  matchType: 'exact' | 'prefix' | 'regex';
  value: string;
  values?: string[];
}

export interface HeaderRouting extends RoutingRule {
  matchRules: HeaderMatch[];
  targetSubset: string;
}

export interface TrafficMirror extends RoutingRule {
  mirrorService: string;
  mirrorSubset?: string;
  mirrorPort?: number;
  sourceService: string;
  percentage: number;
}

export interface DelaySpec {
  fixedDelay: string;
}

export interface AbortSpec {
  httpStatus: number;
}

export interface FaultInjection extends RoutingRule {
  faultType: 'delay' | 'abort';
  percentage: number;
  delay?: DelaySpec;
  abort?: AbortSpec;
}

export interface ServiceNode {
  id: string;
  name: string;
  namespace: string;
  type: string;
  version: string;
  labels?: Record<string, string>;
  metrics?: TrafficMetrics;
  x?: number;
  y?: number;
}

export interface ServiceEdge {
  id: string;
  source: string;
  target: string;
  protocol: string;
  traffic: number;
  latency: number;
  errorRate: number;
  requestCount: number;
}

export interface TrafficTopology {
  nodes: ServiceNode[];
  edges: ServiceEdge[];
}

export interface TrafficMetrics {
  serviceName: string;
  namespace: string;
  requestCount: number;
  errorCount: number;
  p50Latency: number;
  p95Latency: number;
  p99Latency: number;
  successRate: number;
  throughput: number;
  timestamp: string;
}

export interface ServiceReport {
  serviceName: string;
  totalRequests: number;
  errorRate: number;
  avgLatency: number;
  trafficIn: number;
  trafficOut: number;
  versionBreakdown: Record<string, number>;
}

export interface TrafficReport {
  id: string;
  name: string;
  type: string;
  startDate: string;
  endDate: string;
  services: ServiceReport[];
  generatedAt: string;
}

export interface VirtualService {
  apiVersion: string;
  kind: string;
  metadata: {
    name: string;
    namespace: string;
  };
  spec: any;
}

export interface DestinationRule {
  apiVersion: string;
  kind: string;
  metadata: {
    name: string;
    namespace: string;
  };
  spec: any;
}

export interface DeploymentStep {
  timestamp: string;
  weightBlue: number;
  weightGreen: number;
  success: boolean;
  errorRate: number;
  latencyP95: number;
  rollback: boolean;
  message?: string;
}

export interface BlueGreenDeployment {
  id: string;
  name: string;
  namespace: string;
  serviceName: string;
  blueSubset: string;
  greenSubset: string;
  blueVersion: string;
  greenVersion: string;
  currentWeightBlue: number;
  targetWeightBlue: number;
  stepSize: number;
  stepIntervalSeconds: number;
  autoRollbackEnabled: boolean;
  rollbackThreshold: number;
  status: 'pending' | 'running' | 'paused' | 'rollback' | 'rolled-back' | 'completed';
  phase: string;
  createdAt: string;
  updatedAt: string;
  deploymentHistory?: DeploymentStep[];
}

export interface AccessControlRule {
  id: string;
  name: string;
  namespace: string;
  serviceName: string;
  ruleType: 'ip' | 'user' | 'header';
  controlType: 'allow' | 'deny';
  listType: 'whitelist' | 'blacklist';
  ipList?: string[];
  userIdList?: string[];
  headerName?: string;
  headerValues?: string[];
  priority: number;
  status: 'active' | 'inactive';
  description?: string;
  createdAt: string;
  updatedAt: string;
}

export interface CostBreakdownItem {
  name: string;
  description: string;
  amount: number;
  percentage: number;
}

export interface CostEstimateRequest {
  serviceName?: string;
  namespace?: string;
  startDate?: string;
  endDate?: string;
  trafficGB: number;
  crossAZRatio: number;
  region: string;
  cloudProvider: string;
}

export interface CostEstimateResult {
  id: string;
  totalCost: number;
  intraAZCost: number;
  crossAZCost: number;
  intraAZTrafficGB: number;
  crossAZTrafficGB: number;
  costPerGBIntraAZ: number;
  costPerGBCrossAZ: number;
  estimatedRequests: number;
  avgRequestSizeKB: number;
  currency: string;
  region: string;
  cloudProvider: string;
  generatedAt: string;
  breakdown?: CostBreakdownItem[];
}

export interface CostConfig {
  cloudProvider: string;
  region: string;
  currency: string;
  intraAZRate: Record<string, number>;
  crossAZRate: Record<string, number>;
}
