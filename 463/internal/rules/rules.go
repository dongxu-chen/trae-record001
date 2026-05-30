package rules

import (
	"regexp"
	"strings"
	"time"

	"slow-query-killer/internal/analyzer"
	"slow-query-killer/internal/config"
	"slow-query-killer/internal/db"
)

type Rule struct {
	Name        string
	Enabled     bool
	Threshold   time.Duration
	QueryRegex  *regexp.Regexp
	KillMode    string
	NotifyOnly  bool
}

type RuleEngine struct {
	rules     []Rule
	whitelist *Whitelist
}

type Whitelist struct {
	users           map[string]bool
	databases       map[string]bool
	queryPrefix     []string
	sqlFingerprints map[string]bool
}

type MatchResult struct {
	Matched    bool
	RuleName   string
	KillMode   string
	NotifyOnly bool
	Reason     string
}

func NewRuleEngine(cfg *config.Config) *RuleEngine {
	re := &RuleEngine{
		rules: make([]Rule, 0),
		whitelist: &Whitelist{
			users:           make(map[string]bool),
			databases:       make(map[string]bool),
			queryPrefix:     cfg.Monitor.Whitelist.QueryPrefix,
			sqlFingerprints: make(map[string]bool),
		},
	}

	for _, user := range cfg.Monitor.Whitelist.Users {
		re.whitelist.users[user] = true
	}

	for _, db := range cfg.Monitor.Whitelist.Databases {
		re.whitelist.databases[db] = true
	}

	for _, fingerprint := range cfg.Monitor.Whitelist.SQLFingerprints {
		re.whitelist.sqlFingerprints[fingerprint] = true
	}

	for _, ruleCfg := range cfg.Monitor.Rules {
		if !ruleCfg.Enabled {
			continue
		}

		var reg *regexp.Regexp
		if ruleCfg.QueryRegex != "" {
			reg, _ = regexp.Compile(ruleCfg.QueryRegex)
		}

		re.rules = append(re.rules, Rule{
			Name:       ruleCfg.Name,
			Enabled:    ruleCfg.Enabled,
			Threshold:  ruleCfg.Threshold,
			QueryRegex: reg,
			KillMode:   ruleCfg.KillMode,
			NotifyOnly: ruleCfg.NotifyOnly,
		})
	}

	return re
}

func (re *RuleEngine) IsWhitelisted(query *db.SlowQuery) bool {
	if re.whitelist.users[query.User] {
		return true
	}

	if re.whitelist.databases[query.DBName] {
		return true
	}

	normalizedQuery := analyzer.NormalizeQuery(query.Query)
	queryFingerprint := analyzer.HashQuery(normalizedQuery)
	if re.whitelist.sqlFingerprints[queryFingerprint] {
		return true
	}

	upperQuery := strings.ToUpper(strings.TrimSpace(query.Query))
	for _, prefix := range re.whitelist.queryPrefix {
		if strings.HasPrefix(upperQuery, strings.ToUpper(prefix)) {
			return true
		}
	}

	return false
}

func (re *RuleEngine) GetSQLFingerprints() map[string]bool {
	return re.whitelist.sqlFingerprints
}

func (re *RuleEngine) Evaluate(query *db.SlowQuery, defaultThreshold time.Duration, defaultKillMode string) *MatchResult {
	if re.IsWhitelisted(query) {
		return &MatchResult{
			Matched: false,
			Reason:  "query is whitelisted",
		}
	}

	for _, rule := range re.rules {
		if !rule.Enabled {
			continue
		}

		if query.ExecutionTime < rule.Threshold {
			continue
		}

		if rule.QueryRegex != nil && !rule.QueryRegex.MatchString(query.Query) {
			continue
		}

		return &MatchResult{
			Matched:    true,
			RuleName:   rule.Name,
			KillMode:   rule.KillMode,
			NotifyOnly: rule.NotifyOnly,
			Reason:     "matched rule: " + rule.Name,
		}
	}

	if query.ExecutionTime >= defaultThreshold {
		return &MatchResult{
			Matched:    true,
			RuleName:   "default",
			KillMode:   defaultKillMode,
			NotifyOnly: false,
			Reason:     "exceeded default threshold",
		}
	}

	return &MatchResult{
		Matched: false,
		Reason:  "no rules matched",
	}
}

func (re *RuleEngine) GetRules() []Rule {
	return re.rules
}
