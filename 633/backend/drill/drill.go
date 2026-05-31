package drill

import (
	"context"
	"math/rand"
	"sync"
	"sync/atomic"
	"time"

	"clickhouse-rate-limiter/config"
)

type DrillConfig struct {
	Name            string
	Duration        time.Duration
	Concurrency     int
	QueriesPerSec   int
	QueryTemplates  []string
	PriorityWeights map[string]int
	ResourceGroup   string
	UserIDs         []string
	SlowQueryRatio  float64
	ErrorRatio      float64
}

type DrillMetrics struct {
	TotalQueries     int64
	SuccessQueries   int64
	FailedQueries    int64
	RejectedQueries  int64
	TimedOutQueries  int64
	TotalDurationMs  int64
	MinDurationMs    int64
	MaxDurationMs    int64
	LatencyBuckets   map[int]int64
	StartTime        time.Time
	EndTime          time.Time
	mu               sync.RWMutex
}

type DrillReport struct {
	Config     DrillConfig
	Metrics    DrillMetrics
	Throughput float64
	SuccessRate float64
	RejectRate  float64
	AvgLatency  float64
	P95Latency  float64
	P99Latency  float64
}

type QueryExecutor func(context.Context, QueryRequest) (*QueryResponse, error)

type QueryRequest struct {
	UserID        string
	Query         string
	Priority      string
	ResourceGroup string
}

type QueryResponse struct {
	RequestID  string
	Status     string
	Error      string
}

type DrillManager struct {
	activeDrill   *RunningDrill
	mu            sync.Mutex
	queryExecutor QueryExecutor
}

type RunningDrill struct {
	Config     DrillConfig
	Metrics    *DrillMetrics
	CancelFunc context.CancelFunc
	Running    bool
}

func NewDrillManager(executor QueryExecutor) *DrillManager {
	return &DrillManager{
		queryExecutor: executor,
	}
}

func (dm *DrillManager) StartDrill(cfg DrillConfig) (*DrillMetrics, error) {
	dm.mu.Lock()
	defer dm.mu.Unlock()

	if dm.activeDrill != nil && dm.activeDrill.Running {
		return nil, &DrillInProgressError{}
	}

	ctx, cancel := context.WithTimeout(context.Background(), cfg.Duration)

	metrics := &DrillMetrics{
		StartTime:      time.Now(),
		LatencyBuckets: make(map[int]int64),
	}

	drill := &RunningDrill{
		Config:     cfg,
		Metrics:    metrics,
		CancelFunc: cancel,
		Running:    true,
	}
	dm.activeDrill = drill

	go dm.runDrill(ctx, cfg, metrics)

	go func() {
		<-ctx.Done()
		metrics.mu.Lock()
		metrics.EndTime = time.Now()
		metrics.mu.Unlock()
		drill.Running = false
	}()

	return metrics, nil
}

func (dm *DrillManager) runDrill(ctx context.Context, cfg DrillConfig, metrics *DrillMetrics) {
	var wg sync.WaitGroup
	sem := make(chan struct{}, cfg.Concurrency)
	ticker := time.NewTicker(time.Second / time.Duration(cfg.QueriesPerSec))
	defer ticker.Stop()

	randGen := rand.New(rand.NewSource(time.Now().UnixNano()))

	for {
		select {
		case <-ctx.Done():
			wg.Wait()
			return
		case <-ticker.C:
			select {
			case sem <- struct{}{}:
				wg.Add(1)
				go func() {
					defer wg.Done()
					defer func() { <-sem }()

					dm.simulateQuery(ctx, cfg, metrics, randGen)
				}()
			default:
			}
		}
	}
}

func (dm *DrillManager) simulateQuery(ctx context.Context, cfg DrillConfig, metrics *DrillMetrics, r *rand.Rand) {
	query := cfg.QueryTemplates[r.Intn(len(cfg.QueryTemplates))]
	priority := selectPriority(cfg.PriorityWeights, r)
	userID := cfg.UserIDs[r.Intn(len(cfg.UserIDs))]

	if r.Float64() < cfg.SlowQueryRatio {
		query = "SELECT sleep(1)"
	}

	if r.Float64() < cfg.ErrorRatio {
		query = "SELECT * FROM non_existent_table"
	}

	atomic.AddInt64(&metrics.TotalQueries, 1)

	req := QueryRequest{
		UserID:        userID,
		Query:         query,
		Priority:      priority,
		ResourceGroup: cfg.ResourceGroup,
	}

	startTime := time.Now()

	resultChan := make(chan *QueryResponse, 1)

	go func() {
		resp, _ := dm.queryExecutor(ctx, req)
		resultChan <- resp
	}()

	select {
	case resp := <-resultChan:
		duration := time.Since(startTime).Milliseconds()

		metrics.mu.Lock()
		metrics.TotalDurationMs += duration
		if duration < metrics.MinDurationMs || metrics.MinDurationMs == 0 {
			metrics.MinDurationMs = duration
		}
		if duration > metrics.MaxDurationMs {
			metrics.MaxDurationMs = duration
		}
		bucket := int(duration / 100) * 100
		metrics.LatencyBuckets[bucket]++
		metrics.mu.Unlock()

		switch resp.Status {
		case "completed":
			atomic.AddInt64(&metrics.SuccessQueries, 1)
		case "failed":
			atomic.AddInt64(&metrics.FailedQueries, 1)
		case "rejected":
			atomic.AddInt64(&metrics.RejectedQueries, 1)
		case "timeout":
			atomic.AddInt64(&metrics.TimedOutQueries, 1)
		}

	case <-ctx.Done():
		atomic.AddInt64(&metrics.TimedOutQueries, 1)
	}
}

func (dm *DrillManager) StopDrill() bool {
	dm.mu.Lock()
	defer dm.mu.Unlock()

	if dm.activeDrill == nil || !dm.activeDrill.Running {
		return false
	}

	dm.activeDrill.CancelFunc()
	dm.activeDrill.Running = false
	return true
}

func (dm *DrillManager) GetStatus() map[string]interface{} {
	dm.mu.Lock()
	defer dm.mu.Unlock()

	if dm.activeDrill == nil {
		return map[string]interface{}{
			"running": false,
		}
	}

	drill := dm.activeDrill
	metrics := drill.Metrics

	metrics.mu.RLock()
	defer metrics.mu.RUnlock()

	status := map[string]interface{}{
		"running": drill.Running,
		"name":    drill.Config.Name,
		"metrics": map[string]interface{}{
			"total_queries":     metrics.TotalQueries,
			"success_queries":   metrics.SuccessQueries,
			"failed_queries":    metrics.FailedQueries,
			"rejected_queries":  metrics.RejectedQueries,
			"timed_out_queries": metrics.TimedOutQueries,
			"start_time":        metrics.StartTime,
			"elapsed_seconds":   time.Since(metrics.StartTime).Seconds(),
			"duration_seconds":  drill.Config.Duration.Seconds(),
		},
	}

	if metrics.TotalQueries > 0 {
		elapsed := time.Since(metrics.StartTime).Seconds()
		if elapsed > 0 {
			status["metrics"].(map[string]interface{})["throughput"] = float64(metrics.TotalQueries) / elapsed
		}
		status["metrics"].(map[string]interface{})["avg_latency_ms"] = float64(metrics.TotalDurationMs) / float64(metrics.TotalQueries)
	}

	return status
}

func (dm *DrillManager) GetReport() *DrillReport {
	dm.mu.Lock()
	defer dm.mu.Unlock()

	if dm.activeDrill == nil {
		return nil
	}

	metrics := dm.activeDrill.Metrics
	metrics.mu.RLock()
	defer metrics.mu.RUnlock()

	if metrics.TotalQueries == 0 {
		return &DrillReport{
			Config:  dm.activeDrill.Config,
			Metrics: *metrics,
		}
	}

	elapsed := metrics.EndTime.Sub(metrics.StartTime).Seconds()
	if elapsed <= 0 {
		elapsed = time.Since(metrics.StartTime).Seconds()
	}

	report := &DrillReport{
		Config:     dm.activeDrill.Config,
		Metrics:    *metrics,
		Throughput: float64(metrics.TotalQueries) / elapsed,
		SuccessRate: float64(metrics.SuccessQueries) / float64(metrics.TotalQueries) * 100,
		RejectRate:  float64(metrics.RejectedQueries) / float64(metrics.TotalQueries) * 100,
		AvgLatency:  float64(metrics.TotalDurationMs) / float64(metrics.TotalQueries),
	}

	total := int64(0)
	p95Target := int64(float64(metrics.TotalQueries) * 0.95)
	p99Target := int64(float64(metrics.TotalQueries) * 0.99)

	for bucket := 0; bucket <= int(metrics.MaxDurationMs)+100; bucket += 100 {
		count := metrics.LatencyBuckets[bucket]
		total += count
		if report.P95Latency == 0 && total >= p95Target {
			report.P95Latency = float64(bucket)
		}
		if report.P99Latency == 0 && total >= p99Target {
			report.P99Latency = float64(bucket)
		}
	}

	return report
}

func (dm *DrillManager) GetDefaultConfig() DrillConfig {
	return DrillConfig{
		Name:          "default_drill",
		Duration:      60 * time.Second,
		Concurrency:   50,
		QueriesPerSec: 100,
		QueryTemplates: []string{
			"SELECT 1",
			"SELECT count(*) FROM system.tables",
			"SELECT * FROM system.query_log LIMIT 100",
			"SELECT user_id, count(*) FROM system.query_log GROUP BY user_id LIMIT 10",
		},
		PriorityWeights: map[string]int{
			"high":   20,
			"medium": 60,
			"low":    20,
		},
		ResourceGroup: "default",
		UserIDs: []string{
			"user_001", "user_002", "user_003", "user_004", "user_005",
		},
		SlowQueryRatio: 0.05,
		ErrorRatio:      0.02,
	}
}

func selectPriority(weights map[string]int, r *rand.Rand) string {
	total := 0
	for _, w := range weights {
		total += w
	}
	if total == 0 {
		return "medium"
	}
	n := r.Intn(total)
	for p, w := range weights {
		n -= w
		if n < 0 {
			return p
		}
	}
	return "medium"
}

type DrillInProgressError struct{}

func (e *DrillInProgressError) Error() string {
	return "drill already in progress"
}
