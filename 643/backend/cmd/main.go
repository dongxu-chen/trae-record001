package main

import (
	"capacity-planner/pkg/api"
	"log"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func main() {
	r := gin.Default()

	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Type", "Accept", "Authorization"}
	r.Use(cors.New(config))

	handler := api.NewHandler()

	apiGroup := r.Group("/api")
	{
		apiGroup.POST("/evaluate", handler.EvaluateCapacity)
		apiGroup.GET("/server-configs", handler.GetServerConfigs)
		apiGroup.POST("/forecast", handler.ForecastTraffic)
		apiGroup.POST("/queueing", handler.CalculateQueueing)
		apiGroup.POST("/hybrid-cost", handler.CalculateHybridCost)
		apiGroup.GET("/environment-factors", handler.GetEnvironmentFactors)
		apiGroup.POST("/sensitivity", handler.GetSensitivityAnalysis)
	}

	log.Println("Server starting on :8080")
	if err := r.Run(":8080"); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
