package main

import (
	"servicemesh-console/config"
	"servicemesh-console/pkg/k8sclient"
	"servicemesh-console/pkg/tracing"
	"servicemesh-console/pkg/server"
	"servicemesh-console/pkg/handler"
	"github.com/sirupsen/logrus"
)

func main() {
	cfg := config.LoadConfig()

	setupLogger(cfg.LogLevel)

	if err := tracing.InitTracer(); err != nil {
		logrus.Fatalf("Failed to initialize tracer: %v", err)
	}
	defer tracing.ShutdownTracer()

	k8sClient, err := k8sclient.NewClient(cfg.KubeConfigPath)
	if err != nil {
		logrus.Fatalf("Failed to create k8s client: %v", err)
	}

	handlers := handler.NewHandlers(k8sClient, cfg.Namespace)

	srv := server.NewServer(cfg.ServerPort, handlers)
	logrus.Infof("Server starting on port %s", cfg.ServerPort)
	if err := srv.Start(); err != nil {
		logrus.Fatalf("Server failed: %v", err)
	}
}

func setupLogger(level string) {
	logLevel, err := logrus.ParseLevel(level)
	if err != nil {
		logLevel = logrus.InfoLevel
	}
	logrus.SetLevel(logLevel)
	logrus.SetFormatter(&logrus.JSONFormatter{})
}
