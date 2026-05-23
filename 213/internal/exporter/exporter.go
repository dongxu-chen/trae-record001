package exporter

import (
	"net/http"
	"strconv"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"

	"monitor-agent/internal/collector"
)

type Exporter struct {
	collector *collector.Collector

	cpuUsage         prometheus.Gauge
	memoryUsage      prometheus.Gauge
	memoryTotal      prometheus.Gauge
	memoryUsed       prometheus.Gauge
	diskReadBytes    *prometheus.GaugeVec
	diskWriteBytes   *prometheus.GaugeVec
	diskReadCount    *prometheus.GaugeVec
	diskWriteCount   *prometheus.GaugeVec
	netBytesSent     *prometheus.GaugeVec
	netBytesRecv     *prometheus.GaugeVec
	netPacketsSent   *prometheus.GaugeVec
	netPacketsRecv   *prometheus.GaugeVec
	processCPU       *prometheus.GaugeVec
	processMemory    *prometheus.GaugeVec
	processMemoryRSS *prometheus.GaugeVec
	gpuMemoryUsage   *prometheus.GaugeVec
	gpuMemoryUsed    *prometheus.GaugeVec
	gpuMemoryTotal   *prometheus.GaugeVec
	gpuTemperature   *prometheus.GaugeVec
	gpuPowerUsage    *prometheus.GaugeVec
	gpuPowerLimit    *prometheus.GaugeVec
	gpuUtilization   *prometheus.GaugeVec
}

func NewExporter(c *collector.Collector) *Exporter {
	e := &Exporter{
		collector: c,

		cpuUsage: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "system_cpu_usage_percent",
			Help: "System CPU usage percentage",
		}),

		memoryUsage: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "system_memory_usage_percent",
			Help: "System memory usage percentage",
		}),

		memoryTotal: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "system_memory_total_bytes",
			Help: "System total memory in bytes",
		}),

		memoryUsed: prometheus.NewGauge(prometheus.GaugeOpts{
			Name: "system_memory_used_bytes",
			Help: "System used memory in bytes",
		}),

		diskReadBytes: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "system_disk_read_bytes_per_second",
				Help: "Disk read bytes per second",
			},
			[]string{"device"},
		),

		diskWriteBytes: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "system_disk_write_bytes_per_second",
				Help: "Disk write bytes per second",
			},
			[]string{"device"},
		),

		diskReadCount: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "system_disk_read_count_per_second",
				Help: "Disk read operations per second",
			},
			[]string{"device"},
		),

		diskWriteCount: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "system_disk_write_count_per_second",
				Help: "Disk write operations per second",
			},
			[]string{"device"},
		),

		netBytesSent: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "system_network_bytes_sent_per_second",
				Help: "Network bytes sent per second",
			},
			[]string{"interface"},
		),

		netBytesRecv: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "system_network_bytes_recv_per_second",
				Help: "Network bytes received per second",
			},
			[]string{"interface"},
		),

		netPacketsSent: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "system_network_packets_sent_per_second",
				Help: "Network packets sent per second",
			},
			[]string{"interface"},
		),

		netPacketsRecv: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "system_network_packets_recv_per_second",
				Help: "Network packets received per second",
			},
			[]string{"interface"},
		),

		processCPU: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "process_cpu_usage_percent",
				Help: "Process CPU usage percentage",
			},
			[]string{"pid", "name"},
		),

		processMemory: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "process_memory_usage_percent",
				Help: "Process memory usage percentage",
			},
			[]string{"pid", "name"},
		),

		processMemoryRSS: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "process_memory_rss_bytes",
				Help: "Process RSS memory in bytes",
			},
			[]string{"pid", "name"},
		),

		gpuMemoryUsage: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "gpu_memory_usage_percent",
				Help: "GPU memory usage percentage",
			},
			[]string{"gpu_index", "gpu_name"},
		),

		gpuMemoryUsed: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "gpu_memory_used_bytes",
				Help: "GPU used memory in bytes",
			},
			[]string{"gpu_index", "gpu_name"},
		),

		gpuMemoryTotal: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "gpu_memory_total_bytes",
				Help: "GPU total memory in bytes",
			},
			[]string{"gpu_index", "gpu_name"},
		),

		gpuTemperature: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "gpu_temperature_celsius",
				Help: "GPU temperature in Celsius",
			},
			[]string{"gpu_index", "gpu_name"},
		),

		gpuPowerUsage: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "gpu_power_usage_watts",
				Help: "GPU power usage in watts",
			},
			[]string{"gpu_index", "gpu_name"},
		),

		gpuPowerLimit: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "gpu_power_limit_watts",
				Help: "GPU power limit in watts",
			},
			[]string{"gpu_index", "gpu_name"},
		),

		gpuUtilization: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "gpu_utilization_percent",
				Help: "GPU utilization percentage",
			},
			[]string{"gpu_index", "gpu_name"},
		),
	}

	prometheus.MustRegister(e.cpuUsage)
	prometheus.MustRegister(e.memoryUsage)
	prometheus.MustRegister(e.memoryTotal)
	prometheus.MustRegister(e.memoryUsed)
	prometheus.MustRegister(e.diskReadBytes)
	prometheus.MustRegister(e.diskWriteBytes)
	prometheus.MustRegister(e.diskReadCount)
	prometheus.MustRegister(e.diskWriteCount)
	prometheus.MustRegister(e.netBytesSent)
	prometheus.MustRegister(e.netBytesRecv)
	prometheus.MustRegister(e.netPacketsSent)
	prometheus.MustRegister(e.netPacketsRecv)
	prometheus.MustRegister(e.processCPU)
	prometheus.MustRegister(e.processMemory)
	prometheus.MustRegister(e.processMemoryRSS)
	prometheus.MustRegister(e.gpuMemoryUsage)
	prometheus.MustRegister(e.gpuMemoryUsed)
	prometheus.MustRegister(e.gpuMemoryTotal)
	prometheus.MustRegister(e.gpuTemperature)
	prometheus.MustRegister(e.gpuPowerUsage)
	prometheus.MustRegister(e.gpuPowerLimit)
	prometheus.MustRegister(e.gpuUtilization)

	return e
}

func (e *Exporter) UpdateMetrics() {
	metrics := e.collector.GetLatestMetrics()
	if metrics == nil {
		return
	}

	e.cpuUsage.Set(metrics.CPUUsage)
	e.memoryUsage.Set(metrics.MemoryUsage)
	e.memoryTotal.Set(float64(metrics.MemoryTotal))
	e.memoryUsed.Set(float64(metrics.MemoryUsed))

	e.diskReadBytes.Reset()
	e.diskWriteBytes.Reset()
	e.diskReadCount.Reset()
	e.diskWriteCount.Reset()
	for device, disk := range metrics.DiskIO {
		e.diskReadBytes.WithLabelValues(device).Set(float64(disk.ReadBytes))
		e.diskWriteBytes.WithLabelValues(device).Set(float64(disk.WriteBytes))
		e.diskReadCount.WithLabelValues(device).Set(float64(disk.ReadCount))
		e.diskWriteCount.WithLabelValues(device).Set(float64(disk.WriteCount))
	}

	e.netBytesSent.Reset()
	e.netBytesRecv.Reset()
	e.netPacketsSent.Reset()
	e.netPacketsRecv.Reset()
	for iface, net := range metrics.Network {
		e.netBytesSent.WithLabelValues(iface).Set(float64(net.BytesSent))
		e.netBytesRecv.WithLabelValues(iface).Set(float64(net.BytesRecv))
		e.netPacketsSent.WithLabelValues(iface).Set(float64(net.PacketsSent))
		e.netPacketsRecv.WithLabelValues(iface).Set(float64(net.PacketsRecv))
	}

	e.processCPU.Reset()
	e.processMemory.Reset()
	e.processMemoryRSS.Reset()
	for _, proc := range metrics.Processes {
		pidStr := strconv.Itoa(int(proc.PID))
		e.processCPU.WithLabelValues(pidStr, proc.Name).Set(proc.CPUUsage)
		e.processMemory.WithLabelValues(pidStr, proc.Name).Set(proc.MemoryUsage)
		e.processMemoryRSS.WithLabelValues(pidStr, proc.Name).Set(float64(proc.MemoryRSS))
	}

	e.gpuMemoryUsage.Reset()
	e.gpuMemoryUsed.Reset()
	e.gpuMemoryTotal.Reset()
	e.gpuTemperature.Reset()
	e.gpuPowerUsage.Reset()
	e.gpuPowerLimit.Reset()
	e.gpuUtilization.Reset()
	for _, gpu := range metrics.GPUs {
		indexStr := strconv.Itoa(gpu.Index)
		e.gpuMemoryUsage.WithLabelValues(indexStr, gpu.Name).Set(gpu.MemoryUsagePercent)
		e.gpuMemoryUsed.WithLabelValues(indexStr, gpu.Name).Set(float64(gpu.MemoryUsed))
		e.gpuMemoryTotal.WithLabelValues(indexStr, gpu.Name).Set(float64(gpu.MemoryTotal))
		e.gpuTemperature.WithLabelValues(indexStr, gpu.Name).Set(gpu.Temperature)
		e.gpuPowerUsage.WithLabelValues(indexStr, gpu.Name).Set(gpu.PowerUsage)
		e.gpuPowerLimit.WithLabelValues(indexStr, gpu.Name).Set(gpu.PowerLimit)
		e.gpuUtilization.WithLabelValues(indexStr, gpu.Name).Set(gpu.GPUUtilization)
	}
}

func (e *Exporter) Handler() http.Handler {
	return promhttp.Handler()
}
