package metrics

import (
	"db-bench/internal/driver"
	"expvar"
	"fmt"
	"sync"
	"sync/atomic"
	"time"
)

type Metrics struct {
	totalOps     atomic.Uint64
	successOps   atomic.Uint64
	failedOps    atomic.Uint64
	readOps      atomic.Uint64
	writeOps     atomic.Uint64
	hotspotOps   atomic.Uint64
	totalLatency atomic.Uint64

	allLatency     *TDigest
	readLatency    *TDigest
	writeLatency   *TDigest
	hotspotLatency *TDigest

	lastResetTime time.Time
	mu            sync.Mutex
}

type Snapshot struct {
	Timestamp  time.Time
	Duration   time.Duration
	TotalOps   uint64
	SuccessOps uint64
	FailedOps  uint64
	ReadOps    uint64
	WriteOps   uint64
	HotspotOps uint64
	QPS        float64
	TPS        float64
	ErrorRate  float64
	ReadRatio  float64
	WriteRatio float64

	P50  float64
	P99  float64
	P999 float64

	ReadP50  float64
	ReadP99  float64
	ReadP999 float64

	WriteP50  float64
	WriteP99  float64
	WriteP999 float64

	HotspotP50  float64
	HotspotP99  float64
	HotspotP999 float64

	AvgLatency float64
}

func NewMetrics() *Metrics {
	return &Metrics{
		allLatency:     NewTDigest(200, 2000),
		readLatency:    NewTDigest(200, 2000),
		writeLatency:   NewTDigest(200, 2000),
		hotspotLatency: NewTDigest(200, 2000),
		lastResetTime:  time.Now(),
	}
}

func (m *Metrics) Record(result driver.Result, isHotspot bool) {
	m.totalOps.Add(1)

	if result.Success {
		m.successOps.Add(1)
		m.totalLatency.Add(uint64(result.DurationMs * 1000))
	} else {
		m.failedOps.Add(1)
	}

	m.allLatency.Add(result.DurationMs, 1.0)

	switch result.OpType {
	case driver.OpRead:
		m.readOps.Add(1)
		m.readLatency.Add(result.DurationMs, 1.0)
	case driver.OpWrite:
		m.writeOps.Add(1)
		m.writeLatency.Add(result.DurationMs, 1.0)
	}

	if isHotspot {
		m.hotspotOps.Add(1)
		m.hotspotLatency.Add(result.DurationMs, 1.0)
	}
}

func (m *Metrics) Snapshot() Snapshot {
	m.mu.Lock()
	defer m.mu.Unlock()

	now := time.Now()
	duration := now.Sub(m.lastResetTime)
	seconds := duration.Seconds()

	total := m.totalOps.Load()
	success := m.successOps.Load()
	failed := m.failedOps.Load()
	reads := m.readOps.Load()
	writes := m.writeOps.Load()
	totalLat := m.totalLatency.Load()

	var qps, tps, errorRate, avgLat float64
	if seconds > 0 {
		qps = float64(total) / seconds
		tps = float64(writes) / seconds
	}
	if total > 0 {
		errorRate = float64(failed) / float64(total)
	}
	if success > 0 {
		avgLat = float64(totalLat) / float64(success) / 1000.0
	}

	var readRatio, writeRatio float64
	if total > 0 {
		readRatio = float64(reads) / float64(total)
		writeRatio = float64(writes) / float64(total)
	}

	return Snapshot{
		Timestamp:    now,
		Duration:     duration,
		TotalOps:     total,
		SuccessOps:   success,
		FailedOps:    failed,
		ReadOps:      reads,
		WriteOps:     writes,
		HotspotOps:   m.hotspotOps.Load(),
		QPS:          qps,
		TPS:          tps,
		ErrorRate:    errorRate,
		ReadRatio:    readRatio,
		WriteRatio:   writeRatio,
		P50:          m.allLatency.Quantile(0.50),
		P99:          m.allLatency.Quantile(0.99),
		P999:         m.allLatency.Quantile(0.999),
		ReadP50:      m.readLatency.Quantile(0.50),
		ReadP99:      m.readLatency.Quantile(0.99),
		ReadP999:     m.readLatency.Quantile(0.999),
		WriteP50:     m.writeLatency.Quantile(0.50),
		WriteP99:     m.writeLatency.Quantile(0.99),
		WriteP999:    m.writeLatency.Quantile(0.999),
		HotspotP50:   m.hotspotLatency.Quantile(0.50),
		HotspotP99:   m.hotspotLatency.Quantile(0.99),
		HotspotP999:  m.hotspotLatency.Quantile(0.999),
		AvgLatency:   avgLat,
	}
}

func (m *Metrics) Reset() {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.totalOps.Store(0)
	m.successOps.Store(0)
	m.failedOps.Store(0)
	m.readOps.Store(0)
	m.writeOps.Store(0)
	m.hotspotOps.Store(0)
	m.totalLatency.Store(0)

	m.allLatency.Reset()
	m.readLatency.Reset()
	m.writeLatency.Reset()
	m.hotspotLatency.Reset()

	m.lastResetTime = time.Now()
}

func (s Snapshot) String() string {
	return fmt.Sprintf(
		"QPS: %.2f | TPS: %.2f | Err: %.2f%% | P50: %.2fms | P99: %.2fms | P999: %.2fms | Total: %d (R:%d/W:%d)",
		s.QPS, s.TPS, s.ErrorRate*100, s.P50, s.P99, s.P999,
		s.TotalOps, s.ReadOps, s.WriteOps,
	)
}

func (m *Metrics) RestoreFromSnapshot(snap Snapshot) {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.totalOps.Store(snap.TotalOps)
	m.successOps.Store(snap.SuccessOps)
	m.failedOps.Store(snap.FailedOps)
	m.readOps.Store(snap.ReadOps)
	m.writeOps.Store(snap.WriteOps)
	m.hotspotOps.Store(snap.HotspotOps)

	if snap.AvgLatency > 0 && snap.SuccessOps > 0 {
		m.totalLatency.Store(uint64(snap.AvgLatency * float64(snap.SuccessOps) * 1000))
	}

	if snap.P50 > 0 {
		m.allLatency.Add(snap.P50, float64(snap.TotalOps)*0.5)
	}
	if snap.P99 > 0 {
		m.allLatency.Add(snap.P99, float64(snap.TotalOps)*0.49)
	}
	if snap.P999 > 0 {
		m.allLatency.Add(snap.P999, float64(snap.TotalOps)*0.009)
	}

	if snap.ReadP50 > 0 && snap.ReadOps > 0 {
		m.readLatency.Add(snap.ReadP50, float64(snap.ReadOps)*0.5)
	}
	if snap.ReadP99 > 0 && snap.ReadOps > 0 {
		m.readLatency.Add(snap.ReadP99, float64(snap.ReadOps)*0.49)
	}
	if snap.ReadP999 > 0 && snap.ReadOps > 0 {
		m.readLatency.Add(snap.ReadP999, float64(snap.ReadOps)*0.009)
	}

	if snap.WriteP50 > 0 && snap.WriteOps > 0 {
		m.writeLatency.Add(snap.WriteP50, float64(snap.WriteOps)*0.5)
	}
	if snap.WriteP99 > 0 && snap.WriteOps > 0 {
		m.writeLatency.Add(snap.WriteP99, float64(snap.WriteOps)*0.49)
	}
	if snap.WriteP999 > 0 && snap.WriteOps > 0 {
		m.writeLatency.Add(snap.WriteP999, float64(snap.WriteOps)*0.009)
	}

	if snap.HotspotP50 > 0 && snap.HotspotOps > 0 {
		m.hotspotLatency.Add(snap.HotspotP50, float64(snap.HotspotOps)*0.5)
	}
	if snap.HotspotP99 > 0 && snap.HotspotOps > 0 {
		m.hotspotLatency.Add(snap.HotspotP99, float64(snap.HotspotOps)*0.49)
	}
	if snap.HotspotP999 > 0 && snap.HotspotOps > 0 {
		m.hotspotLatency.Add(snap.HotspotP999, float64(snap.HotspotOps)*0.009)
	}

	if snap.Duration > 0 {
		m.lastResetTime = time.Now().Add(-snap.Duration)
	}
}

func (s Snapshot) PrettyPrint() string {
	return fmt.Sprintf(`
=== Metrics Snapshot ===
Duration: %s
Total Operations: %d
  - Read:  %d (%.1f%%)
  - Write: %d (%.1f%%)
  - Hotspot: %d
Success: %d, Failed: %d (Error Rate: %.2f%%)
Throughput:
  - QPS: %.2f
  - TPS: %.2f
Latency (ms):
  - Overall: P50=%.2f, P99=%.2f, P999=%.2f, Avg=%.2f
  - Read:    P50=%.2f, P99=%.2f, P999=%.2f
  - Write:   P50=%.2f, P99=%.2f, P999=%.2f
  - Hotspot: P50=%.2f, P99=%.2f, P999=%.2f
`,
		s.Duration.Round(time.Second),
		s.TotalOps,
		s.ReadOps, s.ReadRatio*100,
		s.WriteOps, s.WriteRatio*100,
		s.HotspotOps,
		s.SuccessOps, s.FailedOps, s.ErrorRate*100,
		s.QPS, s.TPS,
		s.P50, s.P99, s.P999, s.AvgLatency,
		s.ReadP50, s.ReadP99, s.ReadP999,
		s.WriteP50, s.WriteP99, s.WriteP999,
		s.HotspotP50, s.HotspotP99, s.HotspotP999,
	)
}

func (m *Metrics) ExportExpvars() {
	snap := m.Snapshot()
	expvar.Publish("db_bench_qps", expvar.Float(func() float64 { return m.Snapshot().QPS }))
	expvar.Publish("db_bench_tps", expvar.Float(func() float64 { return m.Snapshot().TPS }))
	expvar.Publish("db_bench_error_rate", expvar.Float(func() float64 { return m.Snapshot().ErrorRate }))
	_ = snap
}
