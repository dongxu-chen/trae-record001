package models

import (
	"time"

	"gorm.io/gorm"
)

type AuditLog struct {
	ID             string `gorm:"primaryKey"`
	NamespaceID    string `gorm:"index;size:100"`
	Group          string `gorm:"index;size:255"`
	DataID         string `gorm:"index;size:255"`
	Operator       string `gorm:"size:100"`
	OperatorIP     string `gorm:"size:50"`
	Action         string `gorm:"size:50"`
	OldContent     string `gorm:"type:text"`
	NewContent     string `gorm:"type:text"`
	ContentType    string `gorm:"size:50"`
	Desc           string `gorm:"size:500"`
	CompliancePass *bool
	ComplianceMsg  string `gorm:"size:500"`
	IsAutoRollback bool     `gorm:"default:false"`
	RollbackReason string   `gorm:"size:500"`
	CreatedAt      time.Time `gorm:"index"`
}

type NamespaceConfig struct {
	ID            string `gorm:"primaryKey"`
	NamespaceID   string `gorm:"uniqueIndex;size:100"`
	NamespaceName string `gorm:"size:255"`
	IsEnabled     bool
	NotifyEmails  string `gorm:"size:500"`
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

type ComplianceRule struct {
	ID          string `gorm:"primaryKey"`
	Name        string `gorm:"size:255"`
	Description string `gorm:"size:500"`
	Pattern     string `gorm:"type:text"`
	RuleType    string `gorm:"size:50"`
	IsEnabled   bool
	Severity    string `gorm:"size:50"`
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

type ServiceRegistry struct {
	ID          string `gorm:"primaryKey"`
	ServiceName string `gorm:"index;size:255"`
	NamespaceID string `gorm:"index;size:100"`
	Group       string `gorm:"index;size:255"`
	DataID      string `gorm:"index;size:255"`
	Environment string `gorm:"size:50"`
	Owner       string `gorm:"size:100"`
	OwnerEmail  string `gorm:"size:255"`
	Desc        string `gorm:"size:500"`
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

type RollbackPolicy struct {
	ID                  string `gorm:"primaryKey"`
	Name                string `gorm:"size:255"`
	NamespaceID         string `gorm:"size:100"`
	Group               string `gorm:"size:255"`
	DataID              string `gorm:"size:255"`
	AutoRollbackOnComplianceFail bool
	AutoRollbackOnSensitiveData  bool
	AutoRollbackOnCriticalChange bool
	MaxChangeLines      int
	IsEnabled           bool
	CreatedAt           time.Time
	UpdatedAt           time.Time
}

func (AuditLog) TableName() string {
	return "audit_logs"
}

func (NamespaceConfig) TableName() string {
	return "namespace_configs"
}

func (ComplianceRule) TableName() string {
	return "compliance_rules"
}

func (ServiceRegistry) TableName() string {
	return "service_registries"
}

func (RollbackPolicy) TableName() string {
	return "rollback_policies"
}

func Migrate(db *gorm.DB) error {
	return db.AutoMigrate(
		&AuditLog{},
		&NamespaceConfig{},
		&ComplianceRule{},
		&ServiceRegistry{},
		&RollbackPolicy{},
	)
}
