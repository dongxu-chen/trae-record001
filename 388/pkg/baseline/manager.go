package baseline

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	"container-security-monitor/pkg/ebpf"
)

type LearningMode int

const (
	ModeLearning LearningMode = iota
	ModeDetecting
	ModeHybrid
)

func (m LearningMode) String() string {
	return []string{"learning", "detecting", "hybrid"}[m]
}

type ProcessProfile struct {
	Comm          string            `json:"comm"`
	Count         int64             `json:"count"`
	UIDSet        map[uint32]bool   `json:"uid_set"`
	ParentSet     map[string]bool   `json:"parent_set"`
	FirstSeen     time.Time         `json:"first_seen"`
	LastSeen      time.Time         `json:"last_seen"`
	AvgInterval   float64           `json:"avg_interval"`
	LastTimestamp int64             `json:"-"`
}

type FileProfile struct {
	PathPattern string `json:"path_pattern"`
	Count       int64  `json:"count"`
	AccessTypes map[uint32]bool `json:"access_types"`
	FirstSeen   time.Time `json:"first_seen"`
	LastSeen    time.Time `json:"last_seen"`
}

type NetworkProfile struct {
	IPSet     map[string]bool `json:"ip_set"`
	PortSet   map[uint16]bool `json:"port_set"`
	Count     int64           `json:"count"`
	FirstSeen time.Time       `json:"first_seen"`
	LastSeen  time.Time       `json:"last_seen"`
}

type ContainerBaseline struct {
	ContainerID   string                   `json:"container_id"`
	ContainerName string                   `json:"container_name"`
	CreatedAt     time.Time                `json:"created_at"`
	UpdatedAt     time.Time                `json:"updated_at"`
	Processes     map[string]*ProcessProfile `json:"processes"`
	Files         map[string]*FileProfile    `json:"files"`
	Networks      map[string]*NetworkProfile `json:"networks"`
	TotalEvents   int64                    `json:"total_events"`
	DeviationScore float64                 `json:"deviation_score"`
}

type BaselineManager struct {
	mu              sync.RWMutex
	mode            LearningMode
	learningPeriod  time.Duration
	containers      map[string]*ContainerBaseline
	baselineDir     string
	learningStart   map[string]time.Time
	deviationThreshold float64
}

type AnomalyEvent struct {
	ContainerID   string      `json:"container_id"`
	EventType     string      `json:"event_type"`
	Description   string      `json:"description"`
	Deviation     float64     `json:"deviation"`
	CurrentValue  interface{} `json:"current_value"`
	BaselineInfo  interface{} `json:"baseline_info"`
	Timestamp     time.Time   `json:"timestamp"`
	Severity      string      `json:"severity"`
}

func NewBaselineManager(mode LearningMode, learningPeriod time.Duration, baselineDir string) *BaselineManager {
	if baselineDir == "" {
		baselineDir = "/var/run/csm/baselines"
	}

	bm := &BaselineManager{
		mode:               mode,
		learningPeriod:     learningPeriod,
		baselineDir:        baselineDir,
		containers:         make(map[string]*ContainerBaseline),
		learningStart:      make(map[string]time.Time),
		deviationThreshold: 0.3,
	}

	if err := os.MkdirAll(baselineDir, 0750); err != nil {
		logrus.Warnf("Failed to create baseline directory: %v", err)
	}

	return bm
}

func (bm *BaselineManager) SetMode(mode LearningMode) {
	bm.mu.Lock()
	defer bm.mu.Unlock()
	bm.mode = mode
	logrus.Infof("Baseline manager mode changed to: %s", mode.String())
}

func (bm *BaselineManager) GetMode() LearningMode {
	bm.mu.RLock()
	defer bm.mu.RUnlock()
	return bm.mode
}

func (bm *BaselineManager) ProcessEvent(event interface{}) []*AnomalyEvent {
	bm.mu.Lock()
	defer bm.mu.Unlock()

	var anomalies []*AnomalyEvent

	switch e := event.(type) {
	case ebpf.ProcessEvent:
		anomalies = bm.processProcessEvent(e)
	case ebpf.FileEvent:
		anomalies = bm.processFileEvent(e)
	case ebpf.NetworkEvent:
		anomalies = bm.processNetworkEvent(e)
	}

	return anomalies
}

func (bm *BaselineManager) processProcessEvent(event ebpf.ProcessEvent) []*AnomalyEvent {
	containerID := bytesToString(event.ContainerID[:])
	if containerID == "" {
		return nil
	}

	baseline := bm.getOrCreateBaseline(containerID)
	comm := bytesToString(event.Comm[:])

	profile, exists := baseline.Processes[comm]
	if !exists {
		profile = &ProcessProfile{
			Comm:      comm,
			UIDSet:    make(map[uint32]bool),
			ParentSet: make(map[string]bool),
			FirstSeen: time.Now(),
		}
		baseline.Processes[comm] = profile

		if bm.mode != ModeLearning {
			return []*AnomalyEvent{{
				ContainerID:  containerID,
				EventType:    "new_process",
				Description:  fmt.Sprintf("New process detected: %s (never seen in baseline)", comm),
				Deviation:    1.0,
				CurrentValue: comm,
				Timestamp:    time.Now(),
				Severity:     "medium",
			}}
		}
	}

	profile.Count++
	profile.UIDSet[event.UID] = true
	profile.LastSeen = time.Now()
	baseline.TotalEvents++
	baseline.UpdatedAt = time.Now()

	if bm.mode == ModeDetecting || bm.mode == ModeHybrid {
		return bm.checkProcessAnomalies(containerID, comm, event, profile)
	}

	return nil
}

func (bm *BaselineManager) checkProcessAnomalies(containerID, comm string, event ebpf.ProcessEvent, profile *ProcessProfile) []*AnomalyEvent {
	var anomalies []*AnomalyEvent

	if event.UID == 0 && !profile.UIDSet[0] && profile.Count > 10 {
		anomalies = append(anomalies, &AnomalyEvent{
			ContainerID:  containerID,
			EventType:    "privilege_escalation",
			Description:  fmt.Sprintf("Process %s running as root (never seen before)", comm),
			Deviation:    0.9,
			CurrentValue: event.UID,
			BaselineInfo: fmt.Sprintf("Known UIDs: %v", profile.UIDSet),
			Timestamp:    time.Now(),
			Severity:     "critical",
		})
	}

	return anomalies
}

func (bm *BaselineManager) processFileEvent(event ebpf.FileEvent) []*AnomalyEvent {
	containerID := bytesToString(event.ContainerID[:])
	if containerID == "" {
		return nil
	}

	baseline := bm.getOrCreateBaseline(containerID)
	filename := bytesToString(event.Filename[:])
	pathPattern := normalizeFilePath(filename)

	profile, exists := baseline.Files[pathPattern]
	if !exists {
		profile = &FileProfile{
			PathPattern: pathPattern,
			AccessTypes: make(map[uint32]bool),
			FirstSeen:   time.Now(),
		}
		baseline.Files[pathPattern] = profile

		if bm.mode != ModeLearning && isSuspiciousPath(filename) {
			return []*AnomalyEvent{{
				ContainerID:  containerID,
				EventType:    "new_file_access",
				Description:  fmt.Sprintf("New file access: %s (never seen in baseline)", filename),
				Deviation:    0.8,
				CurrentValue: filename,
				Timestamp:    time.Now(),
				Severity:     "high",
			}}
		}
	}

	profile.Count++
	profile.AccessTypes[event.EventType] = true
	profile.LastSeen = time.Now()
	baseline.TotalEvents++
	baseline.UpdatedAt = time.Now()

	return nil
}

func (bm *BaselineManager) processNetworkEvent(event ebpf.NetworkEvent) []*AnomalyEvent {
	containerID := bytesToString(event.ContainerID[:])
	if containerID == "" {
		return nil
	}

	baseline := bm.getOrCreateBaseline(containerID)
	daddr := intToIP(event.Daddr)

	profile, exists := baseline.Networks["outbound"]
	if !exists {
		profile = &NetworkProfile{
			IPSet:   make(map[string]bool),
			PortSet: make(map[uint16]bool),
			FirstSeen: time.Now(),
		}
		baseline.Networks["outbound"] = profile
	}

	ipKnown := profile.IPSet[daddr]
	portKnown := profile.PortSet[event.Dport]

	profile.IPSet[daddr] = true
	profile.PortSet[event.Dport] = true
	profile.Count++
	profile.LastSeen = time.Now()
	baseline.TotalEvents++
	baseline.UpdatedAt = time.Now()

	if bm.mode == ModeDetecting || bm.mode == ModeHybrid {
		if !ipKnown && !isPrivateIP(daddr) {
			return []*AnomalyEvent{{
				ContainerID:  containerID,
				EventType:    "new_outbound_ip",
				Description:  fmt.Sprintf("New outbound connection: %s:%d (first time connecting to this IP)", daddr, event.Dport),
				Deviation:    0.6,
				CurrentValue: fmt.Sprintf("%s:%d", daddr, event.Dport),
				BaselineInfo: fmt.Sprintf("Known IPs count: %d", len(profile.IPSet)-1),
				Timestamp:    time.Now(),
				Severity:     "medium",
			}}
		}

		if !portKnown && isSuspiciousPort(event.Dport) {
			return []*AnomalyEvent{{
				ContainerID:  containerID,
				EventType:    "suspicious_port",
				Description:  fmt.Sprintf("Connection to suspicious port: %d (never seen before)", event.Dport),
				Deviation:    0.7,
				CurrentValue: event.Dport,
				Timestamp:    time.Now(),
				Severity:     "high",
			}}
		}
	}

	return nil
}

func (bm *BaselineManager) getOrCreateBaseline(containerID string) *ContainerBaseline {
	baseline, exists := bm.containers[containerID]
	if !exists {
		baseline = &ContainerBaseline{
			ContainerID: containerID,
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
			Processes:   make(map[string]*ProcessProfile),
			Files:       make(map[string]*FileProfile),
			Networks:    make(map[string]*NetworkProfile),
		}
		bm.containers[containerID] = baseline
		bm.learningStart[containerID] = time.Now()

		logrus.Infof("Created new baseline for container: %s", containerID)
	}
	return baseline
}

func (bm *BaselineManager) SaveBaseline(containerID string) error {
	bm.mu.RLock()
	baseline, exists := bm.containers[containerID]
	bm.mu.RUnlock()

	if !exists {
		return fmt.Errorf("baseline not found for container: %s", containerID)
	}

	filename := filepath.Join(bm.baselineDir, fmt.Sprintf("%s.json", containerID))
	data, err := json.MarshalIndent(baseline, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filename, data, 0640)
}

func (bm *BaselineManager) LoadBaseline(containerID string) error {
	filename := filepath.Join(bm.baselineDir, fmt.Sprintf("%s.json", containerID))
	data, err := os.ReadFile(filename)
	if err != nil {
		return err
	}

	var baseline ContainerBaseline
	if err := json.Unmarshal(data, &baseline); err != nil {
		return err
	}

	bm.mu.Lock()
	bm.containers[containerID] = &baseline
	bm.mu.Unlock()

	logrus.Infof("Loaded baseline for container: %s", containerID)
	return nil
}

func (bm *BaselineManager) GetBaseline(containerID string) (*ContainerBaseline, bool) {
	bm.mu.RLock()
	defer bm.mu.RUnlock()
	baseline, exists := bm.containers[containerID]
	return baseline, exists
}

func (bm *BaselineManager) GetAllBaselines() map[string]*ContainerBaseline {
	bm.mu.RLock()
	defer bm.mu.RUnlock()

	result := make(map[string]*ContainerBaseline)
	for k, v := range bm.containers {
		result[k] = v
	}
	return result
}

func (bm *BaselineManager) IsLearningComplete(containerID string) bool {
	bm.mu.RLock()
	defer bm.mu.RUnlock()

	start, exists := bm.learningStart[containerID]
	if !exists {
		return false
	}

	return time.Since(start) > bm.learningPeriod
}

func (bm *BaselineManager) CalculateDeviationScore(containerID string) float64 {
	bm.mu.RLock()
	baseline, exists := bm.containers[containerID]
	bm.mu.RUnlock()

	if !exists || baseline.TotalEvents == 0 {
		return 0
	}

	newProcesses := 0
	for _, p := range baseline.Processes {
		if time.Since(p.FirstSeen) < bm.learningPeriod {
			newProcesses++
		}
	}

	processScore := float64(newProcesses) / math.Max(float64(len(baseline.Processes)), 1)
	fileScore := float64(len(baseline.Files)) / math.Max(baseline.TotalEvents/100, 1)
	networkScore := float64(len(baseline.Networks["outbound"].IPSet)) / math.Max(float64(baseline.Networks["outbound"].Count), 1)

	totalScore := (processScore*0.4 + fileScore*0.3 + networkScore*0.3)
	baseline.DeviationScore = totalScore

	return totalScore
}

func (bm *BaselineManager) GetLearningProgress(containerID string) float64 {
	bm.mu.RLock()
	start, exists := bm.learningStart[containerID]
	bm.mu.RUnlock()

	if !exists {
		return 0
	}

	elapsed := time.Since(start)
	progress := float64(elapsed) / float64(bm.learningPeriod)
	return math.Min(progress, 1.0)
}

func bytesToString(b []byte) string {
	for i, c := range b {
		if c == 0 {
			return string(b[:i])
		}
	}
	return string(b)
}

func normalizeFilePath(path string) string {
	if len(path) == 0 {
		return path
	}
	if path[0] != '/' {
		path = "/" + path
	}
	return path
}

func isSuspiciousPath(path string) bool {
	suspiciousPatterns := []string{
		"/etc/shadow", "/etc/passwd", "/root/", ".ssh/", ".kube/",
		"/var/run/docker.sock", "/proc/self/",
	}
	for _, p := range suspiciousPatterns {
		if len(path) >= len(p) && path[:len(p)] == p {
			return true
		}
	}
	return false
}

func isPrivateIP(ip string) bool {
	return len(ip) > 3 && (ip[:3] == "10." || ip[:7] == "192.168" || ip[:3] == "172")
}

func isSuspiciousPort(port uint16) bool {
	suspiciousPorts := []uint16{22, 23, 3389, 4444, 5555, 6666, 7777, 8888, 9999}
	for _, p := range suspiciousPorts {
		if port == p {
			return true
		}
	}
	return false
}
