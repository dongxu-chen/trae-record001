package protection

import (
	"bufio"
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/security/container-escape-detector/pkg/types"
)

type Config struct {
	Enabled             bool     `yaml:"enabled"`
	Mode                string   `yaml:"mode"`
	BlockedActions      []string `yaml:"blocked_actions"`
	AutoBlockSeverity   string   `yaml:"auto_block_severity"`
	NetworkIsolation    bool     `yaml:"network_isolation"`
	KillProcess         bool     `yaml:"kill_process"`
	QuarantineContainer bool     `yaml:"quarantine_container"`
	WhitelistPIDs       []int    `yaml:"whitelist_pids"`
	AlertOnlyRules      []string `yaml:"alert_only_rules"`
}

type Manager struct {
	config            *Config
	logger            *logrus.Logger
	mu                sync.RWMutex
	blockedProcesses  map[int]BlockedProcess
	quarantinedContainers map[string]QuarantineInfo
	netIsolatedPIDs   map[int]bool
	stopChan          chan struct{}
	wg                sync.WaitGroup
	running           bool
}

type BlockedProcess struct {
	PID          int
	Comm         string
	RuleID       string
	Reason       string
	BlockedAt    time.Time
	BlockAction  string
	ContainerID  string
}

type QuarantineInfo struct {
	ContainerID   string
	ContainerName string
	Reason        string
	QuarantinedAt time.Time
	Actions       []string
}

type BlockAction int

const (
	ActionKill BlockAction = iota
	ActionNetworkIsolate
	ActionQuarantine
	ActionThrottle
)

func NewManager(logger *logrus.Logger, config *Config) *Manager {
	if config == nil {
		config = &Config{
			Enabled:             false,
			Mode:                "monitor",
			AutoBlockSeverity:   "HIGH",
			NetworkIsolation:    true,
			KillProcess:         true,
			QuarantineContainer: false,
		}
	}

	return &Manager{
		config:                config,
		logger:                logger,
		blockedProcesses:      make(map[int]BlockedProcess),
		quarantinedContainers: make(map[string]QuarantineInfo),
		netIsolatedPIDs:       make(map[int]bool),
		stopChan:              make(chan struct{}),
	}
}

func (m *Manager) Start() error {
	if !m.config.Enabled {
		m.logger.Info("Protection manager disabled")
		return nil
	}

	m.mu.Lock()
	if m.running {
		m.mu.Unlock()
		return fmt.Errorf("protection manager already running")
	}
	m.running = true
	m.mu.Unlock()

	m.wg.Add(1)
	go m.cleanupLoop()

	m.logger.Infof("Protection manager started in %s mode", m.config.Mode)
	m.logger.Infof("Auto-block severity: %s, Kill: %v, NetIsolation: %v, Quarantine: %v",
		m.config.AutoBlockSeverity, m.config.KillProcess, m.config.NetworkIsolation, m.config.QuarantineContainer)

	return nil
}

func (m *Manager) Stop() {
	m.mu.Lock()
	if !m.running {
		m.mu.Unlock()
		return
	}
	m.running = false
	m.mu.Unlock()

	close(m.stopChan)
	m.wg.Wait()

	m.logger.Info("Protection manager stopped")
}

func (m *Manager) EvaluateAlert(alert *types.Alert, container *types.ContainerInfo) *ProtectionAction {
	if !m.config.Enabled {
		return nil
	}

	if !m.shouldBlock(alert) {
		return nil
	}

	action := &ProtectionAction{
		RuleID:       alert.RuleID,
		AlertID:      alert.ID,
		ProcessPID:   alert.ProcessPID,
		ProcessComm:  alert.ProcessComm,
		ContainerID:  alert.ContainerID,
		Reason:       alert.Description,
		Severity:     alert.Severity,
		TriggeredAt:  time.Now(),
	}

	if container != nil {
		action.ContainerName = container.Name
	}

	m.determineActions(action, alert, container)

	return action
}

func (m *Manager) shouldBlock(alert *types.Alert) bool {
	severityThreshold := m.getSeverityThreshold(m.config.AutoBlockSeverity)
	alertSeverity := m.getSeverityLevel(alert.Severity)

	if alertSeverity < severityThreshold {
		return false
	}

	for _, ruleID := range m.config.AlertOnlyRules {
		if alert.RuleID == ruleID {
			return false
		}
	}

	for _, blocked := range m.config.BlockedActions {
		if strings.Contains(strings.ToLower(alert.Description), strings.ToLower(blocked)) {
			return true
		}
	}

	return true
}

func (m *Manager) determineActions(action *ProtectionAction, alert *types.Alert, container *types.ContainerInfo) {
	severity := alert.Severity

	switch severity {
	case types.RiskCritical:
		if m.config.KillProcess {
			action.Actions = append(action.Actions, ActionKill)
		}
		if m.config.QuarantineContainer {
			action.Actions = append(action.Actions, ActionQuarantine)
		}
		if m.config.NetworkIsolation {
			action.Actions = append(action.Actions, ActionNetworkIsolate)
		}

	case types.RiskHigh:
		if m.config.KillProcess {
			action.Actions = append(action.Actions, ActionKill)
		}
		if m.config.NetworkIsolation {
			action.Actions = append(action.Actions, ActionNetworkIsolate)
		}

	case types.RiskMedium:
		action.Actions = append(action.Actions, ActionThrottle)

	default:
	}
}

func (m *Manager) ExecuteAction(action *ProtectionAction) error {
	if !m.config.Enabled || m.config.Mode == "monitor" {
		m.logger.Warnf("[MONITOR] Would execute protection actions for PID %d: %v",
			action.ProcessPID, action.Actions)
		return nil
	}

	var errors []string

	for _, act := range action.Actions {
		var err error
		switch act {
		case ActionKill:
			err = m.killProcess(action)
		case ActionNetworkIsolate:
			err = m.isolateNetwork(action)
		case ActionQuarantine:
			err = m.quarantineContainer(action)
		case ActionThrottle:
			err = m.throttleProcess(action)
		}

		if err != nil {
			errors = append(errors, fmt.Sprintf("%s: %v", act.String(), err))
		}
	}

	if len(errors) > 0 {
		return fmt.Errorf("some actions failed: %s", strings.Join(errors, "; "))
	}

	m.mu.Lock()
	m.blockedProcesses[action.ProcessPID] = BlockedProcess{
		PID:          action.ProcessPID,
		Comm:         action.ProcessComm,
		RuleID:       action.RuleID,
		Reason:       action.Reason,
		BlockedAt:    time.Now(),
		BlockAction:  action.String(),
		ContainerID:  action.ContainerID,
	}
	m.mu.Unlock()

	m.logger.Warnf("Protection actions executed for PID %d (%s): %v",
		action.ProcessPID, action.ProcessComm, action.Actions)

	return nil
}

func (m *Manager) killProcess(action *ProtectionAction) error {
	pid := action.ProcessPID
	if pid <= 0 {
		return fmt.Errorf("invalid PID: %d", pid)
	}

	for _, wp := range m.config.WhitelistPIDs {
		if wp == pid {
			return fmt.Errorf("PID %d is whitelisted", pid)
		}
	}

	proc, err := os.FindProcess(pid)
	if err != nil {
		return fmt.Errorf("failed to find process %d: %w", pid, err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := proc.Signal(syscall.SIGTERM); err != nil {
		m.logger.Warnf("SIGTERM to PID %d failed, trying SIGKILL: %v", pid, err)
	}

	select {
	case <-ctx.Done():
		if err := proc.Kill(); err != nil {
			return fmt.Errorf("failed to kill process %d: %w", pid, err)
		}
		m.logger.Infof("Process %d killed with SIGKILL after timeout", pid)
	case <-time.After(100 * time.Millisecond):
	}

	m.logger.Infof("Process %d (%s) terminated due to: %s", pid, action.ProcessComm, action.Reason)
	return nil
}

func (m *Manager) isolateNetwork(action *ProtectionAction) error {
	pid := action.ProcessPID
	if pid <= 0 {
		return fmt.Errorf("invalid PID: %d", pid)
	}

	m.mu.Lock()
	if m.netIsolatedPIDs[pid] {
		m.mu.Unlock()
		return fmt.Errorf("PID %d already network isolated", pid)
	}
	m.netIsolatedPIDs[pid] = true
	m.mu.Unlock()

	nsPath := fmt.Sprintf("/proc/%d/ns/net", pid)
	if _, err := os.Stat(nsPath); err != nil {
		return fmt.Errorf("network namespace not found for PID %d: %w", pid, err)
	}

	iptablesCmd := exec.Command("iptables", "-I", "OUTPUT", "-m", "owner", "--uid-owner", strconv.Itoa(pid), "-j", "DROP")
	if out, err := iptablesCmd.CombinedOutput(); err != nil {
		return fmt.Errorf("iptables rule failed: %s, %w", string(out), err)
	}

	m.logger.Infof("Network isolation applied to PID %d", pid)
	return nil
}

func (m *Manager) quarantineContainer(action *ProtectionAction) error {
	containerID := action.ContainerID
	if containerID == "" {
		return fmt.Errorf("no container ID provided")
	}

	m.mu.Lock()
	if _, exists := m.quarantinedContainers[containerID]; exists {
		m.mu.Unlock()
		return fmt.Errorf("container %s already quarantined", containerID[:12])
	}
	m.quarantinedContainers[containerID] = QuarantineInfo{
		ContainerID:   containerID,
		ContainerName: action.ContainerName,
		Reason:        action.Reason,
		QuarantinedAt: time.Now(),
		Actions:       []string{"network-block", "read-only"},
	}
	m.mu.Unlock()

	dockerCmd := exec.Command("docker", "update", "--cpu-quota", "10000", "--memory", "64m", containerID)
	if out, err := dockerCmd.CombinedOutput(); err != nil {
		m.logger.Warnf("Failed to limit container resources: %s", string(out))
	}

	netCmd := exec.Command("docker", "network", "disconnect", "bridge", containerID)
	if out, err := netCmd.CombinedOutput(); err != nil {
		m.logger.Warnf("Failed to disconnect network: %s", string(out))
	}

	m.logger.Warnf("Container %s quarantined due to: %s", containerID[:12], action.Reason)
	return nil
}

func (m *Manager) throttleProcess(action *ProtectionAction) error {
	pid := action.ProcessPID
	if pid <= 0 {
		return fmt.Errorf("invalid PID: %d", pid)
	}

	cpuCmd := exec.Command("cpulimit", "-p", strconv.Itoa(pid), "-l", "10", "-b")
	if out, err := cpuCmd.CombinedOutput(); err != nil {
		m.logger.Debugf("cpulimit not available, using nice: %s", string(out))
		niceCmd := exec.Command("renice", "+19", "-p", strconv.Itoa(pid))
		if out, err := niceCmd.CombinedOutput(); err != nil {
			return fmt.Errorf("renice failed: %s, %w", string(out), err)
		}
	}

	m.logger.Infof("Process %d throttled due to: %s", pid, action.Reason)
	return nil
}

func (m *Manager) cleanupLoop() {
	defer m.wg.Done()

	ticker := time.NewTicker(10 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-m.stopChan:
			return
		case <-ticker.C:
			m.cleanupOldRecords()
		}
	}
}

func (m *Manager) cleanupOldRecords() {
	cutoff := time.Now().Add(-1 * time.Hour)

	m.mu.Lock()
	defer m.mu.Unlock()

	for pid, blocked := range m.blockedProcesses {
		if blocked.BlockedAt.Before(cutoff) {
			delete(m.blockedProcesses, pid)
		}
	}

	for pid := range m.netIsolatedPIDs {
		if _, err := os.Stat(fmt.Sprintf("/proc/%d", pid)); os.IsNotExist(err) {
			delete(m.netIsolatedPIDs, pid)
		}
	}
}

func (m *Manager) getSeverityThreshold(level string) int {
	levels := map[string]int{
		"INFO":     0,
		"LOW":      1,
		"MEDIUM":   2,
		"HIGH":     3,
		"CRITICAL": 4,
	}
	if l, ok := levels[strings.ToUpper(level)]; ok {
		return l
	}
	return 3
}

func (m *Manager) getSeverityLevel(level types.RiskLevel) int {
	levels := map[types.RiskLevel]int{
		types.RiskInfo:     0,
		types.RiskLow:      1,
		types.RiskMedium:   2,
		types.RiskHigh:     3,
		types.RiskCritical: 4,
	}
	if l, ok := levels[level]; ok {
		return l
	}
	return 0
}

func (m *Manager) GetBlockedProcesses() []BlockedProcess {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]BlockedProcess, 0, len(m.blockedProcesses))
	for _, p := range m.blockedProcesses {
		result = append(result, p)
	}
	return result
}

func (m *Manager) GetQuarantinedContainers() []QuarantineInfo {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]QuarantineInfo, 0, len(m.quarantinedContainers))
	for _, c := range m.quarantinedContainers {
		result = append(result, c)
	}
	return result
}

func (m *Manager) UnquarantineContainer(containerID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.quarantinedContainers[containerID]; !exists {
		return fmt.Errorf("container %s not quarantined", containerID[:12])
	}

	delete(m.quarantinedContainers, containerID)

	netCmd := exec.Command("docker", "network", "connect", "bridge", containerID)
	if out, err := netCmd.CombinedOutput(); err != nil {
		m.logger.Warnf("Failed to reconnect network: %s", string(out))
	}

	dockerCmd := exec.Command("docker", "update", "--cpu-quota", "-1", "--memory", "-1", containerID)
	if out, err := dockerCmd.CombinedOutput(); err != nil {
		m.logger.Warnf("Failed to restore container resources: %s", string(out))
	}

	m.logger.Infof("Container %s removed from quarantine", containerID[:12])
	return nil
}

type ProtectionAction struct {
	RuleID       string
	AlertID      string
	ProcessPID   int
	ProcessComm  string
	ContainerID  string
	ContainerName string
	Reason       string
	Severity     types.RiskLevel
	TriggeredAt  time.Time
	Actions      []BlockAction
}

func (a BlockAction) String() string {
	switch a {
	case ActionKill:
		return "kill"
	case ActionNetworkIsolate:
		return "network_isolate"
	case ActionQuarantine:
		return "quarantine"
	case ActionThrottle:
		return "throttle"
	default:
		return "unknown"
	}
}

func (a *ProtectionAction) String() string {
	var actions []string
	for _, act := range a.Actions {
		actions = append(actions, act.String())
	}
	return fmt.Sprintf("ProtectionAction[PID=%d, Actions=[%s], Reason=%s]",
		a.ProcessPID, strings.Join(actions, ","), a.Reason)
}

func GetProcessTree(pid int) []int {
	var tree []int
	current := pid

	for current > 1 {
		tree = append(tree, current)
		parent, err := getPPID(current)
		if err != nil || parent == current {
			break
		}
		current = parent
	}

	for i, j := 0, len(tree)-1; i < j; i, j = i+1, j-1 {
		tree[i], tree[j] = tree[j], tree[i]
	}

	return tree
}

func getPPID(pid int) (int, error) {
	statPath := filepath.Join("/proc", strconv.Itoa(pid), "stat")
	content, err := os.ReadFile(statPath)
	if err != nil {
		return 0, err
	}

	scanner := bufio.NewScanner(bytes.NewReader(content))
	for scanner.Scan() {
		fields := strings.Fields(scanner.Text())
		if len(fields) >= 4 {
			ppid, err := strconv.Atoi(fields[3])
			if err != nil {
				return 0, err
			}
			return ppid, nil
		}
	}

	return 0, fmt.Errorf("failed to parse ppid")
}
