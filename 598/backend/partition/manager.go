package partition

import (
	"fmt"
	"math"
	"regexp"
	"strings"
	"time"

	"mysql-partition-tool/config"
	"mysql-partition-tool/database"
	"mysql-partition-tool/models"
)

type PartitionResizeRequest struct {
	TableName       string
	PartitionNames  []string
	TargetRowCount  int64
	Operation       string
	NewPartitionDefs []models.PartitionDef
}

type PartitionMigrationRequest struct {
	TableName          string
	SourcePartition    string
	TargetPartition    string
	WhereCondition     string
	BatchSize          int
	VerifyData         bool
}

type HotColdSeparationConfig struct {
	TableName        string
	PartitionColumn  string
	HotThresholdDays int
	ColdArchivePath  string
	HotPartitions    []string
	ColdPartitions   []string
}

type PerformanceBenchmarkRequest struct {
	TableName       string
	Queries         []string
	BeforePartition bool
	AfterPartition  bool
	RunCount        int
}

type PerformanceMetric struct {
	Query           string
	AvgTimeMs       float64
	MinTimeMs       float64
	MaxTimeMs       float64
	RowsExamined    int64
	PartitionsScan  int
	PartitionPruned int
	ExecutionPlan   string
}

type PerformanceComparison struct {
	TableName    string
	BeforeMetrics []PerformanceMetric
	AfterMetrics  []PerformanceMetric
	Improvements  map[string]float64
	OverallGain   float64
}

type PartitionResizeResult struct {
	Success        bool
	SqlStatements  []string
	OldPartitions  []string
	NewPartitions  []models.PartitionDef
	MigratedRows   int64
	ExecutionTime int64
	Warnings       []string
}

type MigrationResult struct {
	Success        bool
	MigratedRows   int64
	VerifiedRows   int64
	ExecutionTime  int64
	SourceEmpty    bool
	SqlStatements  []string
}

type HotColdAnalysis struct {
	TableName           string
	TotalRows           int64
	HotRows             int64
	ColdRows            int64
	HotPartitions       []models.PartitionDef
	ColdPartitions      []models.PartitionDef
	HotSizeMB           float64
	ColdSizeMB          float64
	RecommendedAction   string
}

func GenerateSmartSplitPartitionSQL(tableName string, partitionName string, targetRowsPerPartition int64) ([]string, error) {
	db := database.GetInstance()

	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		return nil, err
	}

	if tableInfo.PartitionInfo == nil {
		return nil, fmt.Errorf("table is not partitioned")
	}

	var targetPartition *models.PartitionDef
	for i := range tableInfo.PartitionInfo.Partitions {
		if tableInfo.PartitionInfo.Partitions[i].PartitionName == partitionName {
			targetPartition = &tableInfo.PartitionInfo.Partitions[i]
			break
		}
	}

	if targetPartition == nil {
		return nil, fmt.Errorf("partition %s not found", partitionName)
	}

	currentRows := targetPartition.TableRows
	if currentRows <= targetRowsPerPartition {
		return []string{fmt.Sprintf("-- Partition %s has %d rows, no split needed", partitionName, currentRows)}, nil
	}

	numNewPartitions := int(math.Ceil(float64(currentRows) / float64(targetRowsPerPartition)))
	if numNewPartitions < 2 {
		numNewPartitions = 2
	}

	var newPartitions []models.PartitionDef
	method := tableInfo.PartitionInfo.PartitionMethod

	switch method {
	case "RANGE", "RANGE_ID":
		newPartitions = generateRangeSplitPartitions(targetPartition, numNewPartitions)
	case "LIST":
		newPartitions = generateListSplitPartitions(targetPartition, numNewPartitions, tableName, tableInfo.PartitionInfo.PartitionExpr)
	default:
		return nil, fmt.Errorf("split operation not supported for %s partitioning", method)
	}

	var sqls []string
	sqls = append(sqls, fmt.Sprintf("-- Smart split partition %s into %d partitions", partitionName, numNewPartitions))
	sqls = append(sqls, fmt.Sprintf("-- Current rows: %d, Target rows per partition: %d", currentRows, targetRowsPerPartition))
	sqls = append(sqls, "")

	for _, p := range newPartitions {
		sqls = append(sqls, GenerateAddPartitionSQL(tableName, p))
	}

	sqls = append(sqls, "")
	sqls = append(sqls, "-- Migrate data to new partitions")
	for _, p := range newPartitions {
		sqls = append(sqls, generateDataMigrationSQL(tableName, targetPartition, &p, tableInfo.PartitionInfo.PartitionExpr))
	}

	sqls = append(sqls, "")
	sqls = append(sqls, fmt.Sprintf("-- Drop old partition %s after verification", partitionName))
	sqls = append(sqls, GenerateDropPartitionSQL(tableName, partitionName))

	return sqls, nil
}

func GenerateSmartMergePartitionSQL(tableName string, partitionNames []string) ([]string, error) {
	db := database.GetInstance()

	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		return nil, err
	}

	if tableInfo.PartitionInfo == nil {
		return nil, fmt.Errorf("table is not partitioned")
	}

	if len(partitionNames) < 2 {
		return nil, fmt.Errorf("at least 2 partitions required for merge")
	}

	var partitions []models.PartitionDef
	for _, name := range partitionNames {
		for _, p := range tableInfo.PartitionInfo.Partitions {
			if p.PartitionName == name {
				partitions = append(partitions, p)
				break
			}
		}
	}

	if len(partitions) != len(partitionNames) {
		return nil, fmt.Errorf("some partitions not found")
	}

	totalRows := int64(0)
	for _, p := range partitions {
		totalRows += p.TableRows
	}

	var sqls []string
	sqls = append(sqls, fmt.Sprintf("-- Merge %d partitions into one", len(partitionNames)))
	sqls = append(sqls, fmt.Sprintf("-- Total rows after merge: %d", totalRows))
	sqls = append(sqls, "")

	mergedPartition := generateMergedPartition(partitions, tableInfo.PartitionInfo.PartitionMethod)

	sqls = append(sqls, "-- Create new merged partition")
	sqls = append(sqls, GenerateAddPartitionSQL(tableName, mergedPartition))

	sqls = append(sqls, "")
	sqls = append(sqls, "-- Migrate data from old partitions")
	for _, oldP := range partitions {
		sqls = append(sqls, generateDataMigrationSQL(tableName, &oldP, &mergedPartition, tableInfo.PartitionInfo.PartitionExpr))
	}

	sqls = append(sqls, "")
	sqls = append(sqls, "-- Drop old partitions after verification")
	for _, name := range partitionNames {
		sqls = append(sqls, GenerateDropPartitionSQL(tableName, name))
	}

	return sqls, nil
}

func generateRangeSplitPartitions(oldPartition *models.PartitionDef, numParts int) []models.PartitionDef {
	var partitions []models.PartitionDef

	oldDesc := oldPartition.PartitionDescription
	if oldDesc == "MAXVALUE" {
		for i := 0; i < numParts; i++ {
			partitions = append(partitions, models.PartitionDef{
				PartitionName:        fmt.Sprintf("%s_%d", oldPartition.PartitionName, i+1),
				PartitionMethod:      oldPartition.PartitionMethod,
				PartitionExpression:  oldPartition.PartitionExpression,
				PartitionDescription: fmt.Sprintf("MAXVALUE /* placeholder - adjust based on your data */"),
				PartitionOrdinal:     i + 1,
				Comment:              fmt.Sprintf("Split from %s - part %d", oldPartition.PartitionName, i+1),
			})
		}
		return partitions
	}

	boundary := parseRangeValue(oldDesc)
	step := boundary / int64(numParts)

	for i := 0; i < numParts; i++ {
		partBoundary := step * int64(i+1)
		if strings.Contains(oldDesc, "TO_DAYS") {
			date := time.Unix(partBoundary, 0).Format("2006-01-02")
			partitions = append(partitions, models.PartitionDef{
				PartitionName:        fmt.Sprintf("%s_%d", oldPartition.PartitionName, i+1),
				PartitionMethod:      oldPartition.PartitionMethod,
				PartitionExpression:  oldPartition.PartitionExpression,
				PartitionDescription: fmt.Sprintf("TO_DAYS('%s')", date),
				PartitionOrdinal:     i + 1,
				Comment:              fmt.Sprintf("Split from %s - %s", oldPartition.PartitionName, date),
			})
		} else {
			partitions = append(partitions, models.PartitionDef{
				PartitionName:        fmt.Sprintf("%s_%d", oldPartition.PartitionName, i+1),
				PartitionMethod:      oldPartition.PartitionMethod,
				PartitionExpression:  oldPartition.PartitionExpression,
				PartitionDescription: fmt.Sprintf("%d", partBoundary),
				PartitionOrdinal:     i + 1,
				Comment:              fmt.Sprintf("Split from %s - values up to %d", oldPartition.PartitionName, partBoundary),
			})
		}
	}

	return partitions
}

func generateListSplitPartitions(oldPartition *models.PartitionDef, numParts int, tableName, partitionExpr string) []models.PartitionDef {
	var partitions []models.PartitionDef

	db := database.GetInstance()
	values, _ := db.ExecuteQuery(fmt.Sprintf(`
		SELECT DISTINCT %s as val FROM %s WHERE %s IS NOT NULL LIMIT 100
	`, partitionExpr, "`"+tableName+"`", partitionExpr))

	valuesPerPart := len(values) / numParts

	for i := 0; i < numParts; i++ {
		start := i * valuesPerPart
		end := start + valuesPerPart
		if i == numParts-1 {
			end = len(values)
		}

		var partVals []string
		for j := start; j < end; j++ {
			if v, ok := values[j]["val"]; ok {
				partVals = append(partVals, fmt.Sprintf("'%v'", v))
			}
		}

		partitions = append(partitions, models.PartitionDef{
			PartitionName:        fmt.Sprintf("%s_%d", oldPartition.PartitionName, i+1),
			PartitionMethod:      oldPartition.PartitionMethod,
			PartitionExpression:  oldPartition.PartitionExpression,
			PartitionDescription: strings.Join(partVals, ", "),
			PartitionOrdinal:     i + 1,
			Comment:              fmt.Sprintf("Split from %s - values group %d", oldPartition.PartitionName, i+1),
		})
	}

	return partitions
}

func generateMergedPartition(partitions []models.PartitionDef, method string) models.PartitionDef {
	var maxBoundary int64
	var minBoundary int64 = math.MaxInt64
	var partitionExpr string

	for _, p := range partitions {
		partitionExpr = p.PartitionExpression
		if p.PartitionDescription != "MAXVALUE" && p.PartitionDescription != "DEFAULT" {
			b := parseRangeValue(p.PartitionDescription)
			if b > maxBoundary {
				maxBoundary = b
			}
			if b < minBoundary {
				minBoundary = b
			}
		}
	}

	var desc string
	if method == "RANGE" || method == "RANGE_ID" {
		if strings.Contains(partitions[0].PartitionDescription, "TO_DAYS") {
			date := time.Unix(maxBoundary, 0).Format("2006-01-02")
			desc = fmt.Sprintf("TO_DAYS('%s')", date)
		} else {
			desc = fmt.Sprintf("%d", maxBoundary)
		}
	} else {
		var allValues []string
		for _, p := range partitions {
			if p.PartitionDescription != "DEFAULT" {
				allValues = append(allValues, p.PartitionDescription)
			}
		}
		desc = strings.Join(allValues, ", ")
	}

	return models.PartitionDef{
		PartitionName:        fmt.Sprintf("merged_%d", time.Now().Unix()),
		PartitionMethod:      method,
		PartitionExpression:  partitionExpr,
		PartitionDescription: desc,
		PartitionOrdinal:     1,
		Comment:              fmt.Sprintf("Merged from %d partitions: %s", len(partitions), strings.Join(getPartitionNames(partitions), ", ")),
	}
}

func generateDataMigrationSQL(tableName string, source, target *models.PartitionDef, partitionExpr string) string {
	column := extractPartitionColumn(partitionExpr)
	return fmt.Sprintf(`INSERT INTO \`%s\` SELECT * FROM \`%s\` PARTITION (%s) WHERE %s %s;`,
		tableName, tableName, source.PartitionName,
		generatePartitionCondition(column, target),
		fmt.Sprintf("AND `%s` IS NOT NULL", column))
}

func generatePartitionCondition(column string, partition *models.PartitionDef) string {
	desc := partition.PartitionDescription
	if desc == "MAXVALUE" {
		return "IS NOT NULL"
	}
	if desc == "DEFAULT" {
		return "IS NOT NULL"
	}
	if strings.Contains(desc, "TO_DAYS") {
		re := regexp.MustCompile(`TO_DAYS\('(.+?)'\)`).FindStringSubmatch(desc)
		if len(re) > 1 {
			return fmt.Sprintf("`%s` < '%s'", column, re[1])
		}
	}
	if num, err := parseRangeValue(desc); err == nil {
		return fmt.Sprintf("`%s` < %d", column, num)
	}
	return fmt.Sprintf("`%s` IN (%s)", column, desc)
}

func getPartitionNames(partitions []models.PartitionDef) []string {
	names := make([]string, len(partitions))
	for i, p := range partitions {
		names[i] = p.PartitionName
	}
	return names
}

func ExecutePartitionMigration(req PartitionMigrationRequest) (*MigrationResult, error) {
	db := database.GetInstance()
	result := &MigrationResult{
		Success:       false,
		SQLStatements: []string{},
	}

	startTime := time.Now()

	column := "id"
	tableInfo, err := db.GetTableInfo(req.TableName)
	if err == nil && tableInfo.PartitionInfo != nil {
		column = extractPartitionColumn(tableInfo.PartitionInfo.PartitionExpr)
	}

	batchSize := req.BatchSize
	if batchSize <= 0 {
		batchSize = 1000
	}

	migrateSQL := fmt.Sprintf(`
		INSERT IGNORE INTO \`%s\` PARTITION (%s)
		SELECT * FROM \`%s\` PARTITION (%s)
		WHERE %s LIMIT %d
	`, req.TableName, req.TargetPartition, req.TableName, req.SourcePartition,
		req.WhereCondition, batchSize)

	result.SQLStatements = append(result.SQLStatements, migrateSQL)

	var totalRows int64
	for {
		res, err := db.ExecuteSQL(migrateSQL)
		if err != nil {
			return result, err
		}
		affected, _ := res.RowsAffected()
		totalRows += affected
		if affected == 0 {
			break
		}
	}

	result.MigratedRows = totalRows

	if req.VerifyData {
		countSQL := fmt.Sprintf(`SELECT COUNT(*) as cnt FROM \`%s\` PARTITION (%s)`, req.TableName, req.TargetPartition)
		rows, err := db.ExecuteQuery(countSQL)
		if err == nil && len(rows) > 0 {
			if cnt, ok := rows[0]["cnt"].(int64); ok {
				result.VerifiedRows = cnt
			}
		}
	}

	countSourceSQL := fmt.Sprintf(`SELECT COUNT(*) as cnt FROM \`%s\` PARTITION (%s)`, req.TableName, req.SourcePartition)
	rows, err := db.ExecuteQuery(countSourceSQL)
	if err == nil && len(rows) > 0 {
		if cnt, ok := rows[0]["cnt"].(int64); ok {
			result.SourceEmpty = cnt == 0
		}
	}

	result.ExecutionTime = int64(time.Since(startTime).Seconds())
	result.Success = true

	return result, nil
}

func AnalyzeHotColdSeparation(tableName string, hotThresholdDays int) (*HotColdAnalysis, error) {
	db := database.GetInstance()

	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		return nil, err
	}

	if tableInfo.PartitionInfo == nil {
		return nil, fmt.Errorf("table is not partitioned")
	}

	analysis := &HotColdAnalysis{
		TableName:         tableName,
		HotThresholdDays:  hotThresholdDays,
	}

	cutoffDate := time.Now().AddDate(0, 0, -hotThresholdDays)

	for _, p := range tableInfo.PartitionInfo.Partitions {
		if p.PartitionDescription == "MAXVALUE" || p.PartitionDescription == "DEFAULT" {
			analysis.HotPartitions = append(analysis.HotPartitions, p)
			analysis.HotRows += p.TableRows
			analysis.HotSizeMB += float64(p.DataLength) / (1024 * 1024)
			continue
		}

		partitionDate := getPartitionDate(p)
		if partitionDate.After(cutoffDate) {
			analysis.HotPartitions = append(analysis.HotPartitions, p)
			analysis.HotRows += p.TableRows
			analysis.HotSizeMB += float64(p.DataLength) / (1024 * 1024)
		} else {
			analysis.ColdPartitions = append(analysis.ColdPartitions, p)
			analysis.ColdRows += p.TableRows
			analysis.ColdSizeMB += float64(p.DataLength) / (1024 * 1024)
		}
	}

	analysis.TotalRows = analysis.HotRows + analysis.ColdRows

	if len(analysis.ColdPartitions) > 0 {
		analysis.RecommendedAction = fmt.Sprintf("Consider archiving %d cold partitions containing %d rows (%.2f MB)",
			len(analysis.ColdPartitions), analysis.ColdRows, analysis.ColdSizeMB)
	} else {
		analysis.RecommendedAction = "All data is currently hot - no cold separation needed"
	}

	return analysis, nil
}

func getPartitionDate(p models.PartitionDef) time.Time {
	desc := p.PartitionDescription
	if strings.Contains(desc, "TO_DAYS") {
		re := regexp.MustCompile(`TO_DAYS\('(.+?)'\)`).FindStringSubmatch(desc)
		if len(re) > 1 {
			if t, err := time.Parse("2006-01-02", re[1]); err == nil {
				return t
			}
		}
	}

	if p.UpdateTime != "" {
		if t, err := time.Parse("2006-01-02 15:04:05", p.UpdateTime); err == nil {
			return t
		}
	}

	return time.Now()
}

func RunPerformanceBenchmark(req PerformanceBenchmarkRequest) (*PerformanceComparison, error) {
	db := database.GetInstance()
	comparison := &PerformanceComparison{
		TableName:    req.TableName,
		Improvements: make(map[string]float64),
	}

	runCount := req.RunCount
	if runCount <= 0 {
		runCount = 3
	}

	for _, query := range req.Queries {
		if req.BeforePartition {
			metric, err := benchmarkQuery(db, query, runCount)
			if err == nil {
				comparison.BeforeMetrics = append(comparison.BeforeMetrics, *metric)
			}
		}

		if req.AfterPartition {
			metric, err := benchmarkQuery(db, query, runCount)
			if err == nil {
				comparison.AfterMetrics = append(comparison.AfterMetrics, *metric)
			}
		}
	}

	totalGain := 0.0
	for i := range comparison.BeforeMetrics {
		if i < len(comparison.AfterMetrics) {
			before := comparison.BeforeMetrics[i].AvgTimeMs
			after := comparison.AfterMetrics[i].AvgTimeMs
			if before > 0 {
				gain := (before - after) / before * 100
				comparison.Improvements[comparison.BeforeMetrics[i].Query] = gain
				totalGain += gain
			}
		}
	}

	if len(comparison.BeforeMetrics) > 0 {
		comparison.OverallGain = totalGain / float64(len(comparison.BeforeMetrics))
	}

	return comparison, nil
}

func benchmarkQuery(db *database.DBManager, query string, runCount int) (*PerformanceMetric, error) {
	metric := &PerformanceMetric{
		Query: query,
	}

	totalTime := 0.0
	minTime := math.MaxFloat64
	maxTime := 0.0

	for i := 0; i < runCount; i++ {
		start := time.Now()
		_, err := db.ExecuteQuery(query)
		if err != nil {
			return nil, err
		}
		elapsed := float64(time.Since(start).Microseconds()) / 1000.0

		totalTime += elapsed
		if elapsed < minTime {
			minTime = elapsed
		}
		if elapsed > maxTime {
			maxTime = elapsed
		}
	}

	metric.AvgTimeMs = totalTime / float64(runCount)
	metric.MinTimeMs = minTime
	metric.MaxTimeMs = maxTime

	explainSQL := "EXPLAIN PARTITIONS " + query
	explainResult, err := db.ExecuteQuery(explainSQL)
	if err == nil && len(explainResult) > 0 {
		if partitions, ok := explainResult[0]["partitions"].(string); ok {
			parts := strings.Split(partitions, ",")
			metric.PartitionsScan = len(parts)
			if partitions != "" {
				metric.RowsExamined, _ = explainResult[0]["rows"].(int64)
			}
		}
		metric.ExecutionPlan = fmt.Sprintf("%v", explainResult)
	}

	return metric, nil
}

func GenerateResizePlan(req PartitionResizeRequest) (*PartitionResizeResult, error) {
	result := &PartitionResizeResult{
		Success:       false,
		OldPartitions: req.PartitionNames,
		Warnings: []string{
			"WARNING: Always backup data before resizing partitions",
			"WARNING: Verify data integrity after migration",
		},
	}

	var err error
	switch req.Operation {
	case "SPLIT":
		if len(req.PartitionNames) != 1 {
			return nil, fmt.Errorf("split requires exactly 1 partition name")
		}
		targetRows := req.TargetRowCount
		if targetRows <= 0 {
			targetRows = config.AppConfig.PartitionTargetRows
		}
		result.SqlStatements, err = GenerateSmartSplitPartitionSQL(req.TableName, req.PartitionNames[0], targetRows)
		result.NewPartitions = req.NewPartitionDefs
	case "MERGE":
		if len(req.PartitionNames) < 2 {
			return nil, fmt.Errorf("merge requires at least 2 partition names")
		}
		result.SqlStatements, err = GenerateSmartMergePartitionSQL(req.TableName, req.PartitionNames)
	default:
		return nil, fmt.Errorf("unsupported operation: %s", req.Operation)
	}

	if err != nil {
		return nil, err
	}

	result.Success = true
	return result, nil
}

func GenerateHotColdMigrationSQL(tableName string, coldPartitions []string, archivePath string) []string {
	var sqls []string

	sqls = append(sqls, "-- Hot/Cold Data Separation Script")
	sqls = append(sqls, fmt.Sprintf("-- Archive path: %s", archivePath))
	sqls = append(sqls, "")

	for _, p := range coldPartitions {
		sqls = append(sqls, fmt.Sprintf("-- Export partition %s to archive", p))
		sqls = append(sqls, fmt.Sprintf(`SELECT * INTO OUTFILE '%s/%s.csv' FROM \`%s\` PARTITION (%s);`,
			archivePath, p, tableName, p))
		sqls = append(sqls, "")
		sqls = append(sqls, fmt.Sprintf("-- Verify export before dropping"))
		sqls = append(sqls, GenerateDropPartitionSQL(tableName, p))
		sqls = append(sqls, "")
	}

	return sqls
}

func GenerateRebalancePartitionsSQL(tableName string, targetRows int64) ([]string, error) {
	db := database.GetInstance()

	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		return nil, err
	}

	if tableInfo.PartitionInfo == nil {
		return nil, fmt.Errorf("table is not partitioned")
	}

	var sqls []string
	sqls = append(sqls, "-- Partition Rebalancing Plan")
	sqls = append(sqls, fmt.Sprintf("-- Target rows per partition: %d", targetRows))
	sqls = append(sqls, "")

	for _, p := range tableInfo.PartitionInfo.Partitions {
		if p.TableRows > targetRows*2 {
			sqls = append(sqls, fmt.Sprintf("-- Partition %s has %d rows, needs split", p.PartitionName, p.TableRows))
			splitSQLs, err := GenerateSmartSplitPartitionSQL(tableName, p.PartitionName, targetRows)
			if err == nil {
				sqls = append(sqls, splitSQLs...)
			}
		}
		sqls = append(sqls, "")
	}

	var smallPartitions []models.PartitionDef
	for _, p := range tableInfo.PartitionInfo.Partitions {
		if p.TableRows < targetRows/2 && p.PartitionDescription != "MAXVALUE" {
			smallPartitions = append(smallPartitions, p)
		}
	}

	if len(smallPartitions) >= 2 {
		smallNames := getPartitionNames(smallPartitions)
		sqls = append(sqls, fmt.Sprintf("-- Merge %d small partitions: %s", len(smallNames), strings.Join(smallNames, ", ")))
		mergeSQLs, err := GenerateSmartMergePartitionSQL(tableName, smallNames)
		if err == nil {
			sqls = append(sqls, mergeSQLs...)
		}
	}

	return sqls, nil
}
