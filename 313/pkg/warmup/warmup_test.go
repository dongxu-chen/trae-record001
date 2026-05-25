package warmup

import (
	"context"
	"testing"
	"time"

	"ci-scheduler/pkg/dag"
)

func TestNewWarmupManager(t *testing.T) {
	wm := NewWarmupManager(2)

	if wm == nil {
		t.Fatal("NewWarmupManager returned nil")
	}

	if wm.preheatThreshold != 2 {
		t.Errorf("expected preheatThreshold 2, got %d", wm.preheatThreshold)
	}

	if !wm.enabled {
		t.Error("expected enabled true, got false")
	}
}

func TestNewWarmupManager_ZeroThreshold(t *testing.T) {
	wm := NewWarmupManager(0)

	if wm.preheatThreshold != 2 {
		t.Errorf("expected default preheatThreshold 2 when 0 provided, got %d", wm.preheatThreshold)
	}
}

func TestWarmupManager_EnableDisable(t *testing.T) {
	wm := NewWarmupManager(2)

	if !wm.IsEnabled() {
		t.Error("expected enabled true by default")
	}

	wm.SetEnabled(false)
	if wm.IsEnabled() {
		t.Error("expected enabled false after SetEnabled(false)")
	}

	wm.SetEnabled(true)
	if !wm.IsEnabled() {
		t.Error("expected enabled true after SetEnabled(true)")
	}
}

func TestWarmupManager_SetPreheatThreshold(t *testing.T) {
	wm := NewWarmupManager(2)

	wm.SetPreheatThreshold(3)
	if wm.preheatThreshold != 3 {
		t.Errorf("expected preheatThreshold 3, got %d", wm.preheatThreshold)
	}
}

func TestWarmupManager_CheckAndTriggerWarmup_Disabled(t *testing.T) {
	wm := NewWarmupManager(1)
	wm.SetEnabled(false)

	dagGraph := createTestDAG()
	result := wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)

	if result != nil {
		t.Error("expected nil when warmup is disabled")
	}
}

func TestWarmupManager_CheckAndTriggerWarmup_NoSuchTask(t *testing.T) {
	wm := NewWarmupManager(1)

	dagGraph := createTestDAG()
	result := wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "non-existent", false)

	if result != nil {
		t.Error("expected nil for non-existent task")
	}
}

func TestWarmupManager_CheckAndTriggerWarmup_AboveThreshold(t *testing.T) {
	wm := NewWarmupManager(0)

	dagGraph := createTestDAG()
	result := wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)

	if len(result) != 0 {
		t.Errorf("expected 0 warmup tasks when above threshold, got %d", len(result))
	}
}

func TestWarmupManager_CheckAndTriggerWarmup_TriggerImagePull(t *testing.T) {
	wm := NewWarmupManager(10)

	dagGraph := createTestDAG()
	result := wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)

	if len(result) == 0 {
		t.Error("expected at least 1 warmup task")
	}

	foundImagePull := false
	for _, wt := range result {
		if wt.Type == dag.WarmupTypeImagePull {
			foundImagePull = true
			if wt.TargetTaskID != "task-2" {
				t.Errorf("expected target task-2, got %s", wt.TargetTaskID)
			}
			if wt.Image != "golang:1.21" {
				t.Errorf("expected image golang:1.21, got %s", wt.Image)
			}
			break
		}
	}

	if !foundImagePull {
		t.Error("expected image pull warmup task")
	}
}

func TestWarmupManager_IsWarmedUp(t *testing.T) {
	wm := NewWarmupManager(10)
	dagGraph := createTestDAG()

	if wm.IsWarmedUp("task-2") {
		t.Error("expected task-2 not warmed up initially")
	}

	wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)

	time.Sleep(3 * time.Second)

	if !wm.IsWarmedUp("task-2") {
		t.Error("expected task-2 warmed up after completion")
	}
}

func TestWarmupManager_IsWarmingUp(t *testing.T) {
	wm := NewWarmupManager(10)
	dagGraph := createTestDAG()

	if wm.IsWarmingUp("task-2") {
		t.Error("expected task-2 not warming up initially")
	}

	wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)

	if !wm.IsWarmingUp("task-2") {
		t.Error("expected task-2 warming up after trigger")
	}

	time.Sleep(3 * time.Second)

	if wm.IsWarmingUp("task-2") {
		t.Error("expected task-2 not warming up after completion")
	}
}

func TestWarmupManager_GetWarmupStats(t *testing.T) {
	wm := NewWarmupManager(10)
	dagGraph := createTestDAG()

	completed, inProgress, failed := wm.GetWarmupStats()
	if completed != 0 || inProgress != 0 || failed != 0 {
		t.Errorf("expected all zeros initially, got completed=%d, inProgress=%d, failed=%d",
			completed, inProgress, failed)
	}

	wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)

	completed, inProgress, failed = wm.GetWarmupStats()
	if inProgress == 0 {
		t.Errorf("expected inProgress > 0 after trigger, got %d", inProgress)
	}

	time.Sleep(3 * time.Second)

	completed, inProgress, failed = wm.GetWarmupStats()
	if completed == 0 {
		t.Errorf("expected completed > 0 after completion, got %d", completed)
	}
	if inProgress != 0 {
		t.Errorf("expected inProgress 0 after completion, got %d", inProgress)
	}
}

func TestWarmupManager_GetWarmupTask(t *testing.T) {
	wm := NewWarmupManager(10)
	dagGraph := createTestDAG()

	wt := wm.GetWarmupTask("task-2")
	if wt != nil {
		t.Error("expected nil for non-triggered task")
	}

	wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)

	wt = wm.GetWarmupTask("task-2")
	if wt == nil {
		t.Error("expected non-nil warmup task after trigger")
	}
	if wt.TargetTaskID != "task-2" {
		t.Errorf("expected target task-2, got %s", wt.TargetTaskID)
	}
}

func TestWarmupManager_AlreadyWarmedUp(t *testing.T) {
	wm := NewWarmupManager(10)
	dagGraph := createTestDAG()

	wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)
	time.Sleep(3 * time.Second)

	result := wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)
	if len(result) != 0 {
		t.Errorf("expected 0 warmup tasks for already warmed up task, got %d", len(result))
	}
}

func TestWarmupManager_CustomWarmup(t *testing.T) {
	wm := NewWarmupManager(10)
	dagGraph := createTestDAGWithCustomWarmup()

	result := wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)

	foundCustom := false
	for _, wt := range result {
		if wt.Type == dag.WarmupTypeCustom {
			foundCustom = true
			break
		}
	}

	if !foundCustom {
		t.Error("expected custom warmup task")
	}
}

func TestWarmupManager_DuplicateTriggerWhileWarming(t *testing.T) {
	wm := NewWarmupManager(10)
	dagGraph := createTestDAG()

	result1 := wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)
	if len(result1) == 0 {
		t.Fatal("expected warmup tasks on first trigger")
	}

	result2 := wm.CheckAndTriggerWarmup(context.Background(), dagGraph, "task-1", false)
	if len(result2) != 0 {
		t.Errorf("expected 0 warmup tasks while warming, got %d", len(result2))
	}
}

func createTestDAG() *dag.DAG {
	pipeline := &dag.Pipeline{
		ID:   "test-pipeline",
		Name: "Test Pipeline",
		Tasks: []dag.Task{
			{
				ID:            "task-1",
				Name:          "Task 1",
				Image:         "alpine:latest",
				Command:       []string{"echo", "task1"},
				EstimatedTime: 1 * time.Second,
				Priority:      1,
				Resources: dag.TaskResources{
					CPU:    0.5,
					Memory: 256,
				},
			},
			{
				ID:            "task-2",
				Name:          "Task 2",
				Image:         "golang:1.21",
				Command:       []string{"echo", "task2"},
				EstimatedTime: 2 * time.Second,
				Priority:      1,
				Resources: dag.TaskResources{
					CPU:    1.0,
					Memory: 512,
				},
				Dependencies: []string{"task-1"},
			},
			{
				ID:            "task-3",
				Name:          "Task 3",
				Image:         "node:18",
				Command:       []string{"echo", "task3"},
				EstimatedTime: 2 * time.Second,
				Priority:      1,
				Resources: dag.TaskResources{
					CPU:    1.0,
					Memory: 512,
				},
				Dependencies: []string{"task-1"},
			},
		},
	}

	dagGraph, _ := dag.BuildDAG(pipeline)
	return dagGraph
}

func createTestDAGWithCustomWarmup() *dag.DAG {
	pipeline := &dag.Pipeline{
		ID:   "test-pipeline",
		Name: "Test Pipeline",
		Tasks: []dag.Task{
			{
				ID:            "task-1",
				Name:          "Task 1",
				Image:         "alpine:latest",
				Command:       []string{"echo", "task1"},
				EstimatedTime: 1 * time.Second,
				Priority:      1,
				Resources: dag.TaskResources{
					CPU:    0.5,
					Memory: 256,
				},
			},
			{
				ID:            "task-2",
				Name:          "Task 2",
				Image:         "golang:1.21",
				Command:       []string{"echo", "task2"},
				EstimatedTime: 2 * time.Second,
				Priority:      1,
				Labels: map[string]string{
					"warmup":         "true",
					"warmup_command": "go mod download",
				},
				Resources: dag.TaskResources{
					CPU:    1.0,
					Memory: 512,
				},
				Dependencies: []string{"task-1"},
			},
		},
	}

	dagGraph, _ := dag.BuildDAG(pipeline)
	return dagGraph
}
