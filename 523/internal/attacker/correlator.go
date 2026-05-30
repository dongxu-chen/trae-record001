package attacker

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/security/container-escape-detector/pkg/types"
)

type EventCorrelator struct {
	maxCorrelationWindow time.Duration
	maxCausalDepth       int
	logger               interface {
		Debugf(format string, args ...interface{})
		Warnf(format string, args ...interface{})
	}
}

type CorrelationResult struct {
	Chains       []*types.AttackChain
	CrossChain   []*CrossContainerChain
	CausalLinks  []*CausalLink
	Confidence   float64
}

type CrossContainerChain struct {
	Containers  []string
	Steps       []types.AttackStep
	TotalScore  float64
	Description string
	SharedNS    uint64
}

type CausalLink struct {
	FromEvent *EventWithContext
	ToEvent   *EventWithContext
	LinkType  CausalLinkType
	Confidence float64
	Reason    string
}

type CausalLinkType string

const (
	CausalParentChild  CausalLinkType = "parent_child"
	CausalTemporal     CausalLinkType = "temporal"
	CausalSharedNS     CausalLinkType = "shared_namespace"
	CausalDataFlow     CausalLinkType = "data_flow"
	CausalPrivilegeEsc CausalLinkType = "privilege_escalation"
)

func NewEventCorrelator() *EventCorrelator {
	return &EventCorrelator{
		maxCorrelationWindow: 30 * time.Minute,
		maxCausalDepth:       10,
	}
}

func (ec *EventCorrelator) CorrelateEvents(
	containerEvents map[string][]*EventWithContext,
	triggerEvent *EventWithContext,
	triggerContainerID string,
) *CorrelationResult {
	result := &CorrelationResult{}

	events, exists := containerEvents[triggerContainerID]
	if !exists || len(events) < 2 {
		return result
	}

	sort.Slice(events, func(i, j int) bool {
		return events[i].Event.Timestamp.Before(events[j].Event.Timestamp)
	})

	causalLinks := ec.buildCausalGraph(events)
	result.CausalLinks = causalLinks

	linkedEvents := ec.traverseCausalGraph(events, causalLinks, triggerEvent)
	if len(linkedEvents) > 0 {
		chain := ec.buildCorrelatedChain(linkedEvents, triggerContainerID)
		if chain != nil {
			result.Chains = append(result.Chains, chain)
		}
	}

	ec.addTemporalCorrelations(events, triggerEvent, result)

	crossChains := ec.correlateCrossContainer(containerEvents, triggerEvent, triggerContainerID)
	result.CrossChain = crossChains

	if len(result.Chains) > 0 || len(result.CrossChain) > 0 {
		result.Confidence = ec.calculateConfidence(result)
	}

	return result
}

func (ec *EventCorrelator) buildCausalGraph(events []*EventWithContext) []*CausalLink {
	var links []*CausalLink

	pidMap := make(map[uint32]*EventWithContext)
	for _, event := range events {
		pidMap[event.Event.PID] = event
	}

	for _, event := range events {
		if parent, exists := pidMap[event.Event.PPID]; exists {
			link := &CausalLink{
				FromEvent:  parent,
				ToEvent:    event,
				LinkType:   CausalParentChild,
				Confidence: 0.9,
				Reason:     fmt.Sprintf("PPID %d spawned PID %d", event.Event.PPID, event.Event.PID),
			}
			links = append(links, link)
		}
	}

	for i := 1; i < len(events); i++ {
		prev := events[i-1]
		curr := events[i]

		timeDiff := curr.Event.Timestamp.Sub(prev.Event.Timestamp)
		if timeDiff < 0 {
			timeDiff = -timeDiff
		}

		if timeDiff < 5*time.Second {
			confidence := 0.8
			if timeDiff < time.Second {
				confidence = 0.95
			} else if timeDiff < 2*time.Second {
				confidence = 0.85
			}

			if curr.Event.PID == prev.Event.PID {
				confidence += 0.1
			}

			if confidence > 1.0 {
				confidence = 1.0
			}

			linkType := CausalTemporal
			reason := fmt.Sprintf("Temporal proximity: %v between events", timeDiff)

			if prev.Event.EventType == types.EventMount && curr.Event.EventType == types.EventSyscall {
				linkType = CausalDataFlow
				reason = fmt.Sprintf("Mount at %s followed by syscall within %v", prev.Event.MountTarget, timeDiff)
			} else if prev.Event.EventType == types.EventCapability && curr.Event.EventType == types.EventSyscall {
				linkType = CausalPrivilegeEsc
				reason = fmt.Sprintf("Capability %s used then syscall %s within %v", prev.Event.CapName, curr.Event.SyscallName, timeDiff)
			}

			links = append(links, &CausalLink{
				FromEvent:  prev,
				ToEvent:    curr,
				LinkType:   linkType,
				Confidence: confidence,
				Reason:     reason,
			})
		}
	}

	for i := 0; i < len(events); i++ {
		for j := i + 1; j < len(events); j++ {
			if events[i].Event.PIDNS != 0 && events[i].Event.PIDNS == events[j].Event.PIDNS {
				if events[i].Event.PID != events[j].Event.PID {
					links = append(links, &CausalLink{
						FromEvent:  events[i],
						ToEvent:    events[j],
						LinkType:   CausalSharedNS,
						Confidence: 0.5,
						Reason:     fmt.Sprintf("Same PID namespace: %d", events[i].Event.PIDNS),
					})
				}
			}
		}
	}

	return links
}

func (ec *EventCorrelator) traverseCausalGraph(
	events []*EventWithContext,
	links []*CausalLink,
	trigger *EventWithContext,
) []*EventWithContext {
	adjacency := make(map[uint32][]*CausalLink)
	for _, link := range links {
		if link.FromEvent != nil && link.ToEvent != nil {
			adjacency[link.FromEvent.Event.PID] = append(adjacency[link.FromEvent.Event.PID], link)
		}
	}

	visited := make(map[uint32]bool)
	var result []*EventWithContext

	var dfs func(pid uint32, depth int)
	dfs = func(pid uint32, depth int) {
		if depth > ec.maxCausalDepth || visited[pid] {
			return
		}
		visited[pid] = true

		for _, event := range events {
			if event.Event.PID == pid {
				result = append(result, event)
				break
			}
		}

		for _, link := range adjacency[pid] {
			if link.Confidence >= 0.5 {
				dfs(link.ToEvent.Event.PID, depth+1)
			}
		}
	}

	triggerPID := trigger.Event.PID
	dfs(triggerPID, 0)

	if trigger.Event.PPID != 0 {
		dfs(trigger.Event.PPID, 0)
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].Event.Timestamp.Before(result[j].Event.Timestamp)
	})

	return result
}

func (ec *EventCorrelator) buildCorrelatedChain(events []*EventWithContext, containerID string) *types.AttackChain {
	if len(events) < 2 {
		return nil
	}

	steps := make([]types.AttackStep, 0, len(events))
	totalScore := 0.0

	for i, event := range events {
		phase := ec.detectCorrelatedPhase(event)
		riskScore := ec.calculateCorrelatedRisk(event)

		evidence := ec.generateCorrelatedEvidence(event)
		if i > 0 {
			prev := events[i-1]
			timeDiff := event.Event.Timestamp.Sub(prev.Event.Timestamp)
			evidence += fmt.Sprintf(" [after %v from PID %d]", timeDiff, prev.Event.PID)
		}

		step := types.AttackStep{
			Sequence:  i + 1,
			Phase:     phase,
			Action:    ec.describeCorrelatedEvent(event),
			PID:       event.Event.PID,
			Comm:      event.Event.Comm,
			Timestamp: event.Event.Timestamp,
			RiskScore: riskScore,
			Evidence:  evidence,
		}
		steps = append(steps, step)
		totalScore += riskScore
	}

	if totalScore > 100.0 {
		totalScore = 100.0
	}

	return &types.AttackChain{
		ContainerID: containerID,
		Steps:       steps,
		TotalScore:  totalScore,
		Description: fmt.Sprintf("Correlated attack chain: %d linked events in container %s", len(events), containerID[:12]),
	}
}

func (ec *EventCorrelator) addTemporalCorrelations(
	events []*EventWithContext,
	trigger *EventWithContext,
	result *CorrelationResult,
) {
	windowStart := trigger.Event.Timestamp.Add(-ec.maxCorrelationWindow)
	windowEnd := trigger.Event.Timestamp.Add(ec.maxCorrelationWindow)

	var windowEvents []*EventWithContext
	for _, event := range events {
		if event.Event.Timestamp.After(windowStart) && event.Event.Timestamp.Before(windowEnd) {
			windowEvents = append(windowEvents, event)
		}
	}

	if len(windowEvents) < 2 {
		return
	}

	sequenceGroups := ec.groupByAttackPhase(windowEvents)
	for _, group := range sequenceGroups {
		if len(group) >= 2 {
			chain := ec.buildPhaseSequenceChain(group, trigger)
			if chain != nil {
				alreadyExists := false
				for _, existing := range result.Chains {
					if existing.Description == chain.Description {
						alreadyExists = true
						break
					}
				}
				if !alreadyExists {
					result.Chains = append(result.Chains, chain)
				}
			}
		}
	}
}

func (ec *EventCorrelator) groupByAttackPhase(events []*EventWithContext) [][]*EventWithContext {
	groups := make(map[string][]*EventWithContext)

	for _, event := range events {
		phase := ec.detectCorrelatedPhase(event)
		groups[phase] = append(groups[phase], event)
	}

	var result [][]*EventWithContext
	for _, group := range groups {
		if len(group) >= 2 {
			result = append(result, group)
		}
	}

	return result
}

func (ec *EventCorrelator) buildPhaseSequenceChain(events []*EventWithContext, trigger *EventWithContext) *types.AttackChain {
	sort.Slice(events, func(i, j int) bool {
		return events[i].Event.Timestamp.Before(events[j].Event.Timestamp)
	})

	steps := make([]types.AttackStep, 0, len(events))
	totalScore := 0.0

	for i, event := range events {
		step := types.AttackStep{
			Sequence:  i + 1,
			Phase:     ec.detectCorrelatedPhase(event),
			Action:    ec.describeCorrelatedEvent(event),
			PID:       event.Event.PID,
			Comm:      event.Event.Comm,
			Timestamp: event.Event.Timestamp,
			RiskScore: ec.calculateCorrelatedRisk(event),
			Evidence:  ec.generateCorrelatedEvidence(event),
		}
		steps = append(steps, step)
		totalScore += step.RiskScore
	}

	if totalScore > 100.0 {
		totalScore = 100.0
	}

	return &types.AttackChain{
		Steps:       steps,
		TotalScore:  totalScore,
		Description: fmt.Sprintf("Phase-correlated sequence: %d events", len(events)),
	}
}

func (ec *EventCorrelator) correlateCrossContainer(
	containerEvents map[string][]*EventWithContext,
	trigger *EventWithContext,
	triggerContainerID string,
) []*CrossContainerChain {
	var chains []*CrossContainerChain

	triggerNS := trigger.Event.PIDNS

	for containerID, events := range containerEvents {
		if containerID == triggerContainerID {
			continue
		}

		var relatedEvents []*EventWithContext
		for _, event := range events {
			if event.Event.PIDNS == triggerNS && triggerNS != 0 {
				relatedEvents = append(relatedEvents, event)
				continue
			}

			if trigger.Event.MNTNS != 0 && event.Event.MNTNS == trigger.Event.MNTNS {
				relatedEvents = append(relatedEvents, event)
				continue
			}

			timeDiff := event.Event.Timestamp.Sub(trigger.Event.Timestamp)
			if timeDiff < 0 {
				timeDiff = -timeDiff
			}
			if timeDiff < 2*time.Minute {
				if ec.isCausallyRelated(trigger, event) {
					relatedEvents = append(relatedEvents, event)
				}
			}
		}

		if len(relatedEvents) > 0 {
			crossChain := ec.buildCrossContainerChain(
				triggerContainerID,
				containerID,
				trigger,
				relatedEvents,
				triggerNS,
			)
			if crossChain != nil {
				chains = append(chains, crossChain)
			}
		}
	}

	return chains
}

func (ec *EventCorrelator) isCausallyRelated(a, b *EventWithContext) bool {
	if a.Event.PPID == b.Event.PID || b.Event.PPID == a.Event.PID {
		return true
	}

	if a.Event.EventType == types.EventMount && b.Event.EventType == types.EventSyscall {
		if strings.Contains(b.Event.FileName, a.Event.MountTarget) {
			return true
		}
	}

	if a.Event.EventType == types.EventCapability && b.Event.EventType == types.EventSyscall {
		if a.Event.CapName == "CAP_SYS_ADMIN" || a.Event.CapName == "CAP_SYS_PTRACE" {
			return true
		}
	}

	return false
}

func (ec *EventCorrelator) buildCrossContainerChain(
	sourceID, targetID string,
	trigger *EventWithContext,
	relatedEvents []*EventWithContext,
	sharedNS uint64,
) *CrossContainerChain {
	steps := []types.AttackStep{
		{
			Sequence:  1,
			Phase:     string(PhaseInitialAccess),
			Action:    fmt.Sprintf("Source event in container %s", sourceID[:12]),
			PID:       trigger.Event.PID,
			Comm:      trigger.Event.Comm,
			Timestamp: trigger.Event.Timestamp,
			RiskScore: 30.0,
			Evidence:  fmt.Sprintf("Trigger: %s in container %s", ec.describeCorrelatedEvent(trigger), sourceID[:12]),
		},
	}

	totalScore := 30.0

	for i, event := range relatedEvents {
		step := types.AttackStep{
			Sequence:  i + 2,
			Phase:     ec.detectCorrelatedPhase(event),
			Action:    fmt.Sprintf("Related event in container %s: %s", targetID[:12], ec.describeCorrelatedEvent(event)),
			PID:       event.Event.PID,
			Comm:      event.Event.Comm,
			Timestamp: event.Event.Timestamp,
			RiskScore: ec.calculateCorrelatedRisk(event),
			Evidence:  fmt.Sprintf("Cross-container correlation (shared NS: %d)", sharedNS),
		}
		steps = append(steps, step)
		totalScore += step.RiskScore
	}

	if totalScore > 100.0 {
		totalScore = 100.0
	}

	return &CrossContainerChain{
		Containers:  []string{sourceID, targetID},
		Steps:       steps,
		TotalScore:  totalScore,
		Description: fmt.Sprintf("Cross-container attack: %s -> %s (shared NS: %d)", sourceID[:12], targetID[:12], sharedNS),
		SharedNS:    sharedNS,
	}
}

func (ec *EventCorrelator) calculateConfidence(result *CorrelationResult) float64 {
	if len(result.CausalLinks) == 0 {
		return 0.0
	}

	totalConfidence := 0.0
	for _, link := range result.CausalLinks {
		totalConfidence += link.Confidence
	}

	avgConfidence := totalConfidence / float64(len(result.CausalLinks))

	linkBonus := float64(len(result.CausalLinks)) * 0.05
	if linkBonus > 0.3 {
		linkBonus = 0.3
	}

	confidence := avgConfidence + linkBonus
	if confidence > 1.0 {
		confidence = 1.0
	}

	return confidence
}

func (ec *EventCorrelator) detectCorrelatedPhase(event *EventWithContext) string {
	eventStr := strings.ToLower(fmt.Sprintf("%s %s %s %s %s",
		event.Event.Comm, event.Event.SyscallName, event.Event.FileName,
		event.Event.MountSource, event.Event.CapName))

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

func (ec *EventCorrelator) describeCorrelatedEvent(event *EventWithContext) string {
	switch event.Event.EventType {
	case types.EventSyscall:
		return fmt.Sprintf("Syscall %s by %s", event.Event.SyscallName, event.Event.Comm)
	case types.EventMount:
		return fmt.Sprintf("Mount %s -> %s", event.Event.MountSource, event.Event.MountTarget)
	case types.EventCapability:
		return fmt.Sprintf("Capability %s (%s)", event.Event.CapName, event.Event.CapAction)
	case types.EventFile:
		return fmt.Sprintf("File access %s", event.Event.FileName)
	default:
		return fmt.Sprintf("Event %s", event.Event.EventType)
	}
}

func (ec *EventCorrelator) calculateCorrelatedRisk(event *EventWithContext) float64 {
	score := 5.0

	if event.Node != nil && event.Node.IsSuspicious {
		score += float64(len(event.Node.RiskTags)) * 5.0
	}

	for _, rule := range event.Rules {
		score += rule.Score * 0.5
	}

	switch event.Event.EventType {
	case types.EventMount:
		if strings.Contains(event.Event.MountSource, "docker.sock") {
			score += 40.0
		} else if strings.Contains(event.Event.MountSource, "/proc") || strings.Contains(event.Event.MountSource, "/sys") {
			score += 20.0
		} else {
			score += 10.0
		}
	case types.EventCapability:
		if event.Event.CapName == "CAP_SYS_ADMIN" {
			score += 30.0
		} else if event.Event.CapName == "CAP_SYS_MODULE" {
			score += 35.0
		} else if event.Event.CapName == "CAP_SYS_PTRACE" {
			score += 25.0
		}
	case types.EventSyscall:
		if event.Event.SyscallName == "ptrace" {
			score += 20.0
		} else if event.Event.SyscallName == "unshare" || event.Event.SyscallName == "setns" {
			score += 15.0
		}
	}

	if score > 50.0 {
		score = 50.0
	}

	return score
}

func (ec *EventCorrelator) generateCorrelatedEvidence(event *EventWithContext) string {
	var parts []string

	parts = append(parts, fmt.Sprintf("PID=%d COMM=%s", event.Event.PID, event.Event.Comm))

	if event.Event.SyscallName != "" {
		parts = append(parts, fmt.Sprintf("syscall=%s", event.Event.SyscallName))
	}
	if event.Event.MountSource != "" {
		parts = append(parts, fmt.Sprintf("mount=%s->%s", event.Event.MountSource, event.Event.MountTarget))
	}
	if event.Event.CapName != "" {
		parts = append(parts, fmt.Sprintf("cap=%s", event.Event.CapName))
	}
	if event.Event.FileName != "" {
		parts = append(parts, fmt.Sprintf("file=%s", event.Event.FileName))
	}

	for _, rule := range event.Rules {
		parts = append(parts, fmt.Sprintf("rule=%s", rule.ID))
	}

	return strings.Join(parts, " ")
}
