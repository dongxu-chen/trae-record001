package api

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/autoscaler"
	"pulsar-backlog-manager/pkg/config"
	"pulsar-backlog-manager/pkg/deadletter"
	"pulsar-backlog-manager/pkg/delay"
	"pulsar-backlog-manager/pkg/monitor"
	"pulsar-backlog-manager/pkg/partition"
	"pulsar-backlog-manager/pkg/prediction"
	"pulsar-backlog-manager/pkg/pulsar"
	"pulsar-backlog-manager/pkg/ratelimiter"
	"pulsar-backlog-manager/pkg/replay"
	"pulsar-backlog-manager/pkg/strategy"
)

type Server struct {
	config        config.ServerConfig
	pulsar        *pulsar.Client
	monitorSvc    *monitor.Monitor
	autoScaler    *autoscaler.AutoScaler
	partitionMgr  *partition.Manager
	rateLimiter   *ratelimiter.RateLimiter
	predictor     *prediction.Predictor
	strategyMgr   *strategy.Manager
	auditLog      *audit.AuditLogger
	dlqHandler    *deadletter.DeadLetterHandler
	replayMgr     *replay.ReplayManager
	delayProc     *delay.DelayProcessor
	router        *gin.Engine
}

func NewServer(
	cfg config.ServerConfig,
	pulsarClient *pulsar.Client,
	monitorSvc *monitor.Monitor,
	autoScaler *autoscaler.AutoScaler,
	partitionMgr *partition.Manager,
	rateLimiter *ratelimiter.RateLimiter,
	predictor *prediction.Predictor,
	strategyMgr *strategy.Manager,
	auditLog *audit.AuditLogger,
	dlqHandler *deadletter.DeadLetterHandler,
	replayMgr *replay.ReplayManager,
	delayProc *delay.DelayProcessor,
) *Server {
	server := &Server{
		config:       cfg,
		pulsar:       pulsarClient,
		monitorSvc:   monitorSvc,
		autoScaler:   autoScaler,
		partitionMgr: partitionMgr,
		rateLimiter:  rateLimiter,
		predictor:    predictor,
		strategyMgr:  strategyMgr,
		auditLog:     auditLog,
		dlqHandler:   dlqHandler,
		replayMgr:    replayMgr,
		delayProc:    delayProc,
	}
	server.setupRoutes()
	return server
}

func (s *Server) setupRoutes() {
	r := gin.Default()

	if s.config.EnableCORS {
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
	}

	api := r.Group("/api/v1")
	{
		api.GET("/health", s.HealthCheck)

		topics := api.Group("/topics")
		{
			topics.GET("", s.ListTopics)
			topics.POST("", s.AddTopic)
			topics.DELETE("/:topic", s.RemoveTopic)
			topics.GET("/:topic/backlog", s.GetTopicBacklog)
			topics.GET("/:topic/history", s.GetBacklogHistory)
		}

		autoscale := api.Group("/autoscale")
		{
			autoscale.POST("/:topic/:subscription", s.SetConsumerCount)
			autoscale.GET("/:topic/:subscription", s.GetConsumerCount)
			autoscale.GET("/:topic/:subscription/state", s.GetScaleState)
		}

		partitions := api.Group("/partitions")
		{
			partitions.POST("/:topic", s.SetPartitionCount)
			partitions.GET("/:topic", s.GetPartitionCount)
		}

		ratelimit := api.Group("/ratelimit")
		{
			ratelimit.POST("/:topic", s.SetRateLimit)
			ratelimit.GET("/:topic", s.GetRateLimit)
			ratelimit.POST("/:topic/subscription/:subscription", s.SetSubscriptionRateLimit)
			ratelimit.GET("/:topic/subscription/:subscription", s.GetSubscriptionRateLimit)
			ratelimit.GET("/:topic/status", s.GetThrottleStatus)
		}

		predictions := api.Group("/predictions")
		{
			predictions.GET("/:topic", s.GetPrediction)
		}

		strategies := api.Group("/strategies")
		{
			strategies.GET("", s.ListStrategies)
			strategies.POST("", s.SetStrategy)
			strategies.DELETE("/:topic", s.DeleteStrategy)
			strategies.GET("/:topic", s.GetStrategy)
		}

		dlq := api.Group("/dlq")
		{
			dlq.GET("/stats", s.GetDLQAllStats)
			dlq.GET("/stats/:topic/:subscription", s.GetDLQStats)
			dlq.POST("/config/:topic/:subscription", s.ConfigureDLQ)
			dlq.POST("/retry/:topic/:subscription", s.RetryFromDLQ)
			dlq.POST("/enable/:topic/:subscription", s.EnableDLQ)
			dlq.POST("/disable/:topic/:subscription", s.DisableDLQ)
		}

		replayGroup := api.Group("/replay")
		{
			replayGroup.POST("", s.ReplayMessages)
			replayGroup.POST("/last/:topic", s.ReplayLastN)
			replayGroup.GET("/status/:topic", s.GetReplayStatus)
			replayGroup.GET("/history", s.GetReplayHistory)
			replayGroup.POST("/cancel/:topic", s.CancelReplay)
		}

		delayGroup := api.Group("/delay")
		{
			delayGroup.GET("/stats", s.GetDelayAllStats)
			delayGroup.GET("/stats/:topic", s.GetDelayStats)
			delayGroup.POST("/register/:topic/:subscription", s.RegisterSubscription)
			delayGroup.POST("/pause/:topic/:subscription", s.PauseSubscription)
			delayGroup.POST("/resume/:topic/:subscription", s.ResumeSubscription)
		}

		auditLogs := api.Group("/audit")
		{
			auditLogs.GET("", s.GetAuditLogs)
			auditLogs.GET("/topic/:topic", s.GetAuditLogsByTopic)
		}
	}

	s.router = r
}

func (s *Server) Start() error {
	return s.router.Run(":" + s.config.Port)
}

func (s *Server) HealthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func (s *Server) ListTopics(c *gin.Context) {
	topics := s.monitorSvc.GetTopics()
	c.JSON(http.StatusOK, gin.H{"topics": topics})
}

func (s *Server) AddTopic(c *gin.Context) {
	var req struct {
		Topic string `json:"topic" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	s.monitorSvc.AddTopic(req.Topic)
	c.JSON(http.StatusOK, gin.H{"status": "added"})
}

func (s *Server) RemoveTopic(c *gin.Context) {
	topic := c.Param("topic")
	s.monitorSvc.RemoveTopic(topic)
	c.JSON(http.StatusOK, gin.H{"status": "removed"})
}

func (s *Server) GetTopicBacklog(c *gin.Context) {
	backlogs := s.monitorSvc.GetCurrentBacklogs()
	c.JSON(http.StatusOK, gin.H{"backlogs": backlogs})
}

func (s *Server) GetBacklogHistory(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.DefaultQuery("subscription", "default")
	history := s.monitorSvc.GetBacklogHistory(topic, subscription)
	c.JSON(http.StatusOK, gin.H{"history": history})
}

func (s *Server) SetConsumerCount(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	var req struct {
		Count int `json:"count" binding:"required,min=1"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if err := s.autoScaler.SetConsumerCount(topic, subscription, req.Count); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "updated"})
}

func (s *Server) GetConsumerCount(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	count := s.autoScaler.GetConsumerCount(topic, subscription)
	c.JSON(http.StatusOK, gin.H{"count": count})
}

func (s *Server) SetPartitionCount(c *gin.Context) {
	topic := c.Param("topic")
	var req struct {
		Count int `json:"count" binding:"required,min=1"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	s.partitionMgr.SetPartitionCount(topic, req.Count)
	c.JSON(http.StatusOK, gin.H{"status": "updated"})
}

func (s *Server) GetPartitionCount(c *gin.Context) {
	topic := c.Param("topic")
	count := s.partitionMgr.GetPartitionCount(topic)
	c.JSON(http.StatusOK, gin.H{"count": count})
}

func (s *Server) SetRateLimit(c *gin.Context) {
	topic := c.Param("topic")
	var req struct {
		Rate float64 `json:"rate" binding:"required,min=1"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	s.rateLimiter.SetRateLimit(topic, req.Rate)
	c.JSON(http.StatusOK, gin.H{"status": "updated"})
}

func (s *Server) GetRateLimit(c *gin.Context) {
	topic := c.Param("topic")
	rate := s.rateLimiter.GetCurrentRate(topic)
	c.JSON(http.StatusOK, gin.H{"rate": rate})
}

func (s *Server) GetPrediction(c *gin.Context) {
	topic := c.Param("topic")
	prediction := s.predictor.GetPrediction(topic)
	if prediction == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "no prediction available"})
		return
	}
	c.JSON(http.StatusOK, prediction)
}

func (s *Server) ListStrategies(c *gin.Context) {
	strategies := s.strategyMgr.GetAllStrategies()
	c.JSON(http.StatusOK, gin.H{"strategies": strategies})
}

func (s *Server) SetStrategy(c *gin.Context) {
	var strategy strategy.Strategy
	if err := c.ShouldBindJSON(&strategy); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	s.strategyMgr.SetStrategy(&strategy)
	c.JSON(http.StatusOK, gin.H{"status": "updated"})
}

func (s *Server) DeleteStrategy(c *gin.Context) {
	topic := c.Param("topic")
	s.strategyMgr.DeleteStrategy(topic)
	c.JSON(http.StatusOK, gin.H{"status": "deleted"})
}

func (s *Server) GetStrategy(c *gin.Context) {
	topic := c.Param("topic")
	strategy := s.strategyMgr.GetStrategy(topic)
	c.JSON(http.StatusOK, strategy)
}

func (s *Server) GetAuditLogs(c *gin.Context) {
	limit := 100
	offset := 0
	logs := s.auditLog.GetLogs(limit, offset)
	c.JSON(http.StatusOK, gin.H{"logs": logs})
}

func (s *Server) GetAuditLogsByTopic(c *gin.Context) {
	topic := c.Param("topic")
	logs := s.auditLog.GetLogsByTopic(topic, 100)
	c.JSON(http.StatusOK, gin.H{"logs": logs})
}

func (s *Server) GetScaleState(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	current, target, direction := s.autoScaler.GetScaleState(topic, subscription)
	directionStr := "none"
	if direction == 1 {
		directionStr = "scale_up"
	} else if direction == 2 {
		directionStr = "scale_down"
	}
	c.JSON(http.StatusOK, gin.H{
		"current_count": current,
		"target_count":  target,
		"direction":     directionStr,
	})
}

func (s *Server) SetSubscriptionRateLimit(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	var req struct {
		Rate float64 `json:"rate" binding:"required,min=1"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	s.rateLimiter.SetSubscriptionRateLimit(topic, subscription, req.Rate)
	c.JSON(http.StatusOK, gin.H{"status": "updated"})
}

func (s *Server) GetSubscriptionRateLimit(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	rate := s.rateLimiter.GetSubscriptionRate(topic, subscription)
	c.JSON(http.StatusOK, gin.H{"rate": rate})
}

func (s *Server) GetThrottleStatus(c *gin.Context) {
	topic := c.Param("topic")
	status := s.rateLimiter.GetThrottleStatus(topic)
	c.JSON(http.StatusOK, status)
}

func (s *Server) GetDLQAllStats(c *gin.Context) {
	stats := s.dlqHandler.GetAllStats()
	c.JSON(http.StatusOK, gin.H{"stats": stats})
}

func (s *Server) GetDLQStats(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	stats := s.dlqHandler.GetStats(topic, subscription)
	if stats == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "DLQ not configured"})
		return
	}
	c.JSON(http.StatusOK, stats)
}

func (s *Server) ConfigureDLQ(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	var req struct {
		MaxRedeliveries int    `json:"max_redeliveries" binding:"required,min=1"`
		DLQTopic        string `json:"dlq_topic"`
		RetryTopic      string `json:"retry_topic"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	s.dlqHandler.ConfigureDLQ(topic, subscription, req.MaxRedeliveries, req.DLQTopic, req.RetryTopic)
	c.JSON(http.StatusOK, gin.H{"status": "configured"})
}

func (s *Server) RetryFromDLQ(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	var req struct {
		MaxMessages int `json:"max_messages"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		req.MaxMessages = 100
	}
	if req.MaxMessages <= 0 {
		req.MaxMessages = 100
	}
	retried, err := s.dlqHandler.RetryFromDLQ(topic, subscription, req.MaxMessages)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"retried": retried})
}

func (s *Server) EnableDLQ(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	s.dlqHandler.EnableDLQ(topic, subscription)
	c.JSON(http.StatusOK, gin.H{"status": "enabled"})
}

func (s *Server) DisableDLQ(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	s.dlqHandler.DisableDLQ(topic, subscription)
	c.JSON(http.StatusOK, gin.H{"status": "disabled"})
}

func (s *Server) ReplayMessages(c *gin.Context) {
	var req replay.ReplayRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	result, err := s.replayMgr.ReplayMessages(req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) ReplayLastN(c *gin.Context) {
	topic := c.Param("topic")
	var req struct {
		Count       int    `json:"count" binding:"required,min=1"`
		TargetTopic string `json:"target_topic"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	result, err := s.replayMgr.ReplayMessages(replay.ReplayRequest{
		Topic:       topic,
		Subscription: "default",
		MaxMessages: req.Count,
		TargetTopic: req.TargetTopic,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) GetReplayStatus(c *gin.Context) {
	topic := c.Param("topic")
	status := s.replayMgr.GetReplayStatus(topic)
	c.JSON(http.StatusOK, status)
}

func (s *Server) GetReplayHistory(c *gin.Context) {
	topic := c.DefaultQuery("topic", "")
	history := s.replayMgr.GetReplayHistory(topic)
	c.JSON(http.StatusOK, gin.H{"history": history})
}

func (s *Server) CancelReplay(c *gin.Context) {
	topic := c.Param("topic")
	s.replayMgr.CancelReplay(topic)
	c.JSON(http.StatusOK, gin.H{"status": "cancelled"})
}

func (s *Server) GetDelayAllStats(c *gin.Context) {
	stats := s.delayProc.GetAllStats()
	c.JSON(http.StatusOK, gin.H{"stats": stats})
}

func (s *Server) GetDelayStats(c *gin.Context) {
	topic := c.Param("topic")
	stats := s.delayProc.GetStats(topic)
	if stats == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "delay processor not configured"})
		return
	}
	c.JSON(http.StatusOK, stats)
}

func (s *Server) RegisterSubscription(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	var req struct {
		Priority string `json:"priority" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	var priority delay.SubscriptionPriority
	switch req.Priority {
	case "core":
		priority = delay.PriorityCore
	case "non_core", "noncore":
		priority = delay.PriorityNonCore
	default:
		priority = delay.PriorityNormal
	}
	s.delayProc.RegisterSubscription(topic, subscription, priority)
	c.JSON(http.StatusOK, gin.H{"status": "registered"})
}

func (s *Server) PauseSubscription(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	if err := s.delayProc.PauseSubscription(topic, subscription); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "paused"})
}

func (s *Server) ResumeSubscription(c *gin.Context) {
	topic := c.Param("topic")
	subscription := c.Param("subscription")
	if err := s.delayProc.ResumeSubscription(topic, subscription); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "resumed"})
}

var _ = time.Time{}
