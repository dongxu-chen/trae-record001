package metrics

import (
	"net/http"
	"strconv"
	"sync"
	"time"
	"health-check/internal/model"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	once     sync.Once
	instance *Exporter
)

type Exporter struct {
	probeStatus        *prometheus.GaugeVec
	probeLatency       *prometheus.HistogramVec
	probeTotal         *prometheus.CounterVec
	availability       *prometheus.GaugeVec
	errorRate          *prometheus.GaugeVec
	avgLatency         *prometheus.GaugeVec
	p95Latency         *prometheus.GaugeVec
	alertFiring        *prometheus.GaugeVec
	poolWorkers        prometheus.Gauge
	poolQueueLength    prometheus.Gauge

	schedulingInterval  *prometheus.GaugeVec
	schedulingWeight    *prometheus.GaugeVec
	healthScore         *prometheus.GaugeVec

	predictedValue      *prometheus.GaugeVec
	predictedTrend      *prometheus.GaugeVec
	predictionConfidence *prometheus.GaugeVec
	predictionWarning   *prometheus.GaugeVec

	traceTotal          prometheus.Counter
	spanTotal           prometheus.Counter
	spanLatency         *prometheus.HistogramVec
}

func New() *Exporter {
	once.Do(func() {
		instance = &Exporter{
			probeStatus: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_probe_status",
					Help: "Current status of the endpoint (1=UP, 0=DOWN, 0.5=DEGRADE)",
				},
				[]string{"endpoint_id", "endpoint_name", "protocol"},
			),
			probeLatency: prometheus.NewHistogramVec(
				prometheus.HistogramOpts{
					Name:    "health_probe_latency_seconds",
					Help:    "Latency of probe requests",
					Buckets: prometheus.DefBuckets,
				},
				[]string{"endpoint_id", "endpoint_name", "protocol"},
			),
			probeTotal: prometheus.NewCounterVec(
				prometheus.CounterOpts{
					Name: "health_probe_total",
					Help: "Total number of probes",
				},
				[]string{"endpoint_id", "endpoint_name", "protocol", "status"},
			),
			availability: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_availability_percent",
					Help: "Availability percentage in sliding window",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			errorRate: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_error_rate_percent",
					Help: "Error rate percentage in sliding window",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			avgLatency: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_avg_latency_seconds",
					Help: "Average latency in sliding window",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			p95Latency: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_p95_latency_seconds",
					Help: "P95 latency in sliding window",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			alertFiring: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_alert_firing",
					Help: "Whether an alert is firing (1=firing, 0=not firing)",
				},
				[]string{"alert_id", "endpoint_id", "severity"},
			),
			poolWorkers: prometheus.NewGauge(
				prometheus.GaugeOpts{
					Name: "health_probe_pool_workers",
					Help: "Number of active workers in the probe pool",
				},
			),
			poolQueueLength: prometheus.NewGauge(
				prometheus.GaugeOpts{
					Name: "health_probe_pool_queue_length",
					Help: "Current queue length of the probe pool",
				},
			),
			schedulingInterval: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_scheduling_interval_seconds",
					Help: "Current scheduling interval for each endpoint",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			schedulingWeight: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_scheduling_weight",
					Help: "Current weight of each endpoint",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			healthScore: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_score_percent",
					Help: "Health score for each endpoint based on recent results",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			predictedValue: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_predicted_value",
					Help: "Predicted availability value",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			predictedTrend: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_predicted_trend",
					Help: "Predicted trend direction (-1=degrading, 0=stable, 1=improving)",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			predictionConfidence: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_prediction_confidence",
					Help: "Confidence level of the prediction",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			predictionWarning: prometheus.NewGaugeVec(
				prometheus.GaugeOpts{
					Name: "health_prediction_warning",
					Help: "Whether prediction has warning (1=warning, 0=critical, 2=ok)",
				},
				[]string{"endpoint_id", "endpoint_name"},
			),
			traceTotal: prometheus.NewCounter(
				prometheus.CounterOpts{
					Name: "health_trace_total",
					Help: "Total number of traces",
				},
			),
			spanTotal: prometheus.NewCounter(
				prometheus.CounterOpts{
					Name: "health_span_total",
					Help: "Total number of spans",
				},
			),
			spanLatency: prometheus.NewHistogramVec(
				prometheus.HistogramOpts{
					Name:    "health_span_latency_seconds",
					Help:    "Latency of trace spans",
					Buckets: prometheus.DefBuckets,
				},
				[]string{"endpoint_id", "operation", "status"},
			),
		}

		prometheus.MustRegister(instance.probeStatus)
		prometheus.MustRegister(instance.probeLatency)
		prometheus.MustRegister(instance.probeTotal)
		prometheus.MustRegister(instance.availability)
		prometheus.MustRegister(instance.errorRate)
		prometheus.MustRegister(instance.avgLatency)
		prometheus.MustRegister(instance.p95Latency)
		prometheus.MustRegister(instance.alertFiring)
		prometheus.MustRegister(instance.poolWorkers)
		prometheus.MustRegister(instance.poolQueueLength)
		prometheus.MustRegister(instance.schedulingInterval)
		prometheus.MustRegister(instance.schedulingWeight)
		prometheus.MustRegister(instance.healthScore)
		prometheus.MustRegister(instance.predictedValue)
		prometheus.MustRegister(instance.predictedTrend)
		prometheus.MustRegister(instance.predictionConfidence)
		prometheus.MustRegister(instance.predictionWarning)
		prometheus.MustRegister(instance.traceTotal)
		prometheus.MustRegister(instance.spanTotal)
		prometheus.MustRegister(instance.spanLatency)
	})

	return instance
}

func (e *Exporter) RecordProbe(result *model.ProbeResult) {
	var statusValue float64
	switch result.Status {
	case model.StatusUp:
		statusValue = 1
	case model.StatusDegrade:
		statusValue = 0.5
	case model.StatusDown:
		statusValue = 0
	}

	e.probeStatus.WithLabelValues(result.EndpointID, result.Name, string(result.Protocol)).Set(statusValue)
	e.probeLatency.WithLabelValues(result.EndpointID, result.Name, string(result.Protocol)).Observe(float64(result.Latency) / float64(time.Second))
	e.probeTotal.WithLabelValues(result.EndpointID, result.Name, string(result.Protocol), string(result.Status)).Inc()
}

func (e *Exporter) RecordWindowStats(endpointID, endpointName string, stats *model.WindowStats) {
	e.availability.WithLabelValues(endpointID, endpointName).Set(stats.Availability)
	e.errorRate.WithLabelValues(endpointID, endpointName).Set(stats.ErrorRate)
	e.avgLatency.WithLabelValues(endpointID, endpointName).Set(float64(stats.AvgLatency) / float64(time.Second))
	e.p95Latency.WithLabelValues(endpointID, endpointName).Set(float64(stats.P95Latency) / float64(time.Second))
}

func (e *Exporter) SetAlertFiring(alertID, endpointID, severity string, firing bool) {
	var value float64
	if firing {
		value = 1
	}
	e.alertFiring.WithLabelValues(alertID, endpointID, severity).Set(value)
}

func (e *Exporter) SetPoolStats(activeWorkers int64, queueLength int) {
	e.poolWorkers.Set(float64(activeWorkers))
	e.poolQueueLength.Set(float64(queueLength))
}

func (e *Exporter) RecordScheduling(endpointID, endpointName string, interval int, weight int, healthScore float64) {
	e.schedulingInterval.WithLabelValues(endpointID, endpointName).Set(float64(interval))
	e.schedulingWeight.WithLabelValues(endpointID, endpointName).Set(float64(weight))
	e.healthScore.WithLabelValues(endpointID, endpointName).Set(healthScore)
}

func (e *Exporter) RecordPrediction(pred *model.PredictionResult, endpointName string) {
	e.predictedValue.WithLabelValues(pred.EndpointID, endpointName).Set(pred.PredictedValue)
	e.predictedTrend.WithLabelValues(pred.EndpointID, endpointName).Set(float64(pred.TrendDirection))
	e.predictionConfidence.WithLabelValues(pred.EndpointID, endpointName).Set(pred.Confidence)

	var warningValue float64
	if pred.Critical {
		warningValue = 0
	} else if pred.Warning {
		warningValue = 1
	} else {
		warningValue = 2
	}
	e.predictionWarning.WithLabelValues(pred.EndpointID, endpointName).Set(warningValue)
}

func (e *Exporter) RecordSpan(endpointID, operation string, latency time.Duration, status model.Status) {
	e.spanTotal.Inc()
	e.spanLatency.WithLabelValues(endpointID, operation, string(status)).Observe(float64(latency) / float64(time.Second))
}

func (e *Exporter) RecordTrace() {
	e.traceTotal.Inc()
}

func (e *Exporter) Handler() http.Handler {
	return promhttp.Handler()
}

func (e *Exporter) StartServer(port int) error {
	mux := http.NewServeMux()
	mux.Handle("/metrics", e.Handler())
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	return http.ListenAndServe(":"+strconv.Itoa(port), mux)
}
