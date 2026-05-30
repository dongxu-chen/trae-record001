package api

import (
	"context"
	"net/http"

	"github.com/gin-gonic/gin"
	v1 "k8s.io/api/networking/v1"
	"k8s-network-policy-recommender/pkg/config"
	"k8s-network-policy-recommender/pkg/k8s"
	"k8s-network-policy-recommender/pkg/neo4jclient"
	"k8s-network-policy-recommender/pkg/policy"
)

type Handler struct {
	config           *config.Config
	neo4j            *neo4jclient.Client
	k8sClient        *k8s.Client
	policyGenerator  *policy.Generator
	conflictDetector *policy.ConflictDetector
	policyManager    *policy.PolicyManager
}

func SetupRouter(cfg *config.Config, neo4j *neo4jclient.Client, k8sClient *k8s.Client) *gin.Engine {
	r := gin.Default()

	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	})

	handler := &Handler{
		config:           cfg,
		neo4j:            neo4j,
		k8sClient:        k8sClient,
		policyGenerator:  policy.NewGenerator(cfg.Policy, k8sClient, neo4j),
		conflictDetector: policy.NewConflictDetector(),
		policyManager:    policy.NewPolicyManager(k8sClient, neo4j),
	}

	api := r.Group("/api")
	{
		api.GET("/health", handler.Health)

		topology := api.Group("/topology")
		{
			topology.GET("", handler.GetTopology)
			topology.GET("/namespace/:namespace", handler.GetTopologyByNamespace)
		}

		policies := api.Group("/policies")
		{
			policies.GET("/:namespace", handler.GetPolicies)
			policies.GET("/:namespace/recommend", handler.RecommendPolicies)
			policies.POST("/:namespace", handler.ApplyPolicy)
			policies.DELETE("/:namespace/:name", handler.DeletePolicy)
			policies.POST("/simulate", handler.SimulatePolicy)
			policies.GET("/:namespace/conflicts", handler.DetectConflicts)

			policies.POST("/:namespace/backup", handler.CreateBackup)
			policies.GET("/:namespace/backups", handler.ListBackups)
			policies.GET("/:namespace/backups/:backupID", handler.GetBackup)
			policies.POST("/:namespace/backups/:backupID/rollback", handler.RollbackBackup)
			policies.POST("/:namespace/batch-apply", handler.BatchApplyPolicies)
			policies.POST("/:namespace/evaluate", handler.EvaluateEffect)
			policies.POST("/:namespace/snapshot", handler.TakeSnapshot)
		}

		flows := api.Group("/flows")
		{
			flows.POST("", handler.AddFlow)
			flows.GET("/:namespace", handler.GetFlows)
		}

		k8sApi := api.Group("/k8s")
		{
			k8sApi.GET("/namespaces", handler.GetNamespaces)
			k8sApi.GET("/pods/:namespace", handler.GetPods)
			k8sApi.GET("/services/:namespace", handler.GetServices)
		}
	}

	return r
}

func (h *Handler) Health(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "healthy"})
}

func (h *Handler) GetTopology(c *gin.Context) {
	ctx := context.Background()
	pods, flows, err := h.neo4j.GetTopology(ctx, "")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"pods": pods, "flows": flows})
}

func (h *Handler) GetTopologyByNamespace(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()
	pods, flows, err := h.neo4j.GetTopology(ctx, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"pods": pods, "flows": flows})
}

func (h *Handler) GetPolicies(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()
	policies, err := h.k8sClient.GetNetworkPolicies(ctx, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, policies)
}

func (h *Handler) RecommendPolicies(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()

	recommendations, coverage, err := h.policyGenerator.GeneratePolicies(ctx, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"recommendations": recommendations, "coverage": coverage})
}

type ApplyPolicyRequest struct {
	Policy *v1.NetworkPolicy `json:"policy" binding:"required"`
}

func (h *Handler) ApplyPolicy(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()

	var req ApplyPolicyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	req.Policy.Namespace = namespace

	if err := h.k8sClient.ApplyNetworkPolicy(ctx, namespace, req.Policy); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "applied"})
}

func (h *Handler) DeletePolicy(c *gin.Context) {
	namespace := c.Param("namespace")
	name := c.Param("name")
	ctx := context.Background()

	if err := h.k8sClient.DeleteNetworkPolicy(ctx, namespace, name); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "deleted"})
}

type SimulatePolicyRequest struct {
	Policy    *v1.NetworkPolicy       `json:"policy" binding:"required"`
	Namespace  string                    `json:"namespace"`
}

func (h *Handler) SimulatePolicy(c *gin.Context) {
	ctx := context.Background()

	var req SimulatePolicyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	flows, err := h.neo4j.GetFlowsByNamespace(ctx, req.Namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	result := h.conflictDetector.SimulatePolicy(req.Policy, flows)

	c.JSON(http.StatusOK, result)
}

func (h *Handler) DetectConflicts(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()

	policies, err := h.k8sClient.GetNetworkPolicies(ctx, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	conflicts := h.conflictDetector.DetectConflicts(policies)

	c.JSON(http.StatusOK, gin.H{"conflicts": conflicts, "totalPolicies": len(policies)})
}

func (h *Handler) AddFlow(c *gin.Context) {
	ctx := context.Background()

	var flow neo4jclient.FlowEdge
	if err := c.ShouldBindJSON(&flow); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.neo4j.AddFlow(ctx, flow); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"status": "added"})
}

func (h *Handler) GetFlows(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()

	flows, err := h.neo4j.GetFlowsByNamespace(ctx, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, flows)
}

func (h *Handler) GetNamespaces(c *gin.Context) {
	ctx := context.Background()
	namespaces, err := h.k8sClient.GetNamespaces(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, namespaces)
}

func (h *Handler) GetPods(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()
	pods, err := h.k8sClient.GetPods(ctx, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, pods)
}

func (h *Handler) GetServices(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()
	services, err := h.k8sClient.GetServices(ctx, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, services)
}

type CreateBackupRequest struct {
	Reason string `json:"reason"`
}

func (h *Handler) CreateBackup(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()

	var req CreateBackupRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		req.Reason = "manual"
	}

	backup, err := h.policyManager.CreateBackup(ctx, namespace, req.Reason)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, backup)
}

func (h *Handler) ListBackups(c *gin.Context) {
	namespace := c.Param("namespace")
	backups := h.policyManager.GetBackups(namespace)
	c.JSON(http.StatusOK, gin.H{"backups": backups, "total": len(backups)})
}

func (h *Handler) GetBackup(c *gin.Context) {
	backupID := c.Param("backupID")
	backup, ok := h.policyManager.GetBackup(backupID)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "backup not found"})
		return
	}
	c.JSON(http.StatusOK, backup)
}

func (h *Handler) RollbackBackup(c *gin.Context) {
	namespace := c.Param("namespace")
	backupID := c.Param("backupID")
	ctx := context.Background()

	if err := h.policyManager.Rollback(ctx, backupID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "rolled back", "backupId": backupID, "namespace": namespace})
}

type BatchApplyRequest struct {
	Recommendations []policy.PolicyRecommendation `json:"recommendations" binding:"required"`
}

func (h *Handler) BatchApplyPolicies(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()

	var req BatchApplyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := h.policyManager.BatchApply(ctx, namespace, req.Recommendations)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

type EvaluateEffectRequest struct {
	BackupID    string `json:"backupId"`
	WaitSeconds int    `json:"waitSeconds"`
}

func (h *Handler) EvaluateEffect(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()

	var req EvaluateEffectRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		req.WaitSeconds = 0
	}

	var eval *policy.EffectEvaluation
	var err error

	if req.BackupID != "" {
		eval, err = h.policyManager.EvaluateEffect(ctx, namespace, req.BackupID, req.WaitSeconds)
	} else {
		before, snapErr := h.policyManager.TakeFlowSnapshot(ctx, namespace)
		if snapErr != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": snapErr.Error()})
			return
		}
		eval, err = h.policyManager.EvaluateWithBeforeSnapshot(ctx, namespace, before, req.WaitSeconds)
	}

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, eval)
}

func (h *Handler) TakeSnapshot(c *gin.Context) {
	namespace := c.Param("namespace")
	ctx := context.Background()

	snapshot, err := h.policyManager.TakeFlowSnapshot(ctx, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, snapshot)
}
