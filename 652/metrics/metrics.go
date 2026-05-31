package metrics

import (
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type Metrics struct {
	messagesConsumedTotal   *prometheus.CounterVec
	messagesProducedTotal   *prometheus.CounterVec
	messagesFilteredTotal   *prometheus.CounterVec
	messagesDroppedTotal    *prometheus.CounterVec
	syncLatencySeconds      *prometheus.HistogramVec
	consumerLag             *prometheus.GaugeVec
	consumerLagAvg          *prometheus.GaugeVec
	hopCountDropped         *prometheus.CounterVec
	activeConnections       prometheus.Gauge
	lastSyncTimestamp       *prometheus.GaugeVec
	topicDiscoveredTotal    *prometheus.CounterVec
	topicCreatedTotal       *prometheus.CounterVec
	clusterSwitchTotal      *prometheus.CounterVec
	activeSourceCluster     prometheus.GaugeVec
	compressionRatio        *prometheus.GaugeVec
	bytesCompressedTotal    *prometheus.CounterVec
	bytesUncompressedTotal  *prometheus.CounterVec
	clusterHealthStatus     *prometheus.GaugeVec
	lagMonitor              *LagMonitor
}

type LagMonitor struct {
	mu              sync.RWMutex
	windows         map[string]*slidingWindow
	windowSize      int
	collectInterval time.Duration
	alertThreshold  float64
	stopCh          chan struct{}
	metrics         *Metrics
}

type slidingWindow struct {
	values []float64
	pos    int
	size   int
	sum    float64
	count  int
}

func newSlidingWindow(size int) *slidingWindow {
	return &slidingWindow{
		values: make([]float64, size),
		size:   size,
	}
}

func (w *slidingWindow) Add(val float64) {
	w.sum -= w.values[w.pos]
	w.values[w.pos] = val
	w.sum += val
	w.pos = (w.pos + 1) % w.size
	if w.count < w.size {
		w.count++
	}
}

func (w *slidingWindow) Average() float64 {
	if w.count == 0 {
		return 0
	}
	return w.sum / float64(w.count)
}

func NewMetrics() *Metrics {
	m := &Metrics{
		messagesConsumedTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_messages_consumed_total",
				Help: "Total number of messages consumed from source cluster",
			},
			[]string{"topic", "partition", "cluster"},
		),
		messagesProducedTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_messages_produced_total",
				Help: "Total number of messages produced to target cluster",
			},
			[]string{"topic", "partition"},
		),
		messagesFilteredTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_messages_filtered_total",
				Help: "Total number of messages filtered out",
			},
			[]string{"topic", "reason"},
		),
		messagesDroppedTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_messages_dropped_total",
				Help: "Total number of messages dropped (hop count exhausted)",
			},
			[]string{"topic"},
		),
		syncLatencySeconds: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    "kafka_mirror_sync_latency_seconds",
				Help:    "Latency of message synchronization in seconds",
				Buckets: prometheus.ExponentialBuckets(0.001, 2, 15),
			},
			[]string{"topic"},
		),
		consumerLag: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "kafka_mirror_consumer_lag",
				Help: "Current consumer offset lag for each topic/partition",
			},
			[]string{"topic", "partition"},
		),
		consumerLagAvg: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "kafka_mirror_consumer_lag_avg",
				Help: "Sliding window average consumer lag for each topic/partition",
			},
			[]string{"topic", "partition"},
		),
		hopCountDropped: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_hop_count_dropped_total",
				Help: "Total number of messages dropped due to hop count reaching zero",
			},
			[]string{"topic", "trace_id"},
		),
		activeConnections: prometheus.NewGauge(
			prometheus.GaugeOpts{
				Name: "kafka_mirror_active_connections",
				Help: "Number of active connections",
			},
		),
		lastSyncTimestamp: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "kafka_mirror_last_sync_timestamp_seconds",
				Help: "Timestamp of last successful message sync",
			},
			[]string{"topic"},
		),
		topicDiscoveredTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_topic_discovered_total",
				Help: "Total number of new topics discovered",
			},
			[]string{"topic"},
		),
		topicCreatedTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_topic_created_total",
				Help: "Total number of topics created on target cluster",
			},
			[]string{"topic", "status"},
		),
		clusterSwitchTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_cluster_switch_total",
				Help: "Total number of cluster failovers",
			},
			[]string{"from_cluster", "to_cluster", "reason"},
		),
		activeSourceCluster: *prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "kafka_mirror_active_source_cluster",
				Help: "Currently active source cluster (1=active, 0=standby)",
			},
			[]string{"cluster_name"},
		),
		compressionRatio: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "kafka_mirror_compression_ratio",
				Help: "Compression ratio (uncompressed / compressed)",
			},
			[]string{"codec"},
		),
		bytesCompressedTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_bytes_compressed_total",
				Help: "Total bytes after compression",
			},
			[]string{"codec"},
		),
		bytesUncompressedTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "kafka_mirror_bytes_uncompressed_total",
				Help: "Total bytes before compression",
			},
			[]string{"codec"},
		),
		clusterHealthStatus: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "kafka_mirror_cluster_health_status",
				Help: "Health status of source clusters (1=healthy, 0=unhealthy)",
			},
			[]string{"cluster_name", "cluster_type"},
		),
	}

	prometheus.MustRegister(
		m.messagesConsumedTotal,
		m.messagesProducedTotal,
		m.messagesFilteredTotal,
		m.messagesDroppedTotal,
		m.syncLatencySeconds,
		m.consumerLag,
		m.consumerLagAvg,
		m.hopCountDropped,
		m.activeConnections,
		m.lastSyncTimestamp,
		m.topicDiscoveredTotal,
		m.topicCreatedTotal,
		m.clusterSwitchTotal,
		m.activeSourceCluster,
		m.compressionRatio,
		m.bytesCompressedTotal,
		m.bytesUncompressedTotal,
		m.clusterHealthStatus,
	)

	return m
}

func (m *Metrics) InitLagMonitor(windowSize int, collectInterval time.Duration, alertThreshold float64) {
	m.lagMonitor = &LagMonitor{
		windows:         make(map[string]*slidingWindow),
		windowSize:      windowSize,
		collectInterval: collectInterval,
		alertThreshold:  alertThreshold,
		stopCh:          make(chan struct{}),
		metrics:         m,
	}
}

func (m *Metrics) StartLagCollector(topics []string, partitions map[string][]int32) {
	if m.lagMonitor == nil {
		return
	}

	for topic, parts := range partitions {
		for _, part := range parts {
			key := topic + "-" + strconv.FormatInt(int64(part), 10)
			m.lagMonitor.windows[key] = newSlidingWindow(m.lagMonitor.windowSize)
		}
	}

	go m.lagMonitor.collectLoop(topics, partitions)
}

func (m *Metrics) StopLagCollector() {
	if m.lagMonitor != nil {
		close(m.lagMonitor.stopCh)
	}
}

func (lm *LagMonitor) collectLoop(topics []string, partitions map[string][]int32) {
	ticker := time.NewTicker(lm.collectInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			lm.collectSample(topics, partitions)
		case <-lm.stopCh:
			return
		}
	}
}

func (lm *LagMonitor) collectSample(topics []string, partitions map[string][]int32) {
	lm.mu.Lock()
	defer lm.mu.Unlock()

	for _, topic := range topics {
		parts, ok := partitions[topic]
		if !ok {
			continue
		}
		for _, part := range parts {
			key := topic + "-" + strconv.FormatInt(int64(part), 10)
			window, exists := lm.windows[key]
			if !exists {
				window = newSlidingWindow(lm.windowSize)
				lm.windows[key] = window
			}

			currentLag := lm.metrics.GetCurrentLag(topic, part)
			window.Add(float64(currentLag))

			avgLag := window.Average()
			lm.metrics.consumerLag.WithLabelValues(topic, strconv.FormatInt(int64(part), 10)).Set(float64(currentLag))
			lm.metrics.consumerLagAvg.WithLabelValues(topic, strconv.FormatInt(int64(part), 10)).Set(avgLag)
		}
	}
}

func (m *Metrics) GetCurrentLag(topic string, partition int32) int64 {
	return 0
}

func (m *Metrics) UpdateLag(topic string, partition int32, lag int64) {
	key := topic + "-" + strconv.FormatInt(int64(partition), 10)
	if m.lagMonitor != nil {
		m.lagMonitor.mu.Lock()
		if window, exists := m.lagMonitor.windows[key]; exists {
			window.Add(float64(lag))
			avgLag := window.Average()
			m.consumerLagAvg.WithLabelValues(topic, strconv.FormatInt(int64(partition), 10)).Set(avgLag)
		}
		m.lagMonitor.mu.Unlock()
	}
	m.consumerLag.WithLabelValues(topic, strconv.FormatInt(int64(partition), 10)).Set(float64(lag))
}

func (m *Metrics) IncMessagesConsumed(topic string, partition int32, cluster string) {
	m.messagesConsumedTotal.WithLabelValues(topic, strconv.FormatInt(int64(partition), 10), cluster).Inc()
}

func (m *Metrics) IncMessagesProduced(topic string, partition int32) {
	m.messagesProducedTotal.WithLabelValues(topic, strconv.FormatInt(int64(partition), 10)).Inc()
}

func (m *Metrics) IncMessagesFiltered(topic string, reason string) {
	m.messagesFilteredTotal.WithLabelValues(topic, reason).Inc()
}

func (m *Metrics) IncMessagesDropped(topic string) {
	m.messagesDroppedTotal.WithLabelValues(topic).Inc()
}

func (m *Metrics) IncHopCountDropped(topic string, traceID string) {
	m.hopCountDropped.WithLabelValues(topic, traceID).Inc()
}

func (m *Metrics) ObserveSyncLatency(topic string, startTime time.Time) {
	latency := time.Since(startTime).Seconds()
	m.syncLatencySeconds.WithLabelValues(topic).Observe(latency)
}

func (m *Metrics) SetConsumerLag(topic string, partition int32, lag int64) {
	m.consumerLag.WithLabelValues(topic, strconv.FormatInt(int64(partition), 10)).Set(float64(lag))
}

func (m *Metrics) SetActiveConnections(count float64) {
	m.activeConnections.Set(count)
}

func (m *Metrics) SetLastSyncTimestamp(topic string) {
	m.lastSyncTimestamp.WithLabelValues(topic).Set(float64(time.Now().Unix()))
}

func (m *Metrics) IncTopicDiscovered(topic string) {
	m.topicDiscoveredTotal.WithLabelValues(topic).Inc()
}

func (m *Metrics) IncTopicCreated(topic string, status string) {
	m.topicCreatedTotal.WithLabelValues(topic, status).Inc()
}

func (m *Metrics) IncClusterSwitch(fromCluster, toCluster, reason string) {
	m.clusterSwitchTotal.WithLabelValues(fromCluster, toCluster, reason).Inc()
}

func (m *Metrics) SetActiveSourceCluster(clusterName string) {
	m.activeSourceCluster.Reset()
	m.activeSourceCluster.WithLabelValues(clusterName).Set(1)
}

func (m *Metrics) UpdateCompressionStats(codec string, compressedBytes, uncompressedBytes int64) {
	m.bytesCompressedTotal.WithLabelValues(codec).Add(float64(compressedBytes))
	m.bytesUncompressedTotal.WithLabelValues(codec).Add(float64(uncompressedBytes))
	if compressedBytes > 0 {
		ratio := float64(uncompressedBytes) / float64(compressedBytes)
		m.compressionRatio.WithLabelValues(codec).Set(ratio)
	}
}

func (m *Metrics) SetClusterHealthStatus(clusterName, clusterType string, healthy bool) {
	status := 0.0
	if healthy {
		status = 1.0
	}
	m.clusterHealthStatus.WithLabelValues(clusterName, clusterType).Set(status)
}

func (m *Metrics) StartServer(port int) error {
	http.Handle("/metrics", promhttp.Handler())
	addr := ":" + strconv.Itoa(port)
	return http.ListenAndServe(addr, nil)
}
