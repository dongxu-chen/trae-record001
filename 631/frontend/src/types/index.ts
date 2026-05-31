export interface TopologyNode {
  id: string;
  name: string;
  namespace: string;
  type: string;
  language: string;
  version: string;
  status: string;
  serviceType: string;
  clusterIp: string;
  groupId?: string;
  groupName?: string;
}

export interface TopologyEdge {
  source: string;
  target: string;
  callType: string;
  protocol: string;
  isAsync: boolean;
  messageQueue: string;
  httpMethod: string;
  path: string;
  callCount: number;
  errorCount: number;
  successCount: number;
  avgLatencyMs: number;
  lastSeen: string;
  traceId?: string;
  consumerGroup?: string;
  messageTopic?: string;
  qps?: number;
  peakQps?: number;
}

export interface TopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface TopologyGroup {
  id: string;
  name: string;
  namespace: string;
  groupType: string;
  description: string;
  collapsed: boolean;
  parentId?: string;
  serviceCount: number;
  serviceIds: string[];
}

export interface ConsumerGroupNode {
  id: string;
  name: string;
  namespace: string;
  messageQueue: string;
  topic: string;
  consumerCount: number;
  status: string;
  producerIds: string[];
  consumerIds: string[];
}

export interface GroupedTopologyData {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  groups: TopologyGroup[];
  consumerGroups: ConsumerGroupNode[];
}

export interface TraceInfo {
  traceId: string;
  status: string;
  startTime: string;
  endTime: string;
  durationMs: number;
  spanCount: number;
  errorCount: number;
}

export interface TraceCall {
  sourceId: string;
  sourceName: string;
  targetId: string;
  targetName: string;
  callType: string;
  protocol: string;
  isAsync: boolean;
  messageQueue: string;
  httpMethod: string;
  path: string;
  callCount: number;
  errorCount: number;
  avgLatencyMs: number;
  spanId?: string;
  parentSpanId?: string;
  correlationId?: string;
}

export interface TraceDetail {
  traceId: string;
  status: string;
  startTime: string;
  endTime: string;
  durationMs: number;
  spanCount: number;
  errorCount: number;
  calls: TraceCall[];
}

export interface TopologyStats {
  totalServices: number;
  namespaces: string[];
  languages: string[];
  serviceTypes: string[];
  totalCallRelationships: number;
  totalCallCount: number;
  totalErrorCount: number;
  averageLatencyMs: number;
}

export interface ServiceCallDetail {
  serviceId: string;
  serviceName: string;
  callType: string;
  protocol: string;
  isAsync: boolean;
  messageQueue: string;
  httpMethod: string;
  path: string;
  callCount: number;
  errorCount: number;
  avgLatencyMs: number;
}

export interface ServiceNodeDetail {
  id: string;
  name: string;
  namespace: string;
  type: string;
  language: string;
  version: string;
  status: string;
  serviceType: string;
  clusterIp: string;
  ports: string;
  labels: string;
  annotations: string;
  discoveredAt: string;
  lastUpdated: string;
  incomingCalls: ServiceCallDetail[];
  outgoingCalls: ServiceCallDetail[];
}

export interface GraphNode {
  id: string;
  label: string;
  group?: string;
  level?: number;
  color?: {
    background: string;
    border: string;
  };
  shape?: string;
  size?: number;
  font?: {
    color: string;
    size: number;
  };
  isGroup?: boolean;
  collapsed?: boolean;
  childCount?: number;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  label?: string;
  color?: string;
  width?: number;
  dashes?: boolean;
  arrows?: {
    to: {
      enabled: boolean;
      scaleFactor: number;
    };
  };
}

export interface ImpactAnalysisResult {
  serviceId: string;
  upstreamServices: string[];
  downstreamServices: string[];
  upstreamEdges: ImpactEdge[];
  downstreamEdges: ImpactEdge[];
  totalUpstreamImpact: number;
  totalDownstreamImpact: number;
  riskLevel: string;
}

export interface ImpactEdge {
  source: string;
  target: string;
  callCount: number;
  qps: number;
  avgLatencyMs: number;
}

export interface ChangePredictionResult {
  serviceId: string;
  changeType: string;
  impactedServices: ImpactedService[];
  totalImpactedServices: number;
  highSeverityCount: number;
  mediumSeverityCount: number;
  lowSeverityCount: number;
  estimatedDowntimeMinutes: number;
  estimatedRecoveryHours: number;
  recommendation: string;
}

export interface ImpactedService {
  serviceId: string;
  callCount: number;
  qps: number;
  avgLatencyMs: number;
  severity: string;
  impactScore: number;
}

export interface TrafficEstimate {
  edgeId: string;
  source: string;
  target: string;
  currentQps: number;
  peakQps: number;
  dailyCalls: number;
  projectedGrowthRate: number;
  projectedQpsNextMonth: number;
  trafficLevel: string;
}
