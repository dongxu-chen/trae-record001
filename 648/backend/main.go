package main

import (
	"os"
	"os/signal"
	"redis-keyspace-notifier/api"
	"redis-keyspace-notifier/config"
	"redis-keyspace-notifier/logger"
	"redis-keyspace-notifier/models"
	"redis-keyspace-notifier/processor"
	"redis-keyspace-notifier/redis"
	"syscall"

	"go.uber.org/zap"
)

func main() {
	config.LoadDefaultConfig()

	logger.Init()
	defer logger.Sync()

	logger.Info("Starting Redis Keyspace Notifier...")

	eventChan := make(chan models.KeyEvent, 10000)

	eventStore := processor.NewEventStore(10000)

	if err := redis.GetClient().Connect(); err != nil {
		logger.Fatal("Failed to connect to Redis", zap.Error(err))
	}
	defer redis.GetClient().Close()

	eventProcessor := processor.NewEventProcessor(eventChan, eventStore)
	eventProcessor.Start()
	defer eventProcessor.Stop()

	subscriber := redis.NewSubscriber(eventChan)
	if err := subscriber.Start(); err != nil {
		logger.Fatal("Failed to start subscriber", zap.Error(err))
	}
	defer subscriber.Stop()

	server := api.NewServer(eventStore, eventProcessor, subscriber)
	go func() {
		if err := server.Start(); err != nil {
			logger.Fatal("Failed to start HTTP server", zap.Error(err))
		}
	}()

	logger.Info("Redis Keyspace Notifier started successfully")

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	logger.Info("Shutting down...")
}
