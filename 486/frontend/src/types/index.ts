export type PolicyType = 'mtls' | 'authorization' | 'requestauth';

export type PolicyStatus = 'pending' | 'active' | 'canary' | 'disabled' | 'deleted';

export interface Policy {
  id: string;
  name: string;
  type: PolicyType;
  namespace: string;
  description: string;
  spec: Record<string, any>;
  status: PolicyStatus;
  labels: Record<string, string>;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface ConflictInfo {
  conflict_type: string;
  policy_a: string;
  policy_b: string;
  description: string;
  affected_resources?: string[];
  is_implicit: boolean;
  priority_a: number;
  priority_b: number;
  winning_policy: string;
  severity: string;
}

export interface ConflictDetectionResult {
  has_conflict: boolean;
  conflicts: ConflictInfo[];
  severity: string;
  recommendation?: string;
}

export interface VersionMatrixEntry {
  version: string;
  istio_version: string;
  k8s_version: string;
  release_date: string;
  changes: string[];
  breaking_changes?: string[];
  deprecations?: string[];
  security_fixes?: string[];
}

export interface RiskItem {
  field: string;
  old_value: string;
  new_value: string;
  impact: string;
  severity: string;
}

export interface VersionDiffRisk {
  from_version: string;
  to_version: string;
  risk_level: string;
  risk_score: number;
  risk_items: RiskItem[];
  mitigation: string;
}

export interface ImpactAnalysisResult {
  affected_services: string[];
  affected_workloads: string[];
  risk_level: string;
  estimated_downtime?: string;
  details?: Record<string, any>;
  version_matrix?: VersionMatrixEntry[];
  version_diff_risk?: VersionDiffRisk[];
}

export interface PolicyRecommendation {
  id: string;
  type: PolicyType;
  name: string;
  description: string;
  reason: string;
  confidence: number;
  risk_score: number;
  risk_level: string;
  priority_rank: number;
  security_impact: string;
  business_impact: string;
  affected_services?: string[];
  spec: Record<string, any>;
  generated_at: string;
}

export interface CanaryDeployment {
  id: string;
  policy_id: string;
  strategy: string;
  traffic_percent: number;
  duration: string;
  status: string;
  metrics: CanaryMetrics;
  created_at: string;
  updated_at: string;
}

export interface CanaryMetrics {
  success_rate: number;
  latency_p95: number;
  error_rate: number;
  throughput: number;
}

export interface ServiceTopology {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface TopologyNode {
  id: string;
  name: string;
  type: string;
  health: string;
  metadata?: Record<string, string>;
}

export interface TopologyEdge {
  source: string;
  target: string;
  traffic: number;
  protocol: string;
  metadata?: Record<string, string>;
}

export interface PolicyEvaluationResult {
  policy_id: string;
  allowed: boolean;
  decision_id?: string;
  timestamp: string;
  input: Record<string, any>;
  result?: Record<string, any>;
  explanation?: string;
}

export interface ListPoliciesResponse {
  total: number;
  items: Policy[];
}

export interface SimulationScope {
  namespaces: string[];
  services: string[];
  workloads: string[];
}

export interface PolicySimulationRequest {
  policy_id?: string;
  policy?: Policy;
  target_scope: SimulationScope;
  duration: string;
}

export interface TrafficComparison {
  allow_rate_change: number;
  deny_rate_change: number;
  error_rate_change: number;
  latency_change_pct: number;
  impact_score: number;
}

export interface SimulationTraffic {
  total_requests: number;
  allowed_requests: number;
  denied_requests: number;
  failed_requests: number;
  allow_rate: number;
  deny_rate: number;
  error_rate: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  before_comparison: TrafficComparison;
}

export interface SimulationServiceImpact {
  service_name: string;
  namespace: string;
  before_allow_rate: number;
  after_allow_rate: number;
  request_count: number;
  impact_level: string;
  impact_details: string;
}

export interface SimulationResult {
  simulation_id: string;
  status: string;
  policy_applied: boolean;
  traffic_analysis: SimulationTraffic;
  service_impact: SimulationServiceImpact[];
  conflict_check?: ConflictDetectionResult;
  risk_assessment?: ImpactAnalysisResult;
  recommendations: string[];
  started_at: string;
  completed_at: string;
  is_dry_run: boolean;
}

export type ComplianceStandard = 'pci_dss' | 'gdpr' | 'hipaa' | 'soc2' | 'iso27001';

export interface ComplianceCheckRequest {
  standard: ComplianceStandard;
  scope: SimulationScope;
  include_policies?: string[];
}

export interface ComplianceControl {
  id: string;
  name: string;
  description: string;
  requirement: string;
  category: string;
  severity: string;
  status: string;
  passed: boolean;
  evidence?: string[];
  failed_reasons?: string[];
  affected_resources?: string[];
  related_policies?: string[];
  remediation_guidance?: string;
  references?: string[];
}

export interface ComplianceSummary {
  total_controls: number;
  passed_controls: number;
  failed_controls: number;
  critical_failures: number;
  high_failures: number;
  medium_failures: number;
  low_failures: number;
  estimated_remediation_time: string;
}

export interface ComplianceCheckResult {
  check_id: string;
  standard: ComplianceStandard;
  standard_name: string;
  overall_score: number;
  compliance_rate: number;
  status: string;
  controls: ComplianceControl[];
  failed_controls: ComplianceControl[];
  passed_controls: ComplianceControl[];
  summary: ComplianceSummary;
  checked_at: string;
}

export interface AutoFixRequest {
  policy_id: string;
  issue_type: string;
  issue_detail?: string;
}

export interface PatchChange {
  operation: string;
  path: string;
  old_value: any;
  new_value: any;
  reason: string;
}

export interface PolicyPatch {
  patch_id: string;
  policy_id: string;
  issue_type: string;
  description: string;
  original_spec: Record<string, any>;
  patched_spec: Record<string, any>;
  changes: PatchChange[];
  risk_level: string;
  confidence: number;
  applied: boolean;
  created_at: string;
  alternatives?: PolicyPatch[];
}

export interface AutoFixResult {
  success: boolean;
  patch?: PolicyPatch;
  message: string;
  alternatives?: PolicyPatch[];
  warnings?: string[];
}
