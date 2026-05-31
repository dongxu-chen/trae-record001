package analysis

import (
	"fmt"
	"math"
	"strconv"
	"strings"
	"time"

	"mysql-partition-tool/config"
	"mysql-partition-tool/database"
	"mysql-partition-tool/models"
)

func AnalyzeTableStats(tableName string) (*models.TableStats, error) {
	db := database.GetInstance()

	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		return nil, fmt.Errorf("failed to get table info: %w", err)
	}

	stats := &models.TableStats{
		TotalRows:   tableInfo.TableRows,
		TotalSizeMB: float64(tableInfo.TotalSize) / (1024 * 1024),
	}

	if tableInfo.TableRows > 0 {
		stats.AvgRowSizeKB = float64(tableInfo.DataSize) / float64(tableInfo.TableRows) / 1024
	}

	candidateColumns := FindPartitionCandidateColumns(tableInfo)
	if len(candidateColumns) > 0 {
		bestColumn := candidateColumns[0]
		minVal, maxVal, distinctCount, err := db.GetColumnStats(tableName, bestColumn.ColumnName)
		if err == nil {
			stats.MinValue = minVal
			stats.MaxValue = maxVal
			stats.ValueDistinct = distinctCount

			if IsDateTimeColumn(bestColumn.DataType) {
				stats.ValueRange = calculateDateRange(minVal, maxVal)
			} else if isNumericColumn(bestColumn.DataType) {
				stats.ValueRange = calculateNumericRange(minVal, maxVal)
			}
		}

		dataPoints, err := analyzeGrowthByColumn(tableName, bestColumn)
		if err == nil && len(dataPoints) > 0 {
			stats.DataPoints = dataPoints
			growthRate := calculateGrowthRate(dataPoints)
			stats.GrowthPerDay = growthRate.Daily
			stats.GrowthPerWeek = growthRate.Weekly
			stats.GrowthPerMonth = growthRate.Monthly

			if growthRate.Daily > 0 {
				remainingRows := config.AppConfig.PartitionThresholdRows - tableInfo.TableRows
				if remainingRows > 0 {
					stats.EstimatedDaysToThreshold = int(remainingRows / growthRate.Daily)
				}
			}
		}
	}

	return stats, nil
}

func PredictGrowth(tableName string) (*models.GrowthPrediction, error) {
	db := database.GetInstance()

	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		return nil, err
	}

	stats, err := AnalyzeTableStats(tableName)
	if err != nil {
		return nil, err
	}

	prediction := &models.GrowthPrediction{
		TableName:   tableName,
		CurrentRows: tableInfo.TableRows,
	}

	threshold := config.AppConfig.PartitionThresholdRows

	if stats.GrowthPerDay <= 0 {
		prediction.GrowthRate = 0
		prediction.Predicted30Days = tableInfo.TableRows
		prediction.Predicted90Days = tableInfo.TableRows
		prediction.Predicted365Days = tableInfo.TableRows
		prediction.ShouldPartition = tableInfo.TableRows > threshold
	} else {
		dailyRate := float64(stats.GrowthPerDay)
		prediction.GrowthRate = dailyRate / float64(tableInfo.TableRows) * 100

		prediction.Predicted30Days = tableInfo.TableRows + stats.GrowthPerDay*30
		prediction.Predicted90Days = tableInfo.TableRows + stats.GrowthPerDay*90
		prediction.Predicted365Days = tableInfo.TableRows + stats.GrowthPerDay*365

		prediction.ShouldPartition = tableInfo.TableRows > threshold ||
			prediction.Predicted30Days > threshold
	}

	if prediction.ShouldPartition {
		if tableInfo.PartitionInfo != nil && len(tableInfo.PartitionInfo.Partitions) > 0 {
			prediction.RecommendedAction = "Review existing partition strategy and consider adding new partitions"
		} else {
			prediction.RecommendedAction = "Create partition strategy immediately"
		}
	} else if tableInfo.TableRows > threshold/2 {
		prediction.RecommendedAction = fmt.Sprintf("Monitor growth - expected to reach threshold in %d days",
			stats.EstimatedDaysToThreshold)
	} else {
		prediction.RecommendedAction = "No immediate action needed"
	}

	return prediction, nil
}

type growthRate struct {
	Daily   int64
	Weekly  int64
	Monthly int64
}

func calculateGrowthRate(dataPoints []models.DataPoint) growthRate {
	var rate growthRate
	if len(dataPoints) < 2 {
		return rate
	}

	first := dataPoints[0]
	last := dataPoints[len(dataPoints)-1]

	days := last.Date.Sub(first.Date).Hours() / 24
	if days <= 0 {
		return rate
	}

	totalGrowth := last.Value - first.Value
	if totalGrowth <= 0 {
		return rate
	}

	rate.Daily = int64(float64(totalGrowth) / days)
	rate.Weekly = rate.Daily * 7
	rate.Monthly = rate.Daily * 30

	return rate
}

func analyzeGrowthByColumn(tableName string, column models.ColumnInfo) ([]models.DataPoint, error) {
	db := database.GetInstance()

	if !IsDateTimeColumn(column.DataType) && !isNumericColumn(column.DataType) {
		return nil, fmt.Errorf("unsupported column type for growth analysis")
	}

	var query string
	if IsDateTimeColumn(column.DataType) {
		query = fmt.Sprintf(`
			SELECT 
				DATE(%s) as date_val,
				COUNT(*) as cnt
			FROM %s
			WHERE %s IS NOT NULL
			GROUP BY DATE(%s)
			ORDER BY date_val
			LIMIT 365
		`, "`"+column.ColumnName+"`", "`"+tableName+"`",
			"`"+column.ColumnName+"`", "`"+column.ColumnName+"`")
	} else {
		query = fmt.Sprintf(`
			SELECT 
				FLOOR(%s / 1000) * 1000 as range_val,
				COUNT(*) as cnt
			FROM %s
			WHERE %s IS NOT NULL
			GROUP BY range_val
			ORDER BY range_val
			LIMIT 100
		`, "`"+column.ColumnName+"`", "`"+tableName+"`",
			"`"+column.ColumnName+"`")
	}

	rows, err := db.ExecuteQuery(query)
	if err != nil {
		return nil, err
	}

	var points []models.DataPoint
	var cumulative int64

	for _, row := range rows {
		var dp models.DataPoint
		cumulative += toInt64(row["cnt"])

		if dateVal, ok := row["date_val"]; ok && dateVal != nil {
			dp.Date, _ = time.Parse("2006-01-02", toString(dateVal))
		} else {
			dp.Date = time.Now()
		}
		dp.Value = cumulative
		points = append(points, dp)
	}

	return points, nil
}

func FindPartitionCandidateColumns(tableInfo *models.TableInfo) []models.ColumnInfo {
	var candidates []models.ColumnInfo
	columnPriority := make(map[string]int)

	for _, col := range tableInfo.Columns {
		score := 0

		for _, pk := range tableInfo.PrimaryKeys {
			if col.ColumnName == pk {
				score += 10
				break
			}
		}

		for _, idx := range tableInfo.Indexes {
			if idx.ColumnName == col.ColumnName && !idx.NonUnique {
				score += 5
			} else if idx.ColumnName == col.ColumnName {
				score += 3
			}
		}

		if IsDateTimeColumn(col.DataType) {
			score += 15
		} else if IsIntegerColumn(col.DataType) {
			score += 10
		} else if isNumericColumn(col.DataType) {
			score += 5
		} else {
			continue
		}

		if strings.Contains(strings.ToLower(col.ColumnName), "time") ||
			strings.Contains(strings.ToLower(col.ColumnName), "date") ||
			strings.Contains(strings.ToLower(col.ColumnName), "created") ||
			strings.Contains(strings.ToLower(col.ColumnName), "updated") {
			score += 8
		}

		if strings.Contains(strings.ToLower(col.ColumnName), "id") && IsIntegerColumn(col.DataType) {
			score += 6
		}

		if !col.IsNullable {
			score += 2
		}

		columnPriority[col.ColumnName] = score
	}

	type scoredColumn struct {
		col   models.ColumnInfo
		score int
	}

	var scored []scoredColumn
	for _, col := range tableInfo.Columns {
		if score, ok := columnPriority[col.ColumnName]; ok && score > 0 {
			scored = append(scored, scoredColumn{col, score})
		}
	}

	for i := 0; i < len(scored)-1; i++ {
		for j := i + 1; j < len(scored); j++ {
			if scored[j].score > scored[i].score {
				scored[i], scored[j] = scored[j], scored[i]
			}
		}
	}

	for _, s := range scored {
		candidates = append(candidates, s.col)
	}

	return candidates
}

func IsDateTimeColumn(dataType string) bool {
	lower := strings.ToLower(dataType)
	return lower == "datetime" || lower == "date" || lower == "timestamp" ||
		lower == "time" || lower == "year"
}

func IsIntegerColumn(dataType string) bool {
	lower := strings.ToLower(dataType)
	return lower == "int" || lower == "bigint" || lower == "smallint" ||
		lower == "tinyint" || lower == "mediumint" || lower == "integer"
}

func isNumericColumn(dataType string) bool {
	return IsIntegerColumn(dataType) ||
		strings.Contains(strings.ToLower(dataType), "decimal") ||
		strings.Contains(strings.ToLower(dataType), "numeric") ||
		strings.Contains(strings.ToLower(dataType), "float") ||
		strings.Contains(strings.ToLower(dataType), "double")
}

func IsStringColumn(dataType string) bool {
	lower := strings.ToLower(dataType)
	return strings.Contains(lower, "char") || strings.Contains(lower, "text") ||
		strings.Contains(lower, "varchar") || strings.Contains(lower, "enum") ||
		strings.Contains(lower, "set")
}

func calculateDateRange(minVal, maxVal interface{}) map[string]interface{} {
	minStr := toString(minVal)
	maxStr := toString(maxVal)

	minTime, err1 := time.Parse("2006-01-02 15:04:05", minStr)
	if err1 != nil {
		minTime, _ = time.Parse("2006-01-02", minStr)
	}

	maxTime, err2 := time.Parse("2006-01-02 15:04:05", maxStr)
	if err2 != nil {
		maxTime, _ = time.Parse("2006-01-02", maxStr)
	}

	days := int(maxTime.Sub(minTime).Hours() / 24)

	return map[string]interface{}{
		"days":        days,
		"months":      days / 30,
		"years":       days / 365,
		"min":         minTime.Format("2006-01-02"),
		"max":         maxTime.Format("2006-01-02"),
		"recommended": getRecommendedRangePartition(days),
	}
}

func calculateNumericRange(minVal, maxVal interface{}) map[string]interface{} {
	minNum := toFloat64(minVal)
	maxNum := toFloat64(maxVal)
	rangeVal := maxNum - minNum

	step := calculateRangeStep(rangeVal)

	return map[string]interface{}{
		"min":         minNum,
		"max":         maxNum,
		"range":       rangeVal,
		"step":        step,
		"partitions":  int(math.Ceil(rangeVal / step)),
	}
}

func getRecommendedRangePartition(totalDays int) string {
	switch {
	case totalDays > 365*5:
		return "按年分区 (PARTITION BY RANGE YEAR(column))"
	case totalDays > 365:
		return "按季度分区 (PARTITION BY RANGE TO_DAYS(column))"
	case totalDays > 90:
		return "按月分区 (PARTITION BY RANGE TO_DAYS(column))"
	default:
		return "按周分区 (PARTITION BY RANGE TO_DAYS(column))"
	}
}

func calculateRangeStep(rangeVal float64) float64 {
	targetPartitions := 10.0
	rawStep := rangeVal / targetPartitions

	magnitude := math.Pow(10, math.Floor(math.Log10(rawStep)))
	normalized := rawStep / magnitude

	var step float64
	switch {
	case normalized < 2:
		step = 1
	case normalized < 5:
		step = 2
	case normalized < 10:
		step = 5
	default:
		step = 10
	}

	return step * magnitude
}

func toString(v interface{}) string {
	if v == nil {
		return ""
	}
	switch val := v.(type) {
	case string:
		return val
	case []byte:
		return string(val)
	default:
		return fmt.Sprintf("%v", val)
	}
}

func toInt64(v interface{}) int64 {
	if v == nil {
		return 0
	}
	switch val := v.(type) {
	case int:
		return int64(val)
	case int64:
		return val
	case string:
		if n, err := strconv.ParseInt(val, 10, 64); err == nil {
			return n
		}
	}
	return 0
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
		if n, err := strconv.ParseFloat(val, 64); err == nil {
			return n
		}
	}
	return 0
}
