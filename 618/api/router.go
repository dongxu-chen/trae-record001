package api

import (
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func SetupRouter(handler *Handler) *gin.Engine {
	r := gin.Default()

	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Type", "Accept", "Authorization"}
	r.Use(cors.New(config))

	api := r.Group("/api")
	{
		audit := api.Group("/audit")
		{
			audit.GET("/logs", handler.GetAuditLogs)
			audit.GET("/logs/:id", handler.GetAuditLog)
			audit.GET("/logs/:id/diff", handler.GetDiff)
			audit.GET("/logs/:id/struct-diff", handler.GetStructDiff)
			audit.POST("/logs/:id/rollback", handler.Rollback)
			audit.POST("/record", handler.RecordChange)
			audit.POST("/quick-rollback", handler.QuickRollback)
		}

		namespace := api.Group("/namespaces")
		{
			namespace.GET("", handler.GetNamespaces)
			namespace.GET("/configs", handler.GetNamespaceConfigs)
			namespace.POST("/configs", handler.SaveNamespaceConfig)
		}

		compliance := api.Group("/compliance")
		{
			compliance.GET("/rules", handler.GetComplianceRules)
			compliance.POST("/rules", handler.SaveComplianceRule)
			compliance.DELETE("/rules/:id", handler.DeleteComplianceRule)
		}

		listener := api.Group("/listener")
		{
			listener.POST("/start", handler.StartListener)
			listener.POST("/stop", handler.StopListener)
		}

		impact := api.Group("/impact")
		{
			impact.GET("/analyze", handler.AnalyzeImpact)
		}

		services := api.Group("/services")
		{
			services.GET("", handler.GetServiceRegistries)
			services.POST("", handler.CreateServiceRegistry)
			services.PUT("", handler.UpdateServiceRegistry)
			services.DELETE("/:id", handler.DeleteServiceRegistry)
		}

		rollbackPolicy := api.Group("/rollback-policies")
		{
			rollbackPolicy.GET("", handler.GetRollbackPolicies)
			rollbackPolicy.POST("", handler.CreateRollbackPolicy)
			rollbackPolicy.PUT("", handler.UpdateRollbackPolicy)
			rollbackPolicy.DELETE("/:id", handler.DeleteRollbackPolicy)
		}

		api.GET("/dashboard", handler.GetDashboard)
	}

	return r
}
