package router

import "time"

type QuerySource string

const (
	QuerySourceHot  QuerySource = "hot"
	QuerySourceCold QuerySource = "cold"
	QuerySourceAuto QuerySource = "auto"
)

type QueryInfo struct {
	SQL        string    `json:"sql"`
	Database   string    `json:"database"`
	Table      string    `json:"table"`
	StartTime  time.Time `json:"start_time"`
	EndTime    time.Time `json:"end_time"`
	TableNames []string  `json:"table_names"`
}

type RouteResult struct {
	Source        QuerySource `json:"source"`
	Reason        string      `json:"reason"`
	TargetHost    string      `json:"target_host"`
	EstimatedRows uint64      `json:"estimated_rows"`
}

type RoutingRule struct {
	ID           string      `json:"id"`
	Database     string      `json:"database"`
	Table        string      `json:"table"`
	Pattern      string      `json:"pattern"`
	MinAgeDays   int         `json:"min_age_days"`
	TargetSource QuerySource `json:"target_source"`
	Priority     int         `json:"priority"`
}

type RoutingConfig struct {
	EnableSmartRouting bool        `json:"enable_smart_routing"`
	DefaultSource      QuerySource `json:"default_source"`
	HotHost            string      `json:"hot_host"`
	ColdHost           string      `json:"cold_host"`
	Rules              []RoutingRule `json:"rules"`
}
