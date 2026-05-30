package prometheus

import (
	"context"
	"net/http"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/sirupsen/logrus"
)

type Collector struct {
	registry               *prometheus.Registry
	logger                 *logrus.Logger
	consumerGroupLag       *prometheus.GaugeVec
	consumerGroupTotalLag  *prometheus.GaugeVec
	consumerGroupMembers   *prometheus.GaugeVec
	consumerOffset         *prometheus.GaugeVec
	topicEndOffset         *prometheus.GaugeVec
	scalerReplicas         *prometheus.GaugeVec
	scalerEventsTotal      *prometheus.CounterVec
	scalerActionsTotal     *prometheus.CounterVec
	scalerLagThreshold     *prometheus.GaugeVec
	predictedLag           *prometheus.GaugeVec
	scrapeInterval         time.Duration
	mu                     sync.RWMutex
	lagHistory             map[string][]LagRecord
	maxHistorySize         int
}

type LagRecord struct {
	Timestamp time.Time
	Lag       int64
}

type CollectorConfig struct {
	ScrapeInterval  time.Duration
	MaxHistorySize  int
	ListenAddress   string
}

func NewCollector(config CollectorConfig, logger *logrus.Logger) *Collector {
	registry := prometheus.NewRegistry()

	collector := &Collector{
		registry:       registry,
		logger:         logger,
		scrapeInterval: config.ScrapeInterval,
		maxHistorySize: config.MaxHistorySize,
		lagHistory:     make(map[string][]LagRecord),
	}

	collector.initMetrics()
	collector.startHTTPServer(config.ListenAddress)

	return collector
}

func (c *Collector) initMetrics() {
	c.consumerGroupLag = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "kafka_consumer_group_lag",
			Help: "Current lag of a consumer group per topic partition",
		},
		[]string{"group", "topic", "partition"},
	)

	c.consumerGroupTotalLag = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "kafka_consumer_group_total_lag",
			Help: "Total lag of a consumer group across all partitions",
		},
		[]string{"group"},
	)

	c.consumerGroupMembers = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "kafka_consumer_group_members",
			Help: "Number of members in a consumer group",
		},
		[]string{"group"},
	)

	c.consumerOffset = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "kafka_consumer_group_offset",
			Help: "Current offset of a consumer group per topic partition",
		},
		[]string{"group", "topic", "partition"},
	)

	c.topicEndOffset = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "kafka_topic_end_offset",
			Help: "Latest offset of a topic partition",
		},
		[]string{"topic", "partition"},
	)

	c.scalerReplicas = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "kafka_autoscaler_replicas",
			Help: "Current number of replicas for the consumer deployment",
		},
		[]string{"deployment", "namespace"},
	)

	c.scalerEventsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "kafka_autoscaler_events_total",
			Help: "Total number of scaler events",
		},
		[]string{"type", "group"},
	)

	c.scalerActionsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "kafka_autoscaler_actions_total",
			Help: "Total number of scaler actions (scale up/down)",
		},
		[]string{"action", "group", "deployment"},
	)

	c.scalerLagThreshold = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "kafka_autoscaler_lag_threshold",
			Help: "Lag threshold configured for the autoscaler",
		},
		[]string{"group", "type"},
	)

	c.predictedLag = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "kafka_autoscaler_predicted_lag",
			Help: "Predicted lag for the consumer group",
		},
		[]string{"group", "prediction_window"},
	)

	c.registry.MustRegister(
		c.consumerGroupLag,
		c.consumerGroupTotalLag,
		c.consumerGroupMembers,
		c.consumerOffset,
		c.topicEndOffset,
		c.scalerReplicas,
		c.scalerEventsTotal,
		c.scalerActionsTotal,
		c.scalerLagThreshold,
		c.predictedLag,
	)
}

func (c *Collector) startHTTPServer(address string) {
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.HandlerFor(c.registry, promhttp.HandlerOpts{}))
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	go func() {
		c.logger.Infof("Starting Prometheus metrics server on %s", address)
		if err := http.ListenAndServe(address, mux); err != nil && err != http.ErrServerClosed {
			c.logger.Fatalf("Failed to start metrics server: %v", err)
		}
	}()
}

func (c *Collector) RecordConsumerGroupLag(groupID, topic string, partition int32, currentOffset, endOffset, lag int64) {
	partitionStr := string(rune(partition + '0'))
	c.consumerGroupLag.WithLabelValues(groupID, topic, partitionStr).Set(float64(lag))
	c.consumerOffset.WithLabelValues(groupID, topic, partitionStr).Set(float64(currentOffset))
	c.topicEndOffset.WithLabelValues(topic, partitionStr).Set(float64(endOffset))
}

func (c *Collector) RecordConsumerGroupTotalLag(groupID string, totalLag int64) {
	c.consumerGroupTotalLag.WithLabelValues(groupID).Set(float64(totalLag))
	c.addLagHistory(groupID, totalLag)
}

func (c *Collector) RecordConsumerGroupMembers(groupID string, members int) {
	c.consumerGroupMembers.WithLabelValues(groupID).Set(float64(members))
}

func (c *Collector) RecordScalerReplicas(deployment, namespace string, replicas int32) {
	c.scalerReplicas.WithLabelValues(deployment, namespace).Set(float64(replicas))
}

func (c *Collector) RecordScalerEvent(eventType, groupID string) {
	c.scalerEventsTotal.WithLabelValues(eventType, groupID).Inc()
}

func (c *Collector) RecordScalerAction(action, groupID, deployment string) {
	c.scalerActionsTotal.WithLabelValues(action, groupID, deployment).Inc()
}

func (c *Collector) RecordLagThreshold(groupID, thresholdType string, threshold float64) {
	c.scalerLagThreshold.WithLabelValues(groupID, thresholdType).Set(threshold)
}

func (c *Collector) RecordPredictedLag(groupID, window string, predictedLag int64) {
	c.predictedLag.WithLabelValues(groupID, window).Set(float64(predictedLag))
}

func (c *Collector) addLagHistory(groupID string, lag int64) {
	c.mu.Lock()
	defer c.mu.Unlock()

	record := LagRecord{
		Timestamp: time.Now(),
		Lag:       lag,
	}

	history, ok := c.lagHistory[groupID]
	if !ok {
		history = make([]LagRecord, 0, c.maxHistorySize)
	}

	if len(history) >= c.maxHistorySize {
		history = history[1:]
	}

	c.lagHistory[groupID] = append(history, record)
}

func (c *Collector) GetLagHistory(groupID string) []LagRecord {
	c.mu.RLock()
	defer c.mu.RUnlock()

	history, ok := c.lagHistory[groupID]
	if !ok {
		return []LagRecord{}
	}

	result := make([]LagRecord, len(history))
	copy(result, history)
	return result
}

func (c *Collector) GetLagHistoryForDuration(groupID string, duration time.Duration) []LagRecord {
	c.mu.RLock()
	defer c.mu.RUnlock()

	history, ok := c.lagHistory[groupID]
	if !ok {
		return []LagRecord{}
	}

	cutoff := time.Now().Add(-duration)
	var result []LagRecord
	for i := len(history) - 1; i >= 0; i-- {
		if history[i].Timestamp.After(cutoff) {
			result = append([]LagRecord{history[i]}, result...)
		} else {
			break
		}
	}

	return result
}

func (c *Collector) GetLagRateOfChange(groupID string, duration time.Duration) (float64, bool) {
	history := c.GetLagHistoryForDuration(groupID, duration)
	if len(history) < 2 {
		return 0, false
	}

	first := history[0]
	last := history[len(history)-1]

	timeDiff := last.Timestamp.Sub(first.Timestamp).Seconds()
	if timeDiff <= 0 {
		return 0, false
	}

	lagDiff := float64(last.Lag - first.Lag)
	return lagDiff / timeDiff, true
}

func (c *Collector) GetAverageLag(groupID string, duration time.Duration) (float64, bool) {
	history := c.GetLagHistoryForDuration(groupID, duration)
	if len(history) == 0 {
		return 0, false
	}

	var sum int64
	for _, record := range history {
		sum += record.Lag
	}

	return float64(sum) / float64(len(history)), true
}

func (c *Collector) GetMaxLag(groupID string, duration time.Duration) (int64, bool) {
	history := c.GetLagHistoryForDuration(groupID, duration)
	if len(history) == 0 {
		return 0, false
	}

	maxLag := history[0].Lag
	for _, record := range history[1:] {
		if record.Lag > maxLag {
			maxLag = record.Lag
		}
	}

	return maxLag, true
}

func (c *Collector) GetRegistry() *prometheus.Registry {
	return c.registry
}

func (c *Collector) Shutdown(ctx context.Context) error {
	c.logger.Info("Shutting down Prometheus collector")
	return nil
}

type ConsumerGroupMetrics struct {
	GroupID         string
	TotalLag        int64
	MemberCount     int
	LagRate         float64
	AverageLag      float64
	PredictedLag5m  int64
	PredictedLag15m int64
	PredictedLag1h  int64
}

func (c *Collector) GetConsumerGroupMetrics(groupID string) (*ConsumerGroupMetrics, bool) {
	history := c.GetLagHistory(groupID)
	if len(history) == 0 {
		return nil, false
	}

	metrics := &ConsumerGroupMetrics{
		GroupID:  groupID,
		TotalLag: history[len(history)-1].Lag,
	}

	if lagRate, ok := c.GetLagRateOfChange(groupID, 5*time.Minute); ok {
		metrics.LagRate = lagRate
	}

	if avgLag, ok := c.GetAverageLag(groupID, 5*time.Minute); ok {
		metrics.AverageLag = avgLag
	}

	metrics.PredictedLag5m = c.predictLag(groupID, 5*time.Minute)
	metrics.PredictedLag15m = c.predictLag(groupID, 15*time.Minute)
	metrics.PredictedLag1h = c.predictLag(groupID, time.Hour)

	return metrics, true
}

func (c *Collector) predictLag(groupID string, predictionWindow time.Duration) int64 {
	history := c.GetLagHistory(groupID)
	if len(history) < 2 {
		return 0
	}

	lagRate, ok := c.GetLagRateOfChange(groupID, 15*time.Minute)
	if !ok {
		return history[len(history)-1].Lag
	}

	currentLag := float64(history[len(history)-1].Lag)
	predictedLag := currentLag + lagRate*predictionWindow.Seconds()

	if predictedLag < 0 {
		predictedLag = 0
	}

	return int64(predictedLag)
}
