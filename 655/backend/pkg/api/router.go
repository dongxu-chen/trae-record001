package api

import (
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"

	"servicemesh-gateway/pkg/accesscontrol"
	"servicemesh-gateway/pkg/bluegreen"
	"servicemesh-gateway/pkg/costestimator"
	"servicemesh-gateway/pkg/istio"
	"servicemesh-gateway/pkg/redis"
)

func SetupRouter(
	istioClient *istio.Client,
	trafficStore *redis.TrafficStore,
	bgm *bluegreen.BlueGreenManager,
	acm *accesscontrol.AccessControlManager,
	ce *costestimator.CostEstimator,
) *gin.Engine {
	r := gin.Default()

	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Type", "Accept", "Authorization"}
	r.Use(cors.New(config))

	handler := NewHandler(istioClient, trafficStore, bgm, acm, ce)

	api := r.Group("/api/v1")
	{
		api.GET("/health", handler.HealthCheck)

		routing := api.Group("/routing")
		{
			routing.POST("/weight", handler.CreateWeightRouting)
			routing.POST("/header", handler.CreateHeaderRouting)
			routing.POST("/mirror", handler.CreateTrafficMirror)
			routing.POST("/fault", handler.CreateFaultInjection)
			routing.GET("/rules", handler.GetRoutingRules)
			routing.DELETE("/rules/:namespace/:id", handler.DeleteRoutingRule)
		}

		istioGroup := api.Group("/istio")
		{
			istioGroup.GET("/virtualservices", handler.GetVirtualServices)
			istioGroup.GET("/destinationrules", handler.GetDestinationRules)
		}

		topology := api.Group("/topology")
		{
			topology.GET("", handler.GetTopology)
		}

		metrics := api.Group("/metrics")
		{
			metrics.GET("", handler.GetMetrics)
		}

		reports := api.Group("/reports")
		{
			reports.POST("", handler.GenerateReport)
			reports.GET("/:id", handler.GetReport)
		}

		bluegreen := api.Group("/bluegreen")
		{
			bluegreen.POST("", handler.CreateBlueGreenDeployment)
			bluegreen.GET("", handler.ListBlueGreenDeployments)
			bluegreen.GET("/:id", handler.GetBlueGreenDeployment)
			bluegreen.POST("/:id/start", handler.StartBlueGreenDeployment)
			bluegreen.POST("/:id/pause", handler.PauseBlueGreenDeployment)
			bluegreen.POST("/:id/rollback", handler.RollbackBlueGreenDeployment)
			bluegreen.POST("/:id/complete", handler.CompleteBlueGreenDeployment)
		}

		access := api.Group("/access-control")
		{
			access.POST("", handler.CreateAccessControlRule)
			access.GET("", handler.ListAccessControlRules)
			access.GET("/:id", handler.GetAccessControlRule)
			access.PUT("/:id", handler.UpdateAccessControlRule)
			access.DELETE("/:id", handler.DeleteAccessControlRule)
			access.POST("/check", handler.CheckAccess)
		}

		cost := api.Group("/cost")
		{
			cost.POST("/estimate", handler.EstimateCost)
			cost.GET("/providers", handler.GetCostProviders)
			cost.GET("/regions", handler.GetCostRegions)
			cost.GET("/config/:provider", handler.GetCostConfig)
			cost.POST("/monthly-report", handler.MonthlyCostReport)
			cost.POST("/compare", handler.CompareCloudProviders)
		}
	}

	return r
}
