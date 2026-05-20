package main

import (
	"log"

	"github.com/gin-gonic/gin"
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"

	"prometheus-alert-manager/models"
	"prometheus-alert-manager/routes"
)

func main() {
	db, err := gorm.Open(sqlite.Open("alert_rules.db"), &gorm.Config{})
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}

	err = db.AutoMigrate(
		&models.AlertRule{},
		&models.AlertRuleVersion{},
		&models.AlertGroup{},
	)
	if err != nil {
		log.Fatalf("Failed to migrate database: %v", err)
	}

	r := gin.Default()

	routes.SetupRoutes(r, db)

	log.Println("Server starting on :8080")
	r.Run(":8080")
}
