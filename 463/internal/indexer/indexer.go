package indexer

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"

	"slow-query-killer/internal/analyzer"
)

type IndexSuggestion struct {
	QueryHash       string
	QuerySample     string
	Table           string
	SuggestedIndex  string
	IndexColumns    []string
	Priority        string
	Confidence      float64
	EstimatedBenefit string
	KillCount       int
	TotalSlowTime   time.Duration
	Reason          string
}

type QueryIndexInfo struct {
	Tables      []string
	WhereCols   []string
	JoinCols    []string
	OrderCols   []string
	GroupCols   []string
	SelectCols  []string
	IsStarQuery bool
}

type Indexer struct {
	queryStats    map[string]*QueryIndexStat
	statsLock    sync.RWMutex
	suggestionCb func(IndexSuggestion)
}

type QueryIndexStat struct {
	QuerySample    string
	Table          string
	KillCount      int
	TotalSlowTime  time.Duration
	LastKillTime   time.Time
	WhereColumns   map[string]int
	JoinColumns    map[string]int
	OrderColumns   map[string]int
	GroupColumns   map[string]int
}

func NewIndexer() *Indexer {
	return &Indexer{
		queryStats: make(map[string]*QueryIndexStat),
	}
}

func (idx *Indexer) SetSuggestionCallback(cb func(IndexSuggestion)) {
	idx.suggestionCb = cb
}

func (idx *Indexer) RecordKilledQuery(query string, executionTime time.Duration) {
	normalized := analyzer.NormalizeQuery(query)
	queryHash := analyzer.HashQuery(normalized)

	info := analyzeQueryForIndex(query)

	idx.statsLock.Lock()
	defer idx.statsLock.Unlock()

	stat, exists := idx.queryStats[queryHash]
	if !exists {
		stat = &QueryIndexStat{
			QuerySample:  truncateQuery(query, 200),
			WhereColumns: make(map[string]int),
			JoinColumns:  make(map[string]int),
			OrderColumns: make(map[string]int),
			GroupColumns: make(map[string]int),
		}
		if len(info.Tables) > 0 {
			stat.Table = info.Tables[0]
		}
		idx.queryStats[queryHash] = stat
	}

	stat.KillCount++
	stat.TotalSlowTime += executionTime
	stat.LastKillTime = time.Now()

	for _, col := range info.WhereCols {
		stat.WhereColumns[col]++
	}
	for _, col := range info.JoinCols {
		stat.JoinColumns[col]++
	}
	for _, col := range info.OrderCols {
		stat.OrderColumns[col]++
	}
	for _, col := range info.GroupCols {
		stat.GroupColumns[col]++
	}
}

func (idx *Indexer) AnalyzeAndSuggest() []IndexSuggestion {
	idx.statsLock.RLock()
	defer idx.statsLock.RUnlock()

	suggestions := make([]IndexSuggestion, 0)

	for hash, stat := range idx.queryStats {
		if suggestion := idx.generateSuggestion(hash, stat); suggestion != nil {
			suggestions = append(suggestions, *suggestion)

			if idx.suggestionCb != nil {
				idx.suggestionCb(*suggestion)
			}
		}
	}

	sort.Slice(suggestions, func(i, j int) bool {
		return suggestions[i].KillCount > suggestions[j].KillCount
	})

	return suggestions
}

func (idx *Indexer) generateSuggestion(queryHash string, stat *QueryIndexStat) *IndexSuggestion {
	if stat.KillCount < 3 {
		return nil
	}

	var indexCols []string
	var reason string
	confidence := 0.0

	if len(stat.WhereColumns) > 0 {
		topWhere := getTopColumns(stat.WhereColumns, 3)
		indexCols = append(indexCols, topWhere...)
		confidence += 0.4
		reason += fmt.Sprintf("frequently filtered on %s; ", strings.Join(topWhere, ", "))
	}

	if len(stat.JoinColumns) > 0 {
		topJoin := getTopColumns(stat.JoinColumns, 2)
		for _, col := range topJoin {
			if !contains(indexCols, col) {
				indexCols = append(indexCols, col)
			}
		}
		confidence += 0.3
		reason += fmt.Sprintf("joined on %s; ", strings.Join(topJoin, ", "))
	}

	if len(stat.OrderColumns) > 0 {
		topOrder := getTopColumns(stat.OrderColumns, 2)
		for _, col := range topOrder {
			if !contains(indexCols, col) {
				indexCols = append(indexCols, col)
			}
		}
		confidence += 0.2
		reason += fmt.Sprintf("sorted by %s; ", strings.Join(topOrder, ", "))
	}

	if len(indexCols) == 0 {
		return nil
	}

	if stat.KillCount >= 10 {
		confidence += 0.1
	} else if stat.KillCount >= 5 {
		confidence += 0.05
	}

	priority := "LOW"
	switch {
	case confidence >= 0.7 && stat.KillCount >= 10:
		priority = "CRITICAL"
	case confidence >= 0.5 && stat.KillCount >= 5:
		priority = "HIGH"
	case confidence >= 0.3:
		priority = "MEDIUM"
	}

	indexName := fmt.Sprintf("idx_%s_%s", stat.Table, strings.Join(indexCols, "_"))
	indexName = sanitizeIndexName(indexName)

	benefit := estimateBenefit(stat.TotalSlowTime, stat.KillCount)

	return &IndexSuggestion{
		QueryHash:       queryHash,
		QuerySample:     stat.QuerySample,
		Table:           stat.Table,
		SuggestedIndex:  indexName,
		IndexColumns:    indexCols,
		Priority:        priority,
		Confidence:      confidence,
		EstimatedBenefit: benefit,
		KillCount:       stat.KillCount,
		TotalSlowTime:   stat.TotalSlowTime,
		Reason:          strings.TrimSuffix(reason, "; "),
	}
}

func analyzeQueryForIndex(query string) QueryIndexInfo {
	info := QueryIndexInfo{
		WhereCols:  make([]string, 0),
		JoinCols:   make([]string, 0),
		OrderCols:  make([]string, 0),
		GroupCols:  make([]string, 0),
		SelectCols: make([]string, 0),
	}

	upper := strings.ToUpper(query)
	info.Tables = extractTables(upper)

	whereRegex := regexp.MustCompile(`WHERE\s+(.*?)(?:GROUP|ORDER|LIMIT|$|HAVING|JOIN)`)
	if matches := whereRegex.FindStringSubmatch(upper); len(matches) > 1 {
		info.WhereCols = extractColumns(matches[1])
	}

	joinRegex := regexp.MustCompile(`JOIN\s+\w+\s+ON\s+([\w.]+)\s*=\s*([\w.]+)`)
	for _, match := range joinRegex.FindAllStringSubmatch(upper, -1) {
		if len(match) >= 3 {
			info.JoinCols = append(info.JoinCols, cleanColumnName(match[1]))
			info.JoinCols = append(info.JoinCols, cleanColumnName(match[2]))
		}
	}

	orderRegex := regexp.MustCompile(`ORDER\s+BY\s+(.*?)(?:LIMIT|$)`)
	if matches := orderRegex.FindStringSubmatch(upper); len(matches) > 1 {
		info.OrderCols = extractColumns(matches[1])
	}

	groupRegex := regexp.MustCompile(`GROUP\s+BY\s+(.*?)(?:ORDER|HAVING|LIMIT|$)`)
	if matches := groupRegex.FindStringSubmatch(upper); len(matches) > 1 {
		info.GroupCols = extractColumns(matches[1])
	}

	info.IsStarQuery = strings.Contains(upper, "SELECT *")

	return info
}

func extractTables(upperQuery string) []string {
	tables := make([]string, 0)

	fromRegex := regexp.MustCompile(`FROM\s+([\w, ]+)`)
	if matches := fromRegex.FindStringSubmatch(upperQuery); len(matches) > 1 {
		for _, t := range strings.Split(matches[1], ",") {
			parts := strings.Fields(strings.TrimSpace(t))
			if len(parts) > 0 {
				tables = append(tables, parts[0])
			}
		}
	}

	joinRegex := regexp.MustCompile(`JOIN\s+(\w+)`)
	for _, match := range joinRegex.FindAllStringSubmatch(upperQuery, -1) {
		if len(match) > 1 {
			tables = append(tables, match[1])
		}
	}

	updateRegex := regexp.MustCompile(`UPDATE\s+(\w+)`)
	if matches := updateRegex.FindStringSubmatch(upperQuery); len(matches) > 1 {
		tables = append(tables, matches[1])
	}

	deleteRegex := regexp.MustCompile(`DELETE\s+FROM\s+(\w+)`)
	if matches := deleteRegex.FindStringSubmatch(upperQuery); len(matches) > 1 {
		tables = append(tables, matches[1])
	}

	return uniqueStrings(tables)
}

func extractColumns(expression string) []string {
	columns := make([]string, 0)

	columnRegex := regexp.MustCompile(`\b([a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]*)\b`)
	for _, match := range columnRegex.FindAllStringSubmatch(expression, -1) {
		if len(match) > 2 {
			col := match[2]
			if !isSQLKeyword(col) {
				columns = append(columns, col)
			}
		}
	}

	return uniqueStrings(columns)
}

func cleanColumnName(col string) string {
	if idx := strings.Index(col, "."); idx >= 0 {
		return col[idx+1:]
	}
	return col
}

func isSQLKeyword(word string) bool {
	keywords := map[string]bool{
		"AND": true, "OR": true, "NOT": true, "IN": true, "LIKE": true,
		"BETWEEN": true, "IS": true, "NULL": true, "AS": true,
		"ASC": true, "DESC": true, "ON": true, "USING": true,
		"TRUE": true, "FALSE": true, "NONE": true,
	}
	return keywords[strings.ToUpper(word)]
}

func uniqueStrings(s []string) []string {
	seen := make(map[string]bool)
	result := make([]string, 0)
	for _, str := range s {
		if !seen[str] && str != "" {
			seen[str] = true
			result = append(result, str)
		}
	}
	return result
}

func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

func getTopColumns(colMap map[string]int, limit int) []string {
	type colCount struct {
		col   string
		count int
	}

	list := make([]colCount, 0, len(colMap))
	for col, count := range colMap {
		list = append(list, colCount{col, count})
	}

	sort.Slice(list, func(i, j int) bool {
		return list[i].count > list[j].count
	})

	if len(list) > limit {
		list = list[:limit]
	}

	result := make([]string, 0, len(list))
	for _, cc := range list {
		result = append(result, cc.col)
	}

	return result
}

func sanitizeIndexName(name string) string {
	name = strings.ToLower(name)
	reg := regexp.MustCompile(`[^a-z0-9_]`)
	return reg.ReplaceAllString(name, "_")
}

func estimateBenefit(totalTime time.Duration, killCount int) string {
	avgTime := totalTime / time.Duration(killCount)

	switch {
	case avgTime >= 5*time.Minute:
		return "VERY HIGH - Average execution time >5min"
	case avgTime >= 1*time.Minute:
		return "HIGH - Average execution time >1min"
	case avgTime >= 30*time.Second:
		return "MEDIUM - Average execution time >30s"
	default:
		return "MODERATE - Average execution time improvement expected"
	}
}

func truncateQuery(query string, maxLen int) string {
	if len(query) <= maxLen {
		return query
	}
	return query[:maxLen] + "..."
}

func (idx *Indexer) GenerateIndexReport() string {
	suggestions := idx.AnalyzeAndSuggest()

	var report strings.Builder
	report.WriteString("\n=== Index Optimization Suggestions ===\n")
	report.WriteString(fmt.Sprintf("Total queries analyzed: %d\n", len(idx.queryStats)))
	report.WriteString(fmt.Sprintf("Suggestions generated: %d\n\n", len(suggestions)))

	if len(suggestions) == 0 {
		report.WriteString("No index suggestions at this time. More data needed.\n")
		return report.String()
	}

	limit := 10
	if len(suggestions) < limit {
		limit = len(suggestions)
	}

	for i := 0; i < limit; i++ {
		s := suggestions[i]
		report.WriteString(fmt.Sprintf("\n%d. [%s] %s\n", i+1, s.Priority, s.SuggestedIndex))
		report.WriteString(fmt.Sprintf("   Table: %s\n", s.Table))
		report.WriteString(fmt.Sprintf("   Columns: (%s)\n", strings.Join(s.IndexColumns, ", ")))
		report.WriteString(fmt.Sprintf("   Confidence: %.0f%% | Benefit: %s\n", s.Confidence*100, s.EstimatedBenefit))
		report.WriteString(fmt.Sprintf("   Killed %d times, total slow time: %v\n", s.KillCount, s.TotalSlowTime.Round(time.Second)))
		report.WriteString(fmt.Sprintf("   Reason: %s\n", s.Reason))
		report.WriteString(fmt.Sprintf("   Query: %s\n", s.QuerySample))
	}

	report.WriteString("\n=== SQL Implementation ===\n")
	for i := 0; i < limit; i++ {
		s := suggestions[i]
		if s.Table != "" {
			report.WriteString(fmt.Sprintf("-- %s (%s priority)\n", s.SuggestedIndex, s.Priority))
			report.WriteString(fmt.Sprintf("CREATE INDEX %s ON %s (%s);\n\n",
				s.SuggestedIndex, s.Table, strings.Join(s.IndexColumns, ", ")))
		}
	}

	return report.String()
}
