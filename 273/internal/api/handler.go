package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"scheduler/internal/models"
	"scheduler/internal/scheduler"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	scheduler *scheduler.Scheduler
}

func NewHandler(s *scheduler.Scheduler) *Handler {
	return &Handler{scheduler: s}
}

func (h *Handler) RegisterRoutes(r *gin.Engine) {
	api := r.Group("/api/v1")
	{
		tasks := api.Group("/tasks")
		{
			tasks.POST("", h.CreateTask)
			tasks.GET("/:id", h.GetTask)
			tasks.DELETE("/:id", h.DeleteTask)
			tasks.POST("/:id/pause", h.PauseTask)
			tasks.POST("/:id/resume", h.ResumeTask)
		}

		dags := api.Group("/dags")
		{
			dags.POST("", h.CreateDAG)
			dags.GET("/:id", h.GetDAG)
			dags.POST("/:id/trigger", h.TriggerDAG)
			dags.POST("/dependencies", h.AddDependency)
			dags.GET("/:id/status", h.GetDAGStatus)
		}

		prediction := api.Group("/prediction")
		{
			prediction.GET("/load", h.GetLoadPrediction)
			prediction.GET("/current", h.GetCurrentLoad)
			prediction.GET("/peak", h.GetPeakPrediction)
		}

		pools := api.Group("/pools")
		{
			pools.POST("", h.CreateResourcePool)
			pools.GET("", h.GetAllPools)
			pools.GET("/:name", h.GetPoolStats)
		}

		api.GET("/stats", h.GetStats)
		api.POST("/shards", h.SubmitShardTask)
	}
}

type CreateTaskResponse struct {
	TaskID string `json:"task_id"`
	Status string `json:"status"`
}

func (h *Handler) CreateTask(c *gin.Context) {
	var req models.CreateTaskRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	task, err := h.scheduler.CreateTask(c.Request.Context(), &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, CreateTaskResponse{
		TaskID: task.ID,
		Status: "created",
	})
}

func (h *Handler) GetTask(c *gin.Context) {
	taskID := c.Param("id")
	task, err := h.scheduler.GetTask(c.Request.Context(), taskID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
		return
	}

	c.JSON(http.StatusOK, task)
}

func (h *Handler) DeleteTask(c *gin.Context) {
	taskID := c.Param("id")
	if err := h.scheduler.DeleteTask(c.Request.Context(), taskID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "deleted"})
}

func (h *Handler) PauseTask(c *gin.Context) {
	taskID := c.Param("id")
	if err := h.scheduler.PauseTask(c.Request.Context(), taskID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "paused"})
}

func (h *Handler) ResumeTask(c *gin.Context) {
	taskID := c.Param("id")
	if err := h.scheduler.ResumeTask(c.Request.Context(), taskID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "resumed"})
}

func (h *Handler) GetStats(c *gin.Context) {
	stats, err := h.scheduler.GetStats(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, stats)
}

type SubmitShardRequest struct {
	ShardKey string                 `json:"shard_key" binding:"required"`
	Payload  map[string]interface{} `json:"payload"`
}

func (h *Handler) SubmitShardTask(c *gin.Context) {
	var req SubmitShardRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	payloadBytes, _ := json.Marshal(req.Payload)
	if err := h.scheduler.SubmitShardTask(c.Request.Context(), req.ShardKey, payloadBytes); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusAccepted, gin.H{"status": "submitted"})
}

func (h *Handler) CreateDAG(c *gin.Context) {
	var req models.CreateDAGRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	dag, err := h.scheduler.CreateDAG(c.Request.Context(), &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, dag)
}

func (h *Handler) GetDAG(c *gin.Context) {
	dagID := c.Param("id")
	dag, err := h.scheduler.GetDAG(c.Request.Context(), dagID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "dag not found"})
		return
	}

	c.JSON(http.StatusOK, dag)
}

func (h *Handler) TriggerDAG(c *gin.Context) {
	dagID := c.Param("id")
	if err := h.scheduler.TriggerDAG(c.Request.Context(), dagID); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "triggered"})
}

func (h *Handler) AddDependency(c *gin.Context) {
	var req models.AddDependencyRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.scheduler.AddDependency(c.Request.Context(), &req); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "added"})
}

func (h *Handler) GetDAGStatus(c *gin.Context) {
	dagID := c.Param("id")
	status, err := h.scheduler.GetDAGExecutionStatus(c.Request.Context(), dagID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, status)
}

func (h *Handler) GetLoadPrediction(c *gin.Context) {
	hours := 24
	if h := c.Query("hours"); h != "" {
		fmt.Sscanf(h, "%d", &hours)
	}

	predictions := h.scheduler.PredictLoad(hours)
	c.JSON(http.StatusOK, predictions)
}

func (h *Handler) GetCurrentLoad(c *gin.Context) {
	load := h.scheduler.GetCurrentLoad()
	c.JSON(http.StatusOK, load)
}

func (h *Handler) GetPeakPrediction(c *gin.Context) {
	hours := 24
	if h := c.Query("hours"); h != "" {
		fmt.Sscanf(h, "%d", &hours)
	}

	prediction, hour := h.scheduler.GetPeakPrediction(hours)
	c.JSON(http.StatusOK, gin.H{
		"peak":       prediction,
		"peak_hours": hour,
	})
}

func (h *Handler) CreateResourcePool(c *gin.Context) {
	var req models.ResourcePoolConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	pool := &models.ResourcePool{
		Name:           req.Name,
		WorkerCount:    req.WorkerCount,
		MaxWorkerCount: req.MaxWorkerCount,
		CPUQuota:       req.CPUQuota,
		MemoryQuotaMB:  req.MemoryQuotaMB,
		Description:    req.Description,
	}

	if err := h.scheduler.CreateResourcePool(c.Request.Context(), pool); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, pool)
}

func (h *Handler) GetAllPools(c *gin.Context) {
	pools := h.scheduler.GetResourcePoolStats()
	c.JSON(http.StatusOK, pools)
}

func (h *Handler) GetPoolStats(c *gin.Context) {
	poolName := c.Param("name")
	stats, err := h.scheduler.GetPoolStats(poolName)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, stats)
}
