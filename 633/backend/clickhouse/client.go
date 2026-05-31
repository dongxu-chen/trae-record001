package clickhouse

import (
	"context"
	"database/sql"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"

	"clickhouse-rate-limiter/config"

	_ "github.com/ClickHouse/clickhouse-go"
)

type Client struct {
	db     *sql.DB
	config config.ClickHouseConfig
}

type QueryResult struct {
	Data       []map[string]interface{}
	Columns    []string
	ScanRows   int64
	MemoryUsed int64
	Duration   time.Duration
	Error      error
}

func NewClient(cfg config.ClickHouseConfig) (*Client, error) {
	dsn := fmt.Sprintf("tcp://%s?username=%s&password=%s&database=%s",
		cfg.Address, cfg.Username, cfg.Password, cfg.Database)

	db, err := sql.Open("clickhouse", dsn)
	if err != nil {
		return nil, err
	}

	if err := db.Ping(); err != nil {
		return nil, err
	}

	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(time.Hour)

	return &Client{
		db:     db,
		config: cfg,
	}, nil
}

func (c *Client) ExecuteQuery(ctx context.Context, query string, userID string) *QueryResult {
	startTime := time.Now()
	result := &QueryResult{}

	ctx, cancel := context.WithTimeout(ctx, c.config.Timeout)
	defer cancel()

	tx, err := c.db.BeginTx(ctx, nil)
	if err != nil {
		result.Error = err
		return result
	}
	defer tx.Rollback()

	rows, err := tx.QueryContext(ctx, query)
	if err != nil {
		result.Error = err
		return result
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		result.Error = err
		return result
	}
	result.Columns = columns

	columnTypes, err := rows.ColumnTypes()
	if err != nil {
		result.Error = err
		return result
	}

	for rows.Next() {
		values := make([]interface{}, len(columnTypes))
		valuePtrs := make([]interface{}, len(columnTypes))
		for i := range values {
			valuePtrs[i] = &values[i]
		}

		if err := rows.Scan(valuePtrs...); err != nil {
			result.Error = err
			return result
		}

		row := make(map[string]interface{})
		for i, col := range columns {
			row[col] = values[i]
		}
		result.Data = append(result.Data, row)
		result.ScanRows++
	}

	result.Duration = time.Since(startTime)
	result.MemoryUsed = estimateMemoryUsage(result.ScanRows, len(columns))

	return result
}

func (c *Client) Close() error {
	return c.db.Close()
}

func (c *Client) GetQueryProfile(ctx context.Context, query string) (int64, int64, error) {
	explainQuery := fmt.Sprintf("EXPLAIN ESTIMATE %s", query)
	
	var scanRows, memoryBytes int64
	err := c.db.QueryRowContext(ctx, explainQuery).Scan(&scanRows, &memoryBytes)
	if err != nil {
		return 0, 0, err
	}
	
	return scanRows, memoryBytes, nil
}

type ExplainPlan struct {
	Database        string
	Table           string
	EstimatedRows   int64
	EstimatedCost   float64
	EstimatedMemory int64
	QueryPlan       string
	Stages          []PlanStage
}

type PlanStage struct {
	Name        string
	Description string
	Rows        int64
	Cost        float64
	Memory      int64
	Children    []PlanStage
}

func (c *Client) GetExplainPlan(ctx context.Context, query string) (*ExplainPlan, error) {
	plan := &ExplainPlan{
		Stages: make([]PlanStage, 0),
	}

	headerQuery := fmt.Sprintf("EXPLAIN HEADER %s", query)
	var header string
	err := c.db.QueryRowContext(ctx, headerQuery).Scan(&header)
	if err == nil {
		plan.QueryPlan = header
	}

	jsonQuery := fmt.Sprintf("EXPLAIN JSON %s", query)
	var jsonPlan string
	err = c.db.QueryRowContext(ctx, jsonQuery).Scan(&jsonPlan)
	if err == nil {
		parseJSONPlan(jsonPlan, plan)
	}

	estimateQuery := fmt.Sprintf("EXPLAIN ESTIMATE %s", query)
	var scanRows, memoryBytes int64
	err = c.db.QueryRowContext(ctx, estimateQuery).Scan(&scanRows, &memoryBytes)
	if err == nil {
		plan.EstimatedRows = scanRows
		plan.EstimatedMemory = memoryBytes
		plan.EstimatedCost = calculateCost(scanRows, memoryBytes)
	}

	plan.Stages = parsePlanStages(plan.QueryPlan)

	return plan, nil
}

func calculateCost(rows int64, memory int64) float64 {
	cost := float64(rows) * 0.001
	cost += float64(memory) / 1024.0 / 1024.0 * 0.1
	return cost
}

func parseJSONPlan(jsonStr string, plan *ExplainPlan) {
	rowsRegex := regexp.MustCompile(`"estimated_rows"\s*:\s*(\d+)`)
	costRegex := regexp.MustCompile(`"estimated_cost"\s*:\s*([\d.]+)`)
	memoryRegex := regexp.MustCompile(`"memory_usage"\s*:\s*(\d+)`)

	if match := rowsRegex.FindStringSubmatch(jsonStr); len(match) > 1 {
		if rows, err := strconv.ParseInt(match[1], 10, 64); err == nil && rows > 0 {
			plan.EstimatedRows = rows
		}
	}

	if match := costRegex.FindStringSubmatch(jsonStr); len(match) > 1 {
		if cost, err := strconv.ParseFloat(match[1], 64); err == nil && cost > 0 {
			plan.EstimatedCost = cost
		}
	}

	if match := memoryRegex.FindStringSubmatch(jsonStr); len(match) > 1 {
		if memory, err := strconv.ParseInt(match[1], 10, 64); err == nil && memory > 0 {
			plan.EstimatedMemory = memory
		}
	}
}

func parsePlanStages(planText string) []PlanStage {
	stages := make([]PlanStage, 0)
	lines := strings.Split(planText, "\n")

	currentStage := &PlanStage{}
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		if strings.HasPrefix(line, "Union") || strings.HasPrefix(line, "MergeTree") ||
			strings.HasPrefix(line, "Filter") || strings.HasPrefix(line, "Aggregating") ||
			strings.HasPrefix(line, "Sorting") || strings.HasPrefix(line, "Expression") ||
			strings.HasPrefix(line, "Join") || strings.HasPrefix(line, "Read") {

			if currentStage.Name != "" {
				stages = append(stages, *currentStage)
			}

			parts := strings.SplitN(line, " ", 2)
			currentStage = &PlanStage{
				Name:        parts[0],
				Description: line,
			}

			rowsMatch := regexp.MustCompile(`rows\s*=\s*(\d+)`).FindStringSubmatch(line)
			if len(rowsMatch) > 1 {
				if rows, err := strconv.ParseInt(rowsMatch[1], 10, 64); err == nil {
					currentStage.Rows = rows
				}
			}
		}
	}

	if currentStage.Name != "" {
		stages = append(stages, *currentStage)
	}

	return stages
}

func estimateMemoryUsage(rows int64, columns int) int64 {
	avgBytesPerColumn := int64(64)
	return rows * int64(columns) * avgBytesPerColumn
}
