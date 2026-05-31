package api

import (
	"context"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
	"es-shard-balancer/pkg/balancer"
	"es-shard-balancer/pkg/config"
	"es-shard-balancer/pkg/elasticsearch"
	"es-shard-balancer/pkg/monitor"
)

type Handler struct {
	client           *elasticsearch.Client
	balancer         *balancer.Balancer
	cfg              *config.Config
	logger           *zap.Logger
	loadMonitor      *monitor.LoadMonitor
	speedCtrl        *monitor.SpeedController
	shardHeatMonitor *monitor.ShardHeatMonitor
	autoScaler       *monitor.AutoScaler
}

func NewHandler(client *elasticsearch.Client, bal *balancer.Balancer, cfg *config.Config, logger *zap.Logger, loadMonitor *monitor.LoadMonitor, speedCtrl *monitor.SpeedController, shardHeatMonitor *monitor.ShardHeatMonitor, autoScaler *monitor.AutoScaler) *Handler {
	return &Handler{
		client:           client,
		balancer:         bal,
		cfg:              &cfg,
		logger:           logger,
		loadMonitor:      loadMonitor,
		speedCtrl:        speedCtrl,
		shardHeatMonitor: shardHeatMonitor,
		autoScaler:       autoScaler,
	}
}

func (h *Handler) GetHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ok",
	})
}

func (h *Handler) GetClusterHealth(c *gin.Context) {
	ctx := context.Background()
	health, err := h.client.GetClusterHealth(ctx)
	if err != nil {
		h.logger.Error("failed to get cluster health", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, health)
}

func (h *Handler) GetNodes(c *gin.Context) {
	ctx := context.Background()
	nodes, err := h.client.GetNodes(ctx)
	if err != nil {
		h.logger.Error("failed to get nodes", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, nodes)
}

func (h *Handler) GetShardDistribution(c *gin.Context) {
	ctx := context.Background()
	dist, err := h.balancer.AnalyzeDistribution(ctx)
	if err != nil {
		h.logger.Error("failed to get shard distribution", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, dist)
}

func (h *Handler) GetMigrationPlan(c *gin.Context) {
	ctx := context.Background()
	plans, err := h.balancer.GenerateMigrationPlan(ctx)
	if err != nil {
		h.logger.Error("failed to generate migration plan", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"plans": plans})
}

func (h *Handler) ExecuteMigrations(c *gin.Context) {
	ctx := context.Background()
	result, err := h.balancer.RunBalanceCycle(ctx)
	if err != nil {
		h.logger.Error("failed to execute migrations", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *Handler) MoveShard(c *gin.Context) {
	var req struct {
		Index    string `json:"index" binding:"required"`
		Shard    string `json:"shard" binding:"required"`
		FromNode string `json:"from_node" binding:"required"`
		ToNode   string `json:"to_node" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	shardNum, err := strconv.Atoi(req.Shard)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid shard number"})
		return
	}

	ctx := context.Background()
	if err := h.client.MoveShard(ctx, req.Index, shardNum, req.FromNode, req.ToNode); err != nil {
		h.logger.Error("failed to move shard", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "success", "message": "Shard migration initiated"})
}

func (h *Handler) GetMigrationTasks(c *gin.Context) {
	ctx := context.Background()
	tasks, err := h.client.GetMigrationTasks(ctx)
	if err != nil {
		h.logger.Error("failed to get migration tasks", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"tasks": tasks})
}

func (h *Handler) SetSpeedLimit(c *gin.Context) {
	var req struct {
		MaxBytesPerSec string `json:"max_bytes_per_sec" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()
	if err := h.client.SetSpeedLimit(ctx, req.MaxBytesPerSec); err != nil {
		h.logger.Error("failed to set speed limit", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "success", "message": "Speed limit updated"})
}

func (h *Handler) SetDiskWatermark(c *gin.Context) {
	var req struct {
		Low   string `json:"low" binding:"required"`
		High  string `json:"high" binding:"required"`
		Flood string `json:"flood" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()
	if err := h.client.SetDiskWatermark(ctx, req.Low, req.High, req.Flood); err != nil {
		h.logger.Error("failed to set disk watermark", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "success", "message": "Disk watermark updated"})
}

func (h *Handler) GetConfig(c *gin.Context) {
	c.JSON(http.StatusOK, h.cfg)
}

func (h *Handler) GetShards(c *gin.Context) {
	ctx := context.Background()
	shards, err := h.client.GetShards(ctx)
	if err != nil {
		h.logger.Error("failed to get shards", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"shards": shards})
}

func (h *Handler) GetNodeLoad(c *gin.Context) {
	if h.loadMonitor == nil {
		c.JSON(http.StatusOK, gin.H{"error": "load monitor not enabled"})
		return
	}

	nodeName := c.Param("name")
	if nodeName != "" {
		load := h.loadMonitor.GetNodeLoadHistory(nodeName)
		c.JSON(http.StatusOK, load)
		return
	}

	loads := h.loadMonitor.GetAllLoadHistory()
	c.JSON(http.StatusOK, gin.H{"loads": loads})
}

func (h *Handler) GetSpeedInfo(c *gin.Context) {
	if h.speedCtrl == nil {
		c.JSON(http.StatusOK, gin.H{"error": "speed controller not enabled"})
		return
	}

	info := h.speedCtrl.GetSpeedInfo()
	c.JSON(http.StatusOK, info)
}

func (h *Handler) SetAdaptiveSpeed(c *gin.Context) {
	if h.speedCtrl == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "speed controller not enabled"})
		return
	}

	var req struct {
		Speed string `json:"speed" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx := context.Background()
	if err := h.speedCtrl.SetSpeed(ctx, req.Speed); err != nil {
		h.logger.Error("failed to set speed", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "success", "current_speed": h.speedCtrl.GetCurrentSpeed()})
}

func (h *Handler) GetIndexHeat(c *gin.Context) {
	if h.shardHeatMonitor == nil {
		c.JSON(http.StatusOK, gin.H{"error": "shard heat monitor not enabled"})
		return
	}

	indexName := c.Param("name")
	if indexName != "" {
		heat := h.shardHeatMonitor.GetIndexHeat(indexName)
		c.JSON(http.StatusOK, heat)
		return
	}

	heats := h.shardHeatMonitor.GetAllIndexHeat()
	c.JSON(http.StatusOK, gin.H{"heats": heats})
}

func (h *Handler) GetHotIndices(c *gin.Context) {
	if h.shardHeatMonitor == nil {
		c.JSON(http.StatusOK, gin.H{"hot_indices": []string{}})
		return
	}

	hotIndices := h.shardHeatMonitor.GetHotIndices()
	c.JSON(http.StatusOK, gin.H{"hot_indices": hotIndices})
}

func (h *Handler) SimulateMigration(c *gin.Context) {
	ctx := context.Background()
	result, err := h.balancer.SimulateMigration(ctx)
	if err != nil {
		h.logger.Error("failed to simulate migration", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *Handler) GetAutoScalingStatus(c *gin.Context) {
	if h.autoScaler == nil {
		c.JSON(http.StatusOK, gin.H{"error": "auto scaler not enabled"})
		return
	}

	ctx := context.Background()
	status, err := h.autoScaler.GetScaleStatus(ctx)
	if err != nil {
		h.logger.Error("failed to get auto scaling status", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, status)
}

func (h *Handler) TriggerScaleOut(c *gin.Context) {
	if h.autoScaler == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "auto scaler not enabled"})
		return
	}

	ctx := context.Background()
	if err := h.autoScaler.CheckAndScale(ctx); err != nil {
		h.logger.Error("failed to trigger scale out", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	status, err := h.autoScaler.GetScaleStatus(ctx)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"status": "scale check completed"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "scale check completed", "auto_scaler": status})
}
