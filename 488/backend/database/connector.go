package database

import (
	"bufio"
	"database/sql"
	"fmt"
	"deadlock-resolver/config"
	"deadlock-resolver/models"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

type DBConnector interface {
	Connect() error
	Close() error
	DetectDeadlocks() ([]models.Deadlock, error)
	GetTransactions() ([]models.Transaction, error)
	KillTransaction(transactionID int64) error
	StartLogListener(callback func(*models.DeadlockLogEvent)) error
	StopLogListener()
}

func NewConnector(cfg *config.DatabaseConfig) (DBConnector, error) {
	switch cfg.Type {
	case "mysql":
		return &MySQLConnector{config: cfg}, nil
	case "postgres":
		return &PostgreSQLConnector{config: cfg}, nil
	default:
		return nil, fmt.Errorf("unsupported database type: %s", cfg.Type)
	}
}

type MySQLConnector struct {
	config          *config.DatabaseConfig
	db              *sql.DB
	logListenerStop chan struct{}
	logListenerWg   sync.WaitGroup
}

func (m *MySQLConnector) Connect() error {
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True",
		m.config.User, m.config.Password, m.config.Host, m.config.Port, m.config.DBName)
	
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		return err
	}
	
	if err := db.Ping(); err != nil {
		return err
	}
	
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(time.Hour)
	
	m.db = db
	m.logListenerStop = make(chan struct{})
	return nil
}

func (m *MySQLConnector) Close() error {
	m.StopLogListener()
	if m.db != nil {
		return m.db.Close()
	}
	return nil
}

func (m *MySQLConnector) StartLogListener(callback func(*models.DeadlockLogEvent)) error {
	go func() {
		m.logListenerWg.Add(1)
		defer m.logListenerWg.Done()
		
		ticker := time.NewTicker(100 * time.Millisecond)
		defer ticker.Stop()
		
		lastCheck := time.Now()
		
		for {
			select {
			case <-m.logListenerStop:
				return
			case <-ticker.C:
				deadlocks, err := m.queryDeadlockMonitor()
				if err != nil {
					continue
				}
				
				for _, dl := range deadlocks {
					if dl.DetectedAt.After(lastCheck) {
						event := &models.DeadlockLogEvent{
							Timestamp:  dl.DetectedAt,
							LogEntry:   fmt.Sprintf("Deadlock detected: %s", dl.ID),
							DeadlockID: dl.ID,
							Source:     "realtime_monitor",
						}
						callback(event)
					}
				}
				lastCheck = time.Now()
			}
		}
	}()
	
	return nil
}

func (m *MySQLConnector) StopLogListener() {
	if m.logListenerStop != nil {
		close(m.logListenerStop)
		m.logListenerWg.Wait()
	}
}

func (m *MySQLConnector) queryDeadlockMonitor() ([]models.Deadlock, error) {
	rows, err := m.db.Query(`
		SELECT 
			trx.trx_id,
			trx.trx_started,
			trx.trx_mysql_thread_id,
			trx.trx_wait_started,
			trx.trx_state,
			trx.trx_query,
			trx.trx_rows_locked,
			trx.trx_rows_modified,
			trx.trx_lock_memory_bytes,
			lock_wait.requesting_trx_id,
			lock_wait.requested_lock_id,
			lock_wait.blocking_trx_id,
			lock_wait.blocking_lock_id
		FROM information_schema.innodb_trx trx
		LEFT JOIN information_schema.innodb_lock_waits lock_wait 
			ON trx.trx_id = lock_wait.requesting_trx_id
		WHERE trx.trx_state = 'LOCK WAIT'
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	type WaitRelation struct {
		RequestingTrxID string
		BlockingTrxID   string
	}
	
	var waitRelations []WaitRelation
	var transactions []models.Transaction
	
	trxMap := make(map[string]*models.Transaction)
	
	for rows.Next() {
		var (
			trxID, trxStarted, trxMySQLThreadID, trxWaitStarted, trxState,
			trxQuery, trxIsolationLevel string
			trxRowsLocked, trxRowsModified, trxLockMemoryBytes,
			trxConcurrencyTickets, trxUniqueChecks, trxForeignKeyChecks,
			trxAdaptiveHashLatched, trxAdaptiveHashTimeout,
			trxIsReadOnly, trxAutocommitNonLocking int
			trxLastForeignKeyError, requestingTrxID,
			requestedLockID, blockingTrxID, blockingLockID sql.NullString
		)
		
		err := rows.Scan(
			&trxID, &trxStarted, &trxMySQLThreadID, &trxWaitStarted, &trxState,
			&trxQuery, &trxRowsLocked, &trxRowsModified, &trxLockMemoryBytes,
			&requestingTrxID, &requestedLockID, &blockingTrxID, &blockingLockID,
		)
		if err != nil {
			return nil, err
		}
		
		startTime, _ := time.Parse("2006-01-02 15:04:05", trxStarted)
		
		trxType := DetectTransactionType(trxQuery)
		costScore := CalculateCostScore(trxRowsModified, trxRowsLocked, trxLockMemoryBytes, time.Since(startTime).Seconds())
		killPriority := CalculateKillPriority(trxType, costScore, time.Since(startTime).Seconds())
		
		trx := &models.Transaction{
			TrxID:           trxID,
			ProcessID:       parseUint32(trxMySQLThreadID),
			State:           trxState,
			Info:            trxQuery,
			StartTime:       startTime,
			RowsModified:    trxRowsModified,
			RowsLocked:      trxRowsLocked,
			LockMemoryBytes: trxLockMemoryBytes,
			TransactionType: trxType,
			CostScore:       costScore,
			KillPriority:    killPriority,
		}
		
		trxMap[trxID] = trx
		
		if blockingTrxID.Valid && requestingTrxID.Valid {
			waitRelations = append(waitRelations, WaitRelation{
				RequestingTrxID: requestingTrxID.String,
				BlockingTrxID:   blockingTrxID.String,
			})
		}
	}
	
	for _, wr := range waitRelations {
		if trx, ok := trxMap[wr.RequestingTrxID]; ok {
			trx.WaitLockID = wr.BlockingTrxID
		}
	}
	
	for _, trx := range trxMap {
		transactions = append(transactions, *trx)
	}
	
	deadlocks := detectDeadlockCycle(transactions, waitRelations)
	
	return deadlocks, nil
}

func (m *MySQLConnector) DetectDeadlocks() ([]models.Deadlock, error) {
	return m.queryDeadlockMonitor()
}

func (m *MySQLConnector) GetTransactions() ([]models.Transaction, error) {
	rows, err := m.db.Query(`
		SELECT 
			id, user, host, db, command, time, state, info
		FROM information_schema.processlist
		WHERE command != 'Sleep'
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	
	var transactions []models.Transaction
	
	for rows.Next() {
		var trx models.Transaction
		var db, info sql.NullString
		
		err := rows.Scan(&trx.ID, &trx.User, &trx.Host, &trx.DB, &trx.Command, &trx.Time, &trx.State, &info)
		if err != nil {
			return nil, err
		}
		
		if db.Valid {
			trx.DB = db.String
		}
		if info.Valid {
			trx.Info = info.String
			trx.TransactionType = DetectTransactionType(info.String)
		}
		
		transactions = append(transactions, trx)
	}
	
	return transactions, nil
}

func (m *MySQLConnector) KillTransaction(transactionID int64) error {
	_, err := m.db.Exec(fmt.Sprintf("KILL %d", transactionID))
	return err
}

type PostgreSQLConnector struct {
	config          *config.DatabaseConfig
	db              *sql.DB
	logListenerStop chan struct{}
	logListenerWg   sync.WaitGroup
	logFilePath     string
}

func (p *PostgreSQLConnector) Connect() error {
	dsn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		p.config.Host, p.config.Port, p.config.User, p.config.Password, p.config.DBName)
	
	db, err := sql.Open("postgres", dsn)
	if err != nil {
		return err
	}
	
	if err := db.Ping(); err != nil {
		return err
	}
	
	p.db = db
	p.logListenerStop = make(chan struct{})
	return nil
}

func (p *PostgreSQLConnector) Close() error {
	p.StopLogListener()
	if p.db != nil {
		return p.db.Close()
	}
	return nil
}

func (p *PostgreSQLConnector) StartLogListener(callback func(*models.DeadlockLogEvent)) error {
	go func() {
		p.logListenerWg.Add(1)
		defer p.logListenerWg.Done()
		
		ticker := time.NewTicker(100 * time.Millisecond)
		defer ticker.Stop()
		
		lastCheck := time.Now()
		
		for {
			select {
			case <-p.logListenerStop:
				return
			case <-ticker.C:
				deadlocks, err := p.queryDeadlockMonitor()
				if err != nil {
					continue
				}
				
				for _, dl := range deadlocks {
					if dl.DetectedAt.After(lastCheck) {
						event := &models.DeadlockLogEvent{
							Timestamp:  dl.DetectedAt,
							LogEntry:   fmt.Sprintf("Deadlock detected: %s", dl.ID),
							DeadlockID: dl.ID,
							Source:     "realtime_monitor",
						}
						callback(event)
					}
				}
				lastCheck = time.Now()
			}
		}
	}()
	
	return nil
}

func (p *PostgreSQLConnector) StopLogListener() {
	if p.logListenerStop != nil {
		close(p.logListenerStop)
		p.logListenerWg.Wait()
	}
}

func (p *PostgreSQLConnector) queryDeadlockMonitor() ([]models.Deadlock, error) {
	rows, err := p.db.Query(`
		SELECT 
			blocked.pid AS blocked_pid,
			blocked.usename AS blocked_user,
			blocked.query AS blocked_query,
			blocked.query_start AS blocked_start,
			blocked.state AS blocked_state,
			blocking.pid AS blocking_pid,
			blocking.usename AS blocking_user,
			blocking.query AS blocking_query,
			blocking.query_start AS blocking_start,
			blocking.state AS blocking_state
		FROM pg_catalog.pg_locks blocked_lock
		JOIN pg_catalog.pg_stat_activity blocked ON blocked_lock.pid = blocked.pid
		JOIN pg_catalog.pg_locks blocking_lock 
			ON blocked_lock.locktype = blocking_lock.locktype
			AND blocked_lock.database = blocking_lock.database
			AND blocked_lock.relation = blocking_lock.relation
			AND blocked_lock.page = blocking_lock.page
			AND blocked_lock.tuple = blocking_lock.tuple
			AND blocked_lock.virtualxid = blocking_lock.virtualxid
			AND blocked_lock.transactionid = blocking_lock.transactionid
			AND blocked_lock.classid = blocking_lock.classid
			AND blocked_lock.objid = blocking_lock.objid
			AND blocked_lock.objsubid = blocking_lock.objsubid
			AND blocked_lock.pid != blocking_lock.pid
		JOIN pg_catalog.pg_stat_activity blocking ON blocking_lock.pid = blocking.pid
		WHERE NOT blocked_lock.granted
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	
	var transactions []models.Transaction
	trxMap := make(map[int64]*models.Transaction)
	
	type WaitRelation struct {
		RequestingTrxID int64
		BlockingTrxID   int64
	}
	var waitRelations []WaitRelation
	
	for rows.Next() {
		var (
			blockedPID, blockingPID int
			blockedUser, blockedQuery, blockingUser, blockingQuery string
			blockedStart, blockingStart time.Time
			blockedState, blockingState string
		)
		
		err := rows.Scan(
			&blockedPID, &blockedUser, &blockedQuery, &blockedStart, &blockedState,
			&blockingPID, &blockingUser, &blockingQuery, &blockingStart, &blockingState,
		)
		if err != nil {
			return nil, err
		}
		
		if _, ok := trxMap[int64(blockedPID)]; !ok {
			trxType := DetectTransactionType(blockedQuery)
			costScore := CalculateCostScore(0, 0, 0, time.Since(blockedStart).Seconds())
			killPriority := CalculateKillPriority(trxType, costScore, time.Since(blockedStart).Seconds())
			
			trxMap[int64(blockedPID)] = &models.Transaction{
				ID:              int64(blockedPID),
				User:            blockedUser,
				Info:            blockedQuery,
				StartTime:       blockedStart,
				State:           blockedState,
				TransactionType: trxType,
				CostScore:       costScore,
				KillPriority:    killPriority,
			}
		}
		
		if _, ok := trxMap[int64(blockingPID)]; !ok {
			trxType := DetectTransactionType(blockingQuery)
			costScore := CalculateCostScore(0, 0, 0, time.Since(blockingStart).Seconds())
			killPriority := CalculateKillPriority(trxType, costScore, time.Since(blockingStart).Seconds())
			
			trxMap[int64(blockingPID)] = &models.Transaction{
				ID:              int64(blockingPID),
				User:            blockingUser,
				Info:            blockingQuery,
				StartTime:       blockingStart,
				State:           blockingState,
				TransactionType: trxType,
				CostScore:       costScore,
				KillPriority:    killPriority,
			}
		}
		
		waitRelations = append(waitRelations, WaitRelation{
			RequestingTrxID: int64(blockedPID),
			BlockingTrxID:   int64(blockingPID),
		})
	}
	
	for _, trx := range trxMap {
		transactions = append(transactions, *trx)
	}
	
	for _, wr := range waitRelations {
		if trx, ok := trxMap[wr.RequestingTrxID]; ok {
			trx.WaitLockID = fmt.Sprintf("%d", wr.BlockingTrxID)
		}
	}
	
	deadlocks := detectDeadlockCyclePG(transactions, waitRelations)
	
	return deadlocks, nil
}

func (p *PostgreSQLConnector) DetectDeadlocks() ([]models.Deadlock, error) {
	return p.queryDeadlockMonitor()
}

func (p *PostgreSQLConnector) GetTransactions() ([]models.Transaction, error) {
	rows, err := p.db.Query(`
		SELECT 
			pid, usename, datname, query, state, query_start
		FROM pg_stat_activity
		WHERE state != 'idle'
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	
	var transactions []models.Transaction
	
	for rows.Next() {
		var trx models.Transaction
		var queryStart time.Time
		
		err := rows.Scan(&trx.ID, &trx.User, &trx.DB, &trx.Info, &trx.State, &queryStart)
		if err != nil {
			return nil, err
		}
		
		trx.StartTime = queryStart
		trx.TransactionType = DetectTransactionType(trx.Info)
		transactions = append(transactions, trx)
	}
	
	return transactions, nil
}

func (p *PostgreSQLConnector) KillTransaction(transactionID int64) error {
	_, err := p.db.Exec(fmt.Sprintf("SELECT pg_terminate_backend(%d)", transactionID))
	return err
}

func DetectTransactionType(sql string) models.TransactionType {
	sqlUpper := strings.ToUpper(strings.TrimSpace(sql))
	
	if sqlUpper == "" {
		return models.TransactionTypeUnknown
	}
	
	ddlPatterns := []string{
		"CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME",
		"ADD COLUMN", "DROP COLUMN", "ALTER TABLE", "CREATE INDEX", "DROP INDEX",
	}
	for _, pattern := range ddlPatterns {
		if strings.Contains(sqlUpper, pattern) {
			return models.TransactionTypeDDL
		}
	}
	
	writePatterns := []string{
		"INSERT", "UPDATE", "DELETE", "REPLACE", "UPSERT",
		"MERGE", "WRITE",
	}
	for _, pattern := range writePatterns {
		if strings.HasPrefix(sqlUpper, pattern) || strings.Contains(sqlUpper, " "+pattern+" ") {
			return models.TransactionTypeWrite
		}
	}
	
	readPatterns := []string{
		"SELECT", "SHOW", "DESCRIBE", "EXPLAIN", "WITH",
	}
	for _, pattern := range readPatterns {
		if strings.HasPrefix(sqlUpper, pattern) {
			return models.TransactionTypeRead
		}
	}
	
	return models.TransactionTypeUnknown
}

func CalculateCostScore(rowsModified, rowsLocked, lockMemoryBytes int, durationSeconds float64) int {
	score := 0
	
	score += rowsModified * 10
	
	score += rowsLocked * 2
	
	score += lockMemoryBytes / 1024
	
	score += int(durationSeconds) * 5
	
	if score > 10000 {
		score = 10000
	}
	
	return score
}

func CalculateKillPriority(trxType models.TransactionType, costScore int, durationSeconds float64) int {
	priority := 0
	
	switch trxType {
	case models.TransactionTypeRead:
		priority += 100
	case models.TransactionTypeWrite:
		priority += 50
	case models.TransactionTypeDDL:
		priority += 10
	default:
		priority += 30
	}
	
	if costScore < 100 {
		priority += 100
	} else if costScore < 500 {
		priority += 70
	} else if costScore < 1000 {
		priority += 40
	} else if costScore < 5000 {
		priority += 20
	} else {
		priority -= 20
	}
	
	if durationSeconds < 10 {
		priority += 50
	} else if durationSeconds < 60 {
		priority += 30
	} else if durationSeconds < 300 {
		priority += 10
	}
	
	if priority > 200 {
		priority = 200
	}
	if priority < 0 {
		priority = 0
	}
	
	return priority
}

func CalculateSeverity(deadlock *models.Deadlock) models.SeverityLevel {
	maxCost := 0
	hasDDL := false
	hasLongRunning := false
	
	for _, trx := range deadlock.Transactions {
		if trx.CostScore > maxCost {
			maxCost = trx.CostScore
		}
		if trx.TransactionType == models.TransactionTypeDDL {
			hasDDL = true
		}
		if time.Since(trx.StartTime).Seconds() > 300 {
			hasLongRunning = true
		}
	}
	
	if hasDDL || maxCost > 5000 || hasLongRunning {
		return models.SeverityCritical
	}
	
	if len(deadlock.Transactions) > 3 || maxCost > 2000 {
		return models.SeverityHigh
	}
	
	if maxCost > 500 {
		return models.SeverityMedium
	}
	
	return models.SeverityLow
}

type WaitRelation struct {
	RequestingTrxID string
	BlockingTrxID   string
}

func detectDeadlockCycle(transactions []models.Transaction, waitRelations []WaitRelation) []models.Deadlock {
	graph := make(map[string][]string)
	trxMap := make(map[string]models.Transaction)
	
	for _, trx := range transactions {
		trxMap[trx.TrxID] = trx
	}
	
	for _, wr := range waitRelations {
		graph[wr.RequestingTrxID] = append(graph[wr.RequestingTrxID], wr.BlockingTrxID)
	}
	
	visited := make(map[string]bool)
	recStack := make(map[string]bool)
	var deadlocks []models.Deadlock
	
	var dfs func(string, []string)
	dfs = func(node string, path []string) {
		visited[node] = true
		recStack[node] = true
		path = append(path, node)
		
		for _, neighbor := range graph[node] {
			if !visited[neighbor] {
				dfs(neighbor, path)
			} else if recStack[neighbor] {
				cycleStart := -1
				for i, p := range path {
					if p == neighbor {
						cycleStart = i
						break
					}
				}
				
				if cycleStart != -1 {
					cycle := path[cycleStart:]
					cycle = append(cycle, neighbor)
					
					var deadlockTrxs []models.Transaction
					for _, trxID := range cycle {
						if trx, ok := trxMap[trxID]; ok {
							deadlockTrxs = append(deadlockTrxs, trx)
						}
					}
					
					if len(deadlockTrxs) >= 2 {
						now := time.Now()
						deadlock := models.Deadlock{
							ID:           fmt.Sprintf("dl_%d", now.UnixNano()),
							DetectedAt:   now,
							Source:       "polling",
							Transactions: deadlockTrxs,
							WaitForGraph: buildWaitForGraph(cycle),
						}
						deadlock.Severity = CalculateSeverity(&deadlock)
						deadlocks = append(deadlocks, deadlock)
					}
				}
			}
		}
		
		recStack[node] = false
	}
	
	for node := range graph {
		if !visited[node] {
			dfs(node, []string{})
		}
	}
	
	return deadlocks
}

func detectDeadlockCyclePG(transactions []models.Transaction, waitRelations []struct{RequestingTrxID, BlockingTrxID int64}) []models.Deadlock {
	graph := make(map[int64][]int64)
	trxMap := make(map[int64]models.Transaction)
	
	for _, trx := range transactions {
		trxMap[trx.ID] = trx
	}
	
	for _, wr := range waitRelations {
		graph[wr.RequestingTrxID] = append(graph[wr.RequestingTrxID], wr.BlockingTrxID)
	}
	
	visited := make(map[int64]bool)
	recStack := make(map[int64]bool)
	var deadlocks []models.Deadlock
	
	var dfs func(int64, []int64)
	dfs = func(node int64, path []int64) {
		visited[node] = true
		recStack[node] = true
		path = append(path, node)
		
		for _, neighbor := range graph[node] {
			if !visited[neighbor] {
				dfs(neighbor, path)
			} else if recStack[neighbor] {
				cycleStart := -1
				for i, p := range path {
					if p == neighbor {
						cycleStart = i
						break
					}
				}
				
				if cycleStart != -1 {
					cycle := path[cycleStart:]
					cycle = append(cycle, neighbor)
					
					var deadlockTrxs []models.Transaction
					for _, trxID := range cycle {
						if trx, ok := trxMap[trxID]; ok {
							deadlockTrxs = append(deadlockTrxs, trx)
						}
					}
					
					if len(deadlockTrxs) >= 2 {
						waitForGraph := buildWaitForGraphPG(cycle)
						now := time.Now()
						
						deadlock := models.Deadlock{
							ID:           fmt.Sprintf("dl_%d", now.UnixNano()),
							DetectedAt:   now,
							Source:       "polling",
							Transactions: deadlockTrxs,
							WaitForGraph: waitForGraph,
						}
						deadlock.Severity = CalculateSeverity(&deadlock)
						deadlocks = append(deadlocks, deadlock)
					}
				}
			}
		}
		
		recStack[node] = false
	}
	
	for node := range graph {
		if !visited[node] {
			dfs(node, []int64{})
		}
	}
	
	return deadlocks
}

func buildWaitForGraph(cycle []string) string {
	var builder strings.Builder
	for i := 0; i < len(cycle)-1; i++ {
		builder.WriteString(fmt.Sprintf("%s -> %s; ", cycle[i], cycle[i+1]))
	}
	return builder.String()
}

func buildWaitForGraphPG(cycle []int64) string {
	var builder strings.Builder
	for i := 0; i < len(cycle)-1; i++ {
		builder.WriteString(fmt.Sprintf("%d -> %d; ", cycle[i], cycle[i+1]))
	}
	return builder.String()
}

func parseUint32(s string) uint32 {
	var result uint32
	fmt.Sscanf(s, "%d", &result)
	return result
}
