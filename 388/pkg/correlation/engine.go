package correlation

import (
	"container/list"
	"fmt"
	"sync"
	"time"

	"github.com/sirupsen/logrus"

	"container-security-monitor/pkg/detector"
	"container-security-monitor/pkg/ebpf"
)

type EventType string

const (
	EventProcess EventType = "process"
	EventFile    EventType = "file"
	EventNetwork EventType = "network"
	EventAlert   EventType = "alert"
)

type CorrelatedEvent struct {
	ID          string                 `json:"id"`
	EventType   EventType              `json:"event_type"`
	Timestamp   time.Time              `json:"timestamp"`
	ContainerID string                 `json:"container_id"`
	PID         uint32                 `json:"pid"`
	PPID        uint32                 `json:"ppid"`
	Comm        string                 `json:"comm"`
	Data        map[string]interface{} `json:"data"`
	Alert       *detector.SecurityAlert `json:"alert,omitempty"`
}

type AttackPhase string

const (
	PhaseReconnaissance AttackPhase = "reconnaissance"
	PhaseInitialAccess  AttackPhase = "initial_access"
	PhaseExecution      AttackPhase = "execution"
	PhasePersistence    AttackPhase = "persistence"
	PhasePrivilegeEsc   AttackPhase = "privilege_escalation"
	PhaseDefenseEvasion AttackPhase = "defense_evasion"
	PhaseCredentialAccess AttackPhase = "credential_access"
	PhaseDiscovery      AttackPhase = "discovery"
	PhaseLateralMovement AttackPhase = "lateral_movement"
	PhaseCollection     AttackPhase = "collection"
	PhaseExfiltration   AttackPhase = "exfiltration"
	PhaseCommandControl AttackPhase = "command_control"
	PhaseImpact         AttackPhase = "impact"
)

type AttackStep struct {
	Phase     AttackPhase           `json:"phase"`
	Confidence float64              `json:"confidence"`
	Events    []*CorrelatedEvent    `json:"events"`
	Rules     []string              `json:"rules"`
	StartTime time.Time             `json:"start_time"`
	EndTime   time.Time             `json:"end_time"`
}

type AttackChain struct {
	ID              string           `json:"id"`
	ContainerID     string           `json:"container_id"`
	StartTime       time.Time        `json:"start_time"`
	EndTime         time.Time        `json:"end_time"`
	Steps           []*AttackStep    `json:"steps"`
	TotalConfidence float64          `json:"total_confidence"`
	Severity        string           `json:"severity"`
	Status          string           `json:"status"`
	Description     string           `json:"description"`
	Indicators      []string         `json:"indicators"`
	Remediation     string           `json:"remediation"`
}

type RulePattern struct {
	Name           string
	Phase          AttackPhase
	RuleNames      []string
	EventTypes     []EventType
	MinEvents      int
	TimeWindow     time.Duration
	Confidence     float64
	Description    string
}

type CorrelationEngine struct {
	mu              sync.RWMutex
	eventBuffer     map[string]*list.List
	containerChains map[string]*AttackChain
	maxBufferSize   int
	timeWindow      time.Duration
	patterns        []*RulePattern
}

func NewCorrelationEngine(timeWindow time.Duration, maxBufferSize int) *CorrelationEngine {
	ce := &CorrelationEngine{
		eventBuffer:     make(map[string]*list.List),
		containerChains: make(map[string]*AttackChain),
		maxBufferSize:   maxBufferSize,
		timeWindow:      timeWindow,
		patterns:        initPatterns(),
	}

	return ce
}

func initPatterns() []*RulePattern {
	return []*RulePattern{
		{
			Name:       "privilege_escalation_chain",
			Phase:      PhasePrivilegeEsc,
			RuleNames:  []string{"privilege_escalation", "suspicious_uid_change"},
			EventTypes: []EventType{EventProcess},
			MinEvents:  1,
			TimeWindow: 5 * time.Minute,
			Confidence: 0.9,
			Description: "Detected privilege escalation attempt",
		},
		{
			Name:       "credential_theft",
			Phase:      PhaseCredentialAccess,
			RuleNames:  []string{"etc_shadow_access", "ssh_key_access", "kubeconfig_access"},
			EventTypes: []EventType{EventFile},
			MinEvents:  1,
			TimeWindow: 2 * time.Minute,
			Confidence: 0.85,
			Description: "Credential theft attempt detected",
		},
		{
			Name:       "reverse_shell_chain",
			Phase:      PhaseCommandControl,
			RuleNames:  []string{"reverse_shell_detected", "suspicious_outbound_connection"},
			EventTypes: []EventType{EventProcess, EventNetwork},
			MinEvents:  2,
			TimeWindow: 1 * time.Minute,
			Confidence: 0.95,
			Description: "Reverse shell with C2 communication detected",
		},
		{
			Name:       "container_escape",
			Phase:      PhasePrivilegeEsc,
			RuleNames:  []string{"docker_socket_access", "sensitive_file_access"},
			EventTypes: []EventType{EventFile, EventProcess},
			MinEvents:  2,
			TimeWindow: 3 * time.Minute,
			Confidence: 0.9,
			Description: "Potential container escape attempt",
		},
		{
			Name:       "lateral_movement",
			Phase:      PhaseLateralMovement,
			RuleNames:  []string{"outbound_ssh_connection", "suspicious_high_port_connection"},
			EventTypes: []EventType{EventNetwork},
			MinEvents:  2,
			TimeWindow: 5 * time.Minute,
			Confidence: 0.75,
			Description: "Potential lateral movement detected",
		},
		{
			Name:       "data_exfiltration",
			Phase:      PhaseExfiltration,
			RuleNames:  []string{"suspicious_outbound_connection", "tor_network_connection"},
			EventTypes: []EventType{EventNetwork, EventFile},
			MinEvents:  2,
			TimeWindow: 10 * time.Minute,
			Confidence: 0.8,
			Description: "Potential data exfiltration detected",
		},
		{
			Name:       "malware_execution",
			Phase:      PhaseExecution,
			RuleNames:  []string{"crypto_miner_detection", "suspicious_shell_spawn"},
			EventTypes: []EventType{EventProcess},
			MinEvents:  1,
			TimeWindow: 1 * time.Minute,
			Confidence: 0.85,
			Description: "Malicious code execution detected",
		},
	}
}

func (ce *CorrelationEngine) ProcessEvent(event interface{}) []*AttackChain {
	ce.mu.Lock()
	defer ce.mu.Unlock()

	correlatedEvent := ce.toCorrelatedEvent(event)
	if correlatedEvent == nil {
		return nil
	}

	ce.addToBuffer(correlatedEvent)
	chains := ce.detectChains(correlatedEvent)

	return chains
}

func (ce *CorrelationEngine) toCorrelatedEvent(event interface{}) *CorrelatedEvent {
	id := fmt.Sprintf("evt_%d", time.Now().UnixNano())

	switch e := event.(type) {
	case ebpf.ProcessEvent:
		return &CorrelatedEvent{
			ID:          id,
			EventType:   EventProcess,
			Timestamp:   time.Now(),
			ContainerID: bytesToString(e.ContainerID[:]),
			PID:         e.PID,
			PPID:        e.PPID,
			Comm:        bytesToString(e.Comm[:]),
			Data: map[string]interface{}{
				"uid": e.UID,
				"gid": e.GID,
			},
		}
	case ebpf.FileEvent:
		return &CorrelatedEvent{
			ID:          id,
			EventType:   EventFile,
			Timestamp:   time.Now(),
			ContainerID: bytesToString(e.ContainerID[:]),
			PID:         e.PID,
			Comm:        bytesToString(e.Comm[:]),
			Data: map[string]interface{}{
				"filename": bytesToString(e.Filename[:]),
				"mode":     e.Mode,
			},
		}
	case ebpf.NetworkEvent:
		return &CorrelatedEvent{
			ID:          id,
			EventType:   EventNetwork,
			Timestamp:   time.Now(),
			ContainerID: bytesToString(e.ContainerID[:]),
			PID:         e.PID,
			Comm:        bytesToString(e.Comm[:]),
			Data: map[string]interface{}{
				"saddr":  intToIP(e.Saddr),
				"daddr":  intToIP(e.Daddr),
				"sport":  e.Sport,
				"dport":  e.Dport,
				"proto":  e.Protocol,
			},
		}
	case *detector.SecurityAlert:
		return &CorrelatedEvent{
			ID:          id,
			EventType:   EventAlert,
			Timestamp:   e.Timestamp,
			ContainerID: e.ContainerID,
			PID:         e.PID,
			PPID:        e.PPID,
			Comm:        e.Comm,
			Data:        e.Fields,
			Alert:       e,
		}
	}

	return nil
}

func (ce *CorrelationEngine) addToBuffer(event *CorrelatedEvent) {
	containerID := event.ContainerID
	if containerID == "" {
		return
	}

	if _, exists := ce.eventBuffer[containerID]; !exists {
		ce.eventBuffer[containerID] = list.New()
	}

	buffer := ce.eventBuffer[containerID]
	buffer.PushBack(event)

	if buffer.Len() > ce.maxBufferSize {
		oldest := buffer.Front()
		if oldest != nil {
			buffer.Remove(oldest)
		}
	}

	ce.cleanOldEvents(containerID)
}

func (ce *CorrelationEngine) cleanOldEvents(containerID string) {
	buffer, exists := ce.eventBuffer[containerID]
	if !exists {
		return
	}

	cutoffTime := time.Now().Add(-ce.timeWindow)
	for e := buffer.Front(); e != nil; {
		next := e.Next()
		evt := e.Value.(*CorrelatedEvent)
		if evt.Timestamp.Before(cutoffTime) {
			buffer.Remove(e)
		}
		e = next
	}
}

func (ce *CorrelationEngine) detectChains(event *CorrelatedEvent) []*AttackChain {
	containerID := event.ContainerID
	if containerID == "" {
		return nil
	}

	var chains []*AttackChain

	for _, pattern := range ce.patterns {
		if !ce.matchPattern(pattern, event) {
			continue
		}

		chain := ce.buildChain(containerID, pattern)
		if chain != nil {
			chains = append(chains, chain)

			if existing, exists := ce.containerChains[chain.ID]; exists {
				ce.mergeChains(existing, chain)
			} else {
				ce.containerChains[chain.ID] = chain
			}
		}
	}

	return chains
}

func (ce *CorrelationEngine) matchPattern(pattern *RulePattern, event *CorrelatedEvent) bool {
	if event.Alert == nil {
		return false
	}

	for _, ruleName := range pattern.RuleNames {
		if event.Alert.RuleName == ruleName {
			return true
		}
	}

	return false
}

func (ce *CorrelationEngine) buildChain(containerID string, pattern *RulePattern) *AttackChain {
	buffer, exists := ce.eventBuffer[containerID]
	if !exists {
		return nil
	}

	var matchingEvents []*CorrelatedEvent
	cutoffTime := time.Now().Add(-pattern.TimeWindow)

	for e := buffer.Front(); e != nil; e = e.Next() {
		evt := e.Value.(*CorrelatedEvent)
		if evt.Timestamp.Before(cutoffTime) {
			continue
		}

		for _, ruleName := range pattern.RuleNames {
			if evt.Alert != nil && evt.Alert.RuleName == ruleName {
				matchingEvents = append(matchingEvents, evt)
				break
			}
		}
	}

	if len(matchingEvents) < pattern.MinEvents {
		return nil
	}

	step := &AttackStep{
		Phase:     pattern.Phase,
		Confidence: pattern.Confidence,
		Events:    matchingEvents,
		StartTime: matchingEvents[0].Timestamp,
		EndTime:   matchingEvents[len(matchingEvents)-1].Timestamp,
	}
	for _, evt := range matchingEvents {
		if evt.Alert != nil {
			step.Rules = append(step.Rules, evt.Alert.RuleName)
		}
	}

	chainID := fmt.Sprintf("chain_%s_%d", containerID[:12], time.Now().Unix())

	severity := "medium"
	if pattern.Confidence >= 0.9 {
		severity = "critical"
	} else if pattern.Confidence >= 0.7 {
		severity = "high"
	}

	indicators := []string{pattern.Name}
	for _, evt := range matchingEvents {
		if evt.Alert != nil {
			indicators = append(indicators, evt.Alert.Message)
		}
	}

	return &AttackChain{
		ID:              chainID,
		ContainerID:     containerID,
		StartTime:       step.StartTime,
		EndTime:         step.EndTime,
		Steps:           []*AttackStep{step},
		TotalConfidence: pattern.Confidence,
		Severity:        severity,
		Status:          "active",
		Description:     pattern.Description,
		Indicators:      indicators,
		Remediation:     "Isolate the container, investigate the attack chain, and apply necessary patches.",
	}
}

func (ce *CorrelationEngine) mergeChains(existing, new *AttackChain) {
	for _, newStep := range new.Steps {
		merged := false
		for _, existingStep := range existing.Steps {
			if existingStep.Phase == newStep.Phase {
				existingStep.Events = append(existingStep.Events, newStep.Events...)
				existingStep.Rules = append(existingStep.Rules, newStep.Rules...)
				existingStep.EndTime = newStep.EndTime
				existingStep.Confidence = (existingStep.Confidence + newStep.Confidence) / 2
				merged = true
				break
			}
		}
		if !merged {
			existing.Steps = append(existing.Steps, newStep)
		}
	}

	existing.TotalConfidence = (existing.TotalConfidence + new.TotalConfidence) / 2
	existing.EndTime = new.EndTime
	existing.Indicators = append(existing.Indicators, new.Indicators...)

	if new.EndTime.After(existing.EndTime) {
		existing.EndTime = new.EndTime
	}
}

func (ce *CorrelationEngine) GetActiveChains(containerID string) []*AttackChain {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	var chains []*AttackChain
	for _, chain := range ce.containerChains {
		if chain.ContainerID == containerID && chain.Status == "active" {
			chains = append(chains, chain)
		}
	}
	return chains
}

func (ce *CorrelationEngine) GetAllChains() map[string]*AttackChain {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	result := make(map[string]*AttackChain)
	for k, v := range ce.containerChains {
		result[k] = v
	}
	return result
}

func (ce *CorrelationEngine) CloseChain(chainID string) {
	ce.mu.Lock()
	defer ce.mu.Unlock()

	if chain, exists := ce.containerChains[chainID]; exists {
		chain.Status = "closed"
		chain.EndTime = time.Now()
		logrus.Infof("Attack chain closed: %s", chainID)
	}
}

func (ce *CorrelationEngine) PrintChainSummary(chain *AttackChain) {
	fmt.Printf("\n=== Attack Chain Summary ===\n")
	fmt.Printf("Chain ID: %s\n", chain.ID)
	fmt.Printf("Container: %s\n", chain.ContainerID)
	fmt.Printf("Severity: %s\n", chain.Severity)
	fmt.Printf("Confidence: %.2f%%\n", chain.TotalConfidence*100)
	fmt.Printf("Status: %s\n", chain.Status)
	fmt.Printf("Duration: %v\n", chain.EndTime.Sub(chain.StartTime))
	fmt.Printf("Description: %s\n", chain.Description)
	fmt.Printf("\nAttack Steps:\n")
	for i, step := range chain.Steps {
		fmt.Printf("  Step %d: %s (%.2f%%)\n", i+1, step.Phase, step.Confidence*100)
		fmt.Printf("    Time: %s -> %s\n",
			step.StartTime.Format("15:04:05"), step.EndTime.Format("15:04:05"))
		fmt.Printf("    Rules: %v\n", step.Rules)
		fmt.Printf("    Events: %d\n", len(step.Events))
	}
	fmt.Printf("\nIndicators:\n")
	for _, ind := range chain.Indicators {
		fmt.Printf("  - %s\n", ind)
	}
	fmt.Println("===========================\n")
}

func bytesToString(b []byte) string {
	for i, c := range b {
		if c == 0 {
			return string(b[:i])
		}
	}
	return string(b)
}

func intToIP(ip uint32) string {
	return fmt.Sprintf("%d.%d.%d.%d", byte(ip>>24), byte(ip>>16), byte(ip>>8), byte(ip))
}
