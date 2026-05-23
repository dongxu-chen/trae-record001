package collector

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"

	"github.com/shirou/gopsutil/v3/process"
)

type ProcInfo struct {
	PID      int
	Name     string
	UTime    uint64
	STime    uint64
	CUTime   uint64
	CSTime   uint64
	StartTime uint64
	RSS      uint64
	VSize    uint64
}

type ProcStats struct {
	mu          sync.RWMutex
	lastStats   map[int]*ProcInfo
	lastCPUTime uint64
}

var procStats = &ProcStats{
	lastStats: make(map[int]*ProcInfo),
}

func getClockTicks() int64 {
	return 100
}

func readProcStat(pid int) (*ProcInfo, error) {
	path := fmt.Sprintf("/proc/%d/stat", pid)
	content, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	fields := strings.Fields(string(content))
	if len(fields) < 24 {
		return nil, fmt.Errorf("invalid stat format for pid %d", pid)
	}

	name := strings.Trim(fields[1], "()")
	utime, _ := strconv.ParseUint(fields[13], 10, 64)
	stime, _ := strconv.ParseUint(fields[14], 10, 64)
	cutime, _ := strconv.ParseUint(fields[15], 10, 64)
	cstime, _ := strconv.ParseUint(fields[16], 10, 64)
	startTime, _ := strconv.ParseUint(fields[21], 10, 64)
	vsize, _ := strconv.ParseUint(fields[22], 10, 64)
	rss, _ := strconv.ParseUint(fields[23], 10, 64)

	return &ProcInfo{
		PID:       pid,
		Name:      name,
		UTime:     utime,
		STime:     stime,
		CUTime:    cutime,
		CSTime:    cstime,
		StartTime: startTime,
		VSize:     vsize,
		RSS:       rss * uint64(os.Getpagesize()),
	}, nil
}

func readTotalCPUTime() (uint64, error) {
	file, err := os.Open("/proc/stat")
	if err != nil {
		return 0, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	if scanner.Scan() {
		fields := strings.Fields(scanner.Text())
		if len(fields) < 8 {
			return 0, fmt.Errorf("invalid /proc/stat format")
		}
		var total uint64
		for i := 1; i < len(fields); i++ {
			val, _ := strconv.ParseUint(fields[i], 10, 64)
			total += val
		}
		return total, nil
	}
	return 0, scanner.Err()
}

func getMemTotal() (uint64, error) {
	file, err := os.Open("/proc/meminfo")
	if err != nil {
		return 0, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "MemTotal:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				kb, _ := strconv.ParseUint(fields[1], 10, 64)
				return kb * 1024, nil
			}
		}
	}
	return 0, fmt.Errorf("MemTotal not found")
}

func listProcesses() ([]int, error) {
	matches, err := filepath.Glob("/proc/[0-9]*")
	if err != nil {
		return nil, err
	}

	pids := make([]int, 0, len(matches))
	for _, match := range matches {
		pidStr := filepath.Base(match)
		pid, err := strconv.Atoi(pidStr)
		if err == nil {
			pids = append(pids, pid)
		}
	}
	return pids, nil
}

func collectTopProcessesProc(topN int) ([]ProcessMetric, error) {
	if runtime.GOOS != "linux" {
		return collectTopProcessesFallback(topN)
	}

	pids, err := listProcesses()
	if err != nil {
		return nil, err
	}

	memTotal, err := getMemTotal()
	if err != nil {
		return nil, err
	}

	currentStats := make(map[int]*ProcInfo)
	currentCPUTime, err := readTotalCPUTime()
	if err != nil {
		return nil, err
	}

	for _, pid := range pids {
		info, err := readProcStat(pid)
		if err != nil {
			continue
		}
		currentStats[pid] = info
	}

	procStats.mu.Lock()
	lastStats := procStats.lastStats
	lastCPUTime := procStats.lastCPUTime
	procStats.lastStats = currentStats
	procStats.lastCPUTime = currentCPUTime
	procStats.mu.Unlock()

	metrics := make([]ProcessMetric, 0, len(currentStats))

	if lastCPUTime == 0 {
		for _, info := range currentStats {
			metrics = append(metrics, ProcessMetric{
				PID:         int32(info.PID),
				Name:        info.Name,
				CPUUsage:    0,
				MemoryUsage: float64(info.RSS) / float64(memTotal) * 100,
				MemoryRSS:   info.RSS,
			})
		}
	} else {
		cpuDelta := float64(currentCPUTime - lastCPUTime)
		numCPU := float64(runtime.NumCPU())

		for pid, info := range currentStats {
			lastInfo, ok := lastStats[pid]
			if !ok {
				continue
			}

			totalTime := info.UTime + info.STime + info.CUTime + info.CSTime
			lastTotalTime := lastInfo.UTime + lastInfo.STime + lastInfo.CUTime + lastInfo.CSTime
			timeDelta := float64(totalTime - lastTotalTime)

			cpuUsage := 0.0
			if cpuDelta > 0 {
				cpuUsage = (timeDelta / cpuDelta) * 100 * numCPU
			}

			metrics = append(metrics, ProcessMetric{
				PID:         int32(info.PID),
				Name:        info.Name,
				CPUUsage:    cpuUsage,
				MemoryUsage: float64(info.RSS) / float64(memTotal) * 100,
				MemoryRSS:   info.RSS,
			})
		}
	}

	sort.Slice(metrics, func(i, j int) bool {
		return metrics[i].CPUUsage > metrics[j].CPUUsage
	})

	if len(metrics) > topN {
		metrics = metrics[:topN]
	}

	return metrics, nil
}

func collectTopProcessesFallback(topN int) ([]ProcessMetric, error) {
	processes, err := process.Processes()
	if err != nil {
		return nil, err
	}

	var metrics []ProcessMetric

	for _, p := range processes {
		name, err := p.Name()
		if err != nil {
			continue
		}

		cpuPercent, err := p.CPUPercent()
		if err != nil {
			continue
		}

		memPercent, err := p.MemoryPercent()
		if err != nil {
			continue
		}

		memInfo, err := p.MemoryInfo()
		if err != nil {
			continue
		}

		metrics = append(metrics, ProcessMetric{
			PID:         p.Pid,
			Name:        name,
			CPUUsage:    cpuPercent,
			MemoryUsage: float64(memPercent),
			MemoryRSS:   memInfo.RSS,
		})
	}

	sort.Slice(metrics, func(i, j int) bool {
		return metrics[i].CPUUsage > metrics[j].CPUUsage
	})

	if len(metrics) > topN {
		metrics = metrics[:topN]
	}

	return metrics, nil
}
