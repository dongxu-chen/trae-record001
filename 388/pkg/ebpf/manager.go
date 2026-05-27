package ebpf

import (
	"context"
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"

	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/perf"
	"github.com/sirupsen/logrus"
)

type MonitorMode int

const (
	ModeEBPF MonitorMode = iota
	ModeKprobe
	ModeSimulate
)

func (m MonitorMode) String() string {
	return []string{"eBPF", "kprobe", "simulate"}[m]
}

type Manager struct {
	mode        MonitorMode
	processColl *ebpf.Collection
	fileColl    *ebpf.Collection
	networkColl *ebpf.Collection
	kprobeMgr   *KprobeManager
}

type ProcessEvent struct {
	PID         uint32
	PPID        uint32
	UID         uint32
	GID         uint32
	Comm        [16]byte
	ContainerID [64]byte
	Timestamp   uint64
	EventType   uint32
}

type FileEvent struct {
	PID         uint32
	UID         uint32
	Comm        [16]byte
	ContainerID [64]byte
	Filename    [256]byte
	Timestamp   uint64
	EventType   uint32
	Mode        uint32
}

type NetworkEvent struct {
	PID         uint32
	UID         uint32
	Comm        [16]byte
	ContainerID [64]byte
	Saddr       uint32
	Daddr       uint32
	Sport       uint16
	Dport       uint16
	Protocol    uint8
	Timestamp   uint64
	EventType   uint32
}

type KernelVersion struct {
	Major int
	Minor int
	Patch int
}

func ParseKernelVersion(version string) (*KernelVersion, error) {
	re := regexp.MustCompile(`(\d+)\.(\d+)\.(\d+)`)
	matches := re.FindStringSubmatch(version)
	if len(matches) < 4 {
		return nil, fmt.Errorf("invalid kernel version: %s", version)
	}

	major, _ := strconv.Atoi(matches[1])
	minor, _ := strconv.Atoi(matches[2])
	patch, _ := strconv.Atoi(matches[3])

	return &KernelVersion{Major: major, Minor: minor, Patch: patch}, nil
}

func (kv *KernelVersion) IsEBPFSupported() bool {
	if kv.Major > 5 {
		return true
	}
	if kv.Major == 5 && kv.Minor >= 8 {
		return true
	}
	return false
}

func (kv *KernelVersion) IsKprobeSupported() bool {
	if kv.Major > 4 {
		return true
	}
	if kv.Major == 4 && kv.Minor >= 16 {
		return true
	}
	return false
}

func GetKernelVersion() (*KernelVersion, error) {
	data, err := os.ReadFile("/proc/version")
	if err != nil {
		return nil, fmt.Errorf("failed to read kernel version: %v", err)
	}

	return ParseKernelVersion(string(data))
}

func CheckEBPFSupport() (bool, error) {
	kv, err := GetKernelVersion()
	if err != nil {
		return false, err
	}

	if !kv.IsEBPFSupported() {
		return false, nil
	}

	_, err = os.Stat("/sys/kernel/debug/tracing")
	if err != nil {
		_, err = os.Stat("/sys/kernel/tracing")
		if err != nil {
			return false, fmt.Errorf("debugfs not mounted")
		}
	}

	return true, nil
}

func DetermineMonitorMode() (MonitorMode, error) {
	kv, err := GetKernelVersion()
	if err != nil {
		logrus.Warnf("Failed to get kernel version: %v, using simulate mode", err)
		return ModeSimulate, nil
	}

	logrus.Infof("Kernel version: %d.%d.%d", kv.Major, kv.Minor, kv.Patch)

	ebpfSupported, err := CheckEBPFSupport()
	if err == nil && ebpfSupported {
		logrus.Info("eBPF mode available, will use eBPF for monitoring")
		return ModeEBPF, nil
	}

	if kv.IsKprobeSupported() {
		logrus.Info("eBPF not fully supported, falling back to kprobe mode")
		return ModeKprobe, nil
	}

	logrus.Warn("Neither eBPF nor kprobe supported, using simulation mode")
	return ModeSimulate, nil
}

func NewManager() *Manager {
	return &Manager{}
}

func (m *Manager) Load() error {
	mode, err := DetermineMonitorMode()
	if err != nil {
		logrus.Warnf("Failed to determine monitor mode: %v", err)
		mode = ModeSimulate
	}

	m.mode = mode
	logrus.Infof("Loading programs in %s mode...", mode.String())

	switch mode {
	case ModeEBPF:
		return m.loadEBPF()
	case ModeKprobe:
		return m.loadKprobe()
	default:
		return m.loadSimulate()
	}
}

func (m *Manager) loadEBPF() error {
	logrus.Info("Loading eBPF programs...")

	processSpec, err := ebpf.LoadCollectionSpec("bpf/process_monitor_bpfel.o")
	if err != nil {
		logrus.Warnf("Failed to load process eBPF spec: %v, falling back to kprobe", err)
		return m.loadKprobe()
	}

	m.processColl, err = ebpf.NewCollection(processSpec)
	if err != nil {
		logrus.Warnf("Failed to create process collection: %v", err)
	}

	fileSpec, err := ebpf.LoadCollectionSpec("bpf/file_monitor_bpfel.o")
	if err != nil {
		logrus.Warnf("Failed to load file eBPF spec: %v", err)
	} else {
		m.fileColl, err = ebpf.NewCollection(fileSpec)
		if err != nil {
			logrus.Warnf("Failed to create file collection: %v", err)
		}
	}

	networkSpec, err := ebpf.LoadCollectionSpec("bpf/network_monitor_bpfel.o")
	if err != nil {
		logrus.Warnf("Failed to load network eBPF spec: %v", err)
	} else {
		m.networkColl, err = ebpf.NewCollection(networkSpec)
		if err != nil {
			logrus.Warnf("Failed to create network collection: %v", err)
		}
	}

	if m.processColl == nil && m.fileColl == nil && m.networkColl == nil {
		logrus.Warn("All eBPF programs failed to load, falling back to kprobe")
		return m.loadKprobe()
	}

	logrus.Info("eBPF programs loaded successfully")
	return nil
}

func (m *Manager) loadKprobe() error {
	logrus.Info("Loading kprobe-based monitoring...")
	m.kprobeMgr = NewKprobeManager()
	return m.kprobeMgr.Load()
}

func (m *Manager) loadSimulate() error {
	logrus.Info("Simulation mode - no actual kernel monitoring")
	return nil
}

func (m *Manager) Run(ctx context.Context, eventChan chan<- interface{}) error {
	logrus.Infof("Starting monitoring in %s mode...", m.mode.String())

	switch m.mode {
	case ModeEBPF:
		return m.runEBPF(ctx, eventChan)
	case ModeKprobe:
		return m.runKprobe(ctx, eventChan)
	default:
		return m.runSimulate(ctx, eventChan)
	}
}

func (m *Manager) runEBPF(ctx context.Context, eventChan chan<- interface{}) error {
	logrus.Info("eBPF monitor started")

	if m.processColl != nil {
		if processMap, ok := m.processColl.Maps["process_events"]; ok {
			rd, err := perf.NewReader(processMap, 4096)
			if err != nil {
				logrus.Errorf("Failed to create process perf reader: %v", err)
			} else {
				go readPerfEvents(rd, eventChan, "process")
			}
		}
	}

	if m.fileColl != nil {
		if fileMap, ok := m.fileColl.Maps["file_events"]; ok {
			rd, err := perf.NewReader(fileMap, 4096)
			if err != nil {
				logrus.Errorf("Failed to create file perf reader: %v", err)
			} else {
				go readPerfEvents(rd, eventChan, "file")
			}
		}
	}

	if m.networkColl != nil {
		if networkMap, ok := m.networkColl.Maps["network_events"]; ok {
			rd, err := perf.NewReader(networkMap, 4096)
			if err != nil {
				logrus.Errorf("Failed to create network perf reader: %v", err)
			} else {
				go readPerfEvents(rd, eventChan, "network")
			}
		}
	}

	<-ctx.Done()
	return nil
}

func (m *Manager) runKprobe(ctx context.Context, eventChan chan<- interface{}) error {
	logrus.Info("Kprobe monitor started")
	return m.kprobeMgr.Run(ctx, eventChan)
}

func (m *Manager) runSimulate(ctx context.Context, eventChan chan<- interface{}) error {
	go m.simulateProcessEvents(ctx, eventChan)
	go m.simulateFileEvents(ctx, eventChan)
	go m.simulateNetworkEvents(ctx, eventChan)

	logrus.Info("Simulation monitor started - generating sample events")
	return nil
}

func (m *Manager) simulateProcessEvents(ctx context.Context, eventChan chan<- interface{}) {
	logrus.Info("Process monitor started (simulation mode)")
	<-ctx.Done()
}

func (m *Manager) simulateFileEvents(ctx context.Context, eventChan chan<- interface{}) {
	logrus.Info("File monitor started (simulation mode)")
	<-ctx.Done()
}

func (m *Manager) simulateNetworkEvents(ctx context.Context, eventChan chan<- interface{}) {
	logrus.Info("Network monitor started (simulation mode)")
	<-ctx.Done()
}

func readPerfEvents(rd *perf.Reader, eventChan chan<- interface{}, eventType string) {
	for {
		record, err := rd.Read()
		if err != nil {
			if perf.IsClosed(err) {
				return
			}
			logrus.Errorf("Error reading perf event: %v", err)
			continue
		}

		if record.LostSamples != 0 {
			logrus.Warnf("Lost %d samples", record.LostSamples)
			continue
		}

		eventChan <- record.RawSample
	}
}

func (m *Manager) Close() {
	logrus.Infof("Closing %s monitor...", m.mode.String())

	switch m.mode {
	case ModeEBPF:
		if m.processColl != nil {
			m.processColl.Close()
		}
		if m.fileColl != nil {
			m.fileColl.Close()
		}
		if m.networkColl != nil {
			m.networkColl.Close()
		}
	case ModeKprobe:
		if m.kprobeMgr != nil {
			m.kprobeMgr.Close()
		}
	}

	logrus.Info("Monitor programs unloaded")
}

func (m *Manager) GetMode() MonitorMode {
	return m.mode
}

func LoadCollection(path string, spec interface{}) (*ebpf.Collection, error) {
	return nil, fmt.Errorf("eBPF loading requires Linux kernel with BPF support")
}

func GetHostname() string {
	hostname, err := os.Hostname()
	if err != nil {
		return "unknown"
	}
	return hostname
}

func GetCurrentContainerID() string {
	cgroup, err := os.ReadFile("/proc/self/cgroup")
	if err != nil {
		return ""
	}

	cgroupStr := string(cgroup)
	if strings.Contains(cgroupStr, "docker") || strings.Contains(cgroupStr, "containerd") {
		parts := strings.Split(cgroupStr, "/")
		if len(parts) > 0 {
			containerID := strings.TrimSpace(parts[len(parts)-1])
			if len(containerID) >= 12 {
				return containerID[:12]
			}
		}
	}

	return ""
}
