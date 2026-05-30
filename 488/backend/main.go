package main

import (
	"deadlock-resolver/api"
	"deadlock-resolver/config"
	"deadlock-resolver/database"
	"deadlock-resolver/engine"
	"fmt"
	"log"

	"github.com/gin-gonic/gin"
)

func main() {
	cfg := config.DefaultConfig()

	connector, err := database.NewConnector(&cfg.Database)
	if err != nil {
		log.Fatalf("Failed to create database connector: %v", err)
	}

	err = connector.Connect()
	if err != nil {
		log.Printf("Warning: Failed to connect to database: %v", err)
		log.Println("Starting in simulation mode...")
	} else {
		defer connector.Close()
	}

	detector := engine.NewDeadlockDetector(connector, cfg)

	r := gin.Default()

	handler := api.NewHandler(detector, cfg)
	handler.SetupRoutes(r)

	log.Printf("Starting Deadlock Resolver Server on port %d...", cfg.HTTPPort)
	log.Printf("Database Type: %s", cfg.Database.Type)
	log.Printf("Auto Kill Enabled: %v", cfg.Strategy.AutoKill)
	log.Printf("Detection Interval: %v", cfg.Strategy.DetectionInterval)

	err = r.Run(fmt.Sprintf(":%d", cfg.HTTPPort))
	if err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
