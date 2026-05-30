package main

import (
	"context"
	"flag"
	"os"
	"os/signal"
	"syscall"

	"github.com/sirupsen/logrus"

	"github.com/keymgmt/service/csi-driver/internal/driver"
	"github.com/keymgmt/service/csi-driver/internal/server"
)

var (
	nodeID         = flag.String("nodeid", "", "Node ID")
	endpoint       = flag.String("endpoint", "unix:///csi/csi.sock", "CSI endpoint")
	apiBaseURL     = flag.String("api-url", "http://keymgmt-service:8080", "Key Management API URL")
	apiToken       = flag.String("api-token", "", "API authentication token")
	useLocalSecrets = flag.Bool("use-local-secrets", false, "Use local API instead of K8s secrets (no RBAC required)")
)

func main() {
	flag.Parse()

	log := logrus.New()
	log.SetFormatter(&logrus.JSONFormatter{})
	log.SetOutput(os.Stdout)
	log.SetLevel(logrus.InfoLevel)

	if *nodeID == "" {
		*nodeID = os.Getenv("NODE_ID")
		if *nodeID == "" {
			hostname, err := os.Hostname()
			if err != nil {
				log.Fatalf("Failed to get hostname: %v", err)
			}
			*nodeID = hostname
		}
	}

	if *apiToken == "" {
		*apiToken = os.Getenv("API_TOKEN")
	}

	log.Infof("Starting CSI Driver: node=%s, endpoint=%s, useLocalSecrets=%v", *nodeID, *endpoint, *useLocalSecrets)

	drv, err := driver.NewKeyManagementDriver(*nodeID, *endpoint, *apiBaseURL, *apiToken, *useLocalSecrets, log)
	if err != nil {
		log.Fatalf("Failed to create driver: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	srv := server.NewServer(*endpoint, drv, drv, drv, log)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigCh
		log.Info("Received shutdown signal")
		cancel()
	}()

	if err := srv.Start(ctx); err != nil {
		log.Fatalf("Server error: %v", err)
	}

	log.Info("CSI Driver stopped")
}
