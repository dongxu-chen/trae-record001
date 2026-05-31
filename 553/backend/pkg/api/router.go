package api

import (
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"es-shard-balancer/pkg/config"
)

func SetupRouter(handler *Handler, cfg *config.ServerConfig) *gin.Engine {
	gin.SetMode(cfg.Mode)

	r := gin.Default()

	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
	}))

	api := r.Group("/api")
	{
		api.GET("/health", handler.GetHealth)
		api.GET("/config", handler.GetConfig)

		cluster := api.Group("/cluster")
		{
			cluster.GET("/health", handler.GetClusterHealth)
			cluster.GET("/nodes", handler.GetNodes)
			cluster.GET("/shards", handler.GetShards)
			cluster.GET("/distribution", handler.GetShardDistribution)
		}

		balancer := api.Group("/balancer")
		{
			balancer.GET("/plan", handler.GetMigrationPlan)
			balancer.POST("/execute", handler.ExecuteMigrations)
			balancer.POST("/move", handler.MoveShard)
			balancer.GET("/tasks", handler.GetMigrationTasks)
			balancer.GET("/simulate", handler.SimulateMigration)
		}

		monitor := api.Group("/monitor")
		{
			monitor.GET("/load", handler.GetNodeLoad)
			monitor.GET("/load/:name", handler.GetNodeLoad)
			monitor.GET("/speed", handler.GetSpeedInfo)
			monitor.POST("/speed", handler.SetAdaptiveSpeed)
			monitor.GET("/heat", handler.GetIndexHeat)
			monitor.GET("/heat/:name", handler.GetIndexHeat)
			monitor.GET("/heat/hot-indices", handler.GetHotIndices)
			monitor.GET("/auto-scaling", handler.GetAutoScalingStatus)
			monitor.POST("/auto-scaling/scale-out", handler.TriggerScaleOut)
		}

		settings := api.Group("/settings")
		{
			settings.POST("/speed-limit", handler.SetSpeedLimit)
			settings.POST("/disk-watermark", handler.SetDiskWatermark)
		}
	}

	return r
}
