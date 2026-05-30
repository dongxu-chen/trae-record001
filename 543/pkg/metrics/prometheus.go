package metrics

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type Exporter struct {
	registry *prometheus.Registry

	NodeLoadScore    *prometheus.GaugeVec
	NodeQueueCount   *prometheus.GaugeVec
	NodeTotalMessages *prometheus.GaugeVec
	NodeTotalMemory  *prometheus.GaugeVec
	NodeStatus       *prometheus.GaugeVec
	NodeMemUsed      *prometheus.GaugeVec
	NodeDiskFree     *prometheus.GaugeVec

	QueueMessages       *prometheus.GaugeVec
	QueueConsumers      *prometheus.GaugeVec
	QueueMemory         *prometheus.GaugeVec
	QueuePublishRate    *prometheus.GaugeVec
	QueueDeliverRate    *prometheus.GaugeVec
	QueueNode           *prometheus.GaugeVec
	QueueConsumerPaused *prometheus.GaugeVec

	MigrationTotal        *prometheus.CounterVec
	MigrationSuccessTotal *prometheus.CounterVec
	MigrationFailedTotal  *prometheus.CounterVec
	MigrationDuration     *prometheus.HistogramVec
	MigrationsInProgress  prometheus.Gauge

	RebalanceCyclesTotal    prometheus.Counter
	RebalancePlansGenerated prometheus.Gauge
	LastRebalanceTime       prometheus.Gauge

	PredictionQueueTrend  *prometheus.GaugeVec
	PredictionConfidence  *prometheus.GaugeVec
	PredictedMessages     *prometheus.GaugeVec

	FailedNodesTotal    prometheus.Gauge
	NodeFailuresTotal   *prometheus.CounterVec
	NodeRecoveriesTotal *prometheus.CounterVec

	QueueBurstStatus    *prometheus.GaugeVec
	QueueBurstMagnitude *prometheus.GaugeVec
	QueueBurstDuration  *prometheus.GaugeVec
	QueueBurstBaseline  *prometheus.GaugeVec
	TotalBurstQueues    prometheus.Gauge

	ConsumersPausedTotal prometheus.Gauge

	TenantViolationTotal  prometheus.Gauge
	DedicatedQueueTotal   prometheus.Gauge
	TenantNodeAssignment  *prometheus.GaugeVec

	AutoScalerEventsTotal   *prometheus.CounterVec
	ManagedNodesTotal       prometheus.Gauge
	ScalingDecisionStatus   *prometheus.GaugeVec

	DrillRunsTotal      prometheus.Counter
	DrillRiskScore      prometheus.Gauge
	DrillViolationCount prometheus.Gauge
	DrillBlockedMigrations prometheus.Gauge
}

func NewExporter() *Exporter {
	registry := prometheus.NewRegistry()

	e := &Exporter{
		registry: registry,

		NodeLoadScore: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_node_load_score", Help: "Load score for each node"}, []string{"node"}),
		NodeQueueCount: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_node_queue_count", Help: "Number of queues on each node"}, []string{"node"}),
		NodeTotalMessages: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_node_total_messages", Help: "Total messages on each node"}, []string{"node"}),
		NodeTotalMemory: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_node_total_memory_bytes", Help: "Total memory used by queues on each node"}, []string{"node"}),
		NodeStatus: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_node_status", Help: "Node status (1=running, 0=stopped, -1=failed)"}, []string{"node"}),
		NodeMemUsed: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_node_mem_used_bytes", Help: "Memory used by node"}, []string{"node"}),
		NodeDiskFree: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_node_disk_free_bytes", Help: "Free disk space on node"}, []string{"node"}),

		QueueMessages: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_messages", Help: "Number of messages in queue"}, []string{"vhost", "queue", "node"}),
		QueueConsumers: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_consumers", Help: "Number of consumers on queue"}, []string{"vhost", "queue", "node"}),
		QueueMemory: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_memory_bytes", Help: "Memory used by queue"}, []string{"vhost", "queue", "node"}),
		QueuePublishRate: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_publish_rate", Help: "Message publish rate"}, []string{"vhost", "queue", "node"}),
		QueueDeliverRate: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_deliver_rate", Help: "Message deliver rate"}, []string{"vhost", "queue", "node"}),
		QueueNode: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_node_assignment", Help: "Current node assignment for queue"}, []string{"vhost", "queue", "node"}),
		QueueConsumerPaused: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_consumer_paused", Help: "Whether consumers are paused for this queue (1=paused, 0=active)"}, []string{"vhost", "queue"}),

		MigrationTotal: prometheus.NewCounterVec(prometheus.CounterOpts{Name: "rabbitmq_lb_migrations_total", Help: "Total number of migrations"}, []string{"source_node", "target_node"}),
		MigrationSuccessTotal: prometheus.NewCounterVec(prometheus.CounterOpts{Name: "rabbitmq_lb_migrations_success_total", Help: "Total number of successful migrations"}, []string{"source_node", "target_node"}),
		MigrationFailedTotal: prometheus.NewCounterVec(prometheus.CounterOpts{Name: "rabbitmq_lb_migrations_failed_total", Help: "Total number of failed migrations"}, []string{"source_node", "target_node"}),
		MigrationDuration: prometheus.NewHistogramVec(prometheus.HistogramOpts{Name: "rabbitmq_lb_migration_duration_seconds", Help: "Migration duration in seconds", Buckets: []float64{1, 5, 10, 30, 60, 120, 300}}, []string{"source_node", "target_node"}),
		MigrationsInProgress: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_migrations_in_progress", Help: "Number of migrations in progress"}),

		RebalanceCyclesTotal: prometheus.NewCounter(prometheus.CounterOpts{Name: "rabbitmq_lb_rebalance_cycles_total", Help: "Total number of rebalance cycles"}),
		RebalancePlansGenerated: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_rebalance_plans_generated", Help: "Number of migration plans generated in last cycle"}),
		LastRebalanceTime: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_last_rebalance_timestamp_seconds", Help: "Timestamp of last rebalance cycle"}),

		PredictionQueueTrend: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_prediction_queue_trend", Help: "Queue load trend (1=increasing, 0=stable, -1=decreasing)"}, []string{"vhost", "queue"}),
		PredictionConfidence: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_prediction_confidence", Help: "Prediction confidence score"}, []string{"vhost", "queue"}),
		PredictedMessages: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_predicted_messages", Help: "Predicted message count"}, []string{"vhost", "queue"}),

		FailedNodesTotal: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_failed_nodes_total", Help: "Number of failed nodes"}),
		NodeFailuresTotal: prometheus.NewCounterVec(prometheus.CounterOpts{Name: "rabbitmq_lb_node_failures_total", Help: "Total number of node failures"}, []string{"node"}),
		NodeRecoveriesTotal: prometheus.NewCounterVec(prometheus.CounterOpts{Name: "rabbitmq_lb_node_recoveries_total", Help: "Total number of node recoveries"}, []string{"node"}),

		QueueBurstStatus: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_burst_status", Help: "Burst traffic status (1=bursting, 0=normal)"}, []string{"vhost", "queue"}),
		QueueBurstMagnitude: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_burst_magnitude", Help: "Burst magnitude (current rate / baseline)"}, []string{"vhost", "queue"}),
		QueueBurstDuration: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_burst_duration_seconds", Help: "Current burst duration in seconds"}, []string{"vhost", "queue"}),
		QueueBurstBaseline: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_queue_burst_baseline_rate", Help: "Normal baseline publish rate"}, []string{"vhost", "queue"}),
		TotalBurstQueues: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_burst_queues_total", Help: "Total number of queues currently in burst mode"}),

		ConsumersPausedTotal: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_consumers_paused_total", Help: "Total number of queues with paused consumers"}),

		TenantViolationTotal: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_tenant_violations_total", Help: "Total tenant isolation violations detected"}),
		DedicatedQueueTotal: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_dedicated_queues_total", Help: "Total dedicated queues configured"}),
		TenantNodeAssignment: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_tenant_node_assignment", Help: "Node assignment for tenant (1=exclusive)"}, []string{"tenant", "node"}),

		AutoScalerEventsTotal: prometheus.NewCounterVec(prometheus.CounterOpts{Name: "rabbitmq_lb_autoscaler_events_total", Help: "Total autoscaling events"}, []string{"action", "result"}),
		ManagedNodesTotal: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_autoscaler_managed_nodes_total", Help: "Total nodes managed by autoscaler"}),
		ScalingDecisionStatus: prometheus.NewGaugeVec(prometheus.GaugeOpts{Name: "rabbitmq_lb_autoscaler_decision_status", Help: "Current scaling decision status (1=scale_up, -1=scale_down, 0=none)"}, []string{"decision"}),

		DrillRunsTotal: prometheus.NewCounter(prometheus.CounterOpts{Name: "rabbitmq_lb_drill_runs_total", Help: "Total number of migration drills run"}),
		DrillRiskScore: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_drill_risk_score", Help: "Risk score from last drill run"}),
		DrillViolationCount: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_drill_violation_count", Help: "Number of violations found in last drill"}),
		DrillBlockedMigrations: prometheus.NewGauge(prometheus.GaugeOpts{Name: "rabbitmq_lb_drill_blocked_migrations", Help: "Number of migrations blocked by drill risk assessment"}),
	}

	registry.MustRegister(
		e.NodeLoadScore, e.NodeQueueCount, e.NodeTotalMessages, e.NodeTotalMemory, e.NodeStatus, e.NodeMemUsed, e.NodeDiskFree,
		e.QueueMessages, e.QueueConsumers, e.QueueMemory, e.QueuePublishRate, e.QueueDeliverRate, e.QueueNode, e.QueueConsumerPaused,
		e.MigrationTotal, e.MigrationSuccessTotal, e.MigrationFailedTotal, e.MigrationDuration, e.MigrationsInProgress,
		e.RebalanceCyclesTotal, e.RebalancePlansGenerated, e.LastRebalanceTime,
		e.PredictionQueueTrend, e.PredictionConfidence, e.PredictedMessages,
		e.FailedNodesTotal, e.NodeFailuresTotal, e.NodeRecoveriesTotal,
		e.QueueBurstStatus, e.QueueBurstMagnitude, e.QueueBurstDuration, e.QueueBurstBaseline, e.TotalBurstQueues,
		e.ConsumersPausedTotal,
		e.TenantViolationTotal, e.DedicatedQueueTotal, e.TenantNodeAssignment,
		e.AutoScalerEventsTotal, e.ManagedNodesTotal, e.ScalingDecisionStatus,
		e.DrillRunsTotal, e.DrillRiskScore, e.DrillViolationCount, e.DrillBlockedMigrations,
	)

	return e
}

func (e *Exporter) Handler() http.Handler {
	return promhttp.HandlerFor(e.registry, promhttp.HandlerOpts{})
}

func (e *Exporter) ResetQueueMetrics() {
	e.QueueMessages.Reset()
	e.QueueConsumers.Reset()
	e.QueueMemory.Reset()
	e.QueuePublishRate.Reset()
	e.QueueDeliverRate.Reset()
	e.QueueNode.Reset()
	e.QueueConsumerPaused.Reset()
	e.PredictionQueueTrend.Reset()
	e.PredictionConfidence.Reset()
	e.PredictedMessages.Reset()
	e.QueueBurstStatus.Reset()
	e.QueueBurstMagnitude.Reset()
	e.QueueBurstDuration.Reset()
	e.QueueBurstBaseline.Reset()
}

func (e *Exporter) ResetNodeMetrics() {
	e.NodeLoadScore.Reset()
	e.NodeQueueCount.Reset()
	e.NodeTotalMessages.Reset()
	e.NodeTotalMemory.Reset()
	e.NodeStatus.Reset()
	e.NodeMemUsed.Reset()
	e.NodeDiskFree.Reset()
}
