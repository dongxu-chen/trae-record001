package api

import (
	"db-guardian/internal/baseline"
	"db-guardian/internal/config"
	"db-guardian/internal/leak"
	"db-guardian/internal/lifecycle"
	"db-guardian/internal/limiter"
	"db-guardian/internal/pool"
	"db-guardian/internal/prewarm"
	"db-guardian/internal/proxy"
	"db-guardian/pkg/logger"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
)

type Server struct {
	cfg              config.APIConfig
	dbProxy          *proxy.MySQLProxy
	analyzer         *proxy.ConnectionAnalyzer
	connLimiter      *limiter.ConnectionLimiter
	clientLimiter    *limiter.ClientRateLimiter
	clientIDLimiter  *limiter.ClientIDLimiter
	leakDetector     *leak.LeakDetector
	baselineManager  *baseline.BaselineManager
	scalingPool      *pool.AutoScalingPool
	preWarmEngine    *prewarm.PreWarmEngine
	lifecycleTracker *lifecycle.ConnectionLifecycle
	log              *logger.Logger
	router           *gin.Engine
	httpServer       *http.Server
	wsClients        map[*websocket.Conn]bool
	wsMutex          sync.RWMutex
	upgrader         websocket.Upgrader
}

func NewServer(cfg config.APIConfig, dbProxy *proxy.MySQLProxy,
	analyzer *proxy.ConnectionAnalyzer,
	connLimiter *limiter.ConnectionLimiter,
	clientLimiter *limiter.ClientRateLimiter,
	clientIDLimiter *limiter.ClientIDLimiter,
	leakDetector *leak.LeakDetector,
	baselineManager *baseline.BaselineManager,
	scalingPool *pool.AutoScalingPool,
	preWarmEngine *prewarm.PreWarmEngine,
	lifecycleTracker *lifecycle.ConnectionLifecycle,
	log *logger.Logger) *Server {

	gin.SetMode(gin.ReleaseMode)
	router := gin.New()
	router.Use(gin.Recovery())

	router.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"*"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	return &Server{
		cfg:              cfg,
		dbProxy:          dbProxy,
		analyzer:         analyzer,
		connLimiter:      connLimiter,
		clientLimiter:    clientLimiter,
		clientIDLimiter:  clientIDLimiter,
		leakDetector:     leakDetector,
		baselineManager:  baselineManager,
		scalingPool:      scalingPool,
		preWarmEngine:    preWarmEngine,
		lifecycleTracker: lifecycleTracker,
		log:              log,
		router:           router,
		wsClients:        make(map[*websocket.Conn]bool),
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool {
				return true
			},
		},
	}
}

func (s *Server) Start() error {
	s.setupRoutes()

	addr := fmt.Sprintf("%s:%d", s.cfg.Host, s.cfg.Port)
	s.httpServer = &http.Server{
		Addr:    addr,
		Handler: s.router,
	}

	go s.broadcastStats()

	s.log.Info("API server starting on %s", addr)
	return s.httpServer.ListenAndServe()
}

func (s *Server) setupRoutes() {
	api := s.router.Group("/api")
	{
		api.GET("/stats", s.getStats)
		api.GET("/connections", s.getConnections)
		api.GET("/slow-connections", s.getSlowConnections)
		api.GET("/leak-candidates", s.getLeakCandidates)
		api.GET("/leak-records", s.getLeakRecords)
		api.GET("/alerts", s.getAlerts)
		api.GET("/trend", s.getTrend)
		api.GET("/limiter", s.getLimiterStats)
		api.GET("/clients", s.getClientStats)
		api.GET("/client-limits", s.getClientIDLimits)
		api.GET("/baseline", s.getBaselineStats)
		api.GET("/pool", s.getPoolStats)
		api.GET("/pool/scaling-history", s.getScalingHistory)
		api.GET("/pool/usage-history", s.getUsageHistory)
		api.GET("/prewarm", s.getPreWarmStats)
		api.GET("/lifecycle", s.getLifecycleStats)
		api.GET("/lifecycle/timeline/:id", s.getConnectionTimeline)
		api.GET("/lifecycle/recent", s.getRecentTimelines)
		api.GET("/lifecycle/active", s.getActiveLifecycles)
		api.GET("/lifecycle/phases", s.getPhaseDistribution)

		api.POST("/connections/release", s.releaseConnections)
		api.POST("/limiter/config", s.updateLimiterConfig)
		api.POST("/client-limits/:client_id", s.updateClientLimit)
		api.POST("/client-limits/:client_id/unblock", s.unblockClient)
		api.POST("/leak/close/:id", s.closeLeakConnection)
		api.POST("/baseline/:type/multiplier", s.updateBaselineMultiplier)
		api.POST("/pool/scale-up", s.scaleUpPool)
		api.POST("/pool/scale-down", s.scaleDownPool)
		api.POST("/prewarm", s.triggerPreWarm)
		api.POST("/prewarm/config", s.updatePreWarmConfig)
	}

	s.router.GET("/ws", s.handleWebSocket)
}

func (s *Server) getStats(c *gin.Context) {
	proxyStats := s.dbProxy.GetStats()
	analyzerStats := s.analyzer.GetStats()
	limiterStats := s.connLimiter.GetStats()
	clientIDLimiterStats := s.clientIDLimiter.GetStats()
	leakStats := s.leakDetector.GetStats()
	baselineStats := s.baselineManager.GetAllStats()

	c.JSON(http.StatusOK, gin.H{
		"proxy":              proxyStats,
		"analyzer":           analyzerStats,
		"limiter":            limiterStats,
		"client_id_limiter":  clientIDLimiterStats,
		"leak_detector":      leakStats,
		"baseline":           baselineStats,
		"timestamp":          time.Now(),
	})
}

func (s *Server) getConnections(c *gin.Context) {
	conns := s.dbProxy.GetConnections()
	result := make([]gin.H, 0, len(conns))

	for _, conn := range conns {
		conn.mu.Lock()
		result = append(result, gin.H{
			"id":          conn.ID,
			"client_ip":   conn.ClientIP,
			"client_id":   conn.ClientID,
			"app_name":    conn.AppName,
			"process_id":  conn.ProcessID,
			"username":    conn.Username,
			"start_time":  conn.StartTime,
			"last_active": conn.LastActive,
			"query_count": conn.QueryCount,
			"duration":    time.Since(conn.StartTime).Seconds(),
			"idle_time":   time.Since(conn.LastActive).Seconds(),
		})
		conn.mu.Unlock()
	}

	c.JSON(http.StatusOK, gin.H{
		"connections": result,
		"count":       len(result),
	})
}

func (s *Server) getSlowConnections(c *gin.Context) {
	slowConns := s.analyzer.GetSlowConnections()
	result := make([]gin.H, 0, len(slowConns))

	for _, sc := range slowConns {
		result = append(result, gin.H{
			"client_ip": sc.ClientIP,
			"timestamp": sc.Timestamp,
			"duration":  sc.Duration.Seconds(),
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"slow_connections": result,
		"count":            len(result),
	})
}

func (s *Server) getLeakCandidates(c *gin.Context) {
	leaks := s.analyzer.GetLeakCandidates()
	result := make([]gin.H, 0, len(leaks))

	for _, leak := range leaks {
		result = append(result, gin.H{
			"client_ip":        leak.ClientIP,
			"start_time":       leak.StartTime,
			"duration":         leak.Duration.Seconds(),
			"connection_count": leak.ConnectionCount,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"leak_candidates": result,
		"count":           len(result),
	})
}

func (s *Server) getLeakRecords(c *gin.Context) {
	leakRecords := s.leakDetector.GetLeakRecords()
	result := make([]gin.H, 0, len(leakRecords))

	for _, record := range leakRecords {
		result = append(result, gin.H{
			"id":              record.ID,
			"client_id":       record.ClientID,
			"client_ip":       record.ClientIP,
			"detected_time":   record.DetectedTime,
			"duration":        record.Duration.Seconds(),
			"query_count":     record.QueryCount,
			"idle_duration":   record.IdleDuration.Seconds(),
			"severity":        record.LeakSeverity,
			"app_name":        record.AppName,
			"process_id":      record.ProcessID,
		})
	}

	topClients := s.leakDetector.GetTopLeakClients(10)
	clientStats := make([]gin.H, 0, len(topClients))
	for _, client := range topClients {
		clientStats = append(clientStats, gin.H{
			"client_id":     client.ClientID,
			"total_leaks":   client.TotalLeaks,
			"active_leaks":  client.ActiveLeaks,
			"avg_duration":  client.AvgDuration.Seconds(),
			"last_leak":     client.LastLeakTime,
			"pattern":       client.LeakPattern,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"leak_records":  result,
		"count":         len(result),
		"top_clients":   clientStats,
	})
}

func (s *Server) getAlerts(c *gin.Context) {
	alerts := s.analyzer.GetStormAlerts()
	result := make([]gin.H, 0, len(alerts))

	for _, alert := range alerts {
		result = append(result, gin.H{
			"timestamp":   alert.Timestamp,
			"description": alert.Description,
			"severity":    alert.Severity,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"alerts": result,
		"count":  len(result),
	})
}

func (s *Server) getTrend(c *gin.Context) {
	trend := s.analyzer.GetConnectionTrend()
	c.JSON(http.StatusOK, trend)
}

func (s *Server) getLimiterStats(c *gin.Context) {
	stats := s.connLimiter.GetStats()
	c.JSON(http.StatusOK, stats)
}

func (s *Server) getClientStats(c *gin.Context) {
	stats := s.clientLimiter.GetAllStats()
	c.JSON(http.StatusOK, stats)
}

func (s *Server) getClientIDLimits(c *gin.Context) {
	stats := s.clientIDLimiter.GetAllClientStats()
	c.JSON(http.StatusOK, gin.H{
		"clients": stats,
		"count":   len(stats),
	})
}

func (s *Server) getBaselineStats(c *gin.Context) {
	stats := s.baselineManager.GetAllStats()
	c.JSON(http.StatusOK, stats)
}

func (s *Server) releaseConnections(c *gin.Context) {
	var req struct {
		Count int `json:"count"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		req.Count = 10
	}

	released := s.dbProxy.ReleaseIdleConnections(req.Count)
	c.JSON(http.StatusOK, gin.H{
		"released": released,
		"message":  fmt.Sprintf("Released %d idle connections", released),
	})
}

func (s *Server) updateLimiterConfig(c *gin.Context) {
	var req struct {
		MaxConnections int `json:"max_connections"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	s.connLimiter.SetMaxConnections(req.MaxConnections)
	s.clientIDLimiter.SetMaxTotalConnections(req.MaxConnections)
	c.JSON(http.StatusOK, gin.H{
		"message": fmt.Sprintf("Max connections updated to %d", req.MaxConnections),
	})
}

func (s *Server) updateClientLimit(c *gin.Context) {
	clientID := c.Param("client_id")

	var req struct {
		MaxConnections int `json:"max_connections"`
		RateLimit      int `json:"rate_limit"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	s.clientIDLimiter.SetClientLimit(clientID, req.MaxConnections, req.RateLimit)
	c.JSON(http.StatusOK, gin.H{
		"message": fmt.Sprintf("Client limit updated for %s", clientID),
	})
}

func (s *Server) unblockClient(c *gin.Context) {
	clientID := c.Param("client_id")

	success := s.clientIDLimiter.UnblockClient(clientID)
	if success {
		c.JSON(http.StatusOK, gin.H{
			"message": fmt.Sprintf("Client %s unblocked", clientID),
		})
	} else {
		c.JSON(http.StatusNotFound, gin.H{
			"error": fmt.Sprintf("Client %s not found", clientID),
		})
	}
}

func (s *Server) closeLeakConnection(c *gin.Context) {
	idParam := c.Param("id")
	var id uint64
	if _, err := fmt.Sscanf(idParam, "%d", &id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid connection ID"})
		return
	}

	success := s.leakDetector.ForceCloseLeakConnection(id)
	if success {
		c.JSON(http.StatusOK, gin.H{
			"message": fmt.Sprintf("Leak connection %d closed", id),
		})
	} else {
		c.JSON(http.StatusNotFound, gin.H{
			"error": fmt.Sprintf("Connection %d not found", id),
		})
	}
}

func (s *Server) updateBaselineMultiplier(c *gin.Context) {
	thresholdType := c.Param("type")

	var req struct {
		Multiplier float64 `json:"multiplier"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	s.baselineManager.SetMultiplier(baseline.ThresholdType(thresholdType), req.Multiplier)
	c.JSON(http.StatusOK, gin.H{
		"message": fmt.Sprintf("Baseline multiplier updated for %s", thresholdType),
	})
}

func (s *Server) getPoolStats(c *gin.Context) {
	stats := s.scalingPool.GetStats()
	c.JSON(http.StatusOK, stats)
}

func (s *Server) getScalingHistory(c *gin.Context) {
	history := s.scalingPool.GetScalingHistory()
	result := make([]gin.H, 0, len(history))
	for _, event := range history {
		result = append(result, gin.H{
			"timestamp":    event.Timestamp,
			"event_type":   event.EventType,
			"old_capacity": event.OldCapacity,
			"new_capacity": event.NewCapacity,
			"reason":       event.Reason,
			"active_conns": event.ActiveConns,
		})
	}
	c.JSON(http.StatusOK, gin.H{"events": result, "count": len(result)})
}

func (s *Server) getUsageHistory(c *gin.Context) {
	history := s.scalingPool.GetUsageHistory()
	result := make([]gin.H, 0, len(history))
	for _, snapshot := range history {
		result = append(result, gin.H{
			"timestamp":      snapshot.Timestamp,
			"active_conns":   snapshot.ActiveConns,
			"max_conns":      snapshot.MaxConns,
			"usage_ratio":    snapshot.UsageRatio,
		})
	}
	c.JSON(http.StatusOK, gin.H{"snapshots": result, "count": len(result)})
}

func (s *Server) getPreWarmStats(c *gin.Context) {
	stats := s.preWarmEngine.GetStats()
	c.JSON(http.StatusOK, stats)
}

func (s *Server) scaleUpPool(c *gin.Context) {
	var req struct {
		Factor float64 `json:"factor"`
		Reason string  `json:"reason"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		req.Factor = 1.5
		req.Reason = "Manual scale up"
	}
	if req.Factor <= 1.0 {
		req.Factor = 1.5
	}
	s.scalingPool.ScaleUp(req.Factor, req.Reason)
	c.JSON(http.StatusOK, gin.H{"message": fmt.Sprintf("Pool scaled up by factor %.2f", req.Factor)})
}

func (s *Server) scaleDownPool(c *gin.Context) {
	var req struct {
		Factor float64 `json:"factor"`
		Reason string  `json:"reason"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		req.Factor = 0.7
		req.Reason = "Manual scale down"
	}
	if req.Factor >= 1.0 {
		req.Factor = 0.7
	}
	s.scalingPool.ScaleDown(req.Factor, req.Reason)
	c.JSON(http.StatusOK, gin.H{"message": fmt.Sprintf("Pool scaled down by factor %.2f", req.Factor)})
}

func (s *Server) triggerPreWarm(c *gin.Context) {
	var req struct {
		Count int `json:"count"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		req.Count = 20
	}
	created := s.scalingPool.PreWarmConnections(req.Count)
	c.JSON(http.StatusOK, gin.H{
		"created": created,
		"message": fmt.Sprintf("Pre-warmed %d connections", created),
	})
}

func (s *Server) updatePreWarmConfig(c *gin.Context) {
	var req struct {
		TriggerRate float64 `json:"trigger_rate"`
		BatchSize   int     `json:"batch_size"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	s.preWarmEngine.SetConfig(req.TriggerRate, req.BatchSize)
	c.JSON(http.StatusOK, gin.H{
		"message": fmt.Sprintf("Pre-warm config updated: trigger_rate=%.2f, batch_size=%d", req.TriggerRate, req.BatchSize),
	})
}

func (s *Server) getLifecycleStats(c *gin.Context) {
	stats := s.lifecycleTracker.GetStats()
	c.JSON(http.StatusOK, stats)
}

func (s *Server) getConnectionTimeline(c *gin.Context) {
	idParam := c.Param("id")
	var id uint64
	if _, err := fmt.Sscanf(idParam, "%d", &id); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid connection ID"})
		return
	}

	timeline := s.lifecycleTracker.GetTimeline(id)
	if timeline == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Connection not found"})
		return
	}

	events := make([]gin.H, 0, len(timeline.Events))
	for _, event := range timeline.Events {
		events = append(events, gin.H{
			"event_type":   event.EventType,
			"timestamp":    event.Timestamp,
			"duration":     event.Duration.Seconds(),
			"detail":       event.Detail,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"connection_id": timeline.ConnectionID,
		"client_id":     timeline.ClientID,
		"client_ip":     timeline.ClientIP,
		"current_phase": timeline.CurrentPhase,
		"created_at":    timeline.CreatedAt,
		"duration":      timeline.Duration.Seconds(),
		"events":        events,
	})
}

func (s *Server) getRecentTimelines(c *gin.Context) {
	timelines := s.lifecycleTracker.GetRecentTimelines(50)
	result := make([]gin.H, 0, len(timelines))

	for _, tl := range timelines {
		events := make([]gin.H, 0, len(tl.Events))
		for _, event := range tl.Events {
			events = append(events, gin.H{
				"event_type": event.EventType,
				"timestamp":  event.Timestamp,
				"duration":   event.Duration.Seconds(),
				"detail":     event.Detail,
			})
		}
		result = append(result, gin.H{
			"connection_id": tl.ConnectionID,
			"client_id":     tl.ClientID,
			"client_ip":     tl.ClientIP,
			"current_phase": tl.CurrentPhase,
			"created_at":    tl.CreatedAt,
			"duration":      tl.Duration.Seconds(),
			"events":        events,
		})
	}

	c.JSON(http.StatusOK, gin.H{"timelines": result, "count": len(result)})
}

func (s *Server) getActiveLifecycles(c *gin.Context) {
	timelines := s.lifecycleTracker.GetActiveConnections()
	result := make([]gin.H, 0, len(timelines))

	for _, tl := range timelines {
		events := make([]gin.H, 0, len(tl.Events))
		for _, event := range tl.Events {
			events = append(events, gin.H{
				"event_type": event.EventType,
				"timestamp":  event.Timestamp,
				"detail":     event.Detail,
			})
		}
		result = append(result, gin.H{
			"connection_id": tl.ConnectionID,
			"client_id":     tl.ClientID,
			"current_phase": tl.CurrentPhase,
			"created_at":    tl.CreatedAt,
			"duration":      tl.Duration.Seconds(),
			"events":        events,
		})
	}

	c.JSON(http.StatusOK, gin.H{"connections": result, "count": len(result)})
}

func (s *Server) getPhaseDistribution(c *gin.Context) {
	stats := s.lifecycleTracker.GetPhaseStats()
	c.JSON(http.StatusOK, gin.H{"phases": stats})
}

func (s *Server) handleWebSocket(c *gin.Context) {
	conn, err := s.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		s.log.Error("WebSocket upgrade error: %v", err)
		return
	}

	s.wsMutex.Lock()
	s.wsClients[conn] = true
	s.wsMutex.Unlock()

	defer func() {
		s.wsMutex.Lock()
		delete(s.wsClients, conn)
		s.wsMutex.Unlock()
		conn.Close()
	}()

	for {
		_, _, err := conn.ReadMessage()
		if err != nil {
			break
		}
	}
}

func (s *Server) broadcastStats() {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		s.wsMutex.RLock()
		clients := make([]*websocket.Conn, 0, len(s.wsClients))
		for client := range s.wsClients {
			clients = append(clients, client)
		}
		s.wsMutex.RUnlock()

		if len(clients) == 0 {
			continue
		}

		proxyStats := s.dbProxy.GetStats()
		analyzerStats := s.analyzer.GetStats()
		limiterStats := s.clientIDLimiter.GetStats()
		leakStats := s.leakDetector.GetStats()
		poolStats := s.scalingPool.GetStats()
		preWarmStats := s.preWarmEngine.GetStats()
		lifecycleStats := s.lifecycleTracker.GetStats()

		data := map[string]interface{}{
			"type": "stats",
			"data": map[string]interface{}{
				"proxy":     proxyStats,
				"analyzer":  analyzerStats,
				"limiter":   limiterStats,
				"leak":      leakStats,
				"pool":      poolStats,
				"prewarm":   preWarmStats,
				"lifecycle": lifecycleStats,
				"timestamp": time.Now(),
			},
		}

		for _, client := range clients {
			if err := client.WriteJSON(data); err != nil {
				client.Close()
				s.wsMutex.Lock()
				delete(s.wsClients, client)
				s.wsMutex.Unlock()
			}
		}
	}
}

func (s *Server) Stop() {
	if s.httpServer != nil {
		s.httpServer.Close()
	}

	s.wsMutex.Lock()
	for client := range s.wsClients {
		client.Close()
		delete(s.wsClients, client)
	}
	s.wsMutex.Unlock()
}
