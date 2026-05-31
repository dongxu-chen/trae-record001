package api

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"etcd-backup-manager/internal/backup"
	"etcd-backup-manager/internal/cluster"
	"etcd-backup-manager/internal/cost"
	"etcd-backup-manager/internal/drill"
	"etcd-backup-manager/internal/encryption"
	"etcd-backup-manager/internal/replication"
	"etcd-backup-manager/internal/scheduler"
	"etcd-backup-manager/pkg/models"
)

type Handler struct {
	clusterMgr  *cluster.Manager
	backupMgr   *backup.Manager
	scheduler   *scheduler.Scheduler
	kmsEncrypt  *encryption.KMSEncryptor
	replicator  *replication.Replicator
	drillSched  *drill.DrillScheduler
	costAnalyzer *cost.Analyzer
}

func NewHandler(
	clusterMgr *cluster.Manager,
	backupMgr *backup.Manager,
	scheduler *scheduler.Scheduler,
	kmsEncrypt *encryption.KMSEncryptor,
	replicator *replication.Replicator,
	drillSched *drill.DrillScheduler,
	costAnalyzer *cost.Analyzer,
) *Handler {
	return &Handler{
		clusterMgr:  clusterMgr,
		backupMgr:   backupMgr,
		scheduler:   scheduler,
		kmsEncrypt:  kmsEncrypt,
		replicator:  replicator,
		drillSched:  drillSched,
		costAnalyzer: costAnalyzer,
	}
}

func (h *Handler) SetupRouter() *gin.Engine {
	r := gin.Default()

	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"*"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	api := r.Group("/api/v1")
	{
		api.GET("/health", h.healthCheck)

		clusters := api.Group("/clusters")
		{
			clusters.GET("", h.listClusters)
			clusters.GET("/:id", h.getCluster)
			clusters.GET("/:id/status", h.getClusterStatus)
			clusters.POST("", h.createCluster)
			clusters.PUT("/:id", h.updateCluster)
			clusters.DELETE("/:id", h.deleteCluster)
		}

		backups := api.Group("/backups")
		{
			backups.GET("", h.listBackups)
			backups.GET("/:id", h.getBackup)
			backups.POST("/full", h.createFullBackup)
			backups.POST("/incremental", h.createIncrementalBackup)
			backups.POST("/:id/verify", h.verifyBackup)
			backups.POST("/:id/dryrun", h.dryRunRestore)
			backups.GET("/timepoints/:clusterId", h.listTimePoints)
		}

		restores := api.Group("/restores")
		{
			restores.GET("", h.listRestoreJobs)
			restores.GET("/:id", h.getRestoreJob)
			restores.POST("", h.restoreBackup)
			restores.POST("/wal-index", h.restoreByWALIndex)
		}

		schedules := api.Group("/schedules")
		{
			schedules.GET("", h.listSchedules)
			schedules.GET("/:id", h.getSchedule)
			schedules.POST("", h.createSchedule)
			schedules.PUT("/:id", h.updateSchedule)
			schedules.DELETE("/:id", h.deleteSchedule)
		}

		kms := api.Group("/kms")
		{
			kms.GET("/status", h.kmsStatus)
			kms.POST("/rotate", h.kmsRotate)
		}

		replication := api.Group("/replication")
		{
			replication.GET("", h.listReplicationConfigs)
			replication.GET("/:id", h.getReplicationConfig)
			replication.POST("", h.createReplicationConfig)
			replication.PUT("/:id", h.updateReplicationConfig)
			replication.DELETE("/:id", h.deleteReplicationConfig)
			replication.POST("/:id/replicate", h.replicateBackup)
			replication.POST("/:id/replicate-latest", h.replicateLatestBackups)
			replication.GET("/:id/health", h.checkReplicationHealth)
			replication.GET("/:id/lag", h.getReplicationLag)
			replication.GET("/tasks", h.listReplicationTasks)
			replication.GET("/tasks/:id", h.getReplicationTask)
		}

		drillGroup := api.Group("/drills")
		{
			drillGroup.GET("", h.listDrillConfigs)
			drillGroup.GET("/:id", h.getDrillConfig)
			drillGroup.POST("", h.createDrillConfig)
			drillGroup.PUT("/:id", h.updateDrillConfig)
			drillGroup.DELETE("/:id", h.deleteDrillConfig)
			drillGroup.POST("/:id/run", h.runDrillNow)
			drillGroup.GET("/results", h.listDrillResults)
			drillGroup.GET("/results/:id", h.getDrillResult)
			drillGroup.GET("/stats", h.getDrillStats)
		}

		costGroup := api.Group("/cost")
		{
			costGroup.GET("/analysis/:clusterId", h.getCostAnalysis)
			costGroup.GET("/restore-time/:backupId", h.getEstimatedRestoreTime)
		}
	}

	return r
}

func (h *Handler) healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func (h *Handler) listClusters(c *gin.Context) {
	clusters := h.clusterMgr.ListClusters()
	c.JSON(http.StatusOK, clusters)
}

func (h *Handler) getCluster(c *gin.Context) {
	id := c.Param("id")
	cluster, err := h.clusterMgr.GetCluster(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, cluster)
}

func (h *Handler) getClusterStatus(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	status, err := h.clusterMgr.GetClusterStatus(ctx, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, status)
}

func (h *Handler) createCluster(c *gin.Context) {
	var req models.Cluster
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	cluster := models.NewCluster()
	cluster.Name = req.Name
	cluster.Endpoints = req.Endpoints
	cluster.Username = req.Username
	cluster.Password = req.Password
	cluster.TLS = req.TLS
	cluster.CertFile = req.CertFile
	cluster.KeyFile = req.KeyFile
	cluster.CAFile = req.CAFile
	cluster.Region = req.Region

	if err := h.clusterMgr.AddCluster(cluster); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, cluster)
}

func (h *Handler) updateCluster(c *gin.Context) {
	id := c.Param("id")
	var req models.Cluster
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	existing, err := h.clusterMgr.GetCluster(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}

	existing.Name = req.Name
	existing.Endpoints = req.Endpoints
	existing.Username = req.Username
	existing.Password = req.Password
	existing.TLS = req.TLS
	existing.CertFile = req.CertFile
	existing.KeyFile = req.KeyFile
	existing.CAFile = req.CAFile
	existing.Region = req.Region

	if err := h.clusterMgr.UpdateCluster(existing); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, existing)
}

func (h *Handler) deleteCluster(c *gin.Context) {
	id := c.Param("id")
	if err := h.clusterMgr.RemoveCluster(id); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *Handler) listBackups(c *gin.Context) {
	clusterID := c.Query("clusterId")
	backups := h.backupMgr.ListBackups(clusterID)
	c.JSON(http.StatusOK, backups)
}

func (h *Handler) getBackup(c *gin.Context) {
	id := c.Param("id")
	backup, err := h.backupMgr.GetBackup(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, backup)
}

type CreateBackupRequest struct {
	ClusterID string `json:"clusterId" binding:"required"`
}

func (h *Handler) createFullBackup(c *gin.Context) {
	var req CreateBackupRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	backup, err := h.backupMgr.CreateFullBackup(ctx, req.ClusterID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusAccepted, backup)
}

type CreateIncrementalBackupRequest struct {
	ClusterID      string `json:"clusterId" binding:"required"`
	ParentBackupID string `json:"parentBackupId"`
}

func (h *Handler) createIncrementalBackup(c *gin.Context) {
	var req CreateIncrementalBackupRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	backup, err := h.backupMgr.CreateIncrementalBackup(ctx, req.ClusterID, req.ParentBackupID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusAccepted, backup)
}

func (h *Handler) verifyBackup(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	result, err := h.backupMgr.VerifyBackup(ctx, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (h *Handler) dryRunRestore(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
	defer cancel()

	job, err := h.backupMgr.DryRunRestore(ctx, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusAccepted, job)
}

func (h *Handler) listTimePoints(c *gin.Context) {
	clusterID := c.Param("clusterId")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	timePoints, err := h.backupMgr.ListAvailableTimePoints(ctx, clusterID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, timePoints)
}

func (h *Handler) listRestoreJobs(c *gin.Context) {
	clusterID := c.Query("clusterId")
	jobs := h.backupMgr.ListRestoreJobs(clusterID)
	c.JSON(http.StatusOK, jobs)
}

func (h *Handler) getRestoreJob(c *gin.Context) {
	id := c.Param("id")
	job, err := h.backupMgr.GetRestoreJob(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, job)
}

type RestoreBackupRequest struct {
	BackupID        string    `json:"backupId" binding:"required"`
	TargetClusterID string    `json:"targetClusterId" binding:"required"`
	PointInTime     time.Time `json:"pointInTime"`
}

func (h *Handler) restoreBackup(c *gin.Context) {
	var req RestoreBackupRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	var pointInTime *time.Time
	if !req.PointInTime.IsZero() {
		pointInTime = &req.PointInTime
	}

	job, err := h.backupMgr.RestoreBackup(ctx, req.BackupID, req.TargetClusterID, pointInTime)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusAccepted, job)
}

type RestoreByWALIndexRequest struct {
	BackupID        string `json:"backupId" binding:"required"`
	TargetClusterID string `json:"targetClusterId" binding:"required"`
	WALIndex        int64  `json:"walIndex" binding:"required"`
}

func (h *Handler) restoreByWALIndex(c *gin.Context) {
	var req RestoreByWALIndexRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	job, err := h.backupMgr.RestoreByWALIndex(ctx, req.BackupID, req.TargetClusterID, req.WALIndex)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusAccepted, job)
}

func (h *Handler) listSchedules(c *gin.Context) {
	clusterID := c.Query("clusterId")
	schedules := h.scheduler.ListSchedules(clusterID)
	c.JSON(http.StatusOK, schedules)
}

func (h *Handler) getSchedule(c *gin.Context) {
	id := c.Param("id")
	schedule, err := h.scheduler.GetSchedule(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, schedule)
}

func (h *Handler) createSchedule(c *gin.Context) {
	var req models.Schedule
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	schedule := models.NewSchedule()
	schedule.ClusterID = req.ClusterID
	schedule.Name = req.Name
	schedule.CronExpr = req.CronExpr
	schedule.BackupType = req.BackupType
	schedule.RetentionDays = req.RetentionDays
	schedule.Encrypted = req.Encrypted
	schedule.KMSKeyID = req.KMSKeyID
	schedule.Enabled = req.Enabled

	if err := h.scheduler.AddSchedule(schedule); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, schedule)
}

func (h *Handler) updateSchedule(c *gin.Context) {
	id := c.Param("id")
	var req models.Schedule
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	existing, err := h.scheduler.GetSchedule(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}

	existing.Name = req.Name
	existing.CronExpr = req.CronExpr
	existing.BackupType = req.BackupType
	existing.RetentionDays = req.RetentionDays
	existing.Encrypted = req.Encrypted
	existing.KMSKeyID = req.KMSKeyID
	existing.Enabled = req.Enabled

	if err := h.scheduler.UpdateSchedule(existing); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, existing)
}

func (h *Handler) deleteSchedule(c *gin.Context) {
	id := c.Param("id")
	h.scheduler.RemoveSchedule(id)
	c.Status(http.StatusNoContent)
}

func (h *Handler) kmsStatus(c *gin.Context) {
	if h.kmsEncrypt == nil {
		c.JSON(http.StatusOK, gin.H{"enabled": false, "provider": "none"})
		return
	}

	err := h.kmsEncrypt.HealthCheck()
	status := gin.H{
		"enabled":    true,
		"activeKeyId": h.kmsEncrypt.GetCurrentKeyID(),
		"healthy":    err == nil,
	}
	if err != nil {
		status["error"] = err.Error()
	}
	c.JSON(http.StatusOK, status)
}

func (h *Handler) kmsRotate(c *gin.Context) {
	if h.kmsEncrypt == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "KMS not configured"})
		return
	}

	newKeyID, err := h.kmsEncrypt.RotateKey()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"newKeyId": newKeyID, "message": "Key rotated successfully"})
}

// ---- Replication ----

func (h *Handler) listReplicationConfigs(c *gin.Context) {
	clusterID := c.Query("clusterId")
	configs := h.replicator.ListConfigs(clusterID)
	c.JSON(http.StatusOK, configs)
}

func (h *Handler) getReplicationConfig(c *gin.Context) {
	id := c.Param("id")
	config, err := h.replicator.GetConfig(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, config)
}

func (h *Handler) createReplicationConfig(c *gin.Context) {
	var req models.ReplicationConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	config := models.NewReplicationConfig()
	config.Name = req.Name
	config.SourceClusterID = req.SourceClusterID
	config.TargetClusterID = req.TargetClusterID
	config.TargetStorage = req.TargetStorage
	config.Mode = req.Mode
	config.CronExpr = req.CronExpr
	config.BandwidthLimitMB = req.BandwidthLimitMB
	config.Compress = req.Compress
	config.Encrypted = req.Encrypted
	config.Enabled = req.Enabled

	if err := h.replicator.AddConfig(config); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, config)
}

func (h *Handler) updateReplicationConfig(c *gin.Context) {
	id := c.Param("id")
	var req models.ReplicationConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	existing, err := h.replicator.GetConfig(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}

	existing.Name = req.Name
	existing.TargetStorage = req.TargetStorage
	existing.Mode = req.Mode
	existing.CronExpr = req.CronExpr
	existing.BandwidthLimitMB = req.BandwidthLimitMB
	existing.Compress = req.Compress
	existing.Encrypted = req.Encrypted
	existing.Enabled = req.Enabled

	if err := h.replicator.UpdateConfig(existing); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, existing)
}

func (h *Handler) deleteReplicationConfig(c *gin.Context) {
	id := c.Param("id")
	h.replicator.RemoveConfig(id)
	c.Status(http.StatusNoContent)
}

type ReplicateBackupRequest struct {
	BackupID string `json:"backupId" binding:"required"`
}

func (h *Handler) replicateBackup(c *gin.Context) {
	id := c.Param("id")
	var req ReplicateBackupRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	backup, err := h.backupMgr.GetBackup(req.BackupID)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}

	task, err := h.replicator.ReplicateBackup(ctx, id, backup)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusAccepted, task)
}

func (h *Handler) replicateLatestBackups(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	config, err := h.replicator.GetConfig(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}

	backups := h.backupMgr.ListBackups(config.SourceClusterID)
	tasks, err := h.replicator.ReplicateLatestBackups(ctx, id, backups)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusAccepted, tasks)
}

func (h *Handler) checkReplicationHealth(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	err := h.replicator.CheckTargetHealth(ctx, id)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"healthy": false, "error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"healthy": true})
}

func (h *Handler) getReplicationLag(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	lag, err := h.replicator.GetReplicationLag(ctx, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"lagSeconds": lag})
}

func (h *Handler) listReplicationTasks(c *gin.Context) {
	configID := c.Query("configId")
	tasks := h.replicator.ListTasks(configID)
	c.JSON(http.StatusOK, tasks)
}

func (h *Handler) getReplicationTask(c *gin.Context) {
	id := c.Param("id")
	task, err := h.replicator.GetTask(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, task)
}

// ---- Drill ----

func (h *Handler) listDrillConfigs(c *gin.Context) {
	clusterID := c.Query("clusterId")
	configs := h.drillSched.ListConfigs(clusterID)
	c.JSON(http.StatusOK, configs)
}

func (h *Handler) getDrillConfig(c *gin.Context) {
	id := c.Param("id")
	config, err := h.drillSched.GetConfig(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, config)
}

func (h *Handler) createDrillConfig(c *gin.Context) {
	var req models.DrillConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	config := models.NewDrillConfig()
	config.Name = req.Name
	config.ClusterID = req.ClusterID
	config.CronExpr = req.CronExpr
	config.TargetClusterID = req.TargetClusterID
	config.AutoCleanup = req.AutoCleanup
	config.CleanupDelayMin = req.CleanupDelayMin
	config.VerifyChecksum = req.VerifyChecksum
	config.MaxDataSizeMB = req.MaxDataSizeMB
	config.NotifyOnFailure = req.NotifyOnFailure
	config.Enabled = req.Enabled

	if err := h.drillSched.AddConfig(config); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, config)
}

func (h *Handler) updateDrillConfig(c *gin.Context) {
	id := c.Param("id")
	var req models.DrillConfig
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	existing, err := h.drillSched.GetConfig(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}

	existing.Name = req.Name
	existing.CronExpr = req.CronExpr
	existing.TargetClusterID = req.TargetClusterID
	existing.AutoCleanup = req.AutoCleanup
	existing.CleanupDelayMin = req.CleanupDelayMin
	existing.VerifyChecksum = req.VerifyChecksum
	existing.MaxDataSizeMB = req.MaxDataSizeMB
	existing.NotifyOnFailure = req.NotifyOnFailure
	existing.Enabled = req.Enabled

	if err := h.drillSched.UpdateConfig(existing); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, existing)
}

func (h *Handler) deleteDrillConfig(c *gin.Context) {
	id := c.Param("id")
	h.drillSched.RemoveConfig(id)
	c.Status(http.StatusNoContent)
}

func (h *Handler) runDrillNow(c *gin.Context) {
	id := c.Param("id")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
	defer cancel()

	result, err := h.drillSched.RunDrillNow(ctx, id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusAccepted, result)
}

func (h *Handler) listDrillResults(c *gin.Context) {
	clusterID := c.Query("clusterId")
	results := h.drillSched.ListResults(clusterID)
	c.JSON(http.StatusOK, results)
}

func (h *Handler) getDrillResult(c *gin.Context) {
	id := c.Param("id")
	result, err := h.drillSched.GetResult(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (h *Handler) getDrillStats(c *gin.Context) {
	clusterID := c.Query("clusterId")
	stats := h.drillSched.GetDrillStats(clusterID)
	c.JSON(http.StatusOK, stats)
}

// ---- Cost ----

func (h *Handler) getCostAnalysis(c *gin.Context) {
	clusterID := c.Param("clusterId")
	period := c.DefaultQuery("period", "30d")

	analysis, err := h.costAnalyzer.AnalyzeCluster(clusterID, period)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, analysis)
}

func (h *Handler) getEstimatedRestoreTime(c *gin.Context) {
	backupID := c.Param("backupId")

	seconds, strategy, err := h.costAnalyzer.EstimateRestoreTime(backupID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"estimatedSeconds": seconds,
		"strategy":         strategy,
		"humanReadable":    formatDuration(seconds),
	})
}

func formatDuration(seconds int64) string {
	if seconds < 60 {
		return fmt.Sprintf("%d秒", seconds)
	}
	if seconds < 3600 {
		return fmt.Sprintf("%d分%d秒", seconds/60, seconds%60)
	}
	return fmt.Sprintf("%d时%d分", seconds/3600, (seconds%3600)/60)
}
