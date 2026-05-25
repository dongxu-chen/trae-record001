package autotune

import (
	"context"
	"db-bench/internal/config"
	"db-bench/internal/metrics"
	"log"
	"math"
	"sync"
	"time"
)

type PIDController struct {
	Kp, Ki, Kd float64
	setpoint   float64
	integral   float64
	prevError  float64
	firstRun   bool
}

func NewPIDController(kp, ki, kd float64, setpoint float64) *PIDController {
	return &PIDController{
		Kp:        kp,
		Ki:        ki,
		Kd:        kd,
		setpoint:  setpoint,
		firstRun:  true,
	}
}

func (pid *PIDController) Compute(actual float64, dt float64) float64 {
	error := pid.setpoint - actual

	if pid.firstRun {
		pid.prevError = error
		pid.firstRun = false
		return pid.Kp * error
	}

	pid.integral += error * dt
	derivative := (error - pid.prevError) / dt
	pid.prevError = error

	return pid.Kp*error + pid.Ki*pid.integral + pid.Kd*derivative
}

func (pid *PIDController) Reset() {
	pid.integral = 0
	pid.prevError = 0
	pid.firstRun = true
}

type ConcurrencyChangeEvent struct {
	OldConcurrency int
	NewConcurrency int
	Reason         string
	P99Latency     float64
	QPS            float64
}

type AutoTuner struct {
	cfg           config.AutoTuneConfig
	pid           *PIDController
	mu            sync.Mutex
	concurrency   int
	history       []metrics.Snapshot
	inflectionCnt int
	peakQPS       float64
	peakFound     bool
	peakLatency   float64
	listeners     []func(ConcurrencyChangeEvent)
	lastAdjust    time.Time
}

func NewAutoTuner(cfg config.AutoTuneConfig) *AutoTuner {
	if cfg.MinConcurrency <= 0 {
		cfg.MinConcurrency = 1
	}
	if cfg.MaxConcurrency <= 0 {
		cfg.MaxConcurrency = 1000
	}
	if cfg.AdjustInterval <= 0 {
		cfg.AdjustInterval = 10 * time.Second
	}
	if cfg.Kp == 0 {
		cfg.Kp = 0.5
	}
	if cfg.Ki == 0 {
		cfg.Ki = 0.01
	}
	if cfg.Kd == 0 {
		cfg.Kd = 0.1
	}
	if cfg.InflectionWindow <= 0 {
		cfg.InflectionWindow = 3
	}

	at := &AutoTuner{
		cfg:         cfg,
		concurrency: cfg.MinConcurrency,
		peakQPS:     0,
		peakFound:   false,
		lastAdjust:  time.Now(),
	}

	if cfg.Mode == config.AutoTuneLatency && cfg.TargetLatencyP99 > 0 {
		at.pid = NewPIDController(cfg.Kp, cfg.Ki, cfg.Kd, cfg.TargetLatencyP99)
	}

	return at
}

func (at *AutoTuner) OnConcurrencyChange(fn func(ConcurrencyChangeEvent)) {
	at.mu.Lock()
	defer at.mu.Unlock()
	at.listeners = append(at.listeners, fn)
}

func (at *AutoTuner) notify(event ConcurrencyChangeEvent) {
	for _, fn := range at.listeners {
		fn(event)
	}
}

func (at *AutoTuner) CurrentConcurrency() int {
	at.mu.Lock()
	defer at.mu.Unlock()
	return at.concurrency
}

func (at *AutoTuner) PeakFound() bool {
	at.mu.Lock()
	defer at.mu.Unlock()
	return at.peakFound
}

func (at *AutoTuner) PeakQPS() float64 {
	at.mu.Lock()
	defer at.mu.Unlock()
	return at.peakQPS
}

func (at *AutoTuner) PeakLatency() float64 {
	at.mu.Lock()
	defer at.mu.Unlock()
	return at.peakLatency
}

func (at *AutoTuner) checkInflectionPoint(qps float64) bool {
	at.history = append(at.history, metrics.Snapshot{QPS: qps})
	if len(at.history) > at.cfg.InflectionWindow+2 {
		at.history = at.history[1:]
	}

	if len(at.history) < at.cfg.InflectionWindow+2 {
		return false
	}

	var decreasingCount int
	for i := len(at.history) - at.cfg.InflectionWindow; i < len(at.history); i++ {
		if at.history[i].QPS < at.history[i-1].QPS*0.98 {
			decreasingCount++
		}
	}

	if decreasingCount >= at.cfg.InflectionWindow {
		if !at.peakFound {
			at.peakFound = true
			at.peakQPS = at.history[len(at.history)-at.cfg.InflectionWindow-1].QPS
			at.peakLatency = at.history[len(at.history)-at.cfg.InflectionWindow-1].P99
		}
		return true
	}

	return false
}

func (at *AutoTuner) Adjust(snap metrics.Snapshot) (int, bool, string) {
	at.mu.Lock()
	defer at.mu.Unlock()

	now := time.Now()
	if now.Sub(at.lastAdjust) < at.cfg.AdjustInterval {
		return at.concurrency, false, ""
	}
	at.lastAdjust = now

	dt := at.cfg.AdjustInterval.Seconds()
	oldConcurrency := at.concurrency
	var newConcurrency int
	var reason string

	switch at.cfg.Mode {
	case config.AutoTuneLatency:
		newConcurrency, reason = at.adjustByLatency(snap, dt)
	case config.AutoTuneThroughput:
		newConcurrency, reason = at.adjustByThroughput(snap)
	default:
		newConcurrency, reason = at.adjustByLatency(snap, dt)
	}

	newConcurrency = int(math.Max(float64(at.cfg.MinConcurrency),
		math.Min(float64(at.cfg.MaxConcurrency), float64(newConcurrency))))

	shouldStop := false
	if at.cfg.StopOnInflection && at.checkInflectionPoint(snap.QPS) {
		at.inflectionCnt++
		if at.inflectionCnt >= at.cfg.InflectionWindow {
			shouldStop = true
			reason = "inflection point detected, peak QPS reached"
		}
	}

	event := ConcurrencyChangeEvent{
		OldConcurrency: oldConcurrency,
		NewConcurrency: newConcurrency,
		Reason:         reason,
		P99Latency:     snap.P99,
		QPS:            snap.QPS,
	}

	if newConcurrency != oldConcurrency {
		at.concurrency = newConcurrency
		at.notify(event)
		log.Printf("[AutoTune] %d → %d | P99: %.2fms | QPS: %.2f | %s",
			oldConcurrency, newConcurrency, snap.P99, snap.QPS, reason)
	}

	return newConcurrency, shouldStop, reason
}

func (at *AutoTuner) adjustByLatency(snap metrics.Snapshot, dt float64) (int, string) {
	if at.pid == nil {
		return at.concurrency + 5, "increasing to find limit"
	}

	if snap.TotalOps < 100 {
		return at.concurrency + int(math.Max(1, float64(at.concurrency)*0.1)),
			"warmup period, increasing concurrency"
	}

	output := at.pid.Compute(snap.P99, dt)
	delta := int(math.Round(output))

	if delta > 0 && snap.P99 < at.cfg.TargetLatencyP99*0.7 {
		delta = int(math.Max(float64(delta), float64(at.concurrency)*0.1))
	}

	reason := "PID adjustment"
	if delta > 0 {
		reason = "latency below target, increasing concurrency"
	} else if delta < 0 {
		reason = "latency above target, decreasing concurrency"
	} else {
		reason = "latency at target, holding concurrency"
	}

	return at.concurrency + delta, reason
}

func (at *AutoTuner) adjustByThroughput(snap metrics.Snapshot) (int, string) {
	if snap.TotalOps < 100 {
		return at.concurrency + int(math.Max(5, float64(at.concurrency)*0.1)),
			"warmup period, increasing concurrency"
	}

	step := int(math.Max(1, float64(at.concurrency)*0.1))

	if snap.ErrorRate > 0.05 {
		return at.concurrency - step, "error rate too high, decreasing concurrency"
	}

	if snap.P99 > at.cfg.TargetLatencyP99*1.2 && at.cfg.TargetLatencyP99 > 0 {
		return at.concurrency - step, "latency exceeded limit, decreasing concurrency"
	}

	return at.concurrency + step, "seeking maximum throughput"
}

func (at *AutoTuner) Run(ctx context.Context, getSnapshot func() metrics.Snapshot,
	onAdjust func(newConcurrency int) error) error {

	ticker := time.NewTicker(at.cfg.AdjustInterval / 2)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			snap := getSnapshot()
			newConcurrency, shouldStop, _ := at.Adjust(snap)

			if err := onAdjust(newConcurrency); err != nil {
				return err
			}

			if shouldStop {
				log.Printf("[AutoTune] Stopping: peak QPS=%.2f at P99=%.2fms",
					at.peakQPS, at.peakLatency)
				return nil
			}
		}
	}
}
