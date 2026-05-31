package api

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"sync"
	"time"

	"clickhouse-rate-limiter/clickhouse"
	"clickhouse-rate-limiter/config"
	"clickhouse-rate-limiter/drill"
	"clickhouse-rate-limiter/limiter"
	"clickhouse-rate-limiter/priority"
	"clickhouse-rate-limiter/resourcegroup"

	"github.com/google/uuid"
	"github.com/gorilla/mux"
)

type Handler struct {
	chClient             *clickhouse.Client
	rateLimiter          *limiter.RateLimiter
	priorityQueue        *priority.PriorityQueue
	config               *config.Config
	analyzer             *clickhouse.QueryAnalyzer
	resourceGroupManager *resourcegroup.ResourceGroupManager
	queryHistory         []*QueryRecord
	historyMu            sync.RWMutex
}

type QueryRecord struct {
	ID            string
	UserID        string
	Query         string
	Priority      string
	ResourceGroup string
	Status        string
	ScanRows      int64
	MemoryUsed    int64
	Duration      time.Duration
	Error         string
	CreatedAt     time.Time
}

type QueryRequest struct {
	UserID        string `json:"user_id"`
	Query         string `json:"query"`
	Priority      string `json:"priority"`
	ResourceGroup string `json:"resource_group"`
}

type QueryResponse struct {
	RequestID     string                 `json:"request_id"`
	Status        string                 `json:"status"`
	Data          []map[string]interface{} `json:"data,omitempty"`
	Columns       []string               `json:"columns,omitempty"`
	ScanRows      int64                  `json:"scan_rows,omitempty"`
	MemoryUsed    int64                  `json:"memory_used,omitempty"`
	Duration      string                 `json:"duration,omitempty"`
	Error         string                 `json:"error,omitempty"`
	Complexity    *clickhouse.QueryComplexity `json:"complexity,omitempty"`
	ResourceGroup string                 `json:"resource_group,omitempty"`
}

type StatusResponse struct {
	CircuitBreaker        string                   `json:"circuit_breaker"`
	CircuitBreakerDetail  map[string]interface{}   `json:"circuit_breaker_detail,omitempty"`
	QueueMetrics          map[string]interface{}   `json:"queue_metrics"`
	QueueOrder            []map[string]interface{} `json:"queue_order,omitempty"`
	QueryCount            int                      `json:"query_count"`
	ResourceGroups        []map[string]interface{} `json:"resource_groups,omitempty"`
}

func NewHandler(chClient *clickhouse.Client, rateLimiter *limiter.RateLimiter,
	priorityQueue *priority.PriorityQueue, cfg *config.Config) *Handler {

	h := &Handler{
		chClient:             chClient,
		rateLimiter:          rateLimiter,
		priorityQueue:        priorityQueue,
		config:               cfg,
		analyzer:             clickhouse.NewQueryAnalyzer(chClient),
		resourceGroupManager: resourcegroup.NewResourceGroupManager(cfg.Limiter, cfg.ResourceGroups),
		queryHistory:         make([]*QueryRecord, 0),
	}

	go h.processQueue()

	return h
}

func (h *Handler) Router() http.Handler {
	r := mux.NewRouter()

	r.Use(corsMiddleware)

	r.HandleFunc("/api/query", h.handleQuery).Methods("POST", "OPTIONS")
	r.HandleFunc("/api/preempt", h.handlePreempt).Methods("POST", "OPTIONS")
	r.HandleFunc("/api/status", h.handleStatus).Methods("GET")
	r.HandleFunc("/api/history", h.handleHistory).Methods("GET")
	r.HandleFunc("/api/analyze", h.handleAnalyze).Methods("POST")
	r.HandleFunc("/api/resource-groups", h.handleResourceGroups).Methods("GET")
	r.HandleFunc("/api/resource-groups", h.handleAddResourceGroup).Methods("POST", "OPTIONS")
	r.HandleFunc("/api/resource-groups/{name}", h.handleDeleteResourceGroup).Methods("DELETE", "OPTIONS")
	r.HandleFunc("/api/drill/start", h.handleDrillStart).Methods("POST", "OPTIONS")
	r.HandleFunc("/api/drill/stop", h.handleDrillStop).Methods("POST", "OPTIONS")
	r.HandleFunc("/api/drill/status", h.handleDrillStatus).Methods("GET")
	r.HandleFunc("/api/drill/report", h.handleDrillReport).Methods("GET")
	r.HandleFunc("/api/drill/config", h.handleDrillConfig).Methods("GET")
	r.HandleFunc("/health", h.handleHealth).Methods("GET")

	return r
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func (h *Handler) handleQuery(w http.ResponseWriter, r *http.Request) {
	var req QueryRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	resp := h.ExecuteQueryDirect(r.Context(), req)
	json.NewEncoder(w).Encode(resp)
}

func (h *Handler) ExecuteQueryDirect(ctx context.Context, req QueryRequest) (*QueryResponse, error) {
	if req.UserID == "" {
		req.UserID = "anonymous"
	}
	if req.ResourceGroup == "" {
		req.ResourceGroup = "default"
	}

	analyzeCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	complexity := h.analyzer.AnalyzeQuery(analyzeCtx, req.Query)

	rg := h.resourceGroupManager.GetGroup(req.ResourceGroup)

	limitStatus := rg.Allow(req.UserID, complexity.EstimatedRows, complexity.EstimatedMemory)
	if !limitStatus.Allowed {
		rg.IncrementRejected()
		return &QueryResponse{
			Status:        "rejected",
			Error:         limitStatus.Reason,
			Complexity:    complexity,
			ResourceGroup: req.ResourceGroup,
		}, nil
	}

	rg.IncrementQueued()

	requestID := uuid.New().String()
	prio := priority.ParsePriority(strings.ToLower(req.Priority))

	queryReq := &priority.QueryRequest{
		ID:         requestID,
		UserID:     req.UserID,
		Query:      req.Query,
		Priority:   prio,
		Complexity: complexity.ComplexityScore,
	}

	if err := h.priorityQueue.Submit(queryReq); err != nil {
		rg.RecordFailure()
		rg.DecrementQueued()
		return &QueryResponse{
			RequestID:     requestID,
			Status:        "rejected",
			Error:         err.Error(),
			ResourceGroup: req.ResourceGroup,
		}, nil
	}

	rg.DecrementQueued()
	rg.IncrementActive()
	defer rg.DecrementActive()

	select {
	case result := <-queryReq.Result:
		record := &QueryRecord{
			ID:            requestID,
			UserID:        req.UserID,
			Query:         req.Query,
			Priority:      req.Priority,
			Status:        result.Status,
			Duration:      result.Duration,
			CreatedAt:     time.Now(),
			ResourceGroup: req.ResourceGroup,
		}

		if result.Error != nil {
			record.Error = result.Error.Error()
			rg.RecordFailure()
		} else {
			rg.RecordSuccess()
		}

		h.addHistory(record)

		resp := &QueryResponse{
			RequestID:     requestID,
			Status:        result.Status,
			Error:         record.Error,
			Duration:      result.Duration.String(),
			Complexity:    complexity,
			ResourceGroup: req.ResourceGroup,
		}

		if data, ok := result.Data.(*clickhouse.QueryResult); ok {
			resp.Data = data.Data
			resp.Columns = data.Columns
			resp.ScanRows = data.ScanRows
			resp.MemoryUsed = data.MemoryUsed
			record.ScanRows = data.ScanRows
			record.MemoryUsed = data.MemoryUsed
		}

		return resp, nil

	case <-time.After(h.config.Limiter.QueryTimeout):
		rg.RecordFailure()
		h.addHistory(&QueryRecord{
			ID:            requestID,
			UserID:        req.UserID,
			Query:         req.Query,
			Priority:      req.Priority,
			Status:        "timeout",
			Error:         "query timeout",
			CreatedAt:     time.Now(),
			ResourceGroup: req.ResourceGroup,
		})

		return &QueryResponse{
			RequestID:     requestID,
			Status:        "timeout",
			Error:         "query execution timeout",
			Complexity:    complexity,
			ResourceGroup: req.ResourceGroup,
		}, nil
	}
}

func (h *Handler) processQueue() {
	for {
		req, ok := h.priorityQueue.Next()
		if !ok {
			return
		}

		startTime := time.Now()
		result := h.chClient.ExecuteQuery(context.Background(), req.Query, req.UserID)
		
		duration := time.Since(startTime)

		resp := &priority.QueryResponse{
			Status:   "completed",
			Duration: duration,
		}

		if result.Error != nil {
			resp.Error = result.Error
			resp.Status = "failed"
		} else {
			resp.Data = result
		}

		req.Result <- resp
		close(req.Result)
	}
}

func (h *Handler) handleStatus(w http.ResponseWriter, r *http.Request) {
	groups := h.resourceGroupManager.GetAllGroups()
	groupMetrics := make([]map[string]interface{}, 0, len(groups))
	for _, g := range groups {
		groupMetrics = append(groupMetrics, g.GetMetrics())
	}

	resp := StatusResponse{
		CircuitBreaker:       h.rateLimiter.GetCircuitBreakerStatus(),
		CircuitBreakerDetail: h.rateLimiter.GetCircuitBreakerDetail(),
		QueueMetrics:         h.priorityQueue.GetMetrics(),
		QueueOrder:           h.priorityQueue.GetQueueOrder(),
		QueryCount:           len(h.queryHistory),
		ResourceGroups:       groupMetrics,
	}
	json.NewEncoder(w).Encode(resp)
}

func (h *Handler) handleHistory(w http.ResponseWriter, r *http.Request) {
	h.historyMu.RLock()
	defer h.historyMu.RUnlock()

	count := len(h.queryHistory)
	if count > 100 {
		count = 100
	}

	history := make([]*QueryRecord, count)
	for i := 0; i < count; i++ {
		history[i] = h.queryHistory[len(h.queryHistory)-1-i]
	}

	json.NewEncoder(w).Encode(history)
}

func (h *Handler) handleAnalyze(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Query string `json:"query"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	complexity := h.analyzer.AnalyzeQuery(ctx, req.Query)
	json.NewEncoder(w).Encode(complexity)
}

func (h *Handler) handlePreempt(w http.ResponseWriter, r *http.Request) {
	var req struct {
		RequestID string `json:"request_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	success := h.priorityQueue.Preempt(req.RequestID)

	resp := map[string]interface{}{
		"success": success,
		"message": "preempt request processed",
	}
	if !success {
		resp["message"] = "request not found in queue"
	}

	json.NewEncoder(w).Encode(resp)
}

func (h *Handler) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("OK"))
}

func (h *Handler) handleResourceGroups(w http.ResponseWriter, r *http.Request) {
	groups := h.resourceGroupManager.GetAllGroups()
	result := make([]map[string]interface{}, 0, len(groups))
	for _, g := range groups {
		result = append(result, g.GetMetrics())
	}
	json.NewEncoder(w).Encode(result)
}

func (h *Handler) handleAddResourceGroup(w http.ResponseWriter, r *http.Request) {
	var cfg config.ResourceGroupConfig
	if err := json.NewDecoder(r.Body).Decode(&cfg); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if cfg.Name == "" {
		http.Error(w, "resource group name is required", http.StatusBadRequest)
		return
	}
	group := h.resourceGroupManager.AddGroup(cfg, h.config.Limiter)
	json.NewEncoder(w).Encode(group.GetMetrics())
}

func (h *Handler) handleDeleteResourceGroup(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	name := vars["name"]
	success := h.resourceGroupManager.RemoveGroup(name)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": success,
	})
}

var drillManager *drill.DrillManager

func initDrillManager(h *Handler) {
	executor := func(ctx context.Context, req drill.QueryRequest) (*drill.QueryResponse, error) {
		internalReq := QueryRequest{
			UserID:        req.UserID,
			Query:         req.Query,
			Priority:      req.Priority,
			ResourceGroup: req.ResourceGroup,
		}
		resp, err := h.ExecuteQueryDirect(ctx, internalReq)
		if err != nil {
			return nil, err
		}
		return &drill.QueryResponse{
			RequestID: resp.RequestID,
			Status:    resp.Status,
			Error:     resp.Error,
		}, nil
	}
	drillManager = drill.NewDrillManager(executor)
}

func (h *Handler) handleDrillStart(w http.ResponseWriter, r *http.Request) {
	if drillManager == nil {
		initDrillManager(h)
	}

	var cfg struct {
		Name           string            `json:"name"`
		DurationSec    int               `json:"duration_seconds"`
		Concurrency    int               `json:"concurrency"`
		QueriesPerSec  int               `json:"queries_per_second"`
		QueryTemplates []string          `json:"query_templates"`
		PriorityWeights map[string]int   `json:"priority_weights"`
		ResourceGroup  string            `json:"resource_group"`
		UserIDs        []string          `json:"user_ids"`
		SlowQueryRatio float64           `json:"slow_query_ratio"`
		ErrorRatio     float64           `json:"error_ratio"`
	}

	if err := json.NewDecoder(r.Body).Decode(&cfg); err != nil {
		defaultCfg := drillManager.GetDefaultConfig()
		metrics, err := drillManager.StartDrill(defaultCfg)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		json.NewEncoder(w).Encode(map[string]interface{}{
			"started": true,
			"metrics": metrics,
		})
		return
	}

	drillCfg := drill.DrillConfig{
		Name:            cfg.Name,
		Duration:        time.Duration(cfg.DurationSec) * time.Second,
		Concurrency:     cfg.Concurrency,
		QueriesPerSec:   cfg.QueriesPerSec,
		QueryTemplates:  cfg.QueryTemplates,
		PriorityWeights: cfg.PriorityWeights,
		ResourceGroup:   cfg.ResourceGroup,
		UserIDs:         cfg.UserIDs,
		SlowQueryRatio:  cfg.SlowQueryRatio,
		ErrorRatio:      cfg.ErrorRatio,
	}

	if drillCfg.Duration == 0 {
		drillCfg.Duration = 60 * time.Second
	}
	if drillCfg.Concurrency == 0 {
		drillCfg.Concurrency = 50
	}
	if drillCfg.QueriesPerSec == 0 {
		drillCfg.QueriesPerSec = 100
	}
	if len(drillCfg.QueryTemplates) == 0 {
		drillCfg.QueryTemplates = drillManager.GetDefaultConfig().QueryTemplates
	}
	if len(drillCfg.PriorityWeights) == 0 {
		drillCfg.PriorityWeights = drillManager.GetDefaultConfig().PriorityWeights
	}
	if drillCfg.ResourceGroup == "" {
		drillCfg.ResourceGroup = "default"
	}
	if len(drillCfg.UserIDs) == 0 {
		drillCfg.UserIDs = drillManager.GetDefaultConfig().UserIDs
	}

	metrics, err := drillManager.StartDrill(drillCfg)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"started": true,
		"metrics": metrics,
	})
}

func (h *Handler) handleDrillStop(w http.ResponseWriter, r *http.Request) {
	if drillManager == nil {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"stopped": false,
			"error":   "no drill running",
		})
		return
	}
	success := drillManager.StopDrill()
	json.NewEncoder(w).Encode(map[string]interface{}{
		"stopped": success,
	})
}

func (h *Handler) handleDrillStatus(w http.ResponseWriter, r *http.Request) {
	if drillManager == nil {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"running": false,
		})
		return
	}
	status := drillManager.GetStatus()
	json.NewEncoder(w).Encode(status)
}

func (h *Handler) handleDrillReport(w http.ResponseWriter, r *http.Request) {
	if drillManager == nil {
		json.NewEncoder(w).Encode(nil)
		return
	}
	report := drillManager.GetReport()
	json.NewEncoder(w).Encode(report)
}

func (h *Handler) handleDrillConfig(w http.ResponseWriter, r *http.Request) {
	if drillManager == nil {
		initDrillManager(h)
	}
	defaultCfg := drillManager.GetDefaultConfig()
	json.NewEncoder(w).Encode(map[string]interface{}{
		"name":             defaultCfg.Name,
		"duration_seconds": defaultCfg.Duration.Seconds(),
		"concurrency":      defaultCfg.Concurrency,
		"queries_per_second": defaultCfg.QueriesPerSec,
		"query_templates":  defaultCfg.QueryTemplates,
		"priority_weights": defaultCfg.PriorityWeights,
		"resource_group":   defaultCfg.ResourceGroup,
		"user_ids":         defaultCfg.UserIDs,
		"slow_query_ratio": defaultCfg.SlowQueryRatio,
		"error_ratio":      defaultCfg.ErrorRatio,
	})
}

func (h *Handler) addHistory(record *QueryRecord) {
	h.historyMu.Lock()
	defer h.historyMu.Unlock()

	h.queryHistory = append(h.queryHistory, record)

	if len(h.queryHistory) > 1000 {
		h.queryHistory = h.queryHistory[1:]
	}
}
