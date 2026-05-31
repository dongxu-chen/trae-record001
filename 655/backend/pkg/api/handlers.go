package api

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"

	"servicemesh-gateway/pkg/accesscontrol"
	"servicemesh-gateway/pkg/bluegreen"
	"servicemesh-gateway/pkg/costestimator"
	"servicemesh-gateway/pkg/istio"
	"servicemesh-gateway/pkg/models"
	"servicemesh-gateway/pkg/redis"
)

type Handler struct {
	istioClient          *istio.Client
	trafficStore         *redis.TrafficStore
	blueGreenManager     *bluegreen.BlueGreenManager
	accessControlManager *accesscontrol.AccessControlManager
	costEstimator        *costestimator.CostEstimator
}

func NewHandler(
	istioClient *istio.Client,
	trafficStore *redis.TrafficStore,
	bgm *bluegreen.BlueGreenManager,
	acm *accesscontrol.AccessControlManager,
	ce *costestimator.CostEstimator,
) *Handler {
	return &Handler{
		istioClient:          istioClient,
		trafficStore:         trafficStore,
		blueGreenManager:     bgm,
		accessControlManager: acm,
		costEstimator:        ce,
	}
}

type CreateWeightRoutingRequest struct {
	Name        string                `json:"name" binding:"required"`
	Namespace   string                `json:"namespace" binding:"required"`
	ServiceName string                `json:"serviceName" binding:"required"`
	Subsets     []models.SubsetWeight `json:"subsets" binding:"required"`
}

func (h *Handler) CreateWeightRouting(c *gin.Context) {
	var req CreateWeightRoutingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rule := &models.WeightRouting{
		RoutingRule: models.RoutingRule{
			ID:          uuid.New().String(),
			Name:        req.Name,
			Namespace:   req.Namespace,
			Type:        "weight",
			ServiceName: req.ServiceName,
			Status:      "active",
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		},
		Subsets: req.Subsets,
	}

	if err := h.istioClient.ApplyWeightRouting(rule); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.trafficStore.StoreRoutingRule(rule); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, rule)
}

type CreateHeaderRoutingRequest struct {
	Name         string             `json:"name" binding:"required"`
	Namespace    string             `json:"namespace" binding:"required"`
	ServiceName  string             `json:"serviceName" binding:"required"`
	MatchRules   []models.HeaderMatch `json:"matchRules" binding:"required"`
	TargetSubset string             `json:"targetSubset" binding:"required"`
}

func (h *Handler) CreateHeaderRouting(c *gin.Context) {
	var req CreateHeaderRoutingRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rule := &models.HeaderRouting{
		RoutingRule: models.RoutingRule{
			ID:          uuid.New().String(),
			Name:        req.Name,
			Namespace:   req.Namespace,
			Type:        "header",
			ServiceName: req.ServiceName,
			Status:      "active",
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		},
		MatchRules:   req.MatchRules,
		TargetSubset: req.TargetSubset,
	}

	if err := h.istioClient.ApplyHeaderRouting(rule); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.trafficStore.StoreRoutingRule(rule); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, rule)
}

type CreateTrafficMirrorRequest struct {
	Name          string `json:"name" binding:"required"`
	Namespace     string `json:"namespace" binding:"required"`
	SourceService string `json:"sourceService" binding:"required"`
	MirrorService string `json:"mirrorService" binding:"required"`
	MirrorSubset  string `json:"mirrorSubset,omitempty"`
	MirrorPort    int32  `json:"mirrorPort,omitempty"`
	Percentage    int    `json:"percentage" binding:"required,min=1,max=100"`
}

func (h *Handler) CreateTrafficMirror(c *gin.Context) {
	var req CreateTrafficMirrorRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rule := &models.TrafficMirror{
		RoutingRule: models.RoutingRule{
			ID:          uuid.New().String(),
			Name:        req.Name,
			Namespace:   req.Namespace,
			Type:        "mirror",
			ServiceName: req.SourceService,
			Status:      "active",
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		},
		SourceService: req.SourceService,
		MirrorService: req.MirrorService,
		MirrorSubset:  req.MirrorSubset,
		MirrorPort:    req.MirrorPort,
		Percentage:    req.Percentage,
	}

	if err := h.istioClient.ApplyTrafficMirror(rule); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.trafficStore.StoreRoutingRule(rule); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, rule)
}

type CreateFaultInjectionRequest struct {
	Name        string           `json:"name" binding:"required"`
	Namespace   string           `json:"namespace" binding:"required"`
	ServiceName string           `json:"serviceName" binding:"required"`
	FaultType   string           `json:"faultType" binding:"required,oneof=delay abort"`
	Percentage  int              `json:"percentage" binding:"required,min=1,max=100"`
	Delay       *models.DelaySpec `json:"delay,omitempty"`
	Abort       *models.AbortSpec `json:"abort,omitempty"`
}

func (h *Handler) CreateFaultInjection(c *gin.Context) {
	var req CreateFaultInjectionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rule := &models.FaultInjection{
		RoutingRule: models.RoutingRule{
			ID:          uuid.New().String(),
			Name:        req.Name,
			Namespace:   req.Namespace,
			Type:        "fault",
			ServiceName: req.ServiceName,
			Status:      "active",
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
		},
		FaultType:  req.FaultType,
		Percentage: req.Percentage,
		Delay:      req.Delay,
		Abort:      req.Abort,
	}

	if err := h.istioClient.ApplyFaultInjection(rule); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.trafficStore.StoreRoutingRule(rule); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, rule)
}

func (h *Handler) GetRoutingRules(c *gin.Context) {
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = "default"
	}

	rules, err := h.trafficStore.GetRoutingRules(namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"rules": rules})
}

func (h *Handler) DeleteRoutingRule(c *gin.Context) {
	namespace := c.Param("namespace")
	id := c.Param("id")

	if err := h.trafficStore.DeleteRoutingRule(namespace, id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "rule deleted"})
}

func (h *Handler) GetTopology(c *gin.Context) {
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = "default"
	}

	topology, err := h.trafficStore.GetTopology(namespace)
	if err != nil {
		services, _ := h.trafficStore.GetServiceList(namespace)
		nodes := make([]models.ServiceNode, 0, len(services))
		for i, svc := range services {
			nodes = append(nodes, models.ServiceNode{
				ID:        svc,
				Name:      svc,
				Namespace: namespace,
				Type:      "service",
				X:         float64(100 + i*150),
				Y:         float64(200),
			})
		}
		topology = &models.TrafficTopology{
			Nodes: nodes,
			Edges: []models.ServiceEdge{},
		}
	}

	c.JSON(http.StatusOK, topology)
}

func (h *Handler) GetMetrics(c *gin.Context) {
	namespace := c.Query("namespace")
	serviceName := c.Query("service")
	if namespace == "" {
		namespace = "default"
	}

	startTime := time.Now().Add(-time.Hour * 24)
	endTime := time.Now()

	metrics, err := h.trafficStore.GetMetrics(namespace, serviceName, startTime, endTime)
	if err != nil {
		metrics = []*models.TrafficMetrics{}
	}

	c.JSON(http.StatusOK, gin.H{"metrics": metrics})
}

type GenerateReportRequest struct {
	Name      string    `json:"name" binding:"required"`
	Type      string    `json:"type" binding:"required"`
	StartDate time.Time `json:"startDate" binding:"required"`
	EndDate   time.Time `json:"endDate" binding:"required"`
	Namespace string    `json:"namespace"`
	Services  []string  `json:"services"`
}

func (h *Handler) GenerateReport(c *gin.Context) {
	var req GenerateReportRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Namespace == "" {
		req.Namespace = "default"
	}

	serviceReports := make([]models.ServiceReport, len(req.Services))
	for i, svc := range req.Services {
		serviceReports[i] = models.ServiceReport{
			ServiceName:      svc,
			VersionBreakdown: make(map[string]int64),
		}
	}

	report := &models.TrafficReport{
		ID:          uuid.New().String(),
		Name:        req.Name,
		Type:        req.Type,
		StartDate:   req.StartDate,
		EndDate:     req.EndDate,
		Services:    serviceReports,
		GeneratedAt: time.Now(),
	}

	if err := h.trafficStore.GenerateReport(report); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, report)
}

func (h *Handler) GetReport(c *gin.Context) {
	id := c.Param("id")

	report, err := h.trafficStore.GetReport(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "report not found"})
		return
	}

	c.JSON(http.StatusOK, report)
}

func (h *Handler) GetVirtualServices(c *gin.Context) {
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = "default"
	}

	vsList, err := h.istioClient.ListVirtualServices(namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"virtualServices": vsList})
}

func (h *Handler) GetDestinationRules(c *gin.Context) {
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = "default"
	}

	drList, err := h.istioClient.ListDestinationRules(namespace)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"destinationRules": drList})
}

func (h *Handler) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "healthy"})
}

func (h *Handler) CreateBlueGreenDeployment(c *gin.Context) {
	var req models.BlueGreenDeployment
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	deployment, err := h.blueGreenManager.CreateDeployment(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, deployment)
}

func (h *Handler) ListBlueGreenDeployments(c *gin.Context) {
	namespace := c.Query("namespace")
	deployments := h.blueGreenManager.ListDeployments(namespace)
	c.JSON(http.StatusOK, gin.H{"deployments": deployments})
}

func (h *Handler) GetBlueGreenDeployment(c *gin.Context) {
	id := c.Param("id")
	deployment, exists := h.blueGreenManager.GetDeployment(id)
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "deployment not found"})
		return
	}
	c.JSON(http.StatusOK, deployment)
}

func (h *Handler) StartBlueGreenDeployment(c *gin.Context) {
	id := c.Param("id")
	if err := h.blueGreenManager.StartDeployment(id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "deployment started"})
}

func (h *Handler) PauseBlueGreenDeployment(c *gin.Context) {
	id := c.Param("id")
	if err := h.blueGreenManager.PauseDeployment(id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "deployment paused"})
}

func (h *Handler) RollbackBlueGreenDeployment(c *gin.Context) {
	id := c.Param("id")
	if err := h.blueGreenManager.RollbackDeployment(id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "deployment rolled back"})
}

func (h *Handler) CompleteBlueGreenDeployment(c *gin.Context) {
	id := c.Param("id")
	if err := h.blueGreenManager.CompleteDeployment(id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "deployment completed"})
}

func (h *Handler) CreateAccessControlRule(c *gin.Context) {
	var req models.AccessControlRule
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rule, err := h.accessControlManager.CreateRule(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, rule)
}

func (h *Handler) ListAccessControlRules(c *gin.Context) {
	namespace := c.Query("namespace")
	serviceName := c.Query("service")
	rules := h.accessControlManager.ListRules(namespace, serviceName)
	c.JSON(http.StatusOK, gin.H{"rules": rules})
}

func (h *Handler) GetAccessControlRule(c *gin.Context) {
	id := c.Param("id")
	rule, exists := h.accessControlManager.GetRule(id)
	if !exists {
		c.JSON(http.StatusNotFound, gin.H{"error": "rule not found"})
		return
	}
	c.JSON(http.StatusOK, rule)
}

func (h *Handler) UpdateAccessControlRule(c *gin.Context) {
	id := c.Param("id")
	var updates models.AccessControlRule
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rule, err := h.accessControlManager.UpdateRule(id, &updates)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, rule)
}

func (h *Handler) DeleteAccessControlRule(c *gin.Context) {
	id := c.Param("id")
	if err := h.accessControlManager.DeleteRule(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "rule deleted"})
}

func (h *Handler) CheckAccess(c *gin.Context) {
	type CheckAccessRequest struct {
		RuleID    string            `json:"ruleId" binding:"required"`
		SourceIP    string            `json:"sourceIp"`
		UserID      string            `json:"userId"`
		Headers       map[string]string `json:"headers"`
	}

	var req CheckAccessRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	allowed, reason, err := h.accessControlManager.CheckAccess(c.Request.Context(), req.RuleID, req.SourceIP, req.UserID, req.Headers)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"allowed": allowed, "reason": reason})
}

func (h *Handler) EstimateCost(c *gin.Context) {
	var req models.CostEstimateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := h.costEstimator.Estimate(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) GetCostProviders(c *gin.Context) {
	providers := h.costEstimator.GetSupportedCloudProviders()
	c.JSON(http.StatusOK, gin.H{"providers": providers})
}

func (h *Handler) GetCostRegions(c *gin.Context) {
	provider := c.Query("provider")
	regions := h.costEstimator.GetSupportedRegions(provider)
	c.JSON(http.StatusOK, gin.H{"regions": regions})
}

func (h *Handler) GetCostConfig(c *gin.Context) {
	provider := c.Param("provider")
	config, err := h.costEstimator.GetCostConfig(provider)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, config)
}

func (h *Handler) MonthlyCostReport(c *gin.Context) {
	type MonthlyReportRequest struct {
		CloudProvider  string    `json:"cloudProvider" binding:"required"`
		Region       string    `json:"region" binding:"required"`
		CrossAZRatio float64 `json:"crossAZRatio"`
		DailyTraffic []float64 `json:"dailyTraffic" binding:"required"`
	}

	var req MonthlyReportRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := h.costEstimator.GenerateMonthlyReport(req.CloudProvider, req.Region, req.DailyTraffic, req.CrossAZRatio)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) CompareCloudProviders(c *gin.Context) {
	type CompareRequest struct {
		Regions     []string `json:"regions"`
		TrafficGB   float64  `json:"trafficGB" binding:"required"`
		CrossAZRatio  float64  `json:"crossAZRatio"`
	}

	var req CompareRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	results := h.costEstimator.CompareCloudProviders(req.Regions, req.TrafficGB, req.CrossAZRatio)
	c.JSON(http.StatusOK, gin.H{"results": results})
}
