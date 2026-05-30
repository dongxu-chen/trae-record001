package simulator

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/security/container-escape-detector/pkg/types"
)

type Config struct {
	Enabled           bool     `yaml:"enabled"`
	Mode              string   `yaml:"mode"`
	IntervalSeconds   int      `yaml:"interval_seconds"`
	TargetContainers  []string `yaml:"target_containers"`
	MaxAttemptsPerRun int      `yaml:"max_attempts_per_run"`
	EnableDangerous   bool     `yaml:"enable_dangerous"`
}

type EscapeSimulator struct {
	config     *Config
	logger     *logrus.Logger
	stopChan   chan struct{}
	wg         sync.WaitGroup
	mu         sync.Mutex
	results    map[string]*SimulationResult
	running    bool
	eventCb    func(*types.BPFEvent)
}

type SimulationResult struct {
	TechniqueID   string
	TechniqueName string
	Success       bool
	Output        string
	Timestamp     time.Time
	Duration      time.Duration
	RiskLevel     types.RiskLevel
}

type EscapeTechnique struct {
	ID          string
	Name        string
	Description string
	Category    string
	RiskLevel   types.RiskLevel
	Dangerous   bool
	Execute     func() (bool, string)
}

func NewEscapeSimulator(logger *logrus.Logger, config *Config) *EscapeSimulator {
	if config == nil {
		config = &Config{
			Enabled:           false,
			Mode:              "passive",
			IntervalSeconds:   3600,
			MaxAttemptsPerRun: 10,
			EnableDangerous:   false,
		}
	}

	return &EscapeSimulator{
		config:  config,
		logger:  logger,
		stopChan: make(chan struct{}),
		results:  make(map[string]*SimulationResult),
	}
}

func (s *EscapeSimulator) SetEventCallback(cb func(*types.BPFEvent)) {
	s.eventCb = cb
}

func (s *EscapeSimulator) Start() error {
	if !s.config.Enabled {
		s.logger.Info("Escape simulator disabled")
		return nil
	}

	s.mu.Lock()
	if s.running {
		s.mu.Unlock()
		return fmt.Errorf("simulator already running")
	}
	s.running = true
	s.mu.Unlock()

	s.wg.Add(1)
	go s.runLoop()

	s.logger.Infof("Escape simulator started in %s mode", s.config.Mode)
	return nil
}

func (s *EscapeSimulator) Stop() {
	s.mu.Lock()
	if !s.running {
		s.mu.Unlock()
		return
	}
	s.running = false
	s.mu.Unlock()

	close(s.stopChan)
	s.wg.Wait()

	s.logger.Info("Escape simulator stopped")
}

func (s *EscapeSimulator) runLoop() {
	defer s.wg.Done()

	ticker := time.NewTicker(time.Duration(s.config.IntervalSeconds) * time.Second)
	defer ticker.Stop()

	s.RunSimulation()

	for {
		select {
		case <-s.stopChan:
			return
		case <-ticker.C:
			s.RunSimulation()
		}
	}
}

func (s *EscapeSimulator) RunSimulation() []*SimulationResult {
	s.logger.Info("Starting escape simulation")

	techniques := s.getTechniques()
	results := make([]*SimulationResult, 0)
	count := 0

	for _, tech := range techniques {
		if tech.Dangerous && !s.config.EnableDangerous {
			continue
		}

		if count >= s.config.MaxAttemptsPerRun {
			break
		}

		s.logger.Infof("Simulating escape technique: %s (%s)", tech.ID, tech.Name)

		start := time.Now()
		success, output := tech.Execute()
		duration := time.Since(start)

		result := &SimulationResult{
			TechniqueID:   tech.ID,
			TechniqueName: tech.Name,
			Success:       success,
			Output:        output,
			Timestamp:     time.Now(),
			Duration:      duration,
			RiskLevel:     tech.RiskLevel,
		}

		s.mu.Lock()
		s.results[tech.ID] = result
		s.mu.Unlock()

		results = append(results, result)
		count++

		if success {
			s.logger.Warnf("Technique %s succeeded: %s", tech.ID, output)
		} else {
			s.logger.Debugf("Technique %s failed: %s", tech.ID, output)
		}

		time.Sleep(500 * time.Millisecond)
	}

	s.logger.Infof("Simulation complete: %d techniques tested", len(results))
	return results
}

func (s *EscapeSimulator) getTechniques() []EscapeTechnique {
	return []EscapeTechnique{
		{
			ID:          "ESCAPE-SIM-001",
			Name:        "Docker Socket Mount Check",
			Description: "Check if docker socket is accessible and usable",
			Category:    "mount",
			RiskLevel:   types.RiskCritical,
			Dangerous:   false,
			Execute:     s.checkDockerSocket,
		},
		{
			ID:          "ESCAPE-SIM-002",
			Name:        "Host Proc FS Enumeration",
			Description: "Check if /proc from host is accessible",
			Category:    "mount",
			RiskLevel:   types.RiskHigh,
			Dangerous:   false,
			Execute:     s.checkHostProc,
		},
		{
			ID:          "ESCAPE-SIM-003",
			Name:        "Privileged Container Check",
			Description: "Check if running in privileged mode",
			Category:    "privilege",
			RiskLevel:   types.RiskHigh,
			Dangerous:   false,
			Execute:     s.checkPrivileged,
		},
		{
			ID:          "ESCAPE-SIM-004",
			Name:        "CGroup v1 Release Agent",
			Description: "Test cgroup v1 release agent vulnerability",
			Category:    "cgroup",
			RiskLevel:   types.RiskCritical,
			Dangerous:   true,
			Execute:     s.checkCgroupV1,
		},
		{
			ID:          "ESCAPE-SIM-005",
			Name:        "Host Sys FS Access",
			Description: "Check if host /sys filesystem is accessible",
			Category:    "mount",
			RiskLevel:   types.RiskHigh,
			Dangerous:   false,
			Execute:     s.checkHostSys,
		},
		{
			ID:          "ESCAPE-SIM-006",
			Name:        "MKNOD Capability Test",
			Description: "Test if device node creation is possible",
			Category:    "capability",
			RiskLevel:   types.RiskHigh,
			Dangerous:   true,
			Execute:     s.checkMknod,
		},
		{
			ID:          "ESCAPE-SIM-007",
			Name:        "Kubernetes Service Account",
			Description: "Check for exposed K8s service account token",
			Category:    "kubernetes",
			RiskLevel:   types.RiskHigh,
			Dangerous:   false,
			Execute:     s.checkK8sSA,
		},
		{
			ID:          "ESCAPE-SIM-008",
			Name:        "Host Root Filesystem",
			Description: "Check if host root filesystem is mounted",
			Category:    "mount",
			RiskLevel:   types.RiskCritical,
			Dangerous:   false,
			Execute:     s.checkHostRoot,
		},
		{
			ID:          "ESCAPE-SIM-009",
			Name:        "Ptrace Permission",
			Description: "Test if ptrace can attach to host processes",
			Category:    "syscall",
			RiskLevel:   types.RiskHigh,
			Dangerous:   true,
			Execute:     s.checkPtrace,
		},
		{
			ID:          "ESCAPE-SIM-010",
			Name:        "Namespace Escapability",
			Description: "Test if namespace manipulation is possible",
			Category:    "namespace",
			RiskLevel:   types.RiskHigh,
			Dangerous:   true,
			Execute:     s.checkNamespace,
		},
	}
}

func (s *EscapeSimulator) checkDockerSocket() (bool, string) {
	socketPaths := []string{
		"/var/run/docker.sock",
		"/host/var/run/docker.sock",
		"/run/docker.sock",
		"/host/run/docker.sock",
	}

	for _, path := range socketPaths {
		if _, err := os.Stat(path); err == nil {
			s.emitEvent(types.EventMount, map[string]interface{}{
				"mount_source": path,
				"mount_target": path,
				"fs_type":      "socket",
				"comm":         "escape-sim",
			})
			return true, fmt.Sprintf("Docker socket accessible at %s", path)
		}
	}

	return false, "No docker socket found"
}

func (s *EscapeSimulator) checkHostProc() (bool, string) {
	mountPoints := []string{
		"/host/proc",
		"/proc_host",
		"/mnt/proc",
	}

	for _, mp := range mountPoints {
		if _, err := os.Stat(filepath.Join(mp, "1", "status")); err == nil {
			s.emitEvent(types.EventMount, map[string]interface{}{
				"mount_source": "/proc",
				"mount_target": mp,
				"comm":         "escape-sim",
			})
			return true, fmt.Sprintf("Host /proc accessible at %s", mp)
		}
	}

	envs := os.Environ()
	for _, env := range envs {
		if strings.Contains(env, "HOST_PROC") {
			return true, "Host proc path detected in environment"
		}
	}

	return false, "Host /proc not accessible"
}

func (s *EscapeSimulator) checkPrivileged() (bool, string) {
	// Check if we can access /dev/kmsg (only in privileged)
	if _, err := os.Open("/dev/kmsg"); err == nil {
		s.emitEvent(types.EventFile, map[string]interface{}{
			"file_name": "/dev/kmsg",
			"comm":      "escape-sim",
		})
		return true, "Can access /dev/kmsg - running in privileged mode"
	}

	// Check cap_sys_admin via /proc/self/status
	caps, err := s.readCaps()
	if err == nil {
		if strings.Contains(caps, "CapEff:\t0000003fffffffff") {
			return true, "Full capabilities detected - likely privileged"
		}
		if strings.Contains(caps, "00000000a80425fb") {
			return false, "Standard container capabilities"
		}
	}

	return false, "Not running in privileged mode"
}

func (s *EscapeSimulator) checkCgroupV1() (bool, string) {
	cgroupPaths := []string{
		"/sys/fs/cgroup",
		"/cgroup",
	}

	for _, cp := range cgroupPaths {
		if _, err := os.Stat(filepath.Join(cp, "release_agent")); err == nil {
			return true, fmt.Sprintf("Cgroup release_agent accessible at %s", cp)
		}
	}

	// Check if we can create a cgroup
	testCgroup := "/sys/fs/cgroup/cpu/test_cgroup"
	if err := os.MkdirAll(testCgroup, 0755); err == nil {
		defer os.Remove(testCgroup)
		return true, "Can create cgroup directories"
	}

	return false, "Cgroup v1 escape not possible"
}

func (s *EscapeSimulator) checkHostSys() (bool, string) {
	sysPaths := []string{
		"/host/sys",
		"/sys_host",
		"/mnt/sys",
	}

	for _, sp := range sysPaths {
		if _, err := os.Stat(filepath.Join(sp, "kernel")); err == nil {
			s.emitEvent(types.EventMount, map[string]interface{}{
				"mount_source": "/sys",
				"mount_target": sp,
				"comm":         "escape-sim",
			})
			return true, fmt.Sprintf("Host /sys accessible at %s", sp)
		}
	}

	return false, "Host /sys not accessible"
}

func (s *EscapeSimulator) checkMknod() (bool, string) {
	testDev := "/tmp/test_dev_sda"
	defer os.Remove(testDev)

	err := syscall.Mknod(testDev, syscall.S_IFBLK|0600, int(8<<8))
	if err == nil {
		s.emitEvent(types.EventSyscall, map[string]interface{}{
			"syscall_name": "mknod",
			"file_name":    testDev,
			"comm":         "escape-sim",
		})
		return true, "Can create device nodes - mknod capability available"
	}

	return false, "Cannot create device nodes"
}

func (s *EscapeSimulator) checkK8sSA() (bool, string) {
	saPaths := []string{
		"/var/run/secrets/kubernetes.io/serviceaccount",
		"/run/secrets/kubernetes.io/serviceaccount",
	}

	for _, sp := range saPaths {
		tokenPath := filepath.Join(sp, "token")
		if content, err := os.ReadFile(tokenPath); err == nil && len(content) > 0 {
			s.emitEvent(types.EventFile, map[string]interface{}{
				"file_name": tokenPath,
				"comm":      "escape-sim",
			})
			return true, fmt.Sprintf("K8s service account token found at %s", sp)
		}
	}

	return false, "No K8s service account found"
}

func (s *EscapeSimulator) checkHostRoot() (bool, string) {
	mountPoints := []string{
		"/host",
		"/rootfs",
		"/hostfs",
		"/mnt/host",
	}

	for _, mp := range mountPoints {
		etcPasswd := filepath.Join(mp, "etc", "passwd")
		if content, err := os.ReadFile(etcPasswd); err == nil {
			if strings.Contains(string(content), "root:x:0:0:") {
				s.emitEvent(types.EventMount, map[string]interface{}{
					"mount_source": "/",
					"mount_target": mp,
					"comm":         "escape-sim",
				})
				return true, fmt.Sprintf("Host root filesystem mounted at %s", mp)
			}
		}
	}

	return false, "Host root filesystem not mounted"
}

func (s *EscapeSimulator) checkPtrace() (bool, string) {
	if _, err := os.Stat("/proc/1/status"); err == nil {
		cmd := exec.Command("grep", "TracerPid", "/proc/1/status")
		if output, err := cmd.Output(); err == nil {
			if strings.Contains(string(output), "TracerPid:\t0") {
				return true, "Can read /proc/1/status - potential ptrace target"
			}
		}
	}

	return false, "Ptrace escape not possible"
}

func (s *EscapeSimulator) checkNamespace() (bool, string) {
	if _, err := os.Stat("/proc/self/ns/pid"); err == nil {
		if _, err := os.Stat("/proc/self/ns/mnt"); err == nil {
			return true, "Namespace manipulation may be possible"
		}
	}

	return false, "Namespace escape not possible"
}

func (s *EscapeSimulator) readCaps() (string, error) {
	content, err := os.ReadFile("/proc/self/status")
	if err != nil {
		return "", err
	}

	for _, line := range strings.Split(string(content), "\n") {
		if strings.HasPrefix(line, "CapEff:") {
			return line, nil
		}
	}

	return "", fmt.Errorf("capabilities not found")
}

func (s *EscapeSimulator) emitEvent(eventType types.EventType, data map[string]interface{}) {
	if s.eventCb == nil {
		return
	}

	event := &types.BPFEvent{
		EventType: eventType,
		Timestamp: time.Now(),
		PID:       uint32(os.Getpid()),
		PPID:      uint32(os.Getppid()),
		UID:       uint32(os.Getuid()),
		GID:       uint32(os.Getgid()),
		Comm:      "escape-sim",
	}

	if v, ok := data["mount_source"].(string); ok {
		event.MountSource = v
	}
	if v, ok := data["mount_target"].(string); ok {
		event.MountTarget = v
	}
	if v, ok := data["fs_type"].(string); ok {
		event.FSType = v
	}
	if v, ok := data["file_name"].(string); ok {
		event.FileName = v
	}
	if v, ok := data["syscall_name"].(string); ok {
		event.SyscallName = v
	}
	if v, ok := data["comm"].(string); ok {
		event.Comm = v
	}

	s.eventCb(event)
}

func (s *EscapeSimulator) GetResults() map[string]*SimulationResult {
	s.mu.Lock()
	defer s.mu.Unlock()

	results := make(map[string]*SimulationResult)
	for k, v := range s.results {
		results[k] = v
	}
	return results
}

func (s *EscapeSimulator) GetSuccessfulEscapes() []*SimulationResult {
	s.mu.Lock()
	defer s.mu.Unlock()

	var escapes []*SimulationResult
	for _, result := range s.results {
		if result.Success {
			escapes = append(escapes, result)
		}
	}
	return escapes
}
