package models

import (
	"time"
)

type DBConfig struct {
	Host     string `json:"host"`
	Port     string `json:"port"`
	User     string `json:"user"`
	Password string `json:"password"`
	Database string `json:"database"`
}

type TableInfo struct {
	TableName      string    `json:"tableName"`
	TableRows      int64     `json:"tableRows"`
	DataSize       int64     `json:"dataSize"`
	IndexSize      int64     `json:"indexSize"`
	TotalSize      int64     `json:"totalSize"`
	CreateTime     time.Time `json:"createTime"`
	UpdateTime     time.Time `json:"updateTime"`
	Engine         string    `json:"engine"`
	TableCollation string    `json:"tableCollation"`
	Comment        string    `json:"comment"`
	Columns        []ColumnInfo `json:"columns"`
	PrimaryKeys    []string  `json:"primaryKeys"`
	Indexes        []IndexInfo `json:"indexes"`
	PartitionInfo  *PartitionInfo `json:"partitionInfo,omitempty"`
	Stats          *TableStats `json:"stats,omitempty"`
}

type ColumnInfo struct {
	ColumnName    string `json:"columnName"`
	DataType      string `json:"dataType"`
	ColumnType    string `json:"columnType"`
	IsNullable    bool   `json:"isNullable"`
	ColumnKey     string `json:"columnKey"`
	ColumnDefault string `json:"columnDefault"`
	Extra         string `json:"extra"`
	Comment       string `json:"comment"`
}

type IndexInfo struct {
	IndexName     string   `json:"indexName"`
	NonUnique     bool     `json:"nonUnique"`
	SeqInIndex    int      `json:"seqInIndex"`
	ColumnName    string   `json:"columnName"`
	IndexType     string   `json:"indexType"`
	Comment       string   `json:"comment"`
}

type PartitionInfo struct {
	PartitionMethod string          `json:"partitionMethod"`
	PartitionExpr   string          `json:"partitionExpr"`
	Partitions      []PartitionDef  `json:"partitions"`
}

type PartitionDef struct {
	PartitionName       string    `json:"partitionName"`
	PartitionOrdinal    int       `json:"partitionOrdinal"`
	PartitionMethod     string    `json:"partitionMethod"`
	PartitionExpression string    `json:"partitionExpression"`
	PartitionDescription string   `json:"partitionDescription"`
	TableRows           int64     `json:"tableRows"`
	DataLength          int64     `json:"dataLength"`
	IndexLength         int64     `json:"indexLength"`
	CreateTime          time.Time `json:"createTime"`
	UpdateTime          time.Time `json:"updateTime"`
	Comment             string    `json:"comment"`
}

type TableStats struct {
	TotalRows       int64     `json:"totalRows"`
	TotalSizeMB     float64   `json:"totalSizeMB"`
	AvgRowSizeKB    float64   `json:"avgRowSizeKB"`
	MinValue        interface{} `json:"minValue"`
	MaxValue        interface{} `json:"maxValue"`
	ValueRange      interface{} `json:"valueRange"`
	ValueDistinct   int64     `json:"valueDistinct"`
	GrowthPerDay    int64     `json:"growthPerDay"`
	GrowthPerWeek   int64     `json:"growthPerWeek"`
	GrowthPerMonth  int64     `json:"growthPerMonth"`
	EstimatedDaysToThreshold int `json:"estimatedDaysToThreshold"`
	DataPoints      []DataPoint `json:"dataPoints,omitempty"`
}

type DataPoint struct {
	Date  time.Time `json:"date"`
	Value int64     `json:"value"`
}

type PartitionRecommendation struct {
	TableName         string   `json:"tableName"`
	RecommendedMethod string   `json:"recommendedMethod"`
	PartitionExpr     string   `json:"partitionExpr"`
	PartitionColumn   string   `json:"partitionColumn"`
	Reason            string   `json:"reason"`
	Confidence        int      `json:"confidence"`
	EstimatedPartitions int    `json:"estimatedPartitions"`
	EstimatedPerfGain string   `json:"estimatedPerfGain"`
	SamplePartitions  []PartitionDef `json:"samplePartitions"`
	AlternativeMethods []AlternativeMethod `json:"alternativeMethods"`
}

type AlternativeMethod struct {
	Method       string `json:"method"`
	Reason       string `json:"reason"`
	Confidence   int    `json:"confidence"`
}

type PartitionPlan struct {
	TableName         string         `json:"tableName"`
	PartitionMethod   string         `json:"partitionMethod"`
	PartitionExpr     string         `json:"partitionExpr"`
	PartitionColumn   string         `json:"partitionColumn"`
	Partitions        []PartitionDef `json:"partitions"`
	SqlStatements     []string       `json:"sqlStatements"`
	EstimatedTimeSec  int            `json:"estimatedTimeSec"`
}

type QueryRewriteRequest struct {
	OriginalSQL string `json:"originalSql"`
	TableName   string `json:"tableName"`
}

type QueryRewriteResponse struct {
	OriginalSQL   string   `json:"originalSql"`
	RewrittenSQL  string   `json:"rewrittenSql"`
	AppliedRules  []string `json:"appliedRules"`
	Explanation   string   `json:"explanation"`
	PerformanceHint string `json:"performanceHint"`
}

type PartitionOperationRequest struct {
	TableName     string   `json:"tableName"`
	Operation     string   `json:"operation"`
	PartitionNames []string `json:"partitionNames"`
	NewPartitions []PartitionDef `json:"newPartitions"`
}

type PartitionOperationResponse struct {
	Success    bool     `json:"success"`
	Message    string   `json:"message"`
	SqlExecuted []string `json:"sqlExecuted"`
	Warnings   []string `json:"warnings"`
}

type GrowthPrediction struct {
	TableName        string    `json:"tableName"`
	CurrentRows      int64     `json:"currentRows"`
	Predicted30Days  int64     `json:"predicted30Days"`
	Predicted90Days  int64     `json:"predicted90Days"`
	Predicted365Days int64     `json:"predicted365Days"`
	GrowthRate       float64   `json:"growthRate"`
	ShouldPartition  bool      `json:"shouldPartition"`
	RecommendedAction string  `json:"recommendedAction"`
}
