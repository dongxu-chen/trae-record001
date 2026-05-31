package migration

import (
	"context"
	"fmt"
	"log"
	"sort"
	"sync"
	"time"

	"redis-cluster-scaler/internal/backup"
	"redis-cluster-scaler/internal/cluster"
	"redis-cluster-scaler/pkg/config"
)

type MigrationStep struct {
	Slot       uint16 `json:"slot"`
	FromNode   string `json:"from_node"`
	ToNode     string `json:"to_node"`
	Status     string `json:"status"`
	KeysMoved  int64  `json:"keys_moved"`
	TotalKeys  int64  `json:"total_keys"`
	BatchSize  int64  `json:"batch_size"`
	ChunkIndex int    `json:"chunk_index"`
	TotalChunks int   `json:"total_chunks"`
	Error      string `json:"error,omitempty"`
}

type MigrationPlan struct {
	Steps           []MigrationStep `json:"steps"`
	Status          string          `json:"status"`
	StartAt         int64           `json:"start_at,omitempty"`
	EndAt           int64           `json:"end_at,omitempty"`
	Progress        float64         `json:"progress"`
	TotalKeysToMove int64           `json:"total_keys_to_move"`
	KeysMoved       int64           `json:"keys_moved"`
}

type MigrationTask struct {
	Plan   *MigrationPlan
	Cancel context.CancelFunc
}

type nodeLoad struct {
	nodeID       string
	slotCount    int
	memoryPct    float64
	qps          float64
	loadScore    float64
	excessSlots  int
	deficitSlots int
}

type Migrator struct {
	cfg        config.MigrationConfig
	clusterMgr *cluster.Manager
	backupMgr  *backup.BackupManager
	tasks      map[string]*MigrationTask
	tasksMu    sync.RWMutex
}

func New(cfg config.MigrationConfig, clusterMgr *cluster.Manager, backupMgr *backup.BackupManager) *Migrator {
	return &Migrator{
		cfg:        cfg,
		clusterMgr: clusterMgr,
		backupMgr:  backupMgr,
		tasks:      make(map[string]*MigrationTask),
	}
}

func (m *Migrator) RebalancePlan(ctx context.Context) (*MigrationPlan, error) {
	nodes, err := m.clusterMgr.GetNodes(ctx)
	if err != nil {
		return nil, fmt.Errorf("get nodes: %w", err)
	}

	var masters []cluster.NodeInfo
	for _, node := range nodes {
		if node.Role == "master" {
			masters = append(masters, node)
		}
	}

	if len(masters) == 0 {
		return nil, fmt.Errorf("no master nodes found")
	}

	targetSlots := 16384 / len(masters)
	remainder := 16384 % len(masters)

	loads := make([]nodeLoad, 0, len(masters))
	for _, node := range masters {
		sc := countSlots(node.Slots)
		memPct := node.Memory.UsedPercent

		ts := targetSlots
		if len(loads) < remainder {
			ts = targetSlots + 1
		}

		load := nodeLoad{
			nodeID:    node.ID,
			slotCount: sc,
			memoryPct: memPct,
		}
		load.loadScore = memPct + float64(sc)/16384.0*100

		if sc > ts {
			load.excessSlots = sc - ts
		} else if sc < ts {
			load.deficitSlots = ts - sc
		}

		loads = append(loads, load)
	}

	sort.Slice(loads, func(i, j int) bool {
		if m.cfg.DonorPriorityByMemory {
			if loads[i].memoryPct != loads[j].memoryPct {
				return loads[i].memoryPct > loads[j].memoryPct
			}
		}
		if loads[i].slotCount != loads[j].slotCount {
			return loads[i].slotCount > loads[j].slotCount
		}
		return loads[i].loadScore > loads[j].loadScore
	})

	plan := &MigrationPlan{
		Status: "planned",
		Steps:  []MigrationStep{},
	}

	donors := make([]*nodeLoad, 0)
	recipients := make([]*nodeLoad, 0)
	for i := range loads {
		if loads[i].excessSlots > 0 {
			donors = append(donors, &loads[i])
		}
		if loads[i].deficitSlots > 0 {
			recipients = append(recipients, &loads[i])
		}
	}

	for _, donor := range donors {
		var donorNode *cluster.NodeInfo
		for i := range masters {
			if masters[i].ID == donor.nodeID {
				donorNode = &masters[i]
				break
			}
		}
		if donorNode == nil {
			continue
		}

		slotsToGive := make([]uint16, 0)
		for _, sr := range donorNode.Slots {
			for slot := sr.Start; slot <= sr.End; slot++ {
				if len(slotsToGive) >= donor.excessSlots {
					break
				}
				slotsToGive = append(slotsToGive, slot)
			}
			if len(slotsToGive) >= donor.excessSlots {
				break
			}
		}

		for _, slot := range slotsToGive {
			recipient := pickRecipient(recipients)
			if recipient == nil {
				break
			}

			keyCount, _ := m.clusterMgr.CountKeysInSlot(ctx, slot)

			plan.Steps = append(plan.Steps, MigrationStep{
				Slot:      slot,
				FromNode:  donor.nodeID,
				ToNode:    recipient.nodeID,
				Status:    "pending",
				TotalKeys: keyCount,
			})

			plan.TotalKeysToMove += keyCount
			recipient.deficitSlots--
		}
	}

	return plan, nil
}

func pickRecipient(recipients []*nodeLoad) *nodeLoad {
	sort.Slice(recipients, func(i, j int) bool {
		if recipients[i].memoryPct != recipients[j].memoryPct {
			return recipients[i].memoryPct < recipients[j].memoryPct
		}
		return recipients[i].deficitSlots > recipients[j].deficitSlots
	})

	for _, r := range recipients {
		if r.deficitSlots > 0 {
			return r
		}
	}
	return nil
}

func (m *Migrator) ExecutePlan(ctx context.Context, plan *MigrationPlan) error {
	if len(plan.Steps) == 0 {
		plan.Status = "completed"
		return nil
	}

	taskCtx, cancel := context.WithCancel(ctx)
	taskID := fmt.Sprintf("migration-%d", time.Now().Unix())

	m.tasksMu.Lock()
	m.tasks[taskID] = &MigrationTask{Plan: plan, Cancel: cancel}
	m.tasksMu.Unlock()

	defer func() {
		m.tasksMu.Lock()
		delete(m.tasks, taskID)
		m.tasksMu.Unlock()

		if plan.Status == "completed" && m.cfg.PostMigrationBackup {
			go func() {
				if m.backupMgr != nil {
					log.Println("[Migration] Migration completed, triggering post-migration backup...")
					_, backupErr := m.backupMgr.CreateBackup(context.Background())
					if backupErr != nil {
						log.Printf("[Migration] Post-migration backup failed: %v", backupErr)
					} else {
						log.Println("[Migration] Post-migration backup completed successfully")
					}
				}
			}()
		}
	}()

	plan.Status = "running"
	plan.StartAt = time.Now().Unix()
	totalSteps := len(plan.Steps)
	completedSteps := 0

	for i := range plan.Steps {
		select {
		case <-taskCtx.Done():
			plan.Status = "cancelled"
			return fmt.Errorf("migration cancelled")
		default:
		}

		step := &plan.Steps[i]

		batchSize := m.calculateAdaptiveBatchSize(step.TotalKeys)
		step.BatchSize = batchSize

		chunks := calculateChunks(step.TotalKeys, batchSize)
		step.TotalChunks = chunks

		var keysMoved int64

		for chunk := 0; chunk < chunks; chunk++ {
			select {
			case <-taskCtx.Done():
				plan.Status = "cancelled"
				step.Status = "cancelled"
				return fmt.Errorf("migration cancelled")
			default:
			}

			step.ChunkIndex = chunk

			err := m.migrateSlotChunk(taskCtx, step.Slot, step.FromNode, step.ToNode, batchSize, chunk)
			if err != nil {
				step.Status = "failed"
				step.Error = err.Error()

				if m.shouldRetry(err) {
					retried := m.retryMigrateSlotChunk(taskCtx, step, batchSize, chunk)
					if !retried {
						plan.Status = "failed"
						return fmt.Errorf("slot %d chunk %d migration failed: %w", step.Slot, chunk, err)
					}
				} else {
					plan.Status = "failed"
					return fmt.Errorf("slot %d chunk %d migration failed: %w", step.Slot, chunk, err)
				}
			} else {
				keysMoved += batchSize
				if chunk == chunks-1 {
					remaining := step.TotalKeys - int64(chunk)*batchSize
					if remaining > 0 && remaining < batchSize {
						keysMoved -= (batchSize - remaining)
					}
				}
				step.KeysMoved = keysMoved
			}
		}

		plan.KeysMoved += step.KeysMoved
		step.Status = "completed"

		completedSteps++
		plan.Progress = float64(completedSteps) / float64(totalSteps) * 100
	}

	plan.Status = "completed"
	plan.EndAt = time.Now().Unix()
	plan.Progress = 100
	return nil
}

func (m *Migrator) calculateAdaptiveBatchSize(totalKeys int64) int64 {
	if !m.cfg.AdaptiveBatching {
		return int64(m.cfg.BatchSize)
	}

	baseSize := int64(m.cfg.BatchSize)
	smallThresh := m.cfg.SmallSlotThreshold
	largeThresh := m.cfg.LargeSlotThreshold

	switch {
	case totalKeys <= 100:
		return max(10, totalKeys)
	case totalKeys <= smallThresh:
		return max(50, baseSize/4)
	case totalKeys <= smallThresh*10:
		return max(100, baseSize/2)
	case totalKeys <= largeThresh:
		return baseSize
	default:
		return baseSize / 2
	}
}

func calculateChunks(totalKeys, batchSize int64) int {
	if totalKeys == 0 {
		return 1
	}
	chunks := int(totalKeys / batchSize)
	if totalKeys%batchSize != 0 {
		chunks++
	}
	if chunks == 0 {
		chunks = 1
	}
	return chunks
}

func (m *Migrator) migrateSlotChunk(ctx context.Context, slot uint16, fromNodeID, toNodeID string, batchSize int64, chunk int) error {
	if chunk == 0 {
		err := m.clusterMgr.SetSlot(ctx, slot, toNodeID, "IMPORTING")
		if err != nil {
			return fmt.Errorf("set importing: %w", err)
		}

		err = m.clusterMgr.SetSlot(ctx, slot, fromNodeID, "MIGRATING")
		if err != nil {
			return fmt.Errorf("set migrating: %w", err)
		}
	}

	keys, err := m.clusterMgr.GetKeysInSlot(ctx, slot, batchSize)
	if err != nil {
		return fmt.Errorf("get keys in slot: %w", err)
	}

	if len(keys) == 0 {
		if chunk == 0 {
			err = m.clusterMgr.SetSlot(ctx, slot, toNodeID, "NODE")
			if err != nil {
				return fmt.Errorf("set slot node: %w", err)
			}
		}
		return nil
	}

	var targetAddr string
	nodes, nodeErr := m.clusterMgr.GetNodes(ctx)
	if nodeErr != nil {
		return fmt.Errorf("get nodes: %w", nodeErr)
	}
	for _, node := range nodes {
		if node.ID == toNodeID {
			targetAddr = node.Addr
			break
		}
	}
	if targetAddr == "" {
		return fmt.Errorf("target node address not found for %s", toNodeID)
	}

	timeout := time.Duration(m.cfg.TimeoutSec) * time.Second
	for _, key := range keys {
		migrateErr := m.clusterMgr.MigrateKey(ctx, key, targetAddr, 0, timeout)
		if migrateErr != nil {
			return fmt.Errorf("migrate key %s: %w", key, migrateErr)
		}
	}

	remaining, _ := m.clusterMgr.CountKeysInSlot(ctx, slot)
	if remaining == 0 {
		err = m.clusterMgr.SetSlot(ctx, slot, toNodeID, "NODE")
		if err != nil {
			return fmt.Errorf("set slot node: %w", err)
		}
	}

	return nil
}

func (m *Migrator) retryMigrateSlotChunk(ctx context.Context, step *MigrationStep, batchSize int64, chunk int) bool {
	for i := 0; i < m.cfg.RetryCount; i++ {
		time.Sleep(time.Duration(m.cfg.RetryIntervalMs) * time.Millisecond)

		err := m.migrateSlotChunk(ctx, step.Slot, step.FromNode, step.ToNode, batchSize, chunk)
		if err == nil {
			return true
		}

		step.Error = err.Error()
	}
	return false
}

func (m *Migrator) shouldRetry(err error) bool {
	return true
}

func (m *Migrator) EvacuateNode(ctx context.Context, nodeID string) error {
	nodes, err := m.clusterMgr.GetNodes(ctx)
	if err != nil {
		return fmt.Errorf("get nodes: %w", err)
	}

	var targetNode *cluster.NodeInfo
	for i := range nodes {
		if nodes[i].ID == nodeID && nodes[i].Role == "master" {
			targetNode = &nodes[i]
			break
		}
	}

	if targetNode == nil {
		return fmt.Errorf("master node %s not found", nodeID)
	}

	var otherMasters []cluster.NodeInfo
	for _, node := range nodes {
		if node.Role == "master" && node.ID != nodeID {
			otherMasters = append(otherMasters, node)
		}
	}

	if len(otherMasters) == 0 {
		return fmt.Errorf("no other master nodes available for migration")
	}

	plan := &MigrationPlan{
		Status: "planned",
		Steps:  []MigrationStep{},
	}

	sort.Slice(otherMasters, func(i, j int) bool {
		if otherMasters[i].Memory.UsedPercent != otherMasters[j].Memory.UsedPercent {
			return otherMasters[i].Memory.UsedPercent < otherMasters[j].Memory.UsedPercent
		}
		return countSlots(otherMasters[i].Slots) < countSlots(otherMasters[j].Slots)
	})

	slotIdx := 0
	totalSlots := 0
	for _, sr := range targetNode.Slots {
		totalSlots += int(sr.End - sr.Start + 1)
	}

	slotsPerNode := totalSlots / len(otherMasters)

	for _, sr := range targetNode.Slots {
		for slot := sr.Start; slot <= sr.End; slot++ {
			targetIdx := slotIdx / slotsPerNode
			if targetIdx >= len(otherMasters) {
				targetIdx = len(otherMasters) - 1
			}

			keyCount, _ := m.clusterMgr.CountKeysInSlot(ctx, slot)

			plan.Steps = append(plan.Steps, MigrationStep{
				Slot:      slot,
				FromNode:  nodeID,
				ToNode:    otherMasters[targetIdx].ID,
				Status:    "pending",
				TotalKeys: keyCount,
			})
			plan.TotalKeysToMove += keyCount
			slotIdx++
		}
	}

	return m.ExecutePlan(ctx, plan)
}

func (m *Migrator) MigrateSlots(ctx context.Context, fromNodeID, toNodeID string, slots []uint16) error {
	plan := &MigrationPlan{
		Status: "planned",
		Steps:  []MigrationStep{},
	}

	for _, slot := range slots {
		keyCount, _ := m.clusterMgr.CountKeysInSlot(ctx, slot)
		plan.Steps = append(plan.Steps, MigrationStep{
			Slot:      slot,
			FromNode:  fromNodeID,
			ToNode:    toNodeID,
			Status:    "pending",
			TotalKeys: keyCount,
		})
		plan.TotalKeysToMove += keyCount
	}

	return m.ExecutePlan(ctx, plan)
}

func (m *Migrator) CancelMigration(taskID string) {
	m.tasksMu.RLock()
	defer m.tasksMu.RUnlock()

	if task, ok := m.tasks[taskID]; ok {
		task.Cancel()
		task.Plan.Status = "cancelling"
	}
}

func (m *Migrator) GetActiveTasks() map[string]*MigrationPlan {
	m.tasksMu.RLock()
	defer m.tasksMu.RUnlock()

	result := make(map[string]*MigrationPlan)
	for k, v := range m.tasks {
		result[k] = v.Plan
	}
	return result
}

func max(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}

func countSlots(slots []cluster.SlotRange) int {
	total := 0
	for _, sr := range slots {
		total += int(sr.End-sr.Start) + 1
	}
	return total
}
