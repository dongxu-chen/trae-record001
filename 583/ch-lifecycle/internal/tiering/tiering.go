package tiering

import (
	"context"
	"fmt"
	"time"

	ch "ch-lifecycle/internal/clickhouse"
	"ch-lifecycle/config"
	"ch-lifecycle/internal/policy"
	"go.uber.org/zap"
)

type Tier struct {
	Name     string
	Type     string
	Path     string
	Priority int
}

type Engine struct {
	client  *ch.Client
	store   *policy.Store
	tiers   []Tier
	logger  *zap.Logger
	metrics MetricsCollector
}

type MetricsCollector interface {
	IncTierMigrations(from, to string)
	ObserveDiskUsage(disk string, used, total uint64)
}

func NewEngine(client *ch.Client, store *policy.Store, cfgTiers []config.StorageTier, logger *zap.Logger, metrics MetricsCollector) *Engine {
	tiers := make([]Tier, len(cfgTiers))
	for i, t := range cfgTiers {
		tiers[i] = Tier{
			Name:     t.Name,
			Type:     t.Type,
			Path:     t.Path,
			Priority: t.Priority,
		}
	}
	return &Engine{
		client:  client,
		store:   store,
		tiers:   tiers,
		logger:  logger,
		metrics: metrics,
	}
}

type MigrationPlan struct {
	Database   string `json:"database"`
	Table      string `json:"table"`
	Partition  string `json:"partition"`
	FromDisk   string `json:"from_disk"`
	ToDisk     string `json:"to_disk"`
	AgeDays    int    `json:"age_days"`
	SizeBytes  uint64 `json:"size_bytes"`
	Reason     string `json:"reason"`
}

type MigrationResult struct {
	Planned    int              `json:"planned"`
	Executed   int              `json:"executed"`
	Errors     []MigrationError `json:"errors,omitempty"`
	Duration   time.Duration    `json:"duration"`
}

type MigrationError struct {
	Partition string `json:"partition"`
	FromDisk  string `json:"from_disk"`
	ToDisk    string `json:"to_disk"`
	Error     string `json:"error"`
}

func (e *Engine) Plan(ctx context.Context) ([]MigrationPlan, error) {
	policies, err := e.store.GetActivePolicies()
	if err != nil {
		return nil, fmt.Errorf("get active policies: %w", err)
	}
	diskInfo, err := e.client.GetDisks(ctx)
	if err != nil {
		e.logger.Warn("failed to get disk info", zap.Error(err))
	}
	for _, d := range diskInfo {
		e.metrics.ObserveDiskUsage(d.Name, d.TotalSpace-d.FreeSpace, d.TotalSpace)
	}
	var plans []MigrationPlan
	for _, p := range policies {
		moveRules := filterMoveRules(p.Rules)
		if len(moveRules) == 0 {
			continue
		}
		partitions, err := e.client.GetPartitions(ctx, p.Database, p.Table)
		if err != nil {
			e.logger.Error("failed to get partitions",
				zap.String("database", p.Database),
				zap.String("table", p.Table),
				zap.Error(err),
			)
			continue
		}
		for _, part := range partitions {
			ageDays := calculateAge(part.MaxDate)
			for _, rule := range moveRules {
				if ageDays >= rule.AgeDays && rule.TargetDisk != "" {
					currentDisk := detectDiskFromPath(part.Path)
					if currentDisk != rule.TargetDisk {
						plans = append(plans, MigrationPlan{
							Database:  p.Database,
							Table:     p.Table,
							Partition: part.Partition,
							FromDisk:  currentDisk,
							ToDisk:    rule.TargetDisk,
							AgeDays:   ageDays,
							SizeBytes: part.BytesOnDisk,
							Reason:    fmt.Sprintf("age %d days (UTC) >= threshold %d days, migrate %s -> %s", ageDays, rule.AgeDays, currentDisk, rule.TargetDisk),
						})
					}
					break
				}
			}
		}
	}
	return plans, nil
}

func (e *Engine) Execute(ctx context.Context, dryRun bool) (*MigrationResult, error) {
	start := time.Now()
	plans, err := e.Plan(ctx)
	if err != nil {
		return nil, err
	}
	result := &MigrationResult{Planned: len(plans)}
	if dryRun {
		e.logger.Info("dry run tiering, skipping execution", zap.Int("plans", len(plans)))
		result.Duration = time.Since(start)
		return result, nil
	}
	for _, plan := range plans {
		if err := e.client.MovePartitionToDisk(ctx, plan.Database, plan.Table, plan.Partition, plan.ToDisk); err != nil {
			result.Errors = append(result.Errors, MigrationError{
				Partition: plan.Partition,
				FromDisk:  plan.FromDisk,
				ToDisk:    plan.ToDisk,
				Error:     err.Error(),
			})
			e.logger.Error("tiering migration failed",
				zap.String("partition", plan.Partition),
				zap.String("from", plan.FromDisk),
				zap.String("to", plan.ToDisk),
				zap.Error(err),
			)
		} else {
			result.Executed++
			e.metrics.IncTierMigrations(plan.FromDisk, plan.ToDisk)
			e.logger.Info("tiering migration completed",
				zap.String("partition", plan.Partition),
				zap.String("from", plan.FromDisk),
				zap.String("to", plan.ToDisk),
			)
		}
	}
	result.Duration = time.Since(start)
	return result, nil
}

func (e *Engine) GetTierStatus(ctx context.Context) ([]TierStatus, error) {
	disks, err := e.client.GetDisks(ctx)
	if err != nil {
		return nil, err
	}
	diskMap := make(map[string]ch.DiskInfo)
	for _, d := range disks {
		diskMap[d.Name] = d
	}
	var statuses []TierStatus
	for _, tier := range e.tiers {
		status := TierStatus{
			Name:     tier.Name,
			Type:     tier.Type,
			Path:     tier.Path,
			Priority: tier.Priority,
		}
		if d, ok := diskMap[tier.Name]; ok {
			status.FreeSpace = d.FreeSpace
			status.TotalSpace = d.TotalSpace
			status.UsedPercent = float64(d.TotalSpace-d.FreeSpace) / float64(d.TotalSpace) * 100
		}
		statuses = append(statuses, status)
	}
	return statuses, nil
}

type TierStatus struct {
	Name        string  `json:"name"`
	Type        string  `json:"type"`
	Path        string  `json:"path"`
	Priority    int     `json:"priority"`
	FreeSpace   uint64  `json:"free_space"`
	TotalSpace  uint64  `json:"total_space"`
	UsedPercent float64 `json:"used_percent"`
}

func filterMoveRules(rules []policy.TTLRule) []policy.TTLRule {
	var moveRules []policy.TTLRule
	for _, r := range rules {
		if r.Action == policy.ActionMoveToDisk && r.TargetDisk != "" {
			moveRules = append(moveRules, r)
		}
	}
	return moveRules
}

func detectDiskFromPath(path string) string {
	if path == "" {
		return "default"
	}
	return "default"
}

func calculateAge(dateStr string) int {
	if dateStr == "" || dateStr == "0000-00-00" {
		return 0
	}
	t, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		return 0
	}
	tUTC := time.Date(t.Year(), t.Month(), t.Day(), 0, 0, 0, 0, time.UTC)
	nowUTC := time.Now().UTC()
	days := int(nowUTC.Sub(tUTC).Hours() / 24)
	if days < 0 {
		return 0
	}
	return days
}
