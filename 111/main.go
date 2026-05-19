package main

import (
	"log"

	"cloud-storage-gateway/config"
	"cloud-storage-gateway/database"
	"cloud-storage-gateway/handlers"
	"cloud-storage-gateway/kms"
	"cloud-storage-gateway/redis"
	"cloud-storage-gateway/seaweedfs"

	"github.com/gin-gonic/gin"
)

func main() {
	config.InitConfig()

	if err := database.InitDB(); err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}

	if err := redis.InitRedis(); err != nil {
		log.Fatalf("Failed to initialize Redis: %v", err)
	}

	if err := kms.InitKMS(); err != nil {
		log.Fatalf("Failed to initialize KMS: %v", err)
	}

	if err := seaweedfs.InitSeaweedFS(); err != nil {
		log.Fatalf("Failed to initialize SeaweedFS: %v", err)
	}

	if config.EnableSmallFileMerge {
		seaweedfs.InitSmallFileManager()
		log.Println("Small file merge manager initialized")
	}

	if config.EnableReplication {
		seaweedfs.InitReplication()
		log.Println("Cross-region replication initialized")
	}

	r := gin.Default()

	api := r.Group("/api/v1")
	{
		upload := api.Group("/upload")
		{
			upload.POST("/init", handlers.InitUpload)
			upload.POST("/chunk", handlers.UploadChunk)
			upload.POST("/chunk-md5", handlers.UploadChunkMD5)
			upload.POST("/complete", handlers.CompleteUpload)
			upload.GET("/status/:file_id", handlers.GetUploadStatus)
		}

		files := api.Group("/files")
		{
			files.GET("/:file_id/download", handlers.DownloadFile)
			files.DELETE("/:file_id", handlers.DeleteFile)
			files.GET("/:file_id", handlers.GetFileMetadata)
			files.GET("/", handlers.ListFiles)
		}

		kmsGroup := api.Group("/kms")
		{
			kmsGroup.POST("/keys", handlers.CreateKey)
			kmsGroup.GET("/keys", handlers.ListKeys)
			kmsGroup.GET("/keys/:key_id", handlers.GetKeyMetadata)
			kmsGroup.POST("/keys/:key_id/enable", handlers.EnableKey)
			kmsGroup.POST("/keys/:key_id/disable", handlers.DisableKey)
			kmsGroup.POST("/keys/:key_id/rotate", handlers.RotateKey)
			kmsGroup.POST("/keys/:key_id/export", handlers.ExportKey)
			kmsGroup.POST("/keys/:key_id/import", handlers.ImportKey)
			kmsGroup.POST("/keys/:key_id/generate-data-key", handlers.GenerateDataKey)
		}

		versionGroup := api.Group("/versions")
		{
			versionGroup.GET("/:file_id", handlers.GetObjectVersions)
			versionGroup.POST("/restore", handlers.RestoreObjectVersion)
			versionGroup.DELETE("/:file_id", handlers.DeleteObjectVersion)
			versionGroup.GET("/status", handlers.GetVersioningStatus)
		}

		lifecycleGroup := api.Group("/lifecycle")
		{
			lifecycleGroup.POST("/expiration", handlers.SetObjectExpiration)
			lifecycleGroup.POST("/global-expiration", handlers.SetGlobalExpiration)
			lifecycleGroup.POST("/noncurrent-expiration", handlers.SetNoncurrentVersionExpiration)
			lifecycleGroup.GET("/config", handlers.GetLifecycleConfig)
			lifecycleGroup.DELETE("/rules/:rule_id", handlers.RemoveLifecycleRule)
		}

		mergeGroup := api.Group("/merge")
		{
			mergeGroup.GET("/stats", handlers.GetMergeStats)
			mergeGroup.POST("/trigger", handlers.TriggerMerge)
		}

		replicationGroup := api.Group("/replication")
		{
			replicationGroup.GET("/peers", handlers.GetReplicationPeers)
		}
	}

	log.Printf("Server starting on %s", config.ServerPort)
	if err := r.Run(config.ServerPort); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
