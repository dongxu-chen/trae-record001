package lifecycle

import (
	"context"
	"fmt"
	"sort"
	"time"

	ch "ch-lifecycle/internal/clickhouse"
	"ch-lifecycle/internal/policy"
	"ch-lifecycle/internal/archive"
	"go.uber.org/zap"
)

type Manager struct {
	client   *ch.Client
	store    *policy.Store
	logger   *zap.Logger
	metrics  *MetricsCollector
	archiver *archive.Archiver
}

type MetricsCollector interface {
	IncPartitionsProcessed(action string)
	ObservePartitionSize(database, table string, size uint64)
	IncLifecycleErrors(action string)
}

func NewManager(client *ch.Client, store *policy.Store, logger *zap.Logger, metrics MetricsCollector) *Manager {
	return &Manager{
		client:  client,
		store:   store,
		logger:  logger,
		metrics: metrics,
	}
}

func (m *Manager) SetArchiver(archiver *archive.Archiver) {
	m.archiver = archiver
}

type ShadowMoveStep struct {
	Step        string `json:"step"`
	Database    string `json:"database"`
	Table       string `json:"table"`
	Partition   string `json:"partition"`
	TargetDisk  string `json:"target_disk,omitempty"`
	Status      string `json:"status"`
	Error       string `json:"error,omitempty"`
}

type PartitionAction struct {
	Database   string            `json:"database"`
	Table      string            `json:"table"`
	Partition  string            `json:"partition"`
	Action     policy.ActionType `json:"action"`
	TargetDisk string            `json:"target_disk,omitempty"`
	Reason     string            `json:"reason"`
	AgeDays    int               `json:"age_days"`
	SizeBytes  uint64            `json:"size_bytes"`
	Rows       uint64            `json:"rows"`
	ShadowMove bool              `json:"shadow_move"`
	Steps      []ShadowMoveStep  `json:"steps,omitempty"`
}

type ExecutionResult struct {
	TotalEvaluated int               `json:"total_evaluated"`
	Actions        []PartitionAction `json:"actions"`
	Errors         []ActionError     `json:"errors,omitempty"`
	Duration       time.Duration     `json:"duration"`
}

type ActionError struct {
	Partition string `json:"partition"`
	Action    string `json:"action"`
	Error     string `json:"error"`
}

func (m *Manager) Evaluate(ctx context.Context) (*ExecutionResult, error) {
	start := time.Now()
	policies, err := m.store.GetActivePolicies()
	if err != nil {
		return nil, fmt.Errorf("get active policies: %w", err)
	}
	var actions []PartitionAction
	var errors []ActionError
	totalEvaluated := 0
	for _, p := range policies {
		partitions, err := m.client.GetPartitions(ctx, p.Database, p.Table)
		if err != nil {
			m.logger.Error("failed to get partitions",
				zap.String("database", p.Database),
				zap.String("table", p.Table),
				zap.Error(err),
			)
			continue
		}
		sortedRules := make([]policy.TTLRule, len(p.Rules))
		copy(sortedRules, p.Rules)
		sort.Slice(sortedRules, func(i, j int) bool {
			return sortedRules[i].AgeDays > sortedRules[j].AgeDays
		})
		for _, part := range partitions {
			totalEvaluated++
			ageDays := m.calculateAge(part.MaxDate)
			m.metrics.ObservePartitionSize(p.Database, p.Table, part.BytesOnDisk)
			for _, rule := range sortedRules {
				if ageDays >= rule.AgeDays {
					action := PartitionAction{
						Database:   p.Database,
						Table:      p.Table,
						Partition:  part.Partition,
						Action:     rule.Action,
						TargetDisk: rule.TargetDisk,
						Reason:     fmt.Sprintf("age %d days (UTC) >= rule threshold %d days", ageDays, rule.AgeDays),
						AgeDays:    ageDays,
						SizeBytes:  part.BytesOnDisk,
						Rows:       part.Rows,
					}
					actions = append(actions, action)
					break
				}
			}
		}
	}
	return &ExecutionResult{
		TotalEvaluated: totalEvaluated,
		Actions:        actions,
		Errors:         errors,
		Duration:       time.Since(start),
	}, nil
}

func (m *Manager) Execute(ctx context.Context, dryRun bool) (*ExecutionResult, error) {
	result, err := m.Evaluate(ctx)
	if err != nil {
		return nil, err
	}
	if dryRun {
		m.logger.Info("dry run mode, skipping execution",
			zap.Int("actions", len(result.Actions)),
		)
		return result, nil
	}
	for i := range result.Actions {
		if err := m.executeAction(ctx, &result.Actions[i]); err != nil {
			result.Errors = append(result.Errors, ActionError{
				Partition: result.Actions[i].Partition,
				Action:    string(result.Actions[i].Action),
				Error:     err.Error(),
			})
			m.metrics.IncLifecycleErrors(string(result.Actions[i].Action))
			m.logger.Error("failed to execute action",
				zap.String("database", result.Actions[i].Database),
				zap.String("table", result.Actions[i].Table),
				zap.String("partition", result.Actions[i].Partition),
				zap.String("action", string(result.Actions[i].Action)),
				zap.Error(err),
			)
		} else {
			m.metrics.IncPartitionsProcessed(string(result.Actions[i].Action))
		}
	}
	result.Duration = time.Since(result.Duration)
	return result, nil
}

func (m *Manager) executeAction(ctx context.Context, action *PartitionAction) error {
	switch action.Action {
	case policy.ActionMoveToDisk:
		if action.TargetDisk == "" {
			return fmt.Errorf("target disk not specified for move action")
		}
		return m.executeShadowMove(ctx, action)
	case policy.ActionDrop:
		return m.client.DropPartition(ctx, action.Database, action.Table, action.Partition)
	case policy.ActionFreeze:
		return m.client.FreezePartition(ctx, action.Database, action.Table, action.Partition)
	case policy.ActionOptimize:
		return m.client.OptimizeTable(ctx, action.Database, action.Table, action.Partition, false)
	case policy.ActionArchive:
		if m.archiver == nil {
			return fmt.Errorf("archiver not configured")
		}
		_, err := m.archiver.ExportPartition(ctx, action.Database, action.Table, action.Partition)
		if err != nil {
			return fmt.Errorf("archive partition: %w", err)
		}
		return nil
	default:
		return fmt.Errorf("unknown action: %s", action.Action)
	}
}

func (m *Manager) executeShadowMove(ctx context.Context, action *PartitionAction) error {
	action.ShadowMove = true

	action.Steps = append(action.Steps, ShadowMoveStep{
		Step: "create_shadow", Database: action.Database, Table: action.Table,
		Partition: action.Partition, TargetDisk: action.TargetDisk, Status: "running",
	})
	if err := m.client.CreateShadowPartition(ctx, action.Database, action.Table, action.Partition, action.TargetDisk); err != nil {
		action.Steps[len(action.Steps)-1].Status = "error"
		action.Steps[len(action.Steps)-1].Error = err.Error()
		m.logger.Warn("shadow create failed, falling back to direct move",
			zap.String("partition", action.Partition),
			zap.Error(err),
		)
		action.ShadowMove = false
		action.Steps = append(action.Steps, ShadowMoveStep{
			Step: "direct_move", Database: action.Database, Table: action.Table,
			Partition: action.Partition, TargetDisk: action.TargetDisk, Status: "running",
		})
		if moveErr := m.client.MovePartitionToDisk(ctx, action.Database, action.Table, action.Partition, action.TargetDisk); moveErr != nil {
			action.Steps[len(action.Steps)-1].Status = "error"
			action.Steps[len(action.Steps)-1].Error = moveErr.Error()
			return moveErr
		}
		action.Steps[len(action.Steps)-1].Status = "success"
		return nil
	}
	action.Steps[len(action.Steps)-1].Status = "success"

	action.Steps = append(action.Steps, ShadowMoveStep{
		Step: "verify_shadow", Database: action.Database, Table: action.Table,
		Partition: action.Partition, TargetDisk: action.TargetDisk, Status: "running",
	})
	verified, err := m.client.VerifyShadowPartition(ctx, action.Database, action.Table, action.Partition)
	if err != nil {
		action.Steps[len(action.Steps)-1].Status = "warn"
		action.Steps[len(action.Steps)-1].Error = err.Error()
		m.logger.Warn("shadow verification failed, continuing with caution",
			zap.String("partition", action.Partition),
			zap.Error(err),
		)
	} else if verified {
		action.Steps[len(action.Steps)-1].Status = "success"
		m.logger.Info("shadow partition verified",
			zap.String("database", action.Database),
			zap.String("table", action.Table),
			zap.String("partition", action.Partition),
		)
	} else {
		action.Steps[len(action.Steps)-1].Status = "warn"
		action.Steps[len(action.Steps)-1].Error = "verification returned false"
		m.logger.Warn("shadow partition verification returned false",
			zap.String("partition", action.Partition),
		)
	}

	action.Steps = append(action.Steps, ShadowMoveStep{
		Step: "drop_old", Database: action.Database, Table: action.Table,
		Partition: action.Partition, Status: "running",
	})
	if err := m.client.DropOldPartition(ctx, action.Database, action.Table, action.Partition); err != nil {
		action.Steps[len(action.Steps)-1].Status = "error"
		action.Steps[len(action.Steps)-1].Error = err.Error()
		return fmt.Errorf("drop old partition after shadow move: %w", err)
	}
	action.Steps[len(action.Steps)-1].Status = "success"

	m.logger.Info("shadow partition move completed",
		zap.String("database", action.Database),
		zap.String("table", action.Table),
		zap.String("partition", action.Partition),
		zap.String("target_disk", action.TargetDisk),
	)
	return nil
}

func (m *Manager) ExpirePartitions(ctx context.Context, database, table string, retentionDays int) ([]PartitionAction, error) {
	partitions, err := m.client.GetPartitions(ctx, database, table)
	if err != nil {
		return nil, fmt.Errorf("get partitions: %w", err)
	}
	var expired []PartitionAction
	for _, part := range partitions {
		ageDays := m.calculateAge(part.MaxDate)
		if ageDays > retentionDays {
			expired = append(expired, PartitionAction{
				Database:   database,
				Table:      table,
				Partition:  part.Partition,
				Action:     policy.ActionDrop,
				Reason:     fmt.Sprintf("age %d days (UTC) exceeds retention %d days", ageDays, retentionDays),
				AgeDays:    ageDays,
				SizeBytes:  part.BytesOnDisk,
				Rows:       part.Rows,
			})
		}
	}
	return expired, nil
}

func (m *Manager) calculateAge(dateStr string) int {
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
