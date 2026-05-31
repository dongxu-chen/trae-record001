package partition

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"time"

	"mysql-partition-tool/analysis"
	"mysql-partition-tool/config"
	"mysql-partition-tool/database"
	"mysql-partition-tool/models"
)

type StrategyScore struct {
	Method     string
	Score      int
	Reason     string
	Expression string
	Column     string
}

func RecommendPartitionStrategy(tableName string) (*models.PartitionRecommendation, error) {
	db := database.GetInstance()

	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		return nil, fmt.Errorf("failed to get table info: %w", err)
	}

	stats, err := analysis.AnalyzeTableStats(tableName)
	if err != nil {
		return nil, fmt.Errorf("failed to analyze table stats: %w", err)
	}

	candidates := analysis.FindPartitionCandidateColumns(tableInfo)
	if len(candidates) == 0 {
		return &models.PartitionRecommendation{
			TableName:         tableName,
			RecommendedMethod: "NONE",
			Reason:            "No suitable columns found for partitioning",
			Confidence:        0,
		}, nil
	}

	var strategyScores []StrategyScore

	for _, col := range candidates {
		rangeScore := scoreRangePartition(tableInfo, stats, col)
		strategyScores = append(strategyScores, rangeScore)

		rangeIDScore := scoreRangeIDPartition(tableInfo, stats, col)
		strategyScores = append(strategyScores, rangeIDScore)

		listScore := scoreListPartition(tableInfo, stats, col)
		strategyScores = append(strategyScores, listScore)

		hashScore := scoreHashPartition(tableInfo, stats, col)
		strategyScores = append(strategyScores, hashScore)

		linearHashScore := scoreLinearHashPartition(tableInfo, stats, col)
		strategyScores = append(strategyScores, linearHashScore)

		keyScore := scoreKeyPartition(tableInfo, stats, col)
		strategyScores = append(strategyScores, keyScore)
	}

	sort.Slice(strategyScores, func(i, j int) bool {
		return strategyScores[i].Score > strategyScores[j].Score
	})

	best := strategyScores[0]

	samplePartitions, err := generateSamplePartitions(tableInfo, stats, best)
	if err != nil {
		return nil, err
	}

	estimatedPartitions := len(samplePartitions)
	perfGain := calculatePerformanceGain(stats, estimatedPartitions)

	var alternatives []models.AlternativeMethod
	seenMethods := make(map[string]bool)
	seenMethods[best.Method] = true

	for i := 1; i < len(strategyScores) && len(alternatives) < 5; i++ {
		if strategyScores[i].Score > 30 && !seenMethods[strategyScores[i].Method] {
			alternatives = append(alternatives, models.AlternativeMethod{
				Method:     strategyScores[i].Method,
				Reason:     strategyScores[i].Reason,
				Confidence: strategyScores[i].Score,
			})
			seenMethods[strategyScores[i].Method] = true
		}
	}

	return &models.PartitionRecommendation{
		TableName:         tableName,
		RecommendedMethod: best.Method,
		PartitionExpr:     best.Expression,
		PartitionColumn:   best.Column,
		Reason:            best.Reason,
		Confidence:        best.Score,
		EstimatedPartitions: estimatedPartitions,
		EstimatedPerfGain:  perfGain,
		SamplePartitions:   samplePartitions,
		AlternativeMethods: alternatives,
	}, nil
}

func scoreRangePartition(tableInfo *models.TableInfo, stats *models.TableStats, col models.ColumnInfo) StrategyScore {
	score := 0
	var reasons []string

	if analysis.IsDateTimeColumn(col.DataType) {
		score += 40
		reasons = append(reasons, "Date/time column is ideal for RANGE partitioning")

		if stats.ValueRange != nil {
			if vr, ok := stats.ValueRange.(map[string]interface{}); ok {
				if days, ok := vr["days"].(int); ok {
					if days > 365 {
						score += 20
						reasons = append(reasons, fmt.Sprintf("Data spans %d days, good for time-based partitioning", days))
					}
					if days > 30 {
						score += 15
					}
				}
			}
		}
	} else if analysis.IsIntegerColumn(col.DataType) {
		score += 30
		reasons = append(reasons, "Integer column suitable for RANGE partitioning")
	} else {
		return StrategyScore{Method: "RANGE", Score: 0, Reason: "Column type not suitable for RANGE", Column: col.ColumnName}
	}

	if stats.GrowthPerDay > 1000 {
		score += 20
		reasons = append(reasons, fmt.Sprintf("High growth rate (%d rows/day) benefits from partitioning", stats.GrowthPerDay))
	} else if stats.GrowthPerDay > 100 {
		score += 10
	}

	for _, pk := range tableInfo.PrimaryKeys {
		if col.ColumnName == pk {
			score += 15
			reasons = append(reasons, "Column is part of primary key")
			break
		}
	}

	if !col.IsNullable {
		score += 5
	}

	if stats.ValueDistinct > 100 {
		score += 10
	}

	var expr string
	if analysis.IsDateTimeColumn(col.DataType) {
		expr = fmt.Sprintf("TO_DAYS(`%s`)", col.ColumnName)
	} else {
		expr = fmt.Sprintf("`%s`", col.ColumnName)
	}

	if score > 100 {
		score = 100
	}

	return StrategyScore{
		Method:     "RANGE",
		Score:      score,
		Reason:     strings.Join(reasons, "; "),
		Expression: expr,
		Column:     col.ColumnName,
	}
}

func scoreListPartition(tableInfo *models.TableInfo, stats *models.TableStats, col models.ColumnInfo) StrategyScore {
	score := 0
	var reasons []string

	if analysis.IsStringColumn(col.DataType) || analysis.IsIntegerColumn(col.DataType) {
		score += 25
	} else {
		return StrategyScore{Method: "LIST", Score: 0, Reason: "Column type not suitable for LIST", Column: col.ColumnName}
	}

	if stats.ValueDistinct > 0 && stats.ValueDistinct < 100 {
		score += 40
		reasons = append(reasons, fmt.Sprintf("Low cardinality (%d distinct values) ideal for LIST partitioning", stats.ValueDistinct))
	} else if stats.ValueDistinct < 500 {
		score += 20
	} else {
		return StrategyScore{Method: "LIST", Score: 0, Reason: "High cardinality not suitable for LIST", Column: col.ColumnName}
	}

	hasEnumValues := strings.Contains(strings.ToLower(col.ColumnType), "enum")
	if hasEnumValues {
		score += 20
		reasons = append(reasons, "ENUM column type is perfect for LIST partitioning")
	}

	queryPatternScore := checkQueryPatterns(tableInfo.TableName, col.ColumnName)
	score += queryPatternScore

	if stats.TotalRows > config.AppConfig.PartitionThresholdRows {
		score += 15
	}

	if score > 100 {
		score = 100
	}

	expr := fmt.Sprintf("`%s`", col.ColumnName)

	return StrategyScore{
		Method:     "LIST",
		Score:      score,
		Reason:     strings.Join(reasons, "; "),
		Expression: expr,
		Column:     col.ColumnName,
	}
}

func scoreHashPartition(tableInfo *models.TableInfo, stats *models.TableStats, col models.ColumnInfo) StrategyScore {
	score := 0
	var reasons []string

	if analysis.IsIntegerColumn(col.DataType) {
		score += 35
		reasons = append(reasons, "Integer column ideal for HASH partitioning")
	} else if analysis.IsDateTimeColumn(col.DataType) {
		score += 20
		reasons = append(reasons, "Date column can be used with HASH partitioning")
	} else {
		return StrategyScore{Method: "HASH", Score: 0, Reason: "Column type not suitable for HASH", Column: col.ColumnName}
	}

	if stats.ValueDistinct > 1000 {
		score += 25
		reasons = append(reasons, fmt.Sprintf("High cardinality (%d values) good for uniform distribution", stats.ValueDistinct))
	}

	if stats.GrowthPerDay > 100 {
		score += 15
	}

	if tableInfo.PartitionInfo == nil {
		score += 10
		reasons = append(reasons, "Table not yet partitioned")
	}

	estimatedParts := int(math.Ceil(float64(stats.TotalRows) / float64(config.AppConfig.PartitionTargetRows)))
	if estimatedParts >= 4 && estimatedParts <= 64 {
		score += 15
		reasons = append(reasons, fmt.Sprintf("Optimal partition count estimated: %d", estimatedParts))
	}

	if score > 100 {
		score = 100
	}

	var expr string
	if analysis.IsDateTimeColumn(col.DataType) {
		expr = fmt.Sprintf("YEAR(`%s`)", col.ColumnName)
	} else {
		expr = fmt.Sprintf("`%s`", col.ColumnName)
	}

	return StrategyScore{
		Method:     "HASH",
		Score:      score,
		Reason:     strings.Join(reasons, "; "),
		Expression: expr,
		Column:     col.ColumnName,
	}
}

func checkQueryPatterns(tableName, columnName string) int {
	db := database.GetInstance()
	result, err := db.ExecuteQuery(fmt.Sprintf(`
		SELECT COUNT(*) as cnt 
		FROM information_schema.STATISTICS 
		WHERE TABLE_SCHEMA = DATABASE() 
		AND TABLE_NAME = '%s' 
		AND COLUMN_NAME = '%s'
	`, tableName, columnName))

	if err == nil && len(result) > 0 {
		if cnt, ok := result[0]["cnt"].(int64); ok && cnt > 0 {
			return 15
		}
	}
	return 0
}

func generateSamplePartitions(tableInfo *models.TableInfo, stats *models.TableStats, strategy StrategyScore) ([]models.PartitionDef, error) {
	var partitions []models.PartitionDef

	switch strategy.Method {
	case "RANGE":
		partitions = generateRangePartitions(tableInfo, stats, strategy)
	case "LIST":
		partitions = generateListPartitions(tableInfo, stats, strategy)
	case "HASH":
		partitions = generateHashPartitions(tableInfo, stats, strategy)
	}

	return partitions, nil
}

func generateRangePartitions(tableInfo *models.TableInfo, stats *models.TableStats, strategy StrategyScore) []models.PartitionDef {
	var partitions []models.PartitionDef

	if analysis.IsDateTimeColumn(strategy.Column) {
		now := time.Now()

		historyDays := config.AppConfig.PartitionHistoryDays
		futureDays := config.AppConfig.PartitionFutureDays

		startDate := now.AddDate(0, 0, -historyDays)
		endDate := now.AddDate(0, 0, futureDays)

		granularity := determineGranularity(historyDays + futureDays)

		switch granularity {
		case "year":
			for year := startDate.Year(); year <= endDate.Year(); year++ {
				nextYear := year + 1
				partitionDate := time.Date(nextYear, 1, 1, 0, 0, 0, 0, time.UTC)
				partitions = append(partitions, models.PartitionDef{
					PartitionName:        fmt.Sprintf("p%d", year),
					PartitionOrdinal:     len(partitions) + 1,
					PartitionMethod:      "RANGE",
					PartitionExpression:  strategy.Expression,
					PartitionDescription: fmt.Sprintf("TO_DAYS('%s')", partitionDate.Format("2006-01-02")),
					Comment:              fmt.Sprintf("Data for year %d", year),
				})
			}
		case "quarter":
			current := startDate
			for current.Before(endDate) {
				quarterStart := time.Date(current.Year(), ((current.Month()-1)/3)*3+1, 1, 0, 0, 0, 0, time.UTC)
				quarterEnd := quarterStart.AddDate(0, 3, 0)
				partitions = append(partitions, models.PartitionDef{
					PartitionName:        fmt.Sprintf("p%d_q%d", quarterStart.Year(), (quarterStart.Month()-1)/3+1),
					PartitionOrdinal:     len(partitions) + 1,
					PartitionMethod:      "RANGE",
					PartitionExpression:  strategy.Expression,
					PartitionDescription: fmt.Sprintf("TO_DAYS('%s')", quarterEnd.Format("2006-01-02")),
					Comment:              fmt.Sprintf("Data for Q%d %d", (quarterStart.Month()-1)/3+1, quarterStart.Year()),
				})
				current = quarterEnd
			}
		case "month":
			current := startDate
			for current.Before(endDate) {
				monthStart := time.Date(current.Year(), current.Month(), 1, 0, 0, 0, 0, time.UTC)
				monthEnd := monthStart.AddDate(0, 1, 0)
				partitions = append(partitions, models.PartitionDef{
					PartitionName:        fmt.Sprintf("p%s", monthStart.Format("2006_01")),
					PartitionOrdinal:     len(partitions) + 1,
					PartitionMethod:      "RANGE",
					PartitionExpression:  strategy.Expression,
					PartitionDescription: fmt.Sprintf("TO_DAYS('%s')", monthEnd.Format("2006-01-02")),
					Comment:              fmt.Sprintf("Data for %s", monthStart.Format("January 2006")),
				})
				current = monthEnd
			}
		default:
			current := startDate
			for current.Before(endDate) {
				weekStart := current
				weekEnd := weekStart.AddDate(0, 0, 7)
				partitions = append(partitions, models.PartitionDef{
					PartitionName:        fmt.Sprintf("p%s", weekStart.Format("2006_01_02")),
					PartitionOrdinal:     len(partitions) + 1,
					PartitionMethod:      "RANGE",
					PartitionExpression:  strategy.Expression,
					PartitionDescription: fmt.Sprintf("TO_DAYS('%s')", weekEnd.Format("2006-01-02")),
					Comment:              fmt.Sprintf("Week starting %s", weekStart.Format("2006-01-02")),
				})
				current = weekEnd
			}
		}

		partitions = append(partitions, models.PartitionDef{
			PartitionName:        "pmax",
			PartitionOrdinal:     len(partitions) + 1,
			PartitionMethod:      "RANGE",
			PartitionExpression:  strategy.Expression,
			PartitionDescription: "MAXVALUE",
			Comment:              "Catch-all partition for future data",
		})
	} else if analysis.IsIntegerColumn(strategy.Column) {
		minVal := toFloat64(stats.MinValue)
		maxVal := toFloat64(stats.MaxValue)

		if maxVal > minVal {
			targetPartitions := int(math.Ceil(float64(stats.TotalRows) / float64(config.AppConfig.PartitionTargetRows)))
			if targetPartitions < 4 {
				targetPartitions = 4
			}
			if targetPartitions > 64 {
				targetPartitions = 64
			}

			rangeVal := maxVal - minVal
			step := rangeVal / float64(targetPartitions)
			step = math.Ceil(step/float64(calculateMagnitude(step))) * float64(calculateMagnitude(step))

			current := minVal
			for i := 0; i < targetPartitions; i++ {
				upperBound := current + step
				partitions = append(partitions, models.PartitionDef{
					PartitionName:        fmt.Sprintf("p%d", int(current)),
					PartitionOrdinal:     i + 1,
					PartitionMethod:      "RANGE",
					PartitionExpression:  strategy.Expression,
					PartitionDescription: fmt.Sprintf("%d", int(upperBound)),
					Comment:              fmt.Sprintf("Values from %d to %d", int(current), int(upperBound)-1),
				})
				current = upperBound
			}

			partitions = append(partitions, models.PartitionDef{
				PartitionName:        "pmax",
				PartitionOrdinal:     len(partitions) + 1,
				PartitionMethod:      "RANGE",
				PartitionExpression:  strategy.Expression,
				PartitionDescription: "MAXVALUE",
				Comment:              "Catch-all partition for future data",
			})
		}
	}

	return partitions
}

func generateListPartitions(tableInfo *models.TableInfo, stats *models.TableStats, strategy StrategyScore) []models.PartitionDef {
	db := database.GetInstance()
	var partitions []models.PartitionDef

	query := fmt.Sprintf(`
		SELECT DISTINCT %s as val
		FROM %s
		WHERE %s IS NOT NULL
		LIMIT 50
	`, "`"+strategy.Column+"`", "`"+tableInfo.TableName+"`", "`"+strategy.Column+"`")

	rows, err := db.ExecuteQuery(query)
	if err != nil {
		return partitions
	}

	var values []string
	for _, row := range rows {
		if val, ok := row["val"]; ok && val != nil {
			values = append(values, fmt.Sprintf("'%v'", val))
		}
	}

	for i, val := range values {
		partitions = append(partitions, models.PartitionDef{
			PartitionName:        fmt.Sprintf("p%d", i),
			PartitionOrdinal:     i + 1,
			PartitionMethod:      "LIST",
			PartitionExpression:  strategy.Expression,
			PartitionDescription: val,
			Comment:              fmt.Sprintf("Partition for value: %v", val),
		})
	}

	partitions = append(partitions, models.PartitionDef{
		PartitionName:        "pdefault",
		PartitionOrdinal:     len(partitions) + 1,
		PartitionMethod:      "LIST",
		PartitionExpression:  strategy.Expression,
		PartitionDescription: "DEFAULT",
		Comment:              "Default partition for unlisted values",
	})

	return partitions
}

func generateHashPartitions(tableInfo *models.TableInfo, stats *models.TableStats, strategy StrategyScore) []models.PartitionDef {
	var partitions []models.PartitionDef

	numPartitions := int(math.Ceil(float64(stats.TotalRows) / float64(config.AppConfig.PartitionTargetRows)))
	if numPartitions < 4 {
		numPartitions = 4
	}
	if numPartitions > 64 {
		numPartitions = 64
	}

	for i := 0; i < numPartitions; i++ {
		partitions = append(partitions, models.PartitionDef{
			PartitionName:       fmt.Sprintf("p%d", i),
			PartitionOrdinal:    i + 1,
			PartitionMethod:     "HASH",
			PartitionExpression: strategy.Expression,
			Comment:             fmt.Sprintf("Hash partition %d of %d", i, numPartitions),
		})
	}

	return partitions
}

func determineGranularity(totalDays int) string {
	switch {
	case totalDays > 365*5:
		return "year"
	case totalDays > 365:
		return "quarter"
	case totalDays > 90:
		return "month"
	default:
		return "week"
	}
}

func calculateMagnitude(value float64) int {
	if value <= 0 {
		return 1
	}
	return int(math.Pow(10, math.Floor(math.Log10(value))))
}

func calculatePerformanceGain(stats *models.TableStats, numPartitions int) string {
	if numPartitions <= 1 {
		return "Minimal"
	}

	factor := int(math.Log2(float64(numPartitions)))
	switch {
	case factor >= 5:
		return "Significant (expected 50-80% improvement in partition pruning queries)"
	case factor >= 3:
		return "Moderate (expected 30-50% improvement in partition pruning queries)"
	default:
		return "Mild (expected 10-30% improvement in partition pruning queries)"
	}
}

func scoreRangeIDPartition(tableInfo *models.TableInfo, stats *models.TableStats, col models.ColumnInfo) StrategyScore {
	score := 0
	var reasons []string

	isIDColumn := strings.Contains(strings.ToLower(col.ColumnName), "id")
	isPrimaryKey := false
	for _, pk := range tableInfo.PrimaryKeys {
		if col.ColumnName == pk {
			isPrimaryKey = true
			break
		}
	}

	if !analysis.IsIntegerColumn(col.DataType) || (!isIDColumn && !isPrimaryKey) {
		return StrategyScore{Method: "RANGE_ID", Score: 0, Reason: "Column not suitable for ID-based RANGE partitioning", Column: col.ColumnName}
	}

	if isPrimaryKey {
		score += 35
		reasons = append(reasons, "Primary key column ideal for ID-based range partitioning")
	} else if isIDColumn {
		score += 25
		reasons = append(reasons, "ID column suitable for range partitioning")
	}

	minVal := toFloat64(stats.MinValue)
	maxVal := toFloat64(stats.MaxValue)
	valueRange := maxVal - minVal

	if valueRange > 1000000 {
		score += 25
		reasons = append(reasons, "Large ID range provides good distribution")
	} else if valueRange > 100000 {
		score += 15
	}

	if stats.GrowthPerDay > 1000 {
		score += 20
		reasons = append(reasons, fmt.Sprintf("High growth rate (%d rows/day) benefits from predictable ID ranges", stats.GrowthPerDay))
	} else if stats.GrowthPerDay > 100 {
		score += 10
	}

	if stats.ValueDistinct > 10000 {
		score += 10
		reasons = append(reasons, fmt.Sprintf("High cardinality (%d distinct IDs)", stats.ValueDistinct))
	}

	if !col.IsNullable {
		score += 5
	}

	if score > 100 {
		score = 100
	}

	return StrategyScore{
		Method:     "RANGE_ID",
		Score:      score,
		Reason:     strings.Join(reasons, "; "),
		Expression: fmt.Sprintf("`%s`", col.ColumnName),
		Column:     col.ColumnName,
	}
}

func scoreLinearHashPartition(tableInfo *models.TableInfo, stats *models.TableStats, col models.ColumnInfo) StrategyScore {
	score := 0
	var reasons []string

	if analysis.IsIntegerColumn(col.DataType) {
		score += 30
		reasons = append(reasons, "Integer column ideal for LINEAR HASH partitioning")
	} else if analysis.IsDateTimeColumn(col.DataType) {
		score += 20
		reasons = append(reasons, "Date column suitable for LINEAR HASH partitioning")
	} else {
		return StrategyScore{Method: "LINEAR_HASH", Score: 0, Reason: "Column type not suitable for LINEAR HASH", Column: col.ColumnName}
	}

	if stats.ValueDistinct > 1000 {
		score += 25
		reasons = append(reasons, fmt.Sprintf("High cardinality (%d values) for even distribution", stats.ValueDistinct))
	}

	estimatedParts := int(math.Ceil(float64(stats.TotalRows) / float64(config.AppConfig.PartitionTargetRows)))
	if estimatedParts >= 8 && estimatedParts <= 64 {
		score += 20
		reasons = append(reasons, fmt.Sprintf("Optimal for large partition counts (%d estimated)", estimatedParts))
	}

	if stats.GrowthPerDay > 500 {
		score += 15
		reasons = append(reasons, "Good for high-write workloads with linear scalability")
	}

	isPowerOfTwo := func(n int) bool {
		return n > 0 && (n&(n-1)) == 0
	}
	if isPowerOfTwo(estimatedParts) {
		score += 10
		reasons = append(reasons, "Partition count is power of 2, optimal for linear hash")
	}

	if score > 100 {
		score = 100
	}

	var expr string
	if analysis.IsDateTimeColumn(col.DataType) {
		expr = fmt.Sprintf("TO_DAYS(`%s`)", col.ColumnName)
	} else {
		expr = fmt.Sprintf("`%s`", col.ColumnName)
	}

	return StrategyScore{
		Method:     "LINEAR_HASH",
		Score:      score,
		Reason:     strings.Join(reasons, "; "),
		Expression: expr,
		Column:     col.ColumnName,
	}
}

func scoreKeyPartition(tableInfo *models.TableInfo, stats *models.TableStats, col models.ColumnInfo) StrategyScore {
	score := 0
	var reasons []string

	isPrimaryKey := false
	for _, pk := range tableInfo.PrimaryKeys {
		if col.ColumnName == pk {
			isPrimaryKey = true
			break
		}
	}

	isInUniqueKey := false
	for _, idx := range tableInfo.Indexes {
		if !idx.NonUnique && idx.ColumnName == col.ColumnName {
			isInUniqueKey = true
			break
		}
	}

	if !isPrimaryKey && !isInUniqueKey {
		return StrategyScore{Method: "KEY", Score: 0, Reason: "Column must be in primary key or unique key for KEY partitioning", Column: col.ColumnName}
	}

	if isPrimaryKey {
		score += 35
		reasons = append(reasons, "Primary key column is ideal for KEY partitioning")
	} else if isInUniqueKey {
		score += 25
		reasons = append(reasons, "Unique key column suitable for KEY partitioning")
	}

	if stats.ValueDistinct > 1000 {
		score += 25
		reasons = append(reasons, fmt.Sprintf("High cardinality (%d values) ensures even distribution", stats.ValueDistinct))
	}

	estimatedParts := int(math.Ceil(float64(stats.TotalRows) / float64(config.AppConfig.PartitionTargetRows)))
	if estimatedParts >= 4 && estimatedParts <= 32 {
		score += 15
		reasons = append(reasons, fmt.Sprintf("Good partition count range (%d estimated)", estimatedParts))
	}

	if stats.TotalRows > config.AppConfig.PartitionThresholdRows {
		score += 15
		reasons = append(reasons, "Large table benefits from KEY partitioning distribution")
	}

	if analysis.IsStringColumn(col.DataType) {
		score += 10
		reasons = append(reasons, "String columns work well with KEY partitioning hash algorithm")
	}

	if score > 100 {
		score = 100
	}

	return StrategyScore{
		Method:     "KEY",
		Score:      score,
		Reason:     strings.Join(reasons, "; "),
		Expression: fmt.Sprintf("`%s`", col.ColumnName),
		Column:     col.ColumnName,
	}
}

func toFloat64(v interface{}) float64 {
	if v == nil {
		return 0
	}
	switch val := v.(type) {
	case float64:
		return val
	case int64:
		return float64(val)
	case int:
		return float64(val)
	case string:
		f := 0.0
		fmt.Sscanf(val, "%f", &f)
		return f
	}
	return 0
}
