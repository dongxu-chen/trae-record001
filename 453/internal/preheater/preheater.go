package preheater

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"

	"heatcache/internal/adaptive"
	"heatcache/internal/binlog"
	"heatcache/internal/cache"
	"heatcache/internal/cluster"
	"heatcache/internal/connector"
	"heatcache/internal/incremental"
	"heatcache/internal/notifier"
	"heatcache/internal/parser"
	"heatcache/internal/planner"
	"heatcache/internal/prediction"
	"heatcache/internal/stats"
)

type PreheatJob struct {
	QueryHash    string
	Query        string
	Priority     float64
	Tables       []string
	DbConfigName string
	Retries      int
	RefreshType  string
}

type PreheatResult struct {
	Job      *PreheatJob
	Success  bool
	Duration time.Duration
	Error    error
	Cached   bool
	IsRefresh bool
}

type PreheaterConfig struct {
	WorkerCount      int
	BatchSize        int
	RetryCount       int
	PreheatInterval  time.Duration
	AnalysisInterval time.Duration
	TopN             int
	QueryTimeout     time.Duration
	CacheTTL         time.Duration
	EnableIncremental bool
	EnableBinlog     bool
	EnableAdaptiveInterval bool
	EnableHitRatePrediction bool
	IncrementalInterval time.Duration
	DirtyLimitPerCycle int
	TargetHitRate    float64
	MaxMemoryBytes   int64
}

type Preheater struct {
	config        PreheaterConfig
	parser        *parser.SQLParser
	predictor     *stats.HotQueryPredictor
	analyzer      *cluster.ClusterAnalyzer
	cache         *cache.RedisCache
	connectors    map[string]connector.Connector
	incrementalMgr *incremental.IncrementalManager
	notifier      *notifier.DataChangeNotifier
	hitRatePredictor *prediction.HitRatePredictor
	adaptiveCtrl  *adaptive.AdaptiveController
	cachePlanner  *planner.CachePlanner
	binlogConfigs map[string]interface{}

	jobs   chan *PreheatJob
	results chan *PreheatResult

	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
	mu     sync.Mutex
}

func NewPreheater(
	config PreheaterConfig,
	cacheLayer *cache.RedisCache,
	connectors map[string]connector.Connector,
) *Preheater {
	if config.WorkerCount <= 0 {
		config.WorkerCount = 4
	}
	if config.BatchSize <= 0 {
		config.BatchSize = 50
	}
	if config.RetryCount <= 0 {
		config.RetryCount = 2
	}
	if config.PreheatInterval <= 0 {
		config.PreheatInterval = 5 * time.Minute
	}
	if config.AnalysisInterval <= 0 {
		config.AnalysisInterval = 15 * time.Minute
	}
	if config.TopN <= 0 {
		config.TopN = 50
	}
	if config.QueryTimeout <= 0 {
		config.QueryTimeout = 10 * time.Second
	}
	if config.CacheTTL <= 0 {
		config.CacheTTL = 30 * time.Minute
	}
	if config.IncrementalInterval <= 0 {
		config.IncrementalInterval = 30 * time.Second
	}
	if config.DirtyLimitPerCycle <= 0 {
		config.DirtyLimitPerCycle = 20
	}
	if config.TargetHitRate <= 0 {
		config.TargetHitRate = 0.8
	}

	incManager := incremental.NewIncrementalManager(cacheLayer, 1000)
	dcn := notifier.NewDataChangeNotifier(cacheLayer, incManager, 10000)
	hitPredictor := prediction.NewHitRatePredictor(24 * time.Hour)
	adaptiveCtrl := adaptive.NewAdaptiveController(adaptive.DefaultAdaptiveConfig())
	cachePlanner := planner.NewCachePlanner(config.MaxMemoryBytes)

	return &Preheater{
		config:         config,
		parser:         parser.NewSQLParser(),
		predictor:      stats.NewHotQueryPredictor(0.95, time.Hour),
		analyzer:       cluster.NewClusterAnalyzer(5),
		cache:          cacheLayer,
		connectors:     connectors,
		incrementalMgr: incManager,
		notifier:       dcn,
		hitRatePredictor: hitPredictor,
		adaptiveCtrl:   adaptiveCtrl,
		cachePlanner:   cachePlanner,
		jobs:           make(chan *PreheatJob, config.BatchSize*2),
		results:        make(chan *PreheatResult, config.BatchSize*2),
	}
}

func (p *Preheater) AddMySQLBinlog(name string, config binlog.BinlogListenerConfig) error {
	return p.notifier.AddMySQLListener(name, config)
}

func (p *Preheater) AddPGBinlog(name string, config binlog.PGReplicationConfig) {
	p.notifier.AddPGListener(name, config)
}

func (p *Preheater) AddBinlogHandler(handler func(*binlog.BinlogEvent)) {
	p.notifier.AddProcessor(handler)
}

func (p *Preheater) Start(ctx context.Context) {
	p.ctx, p.cancel = context.WithCancel(ctx)

	p.incrementalMgr.Start(p.ctx)

	if p.config.EnableBinlog {
		p.notifier.Start(p.ctx)
	}

	for i := 0; i < p.config.WorkerCount; i++ {
		p.wg.Add(1)
		go p.worker(i)
	}

	p.wg.Add(1)
	go p.resultCollector()

	p.wg.Add(1)
	go p.scheduler()

	if p.config.EnableIncremental {
		p.wg.Add(1)
		go p.incrementalScheduler()
	}

	log.Println("[preheater] started with config:",
		"workers=", p.config.WorkerCount,
		"incremental=", p.config.EnableIncremental,
		"binlog=", p.config.EnableBinlog)
}

func (p *Preheater) Stop() {
	if p.cancel != nil {
		p.cancel()
	}

	p.notifier.Stop()

	close(p.jobs)
	close(p.results)
	p.wg.Wait()

	log.Println("[preheater] stopped")
}

func (p *Preheater) worker(id int) {
	defer p.wg.Done()

	for job := range p.jobs {
		result := p.executeJob(job)
		select {
		case p.results <- result:
		case <-p.ctx.Done():
			return
		}
	}
}

func (p *Preheater) executeJob(job *PreheatJob) *PreheatResult {
	start := time.Now()

	conn, ok := p.connectors[job.DbConfigName]
	if !ok {
		return &PreheatResult{
			Job:      job,
			Success:  false,
			Duration: time.Since(start),
			Error:    fmt.Errorf("connector not found: %s", job.DbConfigName),
		}
	}

	exists, err := p.cache.Exists(p.ctx, job.QueryHash)
	if err == nil && exists && job.RefreshType != "incremental" && job.RefreshType != "delta" {
		return &PreheatResult{
			Job:      job,
			Success:  true,
			Duration: time.Since(start),
			Cached:   true,
		}
	}

	queryCtx, cancel := context.WithTimeout(p.ctx, p.config.QueryTimeout)
	defer cancel()

	result, err := conn.ExecuteQuery(queryCtx, job.Query)
	if err != nil {
		if job.Retries < p.config.RetryCount {
			job.Retries++
			return p.executeJob(job)
		}
		return &PreheatResult{
			Job:      job,
			Success:  false,
			Duration: time.Since(start),
			Error:    fmt.Errorf("query execution failed: %w", err),
		}
	}

	jsonData, err := connector.QueryResultToJSON(result)
	if err != nil {
		return &PreheatResult{
			Job:      job,
			Success:  false,
			Duration: time.Since(start),
			Error:    fmt.Errorf("result serialization failed: %w", err),
		}
	}

	hashResult := p.incrementalMgr.ComputeDataHash(result.Rows)

	cacheEntry := &cache.CacheEntry{
		Value:     jsonData,
		Tables:    job.Tables,
		QueryHash: job.QueryHash,
		TTL:       p.config.CacheTTL,
		Size:      int64(len(jsonData)),
	}

	if err := p.cache.Set(p.ctx, cacheEntry); err != nil {
		return &PreheatResult{
			Job:      job,
			Success:  false,
			Duration: time.Since(start),
			Error:    fmt.Errorf("cache set failed: %w", err),
		}
	}

	p.incrementalMgr.MarkRefreshed(job.QueryHash, hashResult.Hash, hashResult.RowCount)

	return &PreheatResult{
		Job:       job,
		Success:   true,
		Duration:  time.Since(start),
		Cached:    false,
		IsRefresh: job.RefreshType != "",
	}
}

func (p *Preheater) resultCollector() {
	defer p.wg.Done()

	for result := range p.results {
		if result.Success {
			if result.Cached {
				log.Printf("[preheater] key=%s already cached, skipped (%v)",
					result.Job.QueryHash, result.Duration)
			} else if result.IsRefresh {
				log.Printf("[preheater] key=%s refreshed successfully (%v, type=%s)",
					result.Job.QueryHash, result.Duration, result.Job.RefreshType)
			} else {
				log.Printf("[preheater] key=%s preheated successfully (%v)",
					result.Job.QueryHash, result.Duration)
			}
		} else {
			log.Printf("[preheater] key=%s failed: %v",
				result.Job.QueryHash, result.Error)
		}
	}
}

func (p *Preheater) scheduler() {
	defer p.wg.Done()

	p.runAnalysis()

	preheatInterval := p.config.PreheatInterval
	if p.config.EnableAdaptiveInterval {
		preheatInterval = p.adaptiveCtrl.GetCurrentInterval()
	}

	ticker := time.NewTicker(preheatInterval)
	analysisTicker := time.NewTicker(p.config.AnalysisInterval)
	adaptiveTicker := time.NewTicker(time.Minute)
	defer ticker.Stop()
	defer analysisTicker.Stop()
	defer adaptiveTicker.Stop()

	for {
		select {
		case <-ticker.C:
			p.runPreheatCycle()
			if p.config.EnableAdaptiveInterval {
				newInterval := p.runAdaptiveAdjustment()
				if newInterval != preheatInterval {
					preheatInterval = newInterval
					ticker.Reset(preheatInterval)
					log.Printf("[preheater] adaptive interval adjusted to %v", preheatInterval)
				}
			}
		case <-analysisTicker.C:
			p.runAnalysis()
		case <-adaptiveTicker.C:
			if p.config.EnableAdaptiveInterval {
				p.runAdaptiveAdjustment()
			}
		case <-p.ctx.Done():
			return
		}
	}
}

func (p *Preheater) incrementalScheduler() {
	defer p.wg.Done()

	ticker := time.NewTicker(p.config.IncrementalInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			p.runIncrementalCycle()
		case <-p.ctx.Done():
			return
		}
	}
}

func (p *Preheater) runAnalysis() {
	log.Println("[preheater] starting query pattern analysis...")

	for name, conn := range p.connectors {
		ctx, cancel := context.WithTimeout(p.ctx, 30*time.Second)
		entries, err := conn.FetchQueryStats(ctx)
		cancel()

		if err != nil {
			log.Printf("[preheater] failed to fetch query stats from %s: %v", name, err)
			continue
		}

		for _, entry := range entries {
			parsed, err := p.parser.Parse(entry.Query)
			if err != nil {
				continue
			}

			p.predictor.Record(stats.QueryObservation{
				Fingerprint:  parsed.Pattern.Fingerprint,
				Timestamp:    entry.StartTime,
				Latency:      float64(entry.Duration.Milliseconds()),
				RowsReturned: entry.RowsSent,
			})

			p.incrementalMgr.RegisterQuery(
				parsed.Pattern.Fingerprint,
				entry.Query,
				name,
				parsed.Pattern.Tables,
				0.5,
			)
		}

		log.Printf("[preheater] analyzed %d queries from %s", len(entries), name)
	}

	p.predictor.Prune(72 * time.Hour)
}

func (p *Preheater) runPreheatCycle() {
	log.Println("[preheater] starting preheat cycle...")

	hotQueries := p.predictor.PredictHotQueries(time.Now(), p.config.TopN)
	if len(hotQueries) == 0 {
		log.Println("[preheater] no hot queries identified")
		return
	}

	log.Printf("[preheater] identified %d hot queries", len(hotQueries))

	items := make([]*cluster.QueryClusterItem, 0, len(hotQueries))
	queryMap := make(map[string]*stats.HotQueryResult)

	for i := range hotQueries {
		hq := &hotQueries[i]
		queryMap[hq.Fingerprint] = hq
		vec := make([]float64, 16)
		vec[0] = hq.FrequencyScore
		vec[1] = hq.LatencyScore
		vec[2] = hq.TrendScore
		vec[3] = hq.Score
		vec[4] = float64(hq.CurrentFreq)
		vec[5] = hq.AvgLatency
		vec[6] = hq.P95Latency
		vec[7] = hq.PredictedFreq
		items = append(items, &cluster.QueryClusterItem{
			Vector:     vec,
			Frequency:  hq.CurrentFreq,
			AvgLatency: hq.AvgLatency,
		})

		p.incrementalMgr.RegisterQuery(
			hq.Fingerprint,
			"",
			"",
			nil,
			hq.Score,
		)
	}

	clusters, err := p.analyzer.AnalyzeAndRank(items)
	if err != nil {
		log.Printf("[preheater] clustering failed: %v", err)
		return
	}

	log.Printf("[preheater] formed %d clusters", len(clusters))

	hotItems := p.analyzer.ExtractHotQueries(clusters, p.config.TopN)

	preheatedFps := make(map[string]bool)
	submitted := 0
	for _, item := range hotItems {
		fp := ""
		for k, hq := range queryMap {
			if hq.Score == item.AvgLatency || hq.CurrentFreq == item.Frequency {
				fp = k
				break
			}
		}
		if fp == "" {
			continue
		}
		preheatedFps[fp] = true

		job := &PreheatJob{
			QueryHash: fp,
			Query:     "",
			Priority:  item.AvgLatency*0.6 + float64(item.Frequency)*0.4,
			Tables:    nil,
			Retries:   0,
		}

		select {
		case p.jobs <- job:
			submitted++
		case <-p.ctx.Done():
			return
		default:
			log.Printf("[preheater] job queue full, skipping %s", fp)
		}
	}

	log.Printf("[preheater] submitted %d preheat jobs", submitted)

	if p.config.EnableHitRatePrediction {
		pred := p.hitRatePredictor.Predict(preheatedFps, p.config.TopN)
		log.Printf("[preheater] hit rate prediction: current=%.2f%%, predicted=%.2f%%, improvement=%.2f%%, confidence=%.2f%%",
			pred.CurrentHitRate*100, pred.PredictedHitRate*100, pred.HitRateImprovement*100, pred.Confidence*100)
	}

	p.cache.PerformLRUEviction(p.ctx)
}

func (p *Preheater) runAdaptiveAdjustment() time.Duration {
	queryCount := p.predictor.GetObservationCount()
	newQueryCount := p.predictor.GetPatternCount() / 10
	dirtyCount := p.incrementalMgr.GetDirtyCount()
	currentHitRate := p.hitRatePredictor.GetCurrentHitRate()

	return p.adaptiveCtrl.RecordSample(queryCount, newQueryCount, dirtyCount, currentHitRate)
}

func (p *Preheater) runIncrementalCycle() {
	dirtyCount := p.incrementalMgr.GetDirtyCount()
	if dirtyCount == 0 {
		return
	}

	log.Printf("[preheater] processing %d dirty queries for incremental refresh", dirtyCount)

	dirtyQueries := p.incrementalMgr.GetDirtyQueries(p.config.DirtyLimitPerCycle)

	submitted := 0
	for _, info := range dirtyQueries {
		job := &PreheatJob{
			QueryHash:    info.QueryHash,
			Query:        info.QuerySQL,
			Priority:     info.RefreshPriority,
			Tables:       info.Tables,
			DbConfigName: info.DbConfigName,
			Retries:      0,
			RefreshType:  string(info.RefreshType),
		}

		if job.Query == "" || job.DbConfigName == "" {
			continue
		}

		select {
		case p.jobs <- job:
			submitted++
		case <-p.ctx.Done():
			return
		default:
		}
	}

	if submitted > 0 {
		log.Printf("[preheater] submitted %d incremental refresh jobs", submitted)
	}
}

func (p *Preheater) PreheatQuery(ctx context.Context, dbConfigName, query string) (*PreheatResult, error) {
	parsed, err := p.parser.Parse(query)
	if err != nil {
		return nil, fmt.Errorf("failed to parse query: %w", err)
	}

	job := &PreheatJob{
		QueryHash:    parsed.Pattern.Fingerprint,
		Query:        query,
		Priority:     1.0,
		Tables:       parsed.Pattern.Tables,
		DbConfigName: dbConfigName,
	}

	result := p.executeJob(job)

	p.predictor.Record(stats.QueryObservation{
		Fingerprint:  parsed.Pattern.Fingerprint,
		Timestamp:    time.Now(),
		Latency:      float64(result.Duration.Milliseconds()),
		RowsReturned: 0,
	})

	p.incrementalMgr.RegisterQuery(
		parsed.Pattern.Fingerprint,
		query,
		dbConfigName,
		parsed.Pattern.Tables,
		1.0,
	)

	return result, nil
}

func (p *Preheater) PreheatBatch(ctx context.Context, dbConfigName string, queries []string) ([]*PreheatResult, error) {
	results := make([]*PreheatResult, 0, len(queries))

	for _, q := range queries {
		result, err := p.PreheatQuery(ctx, dbConfigName, q)
		if err != nil {
			log.Printf("[preheater] batch preheat failed for query: %v", err)
			continue
		}
		results = append(results, result)
	}

	return results, nil
}

func (p *Preheater) InvalidateTable(ctx context.Context, table string) error {
	log.Printf("[preheater] invalidating cache for table: %s", table)

	marked := p.incrementalMgr.MarkDirty(table, "manual")
	if marked > 0 {
		log.Printf("[preheater] marked %d queries as dirty", marked)
	}

	return p.cache.InvalidateByTable(ctx, table)
}

func (p *Preheater) GetCacheStats(ctx context.Context) (*cache.CacheStats, error) {
	return p.cache.Stats(ctx)
}

type PreheatReport struct {
	Timestamp      time.Time
	HotQueryCount  int
	ClusterCount   int
	PreheatedCount int
	DirtyQueryCount int
	TotalQueries   int
	BinlogStats    map[string]interface{}
	CacheStats     *cache.CacheStats
	HitRatePrediction *prediction.HitRatePrediction
	AdaptiveMetrics *adaptive.ChangeMetrics
	CachePlan      *planner.CachePlan
}

func (p *Preheater) GenerateReport(ctx context.Context) (*PreheatReport, error) {
	cacheStats, err := p.cache.Stats(ctx)
	if err != nil {
		return nil, err
	}

	hotQueries := p.predictor.PredictHotQueries(time.Now(), p.config.TopN)
	dirtyCount := p.incrementalMgr.GetDirtyCount()
	totalQueries := p.incrementalMgr.GetTotalCount()
	binlogStats := p.notifier.GetStats()

	report := &PreheatReport{
		Timestamp:      time.Now(),
		HotQueryCount:  len(hotQueries),
		DirtyQueryCount: dirtyCount,
		TotalQueries:   totalQueries,
		BinlogStats:    binlogStats,
		CacheStats:     cacheStats,
	}

	if p.config.EnableHitRatePrediction {
		preheatedFps := make(map[string]bool)
		for _, hq := range hotQueries {
			preheatedFps[hq.Fingerprint] = true
		}
		report.HitRatePrediction = p.hitRatePredictor.Predict(preheatedFps, p.config.TopN)
	}

	if p.config.EnableAdaptiveInterval {
		report.AdaptiveMetrics = p.adaptiveCtrl.GetMetrics()
	}

	report.CachePlan = p.cachePlanner.GeneratePlan()

	return report, nil
}

func (p *Preheater) GetHitRatePrediction(topN int) *prediction.HitRatePrediction {
	hotQueries := p.predictor.PredictHotQueries(time.Now(), topN)
	preheatedFps := make(map[string]bool)
	for _, hq := range hotQueries {
		preheatedFps[hq.Fingerprint] = true
	}
	return p.hitRatePredictor.Predict(preheatedFps, topN)
}

func (p *Preheater) GetAdaptiveMetrics() *adaptive.ChangeMetrics {
	return p.adaptiveCtrl.GetMetrics()
}

func (p *Preheater) GenerateCachePlan() *planner.CachePlan {
	return p.cachePlanner.GeneratePlan()
}

func (p *Preheater) GetCurrentInterval() time.Duration {
	return p.adaptiveCtrl.GetCurrentInterval()
}

func (p *Preheater) GetHitRatePredictor() *prediction.HitRatePredictor {
	return p.hitRatePredictor
}

func (p *Preheater) GetAdaptiveController() *adaptive.AdaptiveController {
	return p.adaptiveCtrl
}

func (p *Preheater) GetCachePlanner() *planner.CachePlanner {
	return p.cachePlanner
}

func (p *Preheater) RecordCacheAccess(key string, hit bool, latency float64) {
	p.hitRatePredictor.RecordQuery(key, hit, latency)
	p.cachePlanner.RecordAccess(key, time.Now())
}

func (p *Preheater) GetIncrementalManager() *incremental.IncrementalManager {
	return p.incrementalMgr
}

func (p *Preheater) GetNotifier() *notifier.DataChangeNotifier {
	return p.notifier
}
