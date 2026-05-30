package main

import (
	"context"
	"log"

	"k8s-network-policy-recommender/pkg/api"
	"k8s-network-policy-recommender/pkg/config"
	"k8s-network-policy-recommender/pkg/k8s"
	"k8s-network-policy-recommender/pkg/neo4jclient"
)

func main() {
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	neo4jClient, err := neo4jclient.NewClient(cfg.Neo4j)
	if err != nil {
		log.Fatalf("Failed to create Neo4j client: %v", err)
	}
	defer neo4jClient.Close()

	if err := neo4jClient.InitSchema(context.Background()); err != nil {
		log.Fatalf("Failed to init Neo4j schema: %v", err)
	}

	k8sClient, err := k8s.NewClient(cfg.Kubernetes)
	if err != nil {
		log.Fatalf("Failed to create K8s client: %v", err)
	}

	router := api.SetupRouter(cfg, neo4jClient, k8sClient)

	log.Printf("Server starting on port %s", cfg.Server.Port)
	if err := router.Run(":" + cfg.Server.Port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
