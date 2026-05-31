package api

import (
	"net/http"
	"redis-keyspace-notifier/config"
	"redis-keyspace-notifier/logger"
	"redis-keyspace-notifier/models"
	"redis-keyspace-notifier/processor"
	"redis-keyspace-notifier/redis"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

type Server struct {
	router     *gin.Engine
	store      *processor.EventStore
	processor  *processor.EventProcessor
	subscriber *redis.Subscriber
}

func NewServer(store *processor.EventStore, proc *processor.EventProcessor, sub *redis.Subscriber) *Server {
	gin.SetMode(gin.ReleaseMode)
	router := gin.New()
	router.Use(gin.Recovery())

	router.Use(cors.New(cors.Config{
		AllowAllOrigins:  true,
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
	}))

	server := &Server{
		router:     router,
		store:      store,
		processor:  proc,
		subscriber:  sub,
	}

	server.setupRoutes()

	return server
}

func (s *Server) setupRoutes() {
	api := s.router.Group("/api")
	{
		api.GET("/health", s.healthCheck)
		api.GET("/stats", s.getStats)
		api.GET("/events", s.getEvents)
		api.DELETE("/events", s.clearEvents)
		api.GET("/config", s.getConfig)
		api.PUT("/config", s.updateConfig)
		api.GET("/redis/status", s.getRedisStatus)
		api.GET("/analytics/latency", s.getLatencyStats)
		api.GET("/analytics/hotkeys", s.getHotKeys)
		api.GET("/analytics/sampling", s.getSamplingConfig)
		api.DELETE("/analytics", s.resetAnalytics)
	}
}

func (s *Server) healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "ok",
		"service": "redis-keyspace-notifier",
	})
}

func (s *Server) getStats(c *gin.Context) {
	stats := s.store.GetStats()
	retryCount := s.processor.GetRetryQueueSize()
	sortedCount := s.processor.GetSortedQueueSize()

	c.JSON(http.StatusOK, gin.H{
		"stats":         stats,
		"retry_pending": retryCount,
		"sorted_pending": sortedCount,
	})
}

func (s *Server) getEvents(c *gin.Context) {
	limit := 100
	if l := c.Query("limit"); l != "" {
		if n, err := parseLimit(l); err == nil {
			limit = n
		}
	}

	events := s.store.GetRecent(limit)
	c.JSON(http.StatusOK, gin.H{
		"events": events,
		"count":  len(events),
	})
}

func (s *Server) clearEvents(c *gin.Context) {
	s.store.Clear()
	c.JSON(http.StatusOK, gin.H{
		"message": "events cleared",
	})
}

func (s *Server) getConfig(c *gin.Context) {
	c.JSON(http.StatusOK, config.AppConfig)
}

func (s *Server) updateConfig(c *gin.Context) {
	var newConfig config.Config
	if err := c.ShouldBindJSON(&newConfig); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "invalid config: " + err.Error(),
		})
		return
	}

	config.AppConfig = newConfig
	c.JSON(http.StatusOK, gin.H{
		"message": "config updated",
	})
}

func (s *Server) getRedisStatus(c *gin.Context) {
	client := redis.GetClient()
	dbs := client.GetAllDBs()

	pendingCounts := make(map[int]int)
	if s.subscriber != nil {
		pendingCounts = s.subscriber.GetAllPendingCounts()
	}

	databases := make(map[int]gin.H)
	for db := range dbs {
		databases[db] = gin.H{
			"status":  "connected",
			"pending": pendingCounts[db],
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"address":   config.AppConfig.Redis.Address,
		"databases": databases,
	})
}

func (s *Server) Start() error {
	logger.Info("Starting HTTP server", zap.String("port", config.AppConfig.HTTPPort))
	return s.router.Run(config.AppConfig.HTTPPort)
}

func parseLimit(s string) (int, error) {
	n := 0
	for _, c := range s {
		if c < '0' || c > '9' {
			return 0, nil
		}
		n = n*10 + int(c-'0')
	}
	if n <= 0 || n > 1000 {
		return 100, nil
	}
	return n, nil
}

func (s *Server) getLatencyStats(c *gin.Context) {
	eventType := c.Query("type")

	var latencyStats models.LatencyStats
	if eventType != "" {
		latencyStats = s.processor.GetLatencyStatsByEventType(eventType)
	} else {
		latencyStats = s.processor.GetLatencyStats()
	}

	c.JSON(http.StatusOK, gin.H{
		"latency": latencyStats,
	})
}

func (s *Server) getHotKeys(c *gin.Context) {
	limit := 20
	if l := c.Query("limit"); l != "" {
		if n, err := parseLimit(l); err == nil {
			limit = n
		}
	}

	eventType := c.Query("type")

	var hotKeys []models.KeyEventCount
	if eventType != "" {
		hotKeys = s.processor.GetTopKeysByEventType(eventType, limit)
	} else {
		hotKeys = s.processor.GetTopKeys(limit)
	}

	c.JSON(http.StatusOK, gin.H{
		"hotkeys": hotKeys,
		"count":   len(hotKeys),
	})
}

func (s *Server) getSamplingConfig(c *gin.Context) {
	config := s.processor.GetSamplingConfig()
	c.JSON(http.StatusOK, config)
}

func (s *Server) resetAnalytics(c *gin.Context) {
	s.processor.ResetAnalytics()
	s.store.Clear()
	c.JSON(http.StatusOK, gin.H{
		"message": "analytics reset",
	})
}

var processorInstance *processor.EventProcessor
var storeInstance *processor.EventStore

func SetDependencies(proc *processor.EventProcessor, store *processor.EventStore) {
	processorInstance = proc
	storeInstance = store
}

type EventResponse struct {
	Events []models.KeyEvent `json:"events"`
	Count  int               `json:"count"`
}
