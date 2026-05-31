package api

import (
	"fault-injection-platform/internal/model"
	"fault-injection-platform/internal/resilience"
	"fault-injection-platform/internal/rollback"
	"fault-injection-platform/internal/scenario"
	"fault-injection-platform/pkg/logger"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

type Storage interface {
	CreateFault(fault *model.Fault) error
	GetFault(id string) (*model.Fault, error)
	ListFaults() ([]*model.Fault, error)
	UpdateFault(fault *model.Fault) error
	DeleteFault(id string) error
	CreateScenario(scenario *model.FaultScenario) error
	GetScenario(id string) (*model.FaultScenario, error)
	ListScenarios() ([]*model.FaultScenario, error)
	UpdateScenario(scenario *model.FaultScenario) error
	DeleteScenario(id string) error
	CreateExecution(exec *model.ScenarioExecution) error
	GetExecution(id string) (*model.ScenarioExecution, error)
	UpdateExecution(exec *model.ScenarioExecution) error
	ListExecutions(scenarioID string) ([]*model.ScenarioExecution, error)
	SaveMetric(metric *model.MetricData) error
	GetMetrics(faultID string, metricType string) ([]*model.MetricData, error)
}

type IstioClient interface {
	InjectFault(fault *model.Fault) error
	RemoveFault(serviceName string) error
	GetVirtualServices() ([]string, error)
	GetVirtualServiceFault(serviceName string) (map[string]interface{}, error)
	GetServiceTopology() (*model.ServiceTopology, error)
	GetServicesWithDetails() ([]model.ServiceInfo, error)
	GetServiceVersions(serviceName string) ([]string, error)
}

type JaegerClient interface {
	GetServiceMetrics(service string, lookback time.Duration) (*model.ServiceMetrics, error)
	GetServiceMetricsInRange(service string, startTime, endTime time.Time) (*model.ServiceMetrics, error)
	GetAlignedComparison(service string, faultStartTime time.Time, beforeMinutes, afterMinutes int) (*model.ComparisonMetrics, error)
	GetServices() ([]string, error)
}

type Handler struct {
	storage          Storage
	istioClient      IstioClient
	jaegerClient     JaegerClient
	scenarioLibrary  *scenario.Library
	rollbackManager  *rollback.Manager
	resilienceScorer *resilience.Scorer
}

func NewHandler(storage Storage, istioClient IstioClient, jaegerClient JaegerClient) *Handler {
	return &Handler{
		storage:          storage,
		istioClient:      istioClient,
		jaegerClient:     jaegerClient,
		scenarioLibrary:  scenario.NewLibrary(),
		rollbackManager:  rollback.NewManager(),
		resilienceScorer: resilience.NewScorer(),
	}
}

func (h *Handler) RegisterRoutes(r *gin.Engine) {
	api := r.Group("/api/v1")

	faults := api.Group("/faults")
	{
		faults.POST("", h.CreateFault)
		faults.GET("", h.ListFaults)
		faults.GET("/:id", h.GetFault)
		faults.PUT("/:id", h.UpdateFault)
		faults.DELETE("/:id", h.DeleteFault)
		faults.POST("/:id/start", h.StartFault)
		faults.POST("/:id/stop", h.StopFault)
		faults.POST("/:id/rollback/check", h.ManualRollbackCheck)
		faults.GET("/:id/rollback/status", h.GetRollbackStatus)
	}

	scenarios := api.Group("/scenarios")
	{
		scenarios.POST("", h.CreateScenario)
		scenarios.GET("", h.ListScenarios)
		scenarios.GET("/:id", h.GetScenario)
		scenarios.PUT("/:id", h.UpdateScenario)
		scenarios.DELETE("/:id", h.DeleteScenario)
		scenarios.POST("/:id/execute", h.ExecuteScenario)
	}

	presets := api.Group("/presets")
	{
		presets.GET("", h.ListPresetScenarios)
		presets.GET("/category/:category", h.ListPresetsByCategory)
		presets.GET("/search", h.SearchPresets)
		presets.GET("/:id", h.GetPresetScenario)
		presets.POST("/:id/apply", h.ApplyPresetScenario)
	}

	executions := api.Group("/executions")
	{
		executions.GET("", h.ListExecutions)
		executions.GET("/:id", h.GetExecution)
	}

	services := api.Group("/services")
	{
		services.GET("", h.ListServices)
		services.GET("/detailed", h.ListServicesDetailed)
		services.GET("/topology", h.GetServiceTopology)
		services.GET("/:name/metrics", h.GetServiceMetrics)
		services.GET("/:name/comparison", h.GetServiceComparison)
		services.GET("/:name/versions", h.GetServiceVersions)
		services.GET("/:name/faults", h.GetServiceFaults)
	}

	metrics := api.Group("/metrics")
	{
		metrics.GET("/fault/:id", h.GetFaultMetrics)
		metrics.POST("/comparison", h.GetAlignedComparison)
	}

	resilience := api.Group("/resilience")
	{
		resilience.GET("/fault/:id/score", h.GetResilienceScore)
		resilience.POST("/calculate", h.CalculateResilience)
	}

	rollback := api.Group("/rollback")
	{
		rollback.GET("/active", h.ListActiveMonitors)
		rollback.GET("/default-config", h.GetDefaultRollbackConfig)
	}
}

type CreateFaultRequest struct {
	Name           string                `json:"name" binding:"required"`
	Description    string                `json:"description"`
	Type           model.FaultType       `json:"type" binding:"required"`
	TargetService  string                `json:"target_service" binding:"required"`
	TargetPort     int                   `json:"target_port"`
	Percentage     int                   `json:"percentage" binding:"required,min=1,max=100"`
	Duration       int                   `json:"duration"`
	DelayConfig    *model.DelayConfig    `json:"delay_config"`
	AbortConfig    *model.AbortConfig    `json:"abort_config"`
	ErrorConfig    *model.ErrorConfig    `json:"error_config"`
	Scope          *model.FaultScope     `json:"scope"`
	RollbackConfig *model.RollbackConfig `json:"rollback_config"`
}

func (h *Handler) CreateFault(c *gin.Context) {
	var req CreateFaultRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	fault := model.NewFault()
	fault.Name = req.Name
	fault.Description = req.Description
	fault.Type = req.Type
	fault.TargetService = req.TargetService
	fault.TargetPort = req.TargetPort
	fault.Percentage = req.Percentage
	fault.Duration = req.Duration
	fault.DelayConfig = req.DelayConfig
	fault.AbortConfig = req.AbortConfig
	fault.ErrorConfig = req.ErrorConfig
	fault.Scope = req.Scope
	fault.RollbackConfig = req.RollbackConfig
	fault.CreatedAt = time.Now()
	fault.UpdatedAt = time.Now()

	if err := h.storage.CreateFault(fault); err != nil {
		logger.Errorf("Failed to create fault: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create fault"})
		return
	}

	c.JSON(http.StatusCreated, fault)
}

func (h *Handler) ListFaults(c *gin.Context) {
	faults, err := h.storage.ListFaults()
	if err != nil {
		logger.Errorf("Failed to list faults: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to list faults"})
		return
	}
	c.JSON(http.StatusOK, faults)
}

func (h *Handler) GetFault(c *gin.Context) {
	id := c.Param("id")
	fault, err := h.storage.GetFault(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Fault not found"})
		return
	}
	c.JSON(http.StatusOK, fault)
}

func (h *Handler) UpdateFault(c *gin.Context) {
	id := c.Param("id")
	fault, err := h.storage.GetFault(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Fault not found"})
		return
	}

	var req CreateFaultRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	fault.Name = req.Name
	fault.Description = req.Description
	fault.Type = req.Type
	fault.TargetService = req.TargetService
	fault.TargetPort = req.TargetPort
	fault.Percentage = req.Percentage
	fault.Duration = req.Duration
	fault.DelayConfig = req.DelayConfig
	fault.AbortConfig = req.AbortConfig
	fault.ErrorConfig = req.ErrorConfig
	fault.Scope = req.Scope
	fault.RollbackConfig = req.RollbackConfig
	fault.UpdatedAt = time.Now()

	if err := h.storage.UpdateFault(fault); err != nil {
		logger.Errorf("Failed to update fault: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update fault"})
		return
	}

	c.JSON(http.StatusOK, fault)
}

func (h *Handler) DeleteFault(c *gin.Context) {
	id := c.Param("id")
	if err := h.storage.DeleteFault(id); err != nil {
		logger.Errorf("Failed to delete fault: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete fault"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Fault deleted"})
}

func (h *Handler) StartFault(c *gin.Context) {
	id := c.Param("id")
	fault, err := h.storage.GetFault(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Fault not found"})
		return
	}

	if fault.Status == model.FaultStatusRunning {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Fault is already running"})
		return
	}

	if err := h.istioClient.InjectFault(fault); err != nil {
		logger.Errorf("Failed to inject fault: %v", err)
		fault.Status = model.FaultStatusFailed
		fault.UpdatedAt = time.Now()
		h.storage.UpdateFault(fault)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to inject fault into Istio"})
		return
	}

	now := time.Now()
	fault.Status = model.FaultStatusRunning
	fault.StartedAt = &now
	fault.UpdatedAt = now

	if err := h.storage.UpdateFault(fault); err != nil {
		logger.Errorf("Failed to update fault status: %v", err)
	}

	if fault.Duration > 0 {
		go h.scheduleFaultStop(fault)
	}

	c.JSON(http.StatusOK, fault)
}

func (h *Handler) scheduleFaultStop(fault *model.Fault) {
	time.Sleep(time.Duration(fault.Duration) * time.Second)
	h.istioClient.RemoveFault(fault.TargetService)
	fault.Status = model.FaultStatusCompleted
	now := time.Now()
	fault.EndedAt = &now
	fault.UpdatedAt = now
	h.storage.UpdateFault(fault)
}

func (h *Handler) StopFault(c *gin.Context) {
	id := c.Param("id")
	fault, err := h.storage.GetFault(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Fault not found"})
		return
	}

	if fault.Status != model.FaultStatusRunning {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Fault is not running"})
		return
	}

	if err := h.istioClient.RemoveFault(fault.TargetService); err != nil {
		logger.Errorf("Failed to remove fault: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to remove fault from Istio"})
		return
	}

	now := time.Now()
	fault.Status = model.FaultStatusCompleted
	fault.EndedAt = &now
	fault.UpdatedAt = now

	if err := h.storage.UpdateFault(fault); err != nil {
		logger.Errorf("Failed to update fault status: %v", err)
	}

	c.JSON(http.StatusOK, fault)
}

type CreateScenarioRequest struct {
	Name        string              `json:"name" binding:"required"`
	Description string              `json:"description"`
	FaultIDs    []string            `json:"fault_ids"`
	Steps       []model.ScenarioStep `json:"steps"`
}

func (h *Handler) CreateScenario(c *gin.Context) {
	var req CreateScenarioRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	scenario := model.NewFaultScenario()
	scenario.Name = req.Name
	scenario.Description = req.Description
	scenario.FaultIDs = req.FaultIDs
	scenario.Steps = req.Steps
	scenario.CreatedAt = time.Now()
	scenario.UpdatedAt = time.Now()

	for i := range scenario.Steps {
		scenario.Steps[i].StepID = uuid.New().String()
	}

	if err := h.storage.CreateScenario(scenario); err != nil {
		logger.Errorf("Failed to create scenario: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create scenario"})
		return
	}

	c.JSON(http.StatusCreated, scenario)
}

func (h *Handler) ListScenarios(c *gin.Context) {
	scenarios, err := h.storage.ListScenarios()
	if err != nil {
		logger.Errorf("Failed to list scenarios: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to list scenarios"})
		return
	}
	c.JSON(http.StatusOK, scenarios)
}

func (h *Handler) GetScenario(c *gin.Context) {
	id := c.Param("id")
	scenario, err := h.storage.GetScenario(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Scenario not found"})
		return
	}
	c.JSON(http.StatusOK, scenario)
}

func (h *Handler) UpdateScenario(c *gin.Context) {
	id := c.Param("id")
	scenario, err := h.storage.GetScenario(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Scenario not found"})
		return
	}

	var req CreateScenarioRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	scenario.Name = req.Name
	scenario.Description = req.Description
	scenario.FaultIDs = req.FaultIDs
	scenario.Steps = req.Steps
	scenario.UpdatedAt = time.Now()

	for i := range scenario.Steps {
		if scenario.Steps[i].StepID == "" {
			scenario.Steps[i].StepID = uuid.New().String()
		}
	}

	if err := h.storage.UpdateScenario(scenario); err != nil {
		logger.Errorf("Failed to update scenario: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to update scenario"})
		return
	}

	c.JSON(http.StatusOK, scenario)
}

func (h *Handler) DeleteScenario(c *gin.Context) {
	id := c.Param("id")
	if err := h.storage.DeleteScenario(id); err != nil {
		logger.Errorf("Failed to delete scenario: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to delete scenario"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Scenario deleted"})
}

func (h *Handler) ExecuteScenario(c *gin.Context) {
	id := c.Param("id")
	scenario, err := h.storage.GetScenario(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Scenario not found"})
		return
	}

	exec := model.NewScenarioExecution(id, len(scenario.Steps))
	exec.CreatedAt = time.Now()

	if err := h.storage.CreateExecution(exec); err != nil {
		logger.Errorf("Failed to create execution: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create execution"})
		return
	}

	go h.runScenario(scenario, exec)

	c.JSON(http.StatusOK, exec)
}

func (h *Handler) runScenario(scenario *model.FaultScenario, exec *model.ScenarioExecution) {
	now := time.Now()
	exec.Status = model.FaultStatusRunning
	exec.StartedAt = &now
	h.storage.UpdateExecution(exec)

	for i, step := range scenario.Steps {
		exec.CurrentStep = i + 1
		h.storage.UpdateExecution(exec)

		if step.DelayBefore > 0 {
			time.Sleep(time.Duration(step.DelayBefore) * time.Second)
		}

		fault, err := h.storage.GetFault(step.FaultID)
		if err != nil {
			logger.Errorf("Failed to get fault %s: %v", step.FaultID, err)
			continue
		}

		if err := h.istioClient.InjectFault(fault); err != nil {
			logger.Errorf("Failed to inject fault %s: %v", step.FaultID, err)
			continue
		}

		fault.Status = model.FaultStatusRunning
		fault.StartedAt = &now
		fault.UpdatedAt = now
		h.storage.UpdateFault(fault)

		if step.Duration > 0 {
			time.Sleep(time.Duration(step.Duration) * time.Second)
			h.istioClient.RemoveFault(fault.TargetService)
			endTime := time.Now()
			fault.Status = model.FaultStatusCompleted
			fault.EndedAt = &endTime
			fault.UpdatedAt = endTime
			h.storage.UpdateFault(fault)
		}
	}

	endTime := time.Now()
	exec.Status = model.FaultStatusCompleted
	exec.EndedAt = &endTime
	h.storage.UpdateExecution(exec)
}

func (h *Handler) ListExecutions(c *gin.Context) {
	scenarioID := c.Query("scenario_id")
	execs, err := h.storage.ListExecutions(scenarioID)
	if err != nil {
		logger.Errorf("Failed to list executions: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to list executions"})
		return
	}
	c.JSON(http.StatusOK, execs)
}

func (h *Handler) GetExecution(c *gin.Context) {
	id := c.Param("id")
	exec, err := h.storage.GetExecution(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Execution not found"})
		return
	}
	c.JSON(http.StatusOK, exec)
}

func (h *Handler) ListServices(c *gin.Context) {
	services, err := h.istioClient.GetVirtualServices()
	if err != nil {
		logger.Warnf("Failed to get services from Istio: %v", err)
		services, err = h.jaegerClient.GetServices()
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to list services"})
			return
		}
	}
	c.JSON(http.StatusOK, services)
}

func (h *Handler) GetServiceMetrics(c *gin.Context) {
	name := c.Param("name")
	lookback := 5 * time.Minute
	if lookbackStr := c.Query("lookback"); lookbackStr != "" {
		if d, err := time.ParseDuration(lookbackStr); err == nil {
			lookback = d
		}
	}

	metrics, err := h.jaegerClient.GetServiceMetrics(name, lookback)
	if err != nil {
		logger.Errorf("Failed to get service metrics: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get service metrics"})
		return
	}
	c.JSON(http.StatusOK, metrics)
}

func (h *Handler) GetServiceFaults(c *gin.Context) {
	name := c.Param("name")
	faults, err := h.istioClient.GetVirtualServiceFault(name)
	if err != nil {
		logger.Errorf("Failed to get service faults: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get service faults"})
		return
	}
	c.JSON(http.StatusOK, faults)
}

func (h *Handler) GetFaultMetrics(c *gin.Context) {
	id := c.Param("id")
	metricType := c.Query("type")
	metrics, err := h.storage.GetMetrics(id, metricType)
	if err != nil {
		logger.Errorf("Failed to get fault metrics: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get fault metrics"})
		return
	}
	c.JSON(http.StatusOK, metrics)
}

func (h *Handler) ListServicesDetailed(c *gin.Context) {
	services, err := h.istioClient.GetServicesWithDetails()
	if err != nil {
		logger.Errorf("Failed to get detailed services: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get detailed services"})
		return
	}
	c.JSON(http.StatusOK, services)
}

func (h *Handler) GetServiceTopology(c *gin.Context) {
	topology, err := h.istioClient.GetServiceTopology()
	if err != nil {
		logger.Errorf("Failed to get service topology: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get service topology"})
		return
	}
	c.JSON(http.StatusOK, topology)
}

func (h *Handler) GetServiceVersions(c *gin.Context) {
	name := c.Param("name")
	versions, err := h.istioClient.GetServiceVersions(name)
	if err != nil {
		logger.Errorf("Failed to get service versions: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get service versions"})
		return
	}
	c.JSON(http.StatusOK, versions)
}

func (h *Handler) GetServiceComparison(c *gin.Context) {
	name := c.Param("name")
	faultID := c.Query("fault_id")

	var faultStartTime time.Time
	beforeWindow := 5
	afterWindow := 5

	if faultID != "" {
		fault, err := h.storage.GetFault(faultID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Fault not found"})
			return
		}
		if fault.StartedAt == nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Fault has not been started"})
			return
		}
		faultStartTime = *fault.StartedAt
	} else {
		faultStartTimeStr := c.Query("fault_start_time")
		if faultStartTimeStr == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Either fault_id or fault_start_time is required"})
			return
		}
		var err error
		faultStartTime, err = time.Parse(time.RFC3339, faultStartTimeStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid fault_start_time format, use RFC3339"})
			return
		}
	}

	if bw := c.Query("before_window"); bw != "" {
		if val, err := parseInt(bw); err == nil {
			beforeWindow = val
		}
	}
	if aw := c.Query("after_window"); aw != "" {
		if val, err := parseInt(aw); err == nil {
			afterWindow = val
		}
	}

	comparison, err := h.jaegerClient.GetAlignedComparison(name, faultStartTime, beforeWindow, afterWindow)
	if err != nil {
		logger.Errorf("Failed to get aligned comparison: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get comparison metrics"})
		return
	}
	c.JSON(http.StatusOK, comparison)
}

type ComparisonRequest struct {
	ServiceName    string    `json:"service_name" binding:"required"`
	FaultID        string    `json:"fault_id"`
	FaultStartTime time.Time `json:"fault_start_time"`
	BeforeWindow   int       `json:"before_window_minutes"`
	AfterWindow    int       `json:"after_window_minutes"`
}

func (h *Handler) GetAlignedComparison(c *gin.Context) {
	var req ComparisonRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	var faultStartTime time.Time
	beforeWindow := req.BeforeWindow
	afterWindow := req.AfterWindow

	if beforeWindow == 0 {
		beforeWindow = 5
	}
	if afterWindow == 0 {
		afterWindow = 5
	}

	if req.FaultID != "" {
		fault, err := h.storage.GetFault(req.FaultID)
		if err != nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Fault not found"})
			return
		}
		if fault.StartedAt == nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "Fault has not been started"})
			return
		}
		faultStartTime = *fault.StartedAt
	} else if !req.FaultStartTime.IsZero() {
		faultStartTime = req.FaultStartTime
	} else {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Either fault_id or fault_start_time is required"})
		return
	}

	comparison, err := h.jaegerClient.GetAlignedComparison(req.ServiceName, faultStartTime, beforeWindow, afterWindow)
	if err != nil {
		logger.Errorf("Failed to get aligned comparison: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get comparison metrics"})
		return
	}
	c.JSON(http.StatusOK, comparison)
}

func parseInt(s string) (int, error) {
	var result int
	_, err := fmt.Sscanf(s, "%d", &result)
	return result, err
}

func (h *Handler) ListPresetScenarios(c *gin.Context) {
	presets := h.scenarioLibrary.ListAll()
	c.JSON(http.StatusOK, presets)
}

func (h *Handler) ListPresetsByCategory(c *gin.Context) {
	category := model.PresetScenarioCategory(c.Param("category"))
	presets := h.scenarioLibrary.ListByCategory(category)
	c.JSON(http.StatusOK, presets)
}

func (h *Handler) SearchPresets(c *gin.Context) {
	keyword := c.Query("q")
	presets := h.scenarioLibrary.Search(keyword)
	c.JSON(http.StatusOK, presets)
}

func (h *Handler) GetPresetScenario(c *gin.Context) {
	id := c.Param("id")
	preset := h.scenarioLibrary.GetByID(id)
	if preset == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Preset scenario not found"})
		return
	}
	c.JSON(http.StatusOK, preset)
}

type ApplyPresetRequest struct {
	TargetService string `json:"target_service" binding:"required"`
	TargetPort    int    `json:"target_port"`
	CustomName    string `json:"custom_name"`
}

func (h *Handler) ApplyPresetScenario(c *gin.Context) {
	id := c.Param("id")
	preset := h.scenarioLibrary.GetByID(id)
	if preset == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Preset scenario not found"})
		return
	}

	var req ApplyPresetRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	fault := model.NewFault()
	fault.Name = preset.Name
	if req.CustomName != "" {
		fault.Name = req.CustomName
	}
	fault.Description = preset.Description
	fault.Type = preset.FaultConfig.Type
	fault.TargetService = req.TargetService
	fault.TargetPort = req.TargetPort
	fault.Percentage = preset.FaultConfig.Percentage
	fault.Duration = preset.FaultConfig.Duration
	fault.DelayConfig = preset.FaultConfig.DelayConfig
	fault.AbortConfig = preset.FaultConfig.AbortConfig
	fault.ErrorConfig = preset.FaultConfig.ErrorConfig
	fault.RollbackConfig = rollback.GetDefaultRollbackConfig()
	fault.CreatedAt = time.Now()
	fault.UpdatedAt = time.Now()

	if err := h.storage.CreateFault(fault); err != nil {
		logger.Errorf("Failed to create fault from preset: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create fault"})
		return
	}

	c.JSON(http.StatusCreated, fault)
}

func (h *Handler) ManualRollbackCheck(c *gin.Context) {
	id := c.Param("id")
	fault, err := h.storage.GetFault(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Fault not found"})
		return
	}

	if fault.Status != model.FaultStatusRunning {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Fault is not running"})
		return
	}

	config := fault.RollbackConfig
	if config == nil {
		config = rollback.GetDefaultRollbackConfig()
	}

	monitor, _ := h.rollbackManager.StartMonitoring(
		id,
		fault.TargetService,
		config,
		h.jaegerClient,
		h.istioClient,
	)

	event := monitor.ManualCheck()
	if event != nil {
		c.JSON(http.StatusOK, gin.H{
			"rolled_back": true,
			"event":       event,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"rolled_back": false,
		"message":     "Metrics within thresholds",
	})
}

func (h *Handler) GetRollbackStatus(c *gin.Context) {
	id := c.Param("id")
	status, exists := h.rollbackManager.GetMonitorStatus(id)
	if !exists {
		c.JSON(http.StatusOK, gin.H{
			"monitoring": false,
			"status":     "not_monitoring",
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"monitoring": true,
		"status":     status,
	})
}

func (h *Handler) ListActiveMonitors(c *gin.Context) {
	monitors := h.rollbackManager.ListActiveMonitors()
	c.JSON(http.StatusOK, gin.H{
		"active_monitors": monitors,
		"count":           len(monitors),
	})
}

func (h *Handler) GetDefaultRollbackConfig(c *gin.Context) {
	config := rollback.GetDefaultRollbackConfig()
	c.JSON(http.StatusOK, config)
}

type CalculateResilienceRequest struct {
	ServiceName   string `json:"service_name" binding:"required"`
	FaultID       string `json:"fault_id" binding:"required"`
	BeforeWindow  int    `json:"before_window_minutes"`
	AfterWindow   int    `json:"after_window_minutes"`
}

func (h *Handler) GetResilienceScore(c *gin.Context) {
	faultID := c.Param("id")
	fault, err := h.storage.GetFault(faultID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Fault not found"})
		return
	}

	if fault.StartedAt == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Fault has not been started"})
		return
	}

	beforeWindow := 5
	afterWindow := 5
	if bw := c.Query("before_window"); bw != "" {
		if val, err := parseInt(bw); err == nil {
			beforeWindow = val
		}
	}
	if aw := c.Query("after_window"); aw != "" {
		if val, err := parseInt(aw); err == nil {
			afterWindow = val
		}
	}

	comparison, err := h.jaegerClient.GetAlignedComparison(
		fault.TargetService,
		*fault.StartedAt,
		beforeWindow,
		afterWindow,
	)
	if err != nil {
		logger.Errorf("Failed to get comparison for resilience score: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get comparison metrics"})
		return
	}

	recoveryTrend := h.resilienceScorer.GenerateRecoveryTrend(comparison.Before, comparison, 30)

	var faultDuration time.Duration
	if fault.EndedAt != nil {
		faultDuration = fault.EndedAt.Sub(*fault.StartedAt)
	} else {
		faultDuration = time.Since(*fault.StartedAt)
	}

	report := h.resilienceScorer.CalculateScore(
		faultID,
		fault.TargetService,
		comparison.Before,
		comparison.After,
		comparison.After,
		recoveryTrend,
		faultDuration,
	)

	c.JSON(http.StatusOK, report)
}

func (h *Handler) CalculateResilience(c *gin.Context) {
	var req CalculateResilienceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	fault, err := h.storage.GetFault(req.FaultID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Fault not found"})
		return
	}

	if fault.StartedAt == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Fault has not been started"})
		return
	}

	beforeWindow := req.BeforeWindow
	afterWindow := req.AfterWindow
	if beforeWindow == 0 {
		beforeWindow = 5
	}
	if afterWindow == 0 {
		afterWindow = 5
	}

	comparison, err := h.jaegerClient.GetAlignedComparison(
		req.ServiceName,
		*fault.StartedAt,
		beforeWindow,
		afterWindow,
	)
	if err != nil {
		logger.Errorf("Failed to get comparison for resilience score: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get comparison metrics"})
		return
	}

	recoveryTrend := h.resilienceScorer.GenerateRecoveryTrend(comparison.Before, comparison, 30)

	var faultDuration time.Duration
	if fault.EndedAt != nil {
		faultDuration = fault.EndedAt.Sub(*fault.StartedAt)
	} else {
		faultDuration = time.Since(*fault.StartedAt)
	}

	report := h.resilienceScorer.CalculateScore(
		req.FaultID,
		req.ServiceName,
		comparison.Before,
		comparison.After,
		comparison.After,
		recoveryTrend,
		faultDuration,
	)

	c.JSON(http.StatusOK, report)
}
