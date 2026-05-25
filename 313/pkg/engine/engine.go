package engine

import (
	"context"
	"fmt"
	"sync"
	"time"

	corev1 "k8s.io/api/core/v1"

	"ci-scheduler/pkg/autoscaler"
	"ci-scheduler/pkg/dag"
	"ci-scheduler/pkg/errors"
	"ci-scheduler/pkg/k8sclient"
	"ci-scheduler/pkg/monitor"
	"ci-scheduler/pkg/predictor"
	"ci-scheduler/pkg/scheduler"
	"ci-scheduler/pkg/warmup"
)

type ExecutionMode string

const (
	ModeLocal       ExecutionMode = "local"
	ModeKubernetes  ExecutionMode = "kubernetes"
)

type PipelineResult struct {
	PipelineID   string
	Success      bool
	TotalTime    time.Duration
	TotalTasks   int
	SuccessTasks int
	FailedTasks  int
	SkippedTasks int
	TaskResults  map[string]*TaskResult
}

type TaskResult struct {
	TaskID         string
	Status         dag.TaskStatus
	Executor       string
	StartTime      *time.Time
	EndTime        *time.Time
	Duration       time.Duration
	RetryCount     int
	ErrorMessage   string
	ErrorType      errors.ErrorType
	ErrorRetryable bool
	AlertSent      bool
}

type PipelineEngine struct {
	mode            ExecutionMode
	monitor         *monitor.ResourceMonitor
	scheduler       *scheduler.Scheduler
	k8sClient       *k8sclient.K8sClient
	errorClassifier *errors.ErrorClassifier
	warmupManager   *warmup.WarmupManager
	autoscaler      *autoscaler.Autoscaler
	timePredictor   *predictor.TimePredictor
	dag             *dag.DAG
	pipeline        *dag.Pipeline
	criticalPath    *dag.CriticalPathInfo
	scheduleInfo    map[string]*dag.TaskScheduleInfo
	taskPods        map[string]string
	podToTask       map[string]string
	taskResults     map[string]*TaskResult
	mu              sync.Mutex
	ctx             context.Context
	cancelFunc      context.CancelFunc
	taskChan        chan *dag.Task
	doneChan        chan struct{}
	useK8s          bool
	alertCallback   func(*errors.ErrorClassification, string)
	enableWarmup    bool
	enableAutoscaler bool
	enablePrediction bool
	taskEnqueueTimes map[string]time.Time
}

type EngineOptions struct {
	EnableWarmup     bool
	EnableAutoscaler bool
	EnablePrediction bool
	PreheatThreshold int
	MinExecutors     int
	MaxExecutors     int
	ScaleUpThreshold int
	ScaleDownThreshold int
	CooldownPeriod   time.Duration
}

func DefaultEngineOptions() *EngineOptions {
	return &EngineOptions{
		EnableWarmup:     true,
		EnableAutoscaler: true,
		EnablePrediction: true,
		PreheatThreshold: 2,
		MinExecutors:     2,
		MaxExecutors:     10,
		ScaleUpThreshold: 3,
		ScaleDownThreshold: 1,
		CooldownPeriod:   30 * time.Second,
	}
}

func NewPipelineEngine(
	mode ExecutionMode,
	monitor *monitor.ResourceMonitor,
	scheduler *scheduler.Scheduler,
	k8sClient *k8sclient.K8sClient,
	opts ...*EngineOptions,
) *PipelineEngine {
	var options *EngineOptions
	if len(opts) > 0 && opts[0] != nil {
		options = opts[0]
	} else {
		options = DefaultEngineOptions()
	}

	engine := &PipelineEngine{
		mode:            mode,
		monitor:         monitor,
		scheduler:       scheduler,
		k8sClient:       k8sClient,
		errorClassifier: errors.NewErrorClassifier(),
		taskPods:        make(map[string]string),
		podToTask:       make(map[string]string),
		taskResults:     make(map[string]*TaskResult),
		taskChan:        make(chan *dag.Task, 100),
		doneChan:        make(chan struct{}),
		useK8s:          mode == ModeKubernetes && k8sClient != nil,
		enableWarmup:    options.EnableWarmup,
		enableAutoscaler: options.EnableAutoscaler,
		enablePrediction: options.EnablePrediction,
		taskEnqueueTimes: make(map[string]time.Time),
	}

	if options.EnableWarmup {
		engine.warmupManager = warmup.NewWarmupManager(options.PreheatThreshold)
	}

	if options.EnableAutoscaler {
		scaleUpFunc := func() error {
			return engine.scheduler.AddExecutor()
		}
		scaleDownFunc := func() error {
			return engine.scheduler.RemoveExecutor()
		}
		engine.autoscaler = autoscaler.NewAutoscaler(
			options.MinExecutors,
			options.MaxExecutors,
			options.ScaleUpThreshold,
			options.ScaleDownThreshold,
			options.CooldownPeriod,
			scaleUpFunc,
			scaleDownFunc,
		)
	}

	return engine
}

func (e *PipelineEngine) SetAlertCallback(callback func(*errors.ErrorClassification, string)) {
	e.alertCallback = callback
}

func (e *PipelineEngine) LoadPipeline(pipelinePath string) error {
	pipeline, err := dag.ParsePipelineFromFile(pipelinePath)
	if err != nil {
		return fmt.Errorf("failed to parse pipeline: %w", err)
	}

	dagGraph, err := dag.BuildDAG(pipeline)
	if err != nil {
		return fmt.Errorf("failed to build DAG: %w", err)
	}

	criticalPath, scheduleInfo, err := dagGraph.CalculateCriticalPath()
	if err != nil {
		return fmt.Errorf("failed to calculate critical path: %w", err)
	}

	e.pipeline = pipeline
	e.dag = dagGraph
	e.criticalPath = criticalPath
	e.scheduleInfo = scheduleInfo

	e.scheduler.SetScheduleInfo(scheduleInfo)
	e.scheduler.SetCriticalPath(criticalPath.Path)

	if e.enablePrediction {
		e.timePredictor = predictor.NewTimePredictor(dagGraph, scheduleInfo, criticalPath, e.scheduler.GetExecutorCount())
	}

	for i := range pipeline.Tasks {
		task := &pipeline.Tasks[i]
		if task.Labels == nil {
			task.Labels = make(map[string]string)
		}
		task.Labels["pipeline"] = pipeline.ID
	}

	return nil
}

func (e *PipelineEngine) Run(ctx context.Context) (*PipelineResult, error) {
	e.ctx, e.cancelFunc = context.WithCancel(ctx)
	defer e.cancelFunc()

	fmt.Printf("\n=== Starting Pipeline: %s ===\n", e.pipeline.Name)
	fmt.Printf("Pipeline ID: %s\n", e.pipeline.ID)
	fmt.Printf("Total Tasks: %d\n", len(e.pipeline.Tasks))

	e.criticalPath.Print()
	dag.PrintScheduleInfo(e.scheduleInfo)

	maxParallel := e.dag.GetMaxParallelism()
	fmt.Printf("\nMaximum Parallelism: %d\n", maxParallel)

	startTime := time.Now()

	if e.enablePrediction && e.timePredictor != nil {
		e.timePredictor.SetPipelineStartTime(startTime)
	}

	var wg sync.WaitGroup

	wg.Add(1)
	go func() {
		defer wg.Done()
		e.schedulingLoop()
	}()

	wg.Add(1)
	go func() {
		defer wg.Done()
		e.taskExecutionLoop()
	}()

	if e.useK8s {
		wg.Add(1)
		go func() {
			defer wg.Done()
			e.watchK8sPods()
		}()
	}

	if e.enableAutoscaler || e.enablePrediction {
		wg.Add(1)
		go func() {
			defer wg.Done()
			e.monitorLoop()
		}()
	}

	<-e.doneChan
	e.cancelFunc()

	wg.Wait()

	totalTime := time.Since(startTime)

	if e.enablePrediction && e.timePredictor != nil {
		fmt.Println()
		e.timePredictor.PrintTaskStats()
	}

	return e.buildResult(totalTime), nil
}

func (e *PipelineEngine) monitorLoop() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	lastPredictionPrint := time.Time{}

	for {
		select {
		case <-e.ctx.Done():
			return
		case <-ticker.C:
			if e.enableAutoscaler && e.autoscaler != nil {
				e.checkAutoscaling()
			}

			if e.enablePrediction && e.timePredictor != nil {
				prediction := e.timePredictor.CalculateRemainingTime()
				if time.Since(lastPredictionPrint) >= 10*time.Second {
					fmt.Println()
					fmt.Println(prediction.GetProgressBar(50))
					fmt.Printf("Remaining: ~%s | ETA: %s\n",
						prediction.GetTimeRemaining(),
						prediction.ETA.Format("15:04:05"))
					fmt.Printf("Executors: %d | Running: %d | Pending: %d\n",
						e.scheduler.GetExecutorCount(),
						prediction.TasksRunning,
						prediction.TasksRemaining)
					lastPredictionPrint = time.Now()
				}
			}
		}
	}
}

func (e *PipelineEngine) checkAutoscaling() {
	if e.autoscaler == nil {
		return
	}

	executorCount := e.scheduler.GetExecutorCount()
	pendingCount := e.scheduler.GetPendingCount()
	runningCount := e.scheduler.GetRunningCount()

	var avgWaitTime time.Duration
	if pendingCount > 0 {
		e.mu.Lock()
		now := time.Now()
		totalWait := time.Duration(0)
		count := 0
		for taskID, enqueueTime := range e.taskEnqueueTimes {
			if task, ok := e.dag.Tasks[taskID]; ok && task.Status == dag.TaskStatusPending {
				totalWait += now.Sub(enqueueTime)
				count++
			}
		}
		e.mu.Unlock()
		if count > 0 {
			avgWaitTime = totalWait / time.Duration(count)
		}
	}

	direction, reason, err := e.autoscaler.CheckAndScale(executorCount, pendingCount, runningCount, avgWaitTime)
	if err != nil {
		fmt.Printf("[Autoscaler] Error: %v\n", err)
	} else if direction != autoscaler.ScaleNone {
		fmt.Printf("[Autoscaler] %s: %s (executors: %d, pending: %d, avg_wait: %v)\n",
			direction, reason, executorCount, pendingCount, avgWaitTime)

		if e.enablePrediction && e.timePredictor != nil {
			newCount := executorCount
			if direction == autoscaler.ScaleUp {
				newCount++
			} else if direction == autoscaler.ScaleDown {
				newCount--
			}
			e.timePredictor.UpdateParallelism(newCount)
		}
	}
}

func (e *PipelineEngine) schedulingLoop() {
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-e.ctx.Done():
			return
		case <-ticker.C:
			readyTasks := e.dag.GetReadyTasks()

			for _, task := range readyTasks {
				if task.Status == dag.TaskStatusPending || task.Status == dag.TaskStatusRetry {
					task.Status = dag.TaskStatusPending
					e.scheduler.AddTask(task)
					e.mu.Lock()
					e.taskEnqueueTimes[task.ID] = time.Now()
					e.mu.Unlock()
				}
			}

			for {
				task, executor, ok := e.scheduler.ScheduleNext()
				if !ok {
					break
				}

				select {
				case e.taskChan <- task:
					fmt.Printf("[Schedule] Task %s scheduled to executor %s\n", task.ID, executor)
				case <-e.ctx.Done():
					return
				}
			}

			if !e.dag.HasPendingTasks() && e.scheduler.GetRunningCount() == 0 && e.scheduler.GetPendingCount() == 0 {
				close(e.taskChan)
				close(e.doneChan)
				return
			}
		}
	}
}

func (e *PipelineEngine) taskExecutionLoop() {
	for task := range e.taskChan {
		go e.executeTask(task)
	}
}

func (e *PipelineEngine) executeTask(task *dag.Task) {
	fmt.Printf("[Execute] Starting task %s on %s\n", task.ID, task.ExecutorName)

	now := time.Now()
	task.StartTime = &now

	if e.enablePrediction && e.timePredictor != nil {
		e.timePredictor.RecordTaskStart(task.ID, now)
	}

	var err error
	var success bool
	var errorLogs string

	if e.useK8s {
		success, err, errorLogs = e.executeTaskOnK8s(task)
	} else {
		success, err, errorLogs = e.executeTaskLocal(task)
	}

	endTime := time.Now()
	task.EndTime = &endTime

	if e.enablePrediction && e.timePredictor != nil {
		e.timePredictor.RecordTaskComplete(task.ID, endTime)
	}

	e.mu.Lock()
	defer e.mu.Unlock()

	result := &TaskResult{
		TaskID:     task.ID,
		Status:     task.Status,
		Executor:   task.ExecutorName,
		StartTime:  task.StartTime,
		EndTime:    task.EndTime,
		RetryCount: task.RetryCount,
	}

	if task.StartTime != nil && task.EndTime != nil {
		result.Duration = task.EndTime.Sub(*task.StartTime)
	}

	if !success {
		errorMsg := ""
		if err != nil {
			errorMsg = err.Error()
		}
		if errorLogs != "" {
			if errorMsg != "" {
				errorMsg = errorMsg + "\n" + errorLogs
			} else {
				errorMsg = errorLogs
			}
		}
		result.ErrorMessage = errorMsg

		classification := e.errorClassifier.Classify(errorMsg)
		result.ErrorType = classification.Type
		result.ErrorRetryable = classification.Retryable

		if classification.ShouldAlert() && !result.AlertSent {
			e.sendAlert(classification, task, errorMsg)
			result.AlertSent = true
		}

		canRetry := classification.Retryable && task.RetryCount < task.MaxRetries

		if !classification.Retryable {
			fmt.Printf("[Alert] Task %s error type: %s (not retryable)\n",
				task.ID, classification.Type)
			fmt.Printf("  Description: %s\n", classification.Description)
			fmt.Printf("  Severity: %s\n", classification.Severity)
		}

		task, willRetry := e.scheduler.FailTask(task.ID, canRetry)

		if willRetry {
			fmt.Printf("[Retry] Task %s failed (%s), retrying (%d/%d)\n",
				task.ID, classification.Type, task.RetryCount, task.MaxRetries)
			result.Status = dag.TaskStatusRetry
			delay := task.RetryDelay * time.Second
			if task.RetryCount > 1 {
				delay = time.Duration(task.RetryCount) * task.RetryDelay * time.Second
			}
			go func() {
				time.Sleep(delay)
				e.mu.Lock()
				if node, ok := e.dag.Nodes[task.ID]; ok {
					node.Task.Status = dag.TaskStatusPending
				}
				e.mu.Unlock()
			}()
			e.taskResults[task.ID] = result
			return
		}

		fmt.Printf("[Failed] Task %s failed permanently after %d retries, error type: %s\n",
			task.ID, task.RetryCount, classification.Type)
		e.dag.MarkTaskFailed(task.ID, false)
		result.Status = dag.TaskStatusFailed
	} else {
		fmt.Printf("[Success] Task %s completed in %v\n", task.ID, result.Duration)
		e.scheduler.CompleteTask(task.ID)
		e.dag.MarkTaskComplete(task.ID)
		result.Status = dag.TaskStatusSuccess

		if e.enableWarmup && e.warmupManager != nil {
			go func(taskID string) {
				warmupTasks := e.warmupManager.CheckAndTriggerWarmup(e.ctx, e.dag, taskID, e.useK8s)
				if len(warmupTasks) > 0 {
					fmt.Printf("[Warmup] Triggered %d warmup tasks for dependents of %s\n",
						len(warmupTasks), taskID)
				}
			}(task.ID)
		}
	}

	e.taskResults[task.ID] = result
}

func (e *PipelineEngine) sendAlert(classification *errors.ErrorClassification, task *dag.Task, errorMsg string) {
	alertMsg := classification.GetAlertMessage()
	fmt.Printf("\n%s\n", alertMsg)
	fmt.Printf("  Task: %s (%s)\n", task.ID, task.Name)
	fmt.Printf("  Executor: %s\n", task.ExecutorName)
	if errorMsg != "" && len(errorMsg) > 200 {
		fmt.Printf("  Error snippet: %s...\n", errorMsg[:200])
	} else if errorMsg != "" {
		fmt.Printf("  Error: %s\n", errorMsg)
	}
	fmt.Println()

	if e.alertCallback != nil {
		go e.alertCallback(classification, task.ID)
	}
}

func (e *PipelineEngine) executeTaskLocal(task *dag.Task) (bool, error, string) {
	fmt.Printf("[Local] Simulating task: %s\n", task.ID)
	fmt.Printf("  Image: %s\n", task.Image)
	fmt.Printf("  Command: %v\n", task.Command)
	fmt.Printf("  Resources: CPU=%.2f, Memory=%dMi\n",
		task.Resources.CPU, task.Resources.Memory)

	simulatedDuration := task.EstimatedTime
	if simulatedDuration == 0 {
		simulatedDuration = 2 * time.Second
	}

	select {
	case <-time.After(simulatedDuration):
		return true, nil, ""
	case <-e.ctx.Done():
		return false, e.ctx.Err(), ""
	}
}

func (e *PipelineEngine) executeTaskOnK8s(task *dag.Task) (bool, error, string) {
	pod, err := e.k8sClient.CreatePod(e.ctx, task, task.ExecutorName)
	if err != nil {
		return false, fmt.Errorf("failed to create pod: %w", err), ""
	}

	e.mu.Lock()
	e.taskPods[task.ID] = pod.Name
	e.podToTask[pod.Name] = task.ID
	e.mu.Unlock()

	fmt.Printf("[K8s] Created pod %s for task %s\n", pod.Name, task.ID)

	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	timeout := time.After(1 * time.Hour)

	for {
		select {
		case <-e.ctx.Done():
			e.k8sClient.DeletePod(e.ctx, pod.Name)
			return false, e.ctx.Err(), ""
		case <-timeout:
			e.k8sClient.DeletePod(e.ctx, pod.Name)
			return false, fmt.Errorf("task timeout"), ""
		case <-ticker.C:
			status, err := e.k8sClient.GetPodStatus(e.ctx, pod.Name)
			if err != nil {
				fmt.Printf("[K8s] Failed to get pod status: %v\n", err)
				continue
			}

			if k8sclient.IsPodCompleted(status.Status) {
				endTime := time.Now()
				task.EndTime = &endTime

				logs, _ := e.k8sClient.GetPodLogs(e.ctx, pod.Name)
				if logs != "" {
					fmt.Printf("[K8s] Task %s logs:\n%s\n", task.ID, logs)
				}

				go e.k8sClient.DeletePod(e.ctx, pod.Name)

				return k8sclient.IsPodSuccessful(status.Status),
					fmt.Errorf("%s: %s", status.Reason, status.Message),
					logs
			}
		}
	}
}

func (e *PipelineEngine) watchK8sPods() {
	labelSelector := map[string]string{
		"app":      "ci-scheduler",
		"pipeline": e.pipeline.ID,
	}

	e.k8sClient.WatchPods(e.ctx, labelSelector, func(pod *corev1.Pod) {
		e.mu.Lock()
		defer e.mu.Unlock()

		taskID, ok := e.podToTask[pod.Name]
		if !ok {
			return
		}

		if k8sclient.IsPodCompleted(pod.Status.Phase) {
			fmt.Printf("[K8s Watch] Pod %s (task %s) phase: %s\n",
				pod.Name, taskID, pod.Status.Phase)
		}
	})
}

func (e *PipelineEngine) buildResult(totalTime time.Duration) *PipelineResult {
	result := &PipelineResult{
		PipelineID:  e.pipeline.ID,
		TotalTime:   totalTime,
		TotalTasks:  len(e.pipeline.Tasks),
		TaskResults: make(map[string]*TaskResult),
	}

	for _, task := range e.pipeline.Tasks {
		taskResult, ok := e.taskResults[task.ID]
		if !ok {
			taskResult = &TaskResult{
				TaskID: task.ID,
				Status: task.Status,
			}
		}

		result.TaskResults[task.ID] = taskResult

		switch taskResult.Status {
		case dag.TaskStatusSuccess:
			result.SuccessTasks++
		case dag.TaskStatusFailed:
			result.FailedTasks++
		case dag.TaskStatusSkipped:
			result.SkippedTasks++
		}
	}

	result.Success = result.FailedTasks == 0

	return result
}

func (r *PipelineResult) Print() {
	fmt.Println("\n=== Pipeline Execution Result ===")
	fmt.Printf("Pipeline ID: %s\n", r.PipelineID)
	fmt.Printf("Status: ")
	if r.Success {
		fmt.Println("SUCCESS")
	} else {
		fmt.Println("FAILED")
	}
	fmt.Printf("Total Time: %v\n", r.TotalTime)
	fmt.Printf("Total Tasks: %d\n", r.TotalTasks)
	fmt.Printf("  Success: %d\n", r.SuccessTasks)
	fmt.Printf("  Failed: %d\n", r.FailedTasks)
	fmt.Printf("  Skipped: %d\n", r.SkippedTasks)
	fmt.Println()

	fmt.Println("=== Task Details ===")
	fmt.Printf("%-20s %-12s %-15s %-12s %-8s %-18s %s\n",
		"Task ID", "Status", "Executor", "Duration", "Retries", "Error Type", "Error")
	fmt.Println("----------------------------------------------------------------------------------------------------")

	for taskID, tr := range r.TaskResults {
		errorType := string(tr.ErrorType)
		if errorType == "" {
			errorType = "-"
		}
		errorMsg := tr.ErrorMessage
		if len(errorMsg) > 50 {
			errorMsg = errorMsg[:50] + "..."
		}
		fmt.Printf("%-20s %-12s %-15s %-12v %-8d %-18s %s\n",
			taskID, tr.Status, tr.Executor, tr.Duration, tr.RetryCount, errorType, errorMsg)
	}
	fmt.Println("====================================================================================================")

	compileErrors := 0
	testFailures := 0
	networkErrors := 0
	infraErrors := 0

	for _, tr := range r.TaskResults {
		switch tr.ErrorType {
		case "compile_error":
			compileErrors++
		case "test_failed":
			testFailures++
		case "network_error":
			networkErrors++
		case "infrastructure_error":
			infraErrors++
		}
	}

	if compileErrors+testFailures+networkErrors+infraErrors > 0 {
		fmt.Println("\n=== Error Summary ===")
		if compileErrors > 0 {
			fmt.Printf("  Compile Errors: %d (not retryable)\n", compileErrors)
		}
		if testFailures > 0 {
			fmt.Printf("  Test Failures: %d (not retryable)\n", testFailures)
		}
		if networkErrors > 0 {
			fmt.Printf("  Network Errors: %d (retryable)\n", networkErrors)
		}
		if infraErrors > 0 {
			fmt.Printf("  Infrastructure Errors: %d (retryable)\n", infraErrors)
		}
		fmt.Println()
	}
}

func (e *PipelineEngine) PrintStatus() {
	e.scheduler.PrintStatus()
	e.monitor.PrintStatus()
}
