package remediation

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	"container-security-monitor/pkg/config"
	"container-security-monitor/pkg/detector"
)

type ActionType string

const (
	ActionNetworkIsolate ActionType = "network_isolate"
	ActionProcessKill    ActionType = "process_kill"
	ActionContainerStop  ActionType = "container_stop"
	ActionContainerPause ActionType = "container_pause"
)

type RemediationAction struct {
	Type        ActionType
	ContainerID string
	PID         uint32
	RuleName    string
	Severity    string
	Timestamp   time.Time
	Status      string
	Error       string
}

type RemediationManager struct {
	mu           sync.RWMutex
	cfg          config.RemediationConfig
	quarantined  map[string]bool
	actions      []*RemediationAction
	cancelFuncs  map[string]context.CancelFunc
	running      bool
}

func NewRemediationManager(cfg config.RemediationConfig) *RemediationManager {
	return &RemediationManager{
		cfg:         cfg,
		quarantined: make(map[string]bool),
		actions:     make([]*RemediationAction, 0),
		cancelFuncs: make(map[string]context.CancelFunc),
	}
}

func (rm *RemediationManager) Start() {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	rm.running = true

	if rm.cfg.NetworkIsolate {
		if err := rm.initQuarantineDir(); err != nil {
			logrus.Errorf("Failed to initialize quarantine directory: %v", err)
		}
	}

	logrus.Infof("Remediation manager started (auto_block=%v, network_isolate=%v)",
		rm.cfg.AutoBlock, rm.cfg.NetworkIsolate)
}

func (rm *RemediationManager) Stop() {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	rm.running = false

	for containerID, cancel := range rm.cancelFuncs {
		cancel()
		delete(rm.cancelFuncs, containerID)
		logrus.Infof("Cancelled remediation for container: %s", containerID)
	}

	logrus.Info("Remediation manager stopped")
}

func (rm *RemediationManager) initQuarantineDir() error {
	if rm.cfg.QuarantineDir == "" {
		return nil
	}

	return os.MkdirAll(rm.cfg.QuarantineDir, 0750)
}

func (rm *RemediationManager) ShouldBlock(alert *detector.SecurityAlert) bool {
	if !rm.cfg.AutoBlock {
		return false
	}

	severityOrder := map[string]int{
		"critical": 4,
		"high":     3,
		"medium":   2,
		"low":      1,
	}

	threshold := severityOrder[rm.cfg.BlockSeverity]
	alertSeverity := severityOrder[alert.Severity]

	if alertSeverity >= threshold {
		return true
	}

	for _, rule := range rm.cfg.BlockRules {
		if rule == alert.RuleName {
			return true
		}
	}

	return false
}

func (rm *RemediationManager) ProcessAlert(alert *detector.SecurityAlert) *RemediationAction {
	if !rm.ShouldBlock(alert) {
		return nil
	}

	rm.mu.Lock()
	if rm.quarantined[alert.ContainerID] {
		rm.mu.Unlock()
		logrus.Debugf("Container %s already quarantined", alert.ContainerID)
		return nil
	}
	rm.quarantined[alert.ContainerID] = true
	rm.mu.Unlock()

	action := &RemediationAction{
		Type:        ActionNetworkIsolate,
		ContainerID: alert.ContainerID,
		PID:         alert.PID,
		RuleName:    alert.RuleName,
		Severity:    alert.Severity,
		Timestamp:   time.Now(),
		Status:      "pending",
	}

	if rm.cfg.NetworkIsolate {
		go rm.executeNetworkIsolation(action)
	}

	rm.mu.Lock()
	rm.actions = append(rm.actions, action)
	rm.mu.Unlock()

	return action
}

func (rm *RemediationManager) executeNetworkIsolation(action *RemediationAction) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	rm.mu.Lock()
	rm.cancelFuncs[action.ContainerID] = cancel
	rm.mu.Unlock()

	action.Status = "executing"

	logrus.Warnf("Isolating container %s due to: %s", action.ContainerID, action.RuleName)

	if err := rm.isolateContainerNetwork(action.ContainerID); err != nil {
		action.Status = "failed"
		action.Error = err.Error()
		logrus.Errorf("Failed to isolate container %s: %v", action.ContainerID, err)
		return
	}

	action.Status = "completed"
	logrus.Infof("Container %s network isolated successfully", action.ContainerID)
}

func (rm *RemediationManager) isolateContainerNetwork(containerID string) error {
	if containerID == "" {
		return fmt.Errorf("empty container ID")
	}

	fullID, err := rm.getFullContainerID(containerID)
	if err != nil {
		logrus.Warnf("Cannot get full container ID for %s: %v, using partial", containerID, err)
		fullID = containerID
	}

	netnsPath := fmt.Sprintf("/var/run/netns/%s", fullID)
	if _, err := os.Stat(netnsPath); err == nil {
		if err := rm.createNetworkBlockRules(fullID); err != nil {
			return fmt.Errorf("failed to create network block rules: %v", err)
		}
		return nil
	}

	return rm.isolateViaIPTables(fullID)
}

func (rm *RemediationManager) getFullContainerID(partialID string) (string, error) {
	cmd := exec.Command("docker", "ps", "-q", "--no-trunc")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to list containers: %v", err)
	}

	containers := strings.Split(string(output), "\n")
	for _, id := range containers {
		if strings.HasPrefix(id, partialID) {
			return id, nil
		}
	}

	return "", fmt.Errorf("container not found: %s", partialID)
}

func (rm *RemediationManager) createNetworkBlockRules(containerID string) error {
	blockScript := fmt.Sprintf(`
#!/bin/bash
# Block all inbound and outbound traffic for container %s
iptables -I DOCKER-USER -i %s -j DROP
iptables -I DOCKER-USER -o %s -j DROP
iptables -I FORWARD -i %s -j DROP
iptables -I FORWARD -o %s -j DROP
`, containerID, containerID, containerID, containerID, containerID)

	scriptPath := fmt.Sprintf("%s/block_%s.sh", rm.cfg.QuarantineDir, containerID)
	if err := os.WriteFile(scriptPath, []byte(blockScript), 0700); err != nil {
		return fmt.Errorf("failed to write block script: %v", err)
	}

	cmd := exec.Command("bash", scriptPath)
	cmdOutput, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to execute block script: %v, output: %s", err, string(cmdOutput))
	}

	logrus.Infof("Network block rules applied for container %s", containerID)
	return nil
}

func (rm *RemediationManager) isolateViaIPTables(containerID string) error {
	cmd := exec.Command("docker", "inspect", "-f", "{{.NetworkSettings.IPAddress}}", containerID)
	ipOutput, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("failed to get container IP: %v", err)
	}

	containerIP := strings.TrimSpace(string(ipOutput))
	if containerIP == "" || containerIP == "<no value>" {
		return fmt.Errorf("container has no IP address")
	}

	rules := []string{
		fmt.Sprintf("iptables -I INPUT -s %s -j DROP", containerIP),
		fmt.Sprintf("iptables -I OUTPUT -d %s -j DROP", containerIP),
		fmt.Sprintf("iptables -I FORWARD -s %s -j DROP", containerIP),
		fmt.Sprintf("iptables -I FORWARD -d %s -j DROP", containerIP),
	}

	for _, rule := range rules {
		cmd := exec.Command("bash", "-c", rule)
		if output, err := cmd.CombinedOutput(); err != nil {
			logrus.Warnf("Failed to apply rule '%s': %v, output: %s", rule, err, string(output))
		}
	}

	quarantineFile := fmt.Sprintf("%s/quarantine_%s_%s.txt",
		rm.cfg.QuarantineDir, containerID, time.Now().Format("20060102_150405"))

	quarantineInfo := fmt.Sprintf(`
Container ID: %s
Container IP: %s
Quarantined at: %s
Rules applied:
%s
`, containerID, containerIP, time.Now().Format(time.RFC3339), strings.Join(rules, "\n"))

	if err := os.WriteFile(quarantineFile, []byte(quarantineInfo), 0600); err != nil {
		logrus.Warnf("Failed to write quarantine info: %v", err)
	}

	logrus.Infof("Container %s (%s) network isolated via iptables", containerID, containerIP)
	return nil
}

func (rm *RemediationManager) KillProcess(pid uint32) error {
	process, err := os.FindProcess(int(pid))
	if err != nil {
		return fmt.Errorf("failed to find process %d: %v", pid, err)
	}

	if err := process.Kill(); err != nil {
		return fmt.Errorf("failed to kill process %d: %v", pid, err)
	}

	logrus.Infof("Process %d killed successfully", pid)
	return nil
}

func (rm *RemediationManager) StopContainer(containerID string) error {
	if containerID == "" {
		return fmt.Errorf("empty container ID")
	}

	cmd := exec.Command("docker", "stop", "-t", "5", containerID)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to stop container %s: %v, output: %s",
			containerID, err, string(output))
	}

	logrus.Infof("Container %s stopped successfully", containerID)
	return nil
}

func (rm *RemediationManager) PauseContainer(containerID string) error {
	if containerID == "" {
		return fmt.Errorf("empty container ID")
	}

	cmd := exec.Command("docker", "pause", containerID)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to pause container %s: %v, output: %s",
			containerID, err, string(output))
	}

	logrus.Infof("Container %s paused successfully", containerID)
	return nil
}

func (rm *RemediationManager) ReleaseContainer(containerID string) error {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	if !rm.quarantined[containerID] {
		return fmt.Errorf("container %s is not quarantined", containerID)
	}

	fullID, err := rm.getFullContainerID(containerID)
	if err == nil {
		unblockScript := fmt.Sprintf(`
#!/bin/bash
iptables -D DOCKER-USER -i %s -j DROP 2>/dev/null || true
iptables -D DOCKER-USER -o %s -j DROP 2>/dev/null || true
iptables -D FORWARD -i %s -j DROP 2>/dev/null || true
iptables -D FORWARD -o %s -j DROP 2>/dev/null || true
`, fullID, fullID, fullID, fullID)

		scriptPath := fmt.Sprintf("%s/unblock_%s.sh", rm.cfg.QuarantineDir, fullID)
		os.WriteFile(scriptPath, []byte(unblockScript), 0700)
		exec.Command("bash", scriptPath).Run()
	}

	delete(rm.quarantined, containerID)
	if cancel, ok := rm.cancelFuncs[containerID]; ok {
		cancel()
		delete(rm.cancelFuncs, containerID)
	}

	logrus.Infof("Container %s released from quarantine", containerID)
	return nil
}

func (rm *RemediationManager) IsQuarantined(containerID string) bool {
	rm.mu.RLock()
	defer rm.mu.RUnlock()
	return rm.quarantined[containerID]
}

func (rm *RemediationManager) GetQuarantinedContainers() []string {
	rm.mu.RLock()
	defer rm.mu.RUnlock()

	var containers []string
	for id := range rm.quarantined {
		containers = append(containers, id)
	}
	return containers
}

func (rm *RemediationManager) GetActions() []*RemediationAction {
	rm.mu.RLock()
	defer rm.mu.RUnlock()
	return rm.actions
}

func (rm *RemediationManager) GetConfig() config.RemediationConfig {
	return rm.cfg
}

func (rm *RemediationManager) UpdateConfig(cfg config.RemediationConfig) {
	rm.mu.Lock()
	defer rm.mu.Unlock()
	rm.cfg = cfg
}
