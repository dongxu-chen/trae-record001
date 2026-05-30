package api

import (
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
	"gorm.io/gorm"

	"github.com/keymgmt/service/backend/internal/audit"
	"github.com/keymgmt/service/backend/internal/compliance"
	"github.com/keymgmt/service/backend/internal/recovery"
	"github.com/keymgmt/service/backend/internal/version"
	"github.com/keymgmt/service/backend/internal/vault"
)

func SetupRouter(db *gorm.DB, vaultClient *vault.VaultClient, auditService audit.AuditServiceInterface, log *logrus.Logger) *gin.Engine {
	r := gin.Default()

	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	config.AllowHeaders = []string{"Origin", "Content-Type", "Accept", "Authorization", "X-User"}
	r.Use(cors.New(config))

	r.Use(gin.Logger())
	r.Use(gin.Recovery())

	versionService := version.NewVersionService(db, vaultClient, log)
	complianceService := compliance.NewComplianceService(db, log)
	recoveryService := recovery.NewRecoveryService(db, vaultClient, log)

	secretHandler := NewSecretHandler(db, vaultClient, auditService, log)
	auditHandler := NewAuditHandler(auditService, log)
	healthHandler := NewHealthHandler(db, vaultClient, auditService, log)
	versionHandler := NewVersionHandler(versionService, log)
	complianceHandler := NewComplianceHandler(complianceService, log)
	recoveryHandler := NewRecoveryHandler(recoveryService, log)

	api := r.Group("/api/v1")
	{
		secrets := api.Group("/secrets")
		{
			secrets.POST("", secretHandler.CreateSecret)
			secrets.GET("", secretHandler.ListSecrets)
			secrets.GET("/:id", secretHandler.GetSecret)
			secrets.PUT("/:id", secretHandler.UpdateSecret)
			secrets.DELETE("/:id", secretHandler.DeleteSecret)
			secrets.POST("/:id/rotate", secretHandler.RotateSecret)

			secrets.GET("/:id/versions", versionHandler.GetSecretVersions)
			secrets.POST("/:id/decrypt-version", versionHandler.DecryptWithVersion)
			secrets.POST("/:id/rollback", versionHandler.RollbackToVersion)
			secrets.GET("/:id/compare-versions", versionHandler.CompareVersions)
			secrets.POST("/:id/data-records", versionHandler.CreateDataRecord)
		}

		dataRecords := api.Group("/data-records")
		{
			dataRecords.POST("/:record_id/decrypt", versionHandler.DecryptHistoricalData)
		}

		audit := api.Group("/audit")
		{
			audit.GET("/logs", auditHandler.GetAuditLogs)
			audit.GET("/stats", auditHandler.GetAuditStats)
		}

		compliance := api.Group("/compliance")
		{
			compliance.POST("/check-password", complianceHandler.CheckPasswordStrength)
			compliance.POST("/check-secret/:id", complianceHandler.CheckSecret)
			compliance.POST("/scan", complianceHandler.RunFullScan)
			compliance.GET("/history", complianceHandler.GetCheckHistory)
		}

		recovery := api.Group("/recovery")
		{
			recovery.GET("/exercises", recoveryHandler.GetAvailableExercises)
			recovery.POST("/exercises", recoveryHandler.StartExercise)
			recovery.GET("/history", recoveryHandler.GetExerciseHistory)
			recovery.GET("/exercises/:id", recoveryHandler.GetExerciseDetail)
		}

		health := api.Group("/health")
		{
			health.GET("", healthHandler.HealthCheck)
		}
	}

	return r
}
