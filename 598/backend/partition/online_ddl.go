package partition

import (
	"bytes"
	"fmt"
	"os/exec"
	"runtime"
	"strings"
	"time"

	"mysql-partition-tool/config"
	"mysql-partition-tool/database"
	"mysql-partition-tool/models"
)

type OnlineDDLRequest struct {
	TableName       string
	AlterStatement  string
	PartitionMethod string
	PartitionExpr   string
	Partitions      []models.PartitionDef
}

type OnlineDDLResponse struct {
	Success       bool
	Command       string
	Output        string
	ErrorOutput   string
	ExecutionTime int64
	Warnings      []string
}

type ToolAvailability struct {
	PTOSCAvailable bool
	PTOCSAvailable bool
	Path           string
	Version        string
}

func CheckToolAvailability() (*ToolAvailability, error) {
	result := &ToolAvailability{}

	ptoscPath, err := exec.LookPath("pt-online-schema-change")
	if err == nil {
		result.PTOSCAvailable = true
		result.Path = ptoscPath

		cmd := exec.Command("pt-online-schema-change", "--version")
		var out bytes.Buffer
		cmd.Stdout = &out
		if err := cmd.Run(); err == nil {
			result.Version = strings.TrimSpace(out.String())
		}
	}

	ptocPath, err := exec.LookPath("pt-table-checksum")
	if err == nil {
		result.PTOCSAvailable = true
	}

	return result, nil
}

func GeneratePTOSCCommand(request *OnlineDDLRequest) string {
	cfg := config.AppConfig

	dsn := fmt.Sprintf(
		"D=%s,h=%s,P=%s,u=%s,p=%s",
		cfg.DBName,
		cfg.DBHost,
		cfg.DBPort,
		cfg.DBUser,
		cfg.DBPassword,
	)

	alterStatement := request.AlterStatement
	if alterStatement == "" {
		alterStatement = generateAlterWithPartitioning(request.TableName, request.PartitionMethod, request.PartitionExpr, request.Partitions)
	}

	cmd := fmt.Sprintf(
		`pt-online-schema-change \
  --alter="%s" \
  --alter-foreign-keys-method=auto \
  --max-lag=1 \
  --chunk-time=0.5 \
  --max-load=Threads_running=25 \
  --critical-load=Threads_running=50 \
  --recursion-method=none \
  --print \
  --execute \
  "%s"`,
		escapeShellArg(alterStatement),
		dsn,
	)

	return cmd
}

func generateAlterWithPartitioning(tableName, method, expression string, partitions []models.PartitionDef) string {
	var partitionDefs []string
	for _, p := range partitions {
		switch method {
		case "RANGE", "RANGE_ID":
			partitionDefs = append(partitionDefs,
				fmt.Sprintf("PARTITION %s VALUES LESS THAN (%s) COMMENT = '%s'",
					p.PartitionName, p.PartitionDescription, escapeComment(p.Comment)))
		case "LIST":
			partitionDefs = append(partitionDefs,
				fmt.Sprintf("PARTITION %s VALUES IN (%s) COMMENT = '%s'",
					p.PartitionName, p.PartitionDescription, escapeComment(p.Comment)))
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
		return fmt.Sprintf("%s", byClause)
	}

	return fmt.Sprintf("%s (%s)", byClause, strings.Join(partitionDefs, ", "))
}

func ExecuteOnlineDDL(request *OnlineDDLRequest) (*OnlineDDLResponse, error) {
	response := &OnlineDDLResponse{
		Success: false,
		Warnings: []string{
			"WARNING: pt-online-schema-change requires Perl and Percona Toolkit",
			"WARNING: Ensure no other DDL operations are running on the table",
			"WARNING: Monitor replication lag during large table operations",
		},
	}

	toolCheck, err := CheckToolAvailability()
	if err != nil {
		response.ErrorOutput = fmt.Sprintf("Failed to check tool availability: %v", err)
		return response, err
	}

	if !toolCheck.PTOSCAvailable {
		response.ErrorOutput = "pt-online-schema-change not found. Please install Percona Toolkit."
		response.Warnings = append(response.Warnings,
			"pt-online-schema-change not available - falling back to direct ALTER TABLE")
		return executeFallbackDirectAlter(request, response)
	}

	command := GeneratePTOSCCommand(request)
	response.Command = command

	startTime := time.Now()

	cmd := buildPTOSCCommand(request)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err = cmd.Run()

	response.ExecutionTime = int64(time.Since(startTime).Seconds())
	response.Output = stdout.String()
	response.ErrorOutput = stderr.String()

	if err != nil {
		response.Success = false
		return response, fmt.Errorf("pt-online-schema-change failed: %s", stderr.String())
	}

	response.Success = true
	return response, nil
}

func buildPTOSCCommand(request *OnlineDDLRequest) *exec.Cmd {
	cfg := config.AppConfig

	dsn := fmt.Sprintf(
		"D=%s,h=%s,P=%s,u=%s,p=%s",
		cfg.DBName,
		cfg.DBHost,
		cfg.DBPort,
		cfg.DBUser,
		cfg.DBPassword,
	)

	alterStatement := request.AlterStatement
	if alterStatement == "" {
		alterStatement = generateAlterWithPartitioning(request.TableName, request.PartitionMethod, request.PartitionExpr, request.Partitions)
	}

	args := []string{
		fmt.Sprintf("--alter=%s", alterStatement),
		"--alter-foreign-keys-method=auto",
		"--max-lag=1",
		"--chunk-time=0.5",
		"--max-load=Threads_running=25",
		"--critical-load=Threads_running=50",
		"--recursion-method=none",
		"--print",
		"--execute",
		dsn,
	}

	if runtime.GOOS == "windows" {
		return exec.Command("pt-online-schema-change", args...)
	}
	return exec.Command("pt-online-schema-change", args...)
}

func executeFallbackDirectAlter(request *OnlineDDLRequest, response *OnlineDDLResponse) (*OnlineDDLResponse, error) {
	db := database.GetInstance()

	alterSQL := fmt.Sprintf("ALTER TABLE `%s` %s", request.TableName,
		generateAlterWithPartitioning(request.TableName, request.PartitionMethod, request.PartitionExpr, request.Partitions))

	response.Command = alterSQL
	response.Warnings = append(response.Warnings,
		"Using direct ALTER TABLE - this may lock the table during operation")

	startTime := time.Now()

	_, err := db.ExecuteSQL(alterSQL)

	response.ExecutionTime = int64(time.Since(startTime).Seconds())

	if err != nil {
		response.Success = false
		response.ErrorOutput = err.Error()
		return response, err
	}

	response.Success = true
	response.Output = "Direct ALTER TABLE executed successfully"
	return response, nil
}

func ExecuteOnlinePartitionPlan(plan *models.PartitionPlan, useOnlineDDL bool) (*OnlineDDLResponse, error) {
	if useOnlineDDL {
		request := &OnlineDDLRequest{
			TableName:       plan.TableName,
			PartitionMethod: plan.PartitionMethod,
			PartitionExpr:   plan.PartitionExpr,
			Partitions:      plan.Partitions,
		}
		return ExecuteOnlineDDL(request)
	}

	response := &OnlineDDLResponse{
		Success:  false,
		Warnings: []string{"Using direct ALTER TABLE execution"},
	}

	startTime := time.Now()

	_, err := ExecutePartitionPlan(plan)

	response.ExecutionTime = int64(time.Since(startTime).Seconds())

	if err != nil {
		response.ErrorOutput = err.Error()
		return response, err
	}

	response.Success = true
	response.Output = "Partition plan executed successfully"
	return response, nil
}

func GenerateDryRunCommand(request *OnlineDDLRequest) string {
	cfg := config.AppConfig

	dsn := fmt.Sprintf(
		"D=%s,h=%s,P=%s,u=%s,p=%s",
		cfg.DBName,
		cfg.DBHost,
		cfg.DBPort,
		cfg.DBUser,
		cfg.DBPassword,
	)

	alterStatement := request.AlterStatement
	if alterStatement == "" {
		alterStatement = generateAlterWithPartitioning(request.TableName, request.PartitionMethod, request.PartitionExpr, request.Partitions)
	}

	cmd := fmt.Sprintf(
		`pt-online-schema-change \
  --alter="%s" \
  --alter-foreign-keys-method=auto \
  --dry-run \
  --print \
  "%s"`,
		escapeShellArg(alterStatement),
		dsn,
	)

	return cmd
}

func escapeShellArg(s string) string {
	s = strings.ReplaceAll(s, `\`, `\\`)
	s = strings.ReplaceAll(s, `"`, `\"`)
	s = strings.ReplaceAll(s, "`", "\\`")
	return s
}
