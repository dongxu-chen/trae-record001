package partition

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/xwb1989/sqlparser"
	"mysql-partition-tool/database"
	"mysql-partition-tool/models"
)

type PartitionPruningAnalysis struct {
	CanPrune           bool
	PartitionsToScan   []string
	PartitionsToPrune  []string
	TotalPartitions    int
	PruningEfficiency  float64
	PruningMethod      string
	Confidence         int
}

type QueryOptimizationReport struct {
	OriginalQuery      string
	OptimizedQuery     string
	PartitionAnalysis  *PartitionPruningAnalysis
	AppliedRules       []string
	AntiPatterns       []string
	Suggestions        []string
	EstimatedCostReduction float64
}

func RewriteQuery(req models.QueryRewriteRequest) (*models.QueryRewriteResponse, error) {
	db := database.GetInstance()

	tableInfo, err := db.GetTableInfo(req.TableName)
	if err != nil {
		return nil, fmt.Errorf("failed to get table info: %w", err)
	}

	response := &models.QueryRewriteResponse{
		OriginalSQL: req.OriginalSQL,
		RewrittenSQL: req.OriginalSQL,
	}

	if tableInfo.PartitionInfo == nil || len(tableInfo.PartitionInfo.Partitions) == 0 {
		response.AppliedRules = []string{"Table is not partitioned"}
		response.Explanation = "This table has not been partitioned yet. Partitioning can significantly improve query performance for large datasets."
		response.PerformanceHint = "Consider creating partitions on date, ID, or status columns based on your query patterns."
		return response, nil
	}

	partitionExpr := tableInfo.PartitionInfo.PartitionExpr
	partitionMethod := tableInfo.PartitionInfo.PartitionMethod
	partitionColumn := extractPartitionColumn(partitionExpr)

	analysis := AnalyzePartitionPruning(req.OriginalSQL, tableInfo.PartitionInfo, partitionColumn)

	report := optimizeQueryForPartitions(req.OriginalSQL, tableInfo.PartitionInfo, partitionMethod, partitionColumn)

	response.RewrittenSQL = report.OptimizedQuery
	response.AppliedRules = report.AppliedRules
	response.Explanation = generateDetailedExplanation(tableInfo.PartitionInfo, partitionColumn, analysis, report)
	response.PerformanceHint = generatePerformanceHint(analysis, report)

	return response, nil
}

func AnalyzePartitionPruning(sql string, partitionInfo *models.PartitionInfo, partitionColumn string) *PartitionPruningAnalysis {
	analysis := &PartitionPruningAnalysis{
		TotalPartitions: len(partitionInfo.Partitions),
		CanPrune:        false,
		Confidence:      0,
	}

	if partitionColumn == "" || len(partitionInfo.Partitions) == 0 {
		return analysis
	}

	hasPartitionKey, whereValue := extractPartitionKeyCondition(sql, partitionColumn)
	if !hasPartitionKey {
		analysis.PruningMethod = "FULL_SCAN"
		analysis.PartitionsToScan = getAllPartitionNames(partitionInfo)
		analysis.PruningEfficiency = 0
		return analysis
	}

	analysis.CanPrune = true
	analysis.PruningMethod = determinePruningMethod(partitionInfo.PartitionMethod, whereValue)

	switch partitionInfo.PartitionMethod {
	case "RANGE", "RANGE_ID":
		analysis.PartitionsToScan = determineRangePartitions(partitionInfo, whereValue)
	case "LIST":
		analysis.PartitionsToScan = determineListPartitions(partitionInfo, whereValue)
	case "HASH", "LINEAR_HASH", "KEY":
		analysis.PartitionsToScan = determineHashPartitions(partitionInfo, whereValue)
	default:
		analysis.PartitionsToScan = getAllPartitionNames(partitionInfo)
	}

	analysis.PartitionsToPrune = difference(getAllPartitionNames(partitionInfo), analysis.PartitionsToScan)
	analysis.PruningEfficiency = float64(len(analysis.PartitionsToPrune)) / float64(analysis.TotalPartitions) * 100

	if len(analysis.PartitionsToScan) == 1 {
		analysis.Confidence = 90
	} else if len(analysis.PartitionsToScan) < analysis.TotalPartitions/2 {
		analysis.Confidence = 75
	} else {
		analysis.Confidence = 50
	}

	return analysis
}

func optimizeQueryForPartitions(sql string, partitionInfo *models.PartitionInfo, method, partitionColumn string) *QueryOptimizationReport {
	report := &QueryOptimizationReport{
		OriginalQuery:  sql,
		OptimizedQuery: sql,
		AppliedRules:   []string{},
		AntiPatterns:   []string{},
		Suggestions:    []string{},
	}

	optimized := sql

	if hasFunctionOnPartitionKey(sql, partitionColumn) {
		report.AntiPatterns = append(report.AntiPatterns, "Function used on partition key prevents pruning")
		report.Suggestions = append(report.Suggestions, "Rewrite to avoid functions on the partition key column")
		optimized = fixFunctionOnPartitionKey(optimized, partitionColumn)
		report.AppliedRules = append(report.AppliedRules, "Detected function on partition key - manual rewrite recommended")
	}

	if method == "RANGE" || method == "RANGE_ID" {
		if strings.Contains(strings.ToLower(sql), "between") {
			before := optimized
			optimized = optimizeBetweenToRange(optimized, partitionColumn)
			if optimized != before {
				report.AppliedRules = append(report.AppliedRules, "Converted BETWEEN to explicit range comparison for better pruning")
			}
		}
	}

	if hasIneffectiveORCondition(sql, partitionColumn) {
		report.AntiPatterns = append(report.AntiPatterns, "OR with non-partition keys may disable pruning")
		report.Suggestions = append(report.Suggestions, "Consider using UNION ALL instead of OR with partition keys")
		report.AppliedRules = append(report.AppliedRules, "OR condition detected - review for pruning optimization")
	}

	if method == "LIST" {
		if hasLargeINClause(sql, partitionColumn) {
			report.Suggestions = append(report.Suggestions, "Large IN clauses can impact partition selection performance")
			report.AppliedRules = append(report.AppliedRules, "Large IN clause detected on LIST partition column")
		}
	}

	if strings.Contains(strings.ToLower(sql), "select *") {
		report.AntiPatterns = append(report.AntiPatterns, "SELECT * may prevent index-only scans")
		report.Suggestions = append(report.Suggestions, "Specify only required columns")
		report.AppliedRules = append(report.AppliedRules, "Consider replacing SELECT * with specific columns")
	}

	report.OptimizedQuery = optimized
	report.EstimatedCostReduction = estimateCostReduction(report)

	return report
}

func extractPartitionKeyCondition(sql, partitionColumn string) (bool, string) {
	lowerSQL := strings.ToLower(sql)
	lowerCol := strings.ToLower(partitionColumn)

	whereMatch := regexp.MustCompile(`(?i)WHERE\s+(.+?)(?:\s+GROUP|\s+ORDER|\s+HAVING|\s+LIMIT|;|$)`).FindStringSubmatch(sql)
	if len(whereMatch) > 1 {
		whereClause := whereMatch[1]
		if strings.Contains(strings.ToLower(whereClause), lowerCol) {
			re := regexp.MustCompile(`(?i)` + regexp.QuoteMeta(partitionColumn) + `\s*(=|>=|<=|>|<|IN|BETWEEN)\s*([^AND\s]+)`)
			match := re.FindStringSubmatch(whereClause)
			if len(match) > 2 {
				return true, strings.TrimSpace(match[2])
			}
			return true, ""
		}
	}

	return strings.Contains(lowerSQL, lowerCol), ""
}

func determinePruningMethod(partitionMethod, value string) string {
	switch partitionMethod {
	case "RANGE", "RANGE_ID":
		if strings.HasPrefix(value, "'") && strings.HasSuffix(value, "'") {
			return "RANGE_DATE_PRUNING"
		}
		if _, err := strconv.ParseFloat(strings.Trim(value, "'"), 64); err == nil {
			return "RANGE_NUMERIC_PRUNING"
		}
		return "RANGE_PARTIAL_PRUNING"
	case "LIST":
		return "LIST_EXACT_MATCH"
	case "HASH", "LINEAR_HASH", "KEY":
		return "HASH_DIRECT_MATCH"
	default:
		return "UNKNOWN_PRUNING"
	}
}

func getAllPartitionNames(partitionInfo *models.PartitionInfo) []string {
	names := make([]string, 0, len(partitionInfo.Partitions))
	for _, p := range partitionInfo.Partitions {
		names = append(names, p.PartitionName)
	}
	return names
}

func determineRangePartitions(partitionInfo *models.PartitionInfo, value string) []string {
	var partitionsToScan []string

	targetValue := parseRangeValue(value)

	for _, p := range partitionInfo.Partitions {
		if p.PartitionDescription == "MAXVALUE" {
			continue
		}

		boundary := parseRangeValue(p.PartitionDescription)
		if targetValue < boundary {
			partitionsToScan = append(partitionsToScan, p.PartitionName)
			break
		}
	}

	if len(partitionsToScan) == 0 && len(partitionInfo.Partitions) > 0 {
		lastPartition := partitionInfo.Partitions[len(partitionInfo.Partitions)-1]
		if lastPartition.PartitionDescription == "MAXVALUE" {
			partitionsToScan = append(partitionsToScan, lastPartition.PartitionName)
		}
	}

	if len(partitionsToScan) == 0 {
		return getAllPartitionNames(partitionInfo)
	}

	return partitionsToScan
}

func determineListPartitions(partitionInfo *models.PartitionInfo, value string) []string {
	var partitionsToScan []string

	targetValue := strings.Trim(value, "'")

	for _, p := range partitionInfo.Partitions {
		if p.PartitionDescription == "DEFAULT" {
			continue
		}

		values := strings.Split(p.PartitionDescription, ",")
		for _, v := range values {
			if strings.TrimSpace(v) == targetValue || strings.Trim(strings.TrimSpace(v), "'") == targetValue {
				partitionsToScan = append(partitionsToScan, p.PartitionName)
				break
			}
		}
	}

	if len(partitionsToScan) == 0 {
		for _, p := range partitionInfo.Partitions {
			if p.PartitionDescription == "DEFAULT" {
				partitionsToScan = append(partitionsToScan, p.PartitionName)
				break
			}
		}
	}

	if len(partitionsToScan) == 0 {
		return getAllPartitionNames(partitionInfo)
	}

	return partitionsToScan
}

func determineHashPartitions(partitionInfo *models.PartitionInfo, value string) []string {
	if value == "" {
		return getAllPartitionNames(partitionInfo)
	}

	numPartitions := len(partitionInfo.Partitions)
	hashValue := 0

	if numVal, err := strconv.ParseInt(strings.Trim(value, "'"), 10, 64); err == nil {
		hashValue = int(numVal)
	} else {
		for _, c := range value {
			hashValue += int(c)
		}
	}

	partitionIndex := hashValue % numPartitions
	if partitionIndex < 0 {
		partitionIndex = -partitionIndex
	}
	if partitionIndex >= len(partitionInfo.Partitions) {
		partitionIndex = len(partitionInfo.Partitions) - 1
	}

	return []string{partitionInfo.Partitions[partitionIndex].PartitionName}
}

func parseRangeValue(value string) int64 {
	value = strings.TrimSpace(value)

	if strings.HasPrefix(value, "TO_DAYS(") {
		re := regexp.MustCompile(`TO_DAYS\('(.+?)'\)`).FindStringSubmatch(value)
		if len(re) > 1 {
			if t, err := time.Parse("2006-01-02", re[1]); err == nil {
				return t.Unix()
			}
		}
	}

	if t, err := time.Parse("'2006-01-02'", value); err == nil {
		return t.Unix()
	}

	if num, err := strconv.ParseInt(value, 10, 64); err == nil {
		return num
	}

	return 0
}

func difference(a, b []string) []string {
	bMap := make(map[string]bool)
	for _, x := range b {
		bMap[x] = true
	}

	var diff []string
	for _, x := range a {
		if !bMap[x] {
			diff = append(diff, x)
		}
	}
	return diff
}

func hasFunctionOnPartitionKey(sql, partitionColumn string) bool {
	patterns := []string{
		`DATE\s*\(\s*` + regexp.QuoteMeta(partitionColumn),
		`YEAR\s*\(\s*` + regexp.QuoteMeta(partitionColumn),
		`MONTH\s*\(\s*` + regexp.QuoteMeta(partitionColumn),
		`DAY\s*\(\s*` + regexp.QuoteMeta(partitionColumn),
		`TO_DAYS\s*\(\s*` + regexp.QuoteMeta(partitionColumn),
		`DATE_FORMAT\s*\(\s*` + regexp.QuoteMeta(partitionColumn),
	}

	for _, pattern := range patterns {
		matched, _ := regexp.MatchString(`(?i)`+pattern, sql)
		if matched {
			return true
		}
	}
	return false
}

func fixFunctionOnPartitionKey(sql, partitionColumn string) string {
	return sql
}

func optimizeBetweenToRange(sql, partitionColumn string) string {
	re := regexp.MustCompile(`(?i)(` + regexp.QuoteMeta(partitionColumn) + `)\s+BETWEEN\s+(.+?)\s+AND\s+(.+?)(\s+|;|$)`)
	return re.ReplaceAllStringFunc(sql, func(match string) string {
		matches := re.FindStringSubmatch(match)
		if len(matches) > 4 {
			return fmt.Sprintf("%s >= %s AND %s <= %s%s", matches[1], matches[2], matches[1], matches[3], matches[4])
		}
		return match
	})
}

func hasIneffectiveORCondition(sql, partitionColumn string) bool {
	whereMatch := regexp.MustCompile(`(?i)WHERE\s+(.+?)(?:\s+GROUP|\s+ORDER|\s+HAVING|\s+LIMIT|;|$)`).FindStringSubmatch(sql)
	if len(whereMatch) > 1 {
		whereClause := whereMatch[1]
		if strings.Contains(whereClause, "OR") {
			parts := strings.Split(whereClause, "OR")
			for _, part := range parts {
				if !strings.Contains(strings.ToLower(part), strings.ToLower(partitionColumn)) {
					return true
				}
			}
		}
	}
	return false
}

func hasLargeINClause(sql, partitionColumn string) bool {
	re := regexp.MustCompile(`(?i)` + regexp.QuoteMeta(partitionColumn) + `\s+IN\s*\((.+?)\)`)
	match := re.FindStringSubmatch(sql)
	if len(match) > 1 {
		values := strings.Split(match[1], ",")
		return len(values) > 10
	}
	return false
}

func estimateCostReduction(report *QueryOptimizationReport) float64 {
	reduction := 0.0

	if len(report.AntiPatterns) == 0 {
		reduction += 10
	} else {
		reduction -= float64(len(report.AntiPatterns)) * 5
	}

	if len(report.AppliedRules) > 0 {
		reduction += float64(len(report.AppliedRules)) * 5
	}

	if reduction < 0 {
		reduction = 0
	}

	return reduction
}

func generateDetailedExplanation(partitionInfo *models.PartitionInfo, partitionColumn string, analysis *PartitionPruningAnalysis, report *QueryOptimizationReport) string {
	var explanation strings.Builder

	explanation.WriteString(fmt.Sprintf("=== Partition Information ===\n"))
	explanation.WriteString(fmt.Sprintf("Partition Method: %s\n", partitionInfo.PartitionMethod))
	explanation.WriteString(fmt.Sprintf("Partition Column: %s\n", partitionColumn))
	explanation.WriteString(fmt.Sprintf("Total Partitions: %d\n\n", len(partitionInfo.Partitions)))

	explanation.WriteString(fmt.Sprintf("=== Partition Pruning Analysis ===\n"))
	explanation.WriteString(fmt.Sprintf("Pruning Method: %s\n", analysis.PruningMethod))
	explanation.WriteString(fmt.Sprintf("Can Prune: %v\n", analysis.CanPrune))
	explanation.WriteString(fmt.Sprintf("Confidence: %d%%\n", analysis.Confidence))
	explanation.WriteString(fmt.Sprintf("Pruning Efficiency: %.1f%%\n\n", analysis.PruningEfficiency))

	if analysis.CanPrune {
		explanation.WriteString(fmt.Sprintf("Partitions to Scan (%d): %s\n", len(analysis.PartitionsToScan), strings.Join(analysis.PartitionsToScan, ", ")))
		if len(analysis.PartitionsToPrune) > 0 {
			explanation.WriteString(fmt.Sprintf("Partitions to Prune (%d): %s\n\n", len(analysis.PartitionsToPrune), strings.Join(analysis.PartitionsToPrune, ", ")))
		}
	} else {
		explanation.WriteString("WARNING: Full partition scan required. Consider adding partition key to WHERE clause.\n\n")
	}

	if len(report.AppliedRules) > 0 {
		explanation.WriteString("=== Optimization Rules Applied ===\n")
		for _, rule := range report.AppliedRules {
			explanation.WriteString(fmt.Sprintf("- %s\n", rule))
		}
		explanation.WriteString("\n")
	}

	if len(report.AntiPatterns) > 0 {
		explanation.WriteString("=== Anti-Patterns Detected ===\n")
		for _, ap := range report.AntiPatterns {
			explanation.WriteString(fmt.Sprintf("⚠️  %s\n", ap))
		}
		explanation.WriteString("\n")
	}

	if len(report.Suggestions) > 0 {
		explanation.WriteString("=== Optimization Suggestions ===\n")
		for _, s := range report.Suggestions {
			explanation.WriteString(fmt.Sprintf("💡 %s\n", s))
		}
	}

	return explanation.String()
}

func generatePerformanceHint(analysis *PartitionPruningAnalysis, report *QueryOptimizationReport) string {
	var hint strings.Builder

	if analysis.CanPrune && analysis.PruningEfficiency > 70 {
		hint.WriteString(fmt.Sprintf("Excellent! Partition pruning will scan only %.1f%% of partitions. ", analysis.PruningEfficiency))
	} else if analysis.CanPrune && analysis.PruningEfficiency > 30 {
		hint.WriteString("Good. Some partition pruning will occur. ")
	} else if !analysis.CanPrune {
		hint.WriteString("CRITICAL: No partition pruning possible. ")
	}

	if len(report.AntiPatterns) > 0 {
		hint.WriteString("Anti-patterns detected that may reduce performance. ")
	}

	if len(report.Suggestions) > 0 {
		hint.WriteString("Review the optimization suggestions for best performance.")
	}

	return hint.String()
}

func extractPartitionColumn(expr string) string {
	re := regexp.MustCompile(`TO_DAYS\(\s*` + "`" + `?(\w+)` + "`" + `?\s*\)`)
	matches := re.FindStringSubmatch(expr)
	if len(matches) > 1 {
		return matches[1]
	}

	re2 := regexp.MustCompile(`YEAR\(\s*` + "`" + `?(\w+)` + "`" + `?\s*\)`)
	matches2 := re2.FindStringSubmatch(expr)
	if len(matches2) > 1 {
		return matches2[1]
	}

	re3 := regexp.MustCompile("`" + `?(\w+)` + "`" + `?`)
	matches3 := re3.FindStringSubmatch(expr)
	if len(matches3) > 1 {
		return matches3[1]
	}

	return expr
}

func AnalyzeQuery(sql string, tableName string) (map[string]interface{}, error) {
	result := make(map[string]interface{})

	stmt, err := sqlparser.Parse(sql)
	if err != nil {
		return nil, fmt.Errorf("failed to parse SQL: %w", err)
	}

	switch stmt.(type) {
	case *sqlparser.Select:
		result["type"] = "SELECT"
	case *sqlparser.Insert:
		result["type"] = "INSERT"
	case *sqlparser.Update:
		result["type"] = "UPDATE"
	case *sqlparser.Delete:
		result["type"] = "DELETE"
	default:
		result["type"] = "OTHER"
	}

	lowerSQL := strings.ToLower(sql)

	result["hasWhere"] = strings.Contains(lowerSQL, "where")
	result["hasOrderBy"] = strings.Contains(lowerSQL, "order by")
	result["hasGroupBy"] = strings.Contains(lowerSQL, "group by")
	result["hasJoin"] = strings.Contains(lowerSQL, "join")
	result["hasLimit"] = strings.Contains(lowerSQL, "limit")
	result["selectStar"], _ = regexp.MatchString(`(?i)SELECT\s+\*`, sql)

	tableCount := len(regexp.MustCompile(`(?i)\bFROM\s+` + tableName + `\b`).FindAllString(sql, -1))
	tableCount += len(regexp.MustCompile(`(?i)\bJOIN\s+` + tableName + `\b`).FindAllString(sql, -1))
	result["tableReferences"] = tableCount

	result["hasPartitionFunction"] = hasPartitionFunction(sql)
	result["hasSubquery"] = strings.Contains(lowerSQL, "select") && strings.Count(lowerSQL, "from") > 1

	return result, nil
}

func hasPartitionFunction(sql string) bool {
	functions := []string{"TO_DAYS(", "YEAR(", "MONTH(", "DAY(", "DATE(", "FROM_DAYS("}
	lowerSQL := strings.ToLower(sql)
	for _, f := range functions {
		if strings.Contains(lowerSQL, strings.ToLower(f)) {
			return true
		}
	}
	return false
}
