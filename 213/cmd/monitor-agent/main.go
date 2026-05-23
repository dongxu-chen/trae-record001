package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"monitor-agent/internal/alert"
	"monitor-agent/internal/collector"
	"monitor-agent/internal/config"
	"monitor-agent/internal/exporter"
	"monitor-agent/internal/storage"
)

func main() {
	configPath := flag.String("config", "config.yaml", "Path to config file")
	flag.Parse()

	log.Println("Starting monitor-agent...")

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}
	log.Println("Config loaded successfully")

	if err := config.Watch(*configPath, nil); err != nil {
		log.Printf("Warning: Failed to start config watcher: %v", err)
	}

	c := collector.NewCollector()
	e := exporter.NewExporter(c)
	am := alert.NewAlertManager()

	var s *storage.Storage
	if cfg.Storage.Enabled {
		var err error
		s, err = storage.NewStorage(cfg.Storage.DataDir, cfg.Storage.RetentionDays)
		if err != nil {
			log.Printf("Warning: Failed to initialize storage: %v", err)
		} else {
			log.Printf("Storage initialized, data dir: %s", cfg.Storage.DataDir)
			defer s.Close()
		}
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go startCollector(ctx, c, e, am, s)
	go startHTTPServer(cfg, e, s)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	log.Println("Shutting down monitor-agent...")
	cancel()
	log.Println("monitor-agent stopped")
}

func startCollector(ctx context.Context, c *collector.Collector, e *exporter.Exporter, am *alert.AlertManager, s *storage.Storage) {
	cfg := config.GetConfig()
	ticker := time.NewTicker(cfg.Collector.GetInterval())
	defer ticker.Stop()

	log.Printf("Collector started, interval: %v", cfg.Collector.GetInterval())

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			metrics, err := c.Collect(ctx)
			if err != nil {
				log.Printf("Collection error: %v", err)
				continue
			}

			e.UpdateMetrics()

			am.CheckAndAlert(metrics.CPUUsage, metrics.MemoryUsage)

			if s != nil {
				if err := s.Save(metrics); err != nil {
					log.Printf("Failed to save metrics: %v", err)
				}
			}
		}
	}
}

func startHTTPServer(cfg *config.Config, e *exporter.Exporter, s *storage.Storage) {
	addr := fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
	http.Handle("/metrics", e.Handler())

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	http.HandleFunc("/api/history", func(w http.ResponseWriter, r *http.Request) {
		if s == nil {
			http.Error(w, "Storage not enabled", http.StatusServiceUnavailable)
			return
		}

		startStr := r.URL.Query().Get("start")
		endStr := r.URL.Query().Get("end")

		var startTime, endTime time.Time
		var err error

		if startStr != "" {
			startTime, err = time.Parse(time.RFC3339, startStr)
			if err != nil {
				http.Error(w, "Invalid start time, use RFC3339 format", http.StatusBadRequest)
				return
			}
		} else {
			startTime = time.Now().Add(-1 * time.Hour)
		}

		if endStr != "" {
			endTime, err = time.Parse(time.RFC3339, endStr)
			if err != nil {
				http.Error(w, "Invalid end time, use RFC3339 format", http.StatusBadRequest)
				return
			}
		} else {
			endTime = time.Now()
		}

		records, err := s.Query(startTime, endTime)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"start":   startTime,
			"end":     endTime,
			"count":   len(records),
			"records": records,
		})
	})

	log.Printf("HTTP server starting on %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("Failed to start HTTP server: %v", err)
	}
}
