package main

import (
	"fault-injection-platform/config"
	"fault-injection-platform/internal/api"
	"fault-injection-platform/internal/istio"
	"fault-injection-platform/internal/jaeger"
	"fault-injection-platform/internal/storage"
	"fault-injection-platform/pkg/logger"
	"fmt"
	"log"

	"github.com/gin-gonic/gin"
)

func main() {
	if err := config.Load(); err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	cfg := config.Get()
	logger.Init(cfg.Logging.Level, cfg.Logging.Format)

	db, err := storage.NewSQLiteDB(cfg.Database.Path)
	if err != nil {
		log.Fatalf("Failed to init database: %v", err)
	}
	defer db.Close()

	istioClient, err := istio.NewClient(cfg.Istio.Kubeconfig, cfg.Istio.Namespace)
	if err != nil {
		log.Fatalf("Failed to create Istio client: %v", err)
	}

	jaegerClient := jaeger.NewClient(cfg.Jaeger.QueryEndpoint)

	gin.SetMode(cfg.Server.Mode)
	r := gin.Default()

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

	handler := api.NewHandler(db, istioClient, jaegerClient)
	handler.RegisterRoutes(r)

	addr := fmt.Sprintf(":%d", cfg.Server.Port)
	logger.Infof("Server starting on %s", addr)
	if err := r.Run(addr); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
