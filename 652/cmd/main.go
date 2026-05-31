package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"

	"kafka-mirror/config"
	"kafka-mirror/mirror"
)

func main() {
	configPath := flag.String("config", "config/config.yaml", "Path to configuration file")
	flag.Parse()

	cfg, err := config.LoadConfig(*configPath)
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	mirrorService, err := mirror.NewKafkaMirror(cfg)
	if err != nil {
		log.Fatalf("Failed to create Kafka mirror: %v", err)
	}

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		if err := mirrorService.Start(); err != nil {
			log.Fatalf("Kafka mirror failed: %v", err)
		}
	}()

	<-sigChan
	log.Println("Received shutdown signal")

	mirrorService.Stop()
	log.Println("Shutdown complete")
}
