package model

import (
	"time"

	"gorm.io/gorm"
)

type HeaderRule struct {
	ID        int64     `gorm:"primaryKey" json:"id"`
	Name      string    `gorm:"index;not null" json:"name"`
	Value     string    `json:"value"`
	Operation string    `gorm:"not null;default:'add'" json:"operation"`
	Match     string    `json:"match"`
	Override  bool      `gorm:"default:false" json:"override"`
	Priority  int       `gorm:"default:0" json:"priority"`
	Enabled   bool      `gorm:"default:true" json:"enabled"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type ProtoSchema struct {
	ID             int64     `gorm:"primaryKey" json:"id"`
	MessageType    string    `gorm:"uniqueIndex;not null" json:"message_type"`
	ProtoFileName  string    `json:"proto_file_name"`
	FileDescriptor []byte    `gorm:"type:blob" json:"file_descriptor"`
	PackageName    string    `json:"package_name"`
	ServiceName    string    `json:"service_name"`
	MethodName     string    `json:"method_name"`
	Description    string    `json:"description"`
	Enabled        bool      `gorm:"default:true" json:"enabled"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

type ComparisonResult struct {
	ID               int64          `gorm:"primaryKey" json:"id"`
	RequestID        string         `gorm:"index" json:"request_id"`
	Timestamp        int64          `gorm:"index" json:"timestamp"`
	Path             string         `gorm:"index" json:"path"`
	Method           string         `json:"method"`
	ProdStatus       uint32         `json:"prod_status"`
	TestStatus       uint32         `json:"test_status"`
	StatusMatch      bool           `gorm:"default:true" json:"status_match"`
	BodyMatch        bool           `gorm:"default:true" json:"body_match"`
	HeaderMatch      bool           `gorm:"default:true" json:"header_match"`
	HasDiff          bool           `gorm:"index;default:false" json:"has_diff"`
	Severity         string         `gorm:"index;default:'none'" json:"severity"`
	ProdBodyHash     string         `json:"prod_body_hash"`
	TestBodyHash     string         `json:"test_body_hash"`
	ProdBodyLen      int            `json:"prod_body_len"`
	TestBodyLen      int            `json:"test_body_len"`
	Differences      string         `gorm:"type:text" json:"differences"`
	ProdHeaders      string         `gorm:"type:text" json:"prod_headers,omitempty"`
	TestHeaders      string         `gorm:"type:text" json:"test_headers,omitempty"`
	ProdBody         string         `gorm:"type:text" json:"prod_body,omitempty"`
	TestBody         string         `gorm:"type:text" json:"test_body,omitempty"`
	IsProto          bool           `gorm:"default:false" json:"is_proto"`
	ProtoMessageType string         `gorm:"index" json:"proto_message_type,omitempty"`
	ProtoDifferences string         `gorm:"type:text" json:"proto_differences,omitempty"`
	CreatedAt        time.Time      `json:"created_at"`
	DeletedAt        gorm.DeletedAt `gorm:"index" json:"-"`
}

type Config struct {
	ID        int64     `gorm:"primaryKey" json:"id"`
	Key       string    `gorm:"uniqueIndex;not null" json:"key"`
	Value     string    `gorm:"type:text" json:"value"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

type AnomalyAlert struct {
	ID           int64          `gorm:"primaryKey" json:"id"`
	Timestamp    int64          `gorm:"index" json:"timestamp"`
	RequestID    string         `gorm:"index" json:"request_id"`
	Path         string         `gorm:"index" json:"path"`
	Method       string         `json:"method"`
	AnomalyType  string         `gorm:"index" json:"anomaly_type"`
	Severity     string         `gorm:"index" json:"severity"`
	Message      string         `gorm:"type:text" json:"message"`
	Details      string         `gorm:"type:text" json:"details,omitempty"`
	Acknowledged bool           `gorm:"index;default:false" json:"acknowledged"`
	CreatedAt    time.Time      `json:"created_at"`
}

type ReplayTask struct {
	ID             int64     `gorm:"primaryKey" json:"id"`
	Name           string    `json:"name"`
	StartTime      int64     `json:"start_time"`
	EndTime        int64     `json:"end_time"`
	Speed          float64   `gorm:"default:1" json:"speed"`
	MaxConcurrency int       `gorm:"default:10" json:"max_concurrency"`
	TargetHost     string    `json:"target_host"`
	TargetPort     int       `json:"target_port"`
	Status         string    `gorm:"index;default:'pending'" json:"status"`
	Progress       float64   `gorm:"default:0" json:"progress"`
	TotalCount     int64     `json:"total_count"`
	SentCount      int64     `json:"sent_count"`
	SuccessCount   int64     `json:"success_count"`
	FailedCount    int64     `json:"failed_count"`
	Error          string    `gorm:"type:text" json:"error,omitempty"`
	CreatedAt      time.Time `json:"created_at"`
	UpdatedAt      time.Time `json:"updated_at"`
}

func AutoMigrate(db *gorm.DB) error {
	return db.AutoMigrate(
		&HeaderRule{},
		&ProtoSchema{},
		&ComparisonResult{},
		&AnomalyAlert{},
		&ReplayTask{},
		&Config{},
	)
}
