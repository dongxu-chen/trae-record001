package dag

import (
	"time"
)

type TaskStatus string

const (
	TaskStatusPending   TaskStatus = "pending"
	TaskStatusRunning   TaskStatus = "running"
	TaskStatusSuccess   TaskStatus = "success"
	TaskStatusFailed    TaskStatus = "failed"
	TaskStatusSkipped   TaskStatus = "skipped"
	TaskStatusRetry     TaskStatus = "retrying"
	TaskStatusPreheating TaskStatus = "preheating"
	TaskStatusPreheated TaskStatus = "preheated"
)

type WarmupType string

const (
	WarmupTypeImagePull WarmupType = "image_pull"
	WarmupTypeCache     WarmupType = "cache"
	WarmupTypeDependency WarmupType = "dependency"
	WarmupTypeCustom    WarmupType = "custom"
)

type WarmupTask struct {
	ID           string
	TargetTaskID string
	Type         WarmupType
	Image        string
	Command      []string
	Status       TaskStatus
	StartTime    *time.Time
	EndTime      *time.Time
	ExecutorName string
	Error        string
}

type Resources struct {
	CPU    float64 `yaml:"cpu"`
	Memory int64   `yaml:"memory"`
}

type Task struct {
	ID           string         `yaml:"id"`
	Name         string         `yaml:"name"`
	Image        string         `yaml:"image"`
	Command      []string       `yaml:"command"`
	DependsOn    []string       `yaml:"depends_on"`
	Priority     int            `yaml:"priority"`
	MaxRetries   int            `yaml:"max_retries"`
	RetryDelay     time.Duration  `yaml:"retry_delay"`
	EstimatedTime time.Duration `yaml:"estimated_time"`
	Resources    Resources      `yaml:"resources"`
	Labels       map[string]string `yaml:"labels"`
	Status       TaskStatus     `yaml:"-"`
	RetryCount    int            `yaml:"-"`
	StartTime     *time.Time     `yaml:"-"`
	EndTime       *time.Time     `yaml:"-"`
	ExecutorName     string         `yaml:"-"`
}

type Pipeline struct {
	ID        string            `yaml:"id"`
	Name      string            `yaml:"name"`
	Tasks     []Task            `yaml:"tasks"`
	Resources Resources          `yaml:"default_resources"`
	Labels    map[string]string  `yaml:"labels"`
}

type Node struct {
	Task     *Task
	InDegree  int
	OutEdges  []*Node
	InEdges   []*Node
}

type DAG struct {
	Nodes            map[string]*Node
	Tasks            map[string]*Task
	topoOrder        []string
	topoPosition     map[string]int
	descendantCache  map[string]map[string]bool
	ancestorCache    map[string]map[string]bool
	cacheValid       bool
}
