package main

import (
	"log"

	"k8s-cost-allocation/internal/api"
	"k8s-cost-allocation/internal/config"
	"k8s-cost-allocation/internal/cost"
	"k8s-cost-allocation/internal/k8sclient"
	"k8s-cost-allocation/internal/promclient"
)

func main() {
	cfg, err := config.LoadConfig("config.yaml")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	k8sClient, err := k8sclient.NewClient(cfg.Kubernetes)
	if err != nil {
		log.Fatalf("Failed to create Kubernetes client: %v", err)
	}

	promClient, err := promclient.NewClient(cfg.Prometheus)
	if err != nil {
		log.Fatalf("Failed to create Prometheus client: %v", err)
	}

	costCalculator := cost.NewCalculator(cfg.Cost, cfg.Budgets, cfg.Pricing, k8sClient, promClient)

	router := api.SetupRouter(cfg, k8sClient, promClient, costCalculator)

	log.Printf("Server starting on port %s", cfg.Server.Port)
	if err := router.Run(":" + cfg.Server.Port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
