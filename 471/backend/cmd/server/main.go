package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/spf13/viper"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"

	"github.com/keymgmt/service/backend/internal/api"
	"github.com/keymgmt/service/backend/internal/audit"
	"github.com/keymgmt/service/backend/internal/audit/async"
	"github.com/keymgmt/service/backend/internal/models"
	"github.com/keymgmt/service/backend/internal/vault"
)

func main() {
	log := logrus.New()
	log.SetFormatter(&logrus.JSONFormatter{})
	log.SetOutput(os.Stdout)
	log.SetLevel(logrus.InfoLevel)

	viper.SetConfigName("config")
	viper.SetConfigType("yaml")
	viper.AddConfigPath(".")
	viper.AddConfigPath("./config")
	viper.AutomaticEnv()

	viper.SetDefault("server.port", "8080")
	viper.SetDefault("database.path", "./data/secrets.db")
	viper.SetDefault("vault.address", "http://localhost:8200")
	viper.SetDefault("vault.token", "")
	viper.SetDefault("vault.mount_path", "secret")
	viper.SetDefault("audit.async_enabled", true)
	viper.SetDefault("audit.buffer_size", 10000)
	viper.SetDefault("audit.batch_size", 100)
	viper.SetDefault("audit.flush_interval_seconds", 5)

	if err := viper.ReadInConfig(); err != nil {
		log.Warnf("No config file found, using defaults: %v", err)
	}

	dbPath := viper.GetString("database.path")
	if err := os.MkdirAll("./data", 0755); err != nil {
		log.Fatalf("Failed to create data directory: %v", err)
	}

	db, err := gorm.Open(sqlite.Open(dbPath), &gorm.Config{})
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	if err := db.AutoMigrate(&models.Secret{}, &models.Label{}, &models.AuditLog{}, &models.SecretVersion{}); err != nil {
		log.Fatalf("Failed to migrate database: %v", err)
	}

	var vaultClient *vault.VaultClient
	vaultCfg := vault.Config{
		Address:   viper.GetString("vault.address"),
		Token:     viper.GetString("vault.token"),
		MountPath: viper.GetString("vault.mount_path"),
	}
	if vaultCfg.Token != "" {
		var err error
		vaultClient, err = vault.NewVaultClient(vaultCfg, log)
		if err != nil {
			log.Warnf("Failed to initialize Vault client: %v", err)
			log.Warn("Running in local encryption mode")
		}

		if vaultClient != nil {
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			if err := vaultClient.CreateEncryptionKey(ctx, "secrets-key"); err != nil {
				log.Warnf("Failed to create encryption key in Vault: %v", err)
			}
		}
	} else {
		log.Warn("No Vault token configured, running in local encryption mode")
	}

	asyncEnabled := viper.GetBool("audit.async_enabled")
	asyncCfg := async.Config{
		BufferSize:    viper.GetInt("audit.buffer_size"),
		BatchSize:     viper.GetInt("audit.batch_size"),
		FlushInterval: time.Duration(viper.GetInt("audit.flush_interval_seconds")) * time.Second,
	}

	auditService := audit.NewAuditServiceWithAsync(db, log, asyncEnabled, asyncCfg)
	defer auditService.Stop()

	router := api.SetupRouter(db, vaultClient, auditService, log)

	port := viper.GetString("server.port")
	serverAddr := fmt.Sprintf(":%s", port)

	go func() {
		log.Infof("Starting key management service on %s", serverAddr)
		if err := router.Run(serverAddr); err != nil {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_ = ctx

	log.Info("Server gracefully stopped")
}
