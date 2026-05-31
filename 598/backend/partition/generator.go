package partition

import (
	"fmt"
	"strings"
	"time"

	"mysql-partition-tool/analysis"
	"mysql-partition-tool/config"
	"mysql-partition-tool/database"
	"mysql-partition-tool/models"
)

func GeneratePartitionPlan(tableName string, method string, columnName string) (*models.PartitionPlan, error) {
	db := database.GetInstance()

	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		return nil, fmt.Errorf("failed to get table info: %w", err)
	}

	stats, err := analysis.AnalyzeTableStats(tableName)
	if err != nil {
		return nil, fmt.Errorf("failed to analyze table stats: %w", err)
	}

	strategy := StrategyScore{
		Method: method,
		Column: columnName,
	}

	switch method {
	case "RANGE", "RANGE_ID":
		if analysis.IsDateTimeColumn(columnName) {
			strategy.Expression = fmt.Sprintf("TO_DAYS(`%s`)", columnName)
		} else {
			strategy.Expression = fmt.Sprintf("`%s`", columnName)
		}
	case "LIST":
		strategy.Expression = fmt.Sprintf("`%s`", columnName)
	case "HASH", "LINEAR_HASH":
		if analysis.IsDateTimeColumn(columnName) {
			strategy.Expression = fmt.Sprintf("TO_DAYS(`%s`)", columnName)
		} else {
			strategy.Expression = fmt.Sprintf("`%s`", columnName)
		}
	case "KEY":
		strategy.Expression = fmt.Sprintf("`%s`", columnName)
	default:
		strategy.Expression = fmt.Sprintf("`%s`", columnName)
	}

	partitions, err := generateSamplePartitions(tableInfo, stats, strategy)
	if err != nil {
		return nil, err
	}

	sqlStatements := generatePartitionSQL(tableName, method, strategy.Expression, partitions, tableInfo)

	estimatedTime := estimateExecutionTime(stats, len(partitions))

	return &models.PartitionPlan{
		TableName:       tableName,
		PartitionMethod: method,
		PartitionExpr:   strategy.Expression,
		PartitionColumn: columnName,
		Partitions:      partitions,
		SqlStatements:   sqlStatements,
		EstimatedTimeSec: estimatedTime,
	}, nil
}

func generatePartitionSQL(tableName, method, expression string, partitions []models.PartitionDef, tableInfo *models.TableInfo) []string {
	var sqls []string

	if tableInfo.PartitionInfo != nil && len(tableInfo.PartitionInfo.Partitions) > 0 {
		sqls = append(sqls, fmt.Sprintf("ALTER TABLE `%s` REMOVE PARTITIONING;", tableName))
	}

	sqls = append(sqls, "-- Partition SQL Generated at "+time.Now().Format("2006-01-02 15:04:05"))
	sqls = append(sqls, fmt.Sprintf("-- Method: %s, Expression: %s", method, expression))
	sqls = append(sqls, "-- Make sure to backup your data before executing!")
	sqls = append(sqls, "")

	var partitionDefs []string
	for _, p := range partitions {
		switch method {
		case "RANGE", "RANGE_ID":
			partitionDefs = append(partitionDefs,
				fmt.Sprintf("  PARTITION %s VALUES LESS THAN (%s) COMMENT = '%s'",
					p.PartitionName, p.PartitionDescription, escapeComment(p.Comment)))
		case "LIST":
			partitionDefs = append(partitionDefs,
				fmt.Sprintf("  PARTITION %s VALUES IN (%s) COMMENT = '%s'",
					p.PartitionName, p.PartitionDescription, escapeComment(p.Comment)))
		case "HASH", "LINEAR_HASH", "KEY":
			partitionDefs = append(partitionDefs,
				fmt.Sprintf("  PARTITION %s COMMENT = '%s'",
					p.PartitionName, escapeComment(p.Comment)))
		}
	}

	var byClause string
	switch method {
	case "RANGE", "RANGE_ID":
		byClause = fmt.Sprintf("PARTITION BY RANGE (%s)", expression)
	case "LIST":
		byClause = fmt.Sprintf("PARTITION BY LIST (%s)", expression)
	case "HASH":
		byClause = fmt.Sprintf("PARTITION BY HASH (%s) PARTITIONS %d", expression, len(partitions))
	case "LINEAR_HASH":
		byClause = fmt.Sprintf("PARTITION BY LINEAR HASH (%s) PARTITIONS %d", expression, len(partitions))
	case "KEY":
		byClause = fmt.Sprintf("PARTITION BY KEY (%s) PARTITIONS %d", expression, len(partitions))
	}

	if method == "HASH" || method == "LINEAR_HASH" || method == "KEY" {
		sql := fmt.Sprintf("ALTER TABLE `%s`\n%s;", tableName, byClause)
		sqls = append(sqls, sql)
	} else {
		sql := fmt.Sprintf("ALTER TABLE `%s`\n%s\n(\n%s\n);",
			tableName, byClause, strings.Join(partitionDefs, ",\n"))
		sqls = append(sqls, sql)
	}

	sqls = append(sqls, "")
	sqls = append(sqls, "-- Verification queries")
	sqls = append(sqls, fmt.Sprintf("SELECT PARTITION_NAME, TABLE_ROWS, DATA_LENGTH FROM information_schema.PARTITIONS WHERE TABLE_NAME = '%s';", tableName))
	sqls = append(sqls, fmt.Sprintf("EXPLAIN PARTITIONS SELECT * FROM `%s` LIMIT 1;", tableName))

	return sqls
}

func GenerateAddPartitionSQL(tableName string, newPartition models.PartitionDef) string {
	return fmt.Sprintf("ALTER TABLE `%s` ADD PARTITION (\n  PARTITION %s VALUES LESS THAN (%s) COMMENT = '%s'\n);",
		tableName, newPartition.PartitionName, newPartition.PartitionDescription, escapeComment(newPartition.Comment))
}

func GenerateDropPartitionSQL(tableName, partitionName string) string {
	return fmt.Sprintf("ALTER TABLE `%s` DROP PARTITION %s;", tableName, partitionName)
}

func GenerateMergePartitionSQL(tableName string, partitionNames []string, newPartition models.PartitionDef) []string {
	var sqls []string
	for _, p := range partitionNames {
		sqls = append(sqls, fmt.Sprintf("ALTER TABLE `%s` DROP PARTITION %s;", tableName, p))
	}
	sqls = append(sqls, GenerateAddPartitionSQL(tableName, newPartition))
	return sqls
}

func GenerateSplitPartitionSQL(tableName string, oldPartition string, newPartitions []models.PartitionDef) []string {
	var sqls []string
	sqls = append(sqls, fmt.Sprintf("ALTER TABLE `%s` DROP PARTITION %s;", tableName, oldPartition))
	for _, p := range newPartitions {
		sqls = append(sqls, GenerateAddPartitionSQL(tableName, p))
	}
	return sqls
}

func GenerateAutoExtendPartitionSQL(tableName string, partitionInfo *models.PartitionInfo) []string {
	var sqls []string

	if partitionInfo == nil || len(partitionInfo.Partitions) == 0 {
		return sqls
	}

	method := partitionInfo.PartitionMethod
	lastPartition := partitionInfo.Partitions[len(partitionInfo.Partitions)-1]

	if method == "RANGE" && lastPartition.PartitionDescription != "MAXVALUE" {
		futureDays := config.AppConfig.PartitionFutureDays
		now := time.Now()

		for i := 1; i <= futureDays/30+1; i++ {
			nextMonth := now.AddDate(0, i, 0)
			firstOfMonth := time.Date(nextMonth.Year(), nextMonth.Month(), 1, 0, 0, 0, 0, time.UTC)

			exists := false
			for _, p := range partitionInfo.Partitions {
				desc := strings.TrimSpace(p.PartitionDescription)
				if strings.Contains(desc, firstOfMonth.Format("2006-01-02")) {
					exists = true
					break
				}
			}

			if !exists {
				newPartition := models.PartitionDef{
					PartitionName:        fmt.Sprintf("p%s", firstOfMonth.Format("2006_01")),
					PartitionMethod:      "RANGE",
					PartitionExpression:  partitionInfo.PartitionExpr,
					PartitionDescription: fmt.Sprintf("TO_DAYS('%s')", firstOfMonth.Format("2006-01-02")),
					Comment:              fmt.Sprintf("Data for %s", firstOfMonth.Format("January 2006")),
				}
				sqls = append(sqls, GenerateAddPartitionSQL(tableName, newPartition))
			}
		}
	}

	return sqls
}

func ExecutePartitionPlan(plan *models.PartitionPlan) (*models.PartitionOperationResponse, error) {
	db := database.GetInstance()

	response := &models.PartitionOperationResponse{
		Success: false,
		Warnings: []string{
			"WARNING: Partition operations can be time-consuming for large tables",
			"WARNING: Always backup data before performing partition operations",
		},
	}

	for _, sql := range plan.SqlStatements {
		if strings.HasPrefix(sql, "--") || strings.TrimSpace(sql) == "" {
			continue
		}

		response.SqlExecuted = append(response.SqlExecuted, sql)

		_, err := db.ExecuteSQL(sql)
		if err != nil {
			response.Message = fmt.Sprintf("Failed to execute SQL: %v", err)
			return response, err
		}
	}

	response.Success = true
	response.Message = "Partition plan executed successfully"

	return response, nil
}

func ExecutePartitionOperation(req *models.PartitionOperationRequest) (*models.PartitionOperationResponse, error) {
	db := database.GetInstance()

	response := &models.PartitionOperationResponse{
		Success: false,
		Warnings: []string{
			"WARNING: Partition operations can be time-consuming for large tables",
			"WARNING: Always backup data before performing partition operations",
		},
	}

	var sqls []string

	switch req.Operation {
	case "ADD":
		for _, p := range req.NewPartitions {
			sqls = append(sqls, GenerateAddPartitionSQL(req.TableName, p))
		}
	case "DROP":
		for _, p := range req.PartitionNames {
			sqls = append(sqls, GenerateDropPartitionSQL(req.TableName, p))
		}
	case "MERGE":
		if len(req.PartitionNames) < 2 || len(req.NewPartitions) < 1 {
			return nil, fmt.Errorf("merge operation requires at least 2 source partitions and 1 target partition")
		}
		sqls = GenerateMergePartitionSQL(req.TableName, req.PartitionNames, req.NewPartitions[0])
	case "SPLIT":
		if len(req.PartitionNames) != 1 || len(req.NewPartitions) < 2 {
			return nil, fmt.Errorf("split operation requires 1 source partition and at least 2 target partitions")
		}
		sqls = GenerateSplitPartitionSQL(req.TableName, req.PartitionNames[0], req.NewPartitions)
	case "TRUNCATE":
		for _, p := range req.PartitionNames {
			sqls = append(sqls, fmt.Sprintf("ALTER TABLE `%s` TRUNCATE PARTITION %s;", req.TableName, p))
		}
	case "OPTIMIZE":
		for _, p := range req.PartitionNames {
			sqls = append(sqls, fmt.Sprintf("ALTER TABLE `%s` OPTIMIZE PARTITION %s;", req.TableName, p))
		}
	case "REBUILD":
		for _, p := range req.PartitionNames {
			sqls = append(sqls, fmt.Sprintf("ALTER TABLE `%s` REBUILD PARTITION %s;", req.TableName, p))
		}
	case "CHECK":
		for _, p := range req.PartitionNames {
			sqls = append(sqls, fmt.Sprintf("ALTER TABLE `%s` CHECK PARTITION %s;", req.TableName, p))
		}
	default:
		return nil, fmt.Errorf("unsupported operation: %s", req.Operation)
	}

	for _, sql := range sqls {
		response.SqlExecuted = append(response.SqlExecuted, sql)

		_, err := db.ExecuteSQL(sql)
		if err != nil {
			response.Message = fmt.Sprintf("Failed to execute SQL: %v", err)
			return response, err
		}
	}

	response.Success = true
	response.Message = fmt.Sprintf("%s operation completed successfully", req.Operation)

	return response, nil
}

func estimateExecutionTime(stats *models.TableStats, numPartitions int) int {
	rowsPerSecond := float64(10000)
	if stats.AvgRowSizeKB > 10 {
		rowsPerSecond = float64(5000)
	} else if stats.AvgRowSizeKB > 100 {
		rowsPerSecond = float64(1000)
	}

	estimatedSeconds := float64(stats.TotalRows) / rowsPerSecond
	estimatedSeconds += float64(numPartitions) * 5

	return int(estimatedSeconds)
}

func escapeComment(comment string) string {
	comment = strings.ReplaceAll(comment, "'", "\\'")
	comment = strings.ReplaceAll(comment, "\n", " ")
	return comment
}
