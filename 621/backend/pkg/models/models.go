package models

import (
	"time"
)

type SamplingStrategy string

const (
	SamplingFull    SamplingStrategy = "FULL"
	SamplingEdge    SamplingStrategy = "EDGE"
	SamplingAdaptive SamplingStrategy = "ADAPTIVE"
)

type EdgeType string

const (
	EdgeTypeIngress EdgeType = "INGRESS"
	EdgeTypeEgress  EdgeType = "EGRESS"
	EdgeTypeInternal EdgeType = "INTERNAL"
)

type Service struct {
	Name      string    `json:"name"`
	Namespace string    `json:"namespace"`
	Version   string    `json:"version,omitempty"`
	Labels    map[string]string `json:"labels,omitempty"`
}

type CallEdge struct {
	Source        Service    `json:"source"`
	Destination   Service    `json:"destination"`
	Method        string     `json:"method"`
	Path          string     `json:"path"`
	Count         int        `json:"count"`
	LastSeen      time.Time  `json:"lastSeen"`
	EdgeType      EdgeType   `json:"edgeType"`
	Sampled       bool       `json:"sampled"`
	SamplingReason string    `json:"samplingReason"`
}

type ServiceGraph struct {
	Services []Service  `json:"services"`
	Edges    []CallEdge `json:"edges"`
}

type Span struct {
	TraceID    string            `json:"traceId"`
	SpanID     string            `json:"spanId"`
	ParentID   string            `json:"parentId,omitempty"`
	Service    string            `json:"service"`
	Operation  string            `json:"operation"`
	Method     string            `json:"method"`
	Path       string            `json:"path"`
	StartTime  time.Time         `json:"startTime"`
	Duration   time.Duration   `json:"duration"`
	Tags       map[string]string `json:"tags,omitempty"`
}

type Trace struct {
	TraceID string `json:"traceId"`
	Spans   []Span `json:"spans"`
}

type Rule struct {
	From    string   `json:"from"`
	To      string   `json:"to"`
	Methods []string `json:"methods"`
	Paths   []string `json:"paths,omitempty"`
}

type AuthorizationPolicy struct {
	Name      string   `json:"name"`
	Namespace string   `json:"namespace"`
	Action    string   `json:"action"`
	Rules     []Rule   `json:"rules"`
	Selector  map[string]string `json:"selector,omitempty"`
}

type PolicyConflict struct {
	Type        string   `json:"type"`
	Severity    string   `json:"severity"`
	Description string   `json:"description"`
	PolicyA       string   `json:"policyA"`
	PolicyB       string   `json:"policyB,omitempty"`
	AffectedServices []string `json:"affectedServices"`
}

type SimulationRequest struct {
	Policies []AuthorizationPolicy `json:"policies"`
	Source   string                `json:"source"`
	Dest     string                `json:"dest"`
	Method   string                `json:"method"`
	Path     string                `json:"path"`
}

type SimulationResult struct {
	Allowed bool   `json:"allowed"`
	Reason  string `json:"reason"`
	MatchedPolicy string `json:"matchedPolicy,omitempty"`
}

type ComplianceRule struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
	Severity    string `json:"severity"`
}

type ComplianceResult struct {
	Rule      ComplianceRule `json:"rule"`
	Passed    bool           `json:"passed"`
	Details   string         `json:"details"`
	Violations []string      `json:"violations,omitempty"`
}

type ComplianceReport struct {
	OverallScore int                `json:"overallScore"`
	Results   []ComplianceResult `json:"results"`
}

type PolicyChangeType string

const (
	PolicyChangeAdded   PolicyChangeType = "ADDED"
	PolicyChangeRemoved PolicyChangeType = "REMOVED"
	PolicyChangeModified PolicyChangeType = "MODIFIED"
)

type PolicyChange struct {
	Type      PolicyChangeType  `json:"type"`
	PolicyName string           `json:"policyName"`
	OldPolicy *AuthorizationPolicy `json:"oldPolicy,omitempty"`
	NewPolicy *AuthorizationPolicy `json:"newPolicy,omitempty"`
}

type IncrementalSimulationRequest struct {
	BasePolicies   []AuthorizationPolicy `json:"basePolicies"`
	Changes        []PolicyChange        `json:"changes"`
	TestRequests   []SimulationRequest   `json:"testRequests"`
	OnlyAffected   bool                   `json:"onlyAffected"`
}

type IncrementalSimulationResult struct {
	TotalRequests     int                        `json:"totalRequests"`
	AffectedRequests  int                        `json:"affectedRequests"`
	SkippedRequests   int                        `json:"skippedRequests"`
	Results           []SimulationResult         `json:"results"`
	ChangedResults    []SimulationResult         `json:"changedResults"`
}

type ScenarioCategory string

const (
	ScenarioServiceToService ScenarioCategory = "SERVICE_TO_SERVICE"
	ScenarioDatabaseAccess   ScenarioCategory = "DATABASE_ACCESS"
	ScenarioExternalAPI      ScenarioCategory = "EXTERNAL_API"
	ScenarioAdminAccess      ScenarioCategory = "ADMIN_ACCESS"
	ScenarioPublicAPI        ScenarioCategory = "PUBLIC_API"
	ScenarioSensitiveData    ScenarioCategory = "SENSITIVE_DATA"
	ScenarioMQCommunication  ScenarioCategory = "MQ_COMMUNICATION"
	ScenarioCacheAccess      ScenarioCategory = "CACHE_ACCESS"
)

type ComplianceScenarioTemplate struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Category    ScenarioCategory  `json:"category"`
	Description string            `json:"description"`
	Severity    string            `json:"severity"`
	Conditions  []TemplateCondition `json:"conditions"`
	ExpectedRules []Rule          `json:"expectedRules"`
	Examples    []ScenarioExample `json:"examples"`
}

type TemplateCondition struct {
	Type      string `json:"type"`
	Field     string `json:"field"`
	Operator  string `json:"operator"`
	Value     string `json:"value"`
}

type ScenarioExample struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Valid       bool   `json:"valid"`
	Config      string `json:"config"`
}

type SemanticComplianceRequest struct {
	Policies []AuthorizationPolicy `json:"policies"`
	Graph    *ServiceGraph         `json:"graph,omitempty"`
	Scenarios []string             `json:"scenarios,omitempty"`
}

type SemanticComplianceResult struct {
	ScenarioID       string   `json:"scenarioId"`
	ScenarioName     string   `json:"scenarioName"`
	Category         ScenarioCategory `json:"category"`
	Passed           bool     `json:"passed"`
	Severity         string   `json:"severity"`
	Details          string   `json:"details"`
	MissingRules     []Rule   `json:"missingRules"`
	Recommendations  []string `json:"recommendations"`
	AffectedServices []string `json:"affectedServices"`
}

type SemanticComplianceReport struct {
	TotalScenarios     int                         `json:"totalScenarios"`
	PassedScenarios    int                         `json:"passedScenarios"`
	FailedScenarios    int                         `json:"failedScenarios"`
	OverallScore       int                         `json:"overallScore"`
	Results            []SemanticComplianceResult  `json:"results"`
}

type DeploymentStatus string

const (
	DeploymentPending   DeploymentStatus = "PENDING"
	DeploymentDeploying DeploymentStatus = "DEPLOYING"
	DeploymentSuccess   DeploymentStatus = "SUCCESS"
	DeploymentFailed    DeploymentStatus = "FAILED"
	DeploymentRollingBack DeploymentStatus = "ROLLING_BACK"
	DeploymentRolledBack DeploymentStatus = "ROLLED_BACK"
)

type DeploymentTarget struct {
	Cluster   string `json:"cluster"`
	Namespace string `json:"namespace"`
	Context   string `json:"context,omitempty"`
}

type PolicyDeployment struct {
	ID              string              `json:"id"`
	Name            string              `json:"name"`
	Policies        []AuthorizationPolicy `json:"policies"`
	Target          DeploymentTarget    `json:"target"`
	Status          DeploymentStatus    `json:"status"`
	CreatedAt       time.Time           `json:"createdAt"`
	DeployedAt      *time.Time          `json:"deployedAt,omitempty"`
	Error           string              `json:"error,omitempty"`
	GeneratedYAML   string              `json:"generatedYAML,omitempty"`
	RollbackEnabled bool                `json:"rollbackEnabled"`
}

type DeploymentRequest struct {
	Policies        []AuthorizationPolicy `json:"policies"`
	Target          DeploymentTarget    `json:"target"`
	DryRun          bool                `json:"dryRun"`
	RollbackEnabled bool                `json:"rollbackEnabled"`
}

type DeploymentResult struct {
	Success   bool   `json:"success"`
	Message   string `json:"message"`
	YAML      string `json:"yaml,omitempty"`
	Applied   int    `json:"applied"`
	Failed    int    `json:"failed"`
}

type RollbackRequest struct {
	DeploymentID string `json:"deploymentId"`
}

type EffectivenessMetric struct {
	MetricName    string  `json:"metricName"`
	BeforeValue   float64 `json:"beforeValue"`
	AfterValue    float64 `json:"afterValue"`
	Change        float64 `json:"change"`
	ChangePercent float64 `json:"changePercent"`
	Improved      bool    `json:"improved"`
}

type EffectivenessRequest struct {
	DeploymentID     string                  `json:"deploymentId"`
	BeforeWindow     string                  `json:"beforeWindow"`
	AfterWindow      string                  `json:"afterWindow"`
	TestRequests     []SimulationRequest     `json:"testRequests"`
	BeforePolicies   []AuthorizationPolicy   `json:"beforePolicies"`
	AfterPolicies    []AuthorizationPolicy   `json:"afterPolicies"`
}

type EffectivenessReport struct {
	DeploymentID string             `json:"deploymentId"`
	BeforeWindow string             `json:"beforeWindow"`
	AfterWindow  string             `json:"afterWindow"`
	Metrics      []EffectivenessMetric `json:"metrics"`
	OverallScore float64            `json:"overallScore"`
	Recommendations []string         `json:"recommendations"`
	BeforeResults []SimulationResult `json:"beforeResults"`
	AfterResults  []SimulationResult `json:"afterResults"`
}

type SuccessRateMetric struct {
	ServiceName    string  `json:"serviceName"`
	TotalRequests  int     `json:"totalRequests"`
	AllowedBefore  int     `json:"allowedBefore"`
	AllowedAfter   int     `json:"allowedAfter"`
	RateBefore     float64 `json:"rateBefore"`
	RateAfter      float64 `json:"rateAfter"`
	RateChange     float64 `json:"rateChange"`
}

type PolicyCoverage struct {
	PolicyName     string   `json:"policyName"`
	CoveredCalls   int      `json:"coveredCalls"`
	TotalCalls     int      `json:"totalCalls"`
	CoverageRate   float64  `json:"coverageRate"`
	CoveredEdges   []string `json:"coveredEdges"`
	UncoveredEdges []string `json:"uncoveredEdges"`
}

type CoverageVisualization struct {
	TotalServices    int               `json:"totalServices"`
	TotalEdges       int               `json:"totalEdges"`
	CoveredEdges     int               `json:"coveredEdges"`
	UncoveredEdges   int               `json:"uncoveredEdges"`
	OverallCoverage  float64           `json:"overallCoverage"`
	PolicyCoverages  []PolicyCoverage  `json:"policyCoverages"`
	ServiceGraph     *ServiceGraph     `json:"serviceGraph"`
	CoveredEdgeKeys  []string          `json:"coveredEdgeKeys"`
}

type QuickDeployRequest struct {
	TargetNamespace string `json:"targetNamespace"`
	AutoRollback    bool   `json:"autoRollback"`
	DryRun          bool   `json:"dryRun"`
}
