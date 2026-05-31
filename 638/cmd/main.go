package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/k8s-autoscaler/pkg/api"
	"github.com/k8s-autoscaler/pkg/benefit"
	"github.com/k8s-autoscaler/pkg/controller"
	"github.com/k8s-autoscaler/pkg/cost"
	"github.com/k8s-autoscaler/pkg/linkage"
	"github.com/k8s-autoscaler/pkg/metrics"
	"github.com/k8s-autoscaler/pkg/predictor"
	"github.com/k8s-autoscaler/pkg/recommender"
	"github.com/k8s-autoscaler/pkg/scaler"
	"github.com/k8s-autoscaler/pkg/tuner"
)

func main() {
	mode := os.Getenv("AUTOSCALER_MODE")
	if mode == "" {
		mode = "demo"
	}

	var collector controller.MetricsCollector

	if mode == "demo" {
		collector = metrics.NewMockMetricsCollector(3)
	} else {
		kubeConfig := os.Getenv("KUBECONFIG")
		promURL := os.Getenv("PROMETHEUS_URL")
		if promURL == "" {
			promURL = "http://prometheus-server:9090"
		}
		fmt.Printf("Starting in live mode, kubeconfig=%s, prometheus=%s\n", kubeConfig, promURL)
		return
	}

	predEngine := predictor.NewPredictionEngine(10)

	recommenderCfg := recommender.RecommenderConfig{
		CPUTarget:             200,
		MemoryTarget:          512 * 1024 * 1024,
		QPSTarget:             100,
		LatencyTarget:         0.2,
		ScaleUpCooldown:       3 * time.Minute,
		ScaleDownCooldown:     5 * time.Minute,
		MaxScaleUpRatio:       2.0,
		MaxScaleDownRatio:     2.0,
		EnableCompositeThreshold: true,
		CompositeTarget:       0.75,
		FusionWeights: map[recommender.MetricType]float64{
			recommender.MetricCPU:    0.4,
			recommender.MetricMemory: 0.3,
			recommender.MetricQPS:    0.3,
		},
	}
	hpaRecommender := recommender.NewHPARecommender(recommenderCfg)

	scalerCfg := scaler.PredictiveScalerConfig{
		LookAheadDuration:   30 * time.Minute,
		ScaleUpThreshold:    0.8,
		ScaleDownThreshold:  0.3,
		MinReplicas:         1,
		MaxReplicas:         50,
		PredictionWeights:   []float64{0.2, 0.2, 0.15, 0.15, 0.3},
		StabilizationWindow: 5 * time.Minute,
	}
	predictiveScaler := scaler.NewPredictiveScaler(scalerCfg, predEngine)

	nodeCosts := []cost.NodeCost{
		{NodeType: "n1-standard-4", HourlyCost: 0.190, CPU: 4, Memory: 15 * 1024 * 1024 * 1024},
		{NodeType: "n1-standard-8", HourlyCost: 0.380, CPU: 8, Memory: 30 * 1024 * 1024 * 1024},
		{NodeType: "n1-standard-16", HourlyCost: 0.760, CPU: 16, Memory: 60 * 1024 * 1024 * 1024},
	}
	slaConstraints := []cost.SLAConstraint{
		{
			Name:     "minReplicas",
			Type:     "MinReplicas",
			Value:    2,
			Operator: ">=",
			Priority: 100,
		},
		{
			Name:     "availability",
			Type:     "Availability",
			Value:    99.95,
			Operator: ">=",
			Priority: 90,
		},
		{
			Name:     "latencyP99",
			Type:     "LatencyP99",
			Value:    0.3,
			Operator: "<=",
			Priority: 80,
		},
		{
			Name:     "throughput",
			Type:     "Throughput",
			Value:    100,
			Operator: ">=",
			Priority: 70,
		},
	}
	costOptimizer := cost.NewCostOptimizerWithSLA(nodeCosts, slaConstraints)

	initialParams := tuner.TunableParams{
		ScaleUpThreshold:    0.8,
		ScaleDownThreshold:  0.3,
		CompositeTarget:     0.75,
		ScaleUpCooldownSec:  180,
		ScaleDownCooldownSec: 300,
		MaxScaleUpRatio:     2.0,
		FusionWeights: map[string]float64{
			"CPU":    0.4,
			"Memory": 0.3,
			"QPS":    0.3,
		},
	}
	autoTuner := tuner.NewAutoTuner(initialParams, 100)

	dependencies := []linkage.ServiceDependency{
		{
			SourceService:     "web-frontend",
			SourceNamespace:   "default",
			TargetService:     "api-server",
			TargetNamespace:   "default",
			CorrelationStrength: 0.85,
			LagSeconds:        30,
			MinTriggerScale:   1,
			Weight:            0.7,
		},
		{
			SourceService:     "api-server",
			SourceNamespace:   "default",
			TargetService:     "payment-service",
			TargetNamespace:   "production",
			CorrelationStrength: 0.9,
			LagSeconds:        60,
			MinTriggerScale:   1,
			Weight:            0.5,
		},
	}
	linkageGraph := linkage.NewLinkageGraph(dependencies)

	revenueModel := benefit.RevenueModel{
		RevenuePerQPS:          0.005,
		LatencyPenaltyPerSecond: 10.0,
		DowntimeCostPerMinute:  1000.0,
		SLAErrorPenalty:        5000.0,
	}
	costBenefit := benefit.NewCostBenefitAnalyzer(revenueModel, nodeCosts)

	ctrlCfg := controller.ControllerConfig{
		ReconcileInterval:      30 * time.Second,
		MetricsWindow:          2 * time.Hour,
		PredictiveLookAhead:    30 * time.Minute,
		EnablePredictive:       true,
		EnableCostOptimization: true,
		EnableAutoTuning:       true,
		EnableLinkage:          true,
		EnableCostBenefit:      true,
		DryRun:                 true,
	}
	ctrl := controller.NewController(
		ctrlCfg,
		collector,
		predEngine,
		hpaRecommender,
		predictiveScaler,
		costOptimizer,
		autoTuner,
		linkageGraph,
		costBenefit,
	)

	ctrl.WatchDeployment("default", "web-frontend")
	ctrl.WatchDeployment("default", "api-server")
	ctrl.WatchDeployment("production", "payment-service")

	if err := ctrl.Start(); err != nil {
		log.Fatalf("Failed to start controller: %v", err)
	}

	server := api.NewServer(ctrl, 8080)

	go func() {
		fmt.Println("Starting K8s Autoscaler API server on :8080")
		if err := server.Start(); err != nil {
			log.Fatalf("API server error: %v", err)
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	<-sigCh

	fmt.Println("\nShutting down...")
	ctrl.Stop()
	server.Stop()
	fmt.Println("Shutdown complete")
}
