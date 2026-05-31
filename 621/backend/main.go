package main

import (
	"log"
	"net/http"
	"os"

	"authz-policy-recommender/backend/api"
	"authz-policy-recommender/backend/pkg/analyzer"
	"authz-policy-recommender/backend/pkg/compliance"
	"authz-policy-recommender/backend/pkg/conflict"
	"authz-policy-recommender/backend/pkg/deployer"
	"authz-policy-recommender/backend/pkg/evaluator"
	"authz-policy-recommender/backend/pkg/generator"
	"authz-policy-recommender/backend/pkg/simulator"
	"authz-policy-recommender/backend/pkg/visualizer"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func main() {
	r := gin.Default()

	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}
	config.AllowHeaders = []string{"*"}
	r.Use(cors.New(config))

	callAnalyzer := analyzer.NewCallAnalyzer()
	policyGenerator := generator.NewPolicyGenerator()
	conflictDetector := conflict.NewConflictDetector()
	policySimulator := simulator.NewPolicySimulator()
	complianceChecker := compliance.NewComplianceChecker()
	scenarioChecker := compliance.NewScenarioChecker()
	policyDeployer := deployer.NewPolicyDeployer()
	effectivenessEvaluator := evaluator.NewPolicyEffectivenessEvaluator(policySimulator)
	policyVisualizer := visualizer.NewPolicyVisualizer()

	handler := api.NewHandler(
		callAnalyzer,
		policyGenerator,
		conflictDetector,
		policySimulator,
		complianceChecker,
		scenarioChecker,
		policyDeployer,
		effectivenessEvaluator,
		policyVisualizer,
	)

	api.RegisterRoutes(r, handler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Server starting on port %s...", port)
	if err := r.Run(":" + port); err != nil && err != http.ErrServerClosed {
		log.Fatalf("Failed to start server: %v", err)
	}
}
