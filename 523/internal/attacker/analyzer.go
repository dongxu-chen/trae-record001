package attacker

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/google/uuid"

	"github.com/security/container-escape-detector/pkg/types"
)

type Config struct {
	EnableAttackChain bool
	EnableRiskScore   bool
	RiskWindowMinutes int
}

type Analyzer struct {
	containerEvents map[string][]*EventWithContext
	attackChains    map[string][]*types.AttackChain
	crossChains     map[string][]*CrossContainerChain
	mu              sync.RWMutex
	logger          *logrus.Logger
	maxEventAge     time.Duration
	maxChainAge     time.Duration
	config          *Config
	correlator      *EventCorrelator
}

type EventWithContext struct {
	Event     *types.BPFEvent
	Container *types.ContainerInfo
	Profile   *types.BehaviorProfile
	Rules     []*types.DetectionRule
	Node      *types.ProcessNode
	Timestamp time.Time
}

type EscapePhase string

const (
	PhaseReconnaissance EscapePhase = "Reconnaissance"
	PhaseInitialAccess  EscapePhase = "Initial Access"
	PhaseExecution      EscapePhase = "Execution"
	PhasePrivilegeEsc   EscapePhase = "Privilege Escalation"
	PhaseDefenseEvasion EscapePhase = "Defense Evasion"
	PhaseCredentialAccess EscapePhase = "Credential Access"
	PhaseDiscovery      EscapePhase = "Discovery"
	PhaseLateralMovement EscapePhase = "Lateral Movement"
	PhaseCollection     EscapePhase = "Collection"
	PhaseExfiltration   EscapePhase = "Exfiltration"
	PhaseImpact         EscapePhase = "Impact"
)

var phaseKeywords = map[EscapePhase][]string{
	PhaseReconnaissance: {"nmap", "masscan", "netstat", "ss", "ip", "ifconfig"},
	PhaseExecution:      {"execve", "bash", "sh", "python", "perl", "nc", "netcat"},
	PhasePrivilegeEsc:   {"setuid", "setgid", "mount", "chroot", "pivot_root", "unshare", "setns", "commit_creds", "capset"},
	PhaseDefenseEvasion: {"ptrace", "mknod", "unlink", "rename", "chmod"},
	PhaseCredentialAccess: {"/etc/shadow", "/etc/passwd", ".ssh", "id_rsa", "docker.sock"},
	PhaseDiscovery:      {"ps", "top", "ls", "find", "cat", "readlink"},
	PhaseLateralMovement: {"ssh", "scp", "rsync", "docker", "kubectl"},
	PhaseImpact:         {"reboot", "shutdown", "rm", "dd", "mkfs"},
}

func NewAnalyzer(logger *logrus.Logger, config *Config) *Analyzer {
	if config == nil {
		config = &Config{
			EnableAttackChain: true,
			EnableRiskScore:   true,
			RiskWindowMinutes: 60,
		}
	}

	return &Analyzer{
		containerEvents: make(map[string][]*EventWithContext),
		attackChains:    make(map[string][]*types.AttackChain),
		crossChains:     make(map[string][]*CrossContainerChain),
		logger:          logger,
		maxEventAge:     time.Duration(config.RiskWindowMinutes) * time.Minute,
		maxChainAge:     24 * time.Hour,
		config:          config,
		correlator:      NewEventCorrelator(),
	}
}

func (a *Analyzer) ProcessEvent(event *types.BPFEvent, container *types.ContainerInfo, profile *types.BehaviorProfile, matchedRules []*types.DetectionRule, node *types.ProcessNode) {
	if container == nil {
		return
	}

	containerID := container.ID

	ewc := &EventWithContext{
		Event:     event,
		Container: container,
		Profile:   profile,
		Rules:     matchedRules,
		Node:      node,
		Timestamp: time.Now(),
	}

	a.mu.Lock()
	a.containerEvents[containerID] = append(a.containerEvents[containerID], ewc)

	if len(matchedRules) > 0 {
		chains := a.analyzeAttackChains(containerID, ewc)
		if len(chains) > 0 {
			a.attackChains[containerID] = append(a.attackChains[containerID], chains...)
			for _, chain := range chains {
				a.logger.Warnf("Attack chain detected for container %s: %s (score: %.1f)",
					containerID[:12], chain.Description, chain.TotalScore)
			}
		}
	}

	a.cleanupOldEvents(containerID)
	a.mu.Unlock()
}

func (a *Analyzer) analyzeAttackChains(containerID string, latestEvent *EventWithContext) []*types.AttackChain {
	var chains []*types.AttackChain

	events := a.containerEvents[containerID]
	if len(events) < 2 {
		return chains
	}

	escapePatterns := []EscapePattern{
		a.dockerSocketEscapePattern,
		a.mountEscapePattern,
		a.privilegedContainerEscapePattern,
		a.kernelModulePattern,
		a.namespaceEscapePattern,
		a.ptraceInjectionPattern,
		a.cgroupV1EscapePattern,
		a.deviceAccessPattern,
	}

	for _, pattern := range escapePatterns {
		if chain := pattern(events, latestEvent); chain != nil {
			chain.ContainerID = containerID
			chains = append(chains, chain)
		}
	}

	return chains
}

type EscapePattern func(events []*EventWithContext, latest *EventWithContext) *types.AttackChain

func (a *Analyzer) dockerSocketEscapePattern(events []*EventWithContext, latest *EventWithContext) *types.AttackChain {
	if !containsRule(latest.Rules, "ESCAPE-001") && !containsRule(latest.Rules, "ESCAPE-013") {
		return nil
	}

	steps := []types.AttackStep{
		{
			Sequence:  1,
			Phase:     string(PhaseDiscovery),
			Action:    "Docker socket discovered/accessed",
			PID:       latest.Event.PID,
			Comm:      latest.Event.Comm,
			Timestamp: latest.Event.Timestamp,
			RiskScore: 50.0,
			Evidence:  fmt.Sprintf("Process %s accessed Docker socket", latest.Event.Comm),
		},
	}

	if chain := a.buildChain(latest, steps, "Docker Socket Escape", 100.0); chain != nil {
		return chain
	}
	return nil
}

func (a *Analyzer) mountEscapePattern(events []*EventWithContext, latest *EventWithContext) *types.AttackChain {
	if !containsRule(latest.Rules, "ESCAPE-002") && !containsRule(latest.Rules, "ESCAPE-004") {
		return nil
	}

	steps := []types.AttackStep{}
	sequence := 1

	for _, event := range events {
		if event.Event.EventType == types.EventMount || event.Event.SyscallName == "mount" {
			step := types.AttackStep{
				Sequence:  sequence,
				Phase:     string(PhasePrivilegeEsc),
				Action:    fmt.Sprintf("Mount operation: %s -> %s", event.Event.MountSource, event.Event.MountTarget),
				PID:       event.Event.PID,
				Comm:      event.Event.Comm,
				Timestamp: event.Event.Timestamp,
				RiskScore: 30.0,
				Evidence:  fmt.Sprintf("Mount syscall with flags 0x%x", event.Event.MountFlags),
			}

			if strings.Contains(event.Event.MountSource, "/proc") || strings.Contains(event.Event.MountSource, "/sys") {
				step.RiskScore = 40.0
				step.Evidence += " - Sensitive filesystem mount detected"
			}

			steps = append(steps, step)
			sequence++
		}
	}

	if len(steps) == 0 {
		steps = append(steps, types.AttackStep{
			Sequence:  1,
			Phase:     string(PhasePrivilegeEsc),
			Action:    fmt.Sprintf("Suspicious mount attempt: %s -> %s", latest.Event.MountSource, latest.Event.MountTarget),
			PID:       latest.Event.PID,
			Comm:      latest.Event.Comm,
			Timestamp: latest.Event.Timestamp,
			RiskScore: 50.0,
			Evidence:  fmt.Sprintf("Mount operation detected in container"),
		})
	}

	if chain := a.buildChain(latest, steps, "Container Escape via Mount Operation", 80.0); chain != nil {
		return chain
	}
	return nil
}

func (a *Analyzer) privilegedContainerEscapePattern(events []*EventWithContext, latest *EventWithContext) *types.AttackChain {
	if !containsRule(latest.Rules, "ESCAPE-003") || latest.Container == nil || !latest.Container.Privileged {
		return nil
	}

	steps := []types.AttackStep{
		{
			Sequence:  1,
			Phase:     string(PhaseInitialAccess),
			Action:    "Running in privileged container",
			PID:       latest.Event.PID,
			Comm:      latest.Event.Comm,
			Timestamp: latest.Container.CreatedAt,
			RiskScore: 40.0,
			Evidence:  "Container started with --privileged flag",
		},
	}

	for _, event := range events {
		if len(event.Rules) > 0 {
			steps = append(steps, types.AttackStep{
				Sequence:  len(steps) + 1,
				Phase:     string(PhasePrivilegeEsc),
				Action:    fmt.Sprintf("Dangerous syscall: %s", event.Event.SyscallName),
				PID:       event.Event.PID,
				Comm:      event.Event.Comm,
				Timestamp: event.Event.Timestamp,
				RiskScore: 30.0,
				Evidence:  fmt.Sprintf("Syscall %s executed in privileged mode", event.Event.SyscallName),
			})
		}
	}

	if chain := a.buildChain(latest, steps, "Privileged Container Escape", 85.0); chain != nil {
		return chain
	}
	return nil
}

func (a *Analyzer) kernelModulePattern(events []*EventWithContext, latest *EventWithContext) *types.AttackChain {
	if !containsRule(latest.Rules, "ESCAPE-005") && !containsRule(latest.Rules, "ESCAPE-010") {
		return nil
	}

	steps := []types.AttackStep{}
	sequence := 1

	for _, event := range events {
		if containsRule(event.Rules, "ESCAPE-005") || containsRule(event.Rules, "ESCAPE-010") {
			steps = append(steps, types.AttackStep{
				Sequence:  sequence,
				Phase:     string(PhasePrivilegeEsc),
				Action:    fmt.Sprintf("Kernel module operation: %s", event.Event.SyscallName),
				PID:       event.Event.PID,
				Comm:      event.Event.Comm,
				Timestamp: event.Event.Timestamp,
				RiskScore: 80.0,
				Evidence:  "Attempting to load or unload kernel modules",
			})
			sequence++
		}
	}

	if chain := a.buildChain(latest, steps, "Kernel Module Escape Attempt", 95.0); chain != nil {
		return chain
	}
	return nil
}

func (a *Analyzer) namespaceEscapePattern(events []*EventWithContext, latest *EventWithContext) *types.AttackChain {
	if !containsRule(latest.Rules, "ESCAPE-006") {
		return nil
	}

	steps := []types.AttackStep{}
	sequence := 1

	for _, event := range events {
		if event.Event.SyscallName == "setns" || event.Event.SyscallName == "unshare" {
			action := "Namespace manipulation"
			if event.Event.SyscallName == "setns" {
				action = "Joining another namespace (setns)"
			} else if event.Event.SyscallName == "unshare" {
				action = "Creating new namespace (unshare)"
			}

			steps = append(steps, types.AttackStep{
				Sequence:  sequence,
				Phase:     string(PhasePrivilegeEsc),
				Action:    action,
				PID:       event.Event.PID,
				Comm:      event.Event.Comm,
				Timestamp: event.Event.Timestamp,
				RiskScore: 50.0,
				Evidence:  fmt.Sprintf("Syscall %s with args %v", event.Event.SyscallName, event.Event.Args),
			})
			sequence++
		}
	}

	if chain := a.buildChain(latest, steps, "Namespace Escape Attempt", 75.0); chain != nil {
		return chain
	}
	return nil
}

func (a *Analyzer) ptraceInjectionPattern(events []*EventWithContext, latest *EventWithContext) *types.AttackChain {
	if !containsRule(latest.Rules, "ESCAPE-007") && !containsRule(latest.Rules, "ESCAPE-011") {
		return nil
	}

	steps := []types.AttackStep{}
	sequence := 1

	for _, event := range events {
		if event.Event.SyscallName == "ptrace" {
			steps = append(steps, types.AttackStep{
				Sequence:  sequence,
				Phase:     string(PhaseDefenseEvasion),
				Action:    "Ptrace process injection attempt",
				PID:       event.Event.PID,
				Comm:      event.Event.Comm,
				Timestamp: event.Event.Timestamp,
				RiskScore: 60.0,
				Evidence:  fmt.Sprintf("Ptrace request %d targeting PID %d", event.Event.Args[0], event.Event.Args[1]),
			})
			sequence++
		}
	}

	if chain := a.buildChain(latest, steps, "Process Injection via Ptrace", 70.0); chain != nil {
		return chain
	}
	return nil
}

func (a *Analyzer) cgroupV1EscapePattern(events []*EventWithContext, latest *EventWithContext) *types.AttackChain {
	var hasMount bool
	var hasReleaseAgent bool

	for _, event := range events {
		if strings.Contains(event.Event.MountSource, "cgroup") || strings.Contains(event.Event.FSType, "cgroup") {
			hasMount = true
		}
		if strings.Contains(event.Event.FileName, "release_agent") || strings.Contains(event.Event.FileName, "tasks") {
			hasReleaseAgent = true
		}
	}

	if !hasMount && !hasReleaseAgent {
		return nil
	}

	steps := []types.AttackStep{}
	sequence := 1

	if hasMount {
		steps = append(steps, types.AttackStep{
			Sequence:  sequence,
			Phase:     string(PhasePrivilegeEsc),
			Action:    "Cgroup filesystem mount",
			PID:       latest.Event.PID,
			Comm:      latest.Event.Comm,
			Timestamp: latest.Event.Timestamp,
			RiskScore: 40.0,
			Evidence:  "Mounting cgroup filesystem for potential escape",
		})
		sequence++
	}

	if hasReleaseAgent {
		steps = append(steps, types.AttackStep{
			Sequence:  sequence,
			Phase:     string(PhasePrivilegeEsc),
			Action:    "Modifying cgroup release_agent",
			PID:       latest.Event.PID,
			Comm:      latest.Event.Comm,
			Timestamp: latest.Event.Timestamp,
			RiskScore: 70.0,
			Evidence:  "Potential CGroup v1 release_agent escape attempt",
		})
	}

	if chain := a.buildChain(latest, steps, "CGroup v1 Escape Attempt", 85.0); chain != nil {
		return chain
	}
	return nil
}

func (a *Analyzer) deviceAccessPattern(events []*EventWithContext, latest *EventWithContext) *types.AttackChain {
	if !containsRule(latest.Rules, "ESCAPE-019") && !containsRule(latest.Rules, "ESCAPE-015") {
		return nil
	}

	steps := []types.AttackStep{}
	sequence := 1

	for _, event := range events {
		if containsRule(event.Rules, "ESCAPE-019") {
			steps = append(steps, types.AttackStep{
				Sequence:  sequence,
				Phase:     string(PhaseImpact),
				Action:    "Raw disk device access",
				PID:       event.Event.PID,
				Comm:      event.Event.Comm,
				Timestamp: event.Event.Timestamp,
				RiskScore: 85.0,
				Evidence:  fmt.Sprintf("Accessing raw device: %s", event.Event.FileName),
			})
			sequence++
		}
		if containsRule(event.Rules, "ESCAPE-015") {
			steps = append(steps, types.AttackStep{
				Sequence:  sequence,
				Phase:     string(PhasePrivilegeEsc),
				Action:    "Device node creation",
				PID:       event.Event.PID,
				Comm:      event.Event.Comm,
				Timestamp: event.Event.Timestamp,
				RiskScore: 70.0,
				Evidence:  "Creating device nodes using mknod",
			})
			sequence++
		}
	}

	if chain := a.buildChain(latest, steps, "Device Access Escape", 90.0); chain != nil {
		return chain
	}
	return nil
}

func (a *Analyzer) buildChain(latest *EventWithContext, steps []types.AttackStep, description string, baseScore float64) *types.AttackChain {
	if len(steps) == 0 {
		return nil
	}

	sort.Slice(steps, func(i, j int) bool {
		return steps[i].Timestamp.Before(steps[j].Timestamp)
	})

	for i := range steps {
		steps[i].Sequence = i + 1
	}

	totalScore := baseScore
	for _, step := range steps {
		totalScore += step.RiskScore
	}

	if totalScore > 100.0 {
		totalScore = 100.0
	}

	return &types.AttackChain{
		Steps:       steps,
		TotalScore:  totalScore,
		Description: description,
	}
}

func (a *Analyzer) reconstructEscapePathByID(containerID string, pid uint32) *types.AttackChain {
	a.mu.RLock()
	defer a.mu.RUnlock()

	events, exists := a.containerEvents[containerID]
	if !exists {
		return nil
	}

	var relevantEvents []*EventWithContext
	for _, event := range events {
		if event.Event.PID == pid || event.Node != nil && a.isInProcessTree(event.Node, int(pid)) {
			relevantEvents = append(relevantEvents, event)
		}
	}

	sort.Slice(relevantEvents, func(i, j int) bool {
		return relevantEvents[i].Event.Timestamp.Before(relevantEvents[j].Event.Timestamp)
	})

	steps := make([]types.AttackStep, 0, len(relevantEvents))
	for i, event := range relevantEvents {
		phase := a.detectPhase(event)
		step := types.AttackStep{
			Sequence:  i + 1,
			Phase:     phase,
			Action:    a.describeEvent(event),
			PID:       event.Event.PID,
			Comm:      event.Event.Comm,
			Timestamp: event.Event.Timestamp,
			RiskScore: a.calculateStepRisk(event),
			Evidence:  a.generateEvidence(event),
		}
		steps = append(steps, step)
	}

	if len(steps) == 0 {
		return nil
	}

	totalScore := 0.0
	for _, step := range steps {
		totalScore += step.RiskScore
	}

	if totalScore > 100.0 {
		totalScore = 100.0
	}

	return &types.AttackChain{
		ContainerID: containerID,
		Steps:       steps,
		TotalScore:  totalScore,
		Description: fmt.Sprintf("Reconstructed escape path for PID %d in container %s", pid, containerID[:12]),
	}
}

func (a *Analyzer) isInProcessTree(node *types.ProcessNode, targetPID int) bool {
	if node == nil {
		return false
	}

	if node.PID == targetPID {
		return true
	}

	for _, child := range node.Children {
		if a.isInProcessTree(child, targetPID) {
			return true
		}
	}

	return false
}

func (a *Analyzer) detectPhase(event *EventWithContext) string {
	eventStr := strings.ToLower(fmt.Sprintf("%s %s %s", event.Event.Comm, event.Event.SyscallName, event.Event.FileName))

	for phase, keywords := range phaseKeywords {
		for _, keyword := range keywords {
			if strings.Contains(eventStr, strings.ToLower(keyword)) {
				return string(phase)
			}
		}
	}

	if len(event.Rules) > 0 {
		return string(PhasePrivilegeEsc)
	}

	return string(PhaseDiscovery)
}

func (a *Analyzer) describeEvent(event *EventWithContext) string {
	switch event.Event.EventType {
	case types.EventSyscall:
		return fmt.Sprintf("Executed syscall: %s", event.Event.SyscallName)
	case types.EventMount:
		return fmt.Sprintf("Mount operation: %s -> %s", event.Event.MountSource, event.Event.MountTarget)
	case types.EventCapability:
		return fmt.Sprintf("Capability check: %s (%s)", event.Event.CapName, event.Event.CapAction)
	case types.EventProcess:
		return fmt.Sprintf("Process spawned: %s", event.Event.FileName)
	case types.EventFile:
		return fmt.Sprintf("File access: %s", event.Event.FileName)
	default:
		return fmt.Sprintf("Event: %s", event.Event.EventType)
	}
}

func (a *Analyzer) calculateStepRisk(event *EventWithContext) float64 {
	score := 5.0

	if event.Node != nil && event.Node.IsSuspicious {
		score += float64(len(event.Node.RiskTags)) * 5.0
	}

	for _, rule := range event.Rules {
		score += rule.Score
	}

	if score > 50.0 {
		score = 50.0
	}

	return score
}

func (a *Analyzer) generateEvidence(event *EventWithContext) string {
	var evidence []string

	evidence = append(evidence, fmt.Sprintf("PID: %d, Comm: %s", event.Event.PID, event.Event.Comm))

	if event.Event.SyscallName != "" {
		evidence = append(evidence, fmt.Sprintf("Syscall: %s", event.Event.SyscallName))
	}

	if event.Event.MountSource != "" || event.Event.MountTarget != "" {
		evidence = append(evidence, fmt.Sprintf("Mount: %s -> %s", event.Event.MountSource, event.Event.MountTarget))
	}

	if event.Event.CapName != "" {
		evidence = append(evidence, fmt.Sprintf("Capability: %s", event.Event.CapName))
	}

	if event.Event.FileName != "" {
		evidence = append(evidence, fmt.Sprintf("File: %s", event.Event.FileName))
	}

	for _, rule := range event.Rules {
		evidence = append(evidence, fmt.Sprintf("Rule: %s (%s)", rule.ID, rule.Name))
	}

	if event.Node != nil && len(event.Node.RiskTags) > 0 {
		evidence = append(evidence, fmt.Sprintf("Tags: %v", event.Node.RiskTags))
	}

	return strings.Join(evidence, "; ")
}

func (a *Analyzer) GetAttackChains(containerID string) []*types.AttackChain {
	a.mu.RLock()
	defer a.mu.RUnlock()

	chains, exists := a.attackChains[containerID]
	if !exists {
		return nil
	}

	result := make([]*types.AttackChain, len(chains))
	copy(result, chains)
	return result
}

func (a *Analyzer) GetAllAttackChains() map[string][]*types.AttackChain {
	a.mu.RLock()
	defer a.mu.RUnlock()

	result := make(map[string][]*types.AttackChain)
	for k, v := range a.attackChains {
		chains := make([]*types.AttackChain, len(v))
		copy(chains, v)
		result[k] = chains
	}
	return result
}

func (a *Analyzer) generateRiskAssessmentFull(containerID string, container *types.ContainerInfo, profile *types.BehaviorProfile, alerts []types.Alert) *types.RiskAssessment {
	a.mu.RLock()
	defer a.mu.RUnlock()

	assessment := &types.RiskAssessment{
		ContainerID:   containerID,
		LastUpdated:   time.Now(),
		AlertsCount:   make(map[types.RiskLevel]int),
	}

	if container != nil {
		assessment.ContainerName = container.Name
	}

	if profile != nil {
		assessment.OverallScore = profile.RiskScore
	}

	for _, alert := range alerts {
		assessment.AlertsCount[alert.Severity]++
		if alert.RiskScore > assessment.OverallScore {
			assessment.OverallScore = alert.RiskScore
		}
	}

	if chains, exists := a.attackChains[containerID]; exists {
		assessment.AttackPaths = make([]types.AttackChain, len(chains))
		for i, chain := range chains {
			assessment.AttackPaths[i] = *chain
		}

		for _, chain := range chains {
			if chain.TotalScore > assessment.OverallScore {
				assessment.OverallScore = chain.TotalScore
			}
		}
	}

	switch {
	case assessment.OverallScore >= 80.0:
		assessment.RiskLevel = types.RiskCritical
	case assessment.OverallScore >= 50.0:
		assessment.RiskLevel = types.RiskHigh
	case assessment.OverallScore >= 25.0:
		assessment.RiskLevel = types.RiskMedium
	case assessment.OverallScore >= 10.0:
		assessment.RiskLevel = types.RiskLow
	default:
		assessment.RiskLevel = types.RiskInfo
	}

	assessment.TopRisks = make([]types.Alert, 0, len(alerts))
	for _, alert := range alerts {
		if alert.Severity == types.RiskHigh || alert.Severity == types.RiskCritical {
			assessment.TopRisks = append(assessment.TopRisks, alert)
		}
	}

	sort.Slice(assessment.TopRisks, func(i, j int) bool {
		return assessment.TopRisks[i].RiskScore > assessment.TopRisks[j].RiskScore
	})

	if len(assessment.TopRisks) > 10 {
		assessment.TopRisks = assessment.TopRisks[:10]
	}

	return assessment
}

func (a *Analyzer) cleanupOldEvents(containerID string) {
	events := a.containerEvents[containerID]
	cutoff := time.Now().Add(-a.maxEventAge)

	var cleaned []*EventWithContext
	for _, event := range events {
		if event.Timestamp.After(cutoff) {
			cleaned = append(cleaned, event)
		}
	}
	a.containerEvents[containerID] = cleaned

	chains := a.attackChains[containerID]
	chainCutoff := time.Now().Add(-a.maxChainAge)
	var cleanedChains []*types.AttackChain
	for _, chain := range chains {
		if len(chain.Steps) > 0 && chain.Steps[len(chain.Steps)-1].Timestamp.After(chainCutoff) {
			cleanedChains = append(cleanedChains, chain)
		}
	}
	a.attackChains[containerID] = cleanedChains
}

func containsRule(rules []*types.DetectionRule, ruleID string) bool {
	for _, rule := range rules {
		if rule.ID == ruleID {
			return true
		}
	}
	return false
}

func generateAlertID() string {
	return uuid.New().String()
}

func (a *Analyzer) ReconstructEscapePath(event *types.BPFEvent, container *types.ContainerInfo, node *types.ProcessNode, profile *types.BehaviorProfile) (*types.AttackChain, error) {
	if container == nil {
		return nil, fmt.Errorf("container info is nil")
	}

	if node != nil {
		a.ProcessEvent(event, container, profile, nil, node)
	}

	correlationResult := a.correlator.CorrelateEvents(a.containerEvents, &EventWithContext{
		Event:     event,
		Container: container,
		Profile:   profile,
		Node:      node,
		Timestamp: time.Now(),
	}, container.ID)

	if len(correlationResult.Chains) > 0 {
		bestChain := correlationResult.Chains[0]
		for _, chain := range correlationResult.Chains {
			if chain.TotalScore > bestChain.TotalScore {
				bestChain = chain
			}
		}
		bestChain.ContainerID = container.ID
		return bestChain, nil
	}

	if len(correlationResult.CrossChain) > 0 {
		crossChain := correlationResult.CrossChain[0]
		a.mu.Lock()
		a.crossChains[container.ID] = append(a.crossChains[container.ID], crossChain)
		a.mu.Unlock()

		steps := make([]types.AttackStep, len(crossChain.Steps))
		copy(steps, crossChain.Steps)
		return &types.AttackChain{
			ContainerID: container.ID,
			Steps:       steps,
			TotalScore:  crossChain.TotalScore,
			Description: crossChain.Description,
		}, nil
	}

	chains := a.analyzeAttackChains(container.ID, &EventWithContext{
		Event:     event,
		Container: container,
		Node:      node,
		Timestamp: time.Now(),
	})
	if len(chains) > 0 {
		return chains[0], nil
	}

	return a.reconstructEscapePathByID(container.ID, event.PID), nil
}

func (a *Analyzer) GenerateRiskAssessment(container *types.ContainerInfo, profile *types.BehaviorProfile) *types.RiskAssessment {
	if container == nil {
		return nil
	}

	return a.generateRiskAssessmentFull(container.ID, container, profile, nil)
}

func (a *Analyzer) GetCrossContainerChains(containerID string) []*CrossContainerChain {
	a.mu.RLock()
	defer a.mu.RUnlock()

	chains, exists := a.crossChains[containerID]
	if !exists {
		return nil
	}

	result := make([]*CrossContainerChain, len(chains))
	copy(result, chains)
	return result
}

func (a *Analyzer) GetCausalLinks(containerID string) []*CausalLink {
	a.mu.RLock()
	defer a.mu.RUnlock()

	events, exists := a.containerEvents[containerID]
	if !exists || len(events) < 2 {
		return nil
	}

	return a.correlator.buildCausalGraph(events)
}
