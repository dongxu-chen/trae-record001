package api

import (
	"context"
	"net/http"
	"strconv"
	"time"

	ch "ch-lifecycle/internal/clickhouse"
	"ch-lifecycle/internal/lifecycle"
	"ch-lifecycle/internal/policy"
	"ch-lifecycle/internal/advisor"
	"ch-lifecycle/internal/tiering"
	"ch-lifecycle/internal/scheduler"
	"ch-lifecycle/internal/monitor"
	"ch-lifecycle/internal/archive"
	"ch-lifecycle/internal/router"
	"ch-lifecycle/internal/simulator"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"go.uber.org/zap"
)

type Handler struct {
	client    *ch.Client
	store     *policy.Store
	manager   *lifecycle.Manager
	tiering   *tiering.Engine
	scheduler *scheduler.Scheduler
	advisor   *advisor.Advisor
	monitor   *monitor.Monitor
	archiver  *archive.Archiver
	router    *router.QueryRouter
	simulator *simulator.Simulator
	logger    *zap.Logger
}

func NewHandler(
	client *ch.Client,
	store *policy.Store,
	manager *lifecycle.Manager,
	tieringEngine *tiering.Engine,
	sched *scheduler.Scheduler,
	adv *advisor.Advisor,
	mon *monitor.Monitor,
	arch *archive.Archiver,
	rtr *router.QueryRouter,
	sim *simulator.Simulator,
	logger *zap.Logger,
) *Handler {
	return &Handler{
		client:    client,
		store:     store,
		manager:   manager,
		tiering:   tieringEngine,
		scheduler: sched,
		advisor:   adv,
		monitor:   mon,
		archiver:  arch,
		router:    rtr,
		simulator: sim,
		logger:    logger,
	}
}

func (h *Handler) SetupRouter() *gin.Engine {
	r := gin.Default()
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))
	api := r.Group("/api/v1")
	{
		policies := api.Group("/policies")
		{
			policies.GET("", h.listPolicies)
			policies.GET("/:id", h.getPolicy)
			policies.POST("", h.createPolicy)
			policies.PUT("/:id", h.updatePolicy)
			policies.DELETE("/:id", h.deletePolicy)
		}
		lifecycleGroup := api.Group("/lifecycle")
		{
			lifecycleGroup.GET("/evaluate", h.evaluateLifecycle)
			lifecycleGroup.POST("/execute", h.executeLifecycle)
			lifecycleGroup.GET("/expired", h.getExpiredPartitions)
		}
		tieringGroup := api.Group("/tiering")
		{
			tieringGroup.GET("/plan", h.planTiering)
			tieringGroup.POST("/execute", h.executeTiering)
			tieringGroup.GET("/status", h.getTierStatus)
		}
		schedulerGroup := api.Group("/scheduler")
		{
			schedulerGroup.GET("/status", h.getSchedulerStatus)
			schedulerGroup.POST("/trigger/:jobType", h.triggerJob)
		}
		advisorGroup := api.Group("/advisor")
		{
			advisorGroup.GET("/analyze/:database/:table", h.analyzeTable)
			advisorGroup.GET("/analyze/:database", h.analyzeDatabase)
		}
		cluster := api.Group("/cluster")
		{
			cluster.GET("/tables", h.getTables)
			cluster.GET("/tables/:database/:table/partitions", h.getTablePartitions)
			cluster.GET("/disks", h.getDisks)
			cluster.GET("/storage-policies", h.getStoragePolicies)
		}
		monitorGroup := api.Group("/monitor")
		{
			monitorGroup.GET("/snapshots", h.getSnapshots)
			monitorGroup.GET("/snapshot/current", h.getCurrentSnapshot)
		}
		archiveGroup := api.Group("/archive")
		{
			archiveGroup.GET("", h.listArchives)
			archiveGroup.GET("/:id", h.getArchive)
			archiveGroup.POST("", h.createArchive)
			archiveGroup.POST("/:id/export", h.exportArchive)
			archiveGroup.POST("/:id/restore", h.restoreArchive)
			archiveGroup.POST("/:id/verify", h.verifyArchive)
			archiveGroup.DELETE("/:id", h.deleteArchive)
			archiveGroup.GET("/config", h.getArchiveConfig)
		}
		routerGroup := api.Group("/router")
		{
			routerGroup.POST("/analyze", h.analyzeQuery)
			routerGroup.POST("/route", h.routeQuery)
			routerGroup.POST("/execute", h.executeRoutedQuery)
			routerGroup.GET("/rules", h.listRoutingRules)
			routerGroup.POST("/rules", h.addRoutingRule)
			routerGroup.DELETE("/rules/:id", h.deleteRoutingRule)
			routerGroup.GET("/config", h.getRouterConfig)
			routerGroup.PUT("/config", h.updateRouterConfig)
		}
		simulatorGroup := api.Group("/simulator")
		{
			simulatorGroup.POST("/simulate", h.simulateLifecycle)
			simulatorGroup.POST("/savings", h.calculateSavings)
		}
	}
	r.Static("/dashboard", "./web/dist")
	r.NoRoute(func(c *gin.Context) {
		c.File("./web/dist/index.html")
	})
	return r
}

func (h *Handler) listPolicies(c *gin.Context) {
	policies, err := h.store.List()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"policies": policies})
}

func (h *Handler) getPolicy(c *gin.Context) {
	id := c.Param("id")
	p, err := h.store.Get(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, p)
}

func (h *Handler) createPolicy(c *gin.Context) {
	var p policy.TTLPolicy
	if err := c.ShouldBindJSON(&p); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	created, err := h.store.Create(&p)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, created)
}

func (h *Handler) updatePolicy(c *gin.Context) {
	id := c.Param("id")
	var p policy.TTLPolicy
	if err := c.ShouldBindJSON(&p); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	updated, err := h.store.Update(id, &p)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, updated)
}

func (h *Handler) deletePolicy(c *gin.Context) {
	id := c.Param("id")
	if err := h.store.Delete(id); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "deleted"})
}

func (h *Handler) evaluateLifecycle(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Minute)
	defer cancel()
	dryRun := c.Query("dry_run") == "true"
	if dryRun {
		result, err := h.manager.Evaluate(ctx)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		c.JSON(http.StatusOK, result)
		return
	}
	result, err := h.manager.Execute(ctx, false)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *Handler) executeLifecycle(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 60*time.Minute)
	defer cancel()
	dryRun := c.Query("dry_run") == "true"
	result, err := h.manager.Execute(ctx, dryRun)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *Handler) getExpiredPartitions(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Minute)
	defer cancel()
	database := c.Query("database")
	table := c.Query("table")
	retentionStr := c.DefaultQuery("retention_days", "90")
	retentionDays, _ := strconv.Atoi(retentionStr)
	if database == "" || table == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "database and table are required"})
		return
	}
	expired, err := h.manager.ExpirePartitions(ctx, database, table, retentionDays)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"expired": expired, "count": len(expired)})
}

func (h *Handler) planTiering(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Minute)
	defer cancel()
	plans, err := h.tiering.Plan(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"plans": plans, "count": len(plans)})
}

func (h *Handler) executeTiering(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 60*time.Minute)
	defer cancel()
	dryRun := c.Query("dry_run") == "true"
	result, err := h.tiering.Execute(ctx, dryRun)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *Handler) getTierStatus(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()
	statuses, err := h.tiering.GetTierStatus(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"tiers": statuses})
}

func (h *Handler) getSchedulerStatus(c *gin.Context) {
	statuses := h.scheduler.GetStatuses()
	c.JSON(http.StatusOK, gin.H{"jobs": statuses})
}

func (h *Handler) triggerJob(c *gin.Context) {
	jobType := scheduler.JobType(c.Param("jobType"))
	if err := h.scheduler.TriggerJob(jobType); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "triggered", "job": jobType})
}

func (h *Handler) analyzeTable(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Minute)
	defer cancel()
	database := c.Param("database")
	table := c.Param("table")
	analysis, err := h.advisor.AnalyzeTable(ctx, database, table)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, analysis)
}

func (h *Handler) analyzeDatabase(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Minute)
	defer cancel()
	database := c.Param("database")
	analyses, err := h.advisor.AnalyzeDatabase(ctx, database)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"analyses": analyses})
}

func (h *Handler) getTables(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()
	database := c.Query("database")
	if database == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "database query param required"})
		return
	}
	tables, err := h.client.GetTables(ctx, database)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"tables": tables})
}

func (h *Handler) getTablePartitions(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()
	database := c.Param("database")
	table := c.Param("table")
	partitions, err := h.client.GetPartitions(ctx, database, table)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"partitions": partitions, "count": len(partitions)})
}

func (h *Handler) getDisks(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()
	disks, err := h.client.GetDisks(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"disks": disks})
}

func (h *Handler) getStoragePolicies(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()
	policies, err := h.client.GetStoragePolicies(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"policies": policies})
}

func (h *Handler) getSnapshots(c *gin.Context) {
	snapshots := h.monitor.GetSnapshots()
	c.JSON(http.StatusOK, gin.H{"snapshots": snapshots})
}

func (h *Handler) getCurrentSnapshot(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()
	snapshot, err := h.monitor.CollectSnapshot(ctx)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, snapshot)
}

func (h *Handler) listArchives(c *gin.Context) {
	archives, err := h.archiver.ListArchives()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"archives": archives})
}

func (h *Handler) getArchive(c *gin.Context) {
	id := c.Param("id")
	archive, err := h.archiver.GetArchive(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, archive)
}

func (h *Handler) createArchive(c *gin.Context) {
	var req struct {
		Database  string `json:"database" binding:"required"`
		Table     string `json:"table" binding:"required"`
		Partition string `json:"partition" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Minute)
	defer cancel()
	job, err := h.archiver.ExportPartition(ctx, req.Database, req.Table, req.Partition)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, job)
}

func (h *Handler) exportArchive(c *gin.Context) {
	id := c.Param("id")
	job, err := h.archiver.GetArchive(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Minute)
	defer cancel()
	_, err = h.archiver.ExportPartition(ctx, job.Database, job.Table, job.Partition)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "export started"})
}

func (h *Handler) restoreArchive(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Minute)
	defer cancel()
	if err := h.archiver.RestoreArchive(ctx, id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "restored"})
}

func (h *Handler) verifyArchive(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()
	verified, err := h.archiver.VerifyArchive(ctx, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"verified": verified})
}

func (h *Handler) deleteArchive(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
	defer cancel()
	if err := h.archiver.DeleteArchive(ctx, id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "deleted"})
}

func (h *Handler) getArchiveConfig(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"enabled": true,
		"endpoint": "s3.amazonaws.com",
		"bucket": "clickhouse-archives",
		"path_prefix": "clickhouse-archives",
		"export_format": "Parquet",
		"archive_cron": "0 0 4 * * *",
	})
}

func (h *Handler) analyzeQuery(c *gin.Context) {
	var req struct {
		SQL      string `json:"sql" binding:"required"`
		Database string `json:"database" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	info, err := h.router.AnalyzeQuery(req.SQL, req.Database)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, info)
}

func (h *Handler) routeQuery(c *gin.Context) {
	var req struct {
		SQL      string `json:"sql" binding:"required"`
		Database string `json:"database" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	result, err := h.router.RouteQuery(req.SQL, req.Database)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *Handler) executeRoutedQuery(c *gin.Context) {
	var req struct {
		SQL      string                `json:"sql" binding:"required"`
		Database string                `json:"database" binding:"required"`
		Source   router.QuerySource    `json:"source"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	source := req.Source
	if source == "" {
		routeResult, err := h.router.RouteQuery(req.SQL, req.Database)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		source = routeResult.Source
	}
	rows, err := h.router.ExecuteQuery(req.SQL, req.Database, source)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	defer rows.Close()
	var results []map[string]interface{}
	columns, _ := rows.Columns()
	for rows.Next() {
		row := make(map[string]interface{})
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range columns {
			valuePtrs[i] = &values[i]
		}
		if err := rows.Scan(valuePtrs...); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		for i, col := range columns {
			row[col] = values[i]
		}
		results = append(results, row)
	}
	c.JSON(http.StatusOK, gin.H{
		"source":  source,
		"results": results,
		"count":   len(results),
	})
}

func (h *Handler) listRoutingRules(c *gin.Context) {
	rules, err := h.router.ListRules()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"rules": rules})
}

func (h *Handler) addRoutingRule(c *gin.Context) {
	var rule router.RoutingRule
	if err := c.ShouldBindJSON(&rule); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	created, err := h.router.AddRule(&rule)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusCreated, created)
}

func (h *Handler) deleteRoutingRule(c *gin.Context) {
	id := c.Param("id")
	if err := h.router.DeleteRule(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "deleted"})
}

func (h *Handler) getRouterConfig(c *gin.Context) {
	config := h.router.GetConfig()
	c.JSON(http.StatusOK, config)
}

func (h *Handler) updateRouterConfig(c *gin.Context) {
	var config router.RoutingConfig
	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	h.router.UpdateConfig(config)
	c.JSON(http.StatusOK, config)
}

func (h *Handler) simulateLifecycle(c *gin.Context) {
	var req struct {
		Database     string  `json:"database" binding:"required"`
		Table        string  `json:"table" binding:"required"`
		DaysToSimulate int   `json:"days_to_simulate" binding:"required,min=1,max=3650"`
		DailyGrowthRate float64 `json:"daily_growth_rate" default:"0.001"`
		CompressionRatio float64 `json:"compression_ratio" default:"1.0"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	config := simulator.SimulationConfig{
		DaysToSimulate:   req.DaysToSimulate,
		DailyGrowthRate:  req.DailyGrowthRate,
		CompressionRatio: req.CompressionRatio,
		TZ:               "UTC",
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Minute)
	defer cancel()
	result, err := h.simulator.Simulate(ctx, req.Database, req.Table, config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *Handler) calculateSavings(c *gin.Context) {
	var req struct {
		Database     string  `json:"database" binding:"required"`
		Table        string  `json:"table" binding:"required"`
		DaysToSimulate int   `json:"days_to_simulate" binding:"required"`
		DailyGrowthRate float64 `json:"daily_growth_rate"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	config := simulator.SimulationConfig{
		DaysToSimulate:  req.DaysToSimulate,
		DailyGrowthRate: req.DailyGrowthRate,
		CompressionRatio: 1.0,
		TZ:              "UTC",
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Minute)
	defer cancel()
	result, err := h.simulator.Simulate(ctx, req.Database, req.Table, config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	savings := simulator.CalculateSavings(result)
	charts := simulator.GenerateChartsData(result)
	c.JSON(http.StatusOK, gin.H{
		"savings": savings,
		"charts":  charts,
		"result":  result,
	})
}
