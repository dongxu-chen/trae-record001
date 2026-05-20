package audit

import "time"

type Severity string

const (
	SeverityCritical Severity = "critical"
	SeverityHigh     Severity = "high"
	SeverityMedium   Severity = "medium"
	SeverityLow      Severity = "low"
)

type Violation struct {
	ResourceType string
	Namespace  string
	ResourceName string
	RuleType   string
	Severity   Severity
	Message    string
	Suggestion string
}

type ResourceInfo struct {
	Type      string
	Namespace string
	Name      string
	Labels    map[string]string
	Spec      interface{}
}

type NamespaceQuotaUsage struct {
	Namespace    string
	CPURequests  string
	CPULimits    string
	MemRequests  string
	MemLimits    string
	CPUQuota     string
	MemQuota     string
	CPUPercent   float64
	MemoryPercent float64
	OverQuota    bool
}

type AuditReport struct {
	Timestamp          time.Time
	Cluster            string
	TotalResources     int
	Violations         []Violation
	Summary            map[string]int
	NamespaceQuotaUsages []NamespaceQuotaUsage
}
