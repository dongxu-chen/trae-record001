package api

import (
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jenkins-cache-sharing/internal/cache"
	"github.com/jenkins-cache-sharing/internal/config"
	"github.com/jenkins-cache-sharing/internal/jenkins"
	"github.com/jenkins-cache-sharing/internal/model"
	"github.com/jenkins-cache-sharing/internal/storage"
	"go.uber.org/zap"
)

type Handler struct {
	versionMgr     *cache.VersionManager
	warmupSvc      *cache.WarmupService
	cleanupEng     *cache.CleanupEngine
	sharingMgr     *cache.SharingManager
	hitAnalysis    *cache.HitAnalysis
	migrationEng   *cache.MigrationEngine
	objStorage     *storage.ObjectStorage
	jenkinsCli     *jenkins.Client
	logger         *zap.Logger
}

func NewHandler(
	versionMgr *cache.VersionManager,
	warmupSvc *cache.WarmupService,
	cleanupEng *cache.CleanupEngine,
	sharingMgr *cache.SharingManager,
	hitAnalysis *cache.HitAnalysis,
	migrationEng *cache.MigrationEngine,
	objStorage *storage.ObjectStorage,
	jenkinsCli *jenkins.Client,
	logger *zap.Logger,
) *Handler {
	return &Handler{
		versionMgr:   versionMgr,
		warmupSvc:    warmupSvc,
		cleanupEng:   cleanupEng,
		sharingMgr:   sharingMgr,
		hitAnalysis:  hitAnalysis,
		migrationEng: migrationEng,
		objStorage:   objStorage,
		jenkinsCli:   jenkinsCli,
		logger:       logger,
	}
}

func (h *Handler) RegisterRoutes(r *gin.Engine) {
	api := r.Group("/api/v1")
	{
		caches := api.Group("/caches")
		{
			caches.GET("", h.listCaches)
			caches.GET("/:id", h.getCache)
			caches.POST("", h.createCache)
			caches.POST("/with-deps", h.createCacheWithDependencies)
			caches.DELETE("/:id", h.deleteCache)
			caches.GET("/:id/download", h.downloadCache)
			caches.POST("/:id/access", h.recordAccess)
			caches.POST("/check-deps", h.checkDependencyChange)
			caches.POST("/upload-with-deps", h.uploadCacheWithDependencies)
		}

		versions := api.Group("/versions")
		{
			versions.GET("", h.listVersions)
			versions.POST("/:type/promote", h.promoteVersion)
		}

		warmup := api.Group("/warmup")
		{
			warmup.POST("", h.createWarmupTask)
			warmup.GET("", h.listWarmupTasks)
			warmup.GET("/:id", h.getWarmupTask)
			warmup.POST("/jenkins", h.warmupFromJenkins)
			warmup.POST("/check-and-trigger", h.checkAndTriggerWarmup)
			warmup.GET("/dependency-events", h.listDependencyEvents)
			warmup.POST("/auto-warmup", h.setAutoWarmup)
		}

		cleanup := api.Group("/cleanup")
		{
			cleanup.GET("/policies", h.listPolicies)
			cleanup.GET("/policies/:id", h.getPolicy)
			cleanup.POST("/policies", h.createPolicy)
			cleanup.PUT("/policies/:id", h.updatePolicy)
			cleanup.DELETE("/policies/:id", h.deletePolicy)
			cleanup.POST("/policies/:id/execute", h.executePolicy)
			cleanup.GET("/results", h.listResults)
			cleanup.POST("/evict", h.evictBySize)
		}

		jenkinsGroup := api.Group("/jenkins")
		{
			jenkinsGroup.GET("/jobs", h.listJenkinsJobs)
			jenkinsGroup.GET("/jobs/:name/builds/:number", h.getJenkinsBuild)
			jenkinsGroup.GET("/jobs/:name/latest", h.getJenkinsLatestBuild)
			jenkinsGroup.POST("/jobs/:name/trigger", h.triggerJenkinsBuild)
			jenkinsGroup.GET("/test", h.testJenkinsConnection)
		}

		deps := api.Group("/dependencies")
		{
			deps.POST("/hash", h.computeDependencyHash)
			deps.GET("/latest-hash", h.getLatestDependencyHash)
			deps.GET("/patterns", h.getDependencyPatterns)
		}

		groups := api.Group("/groups")
		{
			groups.GET("", h.listGroups)
			groups.GET("/:id", h.getGroup)
			groups.POST("", h.createGroup)
			groups.PUT("/:id", h.updateGroup)
			groups.DELETE("/:id", h.deleteGroup)
			groups.POST("/:id/jobs", h.addJobToGroup)
			groups.DELETE("/:id/jobs/:job", h.removeJobFromGroup)
		}

		sharing := api.Group("/sharing")
		{
			sharing.POST("/find-similar", h.findSimilarCaches)
			sharing.GET("/job/:job", h.getGroupsForJob)
		}

		hits := api.Group("/hits")
		{
			hits.POST("", h.recordHit)
			hits.GET("", h.listHitRecords)
			hits.GET("/stats", h.getHitRateStats)
			hits.GET("/build/:job/:number", h.getBuildHitRecords)
			hits.GET("/missed", h.getTopMissedKeys)
			hits.DELETE("/clean", h.cleanOldRecords)
		}

		backends := api.Group("/backends")
		{
			backends.GET("", h.listBackends)
			backends.POST("", h.addBackend)
			backends.DELETE("/:id", h.removeBackend)
		}

		migration := api.Group("/migration")
		{
			migration.GET("/tasks", h.listMigrationTasks)
			migration.GET("/tasks/:id", h.getMigrationTask)
			migration.POST("/tasks", h.createMigrationTask)
			migration.POST("/tasks/:id/start", h.startMigration)
			migration.POST("/tasks/:id/pause", h.pauseMigration)
			migration.POST("/tasks/:id/resume", h.resumeMigration)
			migration.POST("/tasks/:id/cancel", h.cancelMigration)
			migration.GET("/tasks/:id/progress", h.getMigrationProgress)
		}

		api.GET("/stats", h.getStats)
		api.GET("/health", h.healthCheck)
	}
}

func (h *Handler) listCaches(c *gin.Context) {
	cacheType := model.CacheType(c.Query("type"))
	jobName := c.Query("job")
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))

	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 20
	}

	result, err := h.versionMgr.ListEntries(c.Request.Context(), cacheType, jobName, page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: result})
}

func (h *Handler) getCache(c *gin.Context) {
	id := c.Param("id")
	entry, err := h.versionMgr.GetEntry(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: entry})
}

func (h *Handler) createCache(c *gin.Context) {
	var entry model.CacheEntry
	if err := c.ShouldBindJSON(&entry); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	created, err := h.versionMgr.CreateEntry(c.Request.Context(), &entry)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusCreated, model.APIMessage{Success: true, Data: created})
}

func (h *Handler) deleteCache(c *gin.Context) {
	id := c.Param("id")
	if err := h.versionMgr.DeleteEntry(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "cache entry deleted"})
}

func (h *Handler) downloadCache(c *gin.Context) {
	id := c.Param("id")
	entry, err := h.versionMgr.GetEntry(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	reader, size, err := h.objStorage.Download(c.Request.Context(), entry.ObjectKey)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	defer reader.Close()

	c.Header("Content-Disposition", "attachment; filename="+entry.Name+".tar.gz")
	c.Header("Content-Length", strconv.FormatInt(size, 10))
	c.DataFromReader(http.StatusOK, size, "application/gzip", reader, nil)
}

func (h *Handler) recordAccess(c *gin.Context) {
	id := c.Param("id")
	if err := h.versionMgr.RecordAccess(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "access recorded"})
}

func (h *Handler) listVersions(c *gin.Context) {
	cacheType := model.CacheType(c.Query("type"))
	versions, err := h.versionMgr.GetVersions(c.Request.Context(), cacheType)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: versions})
}

func (h *Handler) promoteVersion(c *gin.Context) {
	cacheType := model.CacheType(c.Param("type"))
	var req struct {
		Version string `json:"version" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	if err := h.versionMgr.PromoteVersion(c.Request.Context(), cacheType, req.Version); err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "version promoted"})
}

func (h *Handler) listWarmupTasks(c *gin.Context) {
	tasks, err := h.warmupSvc.ListTasks(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: tasks})
}

func (h *Handler) getWarmupTask(c *gin.Context) {
	id := c.Param("id")
	task, err := h.warmupSvc.GetTask(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: task})
}

func (h *Handler) warmupFromJenkins(c *gin.Context) {
	var req struct {
		CacheType   model.CacheType `json:"cache_type" binding:"required"`
		JobName     string          `json:"job_name" binding:"required"`
		BuildNumber int             `json:"build_number"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	task, err := h.warmupSvc.WarmupFromJenkins(c.Request.Context(), req.CacheType, req.JobName, req.BuildNumber)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusCreated, model.APIMessage{Success: true, Data: task})
}

func (h *Handler) listPolicies(c *gin.Context) {
	policies := h.cleanupEng.GetPolicies()
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: policies})
}

func (h *Handler) getPolicy(c *gin.Context) {
	id := c.Param("id")
	policy, err := h.cleanupEng.GetPolicy(id)
	if err != nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: policy})
}

func (h *Handler) createPolicy(c *gin.Context) {
	var policy model.CleanupPolicy
	if err := c.ShouldBindJSON(&policy); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	created, err := h.cleanupEng.CreatePolicy(&policy)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusCreated, model.APIMessage{Success: true, Data: created})
}

func (h *Handler) updatePolicy(c *gin.Context) {
	id := c.Param("id")
	var updates struct {
		Name           *string         `json:"name"`
		MaxAge         *time.Duration  `json:"max_age"`
		MaxSize        *int64          `json:"max_size"`
		MaxVersions    *int            `json:"max_versions"`
		KeepLatest     *int            `json:"keep_latest"`
		Enabled        *bool           `json:"enabled"`
		CronExpression *string         `json:"cron_expression"`
		CacheTypes     []model.CacheType `json:"cache_types"`
	}
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	policy, err := h.cleanupEng.UpdatePolicy(id, func(p *model.CleanupPolicy) {
		if updates.Name != nil {
			p.Name = *updates.Name
		}
		if updates.MaxAge != nil {
			p.MaxAge = *updates.MaxAge
		}
		if updates.MaxSize != nil {
			p.MaxSize = *updates.MaxSize
		}
		if updates.MaxVersions != nil {
			p.MaxVersions = *updates.MaxVersions
		}
		if updates.KeepLatest != nil {
			p.KeepLatest = *updates.KeepLatest
		}
		if updates.Enabled != nil {
			p.Enabled = *updates.Enabled
		}
		if updates.CronExpression != nil {
			p.CronExpression = *updates.CronExpression
		}
		if updates.CacheTypes != nil {
			p.CacheTypes = updates.CacheTypes
		}
	})
	if err != nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: policy})
}

func (h *Handler) deletePolicy(c *gin.Context) {
	id := c.Param("id")
	if err := h.cleanupEng.DeletePolicy(id); err != nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "policy deleted"})
}

func (h *Handler) executePolicy(c *gin.Context) {
	id := c.Param("id")
	result, err := h.cleanupEng.ExecutePolicy(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: result})
}

func (h *Handler) listResults(c *gin.Context) {
	results := h.cleanupEng.GetResults()
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: results})
}

func (h *Handler) listJenkinsJobs(c *gin.Context) {
	jobs, err := h.jenkinsCli.ListJobs(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: jobs})
}

func (h *Handler) getJenkinsBuild(c *gin.Context) {
	name := c.Param("name")
	number, _ := strconv.Atoi(c.Param("number"))

	build, err := h.jenkinsCli.GetBuild(c.Request.Context(), name, number)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: build})
}

func (h *Handler) getJenkinsLatestBuild(c *gin.Context) {
	name := c.Param("name")

	build, err := h.jenkinsCli.GetLatestBuild(c.Request.Context(), name)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: build})
}

func (h *Handler) triggerJenkinsBuild(c *gin.Context) {
	name := c.Param("name")
	var req struct {
		Parameters map[string]string `json:"parameters"`
	}
	c.ShouldBindJSON(&req)

	if req.Parameters == nil {
		req.Parameters = make(map[string]string)
	}

	queueNum, err := h.jenkinsCli.TriggerBuild(c.Request.Context(), name, req.Parameters)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: map[string]int{"queue_number": queueNum}})
}

func (h *Handler) testJenkinsConnection(c *gin.Context) {
	err := h.jenkinsCli.TestConnection(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusBadGateway, model.APIMessage{Success: false, Message: "connection failed: " + err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "connection successful"})
}

func (h *Handler) getStats(c *gin.Context) {
	stats, err := h.versionMgr.GetStats(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: stats})
}

func (h *Handler) healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, model.APIMessage{
		Success: true,
		Message: "ok",
		Data: map[string]string{
			"status": "healthy",
			"time":   time.Now().Format(time.RFC3339),
		},
	})
}

func (h *Handler) UploadCache(c *gin.Context) {
	cacheType := model.CacheType(c.PostForm("cache_type"))
	jobName := c.PostForm("job_name")
	version := c.PostForm("version")
	buildNumber, _ := strconv.Atoi(c.PostForm("build_number"))

	if cacheType == "" || jobName == "" || version == "" {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: "cache_type, job_name and version are required"})
		return
	}

	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: "file upload failed: " + err.Error()})
		return
	}
	defer file.Close()

	objectKey, err := h.objStorage.Upload(c.Request.Context(), cacheType, jobName, buildNumber, file, header.Size, version)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	entry := &model.CacheEntry{
		Name:        fmt.Sprintf("%s-%s-%d", cacheType, jobName, buildNumber),
		Type:        cacheType,
		Version:     version,
		BuildNumber: buildNumber,
		JobName:     jobName,
		Size:        header.Size,
		ObjectKey:   objectKey,
	}

	created, err := h.versionMgr.CreateEntry(c.Request.Context(), entry)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusCreated, model.APIMessage{Success: true, Data: created})
}

func (h *Handler) GetPresignedURL(c *gin.Context) {
	id := c.Param("id")
	entry, err := h.versionMgr.GetEntry(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	url, err := h.objStorage.GetPresignedURL(c.Request.Context(), entry.ObjectKey, 1*time.Hour)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: map[string]string{"url": url}})
}

func (h *Handler) createCacheWithDependencies(c *gin.Context) {
	var req struct {
		Entry        model.CacheEntry    `json:"entry" binding:"required"`
		FileContents map[string]string `json:"file_contents"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	created, depHash, changed, err := h.versionMgr.CreateEntryWithDependencies(
		c.Request.Context(),
		&req.Entry,
		req.FileContents,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusCreated, model.APIMessage{
		Success: true,
		Data: map[string]interface{}{
			"entry":           created,
			"dependency_hash": depHash,
			"changed":         changed,
		},
	})
}

func (h *Handler) checkDependencyChange(c *gin.Context) {
	var req struct {
		CacheType    model.CacheType `json:"cache_type" binding:"required"`
		JobName      string          `json:"job_name" binding:"required"`
		BuildNumber  int             `json:"build_number"`
		FileContents map[string]string `json:"file_contents"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	event, err := h.versionMgr.CheckDependencyChange(
		c.Request.Context(),
		req.CacheType,
		req.JobName,
		req.FileContents,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.APIMessage{
		Success: true,
		Data: map[string]interface{}{
			"changed": event != nil,
			"event":   event,
		},
	})
}

func (h *Handler) uploadCacheWithDependencies(c *gin.Context) {
	cacheType := model.CacheType(c.PostForm("cache_type"))
	jobName := c.PostForm("job_name")
	version := c.PostForm("version")
	buildNumber, _ := strconv.Atoi(c.PostForm("build_number"))
	depHash := c.PostForm("dependency_hash")

	if cacheType == "" || jobName == "" || version == "" {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: "cache_type, job_name and version are required"})
		return
	}

	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: "file upload failed: " + err.Error()})
		return
	}
	defer file.Close()

	objectKey, err := h.objStorage.Upload(c.Request.Context(), cacheType, jobName, buildNumber, file, header.Size, version)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	entry := &model.CacheEntry{
		Name:             fmt.Sprintf("%s-%s-%d", cacheType, jobName, buildNumber),
		Type:             cacheType,
		Version:          version,
		BuildNumber:      buildNumber,
		JobName:          jobName,
		Size:             header.Size,
		ObjectKey:        objectKey,
		DependencyHash:   depHash,
	}

	created, err := h.versionMgr.CreateEntry(c.Request.Context(), entry)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	previousHash := h.versionMgr.GetLatestDependencyHash(c.Request.Context(), cacheType, jobName)
	changed := previousHash != "" && previousHash != depHash

	c.JSON(http.StatusCreated, model.APIMessage{
		Success: true,
		Data: map[string]interface{}{
			"entry":           created,
			"changed":         changed,
			"previous_hash":   previousHash,
			"dependency_hash": depHash,
		},
	})
}

func (h *Handler) createWarmupTask(c *gin.Context) {
	var req struct {
		CacheType    model.CacheType `json:"cache_type" binding:"required"`
		SourceJob    string          `json:"source_job" binding:"required"`
		SourceBuild  int             `json:"source_build"`
		TargetJobs   []string        `json:"target_jobs" binding:"required"`
		Trigger      model.WarmupTrigger `json:"trigger"`
		PreviousHash string          `json:"previous_hash"`
		CurrentHash  string          `json:"current_hash"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	if req.Trigger == "" {
		req.Trigger = model.WarmupTriggerManual
	}

	task, err := h.warmupSvc.CreateWarmupTask(
		c.Request.Context(),
		req.CacheType,
		req.SourceJob,
		req.SourceBuild,
		req.TargetJobs,
		req.Trigger,
		req.PreviousHash,
		req.CurrentHash,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusCreated, model.APIMessage{Success: true, Data: task})
}

func (h *Handler) checkAndTriggerWarmup(c *gin.Context) {
	var req struct {
		CacheType    model.CacheType `json:"cache_type" binding:"required"`
		JobName      string          `json:"job_name" binding:"required"`
		BuildNumber  int             `json:"build_number"`
		FileContents map[string]string `json:"file_contents"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	task, event, err := h.warmupSvc.CheckAndTriggerWarmup(
		c.Request.Context(),
		req.CacheType,
		req.JobName,
		req.BuildNumber,
		req.FileContents,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.APIMessage{
		Success: true,
		Data: map[string]interface{}{
			"task":   task,
			"event":  event,
			"triggered": task != nil,
		},
	})
}

func (h *Handler) listDependencyEvents(c *gin.Context) {
	cacheType := model.CacheType(c.Query("type"))
	jobName := c.Query("job")

	events := h.warmupSvc.GetDependencyEvents(c.Request.Context(), cacheType, jobName)
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: events})
}

func (h *Handler) setAutoWarmup(c *gin.Context) {
	var req struct {
		Enabled bool `json:"enabled" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	h.warmupSvc.SetAutoWarmup(req.Enabled)
	c.JSON(http.StatusOK, model.APIMessage{
		Success: true,
		Message: fmt.Sprintf("auto warmup %s", map[bool]string{true: "enabled", false: "disabled"}[req.Enabled]),
	})
}

func (h *Handler) computeDependencyHash(c *gin.Context) {
	var req struct {
		CacheType    model.CacheType `json:"cache_type" binding:"required"`
		FileContents map[string]string `json:"file_contents"`
		ProjectDir   string          `json:"project_dir"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	var hash interface{}
	var err error

	if req.ProjectDir != "" {
		hash, err = h.versionMgr.ComputeHashForDir(req.CacheType, req.ProjectDir)
	} else if req.FileContents != nil {
		hash, err = h.versionMgr.ComputeHashForContents(req.CacheType, req.FileContents)
	} else {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: "either file_contents or project_dir is required"})
		return
	}

	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: hash})
}

func (h *Handler) getLatestDependencyHash(c *gin.Context) {
	cacheType := model.CacheType(c.Query("type"))
	jobName := c.Query("job")

	if cacheType == "" || jobName == "" {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: "type and job are required"})
		return
	}

	hash := h.versionMgr.GetLatestDependencyHash(c.Request.Context(), cacheType, jobName)
	c.JSON(http.StatusOK, model.APIMessage{
		Success: true,
		Data: map[string]string{
			"dependency_hash": hash,
		},
	})
}

func (h *Handler) getDependencyPatterns(c *gin.Context) {
	cacheType := model.CacheType(c.Query("type"))

	patterns := map[model.CacheType][]string{
		model.CacheTypeMaven:  {"pom.xml", "pom.properties"},
		model.CacheTypeNPM:    {"package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml"},
		model.CacheTypeGradle: {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "gradle.properties", "gradle-wrapper.properties"},
	}

	result := make(map[string][]string)
	if cacheType != "" {
		result[string(cacheType)] = patterns[cacheType]
	} else {
		for t, p := range patterns {
			result[string(t)] = p
		}
	}

	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: result})
}

func (h *Handler) evictBySize(c *gin.Context) {
	var req struct {
		CacheType model.CacheType `json:"cache_type"`
		MaxSize   int64           `json:"max_size" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	result, err := h.cleanupEng.CheckSizeAndEvict(c.Request.Context(), req.CacheType, req.MaxSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: result})
}

func (h *Handler) listGroups(c *gin.Context) {
	groups, err := h.sharingMgr.ListGroups(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: groups})
}

func (h *Handler) getGroup(c *gin.Context) {
	id := c.Param("id")
	group, err := h.sharingMgr.GetGroup(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	if group == nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: "group not found"})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: group})
}

func (h *Handler) createGroup(c *gin.Context) {
	var group model.ProjectGroup
	if err := c.ShouldBindJSON(&group); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	created, err := h.sharingMgr.CreateGroup(c.Request.Context(), &group)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusCreated, model.APIMessage{Success: true, Data: created})
}

func (h *Handler) updateGroup(c *gin.Context) {
	id := c.Param("id")
	var updates model.ProjectGroup
	if err := c.ShouldBindJSON(&updates); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	updated, err := h.sharingMgr.UpdateGroup(c.Request.Context(), id, func(g *model.ProjectGroup) {
		if updates.Name != "" {
			g.Name = updates.Name
		}
		if updates.Description != "" {
			g.Description = updates.Description
		}
		if updates.Jobs != nil {
			g.Jobs = updates.Jobs
		}
		if updates.CacheTypes != nil {
			g.CacheTypes = updates.CacheTypes
		}
		g.SharingEnabled = updates.SharingEnabled
		if updates.MinSimilarity > 0 {
			g.MinSimilarity = updates.MinSimilarity
		}
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	if updated == nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: "group not found"})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: updated})
}

func (h *Handler) deleteGroup(c *gin.Context) {
	id := c.Param("id")
	if err := h.sharingMgr.DeleteGroup(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "group deleted"})
}

func (h *Handler) addJobToGroup(c *gin.Context) {
	groupID := c.Param("id")
	var req struct {
		JobName string `json:"job_name" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	if err := h.sharingMgr.AddJobToGroup(c.Request.Context(), groupID, req.JobName); err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "job added to group"})
}

func (h *Handler) removeJobFromGroup(c *gin.Context) {
	groupID := c.Param("id")
	jobName := c.Param("job")

	if err := h.sharingMgr.RemoveJobFromGroup(c.Request.Context(), groupID, jobName); err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "job removed from group"})
}

func (h *Handler) findSimilarCaches(c *gin.Context) {
	var req struct {
		CacheType      model.CacheType            `json:"cache_type" binding:"required"`
		JobName        string                     `json:"job_name" binding:"required"`
		DependencyHash string                     `json:"dependency_hash"`
		DependencyFiles []model.DependencyFileHash `json:"dependency_files" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	matches := h.sharingMgr.FindSimilarCaches(
		c.Request.Context(),
		req.CacheType,
		req.JobName,
		req.DependencyHash,
		req.DependencyFiles,
	)
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: matches})
}

func (h *Handler) getGroupsForJob(c *gin.Context) {
	jobName := c.Param("job")
	groups := h.sharingMgr.GetGroupsForJob(c.Request.Context(), jobName)
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: groups})
}

func (h *Handler) recordHit(c *gin.Context) {
	var req struct {
		CacheType      model.CacheType `json:"cache_type" binding:"required"`
		JobName        string          `json:"job_name" binding:"required"`
		BuildNumber    int             `json:"build_number" binding:"required"`
		Stage          model.BuildStage `json:"stage" binding:"required"`
		Hit            bool            `json:"hit" binding:"required"`
		RequestedKey   string          `json:"requested_key" binding:"required"`
		MatchedEntry   string          `json:"matched_entry"`
		DependencyHash string          `json:"dependency_hash"`
		Source         string          `json:"source"`
		LatencyMs      int64           `json:"latency_ms"`
		SizeSaved      int64           `json:"size_saved"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	record := h.hitAnalysis.RecordHit(
		c.Request.Context(),
		req.CacheType,
		req.JobName,
		req.BuildNumber,
		req.Stage,
		req.Hit,
		req.RequestedKey,
		req.MatchedEntry,
		req.DependencyHash,
		req.Source,
		req.LatencyMs,
		req.SizeSaved,
	)
	c.JSON(http.StatusCreated, model.APIMessage{Success: true, Data: record})
}

func (h *Handler) listHitRecords(c *gin.Context) {
	cacheType := model.CacheType(c.Query("type"))
	jobName := c.Query("job")
	stage := model.BuildStage(c.Query("stage"))

	records := h.hitAnalysis.GetRecords(c.Request.Context(), cacheType, jobName, stage, time.Time{}, time.Time{})
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: records})
}

func (h *Handler) getHitRateStats(c *gin.Context) {
	cacheType := model.CacheType(c.Query("type"))
	jobName := c.Query("job")
	timeRange := c.DefaultQuery("range", "24h")

	stats := h.hitAnalysis.GetHitRateStats(c.Request.Context(), cacheType, jobName, timeRange)
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: stats})
}

func (h *Handler) getBuildHitRecords(c *gin.Context) {
	jobName := c.Param("job")
	buildNumber, _ := strconv.Atoi(c.Param("number"))

	records := h.hitAnalysis.GetRecordsByBuild(c.Request.Context(), jobName, buildNumber)
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: records})
}

func (h *Handler) getTopMissedKeys(c *gin.Context) {
	cacheType := model.CacheType(c.Query("type"))
	jobName := c.Query("job")
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))

	missed := h.hitAnalysis.GetTopMissedKeys(c.Request.Context(), cacheType, jobName, limit)
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: missed})
}

func (h *Handler) cleanOldRecords(c *gin.Context) {
	maxAge, err := time.ParseDuration(c.DefaultQuery("max_age", "720h"))
	if err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: "invalid max_age"})
		return
	}

	removed := h.hitAnalysis.CleanOldRecords(c.Request.Context(), maxAge)
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: map[string]int{"removed": removed}})
}

func (h *Handler) listBackends(c *gin.Context) {
	backends, err := h.migrationEng.ListBackends(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: backends})
}

func (h *Handler) addBackend(c *gin.Context) {
	var cfg config.StorageBackendConfig
	if err := c.ShouldBindJSON(&cfg); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	backend, err := h.migrationEng.AddBackend(c.Request.Context(), cfg)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusCreated, model.APIMessage{Success: true, Data: backend})
}

func (h *Handler) removeBackend(c *gin.Context) {
	id := c.Param("id")
	if err := h.migrationEng.RemoveBackend(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "backend removed"})
}

func (h *Handler) listMigrationTasks(c *gin.Context) {
	tasks, err := h.migrationEng.ListTasks(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: tasks})
}

func (h *Handler) getMigrationTask(c *gin.Context) {
	id := c.Param("id")
	task, err := h.migrationEng.GetTask(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	if task == nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: "task not found"})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: task})
}

func (h *Handler) createMigrationTask(c *gin.Context) {
	var req struct {
		Name            string             `json:"name" binding:"required"`
		SourceBackendID string             `json:"source_backend_id" binding:"required"`
		TargetBackendID string             `json:"target_backend_id" binding:"required"`
		Mode            model.MigrationMode `json:"mode" binding:"required"`
		CacheTypes      []model.CacheType   `json:"cache_types"`
		JobNames        []string           `json:"job_names"`
		EntryIDs        []string           `json:"entry_ids"`
		DeleteSource    bool               `json:"delete_source"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, model.APIMessage{Success: false, Message: err.Error()})
		return
	}

	task, err := h.migrationEng.CreateMigrationTask(
		c.Request.Context(),
		req.Name,
		req.SourceBackendID,
		req.TargetBackendID,
		req.Mode,
		req.CacheTypes,
		req.JobNames,
		req.EntryIDs,
		req.DeleteSource,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusCreated, model.APIMessage{Success: true, Data: task})
}

func (h *Handler) startMigration(c *gin.Context) {
	id := c.Param("id")
	task, err := h.migrationEng.StartMigration(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	if task == nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: "task not found"})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: task})
}

func (h *Handler) pauseMigration(c *gin.Context) {
	id := c.Param("id")
	if err := h.migrationEng.PauseMigration(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "migration paused"})
}

func (h *Handler) resumeMigration(c *gin.Context) {
	id := c.Param("id")
	if err := h.migrationEng.ResumeMigration(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "migration resumed"})
}

func (h *Handler) cancelMigration(c *gin.Context) {
	id := c.Param("id")
	if err := h.migrationEng.CancelMigration(c.Request.Context(), id); err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Message: "migration cancelled"})
}

func (h *Handler) getMigrationProgress(c *gin.Context) {
	id := c.Param("id")
	progress, err := h.migrationEng.GetProgress(c.Request.Context(), id)
	if err != nil {
		c.JSON(http.StatusInternalServerError, model.APIMessage{Success: false, Message: err.Error()})
		return
	}
	if progress == nil {
		c.JSON(http.StatusNotFound, model.APIMessage{Success: false, Message: "task not found"})
		return
	}
	c.JSON(http.StatusOK, model.APIMessage{Success: true, Data: progress})
}

