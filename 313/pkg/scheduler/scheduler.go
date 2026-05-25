package scheduler

import (
	"container/heap"
	"fmt"
	"sort"
	"sync"
	"time"

	"ci-scheduler/pkg/dag"
	"ci-scheduler/pkg/monitor"
)

type SchedulingStrategy string

const (
	StrategyCriticalPathFirst SchedulingStrategy = "critical_path_first"
	StrategyPriorityFirst     SchedulingStrategy = "priority_first"
	StrategyResourceAware     SchedulingStrategy = "resource_aware"
	StrategyBalanced          SchedulingStrategy = "balanced"
)

type Executor struct {
	Name        string
	TotalCPU    float64
	TotalMemory int64
	RunningTasks int
}

type TaskQueueItem struct {
	Task     *dag.Task
	Priority float64
	Index     int
}

type TaskPriorityQueue []*TaskQueueItem

type Scheduler struct {
	mu                 sync.Mutex
	executors          map[string]*Executor
	monitor            *monitor.ResourceMonitor
	strategy           SchedulingStrategy
	priorityQueue      TaskPriorityQueue
	scheduleInfo       map[string]*dag.TaskScheduleInfo
	criticalPath       map[string]bool
	taskToExecutor     map[string]string
	executorToTasks    map[string][]*dag.Task
	executorCounter    int
}

func NewScheduler(monitor *monitor.ResourceMonitor, strategy SchedulingStrategy) *Scheduler {
	if strategy == "" {
		strategy = StrategyBalanced
	}

	s := &Scheduler{
		executors:       make(map[string]*Executor),
		monitor:         monitor,
		strategy:        strategy,
		priorityQueue:   make(TaskPriorityQueue, 0),
		scheduleInfo:    make(map[string]*dag.TaskScheduleInfo),
		criticalPath:    make(map[string]bool),
		taskToExecutor:  make(map[string]string),
		executorToTasks: make(map[string][]*dag.Task),
		executorCounter: 100,
	}

	heap.Init(&s.priorityQueue)
	return s
}

func (s *Scheduler) AddExecutor(name string, totalCPU float64, totalMemory int64) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.executors[name] = &Executor{
		Name:        name,
		TotalCPU:    totalCPU,
		TotalMemory: totalMemory,
	}
	s.monitor.RegisterExecutor(name, totalCPU, totalMemory)
}

func (s *Scheduler) RemoveExecutor(name string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if exec, ok := s.executors[name]; ok {
		if exec.RunningTasks > 0 {
			return
		}
	}
	delete(s.executors, name)
}

func (s *Scheduler) GetExecutorCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.executors)
}

func (s *Scheduler) AddExecutor() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.executorCounter++
	name := fmt.Sprintf("auto-exec-%d", s.executorCounter)
	cpu := 4.0
	mem := int64(8192)

	s.executors[name] = &Executor{
		Name:        name,
		TotalCPU:    cpu,
		TotalMemory: mem,
	}
	s.monitor.RegisterExecutor(name, cpu, mem)
	return nil
}

func (s *Scheduler) RemoveExecutor() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	for name, exec := range s.executors {
		if exec.RunningTasks == 0 {
			delete(s.executors, name)
			return nil
		}
	}

	for name := range s.executors {
		if len(s.executors) > 1 {
			delete(s.executors, name)
			return nil
		}
	}

	return fmt.Errorf("no executor available to remove")
}

func (s *Scheduler) SetScheduleInfo(info map[string]*dag.TaskScheduleInfo) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.scheduleInfo = info
}

func (s *Scheduler) SetCriticalPath(criticalPath []string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.criticalPath = make(map[string]bool)
	for _, taskID := range criticalPath {
		s.criticalPath[taskID] = true
	}
}

func (s *Scheduler) AddTask(task *dag.Task) {
	s.mu.Lock()
	defer s.mu.Unlock()

	priority := s.calculateTaskPriority(task)
	item := &TaskQueueItem{
		Task:     task,
		Priority: priority,
	}
	heap.Push(&s.priorityQueue, item)
}

func (s *Scheduler) calculateTaskPriority(task *dag.Task) float64 {
	basePriority := float64(task.Priority)
	isCritical := s.criticalPath[task.ID]

	switch s.strategy {
	case StrategyCriticalPathFirst:
		if isCritical {
			return basePriority + 1000
		}
		return basePriority

	case StrategyPriorityFirst:
		return basePriority

	case StrategyResourceAware:
		resourceScore := task.Resources.CPU*10 + float64(task.Resources.Memory)/1024
		return basePriority - resourceScore

	case StrategyBalanced:
		criticalBonus := 0.0
		if isCritical {
			criticalBonus = 500
		}
		resourceScore := task.Resources.CPU*5 + float64(task.Resources.Memory)/2048
		slackBonus := 0.0
		if info, ok := s.scheduleInfo[task.ID]; ok {
			slackBonus = 100.0 / (info.Slack.Seconds() + 1)
		}
		return basePriority + criticalBonus + slackBonus - resourceScore

	default:
		return basePriority
	}
}

func (s *Scheduler) ScheduleNext() (*dag.Task, string, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.priorityQueue.Len() == 0 {
		return nil, "", false
	}

	tempQueue := make(TaskPriorityQueue, 0)
	heap.Init(&tempQueue)

	for s.priorityQueue.Len() > 0 {
		item := heap.Pop(&s.priorityQueue).(*TaskQueueItem)

		executorName, found := s.findSuitableExecutor(item.Task)
		if found {
			for tempQueue.Len() > 0 {
				heap.Push(&s.priorityQueue, heap.Pop(&tempQueue))
			}

			err := s.monitor.AllocateResources(executorName, item.Task.Resources.CPU, item.Task.Resources.Memory)
			if err != nil {
				continue
			}

			item.Task.Status = dag.TaskStatusRunning
			now := time.Now()
			item.Task.StartTime = &now
			item.Task.ExecutorName = executorName

			s.taskToExecutor[item.Task.ID] = executorName
			s.executorToTasks[executorName] = append(s.executorToTasks[executorName], item.Task)
			s.executors[executorName].RunningTasks++

			return item.Task, executorName, true
		}

		heap.Push(&tempQueue, item)
	}

	for tempQueue.Len() > 0 {
		heap.Push(&s.priorityQueue, heap.Pop(&tempQueue))
	}

	return nil, "", false
}

func (s *Scheduler) findSuitableExecutor(task *dag.Task) (string, bool) {
	bestFit, found := s.monitor.FindBestFit(task.Resources.CPU, task.Resources.Memory)
	if found {
		return bestFit, true
	}

	candidates := make([]string, 0)
	for name, exec := range s.executors {
		if s.monitor.CanFitResources(name, task.Resources.CPU, task.Resources.Memory) {
			candidates = append(candidates, name)
		}
	}

	if len(candidates) == 0 {
		return "", false
	}

	historyWeight := 0.3
	currentWeight := 0.7

	sort.Slice(candidates, func(i, j int) bool {
		ei := s.executors[candidates[i]]
		ej := s.executors[candidates[j]]

		ri, _ := s.monitor.GetExecutorResources(candidates[i])
		rj, _ := s.monitor.GetExecutorResources(candidates[j])

		histCPUI, _ := s.monitor.GetWeightedAvgCPU(candidates[i])
		histMemI, _ := s.monitor.GetWeightedAvgMemory(candidates[i])
		histCPUJ, _ := s.monitor.GetWeightedAvgCPU(candidates[j])
		histMemJ, _ := s.monitor.GetWeightedAvgMemory(candidates[j])

		currentCPUI := (ri.AllocatedCPU + task.Resources.CPU) / ei.TotalCPU
		currentMemI := float64(ri.AllocatedMemory+task.Resources.Memory) / float64(ei.TotalMemory)
		combinedCPUI := currentWeight*currentCPUI + historyWeight*(histCPUI/100.0)
		combinedMemI := currentWeight*currentMemI + historyWeight*(histMemI/100.0)
		scoreI := combinedCPUI + combinedMemI + float64(ri.RunningTasks)*0.05

		currentCPUJ := (rj.AllocatedCPU + task.Resources.CPU) / ej.TotalCPU
		currentMemJ := float64(rj.AllocatedMemory+task.Resources.Memory) / float64(ej.TotalMemory)
		combinedCPUJ := currentWeight*currentCPUJ + historyWeight*(histCPUJ/100.0)
		combinedMemJ := currentWeight*currentMemJ + historyWeight*(histMemJ/100.0)
		scoreJ := combinedCPUJ + combinedMemJ + float64(rj.RunningTasks)*0.05

		return scoreI < scoreJ
	})

	return candidates[0], true
}

func (s *Scheduler) CompleteTask(taskID string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	executorName, ok := s.taskToExecutor[taskID]
	if !ok {
		return fmt.Errorf("task %s not found in scheduler", taskID)
	}

	task := s.findTask(taskID)
	if task != nil {
		s.monitor.ReleaseResources(executorName, task.Resources.CPU, task.Resources.Memory)
		task.Status = dag.TaskStatusSuccess
		now := time.Now()
		task.EndTime = &now
	}

	if exec, ok := s.executors[executorName]; ok {
		exec.RunningTasks--
		if exec.RunningTasks < 0 {
			exec.RunningTasks = 0
		}
	}

	delete(s.taskToExecutor, taskID)
	s.removeTaskFromExecutor(executorName, taskID)

	return nil
}

func (s *Scheduler) FailTask(taskID string, canRetry bool) (*dag.Task, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()

	executorName, ok := s.taskToExecutor[taskID]
	if !ok {
		return nil, false
	}

	task := s.findTask(taskID)
	if task != nil {
		s.monitor.ReleaseResources(executorName, task.Resources.CPU, task.Resources.Memory)

		if canRetry && task.RetryCount < task.MaxRetries {
			task.Status = dag.TaskStatusRetry
			task.RetryCount++
			item := &TaskQueueItem{
				Task:     task,
				Priority: s.calculateTaskPriority(task),
			}
			heap.Push(&s.priorityQueue, item)
		} else {
			task.Status = dag.TaskStatusFailed
			now := time.Now()
			task.EndTime = &now
		}
	}

	if exec, ok := s.executors[executorName]; ok {
		exec.RunningTasks--
		if exec.RunningTasks < 0 {
			exec.RunningTasks = 0
		}
	}

	delete(s.taskToExecutor, taskID)
	s.removeTaskFromExecutor(executorName, taskID)

	return task, canRetry && task != nil && task.RetryCount < task.MaxRetries
}

func (s *Scheduler) findTask(taskID string) *dag.Task {
	for _, tasks := range s.executorToTasks {
		for _, t := range tasks {
			if t.ID == taskID {
				return t
			}
		}
	}
	return nil
}

func (s *Scheduler) removeTaskFromExecutor(executorName, taskID string) {
	tasks := s.executorToTasks[executorName]
	for i, t := range tasks {
		if t.ID == taskID {
			s.executorToTasks[executorName] = append(tasks[:i], tasks[i+1:]...)
			break
		}
	}
}

func (s *Scheduler) GetPendingCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.priorityQueue.Len()
}

func (s *Scheduler) GetRunningCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	count := 0
	for _, exec := range s.executors {
		count += exec.RunningTasks
	}
	return count
}

func (s *Scheduler) GetExecutorLoad() map[string]float64 {
	s.mu.Lock()
	defer s.mu.Unlock()

	load := make(map[string]float64)
	for name, exec := range s.executors {
		cpuLoad := 0.0
		memLoad := 0.0
		if exec.TotalCPU > 0 {
			cpuLoad = float64(exec.RunningTasks) / float64(len(s.executors))
		}
		load[name] = cpuLoad + memLoad
	}
	return load
}

func (s *Scheduler) HasPendingTasks() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.priorityQueue.Len() > 0
}

func (s *Scheduler) PrintStatus() {
	s.mu.Lock()
	defer s.mu.Unlock()

	fmt.Println("\n=== Scheduler Status ===")
	fmt.Printf("Strategy: %s\n", s.strategy)
	fmt.Printf("Pending Tasks: %d\n", s.priorityQueue.Len())
	fmt.Println()

	if len(s.executors) > 0 {
		fmt.Println("=== Executor Status ===")
		fmt.Printf("%-20s %-12s %-12s %-12s\n", "Executor", "CPU Total", "Mem Total", "Running Tasks")
		fmt.Println("------------------------------------------------------------")
		for name, exec := range s.executors {
			fmt.Printf("%-20s %-12.2f %-12d %-12d\n",
				name, exec.TotalCPU, exec.TotalMemory, exec.RunningTasks)
		}
		fmt.Println("============================================================")
	}

	if s.priorityQueue.Len() > 0 {
		fmt.Println("\n=== Pending Task Queue ===")
		fmt.Printf("%-20s %-12s %-12s %-12s\n", "Task ID", "Priority", "CPU", "Memory")
		fmt.Println("------------------------------------------------------------")

		tempQueue := make(TaskPriorityQueue, 0)
		heap.Init(&tempQueue)
		for s.priorityQueue.Len() > 0 {
			item := heap.Pop(&s.priorityQueue).(*TaskQueueItem)
			fmt.Printf("%-20s %-12.2f %-12.2f %-12d\n",
				item.Task.ID, item.Priority, item.Task.Resources.CPU, item.Task.Resources.Memory)
			heap.Push(&tempQueue, item)
		}
		for tempQueue.Len() > 0 {
			heap.Push(&s.priorityQueue, heap.Pop(&tempQueue))
		}
		fmt.Println("============================================================")
	}
}

func (pq TaskPriorityQueue) Len() int { return len(pq) }

func (pq TaskPriorityQueue) Less(i, j int) bool {
	return pq[i].Priority > pq[j].Priority
}

func (pq TaskPriorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
	pq[i].Index = i
	pq[j].Index = j
}

func (pq *TaskPriorityQueue) Push(x interface{}) {
	n := len(*pq)
	item := x.(*TaskQueueItem)
	item.Index = n
	*pq = append(*pq, item)
}

func (pq *TaskPriorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	old[n-1] = nil
	item.Index = -1
	*pq = old[0 : n-1]
	return item
}
