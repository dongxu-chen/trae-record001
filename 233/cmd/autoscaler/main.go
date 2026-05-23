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

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/cloud-autoscaler/pkg/cloud"
	_ "github.com/cloud-autoscaler/pkg/cloud/aws"
	_ "github.com/cloud-autoscaler/pkg/cloud/aliyun"
	_ "github.com/cloud-autoscaler/pkg/cloud/tencent"
	"github.com/cloud-autoscaler/pkg/config"
	"github.com/cloud-autoscaler/pkg/cost"
	"github.com/cloud-autoscaler/pkg/history"
	"github.com/cloud-autoscaler/pkg/metrics"
	"github.com/cloud-autoscaler/pkg/scaling"
)

var (
	configFile = flag.String("config", "config.yaml", "Path to configuration file")
	httpAddr   = flag.String("http-addr", ":8080", "HTTP server address")
	dryRun     = flag.Bool("dry-run", false, "Run in dry-run mode (no actual scaling)")
)

var (
	scalingDecisionsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "autoscaler_scaling_decisions_total",
			Help: "Total number of scaling decisions made",
		},
		[]string{"decision"},
	)
	scalingActionsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "autoscaler_scaling_actions_total",
			Help: "Total number of scaling actions executed",
		},
		[]string{"action", "status"},
	)
	currentInstances = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "autoscaler_current_instances",
			Help: "Current number of instances",
		},
	)
	cpuUtilization = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "autoscaler_cpu_utilization_percent",
			Help: "Current CPU utilization percentage",
		},
	)
	memoryUtilization = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "autoscaler_memory_utilization_percent",
			Help: "Current memory utilization percentage",
		},
	)
	slidingWindowAvgCPU = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "autoscaler_sliding_window_avg_cpu_percent",
			Help: "Sliding window average CPU utilization percentage",
		},
	)
	slidingWindowAvgMemory = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "autoscaler_sliding_window_avg_memory_percent",
			Help: "Sliding window average memory utilization percentage",
		},
	)
	monthlyCost = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "autoscaler_monthly_cost_dollars",
			Help: "Estimated monthly cost in dollars",
		},
	)
	potentialMonthlySaving = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "autoscaler_potential_monthly_saving_dollars",
			Help: "Potential monthly cost saving from optimization",
		},
	)
)

func init() {
	prometheus.MustRegister(scalingDecisionsTotal)
	prometheus.MustRegister(scalingActionsTotal)
	prometheus.MustRegister(currentInstances)
	prometheus.MustRegister(cpuUtilization)
	prometheus.MustRegister(memoryUtilization)
	prometheus.MustRegister(slidingWindowAvgCPU)
	prometheus.MustRegister(slidingWindowAvgMemory)
	prometheus.MustRegister(monthlyCost)
	prometheus.MustRegister(potentialMonthlySaving)
}

type Autoscaler struct {
	cfg           *config.Config
	provider      cloud.Provider
	metricsClient *metrics.PrometheusClient
	engine        *scaling.ScalingEngine
	historyStore  *history.HistoryStore
	costOptimizer *cost.CostOptimizer
	dryRun        bool
}

func NewAutoscaler(cfg *config.Config, dryRun bool) (*Autoscaler, error) {
	var provider cloud.Provider
	var err error

	if cfg.Cloud.Provider == "hybrid" {
		provider, err = cloud.NewHybridProviderFromConfig(cfg)
	} else {
		provider, err = cloud.NewProvider(cfg)
	}
	if err != nil {
		return nil, fmt.Errorf("failed to create cloud provider: %w", err)
	}

	metricsClient, err := metrics.NewPrometheusClient(&cfg.Prometheus)
	if err != nil {
		return nil, fmt.Errorf("failed to create metrics client: %w", err)
	}

	var predictionCfg *config.PredictionConfig
	if cfg.Prediction.Enabled {
		predictionCfg = &cfg.Prediction
	}

	engine := scaling.NewScalingEngine(&cfg.Scaling, predictionCfg, cfg.Cloud.InstanceGroup, provider, metricsClient)

	var historyStore *history.HistoryStore
	if cfg.History.Enabled {
		maxRecords := cfg.History.MaxRecords
		if maxRecords == 0 {
			maxRecords = 1000
		}
		historyStore = history.NewHistoryStore(cfg.History.FilePath, maxRecords)
	}

	var costOptimizer *cost.CostOptimizer
	if cfg.Cost.Enabled {
		costOptimizer = cost.NewCostOptimizer(provider, 1440)
	}

	return &Autoscaler{
		cfg:           cfg,
		provider:      provider,
		metricsClient: metricsClient,
		engine:        engine,
		historyStore:  historyStore,
		costOptimizer: costOptimizer,
		dryRun:        dryRun,
	}, nil
}

func (a *Autoscaler) Run(ctx context.Context) error {
	log.Printf("Starting autoscaler for instance group: %s", a.cfg.Cloud.InstanceGroup)
	log.Printf("Cloud provider: %s", a.cfg.Cloud.Provider)
	log.Printf("Scaling mode: %s", a.cfg.Scaling.Mode)
	log.Printf("Dry run mode: %v", a.dryRun)
	log.Printf("Metrics interval: %v", a.cfg.Prometheus.Interval)
	log.Printf("Sliding window size: %d", a.cfg.Scaling.SlidingWindowSize)
	log.Printf("Prediction enabled: %v", a.cfg.Prediction.Enabled)
	log.Printf("History enabled: %v", a.cfg.History.Enabled)
	log.Printf("Cost optimization enabled: %v", a.cfg.Cost.Enabled)

	ticker := time.NewTicker(a.cfg.Prometheus.Interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			if err := a.tick(ctx); err != nil {
				log.Printf("Error in tick: %v", err)
			}
		}
	}
}

func (a *Autoscaler) tick(ctx context.Context) error {
	if err := a.engine.CollectMetrics(ctx); err != nil {
		return fmt.Errorf("failed to collect metrics: %w", err)
	}

	cpu, memory, err := a.metricsClient.GetMetrics(ctx)
	if err != nil {
		return fmt.Errorf("failed to get metrics: %w", err)
	}

	cpuUtilization.Set(cpu)
	memoryUtilization.Set(memory)

	instanceCount, err := a.provider.GetInstanceCount(ctx)
	if err != nil {
		return fmt.Errorf("failed to get instance count: %w", err)
	}
	currentInstances.Set(float64(instanceCount))

	if a.costOptimizer != nil {
		instances, err := a.provider.GetInstances(ctx)
		if err == nil {
			for _, inst := range instances {
				a.costOptimizer.UpdateInstanceMetrics(inst.ID, cpu, memory)
			}
			activeIDs := make([]string, len(instances))
			for i, inst := range instances {
				activeIDs[i] = inst.ID
			}
			a.costOptimizer.CleanupStaleInstances(activeIDs)

			instanceType := a.cfg.Cloud.Infrastructure.InstanceType
			costSummary := a.costOptimizer.GetCostSummary(instanceType, instanceCount)
			monthlyCost.Set(costSummary["monthly_cost"].(float64))
			potentialMonthlySaving.Set(costSummary["potential_saving"].(float64))
		}
	}

	decision, count, err := a.engine.Evaluate(ctx)
	if err != nil {
		return fmt.Errorf("failed to evaluate scaling: %w", err)
	}

	decisionStr := decisionToString(decision)
	scalingDecisionsTotal.WithLabelValues(decisionStr).Inc()

	status := a.engine.GetStatus()
	if avgCPU, ok := status["avg_cpu_utilization"].(float64); ok {
		slidingWindowAvgCPU.Set(avgCPU)
	}
	if avgMemory, ok := status["avg_memory_utilization"].(float64); ok {
		slidingWindowAvgMemory.Set(avgMemory)
	}

	log.Printf("Metrics - CPU: %.2f%%, Memory: %.2f%%, Instances: %d", cpu, memory, instanceCount)
	log.Printf("Sliding window avg - CPU: %.2f%%, Memory: %.2f%%, Ready: %v",
		status["avg_cpu_utilization"], status["avg_memory_utilization"], status["window_ready"])
	log.Printf("Scaling status: %s", status["scaling_status"])
	log.Printf("Decision: %s, Count: %d", decisionStr, count)

	if a.cfg.Prediction.Enabled {
		if predCPU, ok := status["next_predicted_cpu"]; ok {
			log.Printf("Next predicted - CPU: %.2f%%, Memory: %.2f%%, Confidence: %.2f",
				predCPU, status["next_predicted_memory"], status["prediction_confidence"])
		}
	}

	if decision != scaling.DecisionNoChange && count > 0 {
		startTime := time.Now()
		instancesBefore := instanceCount
		instancesAfter := instanceCount
		reason := a.determineReason(cpu, memory, decision)

		var costBefore, costAfter, costChange float64
		if a.costOptimizer != nil {
			instanceType := a.cfg.Cloud.Infrastructure.InstanceType
			costBefore = a.costOptimizer.CalculateMonthlyCost(instanceType, instancesBefore)
		}

		execStatus := "success"
		errorMsg := ""

		if a.dryRun {
			log.Printf("Dry run: would have executed %s of %d instances", decisionStr, count)
			scalingActionsTotal.WithLabelValues(decisionStr, "dry_run").Inc()
			execStatus = "dry_run"
		} else {
			log.Printf("Executing %s of %d instances", decisionStr, count)
			if err := a.engine.Execute(ctx, decision, count); err != nil {
				scalingActionsTotal.WithLabelValues(decisionStr, "failed").Inc()
				execStatus = "failed"
				errorMsg = err.Error()
				log.Printf("Failed to execute scaling: %v", err)
			} else {
				scalingActionsTotal.WithLabelValues(decisionStr, "success").Inc()
				log.Printf("Successfully executed %s of %d instances", decisionStr, count)

				if decision == scaling.DecisionScaleUp {
					instancesAfter = instancesBefore + count
				} else if decision == scaling.DecisionScaleDown {
					instancesAfter = instancesBefore - count
				}
			}
		}

		if a.costOptimizer != nil {
			instanceType := a.cfg.Cloud.Infrastructure.InstanceType
			costAfter = a.costOptimizer.CalculateMonthlyCost(instanceType, instancesAfter)
			costChange = costAfter - costBefore
		}

		if a.historyStore != nil {
			record := history.ScalingRecord{
				InstanceGroup:   a.cfg.Cloud.InstanceGroup,
				Action:          history.ScalingAction(decisionStr),
				InstanceCount:   count,
				InstancesBefore: instancesBefore,
				InstancesAfter:  instancesAfter,
				Reason:          reason,
				CPUUtilization:  cpu,
				MemoryUtilization: memory,
				CostBefore:      costBefore,
				CostAfter:       costAfter,
				CostChange:      costChange,
				Status:          execStatus,
				ErrorMessage:    errorMsg,
				DurationMs:      time.Since(startTime).Milliseconds(),
			}
			a.historyStore.AddRecord(record)
		}
	}

	return nil
}

func (a *Autoscaler) determineReason(cpu, memory float64, decision scaling.ScalingDecision) history.ScalingReason {
	targetCPU := a.cfg.Scaling.TargetCPUUtilization
	targetMemory := a.cfg.Scaling.TargetMemoryUtilization

	if decision == scaling.DecisionScaleUp {
		if cpu > targetCPU {
			return history.ReasonHighCPU
		}
		if memory > targetMemory {
			return history.ReasonHighMemory
		}
		if a.cfg.Prediction.Enabled {
			return history.ReasonPredictedLoad
		}
	} else if decision == scaling.DecisionScaleDown {
		if cpu < targetMemory*0.5 {
			return history.ReasonLowCPU
		}
		if memory < targetMemory*0.5 {
			return history.ReasonLowMemory
		}
	}
	return history.ReasonHighCPU
}

func decisionToString(decision scaling.ScalingDecision) string {
	switch decision {
	case scaling.DecisionScaleUp:
		return "scale_up"
	case scaling.DecisionScaleDown:
		return "scale_down"
	default:
		return "no_change"
	}
}

func main() {
	flag.Parse()

	cfg, err := config.Load(*configFile)
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	autoscaler, err := NewAutoscaler(cfg, *dryRun)
	if err != nil {
		log.Fatalf("Failed to create autoscaler: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	http.Handle("/metrics", promhttp.Handler())
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})
	http.HandleFunc("/status", func(w http.ResponseWriter, r *http.Request) {
		status := autoscaler.engine.GetStatus()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(status)
	})
	http.HandleFunc("/history", func(w http.ResponseWriter, r *http.Request) {
		if autoscaler.historyStore == nil {
			http.Error(w, "History not enabled", http.StatusServiceUnavailable)
			return
		}
		records := autoscaler.historyStore.GetLatest(50)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(records)
	})
	http.HandleFunc("/report", func(w http.ResponseWriter, r *http.Request) {
		if autoscaler.historyStore == nil {
			http.Error(w, "History not enabled", http.StatusServiceUnavailable)
			return
		}
		start := time.Now().AddDate(0, 0, -7)
		end := time.Now()
		html := autoscaler.historyStore.GenerateHTMLReport(start, end)
		w.Header().Set("Content-Type", "text/html")
		w.Write([]byte(html))
	})
	http.HandleFunc("/cost", func(w http.ResponseWriter, r *http.Request) {
		if autoscaler.costOptimizer == nil {
			http.Error(w, "Cost optimization not enabled", http.StatusServiceUnavailable)
			return
		}
		suggestions := autoscaler.costOptimizer.GetSuggestions()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"suggestions": suggestions,
			"total_saving_monthly": autoscaler.costOptimizer.GetTotalMonthlySaving(),
		})
	})

	go func() {
		log.Printf("HTTP server listening on %s", *httpAddr)
		if err := http.ListenAndServe(*httpAddr, nil); err != nil {
			log.Printf("HTTP server error: %v", err)
		}
	}()

	go func() {
		if err := autoscaler.Run(ctx); err != nil && err != context.Canceled {
			log.Printf("Autoscaler error: %v", err)
		}
	}()

	<-sigChan
	log.Println("Shutting down...")
	cancel()
	log.Println("Shutdown complete")
}
