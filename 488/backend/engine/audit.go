package engine

import (
	"deadlock-resolver/models"
	"fmt"
	"sync"
	"time"
)

type AuditEngine struct {
	mu        sync.RWMutex
	logs      []models.AuditLog
	callbacks []func(models.AuditLog)
}

func NewAuditEngine() *AuditEngine {
	return &AuditEngine{
		logs:      make([]models.AuditLog, 0),
		callbacks: make([]func(models.AuditLog), 0),
	}
}

func (ae *AuditEngine) RegisterCallback(cb func(models.AuditLog)) {
	ae.mu.Lock()
	defer ae.mu.Unlock()
	ae.callbacks = append(ae.callbacks, cb)
}

func (ae *AuditEngine) LogKillAction(deadlock models.Deadlock, victim *models.Transaction, strategy, ruleApplied string, operator string, clientIP string, userAgent string) models.AuditLog {
	ae.mu.Lock()
	defer ae.mu.Unlock()

	queriesAffected := make([]string, 0)
	for _, tx := range deadlock.Transactions {
		queriesAffected = append(queriesAffected, tx.Info)
	}

	businessImpact := ae.assessBusinessImpact(victim, deadlock)
	rollbackTime := ae.estimateRollbackTime(victim)

	log := models.AuditLog{
		ID:              fmt.Sprintf("audit_%d", time.Now().UnixNano()),
		Timestamp:       time.Now(),
		Action:          "KILL_TRANSACTION",
		DeadlockID:      deadlock.ID,
		TransactionID:   victim.ID,
		TransactionInfo: victim.Info,
		TransactionType: victim.TransactionType,
		User:            victim.User,
		Operator:        operator,
		Source:          deadlock.Source,
		Strategy:        strategy,
		RuleApplied:     ruleApplied,
		CostScore:       victim.CostScore,
		KillPriority:    victim.KillPriority,
		BusinessImpact:  businessImpact,
		RollbackTime:    rollbackTime,
		QueriesAffected: queriesAffected,
		Success:         true,
		ClientIP:        clientIP,
		UserAgent:       userAgent,
	}

	ae.logs = append(ae.logs, log)

	for _, cb := range ae.callbacks {
		go cb(log)
	}

	return log
}

func (ae *AuditEngine) LogManualAction(deadlockID string, transactionID int64, action string, operator string, clientIP string, userAgent string, success bool, errMsg string) models.AuditLog {
	ae.mu.Lock()
	defer ae.mu.Unlock()

	log := models.AuditLog{
		ID:            fmt.Sprintf("audit_%d", time.Now().UnixNano()),
		Timestamp:     time.Now(),
		Action:        action,
		DeadlockID:    deadlockID,
		TransactionID: transactionID,
		Operator:      operator,
		Source:        "MANUAL",
		Strategy:      "MANUAL",
		Success:       success,
		ErrorMessage:  errMsg,
		ClientIP:      clientIP,
		UserAgent:     userAgent,
	}

	ae.logs = append(ae.logs, log)

	for _, cb := range ae.callbacks {
		go cb(log)
	}

	return log
}

func (ae *AuditEngine) LogSystemEvent(action string, message string, operator string) models.AuditLog {
	ae.mu.Lock()
	defer ae.mu.Unlock()

	log := models.AuditLog{
		ID:           fmt.Sprintf("audit_%d", time.Now().UnixNano()),
		Timestamp:    time.Now(),
		Action:       action,
		Operator:     operator,
		Source:       "SYSTEM",
		Strategy:     "SYSTEM",
		Success:      true,
		ErrorMessage: message,
	}

	ae.logs = append(ae.logs, log)

	for _, cb := range ae.callbacks {
		go cb(log)
	}

	return log
}

func (ae *AuditEngine) assessBusinessImpact(tx *models.Transaction, deadlock models.Deadlock) string {
	var impact string

	switch tx.TransactionType {
	case models.TransactionTypeDDL:
		impact = "高影响：DDL操作被终止，表结构变更未完成，可能需要手动恢复。"
		if tx.RowsModified > 0 {
			impact += fmt.Sprintf(" 已修改%d行数据可能需要回滚。", tx.RowsModified)
		}
	case models.TransactionTypeWrite:
		if tx.CostScore > 5000 {
			impact = fmt.Sprintf("高影响：写事务被终止，开销分数%d，需回滚%d行修改。", tx.CostScore, tx.RowsModified)
		} else if tx.CostScore > 1000 {
			impact = fmt.Sprintf("中影响：写事务被终止，开销分数%d，需回滚%d行修改。", tx.CostScore, tx.RowsModified)
		} else {
			impact = fmt.Sprintf("低影响：写事务被终止，开销分数%d，仅需回滚少量数据。", tx.CostScore)
		}
	case models.TransactionTypeRead:
		impact = "低影响：只读事务被终止，无数据修改，业务影响较小。"
	default:
		impact = "未知类型事务被终止，需要检查业务影响。"
	}

	if tx.Time > 60 {
		impact += fmt.Sprintf(" 注意：事务已执行%d秒，回滚可能需要较长时间。", tx.Time)
	}

	if len(deadlock.Transactions) > 2 {
		impact += fmt.Sprintf(" 死锁涉及%d个事务，建议检查其他事务状态。", len(deadlock.Transactions))
	}

	return impact
}

func (ae *AuditEngine) estimateRollbackTime(tx *models.Transaction) string {
	if tx == nil {
		return "未知"
	}

	baseTimeMs := tx.RowsModified * 10
	if tx.TransactionType == models.TransactionTypeDDL {
		baseTimeMs *= 10
	}

	if baseTimeMs < 1000 {
		return fmt.Sprintf("%dms", baseTimeMs)
	} else if baseTimeMs < 60000 {
		return fmt.Sprintf("%.1fs", float64(baseTimeMs)/1000)
	} else {
		return fmt.Sprintf("%.1fmin", float64(baseTimeMs)/60000)
	}
}

func (ae *AuditEngine) GetLogs(limit int, filters map[string]string) []models.AuditLog {
	ae.mu.RLock()
	defer ae.mu.RUnlock()

	var result []models.AuditLog

	for i := len(ae.logs) - 1; i >= 0; i-- {
		log := ae.logs[i]
		match := true

		if action, ok := filters["action"]; ok && action != "" {
			if log.Action != action {
				match = false
			}
		}
		if deadlockID, ok := filters["deadlock_id"]; ok && deadlockID != "" {
			if log.DeadlockID != deadlockID {
				match = false
			}
		}
		if operator, ok := filters["operator"]; ok && operator != "" {
			if log.Operator != operator {
				match = false
			}
		}
		if success, ok := filters["success"]; ok && success != "" {
			s := success == "true"
			if log.Success != s {
				match = false
			}
		}
		if source, ok := filters["source"]; ok && source != "" {
			if log.Source != source {
				match = false
			}
		}
		if txType, ok := filters["transaction_type"]; ok && txType != "" {
			if string(log.TransactionType) != txType {
				match = false
			}
		}

		if match {
			result = append(result, log)
			if len(result) >= limit {
				break
			}
		}
	}

	return result
}

func (ae *AuditEngine) GetLog(id string) (*models.AuditLog, error) {
	ae.mu.RLock()
	defer ae.mu.RUnlock()

	for _, log := range ae.logs {
		if log.ID == id {
			return &log, nil
		}
	}
	return nil, fmt.Errorf("audit log not found")
}

func (ae *AuditEngine) GetStatistics() map[string]interface{} {
	ae.mu.RLock()
	defer ae.mu.RUnlock()

	totalKills := 0
	autoKills := 0
	manualKills := 0
	successCount := 0
	failedCount := 0
	byAction := make(map[string]int)
	bySource := make(map[string]int)
	byTxType := make(map[string]int)
	totalRollbackTime := int64(0)
	avgCostScore := 0
	costScoreCount := 0

	for _, log := range ae.logs {
		byAction[log.Action]++
		bySource[log.Source]++

		if log.TransactionType != "" {
			byTxType[string(log.TransactionType)]++
		}

		if log.Action == "KILL_TRANSACTION" {
			totalKills++
			if log.Source == "AUTO" {
				autoKills++
			} else if log.Source == "MANUAL" {
				manualKills++
			}
		}

		if log.Success {
			successCount++
		} else {
			failedCount++
		}

		if log.CostScore > 0 {
			avgCostScore += log.CostScore
			costScoreCount++
		}
	}

	if costScoreCount > 0 {
		avgCostScore = avgCostScore / costScoreCount
	}

	actionStats := make([]models.KV, 0)
	for k, v := range byAction {
		actionStats = append(actionStats, models.KV{Key: k, Value: v})
	}

	sourceStats := make([]models.KV, 0)
	for k, v := range bySource {
		sourceStats = append(sourceStats, models.KV{Key: k, Value: v})
	}

	txTypeStats := make([]models.KV, 0)
	for k, v := range byTxType {
		txTypeStats = append(txTypeStats, models.KV{Key: k, Value: v})
	}

	return map[string]interface{}{
		"total_logs":        len(ae.logs),
		"total_kills":       totalKills,
		"auto_kills":        autoKills,
		"manual_kills":      manualKills,
		"success_count":     successCount,
		"failed_count":      failedCount,
		"success_rate":      float64(successCount) / float64(len(ae.logs)) * 100,
		"avg_cost_score":    avgCostScore,
		"total_rollback_time": fmt.Sprintf("%dms", totalRollbackTime),
		"by_action":         actionStats,
		"by_source":         sourceStats,
		"by_transaction_type": txTypeStats,
	}
}

func (ae *AuditEngine) GetTraceByDeadlock(deadlockID string) []models.AuditLog {
	ae.mu.RLock()
	defer ae.mu.RUnlock()

	var result []models.AuditLog
	for _, log := range ae.logs {
		if log.DeadlockID == deadlockID {
			result = append(result, log)
		}
	}
	return result
}
