package main

import (
	"cloud-tag-compliance/internal/api"
	"cloud-tag-compliance/internal/audit"
	"cloud-tag-compliance/internal/auth"
	"cloud-tag-compliance/internal/cloud"
	"cloud-tag-compliance/internal/config"
	"cloud-tag-compliance/internal/cost"
	"cloud-tag-compliance/internal/nlparser"
	"cloud-tag-compliance/internal/rules"
	"cloud-tag-compliance/internal/suggestion"
	"cloud-tag-compliance/internal/templates"
	"log"
)

func main() {
	cfg, err := config.Load("config/config.yaml")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	cloudManager := cloud.NewManager(cfg)

	ruleEngine := rules.NewEngine()
	if err := ruleEngine.LoadRules("config/rules.yaml"); err != nil {
		log.Printf("Warning: Failed to load rules: %v", err)
	}

	trustManager := auth.NewTrustManager(cfg)

	suggestionEngine := suggestion.NewSuggestionEngine()
	suggestionEngine.LearnFromResources(cloudManager.GetAllResources())

	nlParser := nlparser.NewNLParser()

	costEngine := cost.NewAllocationEngine()

	auditLogger := audit.NewAuditLogger("data/audit_logs.json")

	templateManager := templates.NewTemplateManager("data/templates.json")

	router := api.SetupRouter(cloudManager, ruleEngine, cfg, trustManager, suggestionEngine, nlParser, costEngine, auditLogger, templateManager)

	log.Printf("Server starting on :%d", cfg.Server.Port)
	if err := router.Run(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
