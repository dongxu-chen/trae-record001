package models

import (
	"time"
)

type TransactionType string

const (
	TransactionTypeRead  TransactionType = "READ"
	TransactionTypeWrite TransactionType = "WRITE"
	TransactionTypeDDL   TransactionType = "DDL"
	TransactionTypeUnknown TransactionType = "UNKNOWN"
)

type SeverityLevel string

const (
	SeverityCritical SeverityLevel = "CRITICAL"
	SeverityHigh     SeverityLevel = "HIGH"
	SeverityMedium   SeverityLevel = "MEDIUM"
	SeverityLow      SeverityLevel = "LOW"
)

type Transaction struct {
	ID               int64           `json:"id"`
	TrxID            string          `json:"trx_id"`
	ThreadID         uint32          `json:"thread_id"`
	ProcessID        uint32          `json:"process_id"`
	User             string          `json:"user"`
	Host             string          `json:"host"`
	DB               string          `json:"db"`
	Command          string          `json:"command"`
	Time             int             `json:"time"`
	State            string          `json:"state"`
	Info             string          `json:"info"`
	LockWaitTime     int             `json:"lock_wait_time"`
	LockedTables     string          `json:"locked_tables"`
	WaitLockID       string          `json:"wait_lock_id"`
	HoldLockID       string          `json:"hold_lock_id"`
	StartTime        time.Time       `json:"start_time"`
	TransactionType  TransactionType `json:"transaction_type"`
	KillPriority     int             `json:"kill_priority"`
	CostScore        int             `json:"cost_score"`
	RowsModified     int             `json:"rows_modified"`
	RowsLocked       int             `json:"rows_locked"`
	LockMemoryBytes  int             `json:"lock_memory_bytes"`
}

type Deadlock struct {
	ID               string            `json:"id"`
	DetectedAt       time.Time         `json:"detected_at"`
	Source           string            `json:"source"`
	Transactions     []Transaction     `json:"transactions"`
	WaitForGraph     string            `json:"wait_for_graph"`
	VictimSelected   int64             `json:"victim_selected"`
	ResolutionType   string            `json:"resolution_type"`
	ResolvedAt       *time.Time        `json:"resolved_at,omitempty"`
	ImpactAssessment *ImpactAssessment `json:"impact_assessment,omitempty"`
	Severity         SeverityLevel     `json:"severity"`
	DetectionLatencyMs int64           `json:"detection_latency_ms"`
}

type ImpactAssessment struct {
	AffectedRows      int             `json:"affected_rows"`
	RollbackTime      string          `json:"rollback_time"`
	QueriesAffected   []string        `json:"queries_affected"`
	BusinessImpact    string          `json:"business_impact"`
	Recommendation    string          `json:"recommendation"`
	TransactionType   TransactionType `json:"transaction_type"`
	Severity          SeverityLevel   `json:"severity"`
	CostScore         int             `json:"cost_score"`
}

type Rule struct {
	ID          string        `json:"id"`
	Name        string        `json:"name"`
	Description string        `json:"description"`
	Enabled     bool          `json:"enabled"`
	Priority    int           `json:"priority"`
	Condition   RuleCondition `json:"condition"`
	Action      RuleAction    `json:"action"`
}

type RuleCondition struct {
	MinTransactionTime int               `json:"min_transaction_time"`
	MinAffectedRows    int               `json:"min_affected_rows"`
	Users              []string          `json:"users"`
	Databases          []string          `json:"databases"`
	QueryPatterns      []string          `json:"query_patterns"`
	TransactionTypes   []TransactionType `json:"transaction_types"`
	MinCostScore       int               `json:"min_cost_score"`
	SeverityLevels     []SeverityLevel   `json:"severity_levels"`
}

type RuleAction struct {
	KillTransaction bool   `json:"kill_transaction"`
	LogOnly         bool   `json:"log_only"`
	Notify          bool   `json:"notify"`
	Message         string `json:"message"`
	PriorityBoost   int    `json:"priority_boost"`
}

type ResolutionHistory struct {
	ID              string        `json:"id"`
	DeadlockID      string        `json:"deadlock_id"`
	Timestamp       time.Time     `json:"timestamp"`
	Action          string        `json:"action"`
	TransactionID   int64         `json:"transaction_id"`
	TransactionInfo string        `json:"transaction_info"`
	Success         bool          `json:"success"`
	ErrorMessage    string        `json:"error_message,omitempty"`
	CostScore       int           `json:"cost_score"`
	TransactionType TransactionType `json:"transaction_type"`
}

type Statistics struct {
	TotalDeadlocks      int        `json:"total_deadlocks"`
	ResolvedDeadlocks   int        `json:"resolved_deadlocks"`
	AutoKilledCount     int        `json:"auto_killed_count"`
	ManualKilledCount   int        `json:"manual_killed_count"`
	AvgResolutionTime   string     `json:"avg_resolution_time"`
	AvgDetectionLatency string     `json:"avg_detection_latency"`
	TopDeadlockUsers    []KV       `json:"top_deadlock_users"`
	TopDeadlockTables   []KV       `json:"top_deadlock_tables"`
	DeadlocksByHour     []TimeData `json:"deadlocks_by_hour"`
	DeadlocksByType     []KV       `json:"deadlocks_by_type"`
	DeadlocksBySeverity []KV       `json:"deadlocks_by_severity"`
}

type KV struct {
	Key   string `json:"key"`
	Value int    `json:"value"`
}

type TimeData struct {
	Time  string `json:"time"`
	Count int    `json:"count"`
}

type DeadlockLogEvent struct {
	Timestamp    time.Time `json:"timestamp"`
	LogEntry     string    `json:"log_entry"`
	DeadlockID   string    `json:"deadlock_id"`
	Source       string    `json:"source"`
	RawData      string    `json:"raw_data"`
}

type SQLPatternType string

const (
	PatternMissingIndex    SQLPatternType = "MISSING_INDEX"
	PatternLongTransaction SQLPatternType = "LONG_TRANSACTION"
	PatternTableOrder      SQLPatternType = "TABLE_ORDER"
	PatternSelectForUpdate SQLPatternType = "SELECT_FOR_UPDATE"
	PatternBatchOperation  SQLPatternType = "BATCH_OPERATION"
	PatternUnindexedJoin   SQLPatternType = "UNINDEXED_JOIN"
)

type PreventionRecommendation struct {
	ID               string          `json:"id"`
	DeadlockID       string          `json:"deadlock_id"`
	DetectedAt       time.Time       `json:"detected_at"`
	SQLPattern       SQLPatternType  `json:"sql_pattern"`
	PatternDesc      string          `json:"pattern_description"`
	SQLStatement     string          `json:"sql_statement"`
	ProblemAnalysis  string          `json:"problem_analysis"`
	OptimizationTips []string        `json:"optimization_tips"`
	ExpectedBenefit  string          `json:"expected_benefit"`
	Complexity       string          `json:"complexity"`
	Priority         int             `json:"priority"`
	Resolved         bool            `json:"resolved"`
	ResolvedAt       *time.Time      `json:"resolved_at,omitempty"`
	RelatedTables    []string        `json:"related_tables"`
	RelatedQueries   []string        `json:"related_queries"`
}

type SimulationScenario struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	Type        string    `json:"type"`
	DBType      string    `json:"db_type"`
	SetupSQL    []string  `json:"setup_sql"`
	DeadlockSQL []string  `json:"deadlock_sql"`
	ExpectedResult string `json:"expected_result"`
	Difficulty  string    `json:"difficulty"`
	Tags        []string  `json:"tags"`
	CreatedAt   time.Time `json:"created_at"`
}

type SimulationResult struct {
	ID           string    `json:"id"`
	ScenarioID   string    `json:"scenario_id"`
	ScenarioName string    `json:"scenario_name"`
	StartedAt    time.Time `json:"started_at"`
	CompletedAt  *time.Time `json:"completed_at,omitempty"`
	Status       string    `json:"status"`
	DeadlockDetected bool   `json:"deadlock_detected"`
	DeadlockID   string    `json:"deadlock_id,omitempty"`
	Transactions []Transaction `json:"transactions,omitempty"`
	RuleApplied  string    `json:"rule_applied,omitempty"`
	VictimKilled int64     `json:"victim_killed,omitempty"`
	ResolutionTimeMs int64 `json:"resolution_time_ms,omitempty"`
	Success      bool      `json:"success"`
	ErrorMessage string    `json:"error_message,omitempty"`
	KillStrategy string    `json:"kill_strategy"`
}

type AuditLog struct {
	ID             string          `json:"id"`
	Timestamp      time.Time       `json:"timestamp"`
	Action         string          `json:"action"`
	DeadlockID     string          `json:"deadlock_id"`
	TransactionID  int64           `json:"transaction_id"`
	TransactionInfo string         `json:"transaction_info"`
	TransactionType TransactionType `json:"transaction_type"`
	User           string          `json:"user"`
	Operator       string          `json:"operator"`
	Source         string          `json:"source"`
	Strategy       string          `json:"strategy"`
	RuleApplied    string          `json:"rule_applied,omitempty"`
	CostScore      int             `json:"cost_score"`
	KillPriority   int             `json:"kill_priority"`
	BusinessImpact string          `json:"business_impact"`
	RollbackTime   string          `json:"rollback_time"`
	QueriesAffected []string       `json:"queries_affected"`
	RelatedTickets []string        `json:"related_tickets,omitempty"`
	Success        bool            `json:"success"`
	ErrorMessage   string          `json:"error_message,omitempty"`
	ClientIP       string          `json:"client_ip,omitempty"`
	UserAgent      string          `json:"user_agent,omitempty"`
}

type SQLPatternAnalysis struct {
	Pattern     SQLPatternType `json:"pattern"`
	Count       int            `json:"count"`
	Description string         `json:"description"`
	Severity    SeverityLevel  `json:"severity"`
	Tables      []string       `json:"tables"`
	ExampleSQL  string         `json:"example_sql"`
}

type PreventionStatistics struct {
	TotalRecommendations int                 `json:"total_recommendations"`
	ResolvedCount        int                 `json:"resolved_count"`
	PatternDistribution  []SQLPatternAnalysis `json:"pattern_distribution"`
	TopTables            []KV                `json:"top_tables"`
	AvgResolutionTime    string              `json:"avg_resolution_time"`
}
