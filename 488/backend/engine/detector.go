package engine

import (
	"deadlock-resolver/config"
	"deadlock-resolver/database"
	"deadlock-resolver/models"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"
)

type DeadlockDetector struct {
	connector      database.DBConnector
	config         *config.Config
	ruleEngine     *RuleEngine
	store          *HistoryStore
	prevention     *PreventionEngine
	sandbox        *SandboxEngine
	audit          *AuditEngine
	mu             sync.RWMutex
	currentDeadlocks []models.Deadlock
	isRunning      bool
	stopChan       chan struct{}
	logListener    bool
	processedDeadlocks map[string]bool
}

func NewDeadlockDetector(connector database.DBConnector, cfg *config.Config) *DeadlockDetector {
	d := &DeadlockDetector{
		connector:         connector,
		config:            cfg,
		ruleEngine:        NewRuleEngine(&cfg.Strategy),
		store:             NewHistoryStore(cfg.StorePath),
		prevention:        NewPreventionEngine(),
		currentDeadlocks:  make([]models.Deadlock, 0),
		isRunning:         false,
		stopChan:          make(chan struct{}),
		logListener:       false,
		processedDeadlocks: make(map[string]bool),
		audit:             NewAuditEngine(),
	}
	d.sandbox = NewSandboxEngine(d)
	return d
}

func (d *DeadlockDetector) Start() {
	d.mu.Lock()
	if d.isRunning {
		d.mu.Unlock()
		return
	}
	d.isRunning = true
	d.mu.Unlock()
	
	go d.detectionLoop()
	go d.startRealtimeMonitor()
}

func (d *DeadlockDetector) Stop() {
	d.mu.Lock()
	defer d.mu.Unlock()
	
	if !d.isRunning {
		return
	}
	
	d.isRunning = false
	close(d.stopChan)
}

func (d *DeadlockDetector) startRealtimeMonitor() {
	callback := func(event *models.DeadlockLogEvent) {
		log.Printf("Realtime deadlock detected: %s (latency: %v)", event.DeadlockID, time.Since(event.Timestamp))
	}
	
	err := d.connector.StartLogListener(callback)
	if err != nil {
		log.Printf("Failed to start log listener: %v", err)
	}
	d.logListener = true
}

func (d *DeadlockDetector) detectionLoop() {
	ticker := time.NewTicker(d.config.Strategy.DetectionInterval)
	defer ticker.Stop()
	
	for {
		select {
		case <-d.stopChan:
			return
		case <-ticker.C:
			if !d.config.Strategy.Enabled {
				continue
			}
			
			startTime := time.Now()
			deadlocks, err := d.connector.DetectDeadlocks()
			if err != nil {
				log.Printf("Error detecting deadlocks: %v", err)
				continue
			}
			
			d.mu.Lock()
			d.currentDeadlocks = deadlocks
			d.mu.Unlock()
			
			for i := range deadlocks {
				deadlock := &deadlocks[i]
				deadlock.DetectionLatencyMs = time.Since(startTime).Milliseconds()
				
				d.mu.Lock()
				alreadyProcessed := d.processedDeadlocks[deadlock.ID]
				if !alreadyProcessed {
					d.processedDeadlocks[deadlock.ID] = true
				}
				d.mu.Unlock()
				
				if !alreadyProcessed {
					d.processDeadlock(deadlock)
				}
			}
		}
	}
}

func (d *DeadlockDetector) processDeadlock(deadlock *models.Deadlock) {
	log.Printf("Deadlock detected: %s, severity: %s, transactions: %d, latency: %dms", 
		deadlock.ID, deadlock.Severity, len(deadlock.Transactions), deadlock.DetectionLatencyMs)
	
	go d.prevention.AnalyzeDeadlock(*deadlock)
	
	evalResult, err := d.ruleEngine.Evaluate(deadlock)
	if err != nil {
		log.Printf("Error evaluating rules: %v", err)
		return
	}
	
	victimID := d.ruleEngine.SelectVictim(deadlock, evalResult)
	ruleApplied := ""
	if len(evalResult.MatchedRules) > 0 {
		ruleApplied = evalResult.MatchedRules[0].Name
	}
	
	if victimID == 0 {
		log.Printf("No suitable victim found for deadlock %s", deadlock.ID)
		deadlock.ResolutionType = "manual"
		d.store.SaveDeadlock(deadlock)
		return
	}
	
	impact := d.ruleEngine.AssessImpact(deadlock, victimID)
	deadlock.VictimSelected = victimID
	deadlock.ImpactAssessment = impact
	
	var victim *models.Transaction
	for _, tx := range deadlock.Transactions {
		if tx.ID == victimID {
			victim = &tx
			break
		}
	}
	
	if d.config.Strategy.AutoKill {
		err := d.ResolveDeadlock(deadlock.ID, victimID)
		if err != nil {
			log.Printf("Error resolving deadlock %s: %v", deadlock.ID, err)
			deadlock.ResolutionType = "failed"
			if victim != nil {
				d.audit.LogKillAction(*deadlock, victim, d.config.Strategy.KillStrategy, ruleApplied, "SYSTEM", "", "")
			}
		} else {
			deadlock.ResolutionType = "auto"
			if victim != nil {
				d.audit.LogKillAction(*deadlock, victim, d.config.Strategy.KillStrategy, ruleApplied, "SYSTEM", "", "")
			}
		}
	} else {
		deadlock.ResolutionType = "pending"
	}
	
	d.store.SaveDeadlock(deadlock)
}

func (d *DeadlockDetector) SelectVictim(deadlock *models.Deadlock, killStrategy string) (*models.Transaction, string) {
	if killStrategy == "" {
		killStrategy = d.config.Strategy.KillStrategy
	}
	
	evalResult, err := d.ruleEngine.EvaluateWithStrategy(deadlock, killStrategy)
	if err != nil {
		return nil, ""
	}
	
	victimID := d.ruleEngine.SelectVictim(deadlock, evalResult)
	if victimID == 0 {
		return nil, ""
	}
	
	ruleApplied := ""
	if len(evalResult.MatchedRules) > 0 {
		ruleApplied = evalResult.MatchedRules[0].Name
	}
	
	for _, tx := range deadlock.Transactions {
		if tx.ID == victimID {
			return &tx, ruleApplied
		}
	}
	
	return nil, ruleApplied
}

func (d *DeadlockDetector) ResolveDeadlock(deadlockID string, transactionID int64) error {
	err := d.connector.KillTransaction(transactionID)
	if err != nil {
		d.store.SaveResolution(deadlockID, transactionID, "manual", err)
		return err
	}
	
	d.store.SaveResolution(deadlockID, transactionID, "manual", nil)
	
	now := time.Now()
	
	d.mu.Lock()
	for i := range d.currentDeadlocks {
		if d.currentDeadlocks[i].ID == deadlockID {
			d.currentDeadlocks[i].ResolvedAt = &now
		}
	}
	d.mu.Unlock()
	
	return nil
}

func (d *DeadlockDetector) GetCurrentDeadlocks() []models.Deadlock {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.currentDeadlocks
}

func (d *DeadlockDetector) GetRuleEngine() *RuleEngine {
	return d.ruleEngine
}

func (d *DeadlockDetector) GetHistoryStore() *HistoryStore {
	return d.store
}

func (d *DeadlockDetector) IsRunning() bool {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.isRunning
}

func (d *DeadlockDetector) IsLogListenerActive() bool {
	d.mu.RLock()
	defer d.mu.RUnlock()
	return d.logListener
}

func (d *DeadlockDetector) GetTransactions() ([]models.Transaction, error) {
	return d.connector.GetTransactions()
}

func (d *DeadlockDetector) GetPreventionEngine() *PreventionEngine {
	return d.prevention
}

func (d *DeadlockDetector) GetSandboxEngine() *SandboxEngine {
	return d.sandbox
}

func (d *DeadlockDetector) GetAuditEngine() *AuditEngine {
	return d.audit
}

type HistoryStore struct {
	basePath string
	mu       sync.RWMutex
}

func NewHistoryStore(basePath string) *HistoryStore {
	os.MkdirAll(basePath, 0755)
	return &HistoryStore{
		basePath: basePath,
	}
}

func (hs *HistoryStore) SaveDeadlock(deadlock *models.Deadlock) error {
	hs.mu.Lock()
	defer hs.mu.Unlock()
	
	filename := filepath.Join(hs.basePath, fmt.Sprintf("deadlock_%s.json", deadlock.ID))
	data, err := json.MarshalIndent(deadlock)
	if err != nil {
		return err
	}
	
	return os.WriteFile(filename, data, 0644)
}

func (hs *HistoryStore) SaveResolution(deadlockID string, transactionID int64, action string, err error) error {
	hs.mu.Lock()
	defer hs.mu.Unlock()
	
	history := models.ResolutionHistory{
		ID:            fmt.Sprintf("res_%d", time.Now().UnixNano()),
		DeadlockID:    deadlockID,
		Timestamp:       time.Now(),
		Action:          action,
		TransactionID:   transactionID,
		Success:         err == nil,
	}
	
	if err != nil {
		history.ErrorMessage = err.Error()
	}
	
	filename := filepath.Join(hs.basePath, fmt.Sprintf("history_%s.json", history.ID))
	data, jsonErr := json.MarshalIndent(history)
	if jsonErr != nil {
		return jsonErr
	}
	
	return os.WriteFile(filename, data, 0644)
}

func (hs *HistoryStore) GetDeadlockHistory(deadlockID string) (*models.Deadlock, error) {
	hs.mu.RLock()
	defer hs.mu.RUnlock()
	
	filename := filepath.Join(hs.basePath, fmt.Sprintf("deadlock_%s.json", deadlockID))
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, err
	}
	
	var deadlock models.Deadlock
	err = json.Unmarshal(data, &deadlock)
	return &deadlock, err
}

func (hs *HistoryStore) GetAllDeadlocks() ([]models.Deadlock, error) {
	hs.mu.RLock()
	defer hs.mu.RUnlock()
	
	files, err := filepath.Glob(filepath.Join(hs.basePath, "deadlock_*.json"))
	if err != nil {
		return nil, err
	}
	
	var deadlocks []models.Deadlock
	for _, file := range files {
		data, err := os.ReadFile(file)
		if err != nil {
			continue
		}
		
		var deadlock models.Deadlock
		err = json.Unmarshal(data, &deadlock)
		if err != nil {
			continue
		}
		
		deadlocks = append(deadlocks, deadlock)
	}
	
	sort.Slice(deadlocks, func(i, j int) bool {
		return deadlocks[i].DetectedAt.After(deadlocks[j].DetectedAt)
	})
	
	return deadlocks, nil
}

func (hs *HistoryStore) GetResolutionHistory() ([]models.ResolutionHistory, error) {
	hs.mu.RLock()
	defer hs.mu.RUnlock()
	
	files, err := filepath.Glob(filepath.Join(hs.basePath, "history_*.json"))
	if err != nil {
		return nil, err
	}
	
	var histories []models.ResolutionHistory
	for _, file := range files {
		data, err := os.ReadFile(file)
		if err != nil {
			continue
		}
		
		var history models.ResolutionHistory
		err = json.Unmarshal(data, &history)
		if err != nil {
			continue
		}
		
		histories = append(histories, history)
	}
	
	return histories, nil
}

func (hs *HistoryStore) GetStatistics() (*models.Statistics, error) {
	deadlocks, err := hs.GetAllDeadlocks()
	if err != nil {
		return nil, err
	}
	
	histories, err := hs.GetResolutionHistory()
	if err != nil {
		return nil, err
	}
	
	stats := &models.Statistics{
		TotalDeadlocks:      len(deadlocks),
		ResolvedDeadlocks:   0,
		AutoKilledCount:     0,
		ManualKilledCount:   0,
		TopDeadlockUsers:    make([]models.KV, 0),
		TopDeadlockTables:   make([]models.KV, 0),
		DeadlocksByHour:     make([]models.TimeData, 0),
		DeadlocksByType:     make([]models.KV, 0),
		DeadlocksBySeverity: make([]models.KV, 0),
	}
	
	userCount := make(map[string]int)
	hourCount := make(map[string]int)
	typeCount := make(map[string]int)
	severityCount := make(map[string]int)
	
	var totalLatencyMs int64
	latencyCount := 0
	
	for _, deadlock := range deadlocks {
		if deadlock.ResolvedAt != nil {
			stats.ResolvedDeadlocks++
		}
		
		if deadlock.DetectionLatencyMs > 0 {
			totalLatencyMs += deadlock.DetectionLatencyMs
			latencyCount++
		}
		
		for _, trx := range deadlock.Transactions {
			if trx.User != "" {
				userCount[trx.User]++
			}
			if trx.TransactionType != "" {
				typeCount[string(trx.TransactionType)]++
			}
		}
		
		hour := deadlock.DetectedAt.Format("2006-01-02 15:00")
		hourCount[hour]++
		
		if deadlock.Severity != "" {
			severityCount[string(deadlock.Severity)]++
		}
	}
	
	for user, count := range userCount {
		stats.TopDeadlockUsers = append(stats.TopDeadlockUsers, models.KV{Key: user, Value: count})
	}
	
	for hour, count := range hourCount {
		stats.DeadlocksByHour = append(stats.DeadlocksByHour, models.TimeData{Time: hour, Count: count})
	}
	
	for t, count := range typeCount {
		stats.DeadlocksByType = append(stats.DeadlocksByType, models.KV{Key: t, Value: count})
	}
	
	for s, count := range severityCount {
		stats.DeadlocksBySeverity = append(stats.DeadlocksBySeverity, models.KV{Key: s, Value: count})
	}
	
	for _, history := range histories {
		if history.Success {
			if history.Action == "auto" {
				stats.AutoKilledCount++
			} else {
				stats.ManualKilledCount++
			}
		}
	}
	
	if latencyCount > 0 {
		avgLatency := totalLatencyMs / int64(latencyCount)
		stats.AvgDetectionLatency = (time.Duration(avgLatency) * time.Millisecond).String()
	}
	
	sort.Slice(stats.TopDeadlockUsers, func(i, j int) bool {
		return stats.TopDeadlockUsers[i].Value > stats.TopDeadlockUsers[j].Value
	})
	
	return stats, nil
}
