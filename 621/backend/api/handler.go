package api

import (
	"authz-policy-recommender/backend/pkg/analyzer"
	"authz-policy-recommender/backend/pkg/compliance"
	"authz-policy-recommender/backend/pkg/conflict"
	"authz-policy-recommender/backend/pkg/deployer"
	"authz-policy-recommender/backend/pkg/evaluator"
	"authz-policy-recommender/backend/pkg/generator"
	"authz-policy-recommender/backend/pkg/models"
	"authz-policy-recommender/backend/pkg/simulator"
	"authz-policy-recommender/backend/pkg/visualizer"
	"net/http"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	callAnalyzer          *analyzer.CallAnalyzer
	policyGenerator       *generator.PolicyGenerator
	conflictDetector      *conflict.ConflictDetector
	policySimulator       *simulator.PolicySimulator
	complianceChecker     *compliance.ComplianceChecker
	scenarioChecker       *compliance.ScenarioChecker
	policyDeployer        *deployer.PolicyDeployer
	effectivenessEvaluator *evaluator.PolicyEffectivenessEvaluator
	policyVisualizer      *visualizer.PolicyVisualizer
}

func NewHandler(
	ca *analyzer.CallAnalyzer,
	pg *generator.PolicyGenerator,
	cd *conflict.ConflictDetector,
	ps *simulator.PolicySimulator,
	cc *compliance.ComplianceChecker,
	sc *compliance.ScenarioChecker,
	pd *deployer.PolicyDeployer,
	ee *evaluator.PolicyEffectivenessEvaluator,
	pv *visualizer.PolicyVisualizer,
) *Handler {
	return &Handler{
		callAnalyzer:          ca,
		policyGenerator:       pg,
		conflictDetector:      cd,
		policySimulator:       ps,
		complianceChecker:     cc,
		scenarioChecker:       sc,
		policyDeployer:        pd,
		effectivenessEvaluator: ee,
		policyVisualizer:      pv,
	}
}

func RegisterRoutes(r *gin.Engine, h *Handler) {
	api := r.Group("/api/v1")

	api.GET("/health", h.HealthCheck)

	api.POST("/traces", h.AddTrace)
	api.GET("/service-graph", h.GetServiceGraph)
	api.GET("/call-relations", h.GetCallRelations)
	api.POST("/sampling/config", h.SetSamplingConfig)
	api.GET("/sampling/stats", h.GetSamplingStats)

	api.POST("/policies/generate", h.GeneratePolicies)
	api.POST("/policies/optimize", h.OptimizePolicies)
	api.POST("/policies/istio-yaml", h.GenerateIstioYAML)
	api.POST("/policies/changes", h.DetectPolicyChanges)

	api.POST("/conflicts/detect", h.DetectConflicts)

	api.POST("/simulate", h.Simulate)
	api.POST("/simulate/batch", h.SimulateBatch)
	api.POST("/simulate/incremental", h.SimulateIncremental)
	api.POST("/simulate/baseline", h.SetSimulationBaseline)
	api.POST("/coverage", h.GetCoverageReport)

	api.GET("/compliance/rules", h.GetComplianceRules)
	api.POST("/compliance/check", h.CheckCompliance)
	api.GET("/compliance/scenarios", h.GetComplianceScenarios)
	api.POST("/compliance/semantic", h.CheckSemanticCompliance)

	api.POST("/deployment/deploy", h.DeployPolicies)
	api.POST("/deployment/quick-deploy", h.QuickDeployPolicies)
	api.POST("/deployment/rollback", h.RollbackDeployment)
	api.GET("/deployment/:id", h.GetDeployment)
	api.GET("/deployments", h.ListDeployments)
	api.POST("/deployment/generate-yaml", h.GenerateYAML)

	api.POST("/effectiveness/evaluate", h.EvaluateEffectiveness)
	api.POST("/effectiveness/compare-rates", h.CompareSuccessRates)

	api.POST("/visualization/coverage", h.GetCoverageVisualization)

	api.POST("/sample-data", h.LoadSampleData)
	api.DELETE("/data", h.ClearData)
}

func (h *Handler) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func (h *Handler) AddTrace(c *gin.Context) {
	var trace models.Trace
	if err := c.ShouldBindJSON(&trace); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.callAnalyzer.AddTrace(trace)
	c.JSON(http.StatusCreated, gin.H{"message": "Trace added successfully"})
}

func (h *Handler) GetServiceGraph(c *gin.Context) {
	graph := h.callAnalyzer.GetServiceGraph()
	c.JSON(http.StatusOK, graph)
}

func (h *Handler) GetCallRelations(c *gin.Context) {
	relations := h.callAnalyzer.GetCallRelations()
	c.JSON(http.StatusOK, relations)
}

type GeneratePolicyRequest struct {
	Edges []models.CallEdge `json:"edges"`
}

func (h *Handler) GeneratePolicies(c *gin.Context) {
	var req GeneratePolicyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		edges := h.callAnalyzer.GetCallRelations()
		policies := h.policyGenerator.GeneratePolicies(edges)
		c.JSON(http.StatusOK, policies)
		return
	}

	edges := req.Edges
	if len(edges) == 0 {
		edges = h.callAnalyzer.GetCallRelations()
	}

	policies := h.policyGenerator.GeneratePolicies(edges)
	c.JSON(http.StatusOK, policies)
}

type OptimizePolicyRequest struct {
	Policies []models.AuthorizationPolicy `json:"policies"`
}

func (h *Handler) OptimizePolicies(c *gin.Context) {
	var req OptimizePolicyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	optimized := h.policyGenerator.OptimizePolicies(req.Policies)
	c.JSON(http.StatusOK, optimized)
}

type IstioYAMLRequest struct {
	Policy models.AuthorizationPolicy `json:"policy"`
}

func (h *Handler) GenerateIstioYAML(c *gin.Context) {
	var req IstioYAMLRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	yaml, err := h.policyGenerator.GenerateIstioYAML(req.Policy)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"yaml": yaml})
}

type DetectConflictsRequest struct {
	Policies []models.AuthorizationPolicy `json:"policies"`
}

func (h *Handler) DetectConflicts(c *gin.Context) {
	var req DetectConflictsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	conflicts := h.conflictDetector.DetectConflicts(req.Policies)
	c.JSON(http.StatusOK, conflicts)
}

func (h *Handler) Simulate(c *gin.Context) {
	var req models.SimulationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result := h.policySimulator.Simulate(req)
	c.JSON(http.StatusOK, result)
}

func (h *Handler) SimulateBatch(c *gin.Context) {
	var req simulator.BatchSimulationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result := h.policySimulator.SimulateBatch(req)
	c.JSON(http.StatusOK, result)
}

type CoverageRequest struct {
	Policies []models.AuthorizationPolicy `json:"policies"`
	Calls    []models.CallEdge            `json:"calls"`
}

func (h *Handler) GetCoverageReport(c *gin.Context) {
	var req CoverageRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	calls := req.Calls
	if len(calls) == 0 {
		calls = h.callAnalyzer.GetCallRelations()
	}

	report := h.policySimulator.GenerateCoverageReport(req.Policies, calls)
	c.JSON(http.StatusOK, report)
}

func (h *Handler) GetComplianceRules(c *gin.Context) {
	rules := h.complianceChecker.GetRules()
	c.JSON(http.StatusOK, rules)
}

type ComplianceCheckRequest struct {
	Policies []models.AuthorizationPolicy `json:"policies"`
	Graph    *models.ServiceGraph         `json:"graph,omitempty"`
}

func (h *Handler) CheckCompliance(c *gin.Context) {
	var req ComplianceCheckRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	graph := req.Graph
	if graph == nil {
		graph = h.callAnalyzer.GetServiceGraph()
	}

	report := h.complianceChecker.CheckCompliance(req.Policies, graph)
	c.JSON(http.StatusOK, report)
}

func (h *Handler) LoadSampleData(c *gin.Context) {
	h.callAnalyzer.LoadSampleData()
	graph := h.callAnalyzer.GetServiceGraph()
	c.JSON(http.StatusOK, gin.H{
		"message":     "Sample data loaded successfully",
		"serviceGraph": graph,
	})
}

func (h *Handler) ClearData(c *gin.Context) {
	h.callAnalyzer.Clear()
	c.JSON(http.StatusOK, gin.H{"message": "All data cleared"})
}

type SamplingConfigRequest struct {
	Strategy        string   `json:"strategy"`
	IngressServices []string `json:"ingressServices"`
	EgressServices  []string `json:"egressServices"`
}

func (h *Handler) SetSamplingConfig(c *gin.Context) {
	var req SamplingConfigRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Strategy != "" {
		h.callAnalyzer.SetSamplingStrategy(models.SamplingStrategy(req.Strategy))
	}

	if req.IngressServices != nil || req.EgressServices != nil {
		h.callAnalyzer.SetEdgeServices(req.IngressServices, req.EgressServices)
	}

	c.JSON(http.StatusOK, gin.H{
		"message":         "Sampling configuration updated",
		"strategy":        req.Strategy,
		"ingressServices": req.IngressServices,
		"egressServices":  req.EgressServices,
	})
}

func (h *Handler) GetSamplingStats(c *gin.Context) {
	stats := h.callAnalyzer.GetSamplingStats()
	c.JSON(http.StatusOK, stats)
}

type PolicyChangesRequest struct {
	OldPolicies []models.AuthorizationPolicy `json:"oldPolicies"`
	NewPolicies []models.AuthorizationPolicy `json:"newPolicies"`
}

func (h *Handler) DetectPolicyChanges(c *gin.Context) {
	var req PolicyChangesRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	changes := h.policySimulator.GenerateChangeReport(req.OldPolicies, req.NewPolicies)
	c.JSON(http.StatusOK, gin.H{
		"changes": changes,
		"count":   len(changes),
	})
}

func (h *Handler) SimulateIncremental(c *gin.Context) {
	var req models.IncrementalSimulationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result := h.policySimulator.SimulateIncremental(req)
	c.JSON(http.StatusOK, result)
}

type BaselineRequest struct {
	Policies  []models.AuthorizationPolicy `json:"policies"`
	Requests  []models.SimulationRequest   `json:"requests"`
	ClearFirst bool                         `json:"clearFirst"`
}

func (h *Handler) SetSimulationBaseline(c *gin.Context) {
	var req BaselineRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.ClearFirst {
		h.policySimulator.ClearBaseline()
	}

	h.policySimulator.BuildBaseline(req.Policies, req.Requests)
	c.JSON(http.StatusOK, gin.H{
		"message":          "Baseline built successfully",
		"baselineRequests": len(req.Requests),
	})
}

func (h *Handler) GetComplianceScenarios(c *gin.Context) {
	category := c.Query("category")
	var scenarios []models.ComplianceScenarioTemplate

	if category != "" {
		scenarios = h.scenarioChecker.GetScenariosByCategory(models.ScenarioCategory(category))
	} else {
		scenarios = h.scenarioChecker.GetAllScenarios()
	}

	c.JSON(http.StatusOK, gin.H{
		"scenarios": scenarios,
		"total":     len(scenarios),
	})
}

type SemanticComplianceRequest struct {
	Policies  []models.AuthorizationPolicy `json:"policies"`
	Graph     *models.ServiceGraph         `json:"graph,omitempty"`
	Scenarios []string                     `json:"scenarios,omitempty"`
}

func (h *Handler) CheckSemanticCompliance(c *gin.Context) {
	var req SemanticComplianceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	graph := req.Graph
	if graph == nil {
		graph = h.callAnalyzer.GetServiceGraph()
	}

	report := h.scenarioChecker.CheckSemanticCompliance(models.SemanticComplianceRequest{
		Policies:  req.Policies,
		Graph:     graph,
		Scenarios: req.Scenarios,
	})

	c.JSON(http.StatusOK, report)
}

func (h *Handler) DeployPolicies(c *gin.Context) {
	var req models.DeploymentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result := h.policyDeployer.Deploy(req)
	c.JSON(http.StatusOK, result)
}

func (h *Handler) QuickDeployPolicies(c *gin.Context) {
	var req struct {
		TargetNamespace string `json:"targetNamespace"`
		AutoRollback    bool   `json:"autoRollback"`
		DryRun          bool   `json:"dryRun"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	edges := h.callAnalyzer.GetCallRelations()
	policies := h.policyGenerator.GeneratePolicies(edges)

	result := h.policyDeployer.QuickDeploy(policies, req.TargetNamespace, req.DryRun)
	c.JSON(http.StatusOK, result)
}

func (h *Handler) RollbackDeployment(c *gin.Context) {
	var req struct {
		DeploymentID string `json:"deploymentId"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	err := h.policyDeployer.Rollback(req.DeploymentID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "Rollback successful"})
}

func (h *Handler) GetDeployment(c *gin.Context) {
	deploymentID := c.Param("id")

	deployment, exists := h.policyDeployer.GetDeployment(deploymentID)
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "Deployment not found"})
		return
	}

	c.JSON(http.StatusOK, deployment)
}

func (h *Handler) ListDeployments(c *gin.Context) {
	deployments := h.policyDeployer.ListDeployments()
	c.JSON(http.StatusOK, gin.H{"deployments": deployments})
}

func (h *Handler) GenerateYAML(c *gin.Context) {
	var req struct {
		Policies []models.AuthorizationPolicy `json:"policies"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	yaml := h.policyDeployer.GenerateIstioYAML(req.Policies)
	c.JSON(http.StatusOK, gin.H{"yaml": yaml})
}

func (h *Handler) EvaluateEffectiveness(c *gin.Context) {
	var req models.EffectivenessRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	report := h.effectivenessEvaluator.EvaluateEffectiveness(req)
	c.JSON(http.StatusOK, report)
}

func (h *Handler) CompareSuccessRates(c *gin.Context) {
	var req struct {
		BeforePolicies []models.AuthorizationPolicy `json:"beforePolicies"`
		AfterPolicies  []models.AuthorizationPolicy `json:"afterPolicies"`
		TestRequests   []models.SimulationRequest   `json:"testRequests"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	metrics := h.effectivenessEvaluator.CompareSuccessRates(req.BeforePolicies, req.AfterPolicies, req.TestRequests)
	c.JSON(http.StatusOK, gin.H{"metrics": metrics})
}

func (h *Handler) GetCoverageVisualization(c *gin.Context) {
	var req struct {
		Policies []models.AuthorizationPolicy `json:"policies"`
		Graph    *models.ServiceGraph         `json:"graph,omitempty"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	graph := req.Graph
	if graph == nil {
		g := h.callAnalyzer.GetServiceGraph()
		graph = &g
	}

	visualization := h.policyVisualizer.GetCoverageVisualization(req.Policies, graph)
	c.JSON(http.StatusOK, visualization)
}
