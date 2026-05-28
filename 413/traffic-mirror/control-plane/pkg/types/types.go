package types

import "time"

type MirrorConfig struct {
	SamplingRate     float64      `json:"sampling_rate"`
	SamplingHashKey  string       `json:"sampling_hash_key"`
	HeaderRules      []HeaderRule `json:"header_rules"`
	TestCluster      string       `json:"test_cluster"`
	ControlPlane     string       `json:"control_plane"`
	Enabled          bool         `json:"enabled"`
	ProtoContentTypes []string    `json:"proto_content_types,omitempty"`
	ColorEnabled     bool         `json:"color_enabled"`
	ColorHeader      string       `json:"color_header"`
	ColorValue       string       `json:"color_value"`
	AnomalyEnabled   bool         `json:"anomaly_enabled"`
	AnomalyThreshold float64      `json:"anomaly_threshold"`
}

type HeaderRule struct {
	ID        int64  `json:"id" gorm:"primaryKey"`
	Name      string `json:"name"`
	Value     string `json:"value"`
	Operation string `json:"operation"`
	Match     string `json:"match"`
	Override  bool   `json:"override"`
	Priority  int    `json:"priority"`
	Enabled   bool   `json:"enabled"`
}

type ProtoSchema struct {
	ID              int64  `json:"id" gorm:"primaryKey"`
	MessageType     string `json:"message_type" gorm:"uniqueIndex;not null"`
	ProtoFileName   string `json:"proto_file_name"`
	FileDescriptor  []byte `json:"file_descriptor" gorm:"type:blob"`
	PackageName     string `json:"package_name"`
	ServiceName     string `json:"service_name"`
	MethodName      string `json:"method_name"`
	Description     string `json:"description"`
	Enabled         bool   `json:"enabled" gorm:"default:true"`
}

type ComparisonResult struct {
	ID               int64            `json:"id" gorm:"primaryKey"`
	RequestID        string           `json:"request_id"`
	Timestamp        int64            `json:"timestamp"`
	Path             string           `json:"path"`
	Method           string           `json:"method"`
	ProdStatus       uint32           `json:"prod_status"`
	TestStatus       uint32           `json:"test_status"`
	StatusMatch      bool             `json:"status_match"`
	BodyMatch        bool             `json:"body_match"`
	HeaderMatch      bool             `json:"header_match"`
	HasDiff          bool             `json:"has_diff"`
	Severity         string           `json:"severity"`
	ProdBodyHash     string           `json:"prod_body_hash"`
	TestBodyHash     string           `json:"test_body_hash"`
	ProdBodyLen      int              `json:"prod_body_len"`
	TestBodyLen      int              `json:"test_body_len"`
	Differences      []Difference     `json:"differences" gorm:"serializer:json"`
	ProdHeaders      string           `json:"prod_headers,omitempty" gorm:"type:text"`
	TestHeaders      string           `json:"test_headers,omitempty" gorm:"type:text"`
	ProdBody         string           `json:"prod_body,omitempty" gorm:"type:text"`
	TestBody         string           `json:"test_body,omitempty" gorm:"type:text"`
	IsProto          bool             `json:"is_proto"`
	ProtoMessageType string           `json:"proto_message_type,omitempty"`
	ProtoDifferences []ProtoFieldDiff `json:"proto_differences,omitempty" gorm:"serializer:json"`
	Anomaly          string           `json:"anomaly,omitempty"`
}

type Difference struct {
	Field    string `json:"field"`
	Type     string `json:"type"`
	ProdVal  string `json:"prod_value"`
	TestVal  string `json:"test_value"`
	Severity string `json:"severity"`
}

type ProtoFieldDiff struct {
	FieldNumber int32  `json:"field_number"`
	FieldName   string `json:"field_name,omitempty"`
	WireType    int    `json:"wire_type"`
	ProdVal     string `json:"prod_value"`
	TestVal     string `json:"test_value"`
	Severity    string `json:"severity"`
}

type ComparisonQuery struct {
	Path       string `json:"path,omitempty" form:"path"`
	Method     string `json:"method,omitempty" form:"method"`
	Severity   string `json:"severity,omitempty" form:"severity"`
	HasDiff    *bool  `json:"has_diff,omitempty" form:"has_diff"`
	IsProto    *bool  `json:"is_proto,omitempty" form:"is_proto"`
	StartTime  int64  `json:"start_time,omitempty" form:"start_time"`
	EndTime    int64  `json:"end_time,omitempty" form:"end_time"`
	Page       int    `json:"page,omitempty" form:"page"`
	PageSize   int    `json:"page_size,omitempty" form:"page_size"`
}

type ComparisonStats struct {
	TotalCount      int64            `json:"total_count"`
	MatchCount      int64            `json:"match_count"`
	MismatchCount   int64            `json:"mismatch_count"`
	ProtoCount      int64            `json:"proto_count"`
	SeverityCount   map[string]int64 `json:"severity_count"`
	TopDiffs        []TopDiff        `json:"top_diffs"`
	TopProtoDiffs   []TopDiff        `json:"top_proto_diffs"`
	AnomalyCount    int64            `json:"anomaly_count"`
}

type TopDiff struct {
	Path      string `json:"path"`
	Count     int64  `json:"count"`
	Severity  string `json:"severity"`
}

type MirrorStatus struct {
	Enabled           bool    `json:"enabled"`
	SamplingRate      float64 `json:"sampling_rate"`
	SamplingHashKey   string  `json:"sampling_hash_key"`
	TotalRequests     int64   `json:"total_requests"`
	MirroredCount     int64   `json:"mirrored_count"`
	TestCluster       string  `json:"test_cluster"`
	ProtoSchemaCount  int64   `json:"proto_schema_count"`
	ColorEnabled      bool    `json:"color_enabled"`
	ColorHeader       string  `json:"color_header,omitempty"`
	ColorValue        string  `json:"color_value,omitempty"`
	AnomalyCount      int64   `json:"anomaly_count"`
}

type SamplingHashKeyRequest struct {
	HashKey string `json:"hash_key" binding:"required"`
}

type AnomalyAlert struct {
	ID          int64             `json:"id" gorm:"primaryKey"`
	Timestamp   int64             `json:"timestamp"`
	RequestID   string            `json:"request_id"`
	Path        string            `json:"path"`
	Method      string            `json:"method"`
	AnomalyType string            `json:"anomaly_type"`
	Severity    string            `json:"severity"`
	Message     string            `json:"message"`
	Details     map[string]string `json:"details,omitempty" gorm:"serializer:json"`
	Acknowledged bool             `json:"acknowledged" gorm:"default:false"`
	CreatedAt   time.Time         `json:"created_at"`
}

type AnomalyQuery struct {
	AnomalyType string `json:"anomaly_type,omitempty" form:"anomaly_type"`
	Severity    string `json:"severity,omitempty" form:"severity"`
	Acknowledged *bool `json:"acknowledged,omitempty" form:"acknowledged"`
	StartTime   int64  `json:"start_time,omitempty" form:"start_time"`
	EndTime     int64  `json:"end_time,omitempty" form:"end_time"`
	Page        int    `json:"page,omitempty" form:"page"`
	PageSize    int    `json:"page_size,omitempty" form:"page_size"`
}

type AnomalyStats struct {
	TotalCount    int64            `json:"total_count"`
	AckCount      int64            `json:"ack_count"`
	UnackCount    int64            `json:"unack_count"`
	TypeCount     map[string]int64 `json:"type_count"`
	SeverityCount map[string]int64 `json:"severity_count"`
}

type ReplayRequest struct {
	Name           string `json:"name" binding:"required"`
	StartTime      int64  `json:"start_time" binding:"required"`
	EndTime        int64  `json:"end_time" binding:"required"`
	Speed          float64 `json:"speed"`
	MaxConcurrency int    `json:"max_concurrency"`
	TargetHost     string `json:"target_host"`
	TargetPort     int    `json:"target_port"`
	PathFilter     string `json:"path_filter,omitempty"`
	MethodFilter   string `json:"method_filter,omitempty"`
}

type ReplayTask struct {
	ID             int64   `json:"id" gorm:"primaryKey"`
	Name           string  `json:"name"`
	StartTime      int64   `json:"start_time"`
	EndTime        int64   `json:"end_time"`
	Speed          float64 `json:"speed"`
	MaxConcurrency int     `json:"max_concurrency"`
	TargetHost     string  `json:"target_host"`
	TargetPort     int     `json:"target_port"`
	Status         string  `json:"status"`
	Progress       float64 `json:"progress"`
	TotalCount     int64   `json:"total_count"`
	SentCount      int64   `json:"sent_count"`
	SuccessCount   int64   `json:"success_count"`
	FailedCount    int64   `json:"failed_count"`
	Error          string  `json:"error,omitempty"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

type ColorConfigRequest struct {
	Enabled bool   `json:"enabled"`
	Header  string `json:"header"`
	Value   string `json:"value"`
}

type AnomalyConfigRequest struct {
	Enabled   bool    `json:"enabled"`
	Threshold float64 `json:"threshold"`
}
