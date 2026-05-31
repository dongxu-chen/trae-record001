package main

import (
	"log"

	"mysql-partition-tool/api"
	"mysql-partition-tool/config"
)

func main() {
	config.Load()

	log.Println("Starting MySQL Partition Tool Server...")
	log.Printf("Server will run on port: %s", config.AppConfig.ServerPort)

	r := api.SetupRouter()

	if err := r.Run(":" + config.AppConfig.ServerPort); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
