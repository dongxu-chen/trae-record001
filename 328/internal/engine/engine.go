package engine

import (
	"context"
	"crypto/rand"
	"db-bench/internal/autotune"
	"db-bench/internal/config"
	"db-bench/internal/driver"
	"db-bench/internal/metrics"
	"db-bench/internal/scenario"
	"db-bench/internal/storage"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"golang.org/x/time/rate"
)

type BenchmarkEngine struct {
	cfg          config.Config
	dbDriver     driver.DatabaseDriver
	scenario     *scenario.ScenarioGenerator
	exporter     *metrics.PrometheusExporter
	rateLimiter  *rate.Limiter
	store        *storage.Storage
	autoTuner    *autotune.AutoTuner
	wg           sync.WaitGroup
	cancelFunc   context.CancelFunc
	activeWorkers int32
	workerMu     sync.Mutex
	workerCancel []context.CancelFunc
	runID        string
	startTime    time.Time
	checkpointMu sync.Mutex
	checkpointNum int
	lastOps      uint64
	lastOpsTime  time.Time
}

func generateRunID() string {
	b := make([]byte, 8)
	rand.Read(b)
	return "run-" + hex.EncodeToString(b)
}

func NewBenchmarkEngine(cfg config.Config) (*BenchmarkEngine, error) {
	dbDriver, err := driver.NewDriver(cfg.Database)
	if err != nil {
		return nil, fmt.Errorf("failed to create database driver: %w", err)
	}

	gen, err := scenario.NewGenerator(cfg.Scenario)
	if err != nil {
		return nil, fmt.Errorf("failed to create scenario generator: %w", err)
	}

	m := metrics.NewMetrics()
	exporter := metrics.NewPrometheusExporter(m, cfg.Metrics, string(cfg.Database.Type))

	var limiter *rate.Limiter
	if cfg.Scenario.RateLimit > 0 {
		limiter = rate.NewLimiter(rate.Limit(cfg.Scenario.RateLimit), cfg.Scenario.RateLimit)
	}

	var store *storage.Storage
	if cfg.Storage.DataDir != "" {
		store, err = storage.NewStorage(cfg.Storage.DataDir)
		if err != nil {
			return nil, fmt.Errorf("failed to create storage: %w", err)
		}
	}

	var autoTuner *autotune.AutoTuner
	if cfg.AutoTune.Enabled {
		autoTuner = autotune.NewAutoTuner(cfg.AutoTune)
	}

	runID := generateRunID()

	return &BenchmarkEngine{
		cfg:         cfg,
		dbDriver:    dbDriver,
		scenario:    gen,
		exporter:    exporter,
		rateLimiter: limiter,
		store:       store,
		autoTuner:   autoTuner,
		runID:       runID,
	}, nil
}

func (e *BenchmarkEngine) GetRunID() string {
	return e.runID
}

func (e *BenchmarkEngine) GetStorage() *storage.Storage {
	return e.store
}

func (e *BenchmarkEngine) SetRunID(runID string) {
	e.runID = runID
}

func (e *BenchmarkEngine) Prepare(ctx context.Context) error {
	log.Printf("Connecting to %s database at %s:%d...", e.cfg.Database.Type, e.cfg.Database.Host, e.cfg.Database.Port)
	if err := e.dbDriver.Connect(ctx); err != nil {
		return fmt.Errorf("failed to connect to database: %w", err)
	}
	log.Println("Database connection established")

	log.Printf("Initializing schema with %d records...", e.cfg.Scenario.TotalRecords)
	if err := e.dbDriver.InitSchema(ctx, e.cfg.Scenario.TotalRecords); err != nil {
		return fmt.Errorf("failed to initialize schema: %w", err)
	}
	log.Println("Schema initialized successfully")

	if err := e.exporter.Start(ctx); err != nil {
		return fmt.Errorf("failed to start metrics exporter: %w", err)
	}
	log.Printf("Metrics server started on port %d, path: %s", e.cfg.Metrics.PrometheusPort, e.cfg.Metrics.PrometheusPath)

	return nil
}

func (e *BenchmarkEngine) ResumeFromSnapshot(ctx context.Context, runID string) error {
	if e.store == nil {
		return fmt.Errorf("storage not configured, cannot resume")
	}

	snap, err := e.store.GetLatestSnapshot(ctx, runID)
	if err != nil {
		return fmt.Errorf("failed to get snapshot: %w", err)
	}
	if snap == nil {
		return fmt.Errorf("no snapshot found for run %s", runID)
	}

	var restoredCfg config.Config
	if err := json.Unmarshal([]byte(snap.ConfigJSON), &restoredCfg); err != nil {
		return fmt.Errorf("failed to unmarshal config from snapshot: %w", err)
	}

	var restoredMetrics metrics.Snapshot
	if err := json.Unmarshal([]byte(snap.MetricsJSON), &restoredMetrics); err != nil {
		return fmt.Errorf("failed to unmarshal metrics from snapshot: %w", err)
	}

	e.cfg = restoredCfg
	e.runID = runID
	e.checkpointNum = snap.CheckpointNum

	existingMetrics := e.exporter.GetMetrics()
	existingMetrics.RestoreFromSnapshot(restoredMetrics)

	log.Printf("Resumed run %s from checkpoint %d (elapsed: %.1fs, concurrency: %d)",
		runID, snap.CheckpointNum, snap.ElapsedSec, snap.Concurrency)

	return nil
}

func (e *BenchmarkEngine) Run(ctx context.Context) error {
	duration := e.cfg.Scenario.Duration
	if e.cfg.AutoTune.Enabled {
		duration = 24 * time.Hour
	}

	ctx, cancel := context.WithTimeout(ctx, duration)
	e.cancelFunc = cancel
	defer cancel()

	e.startTime = time.Now()
	e.lastOpsTime = e.startTime

	if e.store != nil {
		if err := e.createRunRecord(ctx); err != nil {
			log.Printf("Warning: failed to create run record: %v", err)
		}
	}

	e.printConfig()

	workerCtx, workerCancel := context.WithCancel(ctx)
	defer workerCancel()

	results := make(chan struct{}, e.cfg.Scenario.Concurrency*2)

	go e.reportProgress(ctx, results)
	if e.store != nil && e.cfg.Storage.TimeSeriesInterval > 0 {
		go e.recordTimeSeries(ctx)
	}
	if e.store != nil && e.cfg.Storage.SnapshotInterval > 0 {
		go e.recordSnapshots(ctx)
	}

	if e.cfg.AutoTune.Enabled {
		go e.runAutoTune(ctx, workerCtx, results)
		e.startWorkers(workerCtx, e.autoTuner.CurrentConcurrency(), results)
	} else if e.cfg.Scenario.GradualStartup {
		go e.gradualStartup(workerCtx, results)
		initialWorkers := int(float64(e.cfg.Scenario.Concurrency) * e.cfg.Scenario.GradualStartupStep)
		if initialWorkers < 1 {
			initialWorkers = 1
		}
		e.startWorkers(workerCtx, initialWorkers, results)
		log.Printf("Started initial %d workers", initialWorkers)
	} else {
		e.startWorkers(workerCtx, e.cfg.Scenario.Concurrency, results)
	}

	e.wg.Wait()
	close(results)

	log.Println("Benchmark completed")
	finalSnap := e.exporter.GetSnapshot()
	log.Println(finalSnap.PrettyPrint())

	if e.store != nil {
		if err := e.store.CompleteRun(ctx, e.runID, finalSnap); err != nil {
			log.Printf("Warning: failed to complete run record: %v", err)
		}
	}

	if e.autoTuner != nil && e.autoTuner.PeakFound() {
		log.Printf("========================================")
		log.Printf("Performance拐点检测结果:")
		log.Printf("  峰值QPS:     %.2f ops/sec", e.autoTuner.PeakQPS())
		log.Printf("  拐点延迟P99: %.2f ms", e.autoTuner.PeakLatency())
		log.Printf("  推荐并发数:  %d", e.autoTuner.CurrentConcurrency())
		log.Printf("========================================")
	}

	return nil
}

func (e *BenchmarkEngine) createRunRecord(ctx context.Context) error {
	run := &storage.BenchmarkRun{
		RunID:            e.runID,
		Name:             e.cfg.Scenario.Name,
		DatabaseType:     string(e.cfg.Database.Type),
		DatabaseHost:     e.cfg.Database.Host,
		DatabasePort:     e.cfg.Database.Port,
		DatabaseName:     e.cfg.Database.Database,
		StartTime:        e.startTime,
		TargetConcurrency: e.cfg.Scenario.Concurrency,
		ReadRatio:        e.cfg.Scenario.ReadRatio,
		WriteRatio:       e.cfg.Scenario.WriteRatio,
		HotspotPct:       e.cfg.Scenario.HotspotPercentage,
		HotspotSkew:      e.cfg.Scenario.HotspotSkew,
		TotalRecords:     e.cfg.Scenario.TotalRecords,
		Status:           "running",
	}
	return e.store.CreateRun(ctx, run)
}

func (e *BenchmarkEngine) printConfig() {
	log.Printf("Starting benchmark for %s with target %d workers, duration: %s",
		e.cfg.Scenario.Name, e.cfg.Scenario.Concurrency, e.cfg.Scenario.Duration)
	log.Printf("Scenario: read_ratio=%.2f, write_ratio=%.2f, hotspot=%d%% of data with %.0f%% access ratio",
		e.cfg.Scenario.ReadRatio, e.cfg.Scenario.WriteRatio,
		int(e.cfg.Scenario.HotspotPercentage), e.cfg.Scenario.HotspotAccessRatio*100)
	log.Printf("Hotspot distribution: %s, skew=%.2f",
		e.cfg.Scenario.HotspotDistribution, e.cfg.Scenario.HotspotSkew)
	if e.cfg.Scenario.RateLimit > 0 {
		log.Printf("Rate limit: %d ops/sec", e.cfg.Scenario.RateLimit)
	}
	if e.cfg.Scenario.GradualStartup {
		log.Printf("Gradual startup: enabled, +%.0f%% every %s",
			e.cfg.Scenario.GradualStartupStep*100, e.cfg.Scenario.GradualStartupInterval)
	}
	if e.cfg.AutoTune.Enabled {
		log.Printf("AutoTune: enabled, mode=%s, target P99=%.2fms, concurrency range [%d-%d]",
			e.cfg.AutoTune.Mode, e.cfg.AutoTune.TargetLatencyP99,
			e.cfg.AutoTune.MinConcurrency, e.cfg.AutoTune.MaxConcurrency)
	}
	if e.store != nil {
		log.Printf("Storage: enabled, data_dir=%s, run_id=%s", e.cfg.Storage.DataDir, e.runID)
	}
}

func (e *BenchmarkEngine) SetConcurrency(target int) {
	e.workerMu.Lock()
	defer e.workerMu.Unlock()

	current := len(e.workerCancel)
	if target == current {
		return
	}

	if target > current {
		log.Printf("[AutoTune] Scaling up: %d → %d workers", current, target)
		for i := current; i < target; i++ {
			ctx := context.Background()
			wCtx, wCancel := context.WithCancel(ctx)
			e.workerCancel = append(e.workerCancel, wCancel)
			e.wg.Add(1)
			go e.worker(wCtx, i, nil)
		}
	} else {
		log.Printf("[AutoTune] Scaling down: %d → %d workers", current, target)
		for i := current - 1; i >= target; i-- {
			if i < len(e.workerCancel) && e.workerCancel[i] != nil {
				e.workerCancel[i]()
			}
		}
		e.workerCancel = e.workerCancel[:target]
	}

	e.activeWorkers = int32(target)
	e.exporter.SetActiveWorkers(target)
}

func (e *BenchmarkEngine) startWorkers(ctx context.Context, count int, results chan<- struct{}) {
	e.workerMu.Lock()
	defer e.workerMu.Unlock()

	target := e.cfg.Scenario.Concurrency
	if e.autoTuner != nil {
		target = e.autoTuner.CurrentConcurrency()
	}

	current := len(e.workerCancel)
	for i := 0; i < count && current < target; i++ {
		workerID := current
		wCtx, wCancel := context.WithCancel(ctx)
		e.workerCancel = append(e.workerCancel, wCancel)
		e.wg.Add(1)
		go e.worker(wCtx, workerID, results)
		current++
	}
	e.activeWorkers = int32(current)
	e.exporter.SetActiveWorkers(current)
}

func (e *BenchmarkEngine) stopWorkers() {
	e.workerMu.Lock()
	defer e.workerMu.Unlock()

	for _, cancel := range e.workerCancel {
		cancel()
	}
}

func (e *BenchmarkEngine) gradualStartup(ctx context.Context, results chan<- struct{}) {
	ticker := time.NewTicker(e.cfg.Scenario.GradualStartupInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			e.workerMu.Lock()
			current := len(e.workerCancel)
			target := e.cfg.Scenario.Concurrency
			e.workerMu.Unlock()

			if current >= target {
				return
			}

			addCount := int(float64(target) * e.cfg.Scenario.GradualStartupStep)
			if addCount < 1 {
				addCount = 1
			}

			remaining := target - current
			if addCount > remaining {
				addCount = remaining
			}

			if addCount > 0 {
				e.startWorkers(ctx, addCount, results)
				log.Printf("Gradual startup: added %d workers, total active: %d/%d",
					addCount, current+addCount, target)
			}
		}
	}
}

func (e *BenchmarkEngine) runAutoTune(ctx context.Context, workerCtx context.Context, results chan<- struct{}) {
	if e.autoTuner == nil {
		return
	}

	ticker := time.NewTicker(e.cfg.AutoTune.AdjustInterval / 2)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			snap := e.exporter.GetSnapshot()
			newConcurrency, shouldStop, _ := e.autoTuner.Adjust(snap)

			current := int(e.activeWorkers)
			if newConcurrency != current {
				e.SetConcurrency(newConcurrency)
			}

			if shouldStop {
				log.Printf("[AutoTune] Peak performance detected, stopping benchmark")
				e.cancelFunc()
				return
			}
		}
	}
}

func (e *BenchmarkEngine) worker(ctx context.Context, id int, results chan<- struct{}) {
	defer e.wg.Done()

	for {
		select {
		case <-ctx.Done():
			return
		default:
			if e.rateLimiter != nil {
				if err := e.rateLimiter.Wait(ctx); err != nil {
					if ctx.Err() != nil {
						return
					}
					continue
				}
			}

			op := e.scenario.Next()
			var result driver.Result

			switch op.Type {
			case driver.OpRead:
				result = e.dbDriver.Read(ctx, op.Key)
			case driver.OpWrite:
				result = e.dbDriver.Write(ctx, op.Key, op.Value)
			}

			e.exporter.RecordResult(result, op.IsHotspot)
			if results != nil {
				select {
				case results <- struct{}{}:
				default:
				}
			}
		}
	}
}

func (e *BenchmarkEngine) reportProgress(ctx context.Context, results <-chan struct{}) {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	var lastOps uint64
	lastTime := time.Now()

	for {
		select {
		case <-ctx.Done():
			snap := e.exporter.GetSnapshot()
			log.Printf("Final: %s", snap.String())
			return
		case <-ticker.C:
			snap := e.exporter.GetSnapshot()
			elapsed := time.Since(lastTime).Seconds()
			instQPS := float64(snap.TotalOps-lastOps) / elapsed
			lastOps = snap.TotalOps
			lastTime = time.Now()

			workers := int(e.activeWorkers)
			autoTuneInfo := ""
			if e.autoTuner != nil {
				autoTuneInfo = fmt.Sprintf(" | Workers: %d", workers)
			}

			log.Printf("[%5.1fs] Inst QPS: %8.2f | Avg QPS: %8.2f | TPS: %8.2f | Err: %5.2f%% | P50: %6.2fms | P99: %6.2fms | P999: %7.2fms | Total: %d%s",
				snap.Duration.Seconds(), instQPS, snap.QPS, snap.TPS, snap.ErrorRate*100,
				snap.P50, snap.P99, snap.P999, snap.TotalOps, autoTuneInfo)
		}
	}
}

func (e *BenchmarkEngine) recordTimeSeries(ctx context.Context) {
	if e.store == nil {
		return
	}

	interval := e.cfg.Storage.TimeSeriesInterval
	if interval <= 0 {
		interval = 5 * time.Second
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			snap := e.exporter.GetSnapshot()
			now := time.Now()
			elapsed := now.Sub(e.lastOpsTime).Seconds()
			instQPS := float64(snap.TotalOps-e.lastOps) / elapsed
			e.lastOps = snap.TotalOps
			e.lastOpsTime = now

			point := storage.TimeSeriesPoint{
				Timestamp:   now,
				ElapsedSec:  now.Sub(e.startTime).Seconds(),
				Concurrency: int(e.activeWorkers),
				QPS:         snap.QPS,
				TPS:         snap.TPS,
				ErrorRate:   snap.ErrorRate,
				P50:         snap.P50,
				P99:         snap.P99,
				P999:        snap.P999,
				TotalOps:    snap.TotalOps,
				InstantQPS:  instQPS,
			}

			if err := e.store.InsertTimeSeries(ctx, e.runID, point); err != nil {
				log.Printf("Warning: failed to insert timeseries: %v", err)
			}
		}
	}
}

func (e *BenchmarkEngine) recordSnapshots(ctx context.Context) {
	if e.store == nil {
		return
	}

	interval := e.cfg.Storage.SnapshotInterval
	if interval <= 0 {
		interval = 30 * time.Second
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			e.checkpointMu.Lock()
			e.checkpointNum++
			checkpointNum := e.checkpointNum
			e.checkpointMu.Unlock()

			snap := e.exporter.GetSnapshot()
			elapsed := time.Since(e.startTime).Seconds()

			if err := e.store.SaveSnapshot(
				ctx,
				e.runID,
				elapsed,
				int(e.activeWorkers),
				int(e.activeWorkers),
				e.cfg,
				snap,
				checkpointNum,
			); err != nil {
				log.Printf("Warning: failed to save snapshot: %v", err)
			} else {
				log.Printf("Checkpoint %d saved (elapsed: %.1fs, ops: %d)",
					checkpointNum, elapsed, snap.TotalOps)
			}
		}
	}
}

func (e *BenchmarkEngine) Shutdown(ctx context.Context) error {
	log.Println("Shutting down benchmark engine...")

	if e.cancelFunc != nil {
		e.cancelFunc()
	}

	if e.store != nil {
		if err := e.store.UpdateRunStatus(ctx, e.runID, "interrupted"); err != nil {
			log.Printf("Warning: failed to update run status: %v", err)
		}
	}

	if e.exporter != nil {
		if err := e.exporter.Shutdown(ctx); err != nil {
			log.Printf("Error shutting down metrics exporter: %v", err)
		}
	}

	if e.dbDriver != nil {
		if err := e.dbDriver.Close(ctx); err != nil {
			log.Printf("Error closing database connection: %v", err)
		}
	}

	if e.store != nil {
		if err := e.store.Close(); err != nil {
			log.Printf("Error closing storage: %v", err)
		}
	}

	e.scenario.Close()
	log.Println("Shutdown complete")
	return nil
}

func (e *BenchmarkEngine) GetMetrics() *metrics.Metrics {
	return e.exporter.GetMetrics()
}

func (e *BenchmarkEngine) ForceCheckpoint(ctx context.Context) error {
	if e.store == nil {
		return fmt.Errorf("storage not configured")
	}

	e.checkpointMu.Lock()
	e.checkpointNum++
	checkpointNum := e.checkpointNum
	e.checkpointMu.Unlock()

	snap := e.exporter.GetSnapshot()
	elapsed := time.Since(e.startTime).Seconds()

	return e.store.SaveSnapshot(
		ctx,
		e.runID,
		elapsed,
		int(e.activeWorkers),
		int(e.activeWorkers),
		e.cfg,
		snap,
		checkpointNum,
	)
}
