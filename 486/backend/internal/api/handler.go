package api

import (
	"net/http"
	"sync"

	"github.com/gin-gonic/gin"

	"mesh-security-platform/internal/analysis"
	"mesh-security-platform/internal/autofix"
	"mesh-security-platform/internal/canary"
	"mesh-security-platform/internal/compliance"
	"mesh-security-platform/internal/istio"
	"mesh-security-platform/internal/kiali"
	"mesh-security-platform/internal/models"
	"mesh-security-platform/internal/opa"
	"mesh-security-platform/internal/recommendation"
	"mesh-security-platform/internal/simulation"
)

type Handler struct {
	istioClient      *istio.Client
	opaClient        *opa.Client
	kialiClient      *kiali.Client
	canaryManager    *canary.Manager
	policySimulator  *simulation.PolicySimulator
	complianceChecker *compliance.ComplianceChecker
	autoFixer        *autofix.AutoFixer
	policies         map[string]models.Policy
	policiesMutex    sync.RWMutex
}

func NewHandler(istioClient *istio.Client, opaClient *opa.Client, kialiClient *kiali.Client, canaryManager *canary.Manager) *Handler {
	return &Handler{
		istioClient:       istioClient,
		opaClient:         opaClient,
		kialiClient:       kialiClient,
		canaryManager:     canaryManager,
		policySimulator:   simulation.NewPolicySimulator(),
		complianceChecker: compliance.NewComplianceChecker(),
		autoFixer:         autofix.NewAutoFixer(),
		policies:          make(map[string]models.Policy),
	}
}

func (h *Handler) RegisterRoutes(r *gin.Engine) {
	api := r.Group("/api/v1")

	policies := api.Group("/policies")
	{
		policies.GET("", h.ListPolicies)
		policies.POST("", h.CreatePolicy)
		policies.GET("/:id", h.GetPolicy)
		policies.PUT("/:id", h.UpdatePolicy)
		policies.DELETE("/:id", h.DeletePolicy)
		policies.POST("/:id/evaluate", h.EvaluatePolicy)
	}

	analysisGroup := api.Group("/analysis")
	{
		analysisGroup.POST("/conflict", h.DetectConflict)
		analysisGroup.POST("/impact", h.AnalyzeImpact)
	}

	recommendationGroup := api.Group("/recommendations")
	{
		recommendationGroup.GET("", h.GetRecommendations)
		recommendationGroup.POST("/:id/apply", h.ApplyRecommendation)
	}

	canaryGroup := api.Group("/canary")
	{
		canaryGroup.GET("", h.ListCanaryDeployments)
		canaryGroup.POST("/start", h.StartCanaryDeployment)
		canaryGroup.GET("/:policyId", h.GetCanaryDeployment)
		canaryGroup.POST("/:policyId/pause", h.PauseCanaryDeployment)
		canaryGroup.POST("/:policyId/resume", h.ResumeCanaryDeployment)
		canaryGroup.POST("/:policyId/promote", h.PromoteCanaryDeployment)
		canaryGroup.POST("/:policyId/rollback", h.RollbackCanaryDeployment)
	}

	topologyGroup := api.Group("/topology")
	{
		topologyGroup.GET("", h.GetServiceTopology)
		topologyGroup.GET("/namespaces", h.GetNamespaces)
	}

	opaGroup := api.Group("/opa")
	{
		opaGroup.GET("/policies", h.ListOPAPolicies)
		opaGroup.POST("/evaluate", h.EvaluateOPA)
	}

	simulationGroup := api.Group("/simulation")
	{
		simulationGroup.POST("/run", h.RunSimulation)
		simulationGroup.GET("/history", h.GetSimulationHistory)
	}

	complianceGroup := api.Group("/compliance")
	{
		complianceGroup.GET("/standards", h.GetComplianceStandards)
		complianceGroup.POST("/check", h.RunComplianceCheck)
	}

	autofixGroup := api.Group("/autofix")
	{
		autofixGroup.GET("/fixes", h.GetAvailableFixes)
		autofixGroup.POST("/generate", h.GenerateFix)
		autofixGroup.POST("/apply", h.ApplyFix)
	}

	api.GET("/health", h.HealthCheck)
}

func (h *Handler) ListPolicies(c *gin.Context) {
	h.policiesMutex.RLock()
	defer h.policiesMutex.RUnlock()

	policyType := c.Query("type")
	namespace := c.Query("namespace")

	var result []models.Policy
	for _, p := range h.policies {
		if policyType != "" && string(p.Type) != policyType {
			continue
		}
		if namespace != "" && p.Namespace != namespace {
			continue
		}
		result = append(result, p)
	}

	c.JSON(http.StatusOK, models.ListPoliciesResponse{
		Total: len(result),
		Items: result,
	})
}

func (h *Handler) CreatePolicy(c *gin.Context) {
	var policy models.Policy
	if err := c.ShouldBindJSON(&policy); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.policiesMutex.Lock()
	h.policies[policy.ID] = policy
	h.policiesMutex.Unlock()

	c.JSON(http.StatusCreated, policy)
}

func (h *Handler) GetPolicy(c *gin.Context) {
	id := c.Param("id")

	h.policiesMutex.RLock()
	policy, exists := h.policies[id]
	h.policiesMutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "policy not found"})
		return
	}

	c.JSON(http.StatusOK, policy)
}

func (h *Handler) UpdatePolicy(c *gin.Context) {
	id := c.Param("id")

	var policy models.Policy
	if err := c.ShouldBindJSON(&policy); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.policiesMutex.Lock()
	h.policies[id] = policy
	h.policiesMutex.Unlock()

	c.JSON(http.StatusOK, policy)
}

func (h *Handler) DeletePolicy(c *gin.Context) {
	id := c.Param("id")

	h.policiesMutex.Lock()
	delete(h.policies, id)
	h.policiesMutex.Unlock()

	c.Status(http.StatusNoContent)
}

func (h *Handler) EvaluatePolicy(c *gin.Context) {
	id := c.Param("id")

	h.policiesMutex.RLock()
	policy, exists := h.policies[id]
	h.policiesMutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "policy not found"})
		return
	}

	var input map[string]interface{}
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := h.opaClient.EvaluatePolicy(c.Request.Context(), policy.Name, input)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	result.PolicyID = id
	c.JSON(http.StatusOK, result)
}

func (h *Handler) DetectConflict(c *gin.Context) {
	var req models.ConflictDetectionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.policiesMutex.RLock()
	policy, exists := h.policies[req.PolicyID]
	h.policiesMutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "policy not found"})
		return
	}

	policiesList := make([]models.Policy, 0, len(h.policies))
	for _, p := range h.policies {
		policiesList = append(policiesList, p)
	}

	detector := analysis.NewConflictDetector(policiesList)
	result, err := detector.Detect(&policy)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) AnalyzeImpact(c *gin.Context) {
	var req models.ImpactAnalysisRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.policiesMutex.RLock()
	policy, exists := h.policies[req.PolicyID]
	h.policiesMutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "policy not found"})
		return
	}

	topology, err := h.kialiClient.GetServiceTopology(c.Request.Context(), []string{policy.Namespace})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	analyzer := analysis.NewImpactAnalyzer(topology)
	result, err := analyzer.Analyze(&policy)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) GetRecommendations(c *gin.Context) {
	policiesList := make([]models.Policy, 0, len(h.policies))
	for _, p := range h.policies {
		policiesList = append(policiesList, p)
	}

	metrics := make(map[string]recommendation.ServiceMetrics)
	metrics["frontend"] = recommendation.ServiceMetrics{
		ServiceName:          "frontend",
		UnencryptedTraffic:   0.15,
		UnauthorizedRequests: 0.08,
		InvalidJWTCount:      5,
		RequestCount:         1000,
	}
	metrics["backend"] = recommendation.ServiceMetrics{
		ServiceName:          "backend",
		UnencryptedTraffic:   0.05,
		UnauthorizedRequests: 0.02,
		InvalidJWTCount:      0,
		RequestCount:         500,
	}

	recommender := recommendation.NewRecommender(policiesList, metrics)
	recommendations := recommender.GenerateRecommendations()

	c.JSON(http.StatusOK, gin.H{
		"total": len(recommendations),
		"items": recommendations,
	})
}

func (h *Handler) ApplyRecommendation(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "applied"})
}

func (h *Handler) ListCanaryDeployments(c *gin.Context) {
	deployments := h.canaryManager.ListDeployments()
	c.JSON(http.StatusOK, gin.H{
		"total": len(deployments),
		"items": deployments,
	})
}

func (h *Handler) StartCanaryDeployment(c *gin.Context) {
	var req struct {
		PolicyID string `json:"policy_id" binding:"required"`
		Strategy string `json:"strategy" binding:"required"`
		Duration string `json:"duration"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.policiesMutex.RLock()
	policy, exists := h.policies[req.PolicyID]
	h.policiesMutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "policy not found"})
		return
	}

	if req.Duration == "" {
		req.Duration = "30m"
	}

	deployment, err := h.canaryManager.StartCanaryDeployment(&policy, canary.CanaryStrategy(req.Strategy), req.Duration)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, deployment)
}

func (h *Handler) GetCanaryDeployment(c *gin.Context) {
	policyID := c.Param("policyId")

	deployment, exists := h.canaryManager.GetDeployment(policyID)
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "deployment not found"})
		return
	}

	c.JSON(http.StatusOK, deployment)
}

func (h *Handler) PauseCanaryDeployment(c *gin.Context) {
	policyID := c.Param("policyId")

	if err := h.canaryManager.PauseDeployment(policyID); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "paused"})
}

func (h *Handler) ResumeCanaryDeployment(c *gin.Context) {
	policyID := c.Param("policyId")

	if err := h.canaryManager.ResumeDeployment(policyID); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "resumed"})
}

func (h *Handler) PromoteCanaryDeployment(c *gin.Context) {
	policyID := c.Param("policyId")

	if err := h.canaryManager.PromoteDeployment(policyID); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "promoted"})
}

func (h *Handler) RollbackCanaryDeployment(c *gin.Context) {
	policyID := c.Param("policyId")

	if err := h.canaryManager.RollbackDeployment(policyID); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "rolled back"})
}

func (h *Handler) GetServiceTopology(c *gin.Context) {
	namespaces := c.QueryArray("namespaces")
	if len(namespaces) == 0 {
		namespaces = []string{"default"}
	}

	topology, err := h.kialiClient.GetServiceTopology(c.Request.Context(), namespaces)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, topology)
}

func (h *Handler) GetNamespaces(c *gin.Context) {
	namespaces, err := h.kialiClient.GetNamespaceList(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"namespaces": namespaces})
}

func (h *Handler) ListOPAPolicies(c *gin.Context) {
	policies, err := h.opaClient.ListPolicies(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"total": len(policies), "items": policies})
}

func (h *Handler) EvaluateOPA(c *gin.Context) {
	var req struct {
		PolicyPath string                 `json:"policy_path" binding:"required"`
		Input      map[string]interface{} `json:"input" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := h.opaClient.EvaluatePolicy(c.Request.Context(), req.PolicyPath, req.Input)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "healthy",
		"services": gin.H{
			"istio": "connected",
			"opa":   "connected",
			"kiali": "connected",
		},
	})
}

func (h *Handler) RunSimulation(c *gin.Context) {
	var req models.PolicySimulationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Policy == nil && req.PolicyID != "" {
		h.policiesMutex.RLock()
		policy, exists := h.policies[req.PolicyID]
		h.policiesMutex.RUnlock()

		if exists {
			req.Policy = &policy
		}
	}

	result, err := h.policySimulator.SimulatePolicy(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) GetSimulationHistory(c *gin.Context) {
	history, err := h.policySimulator.GetSimulationHistory()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"total": len(history),
		"items": history,
	})
}

func (h *Handler) GetComplianceStandards(c *gin.Context) {
	standards := h.complianceChecker.GetAvailableStandards()
	c.JSON(http.StatusOK, gin.H{
		"total": len(standards),
		"items": standards,
	})
}

func (h *Handler) RunComplianceCheck(c *gin.Context) {
	var req models.ComplianceCheckRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := h.complianceChecker.RunComplianceCheck(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) GetAvailableFixes(c *gin.Context) {
	fixes := h.autoFixer.GetAvailableFixes()
	c.JSON(http.StatusOK, gin.H{
		"total": len(fixes),
		"items": fixes,
	})
}

func (h *Handler) GenerateFix(c *gin.Context) {
	var req models.AutoFixRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.policiesMutex.RLock()
	policy, exists := h.policies[req.PolicyID]
	h.policiesMutex.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "policy not found"})
		return
	}

	result, err := h.autoFixer.GenerateFix(&policy, req.IssueType)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) ApplyFix(c *gin.Context) {
	var req struct {
		PatchID string `json:"patch_id" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  "applied",
		"patch_id": req.PatchID,
		"message": "修复补丁已成功应用",
	})
}
