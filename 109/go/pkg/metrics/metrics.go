package metrics

import (
	"net/http"
	"sync/atomic"
	"time"

	"backup-tool/pkg/config"
	"backup-tool/pkg/logger"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type BackupMetrics struct {
	backupTotalCount      *prometheus.CounterVec
	backupSuccessCount    *prometheus.CounterVec
	backupFailedCount     *prometheus.CounterVec
	backupDurationSeconds *prometheus.HistogramVec
	backupSizeBytes       *prometheus.GaugeVec
	activeBackups         *prometheus.GaugeVec
	pipelineStageCount    *prometheus.GaugeVec
	lastBackupTime        *prometheus.GaugeVec

	stats *BackupStats
}

type BackupStats struct {
	TotalBackups      int64
	SuccessfulBackups int64
	FailedBackups     int64
	ActiveBackups     int64
}

func NewBackupMetrics() *BackupMetrics {
	return &BackupMetrics{
		stats: &BackupStats{},
	}
}

func (m *BackupMetrics) Register() {
	m.backupTotalCount = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "backup_total_count",
			Help: "Total number of backup attempts",
		},
		[]string{"database", "type"},
	)

	m.backupSuccessCount = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "backup_success_count",
			Help: "Number of successful backups",
		},
		[]string{"database", "type"},
	)

	m.backupFailedCount = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "backup_failed_count",
			Help: "Number of failed backups",
		},
		[]string{"database", "type"},
	)

	m.backupDurationSeconds = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "backup_duration_seconds",
			Help:    "Backup duration in seconds",
			Buckets: []float64{10, 30, 60, 120, 300, 600, 1800, 3600},
		},
		[]string{"database", "type", "stage"},
	)

	m.backupSizeBytes = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "backup_size_bytes",
			Help: "Backup size in bytes",
		},
		[]string{"database", "type"},
	)

	m.activeBackups = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "backup_active_count",
			Help: "Number of currently active backups",
		},
		[]string{"type"},
	)

	m.pipelineStageCount = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "backup_pipeline_stage_count",
			Help: "Number of jobs in each pipeline stage",
		},
		[]string{"stage"},
	)

	m.lastBackupTime = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "backup_last_timestamp_seconds",
			Help: "Timestamp of last successful backup",
		},
		[]string{"database", "type"},
	)

	prometheus.MustRegister(
		m.backupTotalCount,
		m.backupSuccessCount,
		m.backupFailedCount,
		m.backupDurationSeconds,
		m.backupSizeBytes,
		m.activeBackups,
		m.pipelineStageCount,
		m.lastBackupTime,
	)

	logger.Info("Prometheus metrics registered successfully")
}

func (m *BackupMetrics) StartServer(cfg *config.ServerConfig) {
	mux := http.NewServeMux()
	mux.Handle(cfg.MetricsPath, promhttp.Handler())

	server := &http.Server{
		Addr:    ":" + string(rune(cfg.HTTPPort)),
		Handler: mux,
	}

	go func() {
		logger.Infof("Metrics server starting on :%d%s", cfg.HTTPPort, cfg.MetricsPath)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Errorf("Metrics server error: %v", err)
		}
	}()
}

func (m *BackupMetrics) RecordBackupStart(database, backupType string) {
	atomic.AddInt64(&m.stats.TotalBackups, 1)
	atomic.AddInt64(&m.stats.ActiveBackups, 1)
	m.backupTotalCount.WithLabelValues(database, backupType).Inc()
	m.activeBackups.WithLabelValues(backupType).Inc()
}

func (m *BackupMetrics) RecordBackupSuccess(database, backupType string, duration time.Duration, size int64) {
	atomic.AddInt64(&m.stats.SuccessfulBackups, 1)
	atomic.AddInt64(&m.stats.ActiveBackups, -1)
	m.backupSuccessCount.WithLabelValues(database, backupType).Inc()
	m.backupDurationSeconds.WithLabelValues(database, backupType, "total").Observe(duration.Seconds())
	m.backupSizeBytes.WithLabelValues(database, backupType).Set(float64(size))
	m.lastBackupTime.WithLabelValues(database, backupType).Set(float64(time.Now().Unix()))
	m.activeBackups.WithLabelValues(backupType).Dec()
}

func (m *BackupMetrics) RecordBackupFailure(database, backupType string, duration time.Duration) {
	atomic.AddInt64(&m.stats.FailedBackups, 1)
	atomic.AddInt64(&m.stats.ActiveBackups, -1)
	m.backupFailedCount.WithLabelValues(database, backupType).Inc()
	m.backupDurationSeconds.WithLabelValues(database, backupType, "failed").Observe(duration.Seconds())
	m.activeBackups.WithLabelValues(backupType).Dec()
}

func (m *BackupMetrics) RecordStageDuration(database, backupType, stage string, duration time.Duration) {
	m.backupDurationSeconds.WithLabelValues(database, backupType, stage).Observe(duration.Seconds())
}

func (m *BackupMetrics) UpdatePipelineStage(stage string, count float64) {
	m.pipelineStageCount.WithLabelValues(stage).Set(count)
}

func (m *BackupMetrics) GetStats() BackupStats {
	return BackupStats{
		TotalBackups:      atomic.LoadInt64(&m.stats.TotalBackups),
		SuccessfulBackups: atomic.LoadInt64(&m.stats.SuccessfulBackups),
		FailedBackups:     atomic.LoadInt64(&m.stats.FailedBackups),
		ActiveBackups:     atomic.LoadInt64(&m.stats.ActiveBackups),
	}
}
