package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	"etcd-backup-manager/internal/api"
	"etcd-backup-manager/internal/backup"
	"etcd-backup-manager/internal/cluster"
	"etcd-backup-manager/internal/encryption"
	"etcd-backup-manager/internal/scheduler"
	"etcd-backup-manager/internal/storage"
	"etcd-backup-manager/pkg/models"
)

func main() {
	config := loadConfig()

	var encryptor backup.Encryptor
	var kmsEncryptor *encryption.KMSEncryptor

	if config.Encryption.KMS.Provider != "" {
		provider, err := encryption.NewKMSProviderFromConfig(encryption.KMSConfig{
			Provider:  config.Encryption.KMS.Provider,
			Endpoint:  config.Encryption.KMS.Endpoint,
			Region:    config.Encryption.KMS.Region,
			AccessKey: config.Encryption.KMS.AccessKey,
			SecretKey: config.Encryption.KMS.SecretKey,
			KeyID:     config.Encryption.KMS.KeyID,
			KeyVault:  config.Encryption.KMS.KeyVault,
			Token:     config.Encryption.KMS.Token,
		})
		if err != nil {
			log.Fatalf("Failed to create KMS provider: %v", err)
		}

		kmsEncryptor = encryption.NewKMSEncryptor(provider)
		encryptor = kmsEncryptor

		if err := kmsEncryptor.HealthCheck(); err != nil {
			log.Printf("Warning: KMS health check failed: %v", err)
		} else {
			log.Printf("KMS initialized with provider: %s, keyId: %s", config.Encryption.KMS.Provider, kmsEncryptor.GetCurrentKeyID())
		}
	} else if config.Encryption.Enabled {
		legacyEncryptor, err := encryption.NewEncryptor(config.Encryption.Key, true)
		if err != nil {
			log.Fatalf("Failed to create encryptor: %v", err)
		}
		encryptor = legacyEncryptor
		log.Println("Using legacy static key encryption (consider migrating to KMS)")
	} else {
		encryptor = encryption.NewEncryptor("", false)
	}

	store, err := storage.NewStorage(config.Storage)
	if err != nil {
		log.Fatalf("Failed to create storage: %v", err)
	}

	clusterMgr := cluster.NewManager()
	for i := range config.Clusters {
		if err := clusterMgr.AddCluster(&config.Clusters[i]); err != nil {
			log.Printf("Warning: Failed to add cluster %s: %v", config.Clusters[i].Name, err)
		}
	}

	tempDir := filepath.Join(os.TempDir(), "etcd-backup-manager")
	backupMgr, err := backup.NewManager(clusterMgr, store, encryptor, tempDir)
	if err != nil {
		log.Fatalf("Failed to create backup manager: %v", err)
	}

	sched := scheduler.NewScheduler(backupMgr)
	for i := range config.Schedules {
		if err := sched.AddSchedule(&config.Schedules[i]); err != nil {
			log.Printf("Warning: Failed to add schedule %s: %v", config.Schedules[i].Name, err)
		}
	}
	sched.Start()

	handler := api.NewHandler(clusterMgr, backupMgr, sched, kmsEncryptor)
	router := handler.SetupRouter()

	go func() {
		log.Println("Starting server on :8080")
		if err := router.Run(":8080"); err != nil {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Println("Shutting down...")
	sched.Stop()
	clusterMgr.Close()
}

func loadConfig() *models.AppConfig {
	config := &models.AppConfig{
		Storage: models.StorageConfig{
			Type:      "local",
			LocalPath: "./data/backups",
		},
		Encryption: models.EncryptionConfig{
			Enabled:   false,
			Algorithm: "AES-256-GCM",
		},
		Clusters:  []models.Cluster{},
		Schedules: []models.Schedule{},
	}

	loadClustersFromEnv(config)
	loadStorageFromEnv(config)
	loadEncryptionFromEnv(config)

	return config
}

func loadClustersFromEnv(config *models.AppConfig) {
	if clusterName := os.Getenv("ETCD_CLUSTER_NAME"); clusterName != "" {
		cluster := models.NewCluster()
		cluster.Name = clusterName
		cluster.Endpoints = []string{"localhost:2379"}
		cluster.Username = os.Getenv("ETCD_USERNAME")
		cluster.Password = os.Getenv("ETCD_PASSWORD")
		config.Clusters = append(config.Clusters, *cluster)
	}
}

func loadStorageFromEnv(config *models.AppConfig) {
	if storageType := os.Getenv("STORAGE_TYPE"); storageType != "" {
		config.Storage.Type = storageType
	}
	if localPath := os.Getenv("STORAGE_LOCAL_PATH"); localPath != "" {
		config.Storage.LocalPath = localPath
	}
	if s3Endpoint := os.Getenv("S3_ENDPOINT"); s3Endpoint != "" {
		config.Storage.S3Endpoint = s3Endpoint
	}
	if s3Bucket := os.Getenv("S3_BUCKET"); s3Bucket != "" {
		config.Storage.S3Bucket = s3Bucket
	}
	if s3Region := os.Getenv("S3_REGION"); s3Region != "" {
		config.Storage.S3Region = s3Region
	}
	if accessKey := os.Getenv("S3_ACCESS_KEY"); accessKey != "" {
		config.Storage.AccessKey = accessKey
	}
	if secretKey := os.Getenv("S3_SECRET_KEY"); secretKey != "" {
		config.Storage.SecretKey = secretKey
	}
}

func loadEncryptionFromEnv(config *models.AppConfig) {
	if os.Getenv("ENCRYPTION_ENABLED") == "true" {
		config.Encryption.Enabled = true
		if key := os.Getenv("ENCRYPTION_KEY"); key != "" {
			config.Encryption.Key = key
		}
	}

	if kmsProvider := os.Getenv("KMS_PROVIDER"); kmsProvider != "" {
		config.Encryption.KMS.Provider = kmsProvider
		config.Encryption.Enabled = true
		if endpoint := os.Getenv("KMS_ENDPOINT"); endpoint != "" {
			config.Encryption.KMS.Endpoint = endpoint
		}
		if region := os.Getenv("KMS_REGION"); region != "" {
			config.Encryption.KMS.Region = region
		}
		if accessKey := os.Getenv("KMS_ACCESS_KEY"); accessKey != "" {
			config.Encryption.KMS.AccessKey = accessKey
		}
		if secretKey := os.Getenv("KMS_SECRET_KEY"); secretKey != "" {
			config.Encryption.KMS.SecretKey = secretKey
		}
		if keyID := os.Getenv("KMS_KEY_ID"); keyID != "" {
			config.Encryption.KMS.KeyID = keyID
		}
		if keyVault := os.Getenv("KMS_KEY_VAULT"); keyVault != "" {
			config.Encryption.KMS.KeyVault = keyVault
		}
		if token := os.Getenv("KMS_TOKEN"); token != "" {
			config.Encryption.KMS.Token = token
		}
	}
}

func checkClusterHealth(ctx context.Context, clusterMgr *cluster.Manager, clusterID string) {
	status, err := clusterMgr.GetClusterStatus(ctx, clusterID)
	if err != nil {
		log.Printf("Failed to get cluster status: %v", err)
		return
	}
	if status.Healthy {
		log.Printf("Cluster %s is healthy", status.Name)
	} else {
		log.Printf("Cluster %s is unhealthy", status.Name)
	}
}
