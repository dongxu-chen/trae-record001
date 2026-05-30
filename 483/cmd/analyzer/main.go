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
	"strconv"
	"syscall"
	"time"

	"kafka-lag-analyzer/internal/analyzer"
	"kafka-lag-analyzer/internal/config"
	"kafka-lag-analyzer/internal/kafka"
	"kafka-lag-analyzer/internal/metrics"
	"kafka-lag-analyzer/internal/prober"
)

func main() {
	configPath := flag.String("config", "config.yaml", "Path to configuration file")
	flag.Parse()

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	kafkaClient, err := kafka.NewClient(&cfg.Kafka)
	if err != nil {
		log.Fatalf("Failed to create kafka client: %v", err)
	}
	defer kafkaClient.Close()

	var rttProber prober.Prober
	if cfg.Kafka.EnableRTTProbe {
		rttProber, err = prober.NewProber(&cfg.Kafka)
		if err != nil {
			log.Printf("Warning: Failed to create RTT prober (falling back to passive mode): %v", err)
			rttProber = nil
		}
	}

	lagAnalyzer := analyzer.NewAnalyzer(kafkaClient, rttProber, &cfg.Analyzer, &cfg.Kafka)
	metricsExporter := metrics.NewExporter()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go runAnalysisLoop(ctx, lagAnalyzer, metricsExporter, cfg.Kafka.ScrapeInterval)

	if rttProber != nil {
		go rttProber.Start(ctx, cfg.Kafka.RTTProbeInterval)
		log.Printf("RTT prober started with interval %v", cfg.Kafka.RTTProbeInterval)
	}

	mux := http.NewServeMux()
	setupRoutes(mux, lagAnalyzer, metricsExporter, cfg, rttProber)

	serverAddr := fmt.Sprintf("%s:%d", cfg.Server.Host, cfg.Server.Port)
	server := &http.Server{
		Addr:    serverAddr,
		Handler: mux,
	}

	go func() {
		log.Printf("Starting server on %s", serverAddr)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	<-sigChan
	log.Println("Shutting down...")

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("Server shutdown error: %v", err)
	}

	cancel()
	log.Println("Shutdown complete")
}

func runAnalysisLoop(ctx context.Context, lagAnalyzer analyzer.Analyzer, exporter metrics.Exporter, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			analyses, err := lagAnalyzer.Analyze()
			if err != nil {
				log.Printf("Analysis error: %v", err)
				continue
			}

			for _, analysis := range analyses {
				log.Printf("Group %s: total_lag=%d, status=%s, members=%d, topics=%d, hot_partitions=%d",
					analysis.GroupID,
					analysis.TotalLag,
					analysis.OverallStatus,
					analysis.MemberCount,
					len(analysis.Topics),
					len(analysis.HotPartitions),
				)

				if analysis.NetworkRTTSummary != nil {
					log.Printf("  RTT: avg=%.1fms, max=%.1fms, high_rtt_brokers=%d/%d",
						float64(analysis.NetworkRTTSummary.OverallAvgRTT.Microseconds())/1000,
						float64(analysis.NetworkRTTSummary.OverallMaxRTT.Microseconds())/1000,
						analysis.NetworkRTTSummary.HighRTTCount,
						analysis.NetworkRTTSummary.BrokerCount,
					)
				}

				for _, attr := range analysis.DelayAttributions {
					log.Printf("  -> %s (confidence=%.2f, severity=%s): %s",
						attr.Cause,
						attr.Confidence,
						attr.Severity,
						attr.Description,
					)
				}

				codeOptRecs := 0
				for _, rec := range analysis.Recommendations {
					if rec.Category == "CodeOptimization" {
						codeOptRecs++
					}
				}
				if codeOptRecs > 0 {
					log.Printf("  Code optimization recommendations: %d", codeOptRecs)
				}
			}

			exporter.Update(analyses)
		}
	}
}

func setupRoutes(mux *http.ServeMux, lagAnalyzer analyzer.Analyzer, exporter metrics.Exporter, cfg *config.Config, rttProber prober.Prober) {
	if cfg.Metrics.EnablePrometheus {
		mux.Handle(cfg.Metrics.Path, exporter.Handler())
	}

	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	mux.HandleFunc("/api/analysis", func(w http.ResponseWriter, r *http.Request) {
		analyses := lagAnalyzer.GetLatestAnalysis()
		if analyses == nil {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]string{"error": "No analysis available yet"})
			return
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(analyses)
	})

	mux.HandleFunc("/api/analysis/{group}", func(w http.ResponseWriter, r *http.Request) {
		groupID := r.PathValue("group")
		analyses := lagAnalyzer.GetLatestAnalysis()
		if analyses == nil {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]string{"error": "No analysis available yet"})
			return
		}

		for _, analysis := range analyses {
			if analysis.GroupID == groupID {
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(analysis)
				return
			}
		}

		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "Consumer group not found"})
	})

	mux.HandleFunc("/api/history/{group}/{topic}/{partition}", func(w http.ResponseWriter, r *http.Request) {
		groupID := r.PathValue("group")
		topic := r.PathValue("topic")
		partitionStr := r.PathValue("partition")

		partition, err := strconv.Atoi(partitionStr)
		if err != nil {
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(map[string]string{"error": "Invalid partition number"})
			return
		}

		history := lagAnalyzer.GetPartitionHistory(groupID, topic, int32(partition))
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(history)
	})

	mux.HandleFunc("/api/groups", func(w http.ResponseWriter, r *http.Request) {
		analyses := lagAnalyzer.GetLatestAnalysis()
		if analyses == nil {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]string{"error": "No analysis available yet"})
			return
		}

		groups := make([]string, 0, len(analyses))
		for _, analysis := range analyses {
			groups = append(groups, analysis.GroupID)
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(groups)
	})

	if rttProber != nil {
		mux.HandleFunc("/api/rtt", func(w http.ResponseWriter, r *http.Request) {
			result := rttProber.GetLatestResult()
			if result == nil {
				w.WriteHeader(http.StatusNotFound)
				json.NewEncoder(w).Encode(map[string]string{"error": "No RTT probe data available yet"})
				return
			}

			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(result)
		})
	}
}
