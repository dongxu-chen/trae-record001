package api

import (
	"deadlock-resolver/config"
	"deadlock-resolver/engine"
	"deadlock-resolver/models"
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	detector *engine.DeadlockDetector
	config   *config.Config
}

func NewHandler(detector *engine.DeadlockDetector, cfg *config.Config) *Handler {
	return &Handler{
		detector: detector,
		config:   cfg,
	}
}

func (h *Handler) SetupRoutes(r *gin.Engine) {
	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	})

	api := r.Group("/api")
	{
		api.GET("/health", h.HealthCheck)
		
		api.GET("/deadlocks/current", h.GetCurrentDeadlocks)
		api.GET("/deadlocks/history", h.GetDeadlockHistory)
		api.GET("/deadlocks/:id", h.GetDeadlockDetail)
		api.POST("/deadlocks/:id/resolve", h.ResolveDeadlock)
		
		api.GET("/rules", h.GetRules)
		api.POST("/rules", h.CreateRule)
		api.PUT("/rules/:id", h.UpdateRule)
		api.DELETE("/rules/:id", h.DeleteRule)
		
		api.GET("/config", h.GetConfig)
		api.PUT("/config", h.UpdateConfig)
		
		api.GET("/statistics", h.GetStatistics)
		
		api.GET("/transactions", h.GetTransactions)
		
		api.GET("/detector/status", h.GetDetectorStatus)
		api.POST("/detector/start", h.StartDetector)
		api.POST("/detector/stop", h.StopDetector)
		
		api.GET("/prevention/recommendations", h.GetPreventionRecommendations)
		api.GET("/prevention/recommendations/:id", h.GetPreventionRecommendation)
		api.PUT("/prevention/recommendations/:id/resolve", h.MarkRecommendationResolved)
		api.GET("/prevention/statistics", h.GetPreventionStatistics)
		
		api.GET("/sandbox/scenarios", h.GetSandboxScenarios)
		api.GET("/sandbox/scenarios/:id", h.GetSandboxScenario)
		api.POST("/sandbox/scenarios", h.CreateSandboxScenario)
		api.DELETE("/sandbox/scenarios/:id", h.DeleteSandboxScenario)
		api.POST("/sandbox/run", h.RunSimulation)
		api.GET("/sandbox/results", h.GetSimulationResults)
		api.GET("/sandbox/results/:id", h.GetSimulationResult)
		api.GET("/sandbox/results/:id/status", h.GetSimulationStatus)
		
		api.GET("/audit/logs", h.GetAuditLogs)
		api.GET("/audit/logs/:id", h.GetAuditLogDetail)
		api.GET("/audit/statistics", h.GetAuditStatistics)
		api.GET("/audit/trace/:deadlock_id", h.GetAuditTraceByDeadlock)
	}
}

func (h *Handler) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status": "ok",
	})
}

func (h *Handler) GetCurrentDeadlocks(c *gin.Context) {
	deadlocks := h.detector.GetCurrentDeadlocks()
	c.JSON(http.StatusOK, gin.H{
		"data":  deadlocks,
		"count": len(deadlocks),
	})
}

func (h *Handler) GetDeadlockHistory(c *gin.Context) {
	store := h.detector.GetHistoryStore()
	deadlocks, err := store.GetAllDeadlocks()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": err.Error(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"data":  deadlocks,
		"count": len(deadlocks),
	})
}

func (h *Handler) GetDeadlockDetail(c *gin.Context) {
	deadlockID := c.Param("id")
	store := h.detector.GetHistoryStore()
	
	deadlock, err := store.GetDeadlockHistory(deadlockID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Deadlock not found",
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"data": deadlock,
	})
}

func (h *Handler) ResolveDeadlock(c *gin.Context) {
	deadlockID := c.Param("id")
	
	var req struct {
		TransactionID int64 `json:"transaction_id"`
	}
	
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request body",
		})
		return
	}
	
	err := h.detector.ResolveDeadlock(deadlockID, req.TransactionID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": err.Error(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"message": "Deadlock resolved successfully",
	})
}

func (h *Handler) GetRules(c *gin.Context) {
	ruleEngine := h.detector.GetRuleEngine()
	rules := ruleEngine.GetRules()
	
	c.JSON(http.StatusOK, gin.H{
		"data":  rules,
		"count": len(rules),
	})
}

func (h *Handler) CreateRule(c *gin.Context) {
	var rule models.Rule
	if err := c.ShouldBindJSON(&rule); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid rule data",
		})
		return
	}
	
	ruleEngine := h.detector.GetRuleEngine()
	ruleEngine.AddRule(rule)
	
	c.JSON(http.StatusCreated, gin.H{
		"data": rule,
	})
}

func (h *Handler) UpdateRule(c *gin.Context) {
	ruleID := c.Param("id")
	var rule models.Rule
	if err := c.ShouldBindJSON(&rule); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid rule data",
		})
		return
	}
	
	rule.ID = ruleID
	ruleEngine := h.detector.GetRuleEngine()
	ruleEngine.RemoveRule(ruleID)
	ruleEngine.AddRule(rule)
	
	c.JSON(http.StatusOK, gin.H{
		"data": rule,
	})
}

func (h *Handler) DeleteRule(c *gin.Context) {
	ruleID := c.Param("id")
	ruleEngine := h.detector.GetRuleEngine()
	ruleEngine.RemoveRule(ruleID)
	
	c.JSON(http.StatusOK, gin.H{
		"message": "Rule deleted successfully",
	})
}

func (h *Handler) GetConfig(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"data": h.config,
	})
}

func (h *Handler) UpdateConfig(c *gin.Context) {
	var newConfig config.Config
	if err := c.ShouldBindJSON(&newConfig); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid config data",
		})
		return
	}
	
	h.config.Strategy = newConfig.Strategy
	h.config.Database = newConfig.Database
	
	c.JSON(http.StatusOK, gin.H{
		"data": h.config,
	})
}

func (h *Handler) GetStatistics(c *gin.Context) {
	store := h.detector.GetHistoryStore()
	stats, err := store.GetStatistics()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": err.Error(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"data": stats,
	})
}

func (h *Handler) GetTransactions(c *gin.Context) {
	transactions, err := h.detector.GetTransactions()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": err.Error(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"data":  transactions,
		"count": len(transactions),
	})
}

func (h *Handler) GetDetectorStatus(c *gin.Context) {
	isRunning := h.detector.IsRunning()
	
	c.JSON(http.StatusOK, gin.H{
		"running": isRunning,
	})
}

func (h *Handler) StartDetector(c *gin.Context) {
	h.detector.Start()
	
	c.JSON(http.StatusOK, gin.H{
		"message": "Detector started",
	})
}

func (h *Handler) StopDetector(c *gin.Context) {
	h.detector.Stop()
	
	c.JSON(http.StatusOK, gin.H{
		"message": "Detector stopped",
	})
}

func (h *Handler) GetPreventionRecommendations(c *gin.Context) {
	limit := 50
	if l := c.Query("limit"); l != "" {
		if val, err := parseInt(l); err == nil {
			limit = val
		}
	}
	
	prevention := h.detector.GetPreventionEngine()
	recommendations := prevention.GetRecommendations(limit)
	
	c.JSON(http.StatusOK, gin.H{
		"data":  recommendations,
		"count": len(recommendations),
	})
}

func (h *Handler) GetPreventionRecommendation(c *gin.Context) {
	id := c.Param("id")
	prevention := h.detector.GetPreventionEngine()
	
	rec, err := prevention.GetRecommendation(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"data": rec})
}

func (h *Handler) MarkRecommendationResolved(c *gin.Context) {
	id := c.Param("id")
	prevention := h.detector.GetPreventionEngine()
	
	err := prevention.MarkResolved(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"message": "Recommendation marked as resolved"})
}

func (h *Handler) GetPreventionStatistics(c *gin.Context) {
	prevention := h.detector.GetPreventionEngine()
	stats := prevention.GetStatistics()
	
	c.JSON(http.StatusOK, gin.H{"data": stats})
}

func (h *Handler) GetSandboxScenarios(c *gin.Context) {
	sandbox := h.detector.GetSandboxEngine()
	scenarios := sandbox.GetScenarios()
	
	c.JSON(http.StatusOK, gin.H{
		"data":  scenarios,
		"count": len(scenarios),
	})
}

func (h *Handler) GetSandboxScenario(c *gin.Context) {
	id := c.Param("id")
	sandbox := h.detector.GetSandboxEngine()
	
	scenario, err := sandbox.GetScenario(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"data": scenario})
}

func (h *Handler) CreateSandboxScenario(c *gin.Context) {
	var scenario models.SimulationScenario
	if err := c.ShouldBindJSON(&scenario); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	sandbox := h.detector.GetSandboxEngine()
	sandbox.AddScenario(scenario)
	
	c.JSON(http.StatusCreated, gin.H{"data": scenario})
}

func (h *Handler) DeleteSandboxScenario(c *gin.Context) {
	id := c.Param("id")
	sandbox := h.detector.GetSandboxEngine()
	
	err := sandbox.DeleteScenario(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"message": "Scenario deleted successfully"})
}

func (h *Handler) RunSimulation(c *gin.Context) {
	var req struct {
		ScenarioID   string `json:"scenario_id" binding:"required"`
		KillStrategy string `json:"kill_strategy"`
	}
	
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	
	sandbox := h.detector.GetSandboxEngine()
	result, err := sandbox.RunSimulation(req.ScenarioID, req.KillStrategy)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"data": result})
}

func (h *Handler) GetSimulationResults(c *gin.Context) {
	limit := 20
	if l := c.Query("limit"); l != "" {
		if val, err := parseInt(l); err == nil {
			limit = val
		}
	}
	
	sandbox := h.detector.GetSandboxEngine()
	results := sandbox.GetResults(limit)
	
	c.JSON(http.StatusOK, gin.H{
		"data":  results,
		"count": len(results),
	})
}

func (h *Handler) GetSimulationResult(c *gin.Context) {
	id := c.Param("id")
	sandbox := h.detector.GetSandboxEngine()
	
	result, err := sandbox.GetResult(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"data": result})
}

func (h *Handler) GetSimulationStatus(c *gin.Context) {
	id := c.Param("id")
	sandbox := h.detector.GetSandboxEngine()
	
	status, err := sandbox.GetExecutionStatus(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"status": status})
}

func (h *Handler) GetAuditLogs(c *gin.Context) {
	limit := 50
	if l := c.Query("limit"); l != "" {
		if val, err := parseInt(l); err == nil {
			limit = val
		}
	}
	
	filters := make(map[string]string)
	filters["action"] = c.Query("action")
	filters["deadlock_id"] = c.Query("deadlock_id")
	filters["operator"] = c.Query("operator")
	filters["success"] = c.Query("success")
	filters["source"] = c.Query("source")
	filters["transaction_type"] = c.Query("transaction_type")
	
	audit := h.detector.GetAuditEngine()
	logs := audit.GetLogs(limit, filters)
	
	c.JSON(http.StatusOK, gin.H{
		"data":  logs,
		"count": len(logs),
	})
}

func (h *Handler) GetAuditLogDetail(c *gin.Context) {
	id := c.Param("id")
	audit := h.detector.GetAuditEngine()
	
	log, err := audit.GetLog(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"data": log})
}

func (h *Handler) GetAuditStatistics(c *gin.Context) {
	audit := h.detector.GetAuditEngine()
	stats := audit.GetStatistics()
	
	c.JSON(http.StatusOK, gin.H{"data": stats})
}

func (h *Handler) GetAuditTraceByDeadlock(c *gin.Context) {
	deadlockID := c.Param("deadlock_id")
	audit := h.detector.GetAuditEngine()
	
	logs := audit.GetTraceByDeadlock(deadlockID)
	
	c.JSON(http.StatusOK, gin.H{
		"data":  logs,
		"count": len(logs),
	})
}

func parseInt(s string) (int, error) {
	var val int
	_, err := fmt.Sscanf(s, "%d", &val)
	return val, err
}
