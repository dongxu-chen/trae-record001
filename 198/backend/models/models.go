package models

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type AlertGroup struct {
	ID          string    `gorm:"primaryKey" json:"id"`
	Name        string    `gorm:"not null;unique" json:"name"`
	Description string    `json:"description"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
	Rules       []AlertRule `gorm:"foreignKey:GroupID" json:"rules,omitempty"`
}

type AlertRule struct {
	ID          string    `gorm:"primaryKey" json:"id"`
	GroupID     string    `json:"group_id"`
	Group       AlertGroup `gorm:"foreignKey:GroupID" json:"group,omitempty"`
	Name        string    `gorm:"not null" json:"name"`
	Expr        string    `gorm:"not null" json:"expr"`
	For         string    `json:"for"`
	Severity    string    `json:"severity"`
	Description string    `json:"description"`
	Summary     string    `json:"summary"`
	Labels      string    `json:"labels"`
	Annotations string    `json:"annotations"`
	Enabled     bool      `gorm:"default:true" json:"enabled"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
	Versions    []AlertRuleVersion `gorm:"foreignKey:RuleID" json:"versions,omitempty"`
}

type AlertRuleVersion struct {
	ID          string    `gorm:"primaryKey" json:"id"`
	RuleID      string    `json:"rule_id"`
	Version     int       `json:"version"`
	Name        string    `json:"name"`
	Expr        string    `json:"expr"`
	For         string    `json:"for"`
	Severity    string    `json:"severity"`
	Description string    `json:"description"`
	Summary     string    `json:"summary"`
	Labels      string    `json:"labels"`
	Annotations string    `json:"annotations"`
	ChangeLog   string    `json:"change_log"`
	CreatedAt   time.Time `json:"created_at"`
}

func (g *AlertGroup) BeforeCreate(tx *gorm.DB) error {
	if g.ID == "" {
		g.ID = uuid.New().String()
	}
	return nil
}

func (r *AlertRule) BeforeCreate(tx *gorm.DB) error {
	if r.ID == "" {
		r.ID = uuid.New().String()
	}
	return nil
}

func (v *AlertRuleVersion) BeforeCreate(tx *gorm.DB) error {
	if v.ID == "" {
		v.ID = uuid.New().String()
	}
	return nil
}
