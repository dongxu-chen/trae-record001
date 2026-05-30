package monitor

import (
	"context"
	"fmt"
	"log"
	"os"
	"sync"
	"time"

	"slow-query-killer/internal/analyzer"
	"slow-query-killer/internal/auditor"
	"slow-query-killer/internal/config"
	"slow-query-killer/internal/db"
	"slow-query-killer/internal/indexer"
	"slow-query-killer/internal/predictor"
	"slow-query-killer/internal/rules"
)

type KilledQueryLog struct {
	Timestamp        time.Time
	DBName           string
	ConnectionID     int64
	User             string
	Host             string
	Query            string
	ExecutionTime    time.Duration
	RuleName         string
	KillMode         string
	DryRun           bool
	WaitDuration     time.Duration
	CompletedDuringWait bool
}

type PendingKill struct {
	ConnectionID  int64
	DBName        string
	StartTime     time.Time
	Query         string
	MatchResult   *rules.MatchResult
}

type Monitor struct {
	cfg           *config.Config
	databases     map[string]db.Database
	ruleEngine    *rules.RuleEngine
	analyzer      *analyzer.Analyzer
	predictor     *predictor.Predictor
	indexer       *indexer.Indexer
	auditor       *auditor.Auditor
	killLogger    *log.Logger
	stopChan      chan struct{}
	running       bool
	runningLock   sync.RWMutex
	stats         *MonitorStats
	pendingKills  map[string]*PendingKill
	pendingLock   sync.RWMutex
}

type MonitorStats struct {
	TotalScans           int64
	TotalSlowQueries     int64
	TotalKilled          int64
	TotalDryRun          int64
	TotalWaitStarted     int64
	TotalWaitCompleted   int64
	TotalWaitTimeout     int64
	Errors               int64
	StartTime            time.Time
	statsLock            sync.RWMutex
}

func NewMonitor(cfg *config.Config) (*Monitor, error) {
	m := &Monitor{
		cfg:          cfg,
		databases:    make(map[string]db.Database),
		stopChan:     make(chan struct{}),
		pendingKills: make(map[string]*PendingKill),
		stats: &MonitorStats{
			StartTime: time.Now(),
		},
	}

	for name, dbCfg := range cfg.Databases {
		database, err := db.NewDatabase(name, dbCfg)
		if err != nil {
			return nil, fmt.Errorf("failed to create database %s: %w", name, err)
		}
		m.databases[name] = database
	}

	m.ruleEngine = rules.NewRuleEngine(cfg)
	m.analyzer = analyzer.NewAnalyzer()
	m.predictor = predictor.NewPredictor(cfg.Monitor.Threshold.MaxExecutionTime)
	m.indexer = indexer.NewIndexer()

	if cfg.Monitor.Audit.Enabled {
		aud, err := auditor.NewAuditor(cfg.Monitor.Audit.LogPath, cfg.Monitor.Audit.RotateDaily)
		if err != nil {
			return nil, fmt.Errorf("failed to setup auditor: %w", err)
		}
		m.auditor = aud
	}

	if err := m.setupKillLogger(); err != nil {
		return nil, fmt.Errorf("failed to setup kill logger: %w", err)
	}

	return m, nil
}

func (m *Monitor) setupKillLogger() error {
	logFile, err := os.OpenFile(m.cfg.Log.KillLog, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	m.killLogger = log.New(logFile, "", log.LstdFlags)
	return nil
}

func (m *Monitor) Start() error {
	m.runningLock.Lock()
	defer m.runningLock.Unlock()

	if m.running {
		return fmt.Errorf("monitor is already running")
	}

	for name, database := range m.databases {
		if err := database.Connect(); err != nil {
			log.Printf("Warning: failed to connect to database %s: %v", name, err)
		} else {
			log.Printf("Connected to database: %s", name)
		}
	}

	m.running = true
	go m.run()

	log.Printf("Monitor started. Scan interval: %v, Threshold: %v",
		m.cfg.Monitor.Interval, m.cfg.Monitor.Threshold.MaxExecutionTime)

	if m.cfg.Monitor.DryRun {
		log.Println("Running in DRY RUN mode - no queries will actually be killed")
	}

	return nil
}

func (m *Monitor) Stop() {
	m.runningLock.Lock()
	defer m.runningLock.Unlock()

	if !m.running {
		return
	}

	close(m.stopChan)
	m.running = false

	for name, database := range m.databases {
		if err := database.Close(); err != nil {
			log.Printf("Warning: failed to close database %s: %v", name, err)
		}
	}

	if m.auditor != nil {
		m.auditor.Close()
	}

	log.Println("Monitor stopped")
}

func (m *Monitor) run() {
	scanTicker := time.NewTicker(m.cfg.Monitor.Interval)
	defer scanTicker.Stop()

	var pendingCheckTicker *time.Ticker
	if m.cfg.Monitor.TransactionWait.Enabled {
		pendingCheckTicker = time.NewTicker(m.cfg.Monitor.TransactionWait.CheckInterval)
		defer pendingCheckTicker.Stop()
	}

	var predictionTicker *time.Ticker
	if m.cfg.Monitor.Prediction.Enabled {
		predictionTicker = time.NewTicker(m.cfg.Monitor.Prediction.ReportInterval)
		defer predictionTicker.Stop()
	}

	var indexerTicker *time.Ticker
	if m.cfg.Monitor.Indexer.Enabled {
		indexerTicker = time.NewTicker(m.cfg.Monitor.Indexer.ReportInterval)
		defer indexerTicker.Stop()
	}

	for {
		select {
		case <-m.stopChan:
			return
		case <-scanTicker.C:
			m.scanOnce()
		case <-pendingCheckTicker.C:
			if m.cfg.Monitor.TransactionWait.Enabled {
				m.checkPendingQueries()
			}
		case <-predictionTicker.C:
			if m.cfg.Monitor.Prediction.Enabled {
				log.Println(m.predictor.GeneratePredictionReport())
			}
		case <-indexerTicker.C:
			if m.cfg.Monitor.Indexer.Enabled {
				log.Println(m.indexer.GenerateIndexReport())
			}
		}
	}
}

func (m *Monitor) scanOnce() {
	m.stats.statsLock.Lock()
	m.stats.TotalScans++
	m.stats.statsLock.Unlock()

	var wg sync.WaitGroup

	for dbName, database := range m.databases {
		wg.Add(1)
		go func(name string, db db.Database) {
			defer wg.Done()
			m.scanDatabase(name, db)
		}(dbName, database)
	}

	wg.Wait()
}

func (m *Monitor) scanDatabase(dbName string, database db.Database) {
	if err := database.Ping(); err != nil {
		log.Printf("Reconnecting to database %s...", dbName)
		if err := database.Connect(); err != nil {
			log.Printf("Failed to reconnect to %s: %v", dbName, err)
			m.stats.statsLock.Lock()
			m.stats.Errors++
			m.stats.statsLock.Unlock()
			return
		}
	}

	ctx, cancel := context.WithTimeout(context.Background(), m.cfg.Monitor.Interval/2)
	defer cancel()

	slowQueries, err := database.GetSlowQueries(ctx, m.cfg.Monitor.Threshold.MaxExecutionTime)
	if err != nil {
		log.Printf("Error getting slow queries from %s: %v", dbName, err)
		m.stats.statsLock.Lock()
		m.stats.Errors++
		m.stats.statsLock.Unlock()
		return
	}

	m.stats.statsLock.Lock()
	m.stats.TotalSlowQueries += int64(len(slowQueries))
	m.stats.statsLock.Unlock()

	for _, query := range slowQueries {
		m.processQuery(dbName, database, &query)
	}
}

func (m *Monitor) processQuery(dbName string, database db.Database, query *db.SlowQuery) {
	analysis := m.analyzer.AnalyzeQuery(query)
	m.analyzer.RecordQuery(query, analysis)

	if m.cfg.Monitor.Prediction.Enabled {
		m.predictor.RecordQuery(query)

		if prediction := m.predictor.Predict(analysis.QueryHash); prediction != nil {
			if prediction.WillBeKilled && prediction.Confidence >= m.cfg.Monitor.Prediction.ConfidenceThreshold {
				log.Printf("[PREDICTION] High risk query detected (risk: %s, confidence: %.0f%%). "+
					"Current: %v, Predicted: %v, Expected kill in: %v. Query: %s",
					prediction.RiskLevel, prediction.Confidence*100,
					prediction.CurrentTime, prediction.PredictedTime,
					prediction.TimeToKill, truncateQuery(query.Query, 100))
			}
		}
	}

	matchResult := m.ruleEngine.Evaluate(
		query,
		m.cfg.Monitor.Threshold.MaxExecutionTime,
		m.cfg.Monitor.DefaultKillMode,
	)

	if !matchResult.Matched {
		if m.auditor != nil && m.ruleEngine.IsWhitelisted(query) {
			m.auditor.RecordWhitelist(analysis.QueryHash, query.Query, "whitelisted")
		}
		return
	}

	pendingKey := fmt.Sprintf("%s-%d", dbName, query.ConnectionID)

	if m.cfg.Monitor.TransactionWait.Enabled && !m.cfg.Monitor.DryRun && !matchResult.NotifyOnly {
		m.pendingLock.RLock()
		pending, exists := m.pendingKills[pendingKey]
		m.pendingLock.RUnlock()

		if exists {
			if time.Since(pending.StartTime) >= m.cfg.Monitor.TransactionWait.WaitDuration {
				m.performKill(dbName, database, query, matchResult, pendingKey, time.Since(pending.StartTime), false)
			}
			return
		}

		m.pendingLock.Lock()
		m.pendingKills[pendingKey] = &PendingKill{
			ConnectionID: query.ConnectionID,
			DBName:       dbName,
			StartTime:    time.Now(),
			Query:        query.Query,
			MatchResult:  matchResult,
		}
		m.pendingLock.Unlock()

		m.stats.statsLock.Lock()
		m.stats.TotalWaitStarted++
		m.stats.statsLock.Unlock()

		log.Printf("[WAIT] Starting transaction wait for query on %s (conn: %d, user: %s, time: %v, wait: %v)",
			dbName, query.ConnectionID, query.User, query.ExecutionTime,
			m.cfg.Monitor.TransactionWait.WaitDuration)
		return
	}

	m.performKill(dbName, database, query, matchResult, pendingKey, 0, false)
}

func (m *Monitor) performKill(dbName string, database db.Database, query *db.SlowQuery,
	matchResult *rules.MatchResult, pendingKey string, waitDuration time.Duration, completed bool) {

	if pendingKey != "" {
		m.pendingLock.Lock()
		delete(m.pendingKills, pendingKey)
		m.pendingLock.Unlock()
	}

	analysis := m.analyzer.AnalyzeQuery(query)

	if m.cfg.Monitor.Indexer.Enabled && !m.cfg.Monitor.DryRun && !matchResult.NotifyOnly {
		m.indexer.RecordKilledQuery(query.Query, query.ExecutionTime)
		m.predictor.RecordKill(analysis.QueryHash)
	}

	killedLog := KilledQueryLog{
		Timestamp:           time.Now(),
		DBName:              dbName,
		ConnectionID:        query.ConnectionID,
		User:                query.User,
		Host:                query.Host,
		Query:               query.Query,
		ExecutionTime:       query.ExecutionTime,
		RuleName:            matchResult.RuleName,
		KillMode:            matchResult.KillMode,
		DryRun:              m.cfg.Monitor.DryRun || matchResult.NotifyOnly,
		WaitDuration:        waitDuration,
		CompletedDuringWait: completed,
	}

	if m.auditor != nil && !m.cfg.Monitor.DryRun {
		if waitDuration > 0 {
			m.auditor.RecordWait(dbName, query.ConnectionID, query.User, query.Host,
				analysis.QueryHash, query.Query, query.ExecutionTime, completed, waitDuration)
		}

		if !completed {
			var killErr error
			if !matchResult.NotifyOnly {
				ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
				if err := database.KillQuery(ctx, query.ConnectionID, matchResult.KillMode); err != nil {
					killErr = err
				}
				cancel()
			}
			m.auditor.RecordKill(dbName, query.ConnectionID, query.User, query.Host,
				analysis.QueryHash, query.Query, query.ExecutionTime,
				matchResult.RuleName, matchResult.KillMode, waitDuration, killErr)
		}
	}

	if m.cfg.Monitor.DryRun || matchResult.NotifyOnly {
		m.logKilledQuery(killedLog)
		m.stats.statsLock.Lock()
		m.stats.TotalDryRun++
		m.stats.statsLock.Unlock()
		log.Printf("[DRY RUN] Would kill query on %s (conn: %d, user: %s, time: %v, rule: %s)",
			dbName, query.ConnectionID, query.User, query.ExecutionTime, matchResult.RuleName)
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := database.KillQuery(ctx, query.ConnectionID, matchResult.KillMode); err != nil {
		log.Printf("Failed to kill query on %s (conn: %d): %v",
			dbName, query.ConnectionID, err)
		m.stats.statsLock.Lock()
		m.stats.Errors++
		m.stats.statsLock.Unlock()
		return
	}

	m.logKilledQuery(killedLog)
	m.stats.statsLock.Lock()
	m.stats.TotalKilled++
	if waitDuration > 0 {
		m.stats.TotalWaitTimeout++
	}
	m.stats.statsLock.Unlock()

	waitInfo := ""
	if waitDuration > 0 {
		waitInfo = fmt.Sprintf(", waited: %v", waitDuration)
	}
	log.Printf("Killed query on %s (conn: %d, user: %s, time: %v, rule: %s, mode: %s%s)",
		dbName, query.ConnectionID, query.User, query.ExecutionTime,
		matchResult.RuleName, matchResult.KillMode, waitInfo)
}

func (m *Monitor) checkPendingQueries() {
	m.pendingLock.RLock()
	pendingCopy := make(map[string]*PendingKill, len(m.pendingKills))
	for k, v := range m.pendingKills {
		pendingCopy[k] = v
	}
	m.pendingLock.RUnlock()

	for key, pending := range pendingCopy {
		db, exists := m.databases[pending.DBName]
		if !exists {
			m.pendingLock.Lock()
			delete(m.pendingKills, key)
			m.pendingLock.Unlock()
			continue
		}

		ctx, cancel := context.WithTimeout(context.Background(), m.cfg.Monitor.TransactionWait.CheckInterval)
		queries, err := db.GetSlowQueries(ctx, 1*time.Second)
		cancel()

		if err != nil {
			continue
		}

		found := false
		for _, q := range queries {
			if q.ConnectionID == pending.ConnectionID {
				found = true
				break
			}
		}

		if !found {
			m.pendingLock.Lock()
			delete(m.pendingKills, key)
			m.pendingLock.Unlock()

			m.stats.statsLock.Lock()
			m.stats.TotalWaitCompleted++
			m.stats.statsLock.Unlock()

			log.Printf("[WAIT COMPLETE] Query completed during wait period on %s (conn: %d, waited: %v)",
				pending.DBName, pending.ConnectionID, time.Since(pending.StartTime))
		}
	}
}

func (m *Monitor) logKilledQuery(logEntry KilledQueryLog) {
	dryRunFlag := ""
	if logEntry.DryRun {
		dryRunFlag = " [DRY RUN]"
	}

	waitInfo := ""
	if logEntry.WaitDuration > 0 {
		if logEntry.CompletedDuringWait {
			waitInfo = fmt.Sprintf(" | Waited=%v (completed)", logEntry.WaitDuration)
		} else {
			waitInfo = fmt.Sprintf(" | Waited=%v (timeout)", logEntry.WaitDuration)
		}
	}

	m.killLogger.Printf(
		"DB=%s%s | ConnID=%d | User=%s | Host=%s | Time=%v | Rule=%s | Mode=%s%s | Query=%s",
		logEntry.DBName,
		dryRunFlag,
		logEntry.ConnectionID,
		logEntry.User,
		logEntry.Host,
		logEntry.ExecutionTime,
		logEntry.RuleName,
		logEntry.KillMode,
		waitInfo,
		truncateQuery(logEntry.Query, 500),
	)
}

func (m *Monitor) GetStats() *MonitorStats {
	m.stats.statsLock.RLock()
	defer m.stats.statsLock.RUnlock()

	return &MonitorStats{
		TotalScans:         m.stats.TotalScans,
		TotalSlowQueries:   m.stats.TotalSlowQueries,
		TotalKilled:        m.stats.TotalKilled,
		TotalDryRun:        m.stats.TotalDryRun,
		TotalWaitStarted:   m.stats.TotalWaitStarted,
		TotalWaitCompleted: m.stats.TotalWaitCompleted,
		TotalWaitTimeout:   m.stats.TotalWaitTimeout,
		Errors:             m.stats.Errors,
		StartTime:          m.stats.StartTime,
	}
}

func (m *Monitor) GetPendingKillsCount() int {
	m.pendingLock.RLock()
	defer m.pendingLock.RUnlock()
	return len(m.pendingKills)
}

func (m *Monitor) GetAnalyzer() *analyzer.Analyzer {
	return m.analyzer
}

func truncateQuery(query string, maxLen int) string {
	if len(query) <= maxLen {
		return query
	}
	return query[:maxLen] + "... [TRUNCATED]"
}

func (m *Monitor) PrintStats() {
	stats := m.GetStats()
	uptime := time.Since(stats.StartTime)
	pendingCount := m.GetPendingKillsCount()

	log.Println("\n=== Monitor Statistics ===")
	log.Printf("Uptime: %v", uptime)
	log.Printf("Total scans: %d", stats.TotalScans)
	log.Printf("Slow queries detected: %d", stats.TotalSlowQueries)
	log.Printf("Queries killed: %d", stats.TotalKilled)
	log.Printf("Dry-run actions: %d", stats.TotalDryRun)
	log.Printf("Pending kills in wait: %d", pendingCount)

	if m.cfg.Monitor.TransactionWait.Enabled {
		log.Printf("Transaction waits started: %d", stats.TotalWaitStarted)
		log.Printf("Transaction waits completed: %d", stats.TotalWaitCompleted)
		log.Printf("Transaction waits timed out: %d", stats.TotalWaitTimeout)
	}

	log.Printf("Errors: %d", stats.Errors)

	if m.cfg.Monitor.Prediction.Enabled {
		log.Println(m.predictor.GeneratePredictionReport())
	}

	if m.cfg.Monitor.Indexer.Enabled {
		log.Println(m.indexer.GenerateIndexReport())
	}

	if m.auditor != nil {
		log.Println(m.auditor.GenerateImpactReport())
	}

	log.Println(m.analyzer.GenerateReport())
}
