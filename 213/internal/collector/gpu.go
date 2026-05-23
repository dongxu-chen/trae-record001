package collector

import (
	"bufio"
	"bytes"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
	"sync"
)

type GPUMetric struct {
	Index             int
	Name              string
	MemoryUsagePercent float64
	MemoryUsed        uint64
	MemoryTotal       uint64
	Temperature       float64
	PowerUsage        float64
	PowerLimit        float64
	GPUUtilization    float64
}

type GPUCollector struct {
	mu      sync.RWMutex
	metrics []GPUMetric
	enabled bool
}

func NewGPUCollector() *GPUCollector {
	return &GPUCollector{
		metrics: make([]GPUMetric, 0),
		enabled: checkNvidiaSMI(),
	}
}

func checkNvidiaSMI() bool {
	_, err := exec.LookPath("nvidia-smi")
	return err == nil
}

func (g *GPUCollector) IsEnabled() bool {
	return g.enabled
}

func (g *GPUCollector) Collect() ([]GPUMetric, error) {
	if !g.enabled {
		return nil, fmt.Errorf("nvidia-smi not available")
	}

	metrics, err := queryNvidiaGPU()
	if err != nil {
		return nil, err
	}

	g.mu.Lock()
	g.metrics = metrics
	g.mu.Unlock()

	return metrics, nil
}

func (g *GPUCollector) GetLatestMetrics() []GPUMetric {
	g.mu.RLock()
	defer g.mu.RUnlock()
	return g.metrics
}

func queryNvidiaGPU() ([]GPUMetric, error) {
	queryFields := []string{
		"index",
		"name",
		"memory.used",
		"memory.total",
		"temperature.gpu",
		"power.draw",
		"power.limit",
		"utilization.gpu",
	}

	queryStr := strings.Join(queryFields, ",")
	cmd := exec.Command("nvidia-smi",
		"--query-gpu="+queryStr,
		"--format=csv,noheader,nounits",
	)

	var out bytes.Buffer
	cmd.Stdout = &out
	err := cmd.Run()
	if err != nil {
		return nil, fmt.Errorf("nvidia-smi failed: %w", err)
	}

	var metrics []GPUMetric
	scanner := bufio.NewScanner(&out)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}

		fields := strings.Split(line, ", ")
		if len(fields) < 8 {
			continue
		}

		metric, err := parseGPUFields(fields)
		if err != nil {
			continue
		}

		metrics = append(metrics, metric)
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return metrics, nil
}

func parseGPUFields(fields []string) (GPUMetric, error) {
	index, _ := strconv.Atoi(fields[0])
	name := fields[1]
	memUsed, _ := strconv.ParseUint(fields[2], 10, 64)
	memTotal, _ := strconv.ParseUint(fields[3], 10, 64)
	temp, _ := strconv.ParseFloat(fields[4], 64)
	powerDraw, _ := strconv.ParseFloat(fields[5], 64)
	powerLimit, _ := strconv.ParseFloat(fields[6], 64)
	gpuUtil, _ := strconv.ParseFloat(fields[7], 64)

	memUsedBytes := memUsed * 1024 * 1024
	memTotalBytes := memTotal * 1024 * 1024

	memUsagePercent := 0.0
	if memTotal > 0 {
		memUsagePercent = float64(memUsed) / float64(memTotal) * 100
	}

	return GPUMetric{
		Index:              index,
		Name:               name,
		MemoryUsagePercent: memUsagePercent,
		MemoryUsed:         memUsedBytes,
		MemoryTotal:        memTotalBytes,
		Temperature:        temp,
		PowerUsage:         powerDraw,
		PowerLimit:         powerLimit,
		GPUUtilization:     gpuUtil,
	}, nil
}
