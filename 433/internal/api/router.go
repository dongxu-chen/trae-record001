package api

import (
	"context"
	"net/http"
	"strconv"
	"time"

	"k8s-cost-allocation/internal/cloud"
	"k8s-cost-allocation/internal/config"
	"k8s-cost-allocation/internal/cost"
	"k8s-cost-allocation/internal/k8sclient"
	"k8s-cost-allocation/internal/promclient"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

type CostReportRequest struct {
	DurationHours int `json:"durationHours" binding:"required,min=1,max=720"`
}

type ProjectCostRequest struct {
	DurationHours int    `json:"durationHours" binding:"required,min=1,max=720"`
	ProjectLabel  string `json:"projectLabel" binding:"required"`
}

type LabelCostRequest struct {
	DurationHours int    `json:"durationHours" binding:"required,min=1,max=720"`
	LabelKey      string `json:"labelKey" binding:"required"`
}

type PredictionRequest struct {
	Namespace     string `json:"namespace" binding:"required"`
	DurationHours int    `json:"durationHours" binding:"required,min=168"`
}

type BillingRequest struct {
	StartDate string `json:"startDate" binding:"required"`
	EndDate   string `json:"endDate" binding:"required"`
}

type APIHandler struct {
	cfg          *config.Config
	k8sClient    *k8sclient.Client
	promClient   *promclient.Client
	costCalc     *cost.Calculator
	billingClient *cloud.AWSBillingClient
}

func SetupRouter(cfg *config.Config, k8sClient *k8sclient.Client, promClient *promclient.Client, costCalc *cost.Calculator) *gin.Engine {
	r := gin.Default()

	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
	}))

	handler := &APIHandler{
		cfg:      cfg,
		k8sClient:  k8sClient,
		promClient: promClient,
		costCalc:   costCalc,
	}

	if cfg.Cloud.Provider == "aws" {
		billingClient, err := cloud.NewAWSBillingClient(cfg.Cloud)
		if err == nil {
			handler.billingClient = billingClient
		}
	}

	api := r.Group("/api/v1")
	{
		api.GET("/health", handler.HealthCheck)

		api.GET("/namespaces", handler.GetNamespaces)
		api.GET("/pods", handler.GetPods)
		api.GET("/nodes", handler.GetNodes)

		api.POST("/cost/namespace", handler.GetNamespaceCosts)
		api.POST("/cost/project", handler.GetProjectCosts)
		api.POST("/cost/label", handler.GetLabelCosts)

		api.GET("/cost/idle", handler.GetIdleResources)
		api.GET("/cost/contention", handler.GetResourceContention)
		api.POST("/cost/predict", handler.GetCostPrediction)

		api.GET("/optimizations", handler.GetOptimizations)

		api.GET("/budgets/alerts", handler.GetBudgetAlerts)
		api.GET("/budgets", handler.GetBudgets)
		api.POST("/budgets", handler.SetBudget)

		api.POST("/pricing/compare", handler.ComparePricing)
		api.GET("/pricing/spot-recommendations", handler.GetSpotRecommendations)

		api.POST("/billing/current", handler.GetCurrentBilling)
		api.POST("/billing/forecast", handler.GetBillingForecast)
		api.POST("/billing/services", handler.GetBillingByService)
	}

	return r
}

func (h *APIHandler) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ok",
		"time":   time.Now().UTC(),
	})
}

func (h *APIHandler) GetNamespaces(c *gin.Context) {
	ctx := context.Background()
	namespaces, err := h.k8sClient.GetNamespaces(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, namespaces)
}

func (h *APIHandler) GetPods(c *gin.Context) {
	ctx := context.Background()
	namespace := c.Query("namespace")
	pods, err := h.k8sClient.GetPods(ctx, namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, pods)
}

func (h *APIHandler) GetNodes(c *gin.Context) {
	ctx := context.Background()
	nodes, err := h.k8sClient.GetNodes(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, nodes)
}

func (h *APIHandler) GetNamespaceCosts(c *gin.Context) {
	var req CostReportRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()
	duration := time.Duration(req.DurationHours) * time.Hour

	costs, err := h.costCalc.CalculateNamespaceCosts(ctx, duration)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"durationHours": req.DurationHours,
		"generatedAt":   time.Now().UTC(),
		"data":          costs,
	})
}

func (h *APIHandler) GetProjectCosts(c *gin.Context) {
	var req ProjectCostRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()
	duration := time.Duration(req.DurationHours) * time.Hour

	namespaceCosts, err := h.costCalc.CalculateNamespaceCosts(ctx, duration)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	projectCosts := h.costCalc.CalculateProjectCosts(ctx, namespaceCosts, req.ProjectLabel)

	c.JSON(http.StatusOK, gin.H{
		"durationHours": req.DurationHours,
		"projectLabel":  req.ProjectLabel,
		"generatedAt":   time.Now().UTC(),
		"data":          projectCosts,
	})
}

func (h *APIHandler) GetLabelCosts(c *gin.Context) {
	var req LabelCostRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()
	duration := time.Duration(req.DurationHours) * time.Hour

	namespaceCosts, err := h.costCalc.CalculateNamespaceCosts(ctx, duration)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	labelCosts := h.costCalc.CalculateLabelCosts(ctx, namespaceCosts, req.LabelKey)

	c.JSON(http.StatusOK, gin.H{
		"durationHours": req.DurationHours,
		"labelKey":      req.LabelKey,
		"generatedAt":   time.Now().UTC(),
		"data":          labelCosts,
	})
}

func (h *APIHandler) GetIdleResources(c *gin.Context) {
	ctx := context.Background()
	durationHours, _ := strconv.Atoi(c.DefaultQuery("duration", "24"))
	duration := time.Duration(durationHours) * time.Hour

	namespaceCosts, err := h.costCalc.CalculateNamespaceCosts(ctx, duration)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	idleResources := h.costCalc.DetectIdleResources(ctx, namespaceCosts)

	c.JSON(http.StatusOK, gin.H{
		"durationHours": durationHours,
		"generatedAt":   time.Now().UTC(),
		"data":          idleResources,
	})
}

func (h *APIHandler) GetResourceContention(c *gin.Context) {
	ctx := context.Background()
	durationHours, _ := strconv.Atoi(c.DefaultQuery("duration", "24"))
	duration := time.Duration(durationHours) * time.Hour

	namespaceCosts, err := h.costCalc.CalculateNamespaceCosts(ctx, duration)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	contentions, err := h.costCalc.DetectResourceContention(ctx, duration, namespaceCosts)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"durationHours": durationHours,
		"generatedAt":   time.Now().UTC(),
		"data":          contentions,
	})
}

func (h *APIHandler) GetCostPrediction(c *gin.Context) {
	var req PredictionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()
	duration := time.Duration(req.DurationHours) * time.Hour

	prediction, err := h.costCalc.PredictCosts(ctx, req.Namespace, duration)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, prediction)
}

func (h *APIHandler) GetOptimizations(c *gin.Context) {
	ctx := context.Background()
	durationHours, _ := strconv.Atoi(c.DefaultQuery("duration", "24"))
	duration := time.Duration(durationHours) * time.Hour

	namespaceCosts, err := h.costCalc.CalculateNamespaceCosts(ctx, duration)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	idleResources := h.costCalc.DetectIdleResources(ctx, namespaceCosts)
	contentions, err := h.costCalc.DetectResourceContention(ctx, duration, namespaceCosts)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	suggestions := h.costCalc.GetOptimizationSuggestions(ctx, idleResources, namespaceCosts, contentions)

	c.JSON(http.StatusOK, gin.H{
		"durationHours": durationHours,
		"generatedAt":   time.Now().UTC(),
		"data":          suggestions,
	})
}

func (h *APIHandler) GetCurrentBilling(c *gin.Context) {
	if h.billingClient == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Billing client not configured"})
		return
	}

	var req BillingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	start, err := time.Parse("2006-01-02", req.StartDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid start date format, use YYYY-MM-DD"})
		return
	}

	end, err := time.Parse("2006-01-02", req.EndDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid end date format, use YYYY-MM-DD"})
		return
	}

	ctx := context.Background()
	billing, err := h.billingClient.GetCostAndUsage(ctx, start, end, "DAILY")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, billing)
}

func (h *APIHandler) GetBillingForecast(c *gin.Context) {
	if h.billingClient == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Billing client not configured"})
		return
	}

	var req BillingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	start, err := time.Parse("2006-01-02", req.StartDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid start date format, use YYYY-MM-DD"})
		return
	}

	end, err := time.Parse("2006-01-02", req.EndDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid end date format, use YYYY-MM-DD"})
		return
	}

	ctx := context.Background()
	forecast, err := h.billingClient.GetCostForecast(ctx, start, end)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, forecast)
}

func (h *APIHandler) GetBillingByService(c *gin.Context) {
	if h.billingClient == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": "Billing client not configured"})
		return
	}

	var req BillingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	start, err := time.Parse("2006-01-02", req.StartDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid start date format, use YYYY-MM-DD"})
		return
	}

	end, err := time.Parse("2006-01-02", req.EndDate)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid end date format, use YYYY-MM-DD"})
		return
	}

	ctx := context.Background()
	serviceCosts, err := h.billingClient.GetCostByService(ctx, start, end)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"startDate": req.StartDate,
		"endDate":   req.EndDate,
		"data":      serviceCosts,
	})
}

type SetBudgetRequest struct {
	Namespace string  `json:"namespace" binding:"required"`
	Budget    float64 `json:"budget" binding:"required,min=0"`
}

type PriceCompareRequest struct {
	CPUCores float64 `json:"cpuCores" binding:"required,min=0"`
	MemoryGB float64 `json:"memoryGB" binding:"required,min=0"`
}

func (h *APIHandler) GetBudgetAlerts(c *gin.Context) {
	ctx := context.Background()
	durationHours, _ := strconv.Atoi(c.DefaultQuery("duration", "24"))
	duration := time.Duration(durationHours) * time.Hour

	namespaceCosts, err := h.costCalc.CalculateNamespaceCosts(ctx, duration)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	budgetMgr := h.costCalc.GetBudgetManager()
	alerts := budgetMgr.CheckBudgets(namespaceCosts)

	c.JSON(http.StatusOK, gin.H{
		"generatedAt": time.Now().UTC(),
		"count":       len(alerts),
		"data":        alerts,
	})
}

func (h *APIHandler) GetBudgets(c *gin.Context) {
	budgetMgr := h.costCalc.GetBudgetManager()

	ctx := context.Background()
	namespaces, err := h.k8sClient.GetNamespaces(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	budgets := make(map[string]float64)
	for _, ns := range namespaces {
		budgets[ns.Name] = budgetMgr.GetBudget(ns.Name)
	}

	c.JSON(http.StatusOK, gin.H{
		"defaultBudget": h.cfg.Budgets.DefaultMonthlyBudget,
		"namespaces":    budgets,
	})
}

func (h *APIHandler) SetBudget(c *gin.Context) {
	var req SetBudgetRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.cfg.Budgets.Namespaces[req.Namespace] = req.Budget

	c.JSON(http.StatusOK, gin.H{
		"status":    "success",
		"namespace": req.Namespace,
		"budget":    req.Budget,
	})
}

func (h *APIHandler) ComparePricing(c *gin.Context) {
	var req PriceCompareRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	budgetMgr := h.costCalc.GetBudgetManager()
	comparison := budgetMgr.CalculatePriceComparison(req.CPUCores, req.MemoryGB)

	c.JSON(http.StatusOK, gin.H{
		"cpuCores": req.CPUCores,
		"memoryGB": req.MemoryGB,
		"data":     comparison,
	})
}

func (h *APIHandler) GetSpotRecommendations(c *gin.Context) {
	ctx := context.Background()
	durationHours, _ := strconv.Atoi(c.DefaultQuery("duration", "24"))
	duration := time.Duration(durationHours) * time.Hour

	namespaceCosts, err := h.costCalc.CalculateNamespaceCosts(ctx, duration)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	budgetMgr := h.costCalc.GetBudgetManager()
	recommendations := budgetMgr.GetSpotRecommendations(namespaceCosts)

	totalSavings := 0.0
	eligibleCount := 0
	for _, r := range recommendations {
		if r.Eligible {
			totalSavings += r.MonthlySavings
			eligibleCount++
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"generatedAt":   time.Now().UTC(),
		"totalNamespaces": len(recommendations),
		"eligibleCount": eligibleCount,
		"totalMonthlySavings": totalSavings,
		"data":          recommendations,
	})
}
