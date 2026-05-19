package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"ssl-manager/internal/acme"
	"ssl-manager/internal/cert"
	"ssl-manager/internal/config"
	"ssl-manager/internal/dns"
	"ssl-manager/internal/monitoring"
	"ssl-manager/internal/security"
	"ssl-manager/internal/tenant"
)

func main() {
	configPath := flag.String("config", "config.yaml", "Path to config file")
	once := flag.Bool("once", false, "Run once and exit")
	genKey := flag.Bool("gen-key", false, "Generate HSM master key")
	keyOutput := flag.String("key-output", "master.key", "HSM master key output path")
	flag.Parse()

	if *genKey {
		generateMasterKey(*keyOutput)
		return
	}

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("Load config failed: %v", err)
	}

	tenantManager := tenant.NewManager(cfg)

	var monitor *monitoring.Monitor
	if cfg.Monitoring.Enabled {
		monitor = monitoring.NewMonitor(cfg, tenantManager)
		go func() {
			log.Printf("Starting monitoring server on %s", cfg.Monitoring.ListenAddr)
			if err := monitor.StartServer(cfg.Monitoring.ListenAddr); err != nil {
				log.Printf("Monitoring server error: %v", err)
			}
		}()
	}

	acmeClient, err := acme.NewClient(cfg)
	if err != nil {
		log.Fatalf("Create ACME client failed: %v", err)
	}

	dnsProvider, err := dns.NewProvider(&cfg.DNS)
	if err != nil {
		log.Fatalf("Create DNS provider failed: %v", err)
	}

	challengeProvider := dns.NewChallengeProvider(dnsProvider)
	if err := acmeClient.SetDNSProvider(challengeProvider); err != nil {
		log.Fatalf("Set DNS provider failed: %v", err)
	}

	certManager := cert.NewManager(cfg, acmeClient)

	if *once {
		log.Println("Running once...")
		if err := certManager.CheckAndRenewAll(); err != nil {
			log.Fatalf("Check and renew failed: %v", err)
		}
		log.Println("Done")
		return
	}

	checkInterval, err := time.ParseDuration(cfg.Renewal.CheckInterval)
	if err != nil {
		log.Fatalf("Parse check interval failed: %v", err)
	}

	log.Printf("SSL Manager started, checking every %v", checkInterval)

	ticker := time.NewTicker(checkInterval)
	defer ticker.Stop()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	if err := certManager.CheckAndRenewAll(); err != nil {
		log.Printf("Initial check and renew failed: %v", err)
	}

	for {
		select {
		case <-ticker.C:
			log.Println("Starting scheduled certificate check...")
			if err := certManager.CheckAndRenewAll(); err != nil {
				log.Printf("Check and renew failed: %v", err)
			}
			if monitor != nil {
				if _, err := monitor.CollectData(); err != nil {
					log.Printf("Collect monitoring data failed: %v", err)
				}
			}
		case sig := <-sigChan:
			log.Printf("Received signal %v, shutting down...", sig)
			return
		}
	}
}

func generateMasterKey(outputPath string) {
	key, err := security.GenerateMasterKey()
	if err != nil {
		log.Fatalf("Generate master key failed: %v", err)
	}

	if err := os.WriteFile(outputPath, key, 0600); err != nil {
		log.Fatalf("Save master key failed: %v", err)
	}

	log.Printf("Master key generated and saved to %s", outputPath)
	log.Println("WARNING: Keep this key safe! Losing it will make all encrypted private keys unrecoverable.")
}
