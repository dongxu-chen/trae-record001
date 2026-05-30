package analyzer

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"regexp"
	"strings"
	"sync"
	"time"

	"slow-query-killer/internal/db"
)

type QueryStats struct {
	Count           int
	TotalTime       time.Duration
	MaxTime         time.Duration
	MinTime         time.Duration
	AvgTime         time.Duration
	LastSeen        time.Time
	FirstSeen       time.Time
	ExampleQuery    string
	QueryType       string
	Tables          []string
}

type QueryAnalysis struct {
	QueryHash   string
	Normalized  string
	QueryType   string
	Tables      []string
	IsSelect    bool
	IsWrite     bool
	HasFullScan bool
	HasJoin     bool
	HasOrderBy  bool
	HasGroupBy  bool
	HasLimit    bool
}

type Analyzer struct {
	stats     map[string]*QueryStats
	statsLock sync.RWMutex
}

func NewAnalyzer() *Analyzer {
	return &Analyzer{
		stats: make(map[string]*QueryStats),
	}
}

func (a *Analyzer) AnalyzeQuery(query *db.SlowQuery) *QueryAnalysis {
	normalized := NormalizeQuery(query.Query)
	queryHash := HashQuery(normalized)

	upperQuery := strings.ToUpper(strings.TrimSpace(normalized))

	analysis := &QueryAnalysis{
		QueryHash:  queryHash,
		Normalized: normalized,
		QueryType:  detectQueryType(upperQuery),
		Tables:     extractTables(upperQuery),
		IsSelect:   strings.HasPrefix(upperQuery, "SELECT"),
		IsWrite:    isWriteQuery(upperQuery),
		HasJoin:    strings.Contains(upperQuery, " JOIN "),
		HasOrderBy: strings.Contains(upperQuery, " ORDER BY "),
		HasGroupBy: strings.Contains(upperQuery, " GROUP BY "),
		HasLimit:   strings.Contains(upperQuery, " LIMIT "),
	}

	return analysis
}

func (a *Analyzer) RecordQuery(query *db.SlowQuery, analysis *QueryAnalysis) {
	a.statsLock.Lock()
	defer a.statsLock.Unlock()

	stats, exists := a.stats[analysis.QueryHash]
	if !exists {
		stats = &QueryStats{
			Count:        0,
			TotalTime:    0,
			MaxTime:      0,
			MinTime:      query.ExecutionTime,
			FirstSeen:    time.Now(),
			ExampleQuery: query.Query,
			QueryType:    analysis.QueryType,
			Tables:       analysis.Tables,
		}
		a.stats[analysis.QueryHash] = stats
	}

	stats.Count++
	stats.TotalTime += query.ExecutionTime
	stats.LastSeen = time.Now()

	if query.ExecutionTime > stats.MaxTime {
			stats.MaxTime = query.ExecutionTime
	}
	if query.ExecutionTime < stats.MinTime {
		stats.MinTime = query.ExecutionTime
	}
	stats.AvgTime = stats.TotalTime / time.Duration(stats.Count)
}

func (a *Analyzer) GetStats() map[string]*QueryStats {
	a.statsLock.RLock()
	defer a.statsLock.RUnlock()

	result := make(map[string]*QueryStats, len(a.stats))
	for k, v := range a.stats {
		result[k] = v
	}
	return result
}

func (a *Analyzer) GetTopSlowQueries(limit int) []*QueryStats {
	a.statsLock.RLock()
	defer a.statsLock.RUnlock()

	statsList := make([]*QueryStats, 0, len(a.stats))
	for _, v := range a.stats {
		statsList = append(statsList, v)
	}

	for i := 0; i < len(statsList)-1; i++ {
		for j := i + 1; j < len(statsList); j++ {
			if statsList[i].MaxTime < statsList[j].MaxTime {
				statsList[i], statsList[j] = statsList[j], statsList[i]
			}
		}
	}

	if limit > len(statsList) {
		limit = len(statsList)
	}
	return statsList[:limit]
}

func (a *Analyzer) ClearStats() {
	a.statsLock.Lock()
	defer a.statsLock.Unlock()
	a.stats = make(map[string]*QueryStats)
}

func NormalizeQuery(query string) string {
	normalized := strings.TrimSpace(query)
	normalized = strings.ToUpper(normalized)

	numberRegex := regexp.MustCompile(`\b\d+\b`)
	normalized = numberRegex.ReplaceAllString(normalized, "?")

	stringRegex := regexp.MustCompile(`'[^']*'`)
	normalized = stringRegex.ReplaceAllString(normalized, "'?'")

	stringRegex2 := regexp.MustCompile(`"[^"]*"`)
	normalized = stringRegex2.ReplaceAllString(normalized, "\"?\"")

	whitespaceRegex := regexp.MustCompile(`\s+`)
	normalized = whitespaceRegex.ReplaceAllString(normalized, " ")

	return strings.TrimSpace(normalized)
}

func HashQuery(normalizedQuery string) string {
	hash := sha256.Sum256([]byte(normalizedQuery))
	return hex.EncodeToString(hash[:])[:16]
}

func detectQueryType(upperQuery string) string {
	switch {
	case strings.HasPrefix(upperQuery, "SELECT"):
		return "SELECT"
	case strings.HasPrefix(upperQuery, "INSERT"):
		return "INSERT"
	case strings.HasPrefix(upperQuery, "UPDATE"):
		return "UPDATE"
	case strings.HasPrefix(upperQuery, "DELETE"):
		return "DELETE"
	case strings.HasPrefix(upperQuery, "ALTER"):
		return "ALTER"
	case strings.HasPrefix(upperQuery, "CREATE"):
		return "CREATE"
	case strings.HasPrefix(upperQuery, "DROP"):
		return "DROP"
	default:
		return "OTHER"
	}
}

func isWriteQuery(upperQuery string) bool {
	return strings.HasPrefix(upperQuery, "INSERT") ||
		strings.HasPrefix(upperQuery, "UPDATE") ||
		strings.HasPrefix(upperQuery, "DELETE") ||
		strings.HasPrefix(upperQuery, "ALTER") ||
		strings.HasPrefix(upperQuery, "CREATE") ||
		strings.HasPrefix(upperQuery, "DROP")
}

func extractTables(upperQuery string) []string {
	tables := make(map[string]bool)

	fromPattern := regexp.MustCompile(`FROM\s+([\w, ]+)`)
	if matches := fromPattern.FindStringSubmatch(upperQuery); len(matches) > 1 {
		for _, t := range strings.Split(matches[1], ",") {
			t = strings.TrimSpace(t)
			if t != "" {
				parts := strings.Fields(t)
				if len(parts) > 0 {
					tables[parts[0]] = true
				}
			}
		}
	}

	joinPattern := regexp.MustCompile(`JOIN\s+(\w+)`)
	for _, match := range joinPattern.FindAllStringSubmatch(upperQuery, -1) {
		if len(match) > 1 {
			tables[match[1]] = true
		}
	}

	updatePattern := regexp.MustCompile(`UPDATE\s+(\w+)`)
	if matches := updatePattern.FindStringSubmatch(upperQuery); len(matches) > 1 {
		tables[matches[1]] = true
	}

	result := make([]string, 0, len(tables))
	for t := range tables {
		result = append(result, t)
	}
	return result
}

func (a *Analyzer) GenerateReport() string {
	stats := a.GetStats()
	if len(stats) == 0 {
		return "No query statistics available."
	}

	topQueries := a.GetTopSlowQueries(10)

	var report strings.Builder
	report.WriteString("\n=== Slow Query Analysis Report ===\n")
	report.WriteString(fmt.Sprintf("Total unique slow queries: %d\n\n", len(stats)))

	report.WriteString("Top 10 Slowest Queries:\n")
	report.WriteString(strings.Repeat("-", 80) + "\n")

	for i, qs := range topQueries {
		report.WriteString(fmt.Sprintf("\n%d. Query Type: %s\n", i+1, qs.QueryType))
		report.WriteString(fmt.Sprintf("   Tables: %v\n", qs.Tables))
		report.WriteString(fmt.Sprintf("   Count: %d\n", qs.Count))
		report.WriteString(fmt.Sprintf("   Max Time: %v\n", qs.MaxTime))
		report.WriteString(fmt.Sprintf("   Avg Time: %v\n", qs.AvgTime))
		report.WriteString(fmt.Sprintf("   First Seen: %v\n", qs.FirstSeen.Format(time.RFC3339)))
		report.WriteString(fmt.Sprintf("   Example: %s\n", truncateString(qs.ExampleQuery, 100)))
	}

	return report.String()
}

func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
