package api

import (
	"strings"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"mysql-partition-tool/config"
)

func SetupRouter() *gin.Engine {
	r := gin.Default()

	origins := strings.Split(config.AppConfig.AllowOrigins, ",")

	r.Use(cors.New(cors.Config{
		AllowOrigins:     origins,
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	api := r.Group("/api")
	{
		connection := api.Group("/connection")
		{
			connection.POST("/test", TestConnection)
			connection.POST("/connect", Connect)
			connection.GET("/status", GetConnectionStatus)
			connection.POST("/disconnect", Disconnect)
		}

		tables := api.Group("/tables")
		{
			tables.GET("", GetTableList)
			tables.GET("/:tableName", GetTableInfo)
			tables.GET("/:tableName/stats", GetTableStats)
			tables.GET("/:tableName/prediction", GetGrowthPrediction)
			tables.GET("/:tableName/partition-info", GetPartitionInfo)
		}

		partition := api.Group("/partition")
		{
			partition.GET("/recommendations/:tableName", RecommendPartition)
			partition.GET("/recommendations/all", GetAllTablesRecommendations)
			partition.GET("/plan/:tableName", GeneratePartitionPlan)
			partition.POST("/execute", ExecutePartitionPlan)
			partition.POST("/operation", ExecutePartitionOperation)
			partition.GET("/auto-extend/:tableName", AutoExtendPartitions)
			partition.GET("/tool-availability", CheckToolAvailability)
			partition.POST("/generate-ptosc", GeneratePTOSCCommand)
			partition.POST("/execute-online-ddl", ExecuteOnlineDDL)
			partition.GET("/split/:tableName", GenerateSplitPartition)
			partition.POST("/merge", GenerateMergePartition)
			partition.GET("/rebalance/:tableName", GenerateRebalancePartitions)
			partition.POST("/migrate", ExecutePartitionMigration)
			partition.GET("/hot-cold/:tableName", AnalyzeHotColdSeparation)
			partition.POST("/hot-cold/migrate", GenerateHotColdMigrationSQL)
			partition.POST("/benchmark", RunPerformanceBenchmark)
			partition.POST("/resize", GenerateResizePlan)
		}

		query := api.Group("/query")
		{
			query.POST("/rewrite", RewriteQuery)
			query.GET("/analyze", AnalyzeQuery)
		}
	}

	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":  "ok",
			"version": "1.0.0",
		})
	})

	return r
}
