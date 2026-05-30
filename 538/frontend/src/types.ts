export interface PodNode {
  name: string
  namespace: string
  labels: Record<string, string>
  ip: string
  podSelector: Record<string, string>
}

export interface FlowEdge {
  sourceName: string
  sourceNamespace: string
  destName: string
  destNamespace: string
  protocol: string
  port: number
  count: number
  lastSeen: string
}

export interface CommPair {
  source: string
  destination: string
  protocol: string
  port: number
  sourceType: string
  destType: string
  sourceLabel: Record<string, string>
  destLabel: Record<string, string>
}

export interface CoverageReport {
  totalPairs: number
  coveredPairs: number
  coverageRatio: number
  uncoveredPairs: CommPair[]
  coveredByPolicy: Record<string, CommPair[]>
}

export interface PolicyRecommendation {
  name: string
  namespace: string
  description: string
  policy: NetworkPolicy
  reasoning: string[]
  confidence: number
  coveredPairs: CommPair[]
}

export interface NetworkPolicy {
  metadata: {
    name: string
    namespace: string
    labels: Record<string, string>
  }
  spec: {
    podSelector: {
      matchLabels: Record<string, string>
    }
    ingress?: IngressRule[]
    egress?: EgressRule[]
    policyTypes: string[]
  }
}

export interface IngressRule {
  from?: NetworkPolicyPeer[]
  ports?: NetworkPolicyPort[]
}

export interface EgressRule {
  to?: NetworkPolicyPeer[]
  ports?: NetworkPolicyPort[]
}

export interface NetworkPolicyPeer {
  podSelector?: {
    matchLabels: Record<string, string>
  }
  namespaceSelector?: {
    matchLabels: Record<string, string>
  }
}

export interface NetworkPolicyPort {
  protocol?: string
  port?: {
    type: number
    intVal: number
  }
}

export interface AffectedFlow {
  source: string
  destination: string
  port: number
  protocol: string
  direction: string
}

export interface PolicyConflict {
  type: string
  severity: string
  policyA: string
  policyB: string
  description: string
  recommendation: string
  affectedTraffic?: AffectedFlow[]
}

export interface SimulationResult {
  allowedFlows: SimulatedFlow[]
  deniedFlows: SimulatedFlow[]
  policyCoverage: number
}

export interface SimulatedFlow {
  source: string
  destination: string
  port: number
  protocol: string
  allowed: boolean
  reason: string
}

export interface SamplerStats {
  sampleRate: number
  totalSeen: number
  totalSampled: number
  activeEntries: number
  maxEntries: number
  effectiveRate: number
}

export interface PolicyBackup {
  id: string
  name: string
  namespace: string
  createdAt: string
  reason: string
  policies: NetworkPolicy[]
  flowSnapshot?: FlowSnapshot
  policyHash: string
}

export interface FlowSnapshot {
  timestamp: string
  flows: FlowEdge[]
  flowHash: string
}

export interface ApplyResult {
  policyName: string
  status: string
  error?: string
}

export interface BatchApplyResult {
  backupId: string
  totalPolicies: number
  successCount: number
  failedCount: number
  results: ApplyResult[]
}

export interface TrafficSummary {
  source: string
  destination: string
  protocol: string
  port: number
  count: number
  lastSeen: string
}

export interface TrafficDelta extends TrafficSummary {
  countBefore: number
  countAfter: number
  delta: number
}

export interface EffectEvaluation {
  backupId: string
  beforeSnapshot: FlowSnapshot
  afterSnapshot: FlowSnapshot
  newFlows: TrafficSummary[]
  lostFlows: TrafficSummary[]
  changedFlows: TrafficDelta[]
  totalFlowsBefore: number
  totalFlowsAfter: number
  blockedFlowCount: number
  newFlowCount: number
  evaluationTime: string
}
