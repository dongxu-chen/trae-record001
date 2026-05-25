package predictor

import (
	"fmt"
	"math"
	"sort"
	"sync"
	"time"

	"ci-scheduler/pkg/dag"
)

type TaskActualTime struct {
	TaskID        string
	EstimatedTime time.Duration
	ActualTime    time.Duration
	CompletedAt   time.Time
}

type PredictionResult struct {
	TotalEstimated     time.Duration
	TotalActualSoFar     time.Duration
	RemainingEstimated  time.Duration
	RemainingOptimistic time.Duration
	RemainingPessimistic time.Duration
	ETA                time.Time
	ProgressPercent        float64
	TasksCompleted      int
	TasksRemaining      int
	TasksRunning     int
	SlowdownFactor     float64
	CriticalPathRemaining time.Duration
	ParallelismEfficiency float64
}

type TimePredictor struct {
	mu                sync.Mutex
	dag               *dag.DAG
	scheduleInfo      map[string]*dag.TaskScheduleInfo
	criticalPath      *dag.CriticalPathInfo
	actualTimes       map[string]*TaskActualTime
	taskStartTimes     map[string]time.Time
	historicalData    []*TaskActualTime
	pipelineStartTime time.Time
	parallelism       int
	maxParallelism    int
}

func NewTimePredictor(dag *dag.DAG, scheduleInfo map[string]*dag.TaskScheduleInfo, criticalPath *dag.CriticalPathInfo, parallelism int) *TimePredictor {
	return &TimePredictor{
		dag:            dag,
		scheduleInfo:   scheduleInfo,
		criticalPath:   criticalPath,
		actualTimes:    make(map[string]*TaskActualTime),
		taskStartTimes: make(map[string]time.Time),
		historicalData: make([]*TaskActualTime, 0),
		parallelism:    parallelism,
		maxParallelism: dag.GetMaxParallelism(),
	}
}

func (tp *TimePredictor) SetPipelineStartTime(startTime time.Time) {
	tp.mu.Lock()
	defer tp.mu.Unlock()
	tp.pipelineStartTime = startTime
}

func (tp *TimePredictor) UpdateParallelism(parallelism int) {
	tp.mu.Lock()
	defer tp.mu.Unlock()
	if parallelism > 0 {
		tp.parallelism = parallelism
	}
}

func (tp *TimePredictor) RecordTaskStart(taskID string, startTime time.Time) {
	tp.mu.Lock()
	defer tp.mu.Unlock()
	tp.taskStartTimes[taskID] = startTime
}

func (tp *TimePredictor) RecordTaskComplete(taskID string, endTime time.Time) {
	tp.mu.Lock()
	defer tp.mu.Unlock()

	startTime, ok := tp.taskStartTimes[taskID]
	if !ok {
		return
	}

	actualDuration := endTime.Sub(startTime)

	task, ok := tp.dag.Tasks[taskID]
	if !ok {
		return
	}

	estimatedTime := task.EstimatedTime
	if estimatedTime == 0 {
		estimatedTime = 1 * time.Minute
	}

	actual := &TaskActualTime{
		TaskID:        taskID,
		EstimatedTime: estimatedTime,
		ActualTime:    actualDuration,
		CompletedAt:   endTime,
	}

	tp.actualTimes[taskID] = actual
	tp.historicalData = append(tp.historicalData, actual)

	if len(tp.historicalData) > 100 {
		tp.historicalData = tp.historicalData[1:]
	}
}

func (tp *TimePredictor) GetSlowdownFactor() float64 {
	tp.mu.Lock()
	defer tp.mu.Unlock()
	return tp.calculateSlowdownFactorLocked()
}

func (tp *TimePredictor) calculateSlowdownFactorLocked() float64 {
	if len(tp.historicalData) == 0 {
		return 1.0
	}

	var totalActual time.Duration
	var totalEstimated time.Duration

	for _, at := range tp.historicalData {
		if at.EstimatedTime > 0 {
			totalActual += at.ActualTime
			totalEstimated += at.EstimatedTime
		}
	}

	if totalEstimated == 0 {
		return 1.0
	}

	recentWeight := 0.7
	overallFactor := float64(totalActual) / float64(totalEstimated)

	if len(tp.historicalData) >= 3 {
		recentCount := 3
		if len(tp.historicalData) < recentCount {
			recentCount = len(tp.historicalData)
		}
		recent := tp.historicalData[len(tp.historicalData)-recentCount:]

		var recentActual time.Duration
		var recentEstimated time.Duration
		for _, at := range recent {
			if at.EstimatedTime > 0 {
				recentActual += at.ActualTime
				recentEstimated += at.EstimatedTime
			}
		}

		if recentEstimated > 0 {
			recentFactor := float64(recentActual) / float64(recentEstimated)
			return recentWeight*recentFactor + (1-recentWeight)*overallFactor
		}
	}

	return overallFactor
}

func (tp *TimePredictor) CalculateRemainingTime() *PredictionResult {
	tp.mu.Lock()
	defer tp.mu.Unlock()

	now := time.Now()
	slowdownFactor := tp.calculateSlowdownFactorLocked()

	totalEstimated := tp.criticalPath.TotalDuration

	totalActualSoFar := time.Duration(0)
	completedCount := 0
	runningCount := 0

	for _, task := range tp.dag.Tasks {
		if task.Status == dag.TaskStatusSuccess {
			completedCount++
			if at, ok := tp.actualTimes[task.ID]; ok {
				totalActualSoFar += at.ActualTime
			}
		} else if task.Status == dag.TaskStatusRunning || task.Status == dag.TaskStatusRetry {
			runningCount++
		}
	}

	remainingEstimated := tp.calculateRemainingTimeLocked(slowdownFactor)
	remainingOptimistic := tp.calculateRemainingTimeLocked(1.0)
	remainingPessimistic := tp.calculateRemainingTimeLocked(slowdownFactor*1.5)

	parallelismEfficiency := tp.calculateParallelismEfficiencyLocked()
	adjustedRemaining := time.Duration(float64(remainingEstimated) / parallelismEfficiency)

	progressPercent := 0.0
	if totalEstimated > 0 {
		progressPercent = math.Min(100.0, float64(totalActualSoFar)/float64(totalEstimated)*100)
	}

	criticalPathRemaining := tp.calculateCriticalPathRemainingLocked(slowdownFactor)

	eta := now.Add(adjustedRemaining)

	totalTasks := len(tp.dag.Tasks)
	remainingCount := totalTasks - completedCount - runningCount

	return &PredictionResult{
		TotalEstimated:       totalEstimated,
		TotalActualSoFar:     totalActualSoFar,
		RemainingEstimated:  adjustedRemaining,
		RemainingOptimistic: remainingOptimistic,
		RemainingPessimistic: remainingPessimistic,
		ETA:                eta,
		ProgressPercent:    progressPercent,
		TasksCompleted:     completedCount,
		TasksRemaining:     remainingCount,
		TasksRunning:        runningCount,
		SlowdownFactor:     slowdownFactor,
		CriticalPathRemaining: criticalPathRemaining,
		ParallelismEfficiency: parallelismEfficiency,
	}
}

func (tp *TimePredictor) calculateRemainingTimeLocked(slowdownFactor float64) time.Duration {
	var remainingTime := time.Duration(0)
	runningTime := time.Duration(0)

	for taskID, task := range tp.dag.Tasks {
		if task.Status == dag.TaskStatusSuccess {
			continue
		}

		estimatedTime := task.EstimatedTime
		if estimatedTime == 0 {
			estimatedTime = 1 * time.Minute
		}

		adjustedTime := time.Duration(float64(estimatedTime) * slowdownFactor)

		if task.Status == dag.TaskStatusRunning || task.Status == dag.TaskStatusRetry {
			if startTime, ok := tp.taskStartTimes[taskID]; ok {
				elapsed := time.Since(startTime)
				remaining := adjustedTime - elapsed
				if remaining > 0 {
					runningTime += remaining
				}
			} else {
				runningTime += adjustedTime / 2
			}
		} else {
			remainingTime += adjustedTime
		}
	}

	effectiveParallelism := float64(tp.parallelism)
	if effectiveParallelism <= 0 {
		effectiveParallelism = 1
	}

	totalRemaining := remainingTime + runningTime
	return totalRemaining
}

func (tp *TimePredictor) calculateCriticalPathRemainingLocked(slowdownFactor float64) time.Duration {
	if tp.criticalPath == nil || len(tp.criticalPath.Path) == 0 {
		return time.Duration(0)
	}

	remainingDuration := time.Duration(0)

	for _, taskID := range tp.criticalPath.Path {
		task, ok := tp.dag.Tasks[taskID]
		if !ok {
			continue
		}

		if task.Status == dag.TaskStatusSuccess {
			continue
		}

		estimatedTime := task.EstimatedTime
		if estimatedTime == 0 {
			estimatedTime = 1 * time.Minute
		}

		adjustedTime := time.Duration(float64(estimatedTime) * slowdownFactor)

		if task.Status == dag.TaskStatusRunning || task.Status == dag.TaskStatusRetry {
			if startTime, ok := tp.taskStartTimes[taskID]; ok {
				elapsed := time.Since(startTime)
				remaining := adjustedTime - elapsed
				if remaining > 0 {
					remainingDuration += remaining
				}
			} else {
				remainingDuration += adjustedTime / 2
			}
		} else {
			remainingDuration += adjustedTime
		}
	}

	return remainingDuration
}

func (tp *TimePredictor) calculateParallelismEfficiencyLocked() float64 {
	if tp.maxParallelism <= 0 {
		return 1.0
	}

	actualParallelism := float64(tp.parallelism)
	if actualParallelism <= 0 {
		actualParallelism = 1
	}

	efficiency := actualParallelism / float64(tp.maxParallelism)
	if efficiency > 1.0 {
		efficiency = 1.0
	}

	return math.Max(0.3, efficiency)
}

func (tp *TimePredictor) GetTaskActualTime(taskID string) (*TaskActualTime, bool) {
	tp.mu.Lock()
	defer tp.mu.Unlock()

	at, ok := tp.actualTimes[taskID]
	if !ok {
		return nil, false
	}
	result := *at
	return &result, true
}

func (tp *TimePredictor) GetAllActualTimes() []*TaskActualTime {
	tp.mu.Lock()
	defer tp.mu.Unlock()

	result := make([]*TaskActualTime, len(tp.historicalData))
	for i, at := range tp.historicalData {
		copy := *at
		result[i] = &copy
	}
	return result
}

func (pr *PredictionResult) Print() {
	fmt.Println("\n=== Time Prediction ===")
	fmt.Printf("Progress: %.1f%% (%d/%d tasks completed)\n",
		pr.ProgressPercent, pr.TasksCompleted, pr.TasksCompleted+pr.TasksRemaining+pr.TasksRunning)
	fmt.Printf("Elapsed: %v\n", pr.TotalActualSoFar)
	fmt.Printf("Remaining: %v (estimated)\n", pr.RemainingEstimated)
	fmt.Printf("  Optimistic: %v\n", pr.RemainingOptimistic)
	fmt.Printf("  Pessimistic: %v\n", pr.RemainingPessimistic)
	fmt.Printf("ETA: %s\n", pr.ETA.Format("2006-01-02 15:04:05"))
	fmt.Printf("Slowdown Factor: %.2fx\n", pr.SlowdownFactor)
	fmt.Printf("Parallelism Efficiency: %.1f%%\n", pr.ParallelismEfficiency*100)
	fmt.Printf("Critical Path Remaining: %v\n", pr.CriticalPathRemaining)
	fmt.Printf("Running Tasks: %d | Pending Tasks: %d\n", pr.TasksRunning, pr.TasksRemaining)
	fmt.Println("=======================\n")
}

func (pr *PredictionResult) GetProgressBar(width int) string {
	filled := int(float64(width) * pr.ProgressPercent / 100.0)
	if filled > width {
		filled = width
	}

	bar := ""
	for i := 0; i < width; i++ {
		if i < filled {
			bar += "█"
		} else {
			bar += "░"
		}
	}
	return fmt.Sprintf("[%s] %.1f%%", bar, pr.ProgressPercent)
}

func (pr *PredictionResult) GetTimeRemaining() string {
	remaining := pr.RemainingEstimated

	if remaining < time.Minute {
		return fmt.Sprintf("%d seconds", int(remaining.Seconds()))
	} else if remaining < time.Hour {
		return fmt.Sprintf("%d minutes", int(remaining.Minutes()))
	} else {
		hours := int(remaining.Hours())
		minutes := int(remaining.Minutes()) % 60
		return fmt.Sprintf("%d hours %d minutes", hours, minutes)
	}
}

func (tp *TimePredictor) PrintTaskStats() {
	tp.mu.Lock()
	defer tp.mu.Unlock()

	if len(tp.historicalData) == 0 {
		fmt.Println("No task completion data available yet")
		return
	}

	fmt.Println("\n=== Task Time Statistics ===")
	fmt.Printf("%-25s %-15s %-15s %-15s %-15s\n",
		"Task ID", "Estimated", "Actual", "Difference", "Ratio")
	fmt.Println("--------------------------------------------------------------------------------")

	taskIDs := make([]string, 0, len(tp.actualTimes))
	for id := range tp.actualTimes {
		taskIDs = append(taskIDs, id)
	}
	sort.Strings(taskIDs)

	totalDiff := time.Duration(0)
	totalEst := time.Duration(0)
	totalAct := time.Duration(0)

	for _, id := range taskIDs {
		at := tp.actualTimes[id]
		diff := at.ActualTime - at.EstimatedTime
		ratio := float64(0.0)
		if at.EstimatedTime > 0 {
			ratio = float64(at.ActualTime) / float64(at.EstimatedTime)
		}

		diffStr := fmt.Sprintf("%+v", diff)

		fmt.Printf("%-25s %-15v %-15v %-15s %-15.2fx\n",
			id, at.EstimatedTime, at.ActualTime, diffStr, ratio)

		totalDiff += diff
		totalEst += at.EstimatedTime
		totalAct += at.ActualTime
	}

	fmt.Println("--------------------------------------------------------------------------------")

	overallRatio := float64(0.0)
	if totalEst > 0 {
		overallRatio = float64(totalAct) / float64(totalEst)
	}

	fmt.Printf("TOTAL                     %-15v %-15v %-15s %-15.2fx\n",
		totalEst, totalAct, fmt.Sprintf("%+v", totalDiff), overallRatio)
	fmt.Println("================================================================================\n")
}
