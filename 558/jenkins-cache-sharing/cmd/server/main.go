package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/jenkins-cache-sharing/internal/api"
	"github.com/jenkins-cache-sharing/internal/cache"
	"github.com/jenkins-cache-sharing/internal/config"
	"github.com/jenkins-cache-sharing/internal/jenkins"
	"github.com/jenkins-cache-sharing/internal/storage"
	"go.uber.org/zap"
)

func main() {
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	cfg := config.Load()
	if err := cfg.Validate(); err != nil {
		logger.Fatal("invalid configuration", zap.Error(err))
	}

	objStorage, err := storage.NewObjectStorage(cfg.Storage, logger)
	if err != nil {
		logger.Fatal("failed to initialize object storage", zap.Error(err))
	}

	metaStore, err := cache.NewMetaStore(cfg.Cache.MetaStorePath, logger)
	if err != nil {
		logger.Fatal("failed to initialize meta store", zap.Error(err))
	}

	versionMgr := cache.NewVersionManager(metaStore, objStorage, logger)

	jenkinsCli := jenkins.NewClient(cfg.Jenkins)

	warmupSvc := cache.NewWarmupService(metaStore, versionMgr, objStorage, jenkinsCli, cfg.Cache.WarmupWorkers, logger)

	cleanupEng := cache.NewCleanupEngine(metaStore, versionMgr, logger)
	if err := cleanupEng.Start(); err != nil {
		logger.Fatal("failed to start cleanup engine", zap.Error(err))
	}
	defer cleanupEng.Stop()

	sharingMgr := cache.NewSharingManager(metaStore, versionMgr, logger)

	hitAnalysis := cache.NewHitAnalysis(metaStore, logger)

	migrationEng := cache.NewMigrationEngine(metaStore, objStorage, cfg.Storage, logger)

	handler := api.NewHandler(versionMgr, warmupSvc, cleanupEng, sharingMgr, hitAnalysis, migrationEng, objStorage, jenkinsCli, logger)

	if os.Getenv("GIN_MODE") == "" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.Default()

	r.Use(cors.New(cors.Config{
		AllowOrigins:     cfg.Server.AllowOrigins,
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	r.POST("/api/v1/caches/upload", handler.UploadCache)
	r.GET("/api/v1/caches/:id/presign", handler.GetPresignedURL)

	handler.RegisterRoutes(r)

	r.Static("/assets", "./web/dist/assets")
	r.StaticFile("/", "./web/dist/index.html")
	r.NoRoute(func(c *gin.Context) {
		c.File("./web/dist/index.html")
	})

	srv := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.Server.Port),
		Handler:      r,
		ReadTimeout:  cfg.Server.ReadTimeout,
		WriteTimeout: cfg.Server.WriteTimeout,
	}

	go func() {
		logger.Info("starting server", zap.Int("port", cfg.Server.Port))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("server failed", zap.Error(err))
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal("server forced shutdown", zap.Error(err))
	}

	logger.Info("server exited")
}
