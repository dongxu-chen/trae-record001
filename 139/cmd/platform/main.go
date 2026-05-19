package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"prometheus-alert-tester/internal/platform/alert"
	"prometheus-alert-tester/internal/platform/cluster"
	"prometheus-alert-tester/internal/platform/fault"
	"prometheus-alert-tester/internal/platform/query"
)

var (
	port           = flag.String("port", "8080", "API server port")
	thanosEndpoint = flag.String("thanos", "http://localhost:10902", "Thanos Query endpoint")
	developMode    = flag.Bool("dev", false, "Enable development mode")
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type Platform struct {
	router        *gin.Engine
	queryService  *query.Service
	alertService  *alert.Service
	faultService  *fault.Service
	clusterMgr    *cluster.Manager
	wsHub         *WebSocketHub
}

type WebSocketHub struct {
	clients    map[*websocket.Conn]bool
	broadcast  chan []byte
	register   chan *websocket.Conn
	unregister chan *websocket.Conn
}

func NewWebSocketHub() *WebSocketHub {
	return &WebSocketHub{
		clients:    make(map[*websocket.Conn]bool),
		broadcast:  make(chan []byte),
		register:   make(chan *websocket.Conn),
		unregister: make(chan *websocket.Conn),
	}
}

func (h *WebSocketHub) Run() {
	for {
		select {
		case client := <-h.register:
			h.clients[client] = true
		case client := <-h.unregister:
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				client.Close()
			}
		case message := <-h.broadcast:
			for client := range h.clients {
				err := client.WriteMessage(websocket.TextMessage, message)
				if err != nil {
					client.Close()
					delete(h.clients, client)
				}
			}
		}
	}
}

func NewPlatform() *Platform {
	if *developMode {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.Default()

	router.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	qs := query.NewService(*thanosEndpoint)
	as := alert.NewService(qs)
	fs := fault.NewService()
	cm := cluster.NewManager()
	wsHub := NewWebSocketHub()

	go wsHub.Run()

	return &Platform{
		router:       router,
		queryService: qs,
		alertService: as,
		faultService: fs,
		clusterMgr:   cm,
		wsHub:        wsHub,
	}
}

func (p *Platform) SetupRoutes() {
	api := p.router.Group("/api/v1")

	queryGroup := api.Group("/query")
	{
		queryGroup.GET("", p.handleQuery)
		queryGroup.GET("/range", p.handleQueryRange)
		queryGroup.POST("/parse", p.handleParseQuery)
		queryGroup.GET("/series", p.handleSeries)
		queryGroup.GET("/labels", p.handleLabels)
	}

	alertGroup := api.Group("/alerts")
	{
		alertGroup.GET("", p.handleGetAlerts)
		alertGroup.POST("/test", p.handleTestAlert)
		alertGroup.GET("/history", p.handleAlertHistory)
	}

	rulesGroup := api.Group("/rules")
	{
		rulesGroup.GET("", p.handleGetRules)
		rulesGroup.POST("", p.handleUploadRules)
		rulesGroup.DELETE("/:id", p.handleDeleteRule)
	}

	faultGroup := api.Group("/faults")
	{
		faultGroup.GET("", p.handleGetFaults)
		faultGroup.POST("/start", p.handleStartFault)
		faultGroup.POST("/stop", p.handleStopFault)
		faultGroup.POST("/spike", p.handleSpikeFault)
		faultGroup.POST("/outage", p.handleOutageFault)
		faultGroup.POST("/degradation", p.handleDegradationFault)
	}

	clusterGroup := api.Group("/clusters")
	{
		clusterGroup.GET("", p.handleGetClusters)
		clusterGroup.POST("", p.handleAddCluster)
		clusterGroup.GET("/:id/health", p.handleClusterHealth)
		clusterGroup.POST("/:id/start", p.handleStartCluster)
		clusterGroup.POST("/:id/stop", p.handleStopCluster)
	}

	p.router.GET("/health", p.handleHealth)

	p.router.GET("/ws", p.handleWebSocket)

	p.router.Static("/ui", "./ui/dist")
	p.router.GET("/", func(c *gin.Context) {
		c.File("./ui/dist/index.html")
	})
}

func (p *Platform) handleQuery(c *gin.Context) {
	query := c.Query("query")
	timeStr := c.Query("time")

	result, err := p.queryService.Query(c.Request.Context(), query, timeStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (p *Platform) handleQueryRange(c *gin.Context) {
	query := c.Query("query")
	start := c.Query("start")
	end := c.Query("end")
	step := c.Query("step")

	result, err := p.queryService.QueryRange(c.Request.Context(), query, start, end, step)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (p *Platform) handleParseQuery(c *gin.Context) {
	var req struct {
		Query string `json:"query"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := p.queryService.ParseQuery(req.Query)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (p *Platform) handleSeries(c *gin.Context) {
	match := c.QueryArray("match[]")
	result, err := p.queryService.Series(c.Request.Context(), match)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (p *Platform) handleLabels(c *gin.Context) {
	result, err := p.queryService.Labels(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (p *Platform) handleGetAlerts(c *gin.Context) {
	alerts := p.alertService.GetActiveAlerts()
	c.JSON(http.StatusOK, gin.H{"data": alerts})
}

func (p *Platform) handleTestAlert(c *gin.Context) {
	var req alert.TestRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := p.alertService.TestAlert(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (p *Platform) handleAlertHistory(c *gin.Context) {
	history := p.alertService.GetHistory()
	c.JSON(http.StatusOK, gin.H{"data": history})
}

func (p *Platform) handleGetRules(c *gin.Context) {
	rules := p.alertService.GetRules()
	c.JSON(http.StatusOK, gin.H{"data": rules})
}

func (p *Platform) handleUploadRules(c *gin.Context) {
	var req alert.UploadRulesRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := p.alertService.UploadRules(req.YAML); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "success"})
}

func (p *Platform) handleDeleteRule(c *gin.Context) {
	id := c.Param("id")
	if err := p.alertService.DeleteRule(id); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "success"})
}

func (p *Platform) handleGetFaults(c *gin.Context) {
	faults := p.faultService.GetActiveFaults()
	c.JSON(http.StatusOK, gin.H{"data": faults})
}

func (p *Platform) handleStartFault(c *gin.Context) {
	var req fault.FaultConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	id, err := p.faultService.StartFault(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"id": id, "status": "started"})
}

func (p *Platform) handleStopFault(c *gin.Context) {
	var req struct {
		ID string `json:"id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := p.faultService.StopFault(req.ID); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "stopped"})
}

func (p *Platform) handleSpikeFault(c *gin.Context) {
	var req fault.SpikeConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	id, err := p.faultService.CreateSpike(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"id": id, "status": "created"})
}

func (p *Platform) handleOutageFault(c *gin.Context) {
	var req fault.OutageConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	id, err := p.faultService.CreateOutage(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"id": id, "status": "created"})
}

func (p *Platform) handleDegradationFault(c *gin.Context) {
	var req fault.DegradationConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	id, err := p.faultService.CreateDegradation(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"id": id, "status": "created"})
}

func (p *Platform) handleGetClusters(c *gin.Context) {
	clusters := p.clusterMgr.GetAllClusters()
	c.JSON(http.StatusOK, gin.H{"data": clusters})
}

func (p *Platform) handleAddCluster(c *gin.Context) {
	var cfg cluster.Config
	if err := c.ShouldBindJSON(&cfg); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := p.clusterMgr.AddCluster(&cfg); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "added"})
}

func (p *Platform) handleClusterHealth(c *gin.Context) {
	id := c.Param("id")
	health, err := p.clusterMgr.GetClusterHealth(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, health)
}

func (p *Platform) handleStartCluster(c *gin.Context) {
	id := c.Param("id")
	if err := p.clusterMgr.StartCluster(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "started"})
}

func (p *Platform) handleStopCluster(c *gin.Context) {
	id := c.Param("id")
	if err := p.clusterMgr.StopCluster(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "stopped"})
}

func (p *Platform) handleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"service": "thanos-alert-platform",
		"time":    time.Now().Format(time.RFC3339),
	})
}

func (p *Platform) handleWebSocket(c *gin.Context) {
	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}

	p.wsHub.register <- conn

	defer func() {
		p.wsHub.unregister <- conn
	}()

	for {
		_, _, err := conn.ReadMessage()
		if err != nil {
			break
		}
	}
}

func (p *Platform) Run(ctx context.Context) error {
	p.SetupRoutes()

	srv := &http.Server{
		Addr:    ":" + *port,
		Handler: p.router,
	}

	go func() {
		<-ctx.Done()
		log.Println("Shutting down server...")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			log.Printf("Server shutdown error: %v", err)
		}
	}()

	log.Printf("Server starting on :%s", *port)
	log.Printf("Thanos endpoint: %s", *thanosEndpoint)

	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		return fmt.Errorf("server error: %w", err)
	}

	return nil
}

func main() {
	flag.Parse()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigCh
		log.Println("Received shutdown signal")
		cancel()
	}()

	platform := NewPlatform()

	if err := platform.Run(ctx); err != nil {
		log.Fatalf("Platform error: %v", err)
	}
}
