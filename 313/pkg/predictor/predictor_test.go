package predictor

import (
	"fmt"
	"testing"
	"time"

	"ci-scheduler/pkg/dag"
)

func TestNewTimePredictor(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()

	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	if tp == nil {
		t.Fatal("NewTimePredictor returned nil")
	}

	if tp.parallelism != 3 {
		t.Errorf("expected parallelism 3, got %d", tp.parallelism)
	}

	if tp.dag == nil {
		t.Error("expected dag to be set")
	}

	if tp.criticalPath == nil {
		t.Error("expected criticalPath to be set")
	}

	if len(tp.actualTimes) != 0 {
		t.Errorf("expected empty actualTimes initially, got %d entries", len(tp.actualTimes))
	}

	if len(tp.taskStartTimes) != 0 {
		t.Errorf("expected empty taskStartTimes initially, got %d entries", len(tp.taskStartTimes))
	}
}

func TestTimePredictor_SetPipelineStartTime(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	startTime := time.Now()
	tp.SetPipelineStartTime(startTime)

	if tp.pipelineStartTime.IsZero() {
		t.Error("expected pipelineStartTime to be set")
	}

	if !tp.pipelineStartTime.Equal(startTime) {
		t.Errorf("expected pipelineStartTime to be %v, got %v", startTime, tp.pipelineStartTime)
	}
}

func TestTimePredictor_UpdateParallelism(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	tp.UpdateParallelism(5)
	if tp.parallelism != 5 {
		t.Errorf("expected parallelism 5, got %d", tp.parallelism)
	}

	tp.UpdateParallelism(0)
	if tp.parallelism != 5 {
		t.Errorf("expected parallelism to remain 5 when 0 provided, got %d", tp.parallelism)
	}
}

func TestTimePredictor_RecordTaskStart(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	startTime := time.Now()
	tp.RecordTaskStart("task-1", startTime)

	if _, ok := tp.taskStartTimes["task-1"]; !ok {
		t.Error("expected task-1 start time to be recorded")
	}

	if !tp.taskStartTimes["task-1"].Equal(startTime) {
		t.Errorf("expected start time %v, got %v", startTime, tp.taskStartTimes["task-1"])
	}
}

func TestTimePredictor_RecordTaskComplete(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	startTime := time.Now().Add(-5 * time.Second)
	endTime := time.Now()

	tp.RecordTaskStart("task-1", startTime)
	tp.RecordTaskComplete("task-1", endTime)

	at, ok := tp.actualTimes["task-1"]
	if !ok {
		t.Fatal("expected task-1 actual time to be recorded")
	}

	expectedDuration := endTime.Sub(startTime)
	if at.ActualTime != expectedDuration {
		t.Errorf("expected actual time %v, got %v", expectedDuration, at.ActualTime)
	}

	if at.TaskID != "task-1" {
		t.Errorf("expected task ID task-1, got %s", at.TaskID)
	}

	_, ok = tp.taskStartTimes["task-1"]
	if !ok {
		t.Error("expected task-1 start time to remain recorded")
	}
}

func TestTimePredictor_RecordTaskComplete_NoStart(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	tp.RecordTaskComplete("task-1", time.Now())

	if _, ok := tp.actualTimes["task-1"]; ok {
		t.Error("expected no actual time when start time not recorded")
	}
}

func TestTimePredictor_GetSlowdownFactor_NoData(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	factor := tp.GetSlowdownFactor()
	if factor != 1.0 {
		t.Errorf("expected slowdown factor 1.0 with no data, got %.2f", factor)
	}
}

func TestTimePredictor_GetSlowdownFactor_WithData(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	now := time.Now()

	tp.RecordTaskStart("task-1", now.Add(-10*time.Second))
	tp.RecordTaskComplete("task-1", now.Add(-5*time.Second))

	tp.RecordTaskStart("task-2", now.Add(-8*time.Second))
	tp.RecordTaskComplete("task-2", now.Add(-4*time.Second))

	factor := tp.GetSlowdownFactor()

	expectedMin := 1.0
	expectedMax := 10.0
	if factor < expectedMin || factor > expectedMax {
		t.Errorf("expected slowdown factor between %.1f and %.1f, got %.2f", expectedMin, expectedMax, factor)
	}
}

func TestTimePredictor_CalculateRemainingTime_AllPending(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	result := tp.CalculateRemainingTime()

	if result.TotalEstimated <= 0 {
		t.Errorf("expected TotalEstimated > 0, got %v", result.TotalEstimated)
	}

	if result.RemainingEstimated <= 0 {
		t.Errorf("expected RemainingEstimated > 0, got %v", result.RemainingEstimated)
	}

	if result.ProgressPercent != 0 {
		t.Errorf("expected ProgressPercent 0, got %.1f", result.ProgressPercent)
	}

	if result.TasksCompleted != 0 {
		t.Errorf("expected TasksCompleted 0, got %d", result.TasksCompleted)
	}

	if result.ETA.IsZero() {
		t.Error("expected ETA to be set")
	}
}

func TestTimePredictor_CalculateRemainingTime_PartialComplete(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	now := time.Now()

	tp.RecordTaskStart("task-1", now.Add(-5*time.Second))
	tp.RecordTaskComplete("task-1", now.Add(-3*time.Second))

	dagGraph.MarkTaskComplete("task-1")

	result := tp.CalculateRemainingTime()

	if result.ProgressPercent <= 0 {
		t.Errorf("expected ProgressPercent > 0, got %.1f", result.ProgressPercent)
	}

	if result.TasksCompleted != 1 {
		t.Errorf("expected TasksCompleted 1, got %d", result.TasksCompleted)
	}

	if result.TotalActualSoFar <= 0 {
		t.Errorf("expected TotalActualSoFar > 0, got %v", result.TotalActualSoFar)
	}
}

func TestTimePredictor_GetTaskActualTime(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	_, ok := tp.GetTaskActualTime("task-1")
	if ok {
		t.Error("expected false for non-existent task")
	}

	now := time.Now()
	tp.RecordTaskStart("task-1", now.Add(-5*time.Second))
	tp.RecordTaskComplete("task-1", now.Add(-3*time.Second))

	at, ok := tp.GetTaskActualTime("task-1")
	if !ok {
		t.Fatal("expected true for existing task")
	}

	if at.TaskID != "task-1" {
		t.Errorf("expected task ID task-1, got %s", at.TaskID)
	}

	expectedDuration := 2 * time.Second
	if at.ActualTime != expectedDuration {
		t.Errorf("expected actual time %v, got %v", expectedDuration, at.ActualTime)
	}
}

func TestTimePredictor_GetAllActualTimes(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	now := time.Now()

	tp.RecordTaskStart("task-1", now.Add(-10*time.Second))
	tp.RecordTaskComplete("task-1", now.Add(-8*time.Second))

	tp.RecordTaskStart("task-2", now.Add(-7*time.Second))
	tp.RecordTaskComplete("task-2", now.Add(-5*time.Second))

	times := tp.GetAllActualTimes()
	if len(times) != 2 {
		t.Errorf("expected 2 actual times, got %d", len(times))
	}
}

func TestPredictionResult_GetProgressBar(t *testing.T) {
	pr := &PredictionResult{
		ProgressPercent: 50.0,
	}

	bar := pr.GetProgressBar(20)
	if len(bar) < 20 {
		t.Errorf("expected progress bar at least 20 chars, got %d", len(bar))
	}

	pr2 := &PredictionResult{
		ProgressPercent: 150.0,
	}
	bar2 := pr2.GetProgressBar(20)
	if len(bar2) < 20 {
		t.Errorf("expected progress bar at least 20 chars for >100%%, got %d", len(bar2))
	}
}

func TestPredictionResult_GetTimeRemaining(t *testing.T) {
	tests := []struct {
		remaining time.Duration
		expected  string
	}{
		{30 * time.Second, "30 seconds"},
		{2 * time.Minute, "2 minutes"},
		{90 * time.Minute, "1 hours 30 minutes"},
		{65 * time.Second, "65 seconds"},
	}

	for _, tt := range tests {
		t.Run(tt.remaining.String(), func(t *testing.T) {
			pr := &PredictionResult{
				RemainingEstimated: tt.remaining,
			}
			result := pr.GetTimeRemaining()
			if result != tt.expected {
				t.Errorf("expected %q, got %q", tt.expected, result)
			}
		})
	}
}

func TestTimePredictor_CalculateRemainingTime_OptimisticVsPessimistic(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	result := tp.CalculateRemainingTime()

	if result.RemainingOptimistic > result.RemainingEstimated {
		t.Errorf("expected optimistic <= estimated, got optimistic=%v, estimated=%v",
			result.RemainingOptimistic, result.RemainingEstimated)
	}

	if result.RemainingEstimated > result.RemainingPessimistic {
		t.Errorf("expected estimated <= pessimistic, got estimated=%v, pessimistic=%v",
			result.RemainingEstimated, result.RemainingPessimistic)
	}
}

func TestTimePredictor_ParallelismEfficiency(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	maxParallel := dagGraph.GetMaxParallelism()

	tests := []struct {
		name          string
		parallelism   int
		expectMinEff  float64
		expectMaxEff  float64
	}{
		{
			name:         "Full parallelism",
			parallelism:  maxParallel,
			expectMinEff: 0.9,
			expectMaxEff: 1.0,
		},
		{
			name:         "Half parallelism",
			parallelism:  maxParallel / 2,
			expectMinEff: 0.3,
			expectMaxEff: 0.6,
		},
		{
			name:         "Low parallelism",
			parallelism:  1,
			expectMinEff: 0.3,
			expectMaxEff: 0.5,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, tt.parallelism)
			result := tp.CalculateRemainingTime()

			if result.ParallelismEfficiency < tt.expectMinEff {
				t.Errorf("expected efficiency >= %.2f, got %.2f", tt.expectMinEff, result.ParallelismEfficiency)
			}
			if result.ParallelismEfficiency > tt.expectMaxEff {
				t.Errorf("expected efficiency <= %.2f, got %.2f", tt.expectMaxEff, result.ParallelismEfficiency)
			}
		})
	}
}

func TestTimePredictor_CriticalPathRemaining(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	result := tp.CalculateRemainingTime()

	if result.CriticalPathRemaining <= 0 {
		t.Errorf("expected CriticalPathRemaining > 0, got %v", result.CriticalPathRemaining)
	}

	for _, taskID := range criticalPath.Path {
		if task, ok := dagGraph.Tasks[taskID]; ok {
			task.Status = dag.TaskStatusSuccess
		}
	}

	result2 := tp.CalculateRemainingTime()
	if result2.CriticalPathRemaining != 0 {
		t.Errorf("expected CriticalPathRemaining 0 when all critical path tasks complete, got %v",
			result2.CriticalPathRemaining)
	}
}

func TestTimePredictor_HistoricalDataLimit(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	now := time.Now()

	for i := 0; i < 150; i++ {
		taskID := fmt.Sprintf("task-%d", i)
		tp.RecordTaskStart(taskID, now.Add(-time.Duration(i+1)*time.Second))
		tp.RecordTaskComplete(taskID, now.Add(-time.Duration(i)*time.Second))
	}

	if len(tp.historicalData) > 100 {
		t.Errorf("expected historical data <= 100 entries, got %d", len(tp.historicalData))
	}
}

func TestTimePredictor_SlowdownFactor_NoEstimatedTime(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGWithNoEstimatedTime()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	now := time.Now()
	tp.RecordTaskStart("task-1", now.Add(-5*time.Second))
	tp.RecordTaskComplete("task-1", now.Add(-3*time.Second))

	factor := tp.GetSlowdownFactor()
	if factor != 1.0 {
		t.Errorf("expected slowdown factor 1.0 when no estimated time, got %.2f", factor)
	}
}

func TestPredictionResult_Print(t *testing.T) {
	pr := &PredictionResult{
		TotalEstimated:       10 * time.Minute,
		TotalActualSoFar:     5 * time.Minute,
		RemainingEstimated:   5 * time.Minute,
		RemainingOptimistic:  4 * time.Minute,
		RemainingPessimistic: 8 * time.Minute,
		ETA:                  time.Now().Add(5 * time.Minute),
		ProgressPercent:      50.0,
		TasksCompleted:       5,
		TasksRemaining:       5,
		TasksRunning:         2,
		SlowdownFactor:       1.2,
		CriticalPathRemaining: 3 * time.Minute,
		ParallelismEfficiency: 0.8,
	}

	pr.Print()
}

func TestTimePredictor_PrintTaskStats_NoData(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	tp.PrintTaskStats()
}

func TestTimePredictor_PrintTaskStats_WithData(t *testing.T) {
	dagGraph, scheduleInfo, criticalPath := createTestDAGAndSchedule()
	tp := NewTimePredictor(dagGraph, scheduleInfo, criticalPath, 3)

	now := time.Now()
	tp.RecordTaskStart("task-1", now.Add(-5*time.Second))
	tp.RecordTaskComplete("task-1", now.Add(-3*time.Second))

	tp.RecordTaskStart("task-2", now.Add(-8*time.Second))
	tp.RecordTaskComplete("task-2", now.Add(-5*time.Second))

	tp.PrintTaskStats()
}

func createTestDAGAndSchedule() (*dag.DAG, map[string]*dag.TaskScheduleInfo, *dag.CriticalPathInfo) {
	pipeline := &dag.Pipeline{
		ID:   "test-pipeline",
		Name: "Test Pipeline",
		Tasks: []dag.Task{
			{
				ID:            "task-1",
				Name:          "Task 1",
				Image:         "alpine:latest",
				Command:       []string{"echo", "task1"},
				EstimatedTime: 2 * time.Second,
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
				EstimatedTime: 4 * time.Second,
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
				EstimatedTime: 3 * time.Second,
				Priority:      1,
				Resources: dag.TaskResources{
					CPU:    1.0,
					Memory: 512,
				},
				Dependencies: []string{"task-1"},
			},
			{
				ID:            "task-4",
				Name:          "Task 4",
				Image:         "python:3.11",
				Command:       []string{"echo", "task4"},
				EstimatedTime: 2 * time.Second,
				Priority:      1,
				Resources: dag.TaskResources{
					CPU:    0.5,
					Memory: 256,
				},
				Dependencies: []string{"task-2", "task-3"},
			},
		},
	}

	dagGraph, _ := dag.BuildDAG(pipeline)
	criticalPath, scheduleInfo, _ := dagGraph.CalculateCriticalPath()
	return dagGraph, scheduleInfo, criticalPath
}

func createTestDAGWithNoEstimatedTime() (*dag.DAG, map[string]*dag.TaskScheduleInfo, *dag.CriticalPathInfo) {
	pipeline := &dag.Pipeline{
		ID:   "test-pipeline",
		Name: "Test Pipeline",
		Tasks: []dag.Task{
			{
				ID:            "task-1",
				Name:          "Task 1",
				Image:         "alpine:latest",
				Command:       []string{"echo", "task1"},
				EstimatedTime: 0,
				Priority:      1,
				Resources: dag.TaskResources{
					CPU:    0.5,
					Memory: 256,
				},
			},
		},
	}

	dagGraph, _ := dag.BuildDAG(pipeline)
	criticalPath, scheduleInfo, _ := dagGraph.CalculateCriticalPath()
	return dagGraph, scheduleInfo, criticalPath
}
