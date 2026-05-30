package models

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type Secret struct {
	ID          uuid.UUID `gorm:"type:uuid;primaryKey"`
	Name        string    `gorm:"uniqueIndex;not null"`
	Description string
	Type        string    `gorm:"not null"`
	EncryptedValue []byte `gorm:"not null"`
	Version     int       `gorm:"default:1"`
	CreatedAt   time.Time
	UpdatedAt   time.Time
	ExpiresAt   *time.Time
	IsRotated   bool      `gorm:"default:false"`
	LastRotatedAt *time.Time
	Labels      []Label   `gorm:"many2many:secret_labels;"`
}

type Label struct {
	ID    uint   `gorm:"primaryKey"`
	Key   string `gorm:"index"`
	Value string
}

type AuditLog struct {
	ID        uuid.UUID `gorm:"type:uuid;primaryKey"`
	SecretID  uuid.UUID `gorm:"index"`
	Action    string    `gorm:"not null"`
	User      string    `gorm:"not null"`
	IPAddress string
	UserAgent string
	Success   bool
	Message   string
	CreatedAt time.Time `gorm:"index"`
}

type SecretVersion struct {
	ID             uuid.UUID `gorm:"type:uuid;primaryKey"`
	SecretID       uuid.UUID `gorm:"index"`
	Version        int       `gorm:"not null"`
	EncryptedValue []byte    `gorm:"not null"`
	CreatedAt      time.Time
	CreatedBy      string
}

type EncryptedDataRecord struct {
	ID              uuid.UUID `gorm:"type:uuid;primaryKey"`
	SecretID        uuid.UUID `gorm:"index"`
	SecretVersion   int       `gorm:"not null"`
	DataReference   string    `gorm:"type:text;not null"`
	EncryptionKeyID string    `gorm:"index"`
	CreatedAt       time.Time
	Description     string
}

type ComplianceCheck struct {
	ID              uuid.UUID `gorm:"type:uuid;primaryKey"`
	SecretID        uuid.UUID `gorm:"index"`
	CheckType       string    `gorm:"not null"`
	Status          string    `gorm:"not null"`
	Score           int       `gorm:"default:0"`
	Findings        string    `gorm:"type:text"`
	Recommendations string    `gorm:"type:text"`
	CheckedAt       time.Time `gorm:"index"`
	CheckedBy       string
}

type RecoveryExercise struct {
	ID              uuid.UUID `gorm:"type:uuid;primaryKey"`
	ExerciseType    string    `gorm:"not null"`
	Status          string    `gorm:"not null"`
	StartTime       time.Time
	EndTime         *time.Time
	DurationSeconds int
	Steps           string    `gorm:"type:text"`
	Findings        string    `gorm:"type:text"`
	Passed          bool      `gorm:"default:false"`
	Executor        string
	CreatedAt       time.Time
}

func (s *Secret) BeforeCreate(tx *gorm.DB) error {
	s.ID = uuid.New()
	return nil
}

func (a *AuditLog) BeforeCreate(tx *gorm.DB) error {
	a.ID = uuid.New()
	return nil
}

func (v *SecretVersion) BeforeCreate(tx *gorm.DB) error {
	v.ID = uuid.New()
	return nil
}

func (e *EncryptedDataRecord) BeforeCreate(tx *gorm.DB) error {
	e.ID = uuid.New()
	return nil
}

func (c *ComplianceCheck) BeforeCreate(tx *gorm.DB) error {
	c.ID = uuid.New()
	return nil
}

func (r *RecoveryExercise) BeforeCreate(tx *gorm.DB) error {
	r.ID = uuid.New()
	return nil
}
