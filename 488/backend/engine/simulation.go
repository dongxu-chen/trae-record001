package engine

import (
	"deadlock-resolver/models"
	"fmt"
	"sync"
	"time"
)

type SandboxEngine struct {
	mu              sync.RWMutex
	scenarios       []models.SimulationScenario
	results         []models.SimulationResult
	detector        *DeadlockDetector
	runningScenarios map[string]*SimulationExecution
}

type SimulationExecution struct {
	ScenarioID  string
	StartedAt   time.Time
	Status      string
	DeadlockID  string
	Completed   chan bool
}

func NewSandboxEngine(detector *DeadlockDetector) *SandboxEngine {
	se := &SandboxEngine{
		scenarios:        make([]models.SimulationScenario, 0),
		results:          make([]models.SimulationResult, 0),
		detector:         detector,
		runningScenarios: make(map[string]*SimulationExecution),
	}
	se.initDefaultScenarios()
	return se
}

func (se *SandboxEngine) initDefaultScenarios() {
	defaultScenarios := []models.SimulationScenario{
		{
			ID:          "scn_classic_rowlock",
			Name:        "经典行锁死锁",
			Description: "两个事务按相反顺序更新两行数据",
			Type:        "ROW_LOCK",
			DBType:      "MySQL",
			SetupSQL: []string{
				"CREATE TABLE IF NOT EXISTS accounts (id INT PRIMARY KEY, balance DECIMAL(10,2))",
				"INSERT INTO accounts VALUES (1, 1000.00), (2, 2000.00)",
			},
			DeadlockSQL: []string{
				"-- 事务1: 先更新id=1, 再更新id=2",
				"START TRANSACTION",
				"UPDATE accounts SET balance = balance - 100 WHERE id = 1",
				"SELECT SLEEP(1)",
				"UPDATE accounts SET balance = balance + 100 WHERE id = 2",
				"COMMIT",
				"-- 事务2: 先更新id=2, 再更新id=1",
				"START TRANSACTION",
				"UPDATE accounts SET balance = balance - 50 WHERE id = 2",
				"SELECT SLEEP(1)",
				"UPDATE accounts SET balance = balance + 50 WHERE id = 1",
				"COMMIT",
			},
			ExpectedResult: "两个事务相互等待对方持有的行锁，形成死锁",
			Difficulty:     "EASY",
			Tags:           []string{"row-lock", "ordering", "classic"},
			CreatedAt:      time.Now(),
		},
		{
			ID:          "scn_gap_lock",
			Name:        "Gap Lock死锁",
			Description: "InnoDB Gap Lock导致的范围锁死锁",
			Type:        "GAP_LOCK",
			DBType:      "MySQL",
			SetupSQL: []string{
				"CREATE TABLE IF NOT EXISTS orders (id INT AUTO_INCREMENT PRIMARY KEY, status VARCHAR(20), amount DECIMAL(10,2))",
				"INSERT INTO orders (status, amount) VALUES ('PENDING', 100.00), ('PENDING', 200.00)",
			},
			DeadlockSQL: []string{
				"-- 事务1: 删除范围内记录",
				"START TRANSACTION",
				"DELETE FROM orders WHERE status = 'PENDING'",
				"SELECT SLEEP(1)",
				"INSERT INTO orders (status, amount) VALUES ('PENDING', 300.00)",
				"COMMIT",
				"-- 事务2: 同范围操作",
				"START TRANSACTION",
				"DELETE FROM orders WHERE status = 'PENDING'",
				"SELECT SLEEP(1)",
				"INSERT INTO orders (status, amount) VALUES ('PENDING', 400.00)",
				"COMMIT",
			},
			ExpectedResult: "两个事务都持有gap lock，又等待对方的gap lock",
			Difficulty:     "MEDIUM",
			Tags:           []string{"gap-lock", "innodb", "delete-insert"},
			CreatedAt:      time.Now(),
		},
		{
			ID:          "scn_select_for_update",
			Name:        "SELECT FOR UPDATE死锁",
			Description: "使用SELECT FOR UPDATE但顺序不一致导致死锁",
			Type:        "SELECT_FOR_UPDATE",
			DBType:      "MySQL",
			SetupSQL: []string{
				"CREATE TABLE IF NOT EXISTS inventory (id INT PRIMARY KEY, stock INT, name VARCHAR(100))",
				"INSERT INTO inventory VALUES (1, 100, 'Product A'), (2, 200, 'Product B')",
			},
			DeadlockSQL: []string{
				"-- 事务1: 锁定顺序1->2",
				"START TRANSACTION",
				"SELECT * FROM inventory WHERE id = 1 FOR UPDATE",
				"SELECT SLEEP(0.5)",
				"SELECT * FROM inventory WHERE id = 2 FOR UPDATE",
				"COMMIT",
				"-- 事务2: 锁定顺序2->1",
				"START TRANSACTION",
				"SELECT * FROM inventory WHERE id = 2 FOR UPDATE",
				"SELECT SLEEP(0.5)",
				"SELECT * FROM inventory WHERE id = 1 FOR UPDATE",
				"COMMIT",
			},
			ExpectedResult: "两个事务按相反顺序锁定记录，形成死锁",
			Difficulty:     "EASY",
			Tags:           []string{"select-for-update", "ordering", "pessimistic-lock"},
			CreatedAt:      time.Now(),
		},
		{
			ID:          "scn_ddl_mix",
			Name:        "DDL与DML混合死锁",
			Description: "DDL操作与DML操作混合导致的死锁",
			Type:        "DDL_MIX",
			DBType:      "MySQL",
			SetupSQL: []string{
				"CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY, name VARCHAR(100), email VARCHAR(100))",
				"INSERT INTO users VALUES (1, 'user1', 'user1@test.com'), (2, 'user2', 'user2@test.com')",
			},
			DeadlockSQL: []string{
				"-- 事务1: 先DML后DDL",
				"START TRANSACTION",
				"UPDATE users SET name = 'new1' WHERE id = 1",
				"SELECT SLEEP(0.5)",
				"ALTER TABLE users ADD COLUMN phone VARCHAR(20)",
				"COMMIT",
				"-- 事务2: 先DDL后DML",
				"START TRANSACTION",
				"ALTER TABLE users ADD COLUMN address VARCHAR(200)",
				"SELECT SLEEP(0.5)",
				"UPDATE users SET name = 'new2' WHERE id = 2",
				"COMMIT",
			},
			ExpectedResult: "DDL需要元数据锁，与DML持有的锁相互等待",
			Difficulty:     "HARD",
			Tags:           []string{"ddl", "metadata-lock", "alter-table"},
			CreatedAt:      time.Now(),
		},
		{
			ID:          "scn_three_way",
			Name:        "三路死锁",
			Description: "三个事务形成的循环等待链",
			Type:        "MULTI_WAY",
			DBType:      "MySQL",
			SetupSQL: []string{
				"CREATE TABLE IF NOT EXISTS resources (id INT PRIMARY KEY, value VARCHAR(100))",
				"INSERT INTO resources VALUES (1, 'A'), (2, 'B'), (3, 'C')",
			},
			DeadlockSQL: []string{
				"-- 事务1: 锁定1, 等待2",
				"START TRANSACTION",
				"SELECT * FROM resources WHERE id = 1 FOR UPDATE",
				"SELECT SLEEP(0.3)",
				"SELECT * FROM resources WHERE id = 2 FOR UPDATE",
				"COMMIT",
				"-- 事务2: 锁定2, 等待3",
				"START TRANSACTION",
				"SELECT * FROM resources WHERE id = 2 FOR UPDATE",
				"SELECT SLEEP(0.3)",
				"SELECT * FROM resources WHERE id = 3 FOR UPDATE",
				"COMMIT",
				"-- 事务3: 锁定3, 等待1",
				"START TRANSACTION",
				"SELECT * FROM resources WHERE id = 3 FOR UPDATE",
				"SELECT SLEEP(0.3)",
				"SELECT * FROM resources WHERE id = 1 FOR UPDATE",
				"COMMIT",
			},
			ExpectedResult: "三个事务形成1→2→3→1的循环等待",
			Difficulty:     "MEDIUM",
			Tags:           []string{"multi-way", "three-transaction", "cycle"},
			CreatedAt:      time.Now(),
		},
	}

	se.scenarios = defaultScenarios
}

func (se *SandboxEngine) GetScenarios() []models.SimulationScenario {
	se.mu.RLock()
	defer se.mu.RUnlock()
	return se.scenarios
}

func (se *SandboxEngine) GetScenario(id string) (*models.SimulationScenario, error) {
	se.mu.RLock()
	defer se.mu.RUnlock()

	for _, s := range se.scenarios {
		if s.ID == id {
			return &s, nil
		}
	}
	return nil, fmt.Errorf("scenario not found")
}

func (se *SandboxEngine) AddScenario(scenario models.SimulationScenario) {
	se.mu.Lock()
	defer se.mu.Unlock()

	scenario.ID = fmt.Sprintf("scn_%d", time.Now().UnixNano())
	scenario.CreatedAt = time.Now()
	se.scenarios = append(se.scenarios, scenario)
}

func (se *SandboxEngine) DeleteScenario(id string) error {
	se.mu.Lock()
	defer se.mu.Unlock()

	for i, s := range se.scenarios {
		if s.ID == id {
			se.scenarios = append(se.scenarios[:i], se.scenarios[i+1:]...)
			return nil
		}
	}
	return fmt.Errorf("scenario not found")
}

func (se *SandboxEngine) RunSimulation(scenarioID string, killStrategy string) (*models.SimulationResult, error) {
	scenario, err := se.GetScenario(scenarioID)
	if err != nil {
		return nil, err
	}

	result := &models.SimulationResult{
		ID:           fmt.Sprintf("sim_%d", time.Now().UnixNano()),
		ScenarioID:   scenario.ID,
		ScenarioName: scenario.Name,
		StartedAt:    time.Now(),
		Status:       "RUNNING",
		KillStrategy: killStrategy,
	}

	se.mu.Lock()
	se.results = append(se.results, *result)
	se.runningScenarios[result.ID] = &SimulationExecution{
		ScenarioID: scenarioID,
		StartedAt:  time.Now(),
		Status:     "RUNNING",
		Completed:  make(chan bool),
	}
	se.mu.Unlock()

	go se.executeSimulation(result, scenario, killStrategy)

	return result, nil
}

func (se *SandboxEngine) executeSimulation(result *models.SimulationResult, scenario *models.SimulationScenario, killStrategy string) {
	deadlockDetected := false
	var detectedDeadlock *models.Deadlock

	go func() {
		time.Sleep(2 * time.Second)
		mockDeadlock := se.generateMockDeadlock(scenario)
		detectedDeadlock = &mockDeadlock
		deadlockDetected = true
	}()

	timeout := time.After(10 * time.Second)
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

loop:
	for {
		select {
		case <-timeout:
			result.Status = "TIMEOUT"
			result.Success = false
			result.ErrorMessage = "Simulation timeout - no deadlock detected"
			break loop
		case <-ticker.C:
			if deadlockDetected && detectedDeadlock != nil {
				result.DeadlockDetected = true
				result.DeadlockID = detectedDeadlock.ID
				result.Transactions = detectedDeadlock.Transactions

				startResolve := time.Now()
				victim, ruleApplied := se.detector.SelectVictim(detectedDeadlock, killStrategy)
				resolveTime := time.Since(startResolve).Milliseconds()

				if victim != nil {
					result.VictimKilled = victim.ID
					result.RuleApplied = ruleApplied
					result.ResolutionTimeMs = resolveTime
					result.Success = true
					result.Status = "COMPLETED"
				} else {
					result.Success = false
					result.ErrorMessage = "No victim selected by rule engine"
					result.Status = "FAILED"
				}
				break loop
			}
		}
	}

	now := time.Now()
	result.CompletedAt = &now

	se.mu.Lock()
	for i := range se.results {
		if se.results[i].ID == result.ID {
			se.results[i] = *result
		}
	}
	if exec, ok := se.runningScenarios[result.ID]; ok {
		close(exec.Completed)
		delete(se.runningScenarios, result.ID)
	}
	se.mu.Unlock()
}

func (se *SandboxEngine) generateMockDeadlock(scenario *models.SimulationScenario) models.Deadlock {
	var txType1, txType2 models.TransactionType
	switch scenario.Type {
	case "DDL_MIX":
		txType1 = models.TransactionTypeDDL
		txType2 = models.TransactionTypeWrite
	default:
		txType1 = models.TransactionTypeWrite
		txType2 = models.TransactionTypeWrite
	}

	tx1 := models.Transaction{
		ID:              1001,
		TrxID:           "trx_mock_001",
		ThreadID:        12345,
		User:            "test_user",
		Host:            "localhost",
		DB:              "test",
		Command:         "Query",
		Time:            15,
		State:           "Locked",
		Info:            scenario.DeadlockSQL[2],
		LockWaitTime:    5,
		LockedTables:    "accounts",
		WaitLockID:      "lock:2",
		HoldLockID:      "lock:1",
		StartTime:       time.Now().Add(-15 * time.Second),
		TransactionType: txType1,
		KillPriority:    80,
		CostScore:       500,
		RowsModified:    1,
		RowsLocked:      10,
		LockMemoryBytes: 1024,
	}

	tx2 := models.Transaction{
		ID:              1002,
		TrxID:           "trx_mock_002",
		ThreadID:        12346,
		User:            "test_user",
		Host:            "localhost",
		DB:              "test",
		Command:         "Query",
		Time:            12,
		State:           "Locked",
		Info:            scenario.DeadlockSQL[8],
		LockWaitTime:    3,
		LockedTables:    "accounts",
		WaitLockID:      "lock:1",
		HoldLockID:      "lock:2",
		StartTime:       time.Now().Add(-12 * time.Second),
		TransactionType: txType2,
		KillPriority:    120,
		CostScore:       1500,
		RowsModified:    1,
		RowsLocked:      10,
		LockMemoryBytes: 1024,
	}

	transactions := []models.Transaction{tx1, tx2}

	if scenario.Type == "MULTI_WAY" {
		tx3 := models.Transaction{
			ID:              1003,
			TrxID:           "trx_mock_003",
			ThreadID:        12347,
			User:            "test_user",
			Host:            "localhost",
			DB:              "test",
			Command:         "Query",
			Time:            10,
			State:           "Locked",
			Info:            "SELECT * FROM resources WHERE id = 1 FOR UPDATE",
			LockWaitTime:    2,
			LockedTables:    "resources",
			WaitLockID:      "lock:1",
			HoldLockID:      "lock:3",
			StartTime:       time.Now().Add(-10 * time.Second),
			TransactionType: models.TransactionTypeWrite,
			KillPriority:    90,
			CostScore:       800,
			RowsModified:    0,
			RowsLocked:      5,
			LockMemoryBytes: 512,
		}
		transactions = append(transactions, tx3)
	}

	severity := calculateSeverity(transactions)

	return models.Deadlock{
		ID:              fmt.Sprintf("dl_sandbox_%d", time.Now().UnixNano()),
		DetectedAt:      time.Now(),
		Source:          "SANDBOX",
		Transactions:    transactions,
		WaitForGraph:    "1001->1002->1001",
		VictimSelected:  0,
		ResolutionType:  "",
		Severity:        severity,
		DetectionLatencyMs: 0,
	}
}

func (se *SandboxEngine) GetResults(limit int) []models.SimulationResult {
	se.mu.RLock()
	defer se.mu.RUnlock()

	start := len(se.results) - limit
	if start < 0 {
		start = 0
	}
	return se.results[start:]
}

func (se *SandboxEngine) GetResult(id string) (*models.SimulationResult, error) {
	se.mu.RLock()
	defer se.mu.RUnlock()

	for _, r := range se.results {
		if r.ID == id {
			return &r, nil
		}
	}
	return nil, fmt.Errorf("result not found")
}

func (se *SandboxEngine) GetExecutionStatus(resultID string) (string, error) {
	se.mu.RLock()
	defer se.mu.RUnlock()

	if exec, ok := se.runningScenarios[resultID]; ok {
		return exec.Status, nil
	}

	for _, r := range se.results {
		if r.ID == resultID {
			return r.Status, nil
		}
	}

	return "", fmt.Errorf("execution not found")
}
