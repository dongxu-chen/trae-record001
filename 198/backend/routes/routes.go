package routes

import (
	"github.com/gin-gonic/gin"
	"github.com/rs/cors"
	"gorm.io/gorm"

	"prometheus-alert-manager/backend/handlers"
)

func SetupRoutes(r *gin.Engine, db *gorm.DB) {
	c := cors.New(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"*"},
		AllowCredentials: true,
	})
	r.Use(func(ctx *gin.Context) {
		c.HandlerFunc(ctx.Writer, ctx.Request)
		if ctx.Request.Method == "OPTIONS" {
			ctx.AbortWithStatus(204)
			return
		}
		ctx.Next()
	})

	ruleHandler := handlers.NewRuleHandler(db)
	groupHandler := handlers.NewGroupHandler(db)
	promqlHandler := handlers.NewPromQLHandler(db)
	prometheusHandler := handlers.NewPrometheusHandler()

	api := r.Group("/api")
	{
		groups := api.Group("/groups")
		{
			groups.GET("", groupHandler.List)
			groups.POST("", groupHandler.Create)
			groups.GET("/:id", groupHandler.Get)
			groups.PUT("/:id", groupHandler.Update)
			groups.DELETE("/:id", groupHandler.Delete)
		}

		rules := api.Group("/rules")
		{
			rules.GET("", ruleHandler.List)
			rules.POST("", ruleHandler.Create)
			rules.GET("/:id", ruleHandler.Get)
			rules.PUT("/:id", ruleHandler.Update)
			rules.DELETE("/:id", ruleHandler.Delete)

			rules.GET("/:id/versions", ruleHandler.ListVersions)
			rules.GET("/:id/versions/:versionId/compare", ruleHandler.CompareVersions)
			rules.POST("/:id/versions/:versionId/restore", ruleHandler.RestoreVersion)
			rules.POST("/:id/versions/:versionId/restore-confirm", ruleHandler.RestoreVersionWithConfirm)
		}

		promql := api.Group("/promql")
		{
			promql.POST("/validate", promqlHandler.Validate)
			promql.POST("/simulate", promqlHandler.Simulate)
			promql.POST("/simulate/batch", promqlHandler.SimulateBatch)
			promql.POST("/generate-test-data", promqlHandler.GenerateTestData)
		}

		importExport := api.Group("/io")
		{
			importExport.POST("/import", ruleHandler.Import)
			importExport.GET("/export", ruleHandler.Export)
		}

		prometheus := api.Group("/prometheus")
		{
			prometheus.GET("/rules", prometheusHandler.GetRules)
			prometheus.GET("/alerts", prometheusHandler.GetAlerts)
			prometheus.POST("/query", prometheusHandler.Query)
		}

		analysis := api.Group("/analysis")
		{
			analysis.GET("/rules", analysisHandler.AnalyzeAllRules)
			analysis.GET("/rules/:id", analysisHandler.AnalyzeRule)
			analysis.GET("/dependencies", analysisHandler.AnalyzeDependencies)
			analysis.GET("/rules/:id/chain", analysisHandler.GetRuleChain)
		}

		templates := api.Group("/templates")
		{
			templates.GET("", analysisHandler.GetTemplates)
			templates.GET("/:templateId", analysisHandler.GetTemplateByID)
			templates.POST("/:templateId/apply", analysisHandler.ApplyTemplate)
			templates.POST("/category/:categoryId/apply", analysisHandler.BatchApplyCategory)
		}
	}
}
