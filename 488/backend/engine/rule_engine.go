package engine

import (
	"deadlock-resolver/config"
	"deadlock-resolver/models"
	"strings"
	"time"
)

type RuleEngine struct {
	rules    []models.Rule
	strategy *config.StrategyConfig
}

func NewRuleEngine(strategy *config.StrategyConfig) *RuleEngine {
	re := &RuleEngine{
		rules:    make([]models.Rule, 0),
		strategy: strategy,
	}
	re.loadDefaultRules()
	return re
}

func (re *RuleEngine) loadDefaultRules() {
	defaultRules := []models.Rule{
		{
			ID:          "rule_001",
			Name:        "Long Running Transaction Killer",
			Description: "Kill transactions running longer than max allowed time",
			Enabled:     true,
			Priority:    1,
			Condition: models.RuleCondition{
				MinTransactionTime: 300,
				MinAffectedRows:    0,
			},
			Action: models.RuleAction{
				KillTransaction: true,
				LogOnly:         false,
				Notify:          true,
				Message:         "Killed long running transaction",
				PriorityBoost:   20,
			},
		},
		{
			ID:          "rule_002",
			Name:        "High Impact Transaction Protector",
			Description: "Protect transactions with high cost score from being killed",
			Enabled:     true,
			Priority:    100,
			Condition: models.RuleCondition{
				MinCostScore: 5000,
			},
			Action: models.RuleAction{
				KillTransaction: false,
				LogOnly:         true,
				Notify:          true,
				Message:         "High impact transaction detected - manual review required",
			},
		},
		{
			ID:          "rule_003",
			Name:        "System User Exclusion",
			Description: "Never kill system user transactions",
			Enabled:     true,
			Priority:    10,
			Condition: models.RuleCondition{
				Users: []string{"system", "admin", "root"},
			},
			Action: models.RuleAction{
				KillTransaction: false,
				LogOnly:         true,
				Notify:          false,
				Message:         "System user transaction protected",
			},
		},
		{
			ID:          "rule_004",
			Name:        "DDL Transaction Protector",
			Description: "Protect DDL transactions from automatic kill",
			Enabled:     true,
			Priority:    50,
			Condition: models.RuleCondition{
				TransactionTypes: []models.TransactionType{models.TransactionTypeDDL},
			},
			Action: models.RuleAction{
				KillTransaction: false,
				LogOnly:         true,
				Notify:          true,
				Message:         "DDL transaction detected - manual review required",
			},
		},
		{
			ID:          "rule_005",
			Name:        "Read Transaction Priority",
			Description: "Prioritize killing read transactions first",
			Enabled:     true,
			Priority:    5,
			Condition: models.RuleCondition{
				TransactionTypes: []models.TransactionType{models.TransactionTypeRead},
			},
			Action: models.RuleAction{
				KillTransaction: true,
				LogOnly:         false,
				Notify:          false,
				Message:         "Read transaction selected for kill",
				PriorityBoost:   30,
			},
		},
		{
			ID:          "rule_006",
			Name:        "Critical Severity Alert",
			Description: "Alert on critical severity deadlocks",
			Enabled:     true,
			Priority:    1,
			Condition: models.RuleCondition{
				SeverityLevels: []models.SeverityLevel{models.SeverityCritical},
			},
			Action: models.RuleAction{
				KillTransaction: false,
				LogOnly:         true,
				Notify:          true,
				Message:         "CRITICAL severity deadlock detected",
			},
		},
	}
	
	re.rules = defaultRules
}

func (re *RuleEngine) AddRule(rule models.Rule) {
	re.rules = append(re.rules, rule)
}

func (re *RuleEngine) RemoveRule(ruleID string) {
	for i, rule := range re.rules {
		if rule.ID == ruleID {
			re.rules = append(re.rules[:i], re.rules[i+1:]...)
			break
		}
	}
}

func (re *RuleEngine) GetRules() []models.Rule {
	return re.rules
}

func (re *RuleEngine) Evaluate(deadlock *models.Deadlock) (*EvaluationResult, error) {
	return re.EvaluateWithStrategy(deadlock, re.strategy.KillStrategy)
}

func (re *RuleEngine) EvaluateWithStrategy(deadlock *models.Deadlock, killStrategy string) (*EvaluationResult, error) {
	result := &EvaluationResult{
		DeadlockID:     deadlock.ID,
		Violations:     make([]RuleViolation, 0),
		CanKill:        make(map[int64]bool),
		PriorityScores: make(map[int64]int),
		MatchedRules: make([]models.Rule, 0),
	}

	for i := range deadlock.Transactions {
		trx := &deadlock.Transactions[i]
		result.CanKill[trx.ID] = true
		result.PriorityScores[trx.ID] = trx.KillPriority
		
		for _, rule := range re.rules {
			if !rule.Enabled {
				continue
			}
			
			if re.matchesRule(trx, &rule, deadlock) {
				violation := RuleViolation{
					RuleID:        rule.ID,
					RuleName:      rule.Name,
					TransactionID: trx.ID,
					Action:        rule.Action,
				}
				result.Violations = append(result.Violations, violation)
				
				if rule.Priority >= 10 && !rule.Action.KillTransaction {
					result.CanKill[trx.ID] = false
				}
				
				if rule.Action.PriorityBoost > 0 {
					result.PriorityScores[trx.ID] += rule.Action.PriorityBoost
				}
				
				ruleMatched := false
				for _, mr := range result.MatchedRules {
					if mr.ID == rule.ID {
						ruleMatched = true
						break
					}
				}
				if !ruleMatched {
					result.MatchedRules = append(result.MatchedRules, rule)
				}
			}
		}
	}
	
	return result, nil
}

func (re *RuleEngine) matchesRule(trx *models.Transaction, rule *models.Rule, deadlock *models.Deadlock) bool {
	cond := rule.Condition
	
	if cond.MinTransactionTime > 0 {
		elapsed := time.Since(trx.StartTime).Seconds()
		if elapsed < float64(cond.MinTransactionTime) {
			return false
		}
	}
	
	if cond.MinAffectedRows > 0 {
		if trx.RowsModified < cond.MinAffectedRows {
			return false
		}
	}
	
	if cond.MinCostScore > 0 {
		if trx.CostScore < cond.MinCostScore {
			return false
		}
	}
	
	if len(cond.Users) > 0 {
		found := false
		for _, user := range cond.Users {
			if strings.EqualFold(trx.User, user) {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	
	if len(cond.Databases) > 0 {
		found := false
		for _, db := range cond.Databases {
			if strings.EqualFold(trx.DB, db) {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	
	if len(cond.QueryPatterns) > 0 {
		found := false
		for _, pattern := range cond.QueryPatterns {
			if strings.Contains(strings.ToLower(trx.Info), strings.ToLower(pattern)) {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	
	if len(cond.TransactionTypes) > 0 {
		found := false
		for _, t := range cond.TransactionTypes {
			if trx.TransactionType == t {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	
	if len(cond.SeverityLevels) > 0 {
		found := false
		for _, s := range cond.SeverityLevels {
			if deadlock.Severity == s {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	
	return true
}

func (re *RuleEngine) SelectVictim(deadlock *models.Deadlock, evalResult *EvaluationResult) int64 {
	switch re.strategy.KillStrategy {
	case "youngest":
		return re.selectYoungest(deadlock, evalResult)
	case "oldest":
		return re.selectOldest(deadlock, evalResult)
	case "least_work":
		return re.selectLeastWork(deadlock, evalResult)
	case "priority":
		return re.selectByPriority(deadlock, evalResult)
	case "lowest_cost":
		return re.selectLowestCost(deadlock, evalResult)
	default:
		return re.selectByPriority(deadlock, evalResult)
	}
}

func (re *RuleEngine) selectByPriority(deadlock *models.Deadlock, evalResult *EvaluationResult) int64 {
	var victimID int64
	maxPriority := -1
	
	for _, trx := range deadlock.Transactions {
		if !evalResult.CanKill[trx.ID] {
			continue
		}
		
		priority := evalResult.PriorityScores[trx.ID]
		if priority > maxPriority {
			maxPriority = priority
			victimID = trx.ID
		}
	}
	
	return victimID
}

func (re *RuleEngine) selectLowestCost(deadlock *models.Deadlock, evalResult *EvaluationResult) int64 {
	var victimID int64
	minCost := -1
	
	for _, trx := range deadlock.Transactions {
		if !evalResult.CanKill[trx.ID] {
			continue
		}
		
		if minCost == -1 || trx.CostScore < minCost {
			minCost = trx.CostScore
			victimID = trx.ID
		}
	}
	
	return victimID
}

func (re *RuleEngine) selectYoungest(deadlock *models.Deadlock, evalResult *EvaluationResult) int64 {
	var victimID int64
	var latestTime time.Time
	
	for _, trx := range deadlock.Transactions {
		if !evalResult.CanKill[trx.ID] {
			continue
		}
		
		if victimID == 0 || trx.StartTime.After(latestTime) {
			victimID = trx.ID
			latestTime = trx.StartTime
		}
	}
	
	return victimID
}

func (re *RuleEngine) selectOldest(deadlock *models.Deadlock, evalResult *EvaluationResult) int64 {
	var victimID int64
	var earliestTime time.Time
	
	for _, trx := range deadlock.Transactions {
		if !evalResult.CanKill[trx.ID] {
			continue
		}
		
		if victimID == 0 || trx.StartTime.Before(earliestTime) {
			victimID = trx.ID
			earliestTime = trx.StartTime
		}
	}
	
	return victimID
}

func (re *RuleEngine) selectLeastWork(deadlock *models.Deadlock, evalResult *EvaluationResult) int64 {
	var victimID int64
	minCost := -1
	
	for _, trx := range deadlock.Transactions {
		if !evalResult.CanKill[trx.ID] {
			continue
		}
		
		if minCost == -1 || trx.CostScore < minCost {
			victimID = trx.ID
			minCost = trx.CostScore
		}
	}
	
	return victimID
}

func (re *RuleEngine) AssessImpact(deadlock *models.Deadlock, victimID int64) *models.ImpactAssessment {
	var victimTrx *models.Transaction
	for i := range deadlock.Transactions {
		if deadlock.Transactions[i].ID == victimID {
			victimTrx = &deadlock.Transactions[i]
			break
		}
	}
	
	if victimTrx == nil {
		return nil
	}
	
	assessment := &models.ImpactAssessment{
		AffectedRows:    victimTrx.RowsModified,
		RollbackTime:    calculateEstimatedRollbackTime(victimTrx),
		QueriesAffected: []string{victimTrx.Info},
		TransactionType: victimTrx.TransactionType,
		Severity:        deadlock.Severity,
		CostScore:       victimTrx.CostScore,
	}
	
	assessment.BusinessImpact, assessment.Recommendation = generateImpactAssessment(victimTrx, deadlock.Severity)
	
	return assessment
}

func calculateEstimatedRollbackTime(trx *models.Transaction) string {
	baseSeconds := trx.RowsModified / 1000
	if baseSeconds < 1 {
		baseSeconds = 1
	}
	
	if trx.TransactionType == models.TransactionTypeDDL {
		baseSeconds *= 10
	}
	
	return (time.Duration(baseSeconds) * time.Second).String()
}

func generateImpactAssessment(trx *models.Transaction, severity models.SeverityLevel) (string, string) {
	var businessImpact string
	var recommendation string
	
	switch severity {
	case models.SeverityCritical:
		businessImpact = "CRITICAL"
		recommendation = "URGENT: This is a critical severity deadlock. Immediate attention required. "
	case models.SeverityHigh:
		businessImpact = "HIGH"
		recommendation = "High impact deadlock detected. "
	case models.SeverityMedium:
		businessImpact = "MEDIUM"
		recommendation = "Medium impact deadlock detected. "
	default:
		businessImpact = "LOW"
		recommendation = "Low impact deadlock detected. "
	}
	
	switch trx.TransactionType {
	case models.TransactionTypeDDL:
		recommendation += "This is a DDL transaction - rolling back may take significant time. Consider manual intervention."
	case models.TransactionTypeWrite:
		if trx.RowsModified > 10000 {
			recommendation += "This write transaction affects many rows. Rollback may impact data consistency."
		} else {
			recommendation += "This is a standard write transaction. Relatively safe to rollback."
		}
	case models.TransactionTypeRead:
		recommendation += "This is a read transaction. Safe to rollback with minimal impact."
	default:
		recommendation += "Exercise caution when rolling back this transaction."
	}
	
	return businessImpact, recommendation
}

type EvaluationResult struct {
	DeadlockID     string
	Violations     []RuleViolation
	CanKill        map[int64]bool
	PriorityScores map[int64]int
	MatchedRules   []models.Rule
}

type RuleViolation struct {
	RuleID        string
	RuleName      string
	TransactionID int64
	Action        models.RuleAction
}
