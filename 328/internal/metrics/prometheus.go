package metrics

import (
	"context"
	"db-bench/internal/config"
	"db-bench/internal/driver"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type PrometheusExporter struct {
	metrics       *Metrics
	cfg           config.MetricsConfig
	reg           *prometheus.Registry
	mu            sync.Mutex
	activeWorkers int32

	qpsGauge          prometheus.Gauge
	tpsGauge          prometheus.Gauge
	errorRateGauge    prometheus.Gauge
	activeWorkersGauge prometheus.Gauge

	latencyP50Gauge  prometheus.Gauge
	latencyP99Gauge  prometheus.Gauge
	latencyP999Gauge prometheus.Gauge

	readLatencyP50Gauge  prometheus.Gauge
	readLatencyP99Gauge  prometheus.Gauge
	readLatencyP999Gauge prometheus.Gauge

	writeLatencyP50Gauge  prometheus.Gauge
	writeLatencyP99Gauge  prometheus.Gauge
	writeLatencyP999Gauge prometheus.Gauge

	hotspotLatencyP50Gauge  prometheus.Gauge
	hotspotLatencyP99Gauge  prometheus.Gauge
	hotspotLatencyP999Gauge prometheus.Gauge

	totalOpsCounter prometheus.Counter
	readOpsCounter  prometheus.Counter
	writeOpsCounter prometheus.Counter
	errorCounter    prometheus.Counter

	latencyHistogram prometheus.Histogram
	readHistogram    prometheus.Histogram
	writeHistogram   prometheus.Histogram

	operationDuration *prometheus.HistogramVec

	server *http.Server
}

func NewPrometheusExporter(metrics *Metrics, cfg config.MetricsConfig, dbType string) *PrometheusExporter {
	reg := prometheus.NewRegistry()

	labels := prometheus.Labels{"db_type": dbType}

	exporter := &PrometheusExporter{
		metrics: metrics,
		cfg:     cfg,
		reg:     reg,

		qpsGauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_qps",
			Help:        "Queries per second",
			ConstLabels: labels,
		}),
		tpsGauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_tps",
			Help:        "Transactions (writes) per second",
			ConstLabels: labels,
		}),
		errorRateGauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_error_rate",
			Help:        "Error rate (0-1)",
			ConstLabels: labels,
		}),
		activeWorkersGauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_active_workers",
			Help:        "Number of active worker goroutines",
			ConstLabels: labels,
		}),

		latencyP50Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_latency_p50_ms",
			Help:        "Overall latency P50 in milliseconds",
			ConstLabels: labels,
		}),
		latencyP99Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_latency_p99_ms",
			Help:        "Overall latency P99 in milliseconds",
			ConstLabels: labels,
		}),
		latencyP999Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_latency_p999_ms",
			Help:        "Overall latency P999 in milliseconds",
			ConstLabels: labels,
		}),

		readLatencyP50Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_read_latency_p50_ms",
			Help:        "Read latency P50 in milliseconds",
			ConstLabels: labels,
		}),
		readLatencyP99Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_read_latency_p99_ms",
			Help:        "Read latency P99 in milliseconds",
			ConstLabels: labels,
		}),
		readLatencyP999Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_read_latency_p999_ms",
			Help:        "Read latency P999 in milliseconds",
			ConstLabels: labels,
		}),

		writeLatencyP50Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_write_latency_p50_ms",
			Help:        "Write latency P50 in milliseconds",
			ConstLabels: labels,
		}),
		writeLatencyP99Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_write_latency_p99_ms",
			Help:        "Write latency P99 in milliseconds",
			ConstLabels: labels,
		}),
		writeLatencyP999Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_write_latency_p999_ms",
			Help:        "Write latency P999 in milliseconds",
			ConstLabels: labels,
		}),

		hotspotLatencyP50Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_hotspot_latency_p50_ms",
			Help:        "Hotspot latency P50 in milliseconds",
			ConstLabels: labels,
		}),
		hotspotLatencyP99Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_hotspot_latency_p99_ms",
			Help:        "Hotspot latency P99 in milliseconds",
			ConstLabels: labels,
		}),
		hotspotLatencyP999Gauge: prometheus.NewGauge(prometheus.GaugeOpts{
			Name:        "db_bench_hotspot_latency_p999_ms",
			Help:        "Hotspot latency P999 in milliseconds",
			ConstLabels: labels,
		}),

		totalOpsCounter: prometheus.NewCounter(prometheus.CounterOpts{
			Name:        "db_bench_operations_total",
			Help:        "Total number of operations",
			ConstLabels: labels,
		}),
		readOpsCounter: prometheus.NewCounter(prometheus.CounterOpts{
			Name:        "db_bench_read_operations_total",
			Help:        "Total number of read operations",
			ConstLabels: labels,
		}),
		writeOpsCounter: prometheus.NewCounter(prometheus.CounterOpts{
			Name:        "db_bench_write_operations_total",
			Help:        "Total number of write operations",
			ConstLabels: labels,
		}),
		errorCounter: prometheus.NewCounter(prometheus.CounterOpts{
			Name:        "db_bench_errors_total",
			Help:        "Total number of errors",
			ConstLabels: labels,
		}),

		latencyHistogram: prometheus.NewHistogram(prometheus.HistogramOpts{
			Name:        "db_bench_latency_ms",
			Help:        "Latency distribution in milliseconds",
			Buckets:     prometheus.ExponentialBuckets(0.1, 2, 20),
			ConstLabels: labels,
		}),
		readHistogram: prometheus.NewHistogram(prometheus.HistogramOpts{
			Name:        "db_bench_read_latency_ms",
			Help:        "Read latency distribution in milliseconds",
			Buckets:     prometheus.ExponentialBuckets(0.1, 2, 20),
			ConstLabels: labels,
		}),
		writeHistogram: prometheus.NewHistogram(prometheus.HistogramOpts{
			Name:        "db_bench_write_latency_ms",
			Help:        "Write latency distribution in milliseconds",
			Buckets:     prometheus.ExponentialBuckets(0.1, 2, 20),
			ConstLabels: labels,
		}),

		operationDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:        "db_bench_operation_duration_seconds",
				Help:        "Operation duration in seconds",
				Buckets:     prometheus.ExponentialBuckets(0.0001, 2, 25),
				ConstLabels: labels,
			},
			[]string{"operation", "status"},
		),
	}

	reg.MustRegister(
		exporter.qpsGauge,
		exporter.tpsGauge,
		exporter.errorRateGauge,
		exporter.activeWorkersGauge,
		exporter.latencyP50Gauge,
		exporter.latencyP99Gauge,
		exporter.latencyP999Gauge,
		exporter.readLatencyP50Gauge,
		exporter.readLatencyP99Gauge,
		exporter.readLatencyP999Gauge,
		exporter.writeLatencyP50Gauge,
		exporter.writeLatencyP99Gauge,
		exporter.writeLatencyP999Gauge,
		exporter.hotspotLatencyP50Gauge,
		exporter.hotspotLatencyP99Gauge,
		exporter.hotspotLatencyP999Gauge,
		exporter.totalOpsCounter,
		exporter.readOpsCounter,
		exporter.writeOpsCounter,
		exporter.errorCounter,
		exporter.latencyHistogram,
		exporter.readHistogram,
		exporter.writeHistogram,
		exporter.operationDuration,
	)

	return exporter
}

func (p *PrometheusExporter) RecordResult(result driver.Result, isHotspot bool) {
	p.metrics.Record(result, isHotspot)

	status := "success"
	if !result.Success {
		status = "error"
	}

	p.totalOpsCounter.Inc()
	p.latencyHistogram.Observe(result.DurationMs)
	p.operationDuration.WithLabelValues(string(result.OpType), status).Observe(result.DurationMs / 1000.0)

	switch result.OpType {
	case driver.OpRead:
		p.readOpsCounter.Inc()
		p.readHistogram.Observe(result.DurationMs)
	case driver.OpWrite:
		p.writeOpsCounter.Inc()
		p.writeHistogram.Observe(result.DurationMs)
	}

	if !result.Success {
		p.errorCounter.Inc()
	}
}

func (p *PrometheusExporter) UpdateGauges() {
	p.mu.Lock()
	defer p.mu.Unlock()

	snap := p.metrics.Snapshot()

	p.qpsGauge.Set(snap.QPS)
	p.tpsGauge.Set(snap.TPS)
	p.errorRateGauge.Set(snap.ErrorRate)
	p.activeWorkersGauge.Set(float64(p.activeWorkers))

	p.latencyP50Gauge.Set(snap.P50)
	p.latencyP99Gauge.Set(snap.P99)
	p.latencyP999Gauge.Set(snap.P999)

	p.readLatencyP50Gauge.Set(snap.ReadP50)
	p.readLatencyP99Gauge.Set(snap.ReadP99)
	p.readLatencyP999Gauge.Set(snap.ReadP999)

	p.writeLatencyP50Gauge.Set(snap.WriteP50)
	p.writeLatencyP99Gauge.Set(snap.WriteP99)
	p.writeLatencyP999Gauge.Set(snap.WriteP999)

	p.hotspotLatencyP50Gauge.Set(snap.HotspotP50)
	p.hotspotLatencyP99Gauge.Set(snap.HotspotP99)
	p.hotspotLatencyP999Gauge.Set(snap.HotspotP999)
}

func (p *PrometheusExporter) Start(ctx context.Context) error {
	mux := http.NewServeMux()
	mux.Handle(p.cfg.PrometheusPath, promhttp.HandlerFor(p.reg, promhttp.HandlerOpts{}))
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})
	mux.HandleFunc("/debug/metrics", func(w http.ResponseWriter, r *http.Request) {
		snap := p.metrics.Snapshot()
		w.Write([]byte(snap.PrettyPrint()))
	})

	p.server = &http.Server{
		Addr:    fmt.Sprintf(":%d", p.cfg.PrometheusPort),
		Handler: mux,
	}

	go func() {
		ticker := time.NewTicker(1 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				p.UpdateGauges()
			}
		}
	}()

	go func() {
		if err := p.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			fmt.Printf("Prometheus server error: %v\n", err)
		}
	}()

	return nil
}

func (p *PrometheusExporter) Shutdown(ctx context.Context) error {
	if p.server != nil {
		return p.server.Shutdown(ctx)
	}
	return nil
}

func (p *PrometheusExporter) GetMetrics() *Metrics {
	return p.metrics
}

func (p *PrometheusExporter) GetSnapshot() Snapshot {
	return p.metrics.Snapshot()
}

func (p *PrometheusExporter) SetActiveWorkers(count int) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.activeWorkers = int32(count)
}
