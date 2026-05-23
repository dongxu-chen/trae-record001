package collector

import (
	"context"
	"log"
	"sync"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/net"

	"monitor-agent/internal/config"
)

type Metrics struct {
	CPUUsage    float64
	MemoryUsage float64
	MemoryTotal uint64
	MemoryUsed  uint64
	DiskIO      map[string]DiskIOMetric
	Network     map[string]NetworkMetric
	Processes   []ProcessMetric
	GPUs        []GPUMetric
	Timestamp   time.Time
}

type DiskIOMetric struct {
	ReadBytes  uint64
	WriteBytes uint64
	ReadCount  uint64
	WriteCount uint64
}

type NetworkMetric struct {
	BytesSent   uint64
	BytesRecv   uint64
	PacketsSent uint64
	PacketsRecv uint64
}

type ProcessMetric struct {
	PID         int32
	Name        string
	CPUUsage    float64
	MemoryUsage float64
	MemoryRSS   uint64
}

type Collector struct {
	mu              sync.RWMutex
	lastDiskIO      map[string]DiskIOMetric
	lastNetwork     map[string]NetworkMetric
	lastCollectTime time.Time
	currentMetrics  *Metrics
	gpuCollector    *GPUCollector
}

func NewCollector() *Collector {
	return &Collector{
		lastDiskIO:   make(map[string]DiskIOMetric),
		lastNetwork:  make(map[string]NetworkMetric),
		gpuCollector: NewGPUCollector(),
	}
}

func (c *Collector) Collect(ctx context.Context) (*Metrics, error) {
	cfg := config.GetConfig()
	
	metrics := &Metrics{
		Timestamp: time.Now(),
	}

	var wg sync.WaitGroup
	var errMu sync.Mutex
	var errors []error

	wg.Add(4)

	go func() {
		defer wg.Done()
		if cpuUsage, err := collectCPU(); err != nil {
			errMu.Lock()
			errors = append(errors, err)
			errMu.Unlock()
		} else {
			metrics.CPUUsage = cpuUsage
		}
	}()

	go func() {
		defer wg.Done()
		if memMetric, err := collectMemory(); err != nil {
			errMu.Lock()
			errors = append(errors, err)
			errMu.Unlock()
		} else {
			metrics.MemoryUsage = memMetric.Usage
			metrics.MemoryTotal = memMetric.Total
			metrics.MemoryUsed = memMetric.Used
		}
	}()

	go func() {
		defer wg.Done()
		diskIO, err := c.collectDiskIO(cfg.Collector.Disks)
		if err != nil {
			errMu.Lock()
			errors = append(errors, err)
			errMu.Unlock()
		} else {
			metrics.DiskIO = diskIO
		}
	}()

	go func() {
		defer wg.Done()
		network, err := c.collectNetwork(cfg.Collector.NetInterfaces)
		if err != nil {
			errMu.Lock()
			errors = append(errors, err)
			errMu.Unlock()
		} else {
			metrics.Network = network
		}
	}()

	wg.Wait()

	processes, err := collectTopProcessesProc(cfg.Collector.TopProcessCount)
	if err != nil {
		errors = append(errors, err)
	} else {
		metrics.Processes = processes
	}

	if c.gpuCollector.IsEnabled() {
		if gpus, err := c.gpuCollector.Collect(); err != nil {
			errors = append(errors, err)
		} else {
			metrics.GPUs = gpus
		}
	}

	for _, err := range errors {
		log.Printf("Collection error: %v", err)
	}

	c.mu.Lock()
	c.currentMetrics = metrics
	c.mu.Unlock()

	return metrics, nil
}

func collectCPU() (float64, error) {
	percentages, err := cpu.Percent(time.Second, false)
	if err != nil {
		return 0, err
	}
	if len(percentages) > 0 {
		return percentages[0], nil
	}
	return 0, nil
}

type memoryMetric struct {
	Usage float64
	Total uint64
	Used  uint64
}

func collectMemory() (*memoryMetric, error) {
	v, err := mem.VirtualMemory()
	if err != nil {
		return nil, err
	}
	return &memoryMetric{
		Usage: v.UsedPercent,
		Total: v.Total,
		Used:  v.Used,
	}, nil
}

func (c *Collector) collectDiskIO(disks []string) (map[string]DiskIOMetric, error) {
	ioCounters, err := disk.IOCounters(disks...)
	if err != nil {
		return nil, err
	}

	result := make(map[string]DiskIOMetric)
	now := time.Now()

	c.mu.RLock()
	lastTime := c.lastCollectTime
	lastDiskIO := c.lastDiskIO
	c.mu.RUnlock()

	interval := now.Sub(lastTime).Seconds()

	for name, counter := range ioCounters {
		current := DiskIOMetric{
			ReadBytes:  counter.ReadBytes,
			WriteBytes: counter.WriteBytes,
			ReadCount:  counter.ReadCount,
			WriteCount: counter.WriteCount,
		}

		if last, ok := lastDiskIO[name]; ok && interval > 0 {
			result[name] = DiskIOMetric{
				ReadBytes:  uint64(float64(current.ReadBytes-last.ReadBytes) / interval),
				WriteBytes: uint64(float64(current.WriteBytes-last.WriteBytes) / interval),
				ReadCount:  uint64(float64(current.ReadCount-last.ReadCount) / interval),
				WriteCount: uint64(float64(current.WriteCount-last.WriteCount) / interval),
			}
		} else {
			result[name] = current
		}

		c.mu.Lock()
		c.lastDiskIO[name] = current
		c.mu.Unlock()
	}

	c.mu.Lock()
	c.lastCollectTime = now
	c.mu.Unlock()

	return result, nil
}

func (c *Collector) collectNetwork(interfaces []string) (map[string]NetworkMetric, error) {
	ioCounters, err := net.IOCounters(true)
	if err != nil {
		return nil, err
	}

	result := make(map[string]NetworkMetric)
	now := time.Now()

	c.mu.RLock()
	lastTime := c.lastCollectTime
	lastNetwork := c.lastNetwork
	c.mu.RUnlock()

	interval := now.Sub(lastTime).Seconds()

	interfaceSet := make(map[string]bool)
	for _, iface := range interfaces {
		interfaceSet[iface] = true
	}

	for _, counter := range ioCounters {
		if len(interfaces) > 0 && !interfaceSet[counter.Name] {
			continue
		}

		current := NetworkMetric{
			BytesSent:   counter.BytesSent,
			BytesRecv:   counter.BytesRecv,
			PacketsSent: counter.PacketsSent,
			PacketsRecv: counter.PacketsRecv,
		}

		if last, ok := lastNetwork[counter.Name]; ok && interval > 0 {
			result[counter.Name] = NetworkMetric{
				BytesSent:   uint64(float64(current.BytesSent-last.BytesSent) / interval),
				BytesRecv:   uint64(float64(current.BytesRecv-last.BytesRecv) / interval),
				PacketsSent: uint64(float64(current.PacketsSent-last.PacketsSent) / interval),
				PacketsRecv: uint64(float64(current.PacketsRecv-last.PacketsRecv) / interval),
			}
		} else {
			result[counter.Name] = current
		}

		c.mu.Lock()
		c.lastNetwork[counter.Name] = current
		c.mu.Unlock()
	}

	return result, nil
}



func (c *Collector) GetLatestMetrics() *Metrics {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.currentMetrics
}
