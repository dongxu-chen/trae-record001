package engine

import (
	"deadlock-resolver/models"
	"fmt"
	"regexp"
	"strings"
	"sync"
	"time"
)

type PreventionEngine struct {
	mu               sync.RWMutex
	recommendations  []models.PreventionRecommendation
	patternDetectors map[models.SQLPatternType]*SQLPatternDetector
}

type SQLPatternDetector struct {
	Pattern     models.SQLPatternType
	Description string
	Regex       *regexp.Regexp
	AnalyzeFunc func(sql string, tx models.Transaction) *models.PreventionRecommendation
}

func NewPreventionEngine() *PreventionEngine {
	pe := &PreventionEngine{
		recommendations:  make([]models.PreventionRecommendation, 0),
		patternDetectors: make(map[models.SQLPatternType]*SQLPatternDetector),
	}
	pe.registerPatternDetectors()
	return pe
}

func (pe *PreventionEngine) registerPatternDetectors() {
	pe.patternDetectors[models.PatternMissingIndex] = &SQLPatternDetector{
		Pattern:     models.PatternMissingIndex,
		Description: "缺少索引导致全表扫描，锁范围过大",
		Regex:       regexp.MustCompile(`(?i)(UPDATE|DELETE|SELECT)\s+.*\s+FROM\s+(\w+).*WHERE\s+`),
		AnalyzeFunc: pe.analyzeMissingIndex,
	}

	pe.patternDetectors[models.PatternLongTransaction] = &SQLPatternDetector{
		Pattern:     models.PatternLongTransaction,
		Description: "长事务持有锁时间过长",
		Regex:       regexp.MustCompile(`.*`),
		AnalyzeFunc: pe.analyzeLongTransaction,
	}

	pe.patternDetectors[models.PatternTableOrder] = &SQLPatternDetector{
		Pattern:     models.PatternTableOrder,
		Description: "表访问顺序不一致导致死锁",
		Regex:       regexp.MustCompile(`.*`),
		AnalyzeFunc: pe.analyzeTableOrder,
	}

	pe.patternDetectors[models.PatternSelectForUpdate] = &SQLPatternDetector{
		Pattern:     models.PatternSelectForUpdate,
		Description: "SELECT ... FOR UPDATE 使用不当",
		Regex:       regexp.MustCompile(`(?i)SELECT\s+.*\s+FOR\s+UPDATE`),
		AnalyzeFunc: pe.analyzeSelectForUpdate,
	}

	pe.patternDetectors[models.PatternBatchOperation] = &SQLPatternDetector{
		Pattern:     models.PatternBatchOperation,
		Description: "批量操作一次性锁定过多行",
		Regex:       regexp.MustCompile(`(?i)(UPDATE|DELETE)\s+.*\s+WHERE\s+.*(IN\s*\(|>|<|>=|<=)`),
		AnalyzeFunc: pe.analyzeBatchOperation,
	}

	pe.patternDetectors[models.PatternUnindexedJoin] = &SQLPatternDetector{
		Pattern:     models.PatternUnindexedJoin,
		Description: "JOIN条件缺少索引",
		Regex:       regexp.MustCompile(`(?i)JOIN\s+.*\s+ON\s+`),
		AnalyzeFunc: pe.analyzeUnindexedJoin,
	}
}

func (pe *PreventionEngine) AnalyzeDeadlock(deadlock models.Deadlock) []models.PreventionRecommendation {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	var recs []models.PreventionRecommendation

	for _, tx := range deadlock.Transactions {
		for _, detector := range pe.patternDetectors {
			if rec := detector.AnalyzeFunc(tx.Info, tx); rec != nil {
				rec.ID = fmt.Sprintf("rec_%d", time.Now().UnixNano())
				rec.DeadlockID = deadlock.ID
				rec.DetectedAt = time.Now()
				rec.RelatedTables = pe.extractTables(tx.Info)
				rec.RelatedQueries = []string{tx.Info}
				pe.recommendations = append(pe.recommendations, *rec)
				recs = append(recs, *rec)
			}
		}
	}

	return recs
}

func (pe *PreventionEngine) analyzeMissingIndex(sql string, tx models.Transaction) *models.PreventionRecommendation {
	if tx.RowsLocked > 100 && tx.RowsModified == 0 {
		return &models.PreventionRecommendation{
			SQLPattern:      models.PatternMissingIndex,
			PatternDesc:     "缺少索引导致全表扫描，锁定了过多不必要的行",
			SQLStatement:    sql,
			ProblemAnalysis: fmt.Sprintf("查询锁定了%d行，但只修改了%d行，可能缺少合适的索引导致全表扫描。", tx.RowsLocked, tx.RowsModified),
			OptimizationTips: []string{
				"分析查询执行计划，确认是否使用了索引",
				"为WHERE条件中的字段添加合适的索引",
				"考虑使用覆盖索引避免回表",
				"优化查询条件，减少扫描范围",
			},
			ExpectedBenefit: "减少锁范围90%以上，大幅降低死锁概率",
			Complexity:      "MEDIUM",
			Priority:        1,
		}
	}
	return nil
}

func (pe *PreventionEngine) analyzeLongTransaction(sql string, tx models.Transaction) *models.PreventionRecommendation {
	if tx.Time > 30 {
		return &models.PreventionRecommendation{
			SQLPattern:      models.PatternLongTransaction,
			PatternDesc:     "事务执行时间过长，持有锁时间超过30秒",
			SQLStatement:    sql,
			ProblemAnalysis: fmt.Sprintf("事务已执行%d秒，长时间持有锁会增加死锁风险并影响并发性能。", tx.Time),
			OptimizationTips: []string{
				"拆分大事务为多个小事务",
				"将不必要的操作移出事务范围",
				"优化查询性能，减少事务执行时间",
				"考虑设置合理的锁超时时间",
				"避免在事务中进行外部API调用或耗时操作",
			},
			ExpectedBenefit: "锁持有时间减少70%，并发性能提升3-5倍",
			Complexity:      "HIGH",
			Priority:        2,
		}
	}
	return nil
}

func (pe *PreventionEngine) analyzeTableOrder(sql string, tx models.Transaction) *models.PreventionRecommendation {
	tables := pe.extractTables(sql)
	if len(tables) >= 2 {
		return &models.PreventionRecommendation{
			SQLPattern:      models.PatternTableOrder,
			PatternDesc:     "多表操作可能存在访问顺序不一致问题",
			SQLStatement:    sql,
			ProblemAnalysis: fmt.Sprintf("事务访问了%d个表：%s。如果多个事务以不同顺序访问这些表，很容易发生死锁。", len(tables), strings.Join(tables, ", ")),
			OptimizationTips: []string{
				"规范所有事务的表访问顺序（如按表名排序）",
				"将跨表操作拆分为独立事务",
				"使用更短的锁粒度（如行锁而非表锁）",
				"考虑使用SELECT ... FOR UPDATE SKIP LOCKED",
			},
			ExpectedBenefit: "消除80%以上的死锁场景",
			Complexity:      "MEDIUM",
			Priority:        1,
		}
	}
	return nil
}

func (pe *PreventionEngine) analyzeSelectForUpdate(sql string, tx models.Transaction) *models.PreventionRecommendation {
	if strings.Contains(strings.ToUpper(sql), "FOR UPDATE") && !strings.Contains(strings.ToUpper(sql), "WHERE") {
		return &models.PreventionRecommendation{
			SQLPattern:      models.PatternSelectForUpdate,
			PatternDesc:     "SELECT FOR UPDATE 缺少WHERE条件，锁定全表",
			SQLStatement:    sql,
			ProblemAnalysis: "使用SELECT ... FOR UPDATE时缺少WHERE条件，会锁定整个表，严重影响并发性能并极易导致死锁。",
			OptimizationTips: []string{
				"添加精确的WHERE条件，只锁定需要的行",
				"考虑使用UPDATE ... WHERE直接更新而非先查后更",
				"如果业务允许，使用FOR UPDATE SKIP LOCKED",
				"评估是否真的需要悲观锁，考虑乐观锁方案",
			},
			ExpectedBenefit: "锁范围从全表缩小到指定行，并发提升10倍以上",
			Complexity:      "LOW",
			Priority:        1,
		}
	}
	if strings.Contains(strings.ToUpper(sql), "FOR UPDATE") && tx.Time > 10 {
		return &models.PreventionRecommendation{
			SQLPattern:      models.PatternSelectForUpdate,
			PatternDesc:     "SELECT FOR UPDATE 持有锁时间过长",
			SQLStatement:    sql,
			ProblemAnalysis: fmt.Sprintf("使用SELECT ... FOR UPDATE后，事务持有行锁已达%d秒，在此期间其他事务无法修改这些行。", tx.Time),
			OptimizationTips: []string{
				"缩小事务范围，在SELECT FOR UPDATE后立即执行UPDATE",
				"考虑使用NOWAIT选项避免等待",
				"评估是否可以使用乐观锁替代悲观锁",
				"设置合理的innodb_lock_wait_timeout",
			},
			ExpectedBenefit: "减少锁等待时间60%，死锁概率降低50%",
			Complexity:      "MEDIUM",
			Priority:        2,
		}
	}
	return nil
}

func (pe *PreventionEngine) analyzeBatchOperation(sql string, tx models.Transaction) *models.PreventionRecommendation {
	if tx.RowsModified > 1000 {
		return &models.PreventionRecommendation{
			SQLPattern:      models.PatternBatchOperation,
			PatternDesc:     "批量操作一次性修改过多行",
			SQLStatement:    sql,
			ProblemAnalysis: fmt.Sprintf("单条SQL修改了%d行，一次性锁定大量记录会导致锁冲突和死锁概率大幅上升。", tx.RowsModified),
			OptimizationTips: []string{
				"分批处理，每次修改100-500行",
				"使用LIMIT子句限制每次修改的行数",
				"在批次之间增加短暂延迟让其他事务有机会执行",
				"考虑在业务低峰期执行批量操作",
				"评估是否可以使用ON DUPLICATE KEY UPDATE等原子操作",
			},
			ExpectedBenefit: "锁冲突减少90%，死锁基本消除",
			Complexity:      "MEDIUM",
			Priority:        2,
		}
	}
	return nil
}

func (pe *PreventionEngine) analyzeUnindexedJoin(sql string, tx models.Transaction) *models.PreventionRecommendation {
	if strings.Contains(strings.ToUpper(sql), "JOIN") && tx.LockMemoryBytes > 1024*1024 {
		return &models.PreventionRecommendation{
			SQLPattern:      models.PatternUnindexedJoin,
			PatternDesc:     "JOIN查询缺少索引，使用临时表或文件排序",
			SQLStatement:    sql,
			ProblemAnalysis: fmt.Sprintf("JOIN查询消耗了%d KB锁内存，可能缺少连接条件索引导致扫描大量行。", tx.LockMemoryBytes/1024),
			OptimizationTips: []string{
				"为JOIN条件中的字段添加索引",
				"确保JOIN字段的数据类型一致，避免隐式转换",
				"使用EXPLAIN分析执行计划，检查是否有Using filesort或Using temporary",
				"考虑适当反范式设计减少JOIN",
			},
			ExpectedBenefit: "查询性能提升5-10倍，锁范围大幅减少",
			Complexity:      "MEDIUM",
			Priority:        2,
		}
	}
	return nil
}

func (pe *PreventionEngine) extractTables(sql string) []string {
	var tables []string
	fromRegex := regexp.MustCompile(`(?i)FROM\s+([` + "`" + `"\w]+)`)
	joinRegex := regexp.MustCompile(`(?i)JOIN\s+([` + "`" + `"\w]+)`)
	updateRegex := regexp.MustCompile(`(?i)UPDATE\s+([` + "`" + `"\w]+)`)
	deleteRegex := regexp.MustCompile(`(?i)DELETE\s+FROM\s+([` + "`" + `"\w]+)`)
	insertRegex := regexp.MustCompile(`(?i)INSERT\s+INTO\s+([` + "`" + `"\w]+)`)

	allRegex := []*regexp.Regexp{fromRegex, joinRegex, updateRegex, deleteRegex, insertRegex}
	seen := make(map[string]bool)

	for _, re := range allRegex {
		matches := re.FindAllStringSubmatch(sql, -1)
		for _, match := range matches {
			if len(match) > 1 {
				table := strings.Trim(match[1], "`\"")
				if !seen[table] {
					seen[table] = true
					tables = append(tables, table)
				}
			}
		}
	}

	return tables
}

func (pe *PreventionEngine) GetRecommendations(limit int) []models.PreventionRecommendation {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	start := len(pe.recommendations) - limit
	if start < 0 {
		start = 0
	}
	return pe.recommendations[start:]
}

func (pe *PreventionEngine) GetRecommendation(id string) (*models.PreventionRecommendation, error) {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	for _, rec := range pe.recommendations {
		if rec.ID == id {
			return &rec, nil
		}
	}
	return nil, fmt.Errorf("recommendation not found")
}

func (pe *PreventionEngine) MarkResolved(id string) error {
	pe.mu.Lock()
	defer pe.mu.Unlock()

	now := time.Now()
	for i := range pe.recommendations {
		if pe.recommendations[i].ID == id {
			pe.recommendations[i].Resolved = true
			pe.recommendations[i].ResolvedAt = &now
			return nil
		}
	}
	return fmt.Errorf("recommendation not found")
}

func (pe *PreventionEngine) GetStatistics() models.PreventionStatistics {
	pe.mu.RLock()
	defer pe.mu.RUnlock()

	patternCount := make(map[models.SQLPatternType]int)
	tableCount := make(map[string]int)
	resolvedCount := 0
	totalTime := int64(0)

	for _, rec := range pe.recommendations {
		patternCount[rec.SQLPattern]++
		for _, table := range rec.RelatedTables {
			tableCount[table]++
		}
		if rec.Resolved && rec.ResolvedAt != nil {
			resolvedCount++
			totalTime += rec.ResolvedAt.Sub(rec.DetectedAt).Milliseconds()
		}
	}

	patternDist := make([]models.SQLPatternAnalysis, 0)
	for pattern, count := range patternCount {
		desc := ""
		severity := models.SeverityMedium
		switch pattern {
		case models.PatternMissingIndex:
			desc = "缺少索引导致全表扫描"
			severity = models.SeverityHigh
		case models.PatternLongTransaction:
			desc = "长事务持有锁时间过长"
			severity = models.SeverityHigh
		case models.PatternTableOrder:
			desc = "表访问顺序不一致"
			severity = models.SeverityCritical
		case models.PatternSelectForUpdate:
			desc = "SELECT FOR UPDATE 使用不当"
			severity = models.SeverityHigh
		case models.PatternBatchOperation:
			desc = "批量操作锁定过多行"
			severity = models.SeverityMedium
		case models.PatternUnindexedJoin:
			desc = "JOIN条件缺少索引"
			severity = models.SeverityMedium
		}

		patternDist = append(patternDist, models.SQLPatternAnalysis{
			Pattern:     pattern,
			Count:       count,
			Description: desc,
			Severity:    severity,
		})
	}

	topTables := make([]models.KV, 0)
	for table, count := range tableCount {
		topTables = append(topTables, models.KV{Key: table, Value: count})
	}

	avgTime := ""
	if resolvedCount > 0 {
		avgMs := totalTime / int64(resolvedCount)
		avgTime = fmt.Sprintf("%dms", avgMs)
	}

	return models.PreventionStatistics{
		TotalRecommendations: len(pe.recommendations),
		ResolvedCount:        resolvedCount,
		PatternDistribution:  patternDist,
		TopTables:            topTables,
		AvgResolutionTime:    avgTime,
	}
}
