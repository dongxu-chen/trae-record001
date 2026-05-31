package router

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"

	"ch-lifecycle/internal/clickhouse"
)

var (
	tableRegex      = regexp.MustCompile(`(?i)\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_.]+)`)
	whereRegex      = regexp.MustCompile(`(?i)\bWHERE\b(.+?)(?:\bGROUP\s+BY|\bORDER\s+BY|\bLIMIT|\bHAVING|$)`)
	betweenRegex   = regexp.MustCompile(`(?i)(\w+)\s+BETWEEN\s+('?[\d\-T:\.]+'?)\s+AND\s+('?[\d\-T:\.]+'?)`)
	dateFuncRegex  = regexp.MustCompile(`(?i)(\w+)\s*(>=|<=|>|<|=)\s*['"]?(\d{4}-\d{2}-\d{2})['"]?`)
	timestampRegex = regexp.MustCompile(`(?i)(\w+)\s*(>=|<=|>|<|=)\s*['"]?(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})['"]?`)
)

type RoutingRuleStore struct {
	mu       sync.RWMutex
	rules    map[string]*RoutingRule
	filePath string
	logger   *zap.Logger
}

func NewRoutingRuleStore(filePath string, logger *zap.Logger) *RoutingRuleStore {
	s := &RoutingRuleStore{
		rules:    make(map[string]*RoutingRule),
		filePath: filePath,
		logger:   logger,
	}
	if err := s.load(); err != nil {
		logger.Warn("failed to load routing rules, starting fresh", zap.Error(err))
	}
	return s
}

func (s *RoutingRuleStore) load() error {
	data, err := os.ReadFile(s.filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	var rules []*RoutingRule
	if err := json.Unmarshal(data, &rules); err != nil {
		return err
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, r := range rules {
		s.rules[r.ID] = r
	}
	s.logger.Info("loaded routing rules", zap.Int("count", len(rules)))
	return nil
}

func (s *RoutingRuleStore) save() error {
	s.mu.RLock()
	rules := make([]*RoutingRule, 0, len(s.rules))
	for _, r := range s.rules {
		rules = append(rules, r)
	}
	s.mu.RUnlock()
	data, err := json.MarshalIndent(rules, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(s.filePath, data, 0644)
}

func (s *RoutingRuleStore) Add(rule *RoutingRule) (*RoutingRule, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	rule.ID = uuid.New().String()
	s.rules[rule.ID] = rule
	if err := s.save(); err != nil {
		delete(s.rules, rule.ID)
		return nil, err
	}
	s.logger.Info("added routing rule", zap.String("id", rule.ID), zap.String("pattern", rule.Pattern))
	return rule, nil
}

func (s *RoutingRuleStore) Delete(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	existing, ok := s.rules[id]
	if !ok {
		return ErrRuleNotFound
	}
	delete(s.rules, id)
	if err := s.save(); err != nil {
		s.rules[id] = existing
		return err
	}
	s.logger.Info("deleted routing rule", zap.String("id", id))
	return nil
}

func (s *RoutingRuleStore) List() ([]*RoutingRule, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make([]*RoutingRule, 0, len(s.rules))
	for _, r := range s.rules {
		result = append(result, r)
	}
	sort.Slice(result, func(i, j int) bool {
		return result[i].Priority > result[j].Priority
	})
	return result, nil
}

func (s *RoutingRuleStore) Get(id string) (*RoutingRule, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	r, ok := s.rules[id]
	if !ok {
		return nil, ErrRuleNotFound
	}
	return r, nil
}

type QueryRouter struct {
	chClient   *clickhouse.Client
	hotClient   *clickhouse.Client
	coldClient  *clickhouse.Client
	config      RoutingConfig
	ruleStore   *RoutingRuleStore
	logger      *zap.Logger
}

func NewQueryRouter(
	chClient *clickhouse.Client,
	config RoutingConfig,
	ruleStore *RoutingRuleStore,
	logger *zap.Logger,
) *QueryRouter {
	return &QueryRouter{
		chClient:  chClient,
		config:     config,
		ruleStore:  ruleStore,
		logger:     logger,
	}
}

func (qr *QueryRouter) AnalyzeQuery(sqlStr, database string) (QueryInfo, error) {
	if database == "" {
		return QueryInfo{}, ErrNoDatabaseSpecified
	}

	if sqlStr == "" {
		return QueryInfo{}, ErrInvalidSQL
	}

	queryInfo := QueryInfo{
		SQL:      sqlStr,
		Database: database,
	}

	tableNames := extractTableNames(sqlStr)
	queryInfo.TableNames = tableNames
	if len(tableNames) > 0 {
		queryInfo.Table = tableNames[0]
	}

	startTime, endTime := extractTimeRange(sqlStr)
	queryInfo.StartTime = startTime
	queryInfo.EndTime = endTime

	return queryInfo, nil
}

func extractTableNames(sqlStr string) []string {
	var tables := make(map[string]bool)
	matches := tableRegex.FindAllStringSubmatch(sqlStr, -1)
	for _, match := range matches {
		if len(match) > 1 {
			table := match[1]
			if idx := strings.LastIndex(table, "."); idx != -1 {
				table = table[idx+1:]
			}
			tables[table] = true
		}
	}

	result := make([]string, 0, len(tables))
	for table := range tables {
		result = append(result, table)
	}
	return result
}

func extractTimeRange(sqlStr string) (time.Time, time.Time) {
	var startTime, endTime time.Time

	whereMatch := whereRegex.FindStringSubmatch(sqlStr)
	if len(whereMatch) < 2 {
		return startTime, endTime
	}

	whereClause := whereMatch[1]

	betweenMatches := betweenRegex.FindAllStringSubmatch(whereClause)
	for _, match := range betweenMatches {
		if len(match) == 4 {
			start := parseDateTime(match[2])
			end := parseDateTime(match[3])
			if !start.IsZero() && !end.IsZero() {
				if startTime.IsZero() || start.Before(startTime) {
					startTime = start
				}
				if endTime.IsZero() || end.After(endTime) {
					endTime = end
				}
			}
		}
	}

	dateMatches := dateFuncRegex.FindAllStringSubmatch(whereClause)
	for _, match := range dateMatches {
		if len(match) == 4 {
			op := match[2]
			dt := parseDateTime(match[3])
			if dt.IsZero() {
				continue
			}
			switch op {
			case ">=", ">":
				if startTime.IsZero() || dt.After(startTime) {
					startTime = dt
				}
			case "<=", "<":
				if endTime.IsZero() || dt.Before(endTime) {
					endTime = dt
				}
			case "=":
				if startTime.IsZero() || dt.After(startTime) {
					startTime = dt
				}
				if endTime.IsZero() || dt.Before(endTime) {
					endTime = dt
				}
			}
		}
	}

	timestampMatches := timestampRegex.FindAllStringSubmatch(whereClause)
	for _, match := range timestampMatches {
		if len(match) == 4 {
			op := match[2]
			dt := parseDateTime(match[3])
			if dt.IsZero() {
				continue
			}
			switch op {
			case ">=", ">":
				if startTime.IsZero() || dt.After(startTime) {
					startTime = dt
				}
			case "<=", "<":
				if endTime.IsZero() || dt.Before(endTime) {
					endTime = dt
				}
			case "=":
				if startTime.IsZero() || dt.After(startTime) {
					startTime = dt
				}
				if endTime.IsZero() || dt.Before(endTime) {
					endTime = dt
				}
			}
		}
	}

	return startTime, endTime
}

func parseDateTime(s string) time.Time {
	s = strings.Trim(s, "'\"")
	
	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02T15:04:05",
		"2006-01-02",
		"2006-01-02 15:04:05.000",
		"2006-01-02T15:04:05.000",
		time.RFC3339,
	}

	for _, format := range formats {
		if t, err := time.ParseInLocation(format, s, time.UTC); err == nil {
			return t
		}
	}
	return time.Time{}
}

func (qr *QueryRouter) RouteQuery(sqlStr, database string) (RouteResult, error) {
	queryInfo, err := qr.AnalyzeQuery(sqlStr, database)
	if err != nil {
		return RouteResult{}, err
	}

	var result RouteResult

	if qr.config.EnableSmartRouting {
		matchedRule := qr.MatchRules(queryInfo)
		if matchedRule != nil {
			result.Source = matchedRule.TargetSource
			result.Reason = fmt.Sprintf("Matched routing rule: %s", matchedRule.Pattern)
			result.TargetHost = qr.getHostForSource(matchedRule.TargetSource)
			estimatedRows, _ := qr.EstimateDataSize(queryInfo)
			result.EstimatedRows = estimatedRows
			return result, nil
		}

		if !queryInfo.StartTime.IsZero() && !queryInfo.EndTime.IsZero() {
			ageDays := time.Since(queryInfo.EndTime).Hours() / 24
			if ageDays > 30 {
				result.Source = QuerySourceCold
				result.Reason = fmt.Sprintf("Query targets data older than 30 days (%.1f days old)", ageDays)
				result.TargetHost = qr.config.ColdHost
				estimatedRows, _ := qr.EstimateDataSize(queryInfo)
				result.EstimatedRows = estimatedRows
				return result, nil
			}
		}
	}

	result.Source = qr.config.DefaultSource
	result.Reason = "Using default routing"
	result.TargetHost = qr.getHostForSource(qr.config.DefaultSource)
	estimatedRows, _ := qr.EstimateDataSize(queryInfo)
	result.EstimatedRows = estimatedRows
	return result, nil
}

func (qr *QueryRouter) getHostForSource(source QuerySource) string {
	switch source {
	case QuerySourceHot:
		return qr.config.HotHost
	case QuerySourceCold:
		return qr.config.ColdHost
	default:
		return qr.config.HotHost
	}
}

func (qr *QueryRouter) MatchRules(queryInfo QueryInfo) *RoutingRule {
	rules, err := qr.ruleStore.List()
	if err != nil {
		return nil
	}

	for _, rule := range rules {
		if rule.Database != "" && rule.Database != queryInfo.Database {
			continue
		}

		if rule.Table != "" {
			tableMatched := false
			for _, t := range queryInfo.TableNames {
				if t == rule.Table {
					tableMatched = true
					break
				}
			}
			if !tableMatched {
				continue
			}
		}

		if rule.Pattern != "" {
			pattern := strings.ToLower(rule.Pattern)
			sqlLower := strings.ToLower(queryInfo.SQL)
			if !strings.Contains(sqlLower, pattern) {
				continue
			}
		}

		if rule.MinAgeDays > 0 && queryInfo.EndTime.IsZero() {
			continue
		}

		if rule.MinAgeDays > 0 && !queryInfo.EndTime.IsZero() {
			ageDays := time.Since(queryInfo.EndTime).Hours() / 24
			if int(ageDays) < rule.MinAgeDays {
				continue
			}
		}

		qr.logger.Info("routing rule matched",
			zap.String("rule_id", rule.ID),
			zap.String("pattern", rule.Pattern),
			zap.String("target_source", string(rule.TargetSource)),
		)
		return rule
	}

	return nil
}

func (qr *QueryRouter) EstimateDataSize(queryInfo QueryInfo) (uint64, error) {
	if qr.chClient == nil {
		return 0, ErrClientNotAvailable
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	var totalRows uint64

	for _, tableName := range queryInfo.TableNames {
		partitions, err := qr.chClient.GetPartitions(ctx, queryInfo.Database, tableName)
		if err != nil {
			qr.logger.Warn("failed to get partitions for estimation",
				zap.String("table", tableName),
				zap.Error(err),
			)
			continue
		}

		for _, part := range partitions {
			partMinDate := parseDateTime(part.MinDate)
			partMaxDate := parseDateTime(part.MaxDate)

			if partMinDate.IsZero() || partMaxDate.IsZero() {
				totalRows += part.Rows
				continue
			}

			if !queryInfo.StartTime.IsZero() && !queryInfo.EndTime.IsZero() {
				if partMaxDate.Before(queryInfo.StartTime) || partMinDate.After(queryInfo.EndTime) {
					continue
				}
			} else if !queryInfo.StartTime.IsZero() {
				if partMaxDate.Before(queryInfo.StartTime) {
					continue
				}
			} else if !queryInfo.EndTime.IsZero() {
				if partMinDate.After(queryInfo.EndTime) {
					continue
				}
			}

			totalRows += part.Rows
		}
	}

	return totalRows, nil
}

func (qr *QueryRouter) ExecuteQuery(sqlStr, database string, source QuerySource) (*sql.Rows, error) {
	ctx := context.Background()

	var client *clickhouse.Client
	switch source {
	case QuerySourceHot:
		client = qr.hotClient
	case QuerySourceCold:
		client = qr.coldClient
	default:
		client = qr.chClient
	}

	if client == nil {
		client = qr.chClient
	}

	if client == nil {
		return nil, ErrClientNotAvailable
	}

	qr.logger.Info("executing query",
		zap.String("source", string(source)),
		zap.String("database", database),
	)

	return client.Query(ctx, sqlStr)
}

func (qr *QueryRouter) AddRule(rule *RoutingRule) (*RoutingRule, error) {
	return qr.ruleStore.Add(rule)
}

func (qr *QueryRouter) DeleteRule(id string) error {
	return qr.ruleStore.Delete(id)
}

func (qr *QueryRouter) ListRules() ([]*RoutingRule, error) {
	return qr.ruleStore.List()
}

func (qr *QueryRouter) GetRule(id string) (*RoutingRule, error) {
	return qr.ruleStore.Get(id)
}

func (qr *QueryRouter) SetHotClient(client *clickhouse.Client) {
	qr.hotClient = client
}

func (qr *QueryRouter) SetColdClient(client *clickhouse.Client) {
	qr.coldClient = client
}

func (qr *QueryRouter) UpdateConfig(config RoutingConfig) {
	qr.config = config
}

func (qr *QueryRouter) GetConfig() RoutingConfig {
	return qr.config
}
