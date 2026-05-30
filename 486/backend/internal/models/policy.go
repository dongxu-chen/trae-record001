package models

import (
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

type PolicyType string

const (
	PolicyTypeMTLS         PolicyType = "mtls"
	PolicyTypeAuthorization PolicyType = "authorization"
	PolicyTypeRequestAuth   PolicyType = "requestauth"
)

type PolicyStatus string

const (
	PolicyStatusPending   PolicyStatus = "pending"
	PolicyStatusActive    PolicyStatus = "active"
	PolicyStatusCanary    PolicyStatus = "canary"
	PolicyStatusDisabled  PolicyStatus = "disabled"
	PolicyStatusDeleted   PolicyStatus = "deleted"
)

type Policy struct {
	ID          string            `json:"id" gorm:"primaryKey"`
	Name        string            `json:"name"`
	Type        PolicyType        `json:"type"`
	Namespace   string            `json:"namespace"`
	Description string            `json:"description"`
	Spec        map[string]interface{} `json:"spec" gorm:"type:json"`
	Status      PolicyStatus      `json:"status"`
	Labels      map[string]string `json:"labels" gorm:"type:json"`
	CreatedAt   time.Time         `json:"created_at"`
	UpdatedAt   time.Time         `json:"updated_at"`
	CreatedBy   string            `json:"created_by"`
}

type MTLSSpec struct {
	Mode               string   `json:"mode"`
	TargetServices     []string `json:"target_services,omitempty"`
	CertificateDetails string   `json:"certificate_details,omitempty"`
}

type AuthorizationSpec struct {
	Action      string              `json:"action"`
	Rules       []AuthorizationRule `json:"rules"`
	TargetRefs  []TargetReference   `json:"target_refs,omitempty"`
}

type AuthorizationRule struct {
	From []Source `json:"from,omitempty"`
	To   []Target `json:"to,omitempty"`
	When []Condition `json:"when,omitempty"`
}

type Source struct {
	Principals  []string `json:"principals,omitempty"`
	Namespaces  []string `json:"namespaces,omitempty"`
	IPBlocks    []string `json:"ip_blocks,omitempty"`
}

type Target struct {
	Hosts   []string `json:"hosts,omitempty"`
	Methods []string `json:"methods,omitempty"`
	Ports   []string `json:"ports,omitempty"`
}

type Condition struct {
	Key    string   `json:"key"`
	Values []string `json:"values"`
}

type RequestAuthSpec struct {
	Selectors map[string]string `json:"selectors,omitempty"`
	JWTRules  []JWTRule         `json:"jwt_rules"`
}

type JWTRule struct {
	Issuer         string   `json:"issuer"`
	Audiences      []string `json:"audiences,omitempty"`
	JwksURI        string   `json:"jwks_uri,omitempty"`
	OutputPayloadToPrefix string `json:"output_payload_to_prefix,omitempty"`
}

type TargetReference struct {
	Name       string `json:"name"`
	Kind       string `json:"kind"`
	APIGroup   string `json:"api_group,omitempty"`
	Namespace  string `json:"namespace,omitempty"`
}

type ConflictDetectionRequest struct {
	PolicyID string `json:"policy_id"`
}

type ConflictDetectionResult struct {
	HasConflict    bool           `json:"has_conflict"`
	Conflicts      []ConflictInfo `json:"conflicts"`
	Severity       string         `json:"severity"`
	Recommendation string         `json:"recommendation,omitempty"`
}

type ConflictInfo struct {
	ConflictType      string   `json:"conflict_type"`
	PolicyA           string   `json:"policy_a"`
	PolicyB           string   `json:"policy_b"`
	Description       string   `json:"description"`
	AffectedResources []string `json:"affected_resources,omitempty"`
	IsImplicit        bool     `json:"is_implicit"`
	PriorityA         int      `json:"priority_a"`
	PriorityB         int      `json:"priority_b"`
	WinningPolicy     string   `json:"winning_policy"`
	Severity          string   `json:"severity"`
}

type ImpactAnalysisRequest struct {
	PolicyID string `json:"policy_id"`
}

type ImpactAnalysisResult struct {
	AffectedServices  []string        `json:"affected_services"`
	AffectedWorkloads []string        `json:"affected_workloads"`
	RiskLevel         string          `json:"risk_level"`
	EstimatedDowntime string          `json:"estimated_downtime,omitempty"`
	Details           map[string]interface{} `json:"details,omitempty"`
	VersionMatrix     []VersionMatrixEntry  `json:"version_matrix,omitempty"`
	VersionDiffRisk   []VersionDiffRisk     `json:"version_diff_risk,omitempty"`
}

type VersionMatrixEntry struct {
	Version       string            `json:"version"`
	IstioVersion  string            `json:"istio_version"`
	K8sVersion    string            `json:"k8s_version"`
	ReleaseDate   time.Time         `json:"release_date"`
	Changes       []string          `json:"changes"`
	BreakingChanges []string        `json:"breaking_changes,omitempty"`
	Deprecations  []string          `json:"deprecations,omitempty"`
	SecurityFixes []string          `json:"security_fixes,omitempty"`
}

type VersionDiffRisk struct {
	FromVersion   string   `json:"from_version"`
	ToVersion     string   `json:"to_version"`
	RiskLevel     string   `json:"risk_level"`
	RiskScore     float64  `json:"risk_score"`
	RiskItems     []RiskItem `json:"risk_items"`
	Mitigation    string   `json:"mitigation"`
}

type RiskItem struct {
	Field         string `json:"field"`
	OldValue      string `json:"old_value"`
	NewValue      string `json:"new_value"`
	Impact        string `json:"impact"`
	Severity      string `json:"severity"`
}

type PolicyRecommendation struct {
	ID              string            `json:"id"`
	Type            PolicyType        `json:"type"`
	Name            string            `json:"name"`
	Description     string            `json:"description"`
	Reason          string            `json:"reason"`
	Confidence      float64           `json:"confidence"`
	RiskScore       float64           `json:"risk_score"`
	RiskLevel       string            `json:"risk_level"`
	PriorityRank    int               `json:"priority_rank"`
	SecurityImpact  string            `json:"security_impact"`
	BusinessImpact  string            `json:"business_impact"`
	AffectedServices []string         `json:"affected_services,omitempty"`
	Spec            map[string]interface{} `json:"spec"`
	GeneratedAt     time.Time         `json:"generated_at"`
}

type CanaryDeployment struct {
	ID             string    `json:"id"`
	PolicyID       string    `json:"policy_id"`
	Strategy       string    `json:"strategy"`
	TrafficPercent int       `json:"traffic_percent"`
	Duration       string    `json:"duration"`
	Status         string    `json:"status"`
	Metrics        CanaryMetrics `json:"metrics,omitempty"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

type CanaryMetrics struct {
	SuccessRate    float64 `json:"success_rate"`
	LatencyP95     float64 `json:"latency_p95"`
	ErrorRate      float64 `json:"error_rate"`
	Throughput     float64 `json:"throughput"`
}

type ServiceTopology struct {
	Nodes []TopologyNode `json:"nodes"`
	Edges []TopologyEdge `json:"edges"`
}

type TopologyNode struct {
	ID       string            `json:"id"`
	Name     string            `json:"name"`
	Type     string            `json:"type"`
	Health   string            `json:"health"`
	Metadata map[string]string `json:"metadata,omitempty"`
}

type TopologyEdge struct {
	Source   string            `json:"source"`
	Target   string            `json:"target"`
	Traffic  float64           `json:"traffic"`
	Protocol string            `json:"protocol"`
	Metadata map[string]string `json:"metadata,omitempty"`
}

type PolicyEvaluationResult struct {
	PolicyID    string                 `json:"policy_id"`
	Allowed     bool                   `json:"allowed"`
	DecisionID  string                 `json:"decision_id,omitempty"`
	Timestamp   time.Time              `json:"timestamp"`
	Input       map[string]interface{} `json:"input"`
	Result      map[string]interface{} `json:"result,omitempty"`
	Explanation string                 `json:"explanation,omitempty"`
}

type ListPoliciesResponse struct {
	Total int      `json:"total"`
	Items []Policy `json:"items"`
}

type KubernetesResource struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`
}

type PolicySimulationRequest struct {
	PolicyID    string                   `json:"policy_id"`
	Policy      *Policy                  `json:"policy"`
	TargetScope SimulationScope          `json:"target_scope"`
	Duration    string                   `json:"duration"`
}

type SimulationScope struct {
	Namespaces []string `json:"namespaces"`
	Services   []string `json:"services"`
	Workloads  []string `json:"workloads"`
}

type SimulationResult struct {
	SimulationID    string                 `json:"simulation_id"`
	Status          string                 `json:"status"`
	PolicyApplied   bool                   `json:"policy_applied"`
	TrafficAnalysis SimulationTraffic      `json:"traffic_analysis"`
	ServiceImpact   []SimulationServiceImpact `json:"service_impact"`
	ConflictCheck   *ConflictDetectionResult `json:"conflict_check"`
	RiskAssessment  *ImpactAnalysisResult   `json:"risk_assessment"`
	Recommendations []string               `json:"recommendations"`
	StartedAt       time.Time              `json:"started_at"`
	CompletedAt     time.Time              `json:"completed_at"`
	IsDryRun        bool                   `json:"is_dry_run"`
}

type SimulationTraffic struct {
	TotalRequests      int64   `json:"total_requests"`
	AllowedRequests    int64   `json:"allowed_requests"`
	DeniedRequests     int64   `json:"denied_requests"`
	FailedRequests     int64   `json:"failed_requests"`
	AllowRate          float64 `json:"allow_rate"`
	DenyRate           float64 `json:"deny_rate"`
	ErrorRate          float64 `json:"error_rate"`
	AvgLatencyMs       float64 `json:"avg_latency_ms"`
	P95LatencyMs       float64 `json:"p95_latency_ms"`
	BeforeComparison   TrafficComparison `json:"before_comparison"`
}

type TrafficComparison struct {
	AllowRateChange    float64 `json:"allow_rate_change"`
	DenyRateChange     float64 `json:"deny_rate_change"`
	ErrorRateChange    float64 `json:"error_rate_change"`
	LatencyChangePct   float64 `json:"latency_change_pct"`
	ImpactScore        float64 `json:"impact_score"`
}

type SimulationServiceImpact struct {
	ServiceName      string  `json:"service_name"`
	Namespace        string  `json:"namespace"`
	BeforeAllowRate  float64 `json:"before_allow_rate"`
	AfterAllowRate   float64 `json:"after_allow_rate"`
	RequestCount     int64   `json:"request_count"`
	ImpactLevel      string  `json:"impact_level"`
	ImpactDetails    string  `json:"impact_details"`
}

type ComplianceStandard string

const (
	ComplianceStandardPCI   ComplianceStandard = "pci_dss"
	ComplianceStandardGDPR  ComplianceStandard = "gdpr"
	ComplianceStandardHIPAA ComplianceStandard = "hipaa"
	ComplianceStandardSOC2  ComplianceStandard = "soc2"
	ComplianceStandardISO27001 ComplianceStandard = "iso27001"
)

type ComplianceCheckRequest struct {
	Standard     ComplianceStandard `json:"standard"`
	Scope        SimulationScope    `json:"scope"`
	IncludePolicies []string       `json:"include_policies,omitempty"`
}

type ComplianceCheckResult struct {
	CheckID        string             `json:"check_id"`
	Standard       ComplianceStandard `json:"standard"`
	StandardName   string             `json:"standard_name"`
	OverallScore   float64            `json:"overall_score"`
	ComplianceRate float64            `json:"compliance_rate"`
	Status         string             `json:"status"`
	Controls       []ComplianceControl `json:"controls"`
	FailedControls []ComplianceControl `json:"failed_controls"`
	PassedControls []ComplianceControl `json:"passed_controls"`
	Summary        ComplianceSummary  `json:"summary"`
	CheckedAt      time.Time          `json:"checked_at"`
}

type ComplianceControl struct {
	ID              string   `json:"id"`
	Name            string   `json:"name"`
	Description     string   `json:"description"`
	Requirement     string   `json:"requirement"`
	Category        string   `json:"category"`
	Severity        string   `json:"severity"`
	Status          string   `json:"status"`
	Passed          bool     `json:"passed"`
	Evidence        []string `json:"evidence,omitempty"`
	FailedReasons   []string `json:"failed_reasons,omitempty"`
	AffectedResources []string `json:"affected_resources,omitempty"`
	RelatedPolicies []string `json:"related_policies,omitempty"`
	RemediationGuidance string `json:"remediation_guidance,omitempty"`
	References      []string `json:"references,omitempty"`
}

type ComplianceSummary struct {
	TotalControls    int     `json:"total_controls"`
	PassedControls   int     `json:"passed_controls"`
	FailedControls   int     `json:"failed_controls"`
	CriticalFailures int     `json:"critical_failures"`
	HighFailures     int     `json:"high_failures"`
	MediumFailures   int     `json:"medium_failures"`
	LowFailures      int     `json:"low_failures"`
	EstimatedRemediationTime string `json:"estimated_remediation_time"`
}

type AutoFixRequest struct {
	PolicyID    string `json:"policy_id"`
	IssueType   string `json:"issue_type"`
	IssueDetail string `json:"issue_detail"`
}

type PolicyPatch struct {
	PatchID     string                 `json:"patch_id"`
	PolicyID    string                 `json:"policy_id"`
	IssueType   string                 `json:"issue_type"`
	Description string                 `json:"description"`
	OriginalSpec map[string]interface{} `json:"original_spec"`
	PatchedSpec  map[string]interface{} `json:"patched_spec"`
	Changes     []PatchChange          `json:"changes"`
	RiskLevel   string                 `json:"risk_level"`
	Confidence  float64                `json:"confidence"`
	Applied     bool                   `json:"applied"`
	CreatedAt   time.Time              `json:"created_at"`
}

type PatchChange struct {
	Operation string      `json:"operation"`
	Path      string      `json:"path"`
	OldValue  interface{} `json:"old_value"`
	NewValue  interface{} `json:"new_value"`
	Reason    string      `json:"reason"`
}

type AutoFixResult struct {
	Success      bool          `json:"success"`
	Patch        *PolicyPatch  `json:"patch,omitempty"`
	Message      string        `json:"message"`
	Alternatives []PolicyPatch `json:"alternatives,omitempty"`
	Warnings     []string      `json:"warnings,omitempty"`
}
