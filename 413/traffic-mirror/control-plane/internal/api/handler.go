package api

import (
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/traffic-mirror/control-plane/internal/alert"
	"github.com/traffic-mirror/control-plane/internal/compare"
	"github.com/traffic-mirror/control-plane/internal/config"
	"github.com/traffic-mirror/control-plane/internal/replay"
	"github.com/traffic-mirror/control-plane/internal/tracing"
	"github.com/traffic-mirror/control-plane/pkg/types"
)

type Handler struct {
	configMgr    *config.Manager
	compareStore *compare.Store
	tracer       *tracing.JaegerTracer
	xdsUpdater   func(configJSON string) error
	alertMgr     *alert.Manager
	replayMgr    *replay.Manager
}

func NewHandler(configMgr *config.Manager, compareStore *compare.Store, tracer *tracing.JaegerTracer, xdsUpdater func(string) error) *Handler {
	alertStore := alert.NewStore(configMgr.DB())
	alertMgr := alert.NewManager(configMgr.DB(), alertStore)
	replayMgr := replay.NewManager(configMgr.DB(), compareStore)

	return &Handler{
		configMgr:    configMgr,
		compareStore: compareStore,
		tracer:       tracer,
		xdsUpdater:   xdsUpdater,
		alertMgr:     alertMgr,
		replayMgr:    replayMgr,
	}
}

func (h *Handler) RegisterRoutes(router *gin.Engine) {
	api := router.Group("/api/v1")
	{
		config := api.Group("/config")
		{
			config.GET("", h.GetConfig)
			config.PUT("/sampling-rate", h.UpdateSamplingRate)
			config.PUT("/sampling-hash-key", h.UpdateSamplingHashKey)
			config.PUT("/test-cluster", h.UpdateTestCluster)
			config.PUT("/enabled", h.SetEnabled)
			config.PUT("/color", h.UpdateColorConfig)
			config.GET("/color", h.GetColorConfig)
			config.PUT("/anomaly", h.UpdateAnomalyConfig)
			config.GET("/anomaly", h.GetAnomalyConfig)
		}

		headerRules := api.Group("/header-rules")
		{
			headerRules.GET("", h.ListHeaderRules)
			headerRules.POST("", h.CreateHeaderRule)
			headerRules.GET("/:id", h.GetHeaderRule)
			headerRules.PUT("/:id", h.UpdateHeaderRule)
			headerRules.DELETE("/:id", h.DeleteHeaderRule)
		}

		protoSchemas := api.Group("/proto-schemas")
		{
			protoSchemas.GET("", h.ListProtoSchemas)
			protoSchemas.POST("", h.CreateProtoSchema)
			protoSchemas.GET("/:id", h.GetProtoSchema)
			protoSchemas.PUT("/:id", h.UpdateProtoSchema)
			protoSchemas.DELETE("/:id", h.DeleteProtoSchema)
			protoSchemas.GET("/by-message-type/:message_type", h.GetProtoSchemaByMessageType)
		}

		comparisons := api.Group("/comparisons")
		{
			comparisons.GET("", h.QueryComparisons)
			comparisons.GET("/:id", h.GetComparison)
			comparisons.POST("", h.ReceiveComparison)
			comparisons.GET("/stats", h.GetComparisonStats)
		}

		alerts := api.Group("/alerts")
		{
			alerts.GET("", h.QueryAlerts)
			alerts.GET("/stats", h.GetAlertStats)
			alerts.GET("/:id", h.GetAlert)
			alerts.PUT("/:id/ack", h.AcknowledgeAlert)
			alerts.PUT("/ack-all", h.AcknowledgeAllAlerts)
			alerts.DELETE("/:id", h.DeleteAlert)
		}

		replay := api.Group("/replay")
		{
			replay.POST("", h.CreateReplayTask)
			replay.GET("", h.ListReplayTasks)
			replay.GET("/:id", h.GetReplayTask)
			replay.POST("/:id/start", h.StartReplayTask)
			replay.POST("/:id/stop", h.StopReplayTask)
			replay.DELETE("/:id", h.DeleteReplayTask)
		}

		api.GET("/status", h.GetStatus)
	}
}

func (h *Handler) GetConfig(c *gin.Context) {
	cfg := h.configMgr.GetConfig()
	c.JSON(http.StatusOK, cfg)
}

type SamplingRateRequest struct {
	Rate float64 `json:"rate" binding:"gte=0,lte=1"`
}

func (h *Handler) UpdateSamplingRate(c *gin.Context) {
	var req SamplingRateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.configMgr.UpdateSamplingRate(req.Rate); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.updateXDS(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update xDS: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "sampling rate updated", "rate": req.Rate})
}

func (h *Handler) UpdateSamplingHashKey(c *gin.Context) {
	var req types.SamplingHashKeyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.configMgr.UpdateSamplingHashKey(req.HashKey); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.updateXDS(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update xDS: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "sampling hash key updated", "hash_key": req.HashKey})
}

type TestClusterRequest struct {
	Cluster string `json:"cluster" binding:"required"`
}

func (h *Handler) UpdateTestCluster(c *gin.Context) {
	var req TestClusterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.configMgr.UpdateTestCluster(req.Cluster); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.updateXDS(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update xDS: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "test cluster updated", "cluster": req.Cluster})
}

type EnabledRequest struct {
	Enabled bool `json:"enabled"`
}

func (h *Handler) SetEnabled(c *gin.Context) {
	var req EnabledRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.configMgr.SetEnabled(req.Enabled)

	if err := h.updateXDS(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update xDS: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "mirror status updated", "enabled": req.Enabled})
}

func (h *Handler) ListHeaderRules(c *gin.Context) {
	rules := h.configMgr.GetHeaderRules()
	c.JSON(http.StatusOK, rules)
}

func (h *Handler) CreateHeaderRule(c *gin.Context) {
	var rule types.HeaderRule
	if err := c.ShouldBindJSON(&rule); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rule.Enabled = true
	created, err := h.configMgr.AddHeaderRule(rule)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.updateXDS(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update xDS: " + err.Error()})
		return
	}

	c.JSON(http.StatusCreated, created)
}

func (h *Handler) GetHeaderRule(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	rule, ok := h.configMgr.GetHeaderRule(id)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "rule not found"})
		return
	}

	c.JSON(http.StatusOK, rule)
}

func (h *Handler) UpdateHeaderRule(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	var rule types.HeaderRule
	if err := c.ShouldBindJSON(&rule); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	updated, err := h.configMgr.UpdateHeaderRule(id, rule)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.updateXDS(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update xDS: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, updated)
}

func (h *Handler) DeleteHeaderRule(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	if err := h.configMgr.DeleteHeaderRule(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.updateXDS(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update xDS: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "rule deleted"})
}

func (h *Handler) ListProtoSchemas(c *gin.Context) {
	schemas := h.configMgr.GetProtoSchemas()
	c.JSON(http.StatusOK, schemas)
}

func (h *Handler) CreateProtoSchema(c *gin.Context) {
	var schema types.ProtoSchema
	if err := c.ShouldBindJSON(&schema); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	schema.Enabled = true
	created, err := h.configMgr.AddProtoSchema(schema)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, created)
}

func (h *Handler) GetProtoSchema(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	schema, ok := h.configMgr.GetProtoSchema(id)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "proto schema not found"})
		return
	}

	c.JSON(http.StatusOK, schema)
}

func (h *Handler) GetProtoSchemaByMessageType(c *gin.Context) {
	messageType := c.Param("message_type")
	schema, ok := h.configMgr.GetProtoSchemaByMessageType(messageType)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "proto schema not found for message type: " + messageType})
		return
	}

	c.JSON(http.StatusOK, schema)
}

func (h *Handler) UpdateProtoSchema(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	var schema types.ProtoSchema
	if err := c.ShouldBindJSON(&schema); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	updated, err := h.configMgr.UpdateProtoSchema(id, schema)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, updated)
}

func (h *Handler) DeleteProtoSchema(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	if err := h.configMgr.DeleteProtoSchema(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "proto schema deleted"})
}

func (h *Handler) QueryComparisons(c *gin.Context) {
	var query types.ComparisonQuery
	if err := c.ShouldBindQuery(&query); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	results, total, err := h.compareStore.Query(query)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"results":   results,
		"total":     total,
		"page":      query.Page,
		"page_size": query.PageSize,
	})
}

func (h *Handler) GetComparison(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	result, err := h.compareStore.GetByID(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "comparison not found"})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) ReceiveComparison(c *gin.Context) {
	var result types.ComparisonResult
	body, err := c.GetRawData()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := json.Unmarshal(body, &result); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if result.Timestamp == 0 {
		result.Timestamp = time.Now().UnixNano()
	}

	if err := h.compareStore.Save(&result); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if result.Anomaly != "" {
		if err := h.alertMgr.ProcessComparison(&result); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to process alert: " + err.Error()})
			return
		}
	}

	if h.tracer != nil {
		h.tracer.RecordComparison(c.Request.Context(), map[string]interface{}{
			"path":         result.Path,
			"method":       result.Method,
			"has_diff":     result.HasDiff,
			"severity":     result.Severity,
			"prod_status":  result.ProdStatus,
			"test_status":  result.TestStatus,
			"is_proto":     result.IsProto,
			"anomaly":      result.Anomaly,
		})
	}

	c.JSON(http.StatusCreated, gin.H{"id": result.ID})
}

func (h *Handler) GetComparisonStats(c *gin.Context) {
	stats, err := h.compareStore.GetStats()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, stats)
}

func (h *Handler) GetStatus(c *gin.Context) {
	cfg := h.configMgr.GetConfig()
	stats, _ := h.compareStore.GetStats()
	alertStats, _ := h.alertMgr.GetStore().GetStats()

	colorEnabled, colorHeader, colorValue := h.configMgr.GetColorConfig()

	status := types.MirrorStatus{
		Enabled:           cfg.Enabled,
		SamplingRate:      cfg.SamplingRate,
		SamplingHashKey:   cfg.SamplingHashKey,
		TotalRequests:     stats.TotalCount,
		MirroredCount:     stats.MatchCount + stats.MismatchCount,
		TestCluster:       cfg.TestCluster,
		ProtoSchemaCount:  h.configMgr.GetProtoSchemaCount(),
		ColorEnabled:      colorEnabled,
		ColorHeader:       colorHeader,
		ColorValue:        colorValue,
		AnomalyCount:      alertStats.TotalCount,
	}

	c.JSON(http.StatusOK, status)
}

func (h *Handler) updateXDS() error {
	if h.xdsUpdater == nil {
		return nil
	}
	configJSON := h.configMgr.GetConfigJSON()
	return h.xdsUpdater(configJSON)
}

func (h *Handler) GetColorConfig(c *gin.Context) {
	enabled, header, value := h.configMgr.GetColorConfig()
	c.JSON(http.StatusOK, gin.H{
		"enabled": enabled,
		"header":  header,
		"value":   value,
	})
}

func (h *Handler) UpdateColorConfig(c *gin.Context) {
	var req types.ColorConfigRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.configMgr.UpdateColorConfig(req.Enabled, req.Header, req.Value); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.updateXDS(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update xDS: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message": "color config updated",
		"enabled": req.Enabled,
		"header":  req.Header,
		"value":   req.Value,
	})
}

func (h *Handler) GetAnomalyConfig(c *gin.Context) {
	enabled, threshold := h.configMgr.GetAnomalyConfig()
	c.JSON(http.StatusOK, gin.H{
		"enabled":   enabled,
		"threshold": threshold,
	})
}

func (h *Handler) UpdateAnomalyConfig(c *gin.Context) {
	var req types.AnomalyConfigRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.configMgr.UpdateAnomalyConfig(req.Enabled, req.Threshold); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if err := h.updateXDS(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to update xDS: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":   "anomaly config updated",
		"enabled":   req.Enabled,
		"threshold": req.Threshold,
	})
}

func (h *Handler) QueryAlerts(c *gin.Context) {
	var query types.AnomalyQuery
	if err := c.ShouldBindQuery(&query); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	alerts, total, err := h.alertMgr.GetStore().Query(query)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"results":   alerts,
		"total":     total,
		"page":      query.Page,
		"page_size": query.PageSize,
	})
}

func (h *Handler) GetAlertStats(c *gin.Context) {
	stats, err := h.alertMgr.GetStore().GetStats()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, stats)
}

func (h *Handler) GetAlert(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	alert, err := h.alertMgr.GetStore().GetByID(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "alert not found"})
		return
	}

	c.JSON(http.StatusOK, alert)
}

func (h *Handler) AcknowledgeAlert(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	if err := h.alertMgr.GetStore().Acknowledge(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "alert acknowledged"})
}

func (h *Handler) AcknowledgeAllAlerts(c *gin.Context) {
	if err := h.alertMgr.GetStore().AcknowledgeAll(); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "all alerts acknowledged"})
}

func (h *Handler) DeleteAlert(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	if err := h.alertMgr.GetStore().Delete(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "alert deleted"})
}

func (h *Handler) CreateReplayTask(c *gin.Context) {
	var req types.ReplayRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	task, err := h.replayMgr.CreateTask(req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, task)
}

func (h *Handler) ListReplayTasks(c *gin.Context) {
	tasks, err := h.replayMgr.ListTasks()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, tasks)
}

func (h *Handler) GetReplayTask(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	task, err := h.replayMgr.GetTask(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
		return
	}

	c.JSON(http.StatusOK, task)
}

func (h *Handler) StartReplayTask(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	if err := h.replayMgr.StartTask(id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "replay task started"})
}

func (h *Handler) StopReplayTask(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	if err := h.replayMgr.StopTask(id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "replay task stopped"})
}

func (h *Handler) DeleteReplayTask(c *gin.Context) {
	id, err := strconv.ParseInt(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	if err := h.replayMgr.DeleteTask(id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "replay task deleted"})
}
