package api

import (
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
	"mysql-partition-tool/analysis"
	"mysql-partition-tool/database"
	"mysql-partition-tool/models"
	"mysql-partition-tool/partition"
)

type Response struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Message string      `json:"message,omitempty"`
	Error   string      `json:"error,omitempty"`
}

func respondSuccess(c *gin.Context, data interface{}) {
	c.JSON(http.StatusOK, Response{
		Success: true,
		Data:    data,
	})
}

func respondError(c *gin.Context, code int, message string, err error) {
	errMsg := ""
	if err != nil {
		errMsg = err.Error()
	}
	c.JSON(code, Response{
		Success: false,
		Message: message,
		Error:   errMsg,
	})
}

func TestConnection(c *gin.Context) {
	var cfg models.DBConfig
	if err := c.ShouldBindJSON(&cfg); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	db := database.GetInstance()
	if err := db.TestConnection(&cfg); err != nil {
		respondError(c, http.StatusBadRequest, "Connection failed", err)
		return
	}

	respondSuccess(c, gin.H{
		"status":   "connected",
		"host":     cfg.Host,
		"port":     cfg.Port,
		"database": cfg.Database,
	})
}

func Connect(c *gin.Context) {
	var cfg models.DBConfig
	if err := c.ShouldBindJSON(&cfg); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	db := database.GetInstance()
	if err := db.Connect(&cfg); err != nil {
		respondError(c, http.StatusBadRequest, "Connection failed", err)
		return
	}

	respondSuccess(c, gin.H{
		"status":   "connected",
		"host":     cfg.Host,
		"port":     cfg.Port,
		"database": cfg.Database,
	})
}

func GetConnectionStatus(c *gin.Context) {
	db := database.GetInstance()
	_, err := db.GetDB()
	if err != nil {
		respondSuccess(c, gin.H{
			"connected": false,
		})
		return
	}

	respondSuccess(c, gin.H{
		"connected": true,
	})
}

func Disconnect(c *gin.Context) {
	db := database.GetInstance()
	if err := db.Close(); err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to disconnect", err)
		return
	}

	respondSuccess(c, gin.H{
		"status": "disconnected",
	})
}

func GetTableList(c *gin.Context) {
	db := database.GetInstance()
	tables, err := db.GetTableList()
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to get table list", err)
		return
	}

	respondSuccess(c, tables)
}

func GetTableInfo(c *gin.Context) {
	tableName := c.Param("tableName")
	if tableName == "" {
		respondError(c, http.StatusBadRequest, "Table name is required", nil)
		return
	}

	db := database.GetInstance()
	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to get table info", err)
		return
	}

	stats, err := analysis.AnalyzeTableStats(tableName)
	if err == nil {
		tableInfo.Stats = stats
	}

	respondSuccess(c, tableInfo)
}

func GetTableStats(c *gin.Context) {
	tableName := c.Param("tableName")
	if tableName == "" {
		respondError(c, http.StatusBadRequest, "Table name is required", nil)
		return
	}

	stats, err := analysis.AnalyzeTableStats(tableName)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to analyze table stats", err)
		return
	}

	respondSuccess(c, stats)
}

func GetGrowthPrediction(c *gin.Context) {
	tableName := c.Param("tableName")
	if tableName == "" {
		respondError(c, http.StatusBadRequest, "Table name is required", nil)
		return
	}

	prediction, err := analysis.PredictGrowth(tableName)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to predict growth", err)
		return
	}

	respondSuccess(c, prediction)
}

func RecommendPartition(c *gin.Context) {
	tableName := c.Param("tableName")
	if tableName == "" {
		respondError(c, http.StatusBadRequest, "Table name is required", nil)
		return
	}

	recommendation, err := partition.RecommendPartitionStrategy(tableName)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to recommend partition strategy", err)
		return
	}

	respondSuccess(c, recommendation)
}

func GeneratePartitionPlan(c *gin.Context) {
	tableName := c.Param("tableName")
	method := c.Query("method")
	column := c.Query("column")

	if tableName == "" {
		respondError(c, http.StatusBadRequest, "Table name is required", nil)
		return
	}

	if method == "" {
		respondError(c, http.StatusBadRequest, "Partition method is required", nil)
		return
	}

	if column == "" {
		respondError(c, http.StatusBadRequest, "Partition column is required", nil)
		return
	}

	plan, err := partition.GeneratePartitionPlan(tableName, strings.ToUpper(method), column)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to generate partition plan", err)
		return
	}

	respondSuccess(c, plan)
}

func ExecutePartitionPlan(c *gin.Context) {
	var plan models.PartitionPlan
	if err := c.ShouldBindJSON(&plan); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	result, err := partition.ExecutePartitionPlan(&plan)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to execute partition plan", err)
		return
	}

	respondSuccess(c, result)
}

func ExecutePartitionOperation(c *gin.Context) {
	var req models.PartitionOperationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	result, err := partition.ExecutePartitionOperation(&req)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to execute partition operation", err)
		return
	}

	respondSuccess(c, result)
}

func RewriteQuery(c *gin.Context) {
	var req models.QueryRewriteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	result, err := partition.RewriteQuery(req)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to rewrite query", err)
		return
	}

	respondSuccess(c, result)
}

func AnalyzeQuery(c *gin.Context) {
	sql := c.Query("sql")
	tableName := c.Query("tableName")

	if sql == "" {
		respondError(c, http.StatusBadRequest, "SQL query is required", nil)
		return
	}

	result, err := partition.AnalyzeQuery(sql, tableName)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to analyze query", err)
		return
	}

	respondSuccess(c, result)
}

func GetAllTablesRecommendations(c *gin.Context) {
	db := database.GetInstance()
	tables, err := db.GetTableList()
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to get table list", err)
		return
	}

	var recommendations []map[string]interface{}
	for _, table := range tables {
		rec, err := partition.RecommendPartitionStrategy(table.TableName)
		if err != nil {
			continue
		}
		recommendations = append(recommendations, map[string]interface{}{
			"tableName":       table.TableName,
			"tableRows":       table.TableRows,
			"totalSizeMB":     float64(table.TotalSize) / (1024 * 1024),
			"recommendation":  rec,
		})
	}

	respondSuccess(c, recommendations)
}

func AutoExtendPartitions(c *gin.Context) {
	tableName := c.Param("tableName")
	if tableName == "" {
		respondError(c, http.StatusBadRequest, "Table name is required", nil)
		return
	}

	db := database.GetInstance()
	tableInfo, err := db.GetTableInfo(tableName)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to get table info", err)
		return
	}

	if tableInfo.PartitionInfo == nil {
		respondError(c, http.StatusBadRequest, "Table is not partitioned", nil)
		return
	}

	sqls := partition.GenerateAutoExtendPartitionSQL(tableName, tableInfo.PartitionInfo)

	respondSuccess(c, gin.H{
		"sqlStatements": sqls,
		"count":         len(sqls),
	})
}

func GetPartitionInfo(c *gin.Context) {
	tableName := c.Param("tableName")
	if tableName == "" {
		respondError(c, http.StatusBadRequest, "Table name is required", nil)
		return
	}

	db := database.GetInstance()
	partitionInfo, err := db.GetPartitionInfo(tableName)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to get partition info", err)
		return
	}

	respondSuccess(c, partitionInfo)
}

func CheckToolAvailability(c *gin.Context) {
	availability, err := partition.CheckToolAvailability()
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to check tool availability", err)
		return
	}

	respondSuccess(c, availability)
}

func GeneratePTOSCCommand(c *gin.Context) {
	var req partition.OnlineDDLRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	command := partition.GeneratePTOSCCommand(&req)
	dryRunCommand := partition.GenerateDryRunCommand(&req)

	respondSuccess(c, gin.H{
		"command":      command,
		"dryRunCommand": dryRunCommand,
	})
}

func ExecuteOnlineDDL(c *gin.Context) {
	var plan models.PartitionPlan
	if err := c.ShouldBindJSON(&plan); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	useOnlineDDL := c.DefaultQuery("useOnlineDDL", "true") == "true"

	result, err := partition.ExecuteOnlinePartitionPlan(&plan, useOnlineDDL)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Online DDL execution failed", err)
		return
	}

	respondSuccess(c, result)
}

func GenerateSplitPartition(c *gin.Context) {
	tableName := c.Param("tableName")
	partitionName := c.Query("partitionName")
	targetRowsStr := c.DefaultQuery("targetRows", "500000")
	targetRows, _ := strconv.ParseInt(targetRowsStr, 10, 64)

	if tableName == "" || partitionName == "" {
		respondError(c, http.StatusBadRequest, "Table name and partition name are required", nil)
		return
	}

	sqls, err := partition.GenerateSmartSplitPartitionSQL(tableName, partitionName, targetRows)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to generate split SQL", err)
		return
	}

	respondSuccess(c, gin.H{
		"sqlStatements": sqls,
		"tableName":     tableName,
		"partitionName": partitionName,
		"targetRows":    targetRows,
	})
}

func GenerateMergePartition(c *gin.Context) {
	var req struct {
		TableName      string   `json:"tableName" binding:"required"`
		PartitionNames []string `json:"partitionNames" binding:"required,min=2"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	sqls, err := partition.GenerateSmartMergePartitionSQL(req.TableName, req.PartitionNames)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to generate merge SQL", err)
		return
	}

	respondSuccess(c, gin.H{
		"sqlStatements":  sqls,
		"tableName":      req.TableName,
		"partitionNames": req.PartitionNames,
	})
}

func GenerateRebalancePartitions(c *gin.Context) {
	tableName := c.Param("tableName")
	targetRowsStr := c.DefaultQuery("targetRows", "500000")
	targetRows, _ := strconv.ParseInt(targetRowsStr, 10, 64)

	if tableName == "" {
		respondError(c, http.StatusBadRequest, "Table name is required", nil)
		return
	}

	sqls, err := partition.GenerateRebalancePartitionsSQL(tableName, targetRows)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to generate rebalance SQL", err)
		return
	}

	respondSuccess(c, gin.H{
		"sqlStatements": sqls,
		"tableName":     tableName,
		"targetRows":    targetRows,
	})
}

func ExecutePartitionMigration(c *gin.Context) {
	var req partition.PartitionMigrationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	result, err := partition.ExecutePartitionMigration(req)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Partition migration failed", err)
		return
	}

	respondSuccess(c, result)
}

func AnalyzeHotColdSeparation(c *gin.Context) {
	tableName := c.Param("tableName")
	thresholdStr := c.DefaultQuery("thresholdDays", "90")
	threshold, _ := strconv.Atoi(thresholdStr)

	if tableName == "" {
		respondError(c, http.StatusBadRequest, "Table name is required", nil)
		return
	}

	analysis, err := partition.AnalyzeHotColdSeparation(tableName, threshold)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to analyze hot/cold separation", err)
		return
	}

	respondSuccess(c, analysis)
}

func GenerateHotColdMigrationSQL(c *gin.Context) {
	var req struct {
		TableName     string   `json:"tableName" binding:"required"`
		ColdPartitions []string `json:"coldPartitions" binding:"required"`
		ArchivePath   string   `json:"archivePath" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	sqls := partition.GenerateHotColdMigrationSQL(req.TableName, req.ColdPartitions, req.ArchivePath)

	respondSuccess(c, gin.H{
		"sqlStatements":  sqls,
		"tableName":      req.TableName,
		"coldPartitions": req.ColdPartitions,
		"archivePath":    req.ArchivePath,
	})
}

func RunPerformanceBenchmark(c *gin.Context) {
	var req partition.PerformanceBenchmarkRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	result, err := partition.RunPerformanceBenchmark(req)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Performance benchmark failed", err)
		return
	}

	respondSuccess(c, result)
}

func GenerateResizePlan(c *gin.Context) {
	var req partition.PartitionResizeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		respondError(c, http.StatusBadRequest, "Invalid request body", err)
		return
	}

	result, err := partition.GenerateResizePlan(req)
	if err != nil {
		respondError(c, http.StatusInternalServerError, "Failed to generate resize plan", err)
		return
	}

	respondSuccess(c, result)
}
