package monitor

import (
	"fmt"
	"sync"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/mem"
)

type SystemResources struct {
	CPUPercent     float64
	MemoryTotal     uint64
	MemoryUsed    uint64
	MemoryPercent float64
	DiskTotal     uint64
	DiskUsed      uint64
	DiskPercent   float64
	Timestamp   time.Time
}

type ExecutorResources struct {
	ExecutorName        string
	CPUPercent          float64
	MemoryPercent        float64
	AllocatedCPU        float64
	AllocatedMemory     int64
	TotalCPU            float64
	TotalMemory         int64
	RunningTasks        int
	Timestamp           time.Time
	HistoryCPU          []float64
	HistoryMemory       []float64
	WeightedAvgCPU      float64
	WeightedAvgMemory   float64
	MaxHistorySize      int
}

type ResourceMonitor struct {
	mu              sync.RWMutex
	systemResources  SystemResources
	executorResources map[string]*ExecutorResources
	history           []SystemResources
	maxHistorySize   int
	stopCh            chan struct{}
	interval          time.Duration
	running           bool
}

func NewResourceMonitor(interval time.Duration, maxHistorySize int) *ResourceMonitor {
	if interval == 0 {
		interval = 5 * time.Second
	}
	if maxHistorySize == 0 {
		maxHistorySize = 100
	}
	return &ResourceMonitor{
		executorResources: make(map[string]*ExecutorResources),
		history:           make([]SystemResources, 0, maxHistorySize),
		maxHistorySize:    maxHistorySize,
		interval:          interval,
		stopCh:            make(chan struct{}),
	}
}

func (rm *ResourceMonitor) Start() {
	rm.mu.Lock()
	if rm.running {
		rm.mu.Unlock()
		return
	}
	rm.running = true
	rm.mu.Unlock()

	go rm.monitorLoop()
}

func (rm *ResourceMonitor) Stop() {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	if !rm.running {
		return
	}
	close(rm.stopCh)
	rm.running = false
}

func (rm *ResourceMonitor) monitorLoop() {
	ticker := time.NewTicker(rm.interval)
	defer ticker.Stop()

	rm.collectSystemResources()

	for {
		select {
		case <-rm.stopCh:
			return
		case <-ticker.C:
			rm.collectSystemResources()
		}
	}
}

func (rm *ResourceMonitor) collectSystemResources() {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	cpuPercent, err := cpu.Percent(time.Second, false)
	if err != nil {
		cpuPercent = []float64{0}
	}

	memInfo, err := mem.VirtualMemory()
	if err != nil {
		memInfo = &mem.VirtualMemoryInfo{Total: 0, Used: 0, UsedPercent: 0}
	}

	diskInfo, err := disk.Usage("/")
	if err != nil {
		diskInfo = &disk.UsageStat{Total: 0, Used: 0, UsedPercent: 0}
	}

	sr := SystemResources{
		CPUPercent:     cpuPercent[0],
		MemoryTotal:     memInfo.Total,
		MemoryUsed:      memInfo.Used,
		MemoryPercent:   memInfo.UsedPercent,
		DiskTotal:       diskInfo.Total,
		DiskUsed:        diskInfo.Used,
		DiskPercent:     diskInfo.UsedPercent,
		Timestamp:       time.Now(),
	}

	rm.systemResources = sr
	rm.history = append(rm.history, sr)
	if len(rm.history) > rm.maxHistorySize {
		rm.history = rm.history[1:]
	}
}

func (rm *ResourceMonitor) GetSystemResources() SystemResources {
	rm.mu.RLock()
	defer rm.mu.RUnlock()
	return rm.systemResources
}

func (rm *ResourceMonitor) GetHistory() []SystemResources {
	rm.mu.RLock()
	defer rm.mu.RUnlock()
	history := make([]SystemResources, len(rm.history))
	copy(history, rm.history)
	return history
}

func (rm *ResourceMonitor) RegisterExecutor(name string, totalCPU float64, totalMemory int64) {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	maxHistory := 20
	rm.executorResources[name] = &ExecutorResources{
		ExecutorName:    name,
		TotalCPU:        totalCPU,
		TotalMemory:     totalMemory,
		Timestamp:       time.Now(),
		HistoryCPU:      make([]float64, 0, maxHistory),
		HistoryMemory:   make([]float64, 0, maxHistory),
		MaxHistorySize:  maxHistory,
	}
}

func (rm *ResourceMonitor) UpdateExecutorResources(name string, cpuPercent, memPercent float64) {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	if er, exists := rm.executorResources[name]; exists {
		er.CPUPercent = cpuPercent
		er.MemoryPercent = memPercent
		er.Timestamp = time.Now()

		er.HistoryCPU = append(er.HistoryCPU, cpuPercent)
		er.HistoryMemory = append(er.HistoryMemory, memPercent)

		if len(er.HistoryCPU) > er.MaxHistorySize {
			er.HistoryCPU = er.HistoryCPU[1:]
		}
		if len(er.HistoryMemory) > er.MaxHistorySize {
			er.HistoryMemory = er.HistoryMemory[1:]
		}

		er.WeightedAvgCPU = calculateWeightedAverage(er.HistoryCPU)
		er.WeightedAvgMemory = calculateWeightedAverage(er.HistoryMemory)
	}
}

func calculateWeightedAverage(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	n := len(values)
	var totalWeight float64
	var weightedSum float64

	for i, v := range values {
		weight := float64(i+1) / float64(n*(n+1)/2)
		weightedSum += v * weight
		totalWeight += weight
	}

	if totalWeight == 0 {
		return 0
	}
	return weightedSum / totalWeight
}

func (rm *ResourceMonitor) AllocateResources(name string, cpu float64, memory int64) error {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	er, exists := rm.executorResources[name]
	if !exists {
		return fmt.Errorf("executor %s not found", name)
	}

	availableCPU := er.TotalCPU - er.AllocatedCPU
	availableMemory := er.TotalMemory - er.AllocatedMemory

	if cpu > availableCPU {
		return fmt.Errorf("insufficient CPU: requested %.2f, available %.2f", cpu, availableCPU)
	}

	if memory > availableMemory {
		return fmt.Errorf("insufficient memory: requested %d, available %d", memory, availableMemory)
	}

	er.AllocatedCPU += cpu
	er.AllocatedMemory += memory
	er.RunningTasks++
	return nil
}

func (rm *ResourceMonitor) ReleaseResources(name string, cpu float64, memory int64) {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	if er, exists := rm.executorResources[name]; exists {
		er.AllocatedCPU -= cpu
		er.AllocatedMemory -= memory
		if er.AllocatedCPU < 0 {
			er.AllocatedCPU = 0
		}
		if er.AllocatedMemory < 0 {
			er.AllocatedMemory = 0
		}
		er.RunningTasks--
		if er.RunningTasks < 0 {
			er.RunningTasks = 0
		}
	}
}

func (rm *ResourceMonitor) GetExecutorResources(name string) (*ExecutorResources, error) {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	er, exists := rm.executorResources[name]
	if !exists {
		return nil, fmt.Errorf("executor %s not found", name)
	}

	result := *er
	return &result, nil
}

func (rm *ResourceMonitor) GetAllExecutors() map[string]ExecutorResources {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	result := make(map[string]ExecutorResources)
	for name, er := range rm.executorResources {
		result[name] = *er
	}
	return result
}

func (rm *ResourceMonitor) CanFitResources(name string, cpu float64, memory int64) bool {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	er, exists := rm.executorResources[name]
	if !exists {
		return false
	}

	availableCPU := er.TotalCPU - er.AllocatedCPU
	availableMemory := er.TotalMemory - er.AllocatedMemory

	return cpu <= availableCPU && memory <= availableMemory
}

func (rm *ResourceMonitor) FindBestFit(cpu float64, memory int64) (string, bool) {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	var bestExecutor string
	bestScore := -1.0

	historyWeight := 0.3
	currentWeight := 0.7

	for name, er := range rm.executorResources {
		availableCPU := er.TotalCPU - er.AllocatedCPU
		availableMemory := er.TotalMemory - er.AllocatedMemory

		if cpu <= availableCPU && memory <= availableMemory {
			currentCPUUtil := (er.AllocatedCPU + cpu) / er.TotalCPU
			currentMemUtil := float64(er.AllocatedMemory+memory) / float64(er.TotalMemory)

			historicalCPUUtil := er.WeightedAvgCPU / 100.0
			historicalMemUtil := er.WeightedAvgMemory / 100.0

			combinedCPU := currentWeight*currentCPUUtil + historyWeight*historicalCPUUtil
			combinedMem := currentWeight*currentMemUtil + historyWeight*historicalMemUtil

			taskCountPenalty := float64(er.RunningTasks) * 0.05

			score := combinedCPU + combinedMem + taskCountPenalty

			if bestScore < 0 || score < bestScore {
				bestScore = score
				bestExecutor = name
			}
		}
	}

	return bestExecutor, bestScore >= 0
}

func (rm *ResourceMonitor) GetAverageCPUUsage() float64 {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	if len(rm.history) == 0 {
		return 0
	}

	var total float64
	for _, h := range rm.history {
		total += h.CPUPercent
	}
	return total / float64(len(rm.history))
}

func (rm *ResourceMonitor) GetAverageMemoryUsage() float64 {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	if len(rm.history) == 0 {
		return 0
	}

	var total float64
	for _, h := range rm.history {
		total += h.MemoryPercent
	}
	return total / float64(len(rm.history))
}

func (rm *ResourceMonitor) GetWeightedAvgCPU(executorName string) (float64, error) {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	er, exists := rm.executorResources[executorName]
	if !exists {
		return 0, fmt.Errorf("executor %s not found", executorName)
	}
	return er.WeightedAvgCPU, nil
}

func (rm *ResourceMonitor) GetWeightedAvgMemory(executorName string) (float64, error) {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	er, exists := rm.executorResources[executorName]
	if !exists {
		return 0, fmt.Errorf("executor %s not found", executorName)
	}
	return er.WeightedAvgMemory, nil
}

func (rm *ResourceMonitor) GetAllWeightedAverages() map[string]struct{ CPU, Memory float64 } {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	result := make(map[string]struct{ CPU, Memory float64 })
	for name, er := range rm.executorResources {
		result[name] = struct{ CPU, Memory float64 }{
			CPU:    er.WeightedAvgCPU,
			Memory: er.WeightedAvgMemory,
		}
	}
	return result
}

func (rm *ResourceMonitor) PrintStatus() {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	fmt.Println("\n=== System Resource Status ===")
	fmt.Printf("CPU Usage:    %.2f%%\n", rm.systemResources.CPUPercent)
	fmt.Printf("Memory Usage: %.2f%% (%d / %d GB)\n",
		rm.systemResources.MemoryPercent,
		rm.systemResources.MemoryUsed/1024/1024/1024,
		rm.systemResources.MemoryTotal/1024/1024/1024)
	fmt.Printf("Disk Usage:   %.2f%% (%d / %d GB)\n",
		rm.systemResources.DiskPercent,
		rm.systemResources.DiskUsed/1024/1024/1024,
		rm.systemResources.DiskTotal/1024/1024/1024)
	fmt.Println()

	if len(rm.executorResources) > 0 {
		fmt.Println("=== Executor Resource Status ===")
		fmt.Printf("%-20s %-12s %-12s %-12s %-12s %-12s\n",
			"Executor", "CPU Used", "Memory Used", "CPU Alloc", "Mem Alloc", "Tasks")
		fmt.Println("------------------------------------------------------------------------")
		for name, er := range rm.executorResources {
			fmt.Printf("%-20s %-12.2f %-12.2f %-12.2f %-12d %-12d\n",
				name,
				er.CPUPercent,
				er.MemoryPercent,
				er.AllocatedCPU,
				er.AllocatedMemory,
				er.RunningTasks)
		}
		fmt.Println("========================================================================")
	}
}
