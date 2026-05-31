package api

import (
	"net/http"
	"strconv"
	"time"
	"zk-inspector/internal/collector"
	"zk-inspector/internal/health"
	"zk-inspector/internal/hotness"
	"zk-inspector/internal/predictor"
	"zk-inspector/internal/storage"
	"zk-inspector/internal/ttl"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	collector       *collector.ZKCollector
	storage         *storage.MemoryStorage
	predictor       *predictor.TimeSeriesPredictor
	ttlManager      *ttl.TTLManager
	hotnessAnalyzer *hotness.HotnessAnalyzer
	healthScorer    *health.HealthScorer
}

func SetupRoutes(
	r *gin.Engine,
	c *collector.ZKCollector,
	s *storage.MemoryStorage,
	p *predictor.TimeSeriesPredictor,
	t *ttl.TTLManager,
	h *hotness.HotnessAnalyzer,
	hs *health.HealthScorer,
) {
	handler := &Handler{
		collector:       c,
		storage:         s,
		predictor:       p,
		ttlManager:      t,
		hotnessAnalyzer: h,
		healthScorer:    hs,
	}

	api := r.Group("/api")
	{
		api.GET("/overview", handler.GetOverview)
		api.GET("/snapshot", handler.GetSnapshot)
		api.GET("/alerts", handler.GetAlerts)
		api.GET("/paths/top", handler.GetTopPaths)
		api.GET("/timeseries/:metric", handler.GetTimeSeries)
		api.GET("/predictions", handler.GetPredictions)
		api.GET("/recommendations", handler.GetRecommendations)
		api.POST("/collect", handler.TriggerCollection)
		api.GET("/node/*path", handler.GetNodeDetail)

		ttlAPI := api.Group("/ttl")
		{
			ttlAPI.GET("/stats", handler.GetTTLStats)
			ttlAPI.GET("/nodes", handler.GetTTLNodes)
			ttlAPI.POST("/set", handler.SetTTL)
			ttlAPI.POST("/remove", handler.RemoveTTL)
			ttlAPI.POST("/cleanup", handler.TriggerCleanup)
		}

		hotnessAPI := api.Group("/hotness")
		{
			hotnessAPI.GET("/stats", handler.GetHotnessStats)
			hotnessAPI.GET("/hot", handler.GetHotNodes)
			hotnessAPI.GET("/cold", handler.GetColdNodes)
			hotnessAPI.GET("/node/*path", handler.GetNodeHotness)
			hotnessAPI.GET("/migration", handler.GetMigrationSuggestions)
		}

		healthAPI := api.Group("/health")
		{
			healthAPI.GET("/score", handler.GetHealthScore)
		}
	}
}

func (h *Handler) GetOverview(c *gin.Context) {
	latest := h.storage.GetLatestSnapshot()

	response := gin.H{
		"status": "ok",
	}

	if latest != nil {
		response["total_nodes"] = latest.TotalNodes
		response["total_size"] = latest.TotalSize
		response["max_depth"] = latest.MaxDepth
		response["alert_count"] = len(latest.Alerts)
		response["timestamp"] = latest.Timestamp
	}

	c.JSON(http.StatusOK, response)
}

func (h *Handler) GetSnapshot(c *gin.Context) {
	latest := h.storage.GetLatestSnapshot()
	if latest == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "No snapshot available"})
		return
	}

	c.JSON(http.StatusOK, latest)
}

func (h *Handler) GetAlerts(c *gin.Context) {
	latest := h.storage.GetLatestSnapshot()
	if latest == nil {
		c.JSON(http.StatusOK, []interface{}{})
		return
	}

	c.JSON(http.StatusOK, latest.Alerts)
}

func (h *Handler) GetTopPaths(c *gin.Context) {
	by := c.DefaultQuery("by", "total_size")
	limitStr := c.DefaultQuery("limit", "20")
	limit, err := strconv.Atoi(limitStr)
	if err != nil {
		limit = 20
	}

	paths := h.storage.GetTopPaths(by, limit)
	c.JSON(http.StatusOK, paths)
}

func (h *Handler) GetTimeSeries(c *gin.Context) {
	metric := c.Param("metric")
	durationStr := c.DefaultQuery("duration", "24h")

	duration, err := time.ParseDuration(durationStr)
	if err != nil {
		duration = 24 * time.Hour
	}

	data := h.storage.GetTimeSeries(metric, duration)
	c.JSON(http.StatusOK, data)
}

func (h *Handler) GetPredictions(c *gin.Context) {
	metric := c.Query("metric")

	if metric != "" {
		pred := h.storage.GetPrediction(metric)
		if pred == nil {
			c.JSON(http.StatusNotFound, gin.H{"error": "Prediction not found"})
			return
		}
		c.JSON(http.StatusOK, pred)
		return
	}

	allPreds := h.storage.GetAllPredictions()
	c.JSON(http.StatusOK, allPreds)
}

func (h *Handler) GetRecommendations(c *gin.Context) {
	latest := h.storage.GetLatestSnapshot()
	recommendations := h.predictor.GenerateOptimizationRecommendations(latest)
	c.JSON(http.StatusOK, recommendations)
}

func (h *Handler) TriggerCollection(c *gin.Context) {
	snapshot, err := h.collector.Collect()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	h.storage.AddSnapshot(snapshot)
	c.JSON(http.StatusOK, gin.H{
		"message":     "Collection completed",
		"total_nodes": snapshot.TotalNodes,
		"total_size":  snapshot.TotalSize,
	})
}

func (h *Handler) GetNodeDetail(c *gin.Context) {
	path := c.Param("path")
	if path == "" {
		path = "/"
	}

	latest := h.storage.GetLatestSnapshot()
	if latest == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "No snapshot available"})
		return
	}

	if node, ok := latest.Nodes[path]; ok {
		c.JSON(http.StatusOK, node)
	} else {
		c.JSON(http.StatusNotFound, gin.H{"error": "Node not found"})
	}
}

func (h *Handler) GetTTLStats(c *gin.Context) {
	stats := h.ttlManager.GetTTLStats()
	c.JSON(http.StatusOK, stats)
}

func (h *Handler) GetTTLNodes(c *gin.Context) {
	nodes := h.ttlManager.GetAllTTLNodes()
	c.JSON(http.StatusOK, nodes)
}

type SetTTLRequest struct {
	Path       string `json:"path" binding:"required"`
	TTLSeconds int64  `json:"ttl_seconds" binding:"required,min=1"`
	AutoDelete bool   `json:"auto_delete"`
}

func (h *Handler) SetTTL(c *gin.Context) {
	var req SetTTLRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.ttlManager.SetTTL(req.Path, req.TTLSeconds, req.AutoDelete); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "TTL set successfully"})
}

func (h *Handler) RemoveTTL(c *gin.Context) {
	var req struct {
		Path string `json:"path" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.ttlManager.RemoveTTL(req.Path); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "TTL removed successfully"})
}

func (h *Handler) TriggerCleanup(c *gin.Context) {
	deleted, err := h.ttlManager.DeleteExpiredNodes()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"deleted": deleted})
}

func (h *Handler) GetHotnessStats(c *gin.Context) {
	stats := h.hotnessAnalyzer.GetHotnessStats()
	c.JSON(http.StatusOK, stats)
}

func (h *Handler) GetHotNodes(c *gin.Context) {
	limitStr := c.DefaultQuery("limit", "20")
	limit, _ := strconv.Atoi(limitStr)

	nodes := h.hotnessAnalyzer.GetHotNodes(limit)
	c.JSON(http.StatusOK, nodes)
}

func (h *Handler) GetColdNodes(c *gin.Context) {
	thresholdStr := c.DefaultQuery("threshold", "0")
	threshold, _ := strconv.ParseFloat(thresholdStr, 64)

	nodes := h.hotnessAnalyzer.GetColdDataNodes(threshold)
	c.JSON(http.StatusOK, nodes)
}

func (h *Handler) GetNodeHotness(c *gin.Context) {
	path := c.Param("path")
	if path == "" {
		path = "/"
	}

	hotness, ok := h.hotnessAnalyzer.GetNodeHotness(path)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": "Node not tracked"})
		return
	}

	c.JSON(http.StatusOK, hotness)
}

func (h *Handler) GetMigrationSuggestions(c *gin.Context) {
	latest := h.storage.GetLatestSnapshot()
	suggestions := h.hotnessAnalyzer.GenerateMigrationSuggestions(latest)
	c.JSON(http.StatusOK, suggestions)
}

func (h *Handler) GetHealthScore(c *gin.Context) {
	score := h.healthScorer.CalculateHealthScore()
	c.JSON(http.StatusOK, score)
}
