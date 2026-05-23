package handlers

import (
	"net/http"
	"strconv"
	"time"

	"scheduler/internal/models"
	"scheduler/internal/scheduler"
	"scheduler/internal/store"

	"github.com/gin-gonic/gin"
)

type TaskHandler struct {
	store     *store.MySQLStore
	scheduler *scheduler.Scheduler
}

func NewTaskHandler(store *store.MySQLStore, sched *scheduler.Scheduler) *TaskHandler {
	return &TaskHandler{
		store:     store,
		scheduler: sched,
	}
}

type CreateTaskRequest struct {
	Name        string                `json:"name" binding:"required"`
	Description string                `json:"description"`
	TaskType    string                `json:"task_type" binding:"required"`
	Payload     string                `json:"payload"`
	TriggerType models.TriggerType    `json:"trigger_type" binding:"required"`
	CronExpr    string                `json:"cron_expr"`
	IntervalSec int                   `json:"interval_sec"`
	MaxRetries  int                   `json:"max_retries"`
	RetryDelay  int                   `json:"retry_delay"`
	TimeoutSec  int                   `json:"timeout_sec"`
	Dependencies string               `json:"dependencies"`
}

func (h *TaskHandler) CreateTask(c *gin.Context) {
	var req CreateTaskRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.MaxRetries == 0 {
		req.MaxRetries = 3
	}
	if req.RetryDelay == 0 {
		req.RetryDelay = 5
	}
	if req.TimeoutSec == 0 {
		req.TimeoutSec = 300
	}

	task := &models.Task{
		Name:         req.Name,
		Description:  req.Description,
		TaskType:     req.TaskType,
		Payload:      req.Payload,
		TriggerType:  req.TriggerType,
		CronExpr:     req.CronExpr,
		IntervalSec:  req.IntervalSec,
		MaxRetries:   req.MaxRetries,
		RetryDelay:   req.RetryDelay,
		TimeoutSec:   req.TimeoutSec,
		Dependencies: req.Dependencies,
	}

	if err := h.scheduler.RegisterTask(c.Request.Context(), task); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, task)
}

func (h *TaskHandler) GetTask(c *gin.Context) {
	id := c.Param("id")
	task, err := h.store.GetTask(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
		return
	}

	c.JSON(http.StatusOK, task)
}

func (h *TaskHandler) ListTasks(c *gin.Context) {
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))

	tasks, count, err := h.store.ListTasks(c.Request.Context(), offset, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"data":  tasks,
		"count": count,
		"offset": offset,
		"limit":  limit,
	})
}

func (h *TaskHandler) UpdateTask(c *gin.Context) {
	id := c.Param("id")

	var req CreateTaskRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	task, err := h.store.GetTask(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
		return
	}

	task.Name = req.Name
	task.Description = req.Description
	task.TaskType = req.TaskType
	task.Payload = req.Payload
	task.TriggerType = req.TriggerType
	task.CronExpr = req.CronExpr
	task.IntervalSec = req.IntervalSec
	task.MaxRetries = req.MaxRetries
	task.RetryDelay = req.RetryDelay
	task.TimeoutSec = req.TimeoutSec
	task.Dependencies = req.Dependencies

	nextRunAt, err := scheduler.CalculateNextRunTime(task)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	task.NextRunAt = nextRunAt

	if err := h.store.UpdateTask(c.Request.Context(), task); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, task)
}

func (h *TaskHandler) DeleteTask(c *gin.Context) {
	id := c.Param("id")
	task, err := h.store.GetTask(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
		return
	}

	task.Status = models.TaskStatusPaused
	if err := h.store.UpdateTask(c.Request.Context(), task); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "task paused"})
}

func (h *TaskHandler) TriggerTask(c *gin.Context) {
	id := c.Param("id")
	task, err := h.store.GetTask(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "task not found"})
		return
	}

	now := timeNow()
	task.NextRunAt = &now
	task.Status = models.TaskStatusPending

	if err := h.store.UpdateTask(c.Request.Context(), task); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "task triggered"})
}

func (h *TaskHandler) GetTaskExecutions(c *gin.Context) {
	taskID := c.Param("id")
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))

	executions, count, err := h.store.ListExecutions(c.Request.Context(), taskID, offset, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"data":  executions,
		"count": count,
		"offset": offset,
		"limit":  limit,
	})
}

func (h *TaskHandler) ListAllExecutions(c *gin.Context) {
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))

	executions, count, err := h.store.ListExecutions(c.Request.Context(), "", offset, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"data":  executions,
		"count": count,
		"offset": offset,
		"limit":  limit,
	})
}

func (h *TaskHandler) GetExecution(c *gin.Context) {
	id := c.Param("id")
	execution, err := h.store.GetExecution(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "execution not found"})
		return
	}

	c.JSON(http.StatusOK, execution)
}

func timeNow() time.Time {
	return time.Now()
}

func (h *TaskHandler) ListAuditLogs(c *gin.Context) {
	taskID := c.Query("task_id")
	event := c.Query("event")
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))

	logs, count, err := h.store.ListAuditLogs(c.Request.Context(), taskID, event, offset, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"data":  logs,
		"count": count,
		"offset": offset,
		"limit":  limit,
	})
}

func (h *TaskHandler) GetTaskAuditLogs(c *gin.Context) {
	taskID := c.Param("id")
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))

	logs, count, err := h.store.ListAuditLogs(c.Request.Context(), taskID, "", offset, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"data":  logs,
		"count": count,
		"offset": offset,
		"limit":  limit,
	})
}

func (h *TaskHandler) ListWorkerNodes(c *gin.Context) {
	nodes, err := h.store.ListWorkerNodes(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"data": nodes,
	})
}
