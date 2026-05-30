package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"rabbitmq-lb/pkg/autoscaler"
	"rabbitmq-lb/pkg/balancer"
	"rabbitmq-lb/pkg/config"
	"rabbitmq-lb/pkg/drill"
	"rabbitmq-lb/pkg/metrics"
	"rabbitmq-lb/pkg/monitor"
	"rabbitmq-lb/pkg/predictor"
	"rabbitmq-lb/pkg/rabbitmq"
	"rabbitmq-lb/pkg/tenant"
)

type LoadBalancer struct {
	config          *config.Config
	rabbitClient    *rabbitmq.Client
	monitor         *monitor.Monitor
	migrator        *balancer.Migrator
	failureDetector *balancer.FailureDetector
	predictor       *predictor.TimeSeriesPredictor
	exporter        *metrics.Exporter
	tenantManager   *tenant.TenantManager
	autoScaler      *autoscaler.AutoScaler
	drillRunner     *drill.DrillRunner
	ctx             context.Context
	cancel          context.CancelFunc
	rebalanceChan   chan struct{}
}

func NewLoadBalancer(cfg *config.Config) (*LoadBalancer, error) {
	client := rabbitmq.NewClient(rabbitmq.ClientConfig{
		BaseURL:  cfg.RabbitMQ.URL,
		Username: cfg.RabbitMQ.Username,
		Password: cfg.RabbitMQ.Password,
		Timeout:  cfg.RabbitMQ.Timeout,
	})

	mon := monitor.NewMonitor(client)
	migrator := balancer.NewMigrator(client, &cfg.Balancer)
	failureDetector := balancer.NewFailureDetector(cfg.Balancer.NodeFailureTimeout)

	var pred *predictor.TimeSeriesPredictor
	if cfg.Prediction.Enabled {
		pred = predictor.NewTimeSeriesPredictor(
			cfg.Prediction.DataPoints,
			cfg.Prediction.CollectionInterval,
		)
		pred.SetBurstThreshold(cfg.Prediction.BurstThreshold)
		pred.SetBurstDetectionWindow(cfg.Prediction.BurstDetectionWindow)
	}

	exporter := metrics.NewExporter()

	var tm *tenant.TenantManager
	if cfg.Tenant.Enabled {
		tm = tenant.NewTenantManager(&cfg.Tenant, client)
	}

	var as *autoscaler.AutoScaler
	if cfg.AutoScaler.Enabled {
		var provider autoscaler.NodeProvider
		switch cfg.AutoScaler.Provider {
		case "mock":
			provider = autoscaler.NewMockNodeProvider()
		default:
			provider = autoscaler.NewMockNodeProvider()
		}
		as = autoscaler.NewAutoScaler(&cfg.AutoScaler, provider)
	}

	var dr *drill.DrillRunner
	if cfg.Drill.Enabled {
		dr = drill.NewDrillRunner(tm)
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &LoadBalancer{
		config:          cfg,
		rabbitClient:    client,
		monitor:         mon,
		migrator:        migrator,
		failureDetector: failureDetector,
		predictor:       pred,
		exporter:        exporter,
		tenantManager:   tm,
		autoScaler:      as,
		drillRunner:     dr,
		ctx:             ctx,
		cancel:          cancel,
		rebalanceChan:   make(chan struct{}, 10),
	}, nil
}

func (lb *LoadBalancer) Start() error {
	go lb.monitor.Start(lb.ctx, lb.config.Balancer.CheckInterval)

	if lb.config.Prometheus.Enabled {
		go lb.startPrometheusServer()
	}

	if lb.predictor != nil {
		go lb.predictor.StartCollector(lb.ctx, lb.collectTrafficData)
	}

	lb.setupListeners()

	go lb.runRebalanceLoop()

	if lb.autoScaler != nil {
		go lb.runAutoScalerLoop()
	}

	if lb.drillRunner != nil && lb.config.Drill.AutoRun {
		go lb.runDrillLoop()
	}

	return nil
}

func (lb *LoadBalancer) setupListeners() {
	lb.monitor.AddListener(func(state *monitor.ClusterState) {
		lb.updateMetrics(state)
		lb.failureDetector.Update(state)

		if lb.tenantManager != nil {
			violations := lb.tenantManager.EnforceTenantPolicies(state)
			lb.exporter.TenantViolationTotal.Set(float64(len(violations)))
		}
	})

	lb.failureDetector.AddFailureListener(func(failedNodes []string) {
		lb.exporter.FailedNodesTotal.Set(float64(len(failedNodes)))
		for _, node := range failedNodes {
			lb.exporter.NodeFailuresTotal.WithLabelValues(node).Inc()
		}
		lb.triggerRebalance()
	})

	lb.failureDetector.AddRecoveryListener(func(recoveredNodes []string) {
		failedCount := len(lb.failureDetector.GetFailedNodes())
		lb.exporter.FailedNodesTotal.Set(float64(failedCount))
		for _, node := range recoveredNodes {
			lb.exporter.NodeRecoveriesTotal.WithLabelValues(node).Inc()
		}
		lb.triggerRebalance()
	})
}

func (lb *LoadBalancer) triggerRebalance() {
	select {
	case lb.rebalanceChan <- struct{}{}:
	default:
	}
}

func (lb *LoadBalancer) updateMetrics(state *monitor.ClusterState) {
	lb.exporter.ResetNodeMetrics()
	lb.exporter.ResetQueueMetrics()

	for nodeName, node := range state.Nodes {
		lb.exporter.NodeLoadScore.WithLabelValues(nodeName).Set(node.LoadScore)
		lb.exporter.NodeQueueCount.WithLabelValues(nodeName).Set(float64(node.QueueCount))
		lb.exporter.NodeTotalMessages.WithLabelValues(nodeName).Set(float64(node.TotalMessages))
		lb.exporter.NodeTotalMemory.WithLabelValues(nodeName).Set(float64(node.TotalMemory))
		lb.exporter.NodeMemUsed.WithLabelValues(nodeName).Set(float64(node.MemUsed))
		lb.exporter.NodeDiskFree.WithLabelValues(nodeName).Set(float64(node.DiskFree))

		status := 0.0
		if node.Running {
			status = 1.0
		}
		if ns, ok := lb.failureDetector.GetNodeStatus(nodeName); ok && ns.IsFailed {
			status = -1.0
		}
		lb.exporter.NodeStatus.WithLabelValues(nodeName).Set(status)
	}

	for _, queue := range state.Queues {
		lb.exporter.QueueMessages.WithLabelValues(queue.Vhost, queue.Name, queue.Node).Set(float64(queue.Messages))
		lb.exporter.QueueConsumers.WithLabelValues(queue.Vhost, queue.Name, queue.Node).Set(float64(queue.Consumers))
		lb.exporter.QueueMemory.WithLabelValues(queue.Vhost, queue.Name, queue.Node).Set(float64(queue.Memory))
		lb.exporter.QueuePublishRate.WithLabelValues(queue.Vhost, queue.Name, queue.Node).Set(queue.MessageStats.PublishDetails.Rate)
		lb.exporter.QueueDeliverRate.WithLabelValues(queue.Vhost, queue.Name, queue.Node).Set(queue.MessageStats.DeliverDetails.Rate)
		lb.exporter.QueueNode.WithLabelValues(queue.Vhost, queue.Name, queue.Node).Set(1)

		paused := 0.0
		if lb.migrator.IsConsumerPaused(queue.Vhost, queue.Name) {
			paused = 1.0
		}
		lb.exporter.QueueConsumerPaused.WithLabelValues(queue.Vhost, queue.Name).Set(paused)
	}

	lb.exporter.ConsumersPausedTotal.Set(float64(lb.migrator.GetPausedConsumersCount()))

	if lb.predictor != nil {
		burstQueues := lb.predictor.GetAllBurstQueues()
		lb.exporter.TotalBurstQueues.Set(float64(len(burstQueues)))

		for key, burstInfo := range burstQueues {
			lb.exporter.QueueBurstStatus.WithLabelValues(burstInfo.Vhost, burstInfo.QueueName).Set(1)
			lb.exporter.QueueBurstMagnitude.WithLabelValues(burstInfo.Vhost, burstInfo.QueueName).Set(burstInfo.BurstMagnitude)
			lb.exporter.QueueBurstDuration.WithLabelValues(burstInfo.Vhost, burstInfo.QueueName).Set(burstInfo.BurstDuration.Seconds())
			lb.exporter.QueueBurstBaseline.WithLabelValues(burstInfo.Vhost, burstInfo.QueueName).Set(burstInfo.NormalBaseline)
		}
	}

	if lb.tenantManager != nil {
		exclusiveNodes := lb.tenantManager.GetExclusiveNodes()
		for tenantName, nodes := range exclusiveNodes {
			for _, node := range nodes {
				lb.exporter.TenantNodeAssignment.WithLabelValues(tenantName, node).Set(1)
			}
		}
		lb.exporter.DedicatedQueueTotal.Set(float64(len(lb.tenantManager.GetDedicatedNodes())))
	}

	if lb.autoScaler != nil {
		managedNodes := lb.autoScaler.GetManagedNodes()
		lb.exporter.ManagedNodesTotal.Set(float64(len(managedNodes)))
	}
}

func (lb *LoadBalancer) collectTrafficData() []predictor.TrafficDataPoint {
	state := lb.monitor.GetState()
	dataPoints := make([]predictor.TrafficDataPoint, 0, len(state.Queues))

	for _, queue := range state.Queues {
		dataPoints = append(dataPoints, predictor.TrafficDataPoint{
			Timestamp:    time.Now(),
			QueueName:    queue.Name,
			Vhost:        queue.Vhost,
			PublishRate:  queue.MessageStats.PublishDetails.Rate,
			DeliverRate:  queue.MessageStats.DeliverDetails.Rate,
			MessageCount: queue.Messages,
		})
	}

	return dataPoints
}

func (lb *LoadBalancer) runRebalanceLoop() {
	ticker := time.NewTicker(lb.config.Balancer.CheckInterval)
	defer ticker.Stop()

	for {
		select {
		case <-lb.ctx.Done():
			return
		case <-lb.rebalanceChan:
			lb.performImmediateRebalance()
		case <-ticker.C:
			lb.performScheduledRebalance()
		}
	}
}

func (lb *LoadBalancer) performScheduledRebalance() {
	state := lb.monitor.GetState()
	if state == nil {
		return
	}

	burstQueues := make(map[string]bool)
	if lb.predictor != nil {
		burstQueues = lb.predictor.GetBurstQueueNames()
	}

	predictions := make(map[string]*predictor.PredictionResult)
	if lb.predictor != nil {
		for _, queue := range state.Queues {
			if pred, ok := lb.predictor.Predict(queue.Name, queue.Vhost, lb.config.Prediction.PredictionWindow); ok {
				key := queue.Vhost + ":" + queue.Name
				predictions[key] = pred

				trendValue := 0.0
				if pred.Trend == "increasing" {
					trendValue = 1.0
				} else if pred.Trend == "decreasing" {
					trendValue = -1.0
				}
				lb.exporter.PredictionQueueTrend.WithLabelValues(queue.Vhost, queue.Name).Set(trendValue)
				lb.exporter.PredictionConfidence.WithLabelValues(queue.Vhost, queue.Name).Set(pred.Confidence)
				lb.exporter.PredictedMessages.WithLabelValues(queue.Vhost, queue.Name).Set(pred.PredictedMessages)
			}
		}
	}

	failedNodes := lb.failureDetector.GetFailedNodes()

	var plans []balancer.MigrationPlan

	if len(failedNodes) > 0 {
		plans = lb.migrator.GenerateFailureRecoveryPlans(state, failedNodes, burstQueues)
	} else {
		plans = lb.migrator.GenerateMigrationPlans(state, predictions, burstQueues)
	}

	if lb.tenantManager != nil {
		plans = lb.filterPlansByTenantPolicy(plans, state)
	}

	if lb.drillRunner != nil && lb.config.Drill.Enabled && len(plans) > 0 {
		drillResult := lb.drillRunner.RunDrill(state, plans, predictions)
		lb.exporter.DrillRunsTotal.Inc()
		lb.exporter.DrillRiskScore.Set(drillResult.RiskScore)
		lb.exporter.DrillViolationCount.Set(float64(len(drillResult.Violations)))

		if lb.config.Drill.BlockOnRisk && !lb.isRiskAcceptable(drillResult.RiskLevel) {
			blocked := 0
			filtered := make([]balancer.MigrationPlan, 0, len(plans))
			for _, plan := range plans {
				if lb.tenantManager != nil {
					if err := lb.tenantManager.ValidateMigration(plan.QueueName, plan.Vhost, plan.TargetNode, state); err != nil {
						blocked++
						continue
					}
				}
				filtered = append(filtered, plan)
			}
			plans = filtered
			lb.exporter.DrillBlockedMigrations.Set(float64(blocked))

			fmt.Printf("[Drill] Risk level %s (score %.1f), %d migrations blocked\n",
				drillResult.RiskLevel, drillResult.RiskScore, blocked)
		} else {
			lb.exporter.DrillBlockedMigrations.Set(0)
		}
	}

	lb.exporter.RebalanceCyclesTotal.Inc()
	lb.exporter.RebalancePlansGenerated.Set(float64(len(plans)))
	lb.exporter.LastRebalanceTime.Set(float64(time.Now().Unix()))

	lb.executeMigrations(plans)
}

func (lb *LoadBalancer) performImmediateRebalance() {
	state := lb.monitor.GetState()
	if state == nil {
		return
	}

	burstQueues := make(map[string]bool)
	if lb.predictor != nil {
		burstQueues = lb.predictor.GetBurstQueueNames()
	}

	failedNodes := lb.failureDetector.GetFailedNodes()

	var plans []balancer.MigrationPlan
	if len(failedNodes) > 0 {
		plans = lb.migrator.GenerateFailureRecoveryPlans(state, failedNodes, burstQueues)
	}

	if lb.tenantManager != nil {
		plans = lb.filterPlansByTenantPolicy(plans, state)
	}

	lb.executeMigrations(plans)
}

func (lb *LoadBalancer) filterPlansByTenantPolicy(plans []balancer.MigrationPlan, state *monitor.ClusterState) []balancer.MigrationPlan {
	if lb.tenantManager == nil {
		return plans
	}

	filtered := make([]balancer.MigrationPlan, 0, len(plans))
	for _, plan := range plans {
		if err := lb.tenantManager.ValidateMigration(plan.QueueName, plan.Vhost, plan.TargetNode, state); err != nil {
			fmt.Printf("[Tenant] Migration blocked: %s -> %s for queue %s: %v\n",
				plan.SourceNode, plan.TargetNode, plan.QueueName, err)
			continue
		}
		filtered = append(filtered, plan)
	}
	return filtered
}

func (lb *LoadBalancer) isRiskAcceptable(riskLevel string) bool {
	maxLevel := lb.config.Drill.MaxRiskLevel
	levelOrder := map[string]int{"low": 1, "medium": 2, "high": 3, "critical": 4}
	return levelOrder[riskLevel] <= levelOrder[maxLevel]
}

func (lb *LoadBalancer) executeMigrations(plans []balancer.MigrationPlan) {
	for _, plan := range plans {
		lb.exporter.MigrationsInProgress.Inc()

		lb.exporter.MigrationTotal.WithLabelValues(plan.SourceNode, plan.TargetNode).Inc()

		err := lb.migrator.ExecuteMigration(plan)

		lb.exporter.MigrationsInProgress.Dec()

		if err != nil {
			lb.exporter.MigrationFailedTotal.WithLabelValues(plan.SourceNode, plan.TargetNode).Inc()
		} else {
			lb.exporter.MigrationSuccessTotal.WithLabelValues(plan.SourceNode, plan.TargetNode).Inc()
			lb.exporter.MigrationDuration.WithLabelValues(plan.SourceNode, plan.TargetNode).Observe(plan.EstimatedTime.Seconds())
		}

		select {
		case <-lb.ctx.Done():
			return
		default:
		}
	}
}

func (lb *LoadBalancer) runAutoScalerLoop() {
	ticker := time.NewTicker(lb.config.AutoScaler.EvaluationInterval)
	defer ticker.Stop()

	for {
		select {
		case <-lb.ctx.Done():
			return
		case <-ticker.C:
			lb.evaluateScaling()
		}
	}
}

func (lb *LoadBalancer) evaluateScaling() {
	if lb.autoScaler == nil {
		return
	}

	state := lb.monitor.GetState()
	if state == nil {
		return
	}

	decision := lb.autoScaler.Evaluate(state)
	if decision == nil {
		lb.exporter.ScalingDecisionStatus.WithLabelValues("none").Set(0)
		return
	}

	switch decision.Action {
	case "scale_up":
		lb.exporter.ScalingDecisionStatus.WithLabelValues("scale_up").Set(1)
		fmt.Printf("[AutoScaler] Scale up: %s (current: %d, target: %d, avgLoad: %.2f)\n",
			decision.Reason, decision.CurrentNodes, decision.TargetNodes, decision.AvgLoad)

		err := lb.autoScaler.ExecuteScaleUp(lb.ctx, decision)
		if err != nil {
			lb.exporter.AutoScalerEventsTotal.WithLabelValues("scale_up", "failed").Inc()
			fmt.Printf("[AutoScaler] Scale up failed: %v\n", err)
		} else {
			lb.exporter.AutoScalerEventsTotal.WithLabelValues("scale_up", "success").Inc()
			lb.triggerRebalance()
		}

	case "scale_down":
		lb.exporter.ScalingDecisionStatus.WithLabelValues("scale_down").Set(-1)
		fmt.Printf("[AutoScaler] Scale down: %s\n", decision.Reason)
		lb.exporter.AutoScalerEventsTotal.WithLabelValues("scale_down", "success").Inc()
	}
}

func (lb *LoadBalancer) runDrillLoop() {
	ticker := time.NewTicker(lb.config.Drill.Interval)
	defer ticker.Stop()

	for {
		select {
		case <-lb.ctx.Done():
			return
		case <-ticker.C:
			state := lb.monitor.GetState()
			if state == nil {
				continue
			}

			burstQueues := make(map[string]bool)
			if lb.predictor != nil {
				burstQueues = lb.predictor.GetBurstQueueNames()
			}

			predictions := make(map[string]*predictor.PredictionResult)
			if lb.predictor != nil {
				for _, queue := range state.Queues {
					if pred, ok := lb.predictor.Predict(queue.Name, queue.Vhost, lb.config.Prediction.PredictionWindow); ok {
						predictions[queue.Vhost+":"+queue.Name] = pred
					}
				}
			}

			failedNodes := lb.failureDetector.GetFailedNodes()
			var plans []balancer.MigrationPlan

			if len(failedNodes) > 0 {
				plans = lb.migrator.GenerateFailureRecoveryPlans(state, failedNodes, burstQueues)
			} else {
				plans = lb.migrator.GenerateMigrationPlans(state, predictions, burstQueues)
			}

			if len(plans) > 0 {
				result := lb.drillRunner.RunDrill(state, plans, predictions)
				lb.exporter.DrillRunsTotal.Inc()
				lb.exporter.DrillRiskScore.Set(result.RiskScore)
				lb.exporter.DrillViolationCount.Set(float64(len(result.Violations)))

				report := drill.GenerateDrillReport(result)
				fmt.Printf("[Drill] Auto drill completed:\n%s\n", report)
			}
		}
	}
}

func (lb *LoadBalancer) startPrometheusServer() {
	mux := http.NewServeMux()
	mux.Handle(lb.config.Prometheus.Path, lb.exporter.Handler())

	server := &http.Server{
		Addr:    lb.config.Prometheus.Address,
		Handler: mux,
	}

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		fmt.Printf("Prometheus server error: %v\n", err)
	}
}

func (lb *LoadBalancer) Stop() {
	lb.cancel()
	lb.migrator.Stop()
}

func main() {
	configPath := "config.yaml"
	if len(os.Args) > 1 {
		configPath = os.Args[1]
	}

	cfg, err := config.Load(configPath)
	if err != nil {
		fmt.Printf("Failed to load config: %v\n", err)
		os.Exit(1)
	}

	lb, err := NewLoadBalancer(cfg)
	if err != nil {
		fmt.Printf("Failed to create load balancer: %v\n", err)
		os.Exit(1)
	}

	if err := lb.Start(); err != nil {
		fmt.Printf("Failed to start load balancer: %v\n", err)
		os.Exit(1)
	}

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	<-sigChan

	lb.Stop()
}
