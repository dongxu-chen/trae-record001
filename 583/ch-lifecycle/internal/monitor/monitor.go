package monitor

import (
	"context"
	"sync"
	"time"

	ch "ch-lifecycle/internal/clickhouse"
	"github.com/prometheus/client_golang/prometheus"
	"go.uber.org/zap"
)

type Metrics struct {
	partitionsProcessed *prometheus.CounterVec
	partitionSize       *prometheus.HistogramVec
	lifecycleErrors     *prometheus.CounterVec
	tierMigrations      *prometheus.CounterVec
	diskUsage           *prometheus.GaugeVec
	schedulerRuns       *prometheus.CounterVec
	schedulerDuration   *prometheus.HistogramVec
}

type Monitor struct {
	client  *ch.Client
	logger  *zap.Logger
	metrics *Metrics
	registry *prometheus.Registry
	mu      sync.RWMutex
	snapshots []ClusterSnapshot
}

type ClusterSnapshot struct {
	Timestamp time.Time               `json:"timestamp"`
	Disks     []DiskSnapshot          `json:"disks"`
	Tables    []TableSnapshot         `json:"tables"`
}

type DiskSnapshot struct {
	Name       string `json:"name"`
	Type       string `json:"type"`
	FreeSpace  uint64 `json:"free_space"`
	TotalSpace uint64 `json:"total_space"`
	UsedPct    float64 `json:"used_pct"`
}

type TableSnapshot struct {
	Database       string `json:"database"`
	Table          string `json:"table"`
	TotalRows      uint64 `json:"total_rows"`
	TotalBytes     uint64 `json:"total_bytes"`
	PartitionCount int    `json:"partition_count"`
}

func NewMonitor(client *ch.Client, logger *zap.Logger) *Monitor {
	registry := prometheus.NewRegistry()
	m := &Metrics{
		partitionsProcessed: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "ch_lifecycle_partitions_processed_total",
			Help: "Total number of partitions processed by action type",
		}, []string{"action"}),
		partitionSize: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Name:    "ch_lifecycle_partition_size_bytes",
			Help:    "Size of partitions processed",
			Buckets: prometheus.ExponentialBuckets(1024, 4, 10),
		}, []string{"database", "table"}),
		lifecycleErrors: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "ch_lifecycle_errors_total",
			Help: "Total number of lifecycle errors by action type",
		}, []string{"action"}),
		tierMigrations: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "ch_lifecycle_tier_migrations_total",
			Help: "Total number of tier migration operations",
		}, []string{"from_disk", "to_disk"}),
		diskUsage: prometheus.NewGaugeVec(prometheus.GaugeOpts{
			Name: "ch_lifecycle_disk_usage_bytes",
			Help: "Disk usage in bytes",
		}, []string{"disk", "type"}),
		schedulerRuns: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "ch_lifecycle_scheduler_runs_total",
			Help: "Total scheduler job runs by type",
		}, []string{"job_type"}),
		schedulerDuration: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Name:    "ch_lifecycle_scheduler_duration_seconds",
			Help:    "Duration of scheduler jobs",
			Buckets: prometheus.DefBuckets,
		}, []string{"job_type"}),
	}
	registry.MustRegister(
		m.partitionsProcessed,
		m.partitionSize,
		m.lifecycleErrors,
		m.tierMigrations,
		m.diskUsage,
		m.schedulerRuns,
		m.schedulerDuration,
	)
	return &Monitor{
		client:   client,
		logger:   logger,
		metrics:  m,
		registry: registry,
	}
}

func (m *Monitor) Registry() *prometheus.Registry {
	return m.registry
}

func (m *Monitor) IncPartitionsProcessed(action string) {
	m.metrics.partitionsProcessed.WithLabelValues(action).Inc()
}

func (m *Monitor) ObservePartitionSize(database, table string, size uint64) {
	m.metrics.partitionSize.WithLabelValues(database, table).Observe(float64(size))
}

func (m *Monitor) IncLifecycleErrors(action string) {
	m.metrics.lifecycleErrors.WithLabelValues(action).Inc()
}

func (m *Monitor) IncTierMigrations(from, to string) {
	m.metrics.tierMigrations.WithLabelValues(from, to).Inc()
}

func (m *Monitor) ObserveDiskUsage(disk string, used, total uint64) {
	m.metrics.diskUsage.WithLabelValues(disk, "used").Set(float64(used))
	m.metrics.diskUsage.WithLabelValues(disk, "total").Set(float64(total))
}

func (m *Monitor) RecordSchedulerRun(jobType string, duration time.Duration) {
	m.metrics.schedulerRuns.WithLabelValues(jobType).Inc()
	m.metrics.schedulerDuration.WithLabelValues(jobType).Observe(duration.Seconds())
}

func (m *Monitor) CollectSnapshot(ctx context.Context) (*ClusterSnapshot, error) {
	snapshot := &ClusterSnapshot{Timestamp: time.Now()}
	disks, err := m.client.GetDisks(ctx)
	if err != nil {
		return nil, err
	}
	for _, d := range disks {
		var usedPct float64
		if d.TotalSpace > 0 {
			usedPct = float64(d.TotalSpace-d.FreeSpace) / float64(d.TotalSpace) * 100
		}
		snapshot.Disks = append(snapshot.Disks, DiskSnapshot{
			Name:       d.Name,
			Type:       d.Type,
			FreeSpace:  d.FreeSpace,
			TotalSpace: d.TotalSpace,
			UsedPct:    usedPct,
		})
	}
	m.mu.Lock()
	m.snapshots = append(m.snapshots, *snapshot)
	if len(m.snapshots) > 288 {
		m.snapshots = m.snapshots[len(m.snapshots)-288:]
	}
	m.mu.Unlock()
	return snapshot, nil
}

func (m *Monitor) GetSnapshots() []ClusterSnapshot {
	m.mu.RLock()
	defer m.mu.RUnlock()
	result := make([]ClusterSnapshot, len(m.snapshots))
	copy(result, m.snapshots)
	return result
}

func (m *Monitor) StartCollection(ctx context.Context, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if _, err := m.CollectSnapshot(ctx); err != nil {
				m.logger.Warn("failed to collect snapshot", zap.Error(err))
			}
		}
	}
}
