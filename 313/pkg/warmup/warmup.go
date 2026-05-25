package warmup

import (
	"context"
	"fmt"
	"sync"
	"time"

	"ci-scheduler/pkg/dag"
)

type WarmupManager struct {
	mu                sync.Mutex
	warmupTasks       map[string]*dag.WarmupTask
	completedWarmups  map[string]bool
	warmupInProgress  map[string]bool
	preheatThreshold  int
	enabled           bool
}

func NewWarmupManager(preheatThreshold int) *WarmupManager {
	if preheatThreshold <= 0 {
		preheatThreshold = 2
	}
	return &WarmupManager{
		warmupTasks:       make(map[string]*dag.WarmupTask),
		completedWarmups:  make(map[string]bool),
		warmupInProgress:  make(map[string]bool),
		preheatThreshold:  preheatThreshold,
		enabled:           true,
	}
}

func (wm *WarmupManager) SetEnabled(enabled bool) {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	wm.enabled = enabled
}

func (wm *WarmupManager) IsEnabled() bool {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	return wm.enabled
}

func (wm *WarmupManager) SetPreheatThreshold(threshold int) {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	wm.preheatThreshold = threshold
}

func (wm *WarmupManager) CheckAndTriggerWarmup(ctx context.Context, dagGraph *dag.DAG, completedTaskID string, useK8s bool) []*dag.WarmupTask {
	wm.mu.Lock()
	defer wm.mu.Unlock()

	if !wm.enabled {
		return nil
	}

	completedNode, ok := dagGraph.Nodes[completedTaskID]
	if !ok {
		return nil
	}

	triggered := make([]*dag.WarmupTask, 0)

	for _, downstreamNode := range completedNode.OutEdges {
		downstreamTask := downstreamNode.Task

		if wm.completedWarmups[downstreamTask.ID] || wm.warmupInProgress[downstreamTask.ID] {
			continue
		}

		if downstreamTask.Status != dag.TaskStatusPending && downstreamTask.Status != dag.TaskStatusRetry {
			continue
		}

		remainingDeps := downstreamNode.InDegree
		if remainingDeps <= wm.preheatThreshold {
			warmupTasks := wm.generateWarmupTasks(downstreamTask)
			for _, wt := range warmupTasks {
				wm.warmupTasks[wt.ID] = wt
				wm.warmupInProgress[downstreamTask.ID] = true
				triggered = append(triggered, wt)

				go func(wt *dag.WarmupTask) {
					wm.executeWarmup(ctx, wt, useK8s)
				}(wt)
			}
		}
	}

	return triggered
}

func (wm *WarmupManager) generateWarmupTasks(task *dag.Task) []*dag.WarmupTask {
	tasks := make([]*dag.WarmupTask, 0)

	if task.Image != "" {
		warmupID := fmt.Sprintf("warmup-image-%s", task.ID)
		tasks = append(tasks, &dag.WarmupTask{
			ID:           warmupID,
			TargetTaskID: task.ID,
			Type:         dag.WarmupTypeImagePull,
			Image:        task.Image,
			Command:      []string{"docker", "pull", task.Image},
			Status:       dag.TaskStatusPending,
		})
	}

	if task.Labels != nil && task.Labels["warmup"] == "true" {
		if customCmd, ok := task.Labels["warmup_command"]; ok {
			warmupID := fmt.Sprintf("warmup-custom-%s", task.ID)
			tasks = append(tasks, &dag.WarmupTask{
				ID:           warmupID,
				TargetTaskID: task.ID,
				Type:         dag.WarmupTypeCustom,
				Image:        task.Image,
				Command:      []string{"sh", "-c", customCmd},
				Status:       dag.TaskStatusPending,
			})
		}
	}

	return tasks
}

func (wm *WarmupManager) executeWarmup(ctx context.Context, wt *dag.WarmupTask, useK8s bool) {
	wm.mu.Lock()
	wt.Status = dag.TaskStatusPreheating
	now := time.Now()
	wt.StartTime = &now
	wm.mu.Unlock()

	fmt.Printf("[Warmup] Starting %s for task %s: %s\n", wt.Type, wt.TargetTaskID, wt.Command)

	var success bool
	var err error

	success = wm.simulateWarmup(wt)
	err = nil

	wm.mu.Lock()
	defer wm.mu.Unlock()

	endTime := time.Now()
	wt.EndTime = &endTime

	if success {
		wt.Status = dag.TaskStatusPreheated
		wm.completedWarmups[wt.TargetTaskID] = true
		duration := wt.EndTime.Sub(*wt.StartTime)
		fmt.Printf("[Warmup] Completed %s for task %s in %v\n", wt.Type, wt.TargetTaskID, duration)
	} else {
		wt.Status = dag.TaskStatusFailed
		if err != nil {
			wt.Error = err.Error()
		}
		fmt.Printf("[Warmup] Failed %s for task %s: %v\n", wt.Type, wt.TargetTaskID, err)
	}

	delete(wm.warmupInProgress, wt.TargetTaskID)
}

func (wm *WarmupManager) simulateWarmup(wt *dag.WarmupTask) bool {
	simulatedTime := 500 * time.Millisecond
	if wt.Type == dag.WarmupTypeImagePull {
		simulatedTime = 2 * time.Second
	}

	select {
	case <-time.After(simulatedTime):
		return true
	case <-time.After(10 * time.Second):
		return false
	}
}

func (wm *WarmupManager) IsWarmedUp(taskID string) bool {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	return wm.completedWarmups[taskID]
}

func (wm *WarmupManager) IsWarmingUp(taskID string) bool {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	return wm.warmupInProgress[taskID]
}

func (wm *WarmupManager) GetWarmupTask(taskID string) *dag.WarmupTask {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	for _, wt := range wm.warmupTasks {
		if wt.TargetTaskID == taskID {
			return wt
		}
	}
	return nil
}

func (wm *WarmupManager) GetAllWarmupTasks() map[string]*dag.WarmupTask {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	result := make(map[string]*dag.WarmupTask)
	for k, v := range wm.warmupTasks {
		result[k] = v
	}
	return result
}

func (wm *WarmupManager) GetWarmupStats() (completed, inProgress, failed int) {
	wm.mu.Lock()
	defer wm.mu.Unlock()

	completed = len(wm.completedWarmups)
	inProgress = len(wm.warmupInProgress)

	for _, wt := range wm.warmupTasks {
		if wt.Status == dag.TaskStatusFailed {
			failed++
		}
	}
	return
}

func (wm *WarmupManager) PrintStatus() {
	wm.mu.Lock()
	defer wm.mu.Unlock()

	completed, inProgress, failed := wm.GetWarmupStats()

	fmt.Println("\n=== Warmup Manager Status ===")
	fmt.Printf("Enabled: %v\n", wm.enabled)
	fmt.Printf("Preheat Threshold: %d remaining deps\n", wm.preheatThreshold)
	fmt.Printf("Completed: %d | In Progress: %d | Failed: %d\n", completed, inProgress, failed)

	if len(wm.warmupTasks) > 0 {
		fmt.Println("\nWarmup Tasks:")
		fmt.Printf("%-30s %-15s %-12s %-15s %s\n",
			"ID", "Target Task", "Type", "Status", "Duration")
		fmt.Println("--------------------------------------------------------------------------------")

		for _, wt := range wm.warmupTasks {
			duration := "-"
			if wt.StartTime != nil && wt.EndTime != nil {
				duration = wt.EndTime.Sub(*wt.StartTime).String()
			}
			fmt.Printf("%-30s %-15s %-12s %-15s %s\n",
				wt.ID, wt.TargetTaskID, wt.Type, wt.Status, duration)
		}
		fmt.Println("================================================================================")
	}
	fmt.Println()
}
