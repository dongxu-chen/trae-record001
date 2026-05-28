package metrics

import (
	"context"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"github.com/coldstart-optimizer/coldstart/internal/model"
)

type Collector struct {
	registry *prometheus.Registry

	coldStartTotal        *prometheus.CounterVec
	coldStartDuration     *prometheus.HistogramVec
	phaseDuration         *prometheus.HistogramVec
	imagePullBytes        prometheus.Gauge
	imagePullLatency      prometheus.Gauge
	dependencyLoadLatency prometheus.Gauge
	activeEnvs            prometheus.Gauge
	reusedEnvs            prometheus.Gauge
	poolTotal             prometheus.Gauge
	poolIdle              prometheus.Gauge
	poolBusy              prometheus.Gauge
	poolEvicted           prometheus.Counter
	poolReclaimed         prometheus.Counter
	poolLeakDetected      prometheus.Counter

	mu    sync.RWMutex
	srv   *http.Server
	addr  string
}

func NewCollector() *Collector {
	reg := prometheus.NewRegistry()
	c := &Collector{registry: reg}

	c.coldStartTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
		Namespace: "coldstart",
		Name:      "invocations_total",
		Help:      "Total number of cold start invocations by function and runtime.",
	}, []string{"function", "runtime", "status"})

	c.coldStartDuration = prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Namespace: "coldstart",
		Name:      "duration_seconds",
		Help:      "Overall cold start duration.",
		Buckets:   prometheus.ExponentialBuckets(0.01, 2, 12),
	}, []string{"function", "runtime"})

	c.phaseDuration = prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Namespace: "coldstart",
		Name:      "phase_duration_seconds",
		Help:      "Duration by phase.",
		Buckets:   prometheus.ExponentialBuckets(0.001, 2, 14),
	}, []string{"phase", "source"})

	c.imagePullBytes = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "coldstart",
		Subsystem: "image",
		Name:      "pull_bytes",
		Help:      "Size of the most recent image pull.",
	})
	c.imagePullLatency = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "coldstart",
		Subsystem: "image",
		Name:      "pull_latency_seconds",
		Help:      "Most recent image pull latency.",
	})
	c.dependencyLoadLatency = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "coldstart",
		Subsystem: "deps",
		Name:      "load_latency_seconds",
		Help:      "Most recent dependency load latency.",
	})
	c.activeEnvs = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "coldstart",
		Subsystem: "pool",
		Name:      "active_envs",
		Help:      "Active warm environments in the pool.",
	})
	c.reusedEnvs = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "coldstart",
		Subsystem: "pool",
		Name:      "reused_envs",
		Help:      "Number of times warm environments were reused.",
	})
	c.poolTotal = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "coldstart",
		Subsystem: "pool",
		Name:      "total_envs",
		Help:      "Total envs in the pool.",
	})
	c.poolIdle = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "coldstart",
		Subsystem: "pool",
		Name:      "idle_envs",
		Help:      "Idle envs in the pool.",
	})
	c.poolBusy = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "coldstart",
		Subsystem: "pool",
		Name:      "busy_envs",
		Help:      "Busy envs in the pool (max connections reached).",
	})
	c.poolEvicted = prometheus.NewCounter(prometheus.CounterOpts{
		Namespace: "coldstart",
		Subsystem: "pool",
		Name:      "evicted_total",
		Help:      "Total envs evicted from pool.",
	})
	c.poolReclaimed = prometheus.NewCounter(prometheus.CounterOpts{
		Namespace: "coldstart",
		Subsystem: "pool",
		Name:      "reclaimed_total",
		Help:      "Total envs reclaimed due to leak.",
	})
	c.poolLeakDetected = prometheus.NewCounter(prometheus.CounterOpts{
		Namespace: "coldstart",
		Subsystem: "pool",
		Name:      "leaks_detected_total",
		Help:      "Total leaks detected.",
	})

	reg.MustRegister(
		c.coldStartTotal,
		c.coldStartDuration,
		c.phaseDuration,
		c.imagePullBytes,
		c.imagePullLatency,
		c.dependencyLoadLatency,
		c.activeEnvs,
		c.reusedEnvs,
		c.poolTotal,
		c.poolIdle,
		c.poolBusy,
		c.poolEvicted,
		c.poolReclaimed,
		c.poolLeakDetected,
	)
	return c
}

func (c *Collector) Registry() *prometheus.Registry { return c.registry }

func (c *Collector) RecordProfile(p model.ColdStartProfile) {
	c.coldStartTotal.WithLabelValues(p.Function, p.Runtime, "cold").Inc()
	c.coldStartDuration.WithLabelValues(p.Function, p.Runtime).Observe(p.Total.Seconds())
	for _, ph := range p.Phases {
		c.phaseDuration.WithLabelValues(string(ph.Phase), ph.Source).Observe(ph.Duration.Seconds())
	}
	if d := p.PhaseDuration(model.PhaseDependencyLoad); d > 0 {
		c.dependencyLoadLatency.Set(d.Seconds())
	}
}

func (c *Collector) RecordImagePull(sizeBytes int64, dur time.Duration) {
	c.imagePullBytes.Set(float64(sizeBytes))
	c.imagePullLatency.Set(dur.Seconds())
}

func (c *Collector) IncActive(delta float64)  { c.activeEnvs.Add(delta) }
func (c *Collector) IncReused()               { c.reusedEnvs.Inc() }

func (c *Collector) RecordPoolStats(total, idle, busy int) {
	c.poolTotal.Set(float64(total))
	c.poolIdle.Set(float64(idle))
	c.poolBusy.Set(float64(busy))
}

func (c *Collector) IncPoolEvicted()   { c.poolEvicted.Inc() }
func (c *Collector) IncPoolReclaimed() { c.poolReclaimed.Inc() }
func (c *Collector) IncPoolLeak()      { c.poolLeakDetected.Inc() }

func (c *Collector) Listen(addr string) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.srv != nil {
		return fmt.Errorf("metrics server already running")
	}
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.HandlerFor(c.registry, promhttp.HandlerOpts{}))
	c.srv = &http.Server{Addr: addr, Handler: mux}
	c.addr = addr
	go func() {
		if err := c.srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			_ = err
		}
	}()
	return nil
}

func (c *Collector) Shutdown(ctx context.Context) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.srv == nil {
		return nil
	}
	return c.srv.Shutdown(ctx)
}
