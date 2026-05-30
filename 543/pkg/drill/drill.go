package drill

import (
	"fmt"
	"math"
	"sort"
	"sync"
	"time"

	"rabbitmq-lb/pkg/balancer"
	"rabbitmq-lb/pkg/monitor"
	"rabbitmq-lb/pkg/predictor"
	"rabbitmq-lb/pkg/rabbitmq"
	"rabbitmq-lb/pkg/tenant"
)

type DrillResult struct {
	ID                string
	Timestamp         time.Time
	TotalPlans        int
	TotalMessages     int64
	TotalMemory       int64
	EstimatedDuration time.Duration
	SourceNodeImpact  map[string]*NodeImpact
	TargetNodeImpact  map[string]*NodeImpact
	RiskLevel         string
	RiskScore         float64
	Violations        []RiskViolation
	Recommendations   []string
	SimulatedPlans    []SimulatedPlan
	TenantViolations  []tenant.Violation
}

type NodeImpact struct {
	NodeName        string
	QueuesBefore    int
	QueuesAfter     int
	MessagesBefore  int64
	MessagesAfter   int64
	MemoryBefore    int64
	MemoryAfter     int64
	LoadScoreBefore float64
	LoadScoreAfter  float64
	DeltaLoad       float64
}

type SimulatedPlan struct {
	QueueName      string
	Vhost          string
	SourceNode     string
	TargetNode     string
	Messages       int64
	Memory         int64
	EstimatedTime  time.Duration
	TrafficRate    float64
	RiskLevel      string
	RiskReason     string
	ConsumerImpact string
}

type RiskViolation struct {
	Type     string
	Detail   string
	Severity string
}

type DrillRunner struct {
	mu       sync.Mutex
	history  []DrillResult
	tenant   *tenant.TenantManager
}

func NewDrillRunner(tm *tenant.TenantManager) *DrillRunner {
	return &DrillRunner{
		history: make([]DrillResult, 0),
		tenant:  tm,
	}
}

func (dr *DrillRunner) RunDrill(
	state *monitor.ClusterState,
	plans []balancer.MigrationPlan,
	predictions map[string]*predictor.PredictionResult,
) *DrillResult {
	dr.mu.Lock()
	defer dr.mu.Unlock()

	result := &DrillResult{
		ID:               fmt.Sprintf("drill-%d", time.Now().Unix()),
		Timestamp:        time.Now(),
		SourceNodeImpact: make(map[string]*NodeImpact),
		TargetNodeImpact: make(map[string]*NodeImpact),
		Violations:       make([]RiskViolation, 0),
		Recommendations:  make([]string, 0),
		SimulatedPlans:   make([]SimulatedPlan, 0),
	}

	simulatedNodeState := dr.buildSimulatedState(state)

	var totalMessages int64
	var totalMemory int64
	var totalDuration time.Duration

	for _, plan := range plans {
		totalMessages += plan.Messages
		totalMemory += plan.Memory
		totalDuration += plan.EstimatedTime

		simPlan := dr.simulatePlan(plan, simulatedNodeState, predictions)

		result.SimulatedPlans = append(result.SimulatedPlans, simPlan)

		if _, exists := result.SourceNodeImpact[plan.SourceNode]; !exists {
			ns := simulatedNodeState[plan.SourceNode]
			result.SourceNodeImpact[plan.SourceNode] = &NodeImpact{
				NodeName:        plan.SourceNode,
				QueuesBefore:    ns.QueueCount,
				MessagesBefore:  ns.TotalMessages,
				MemoryBefore:    ns.TotalMemory,
				LoadScoreBefore: ns.LoadScore,
			}
		}

		if _, exists := result.TargetNodeImpact[plan.TargetNode]; !exists {
			ns := simulatedNodeState[plan.TargetNode]
			result.TargetNodeImpact[plan.TargetNode] = &NodeImpact{
				NodeName:        plan.TargetNode,
				QueuesBefore:    ns.QueueCount,
				MessagesBefore:  ns.TotalMessages,
				MemoryBefore:    ns.TotalMemory,
				LoadScoreBefore: ns.LoadScore,
			}
		}

		dr.applySimulation(simulatedNodeState, plan)

		if plan.Messages > 500000 {
			result.Violations = append(result.Violations, RiskViolation{
				Type:     "large_queue",
				Detail:   fmt.Sprintf("Queue %s has %d messages, migration may take long", plan.QueueName, plan.Messages),
				Severity: "high",
			})
		}

		if plan.TrafficRate > 0.5 {
			result.Violations = append(result.Violations, RiskViolation{
				Type:     "active_traffic",
				Detail:   fmt.Sprintf("Queue %s has active traffic (%.2f msg/s)", plan.QueueName, plan.TrafficRate),
				Severity: "medium",
			})
		}

		if dr.tenant != nil {
			if err := dr.tenant.ValidateMigration(plan.QueueName, plan.Vhost, plan.TargetNode, state); err != nil {
				result.Violations = append(result.Violations, RiskViolation{
					Type:     "tenant_violation",
					Detail:   err.Error(),
					Severity: "high",
				})
			}
		}
	}

	for nodeName, impact := range result.SourceNodeImpact {
		if ns, exists := simulatedNodeState[nodeName]; exists {
			impact.QueuesAfter = ns.QueueCount
			impact.MessagesAfter = ns.TotalMessages
			impact.MemoryAfter = ns.TotalMemory
			impact.LoadScoreAfter = ns.LoadScore
			impact.DeltaLoad = impact.LoadScoreAfter - impact.LoadScoreBefore
		}
	}

	for nodeName, impact := range result.TargetNodeImpact {
		if ns, exists := simulatedNodeState[nodeName]; exists {
			impact.QueuesAfter = ns.QueueCount
			impact.MessagesAfter = ns.TotalMessages
			impact.MemoryAfter = ns.TotalMemory
			impact.LoadScoreAfter = ns.LoadScore
			impact.DeltaLoad = impact.LoadScoreAfter - impact.LoadScoreBefore
		}
	}

	result.TotalPlans = len(plans)
	result.TotalMessages = totalMessages
	result.TotalMemory = totalMemory
	result.EstimatedDuration = totalDuration

	result.RiskScore = dr.calculateRiskScore(result)
	result.RiskLevel = dr.riskLevelFromScore(result.RiskScore)

	if dr.tenant != nil {
		result.TenantViolations = dr.tenant.EnforceTenantPolicies(state)
	}

	result.Recommendations = dr.generateRecommendations(result)

	dr.history = append(dr.history, *result)
	if len(dr.history) > 100 {
		dr.history = dr.history[1:]
	}

	return result
}

func (dr *DrillRunner) buildSimulatedState(state *monitor.ClusterState) map[string]*monitor.NodeState {
	result := make(map[string]*monitor.NodeState)
	for name, ns := range state.Nodes {
		copied := *ns
		result[name] = &copied
	}
	return result
}

func (dr *DrillRunner) simulatePlan(plan balancer.MigrationPlan, nodeState map[string]*monitor.NodeState, predictions map[string]*predictor.PredictionResult) SimulatedPlan {
	sim := SimulatedPlan{
		QueueName:     plan.QueueName,
		Vhost:         plan.Vhost,
		SourceNode:    plan.SourceNode,
		TargetNode:    plan.TargetNode,
		Messages:      plan.Messages,
		Memory:        plan.Memory,
		EstimatedTime: plan.EstimatedTime,
		TrafficRate:   plan.TrafficRate,
	}

	if plan.Messages > 1000000 {
		sim.RiskLevel = "critical"
		sim.RiskReason = "Very large queue, extended migration time expected"
		sim.ConsumerImpact = "Consumers will be paused for extended period"
	} else if plan.Messages > 100000 {
		sim.RiskLevel = "high"
		sim.RiskReason = "Large queue migration"
		sim.ConsumerImpact = "Consumers will be paused during migration"
	} else if plan.Messages > 10000 {
		sim.RiskLevel = "medium"
		sim.RiskReason = "Moderate queue size"
		sim.ConsumerImpact = "Brief consumer pause expected"
	} else {
		sim.RiskLevel = "low"
		sim.RiskReason = "Small queue, quick migration"
		sim.ConsumerImpact = "Minimal consumer impact"
	}

	key := plan.Vhost + ":" + plan.QueueName
	if pred, exists := predictions[key]; exists {
		if pred.Trend == "increasing" && pred.Confidence > 0.6 {
			sim.RiskLevel = "high"
			sim.RiskReason += "; predicted increasing traffic"
			sim.ConsumerImpact = "Traffic may increase during migration"
		}
	}

	return sim
}

func (dr *DrillRunner) applySimulation(nodeState map[string]*monitor.NodeState, plan balancer.MigrationPlan) {
	if src, exists := nodeState[plan.SourceNode]; exists {
		src.QueueCount--
		src.TotalMessages -= plan.Messages
		src.TotalMemory -= plan.Memory
		src.LoadScore = recalcLoad(src)
	}

	if tgt, exists := nodeState[plan.TargetNode]; exists {
		tgt.QueueCount++
		tgt.TotalMessages += plan.Messages
		tgt.TotalMemory += plan.Memory
		tgt.LoadScore = recalcLoad(tgt)
	}
}

func recalcLoad(ns *monitor.NodeState) float64 {
	queueFactor := float64(ns.QueueCount) * 0.4
	msgFactor := float64(ns.TotalMessages) * 0.0001 * 0.4
	memFactor := 0.0
	if ns.MemLimit > 0 {
		memFactor = float64(ns.TotalMemory) / float64(ns.MemLimit) * 0.2
	}
	return queueFactor + msgFactor + memFactor
}

func (dr *DrillRunner) calculateRiskScore(result *DrillResult) float64 {
	score := 0.0

	for _, violation := range result.Violations {
		switch violation.Severity {
		case "high":
			score += 30
		case "medium":
			score += 15
		case "low":
			score += 5
		}
	}

	for _, impact := range result.TargetNodeImpact {
		if impact.DeltaLoad > 1.0 {
			score += 25
		} else if impact.DeltaLoad > 0.5 {
			score += 15
		}
	}

	for _, impact := range result.SourceNodeImpact {
		if impact.DeltaLoad < -0.3 {
			score += 5
		}
	}

	if result.EstimatedDuration > 10*time.Minute {
		score += 20
	} else if result.EstimatedDuration > 5*time.Minute {
		score += 10
	}

	if result.TotalMessages > 5000000 {
		score += 15
	} else if result.TotalMessages > 1000000 {
		score += 8
	}

	if len(result.TenantViolations) > 0 {
		score += float64(len(result.TenantViolations)) * 10
	}

	return math.Min(score, 100)
}

func (dr *DrillRunner) riskLevelFromScore(score float64) string {
	if score >= 70 {
		return "critical"
	} else if score >= 50 {
		return "high"
	} else if score >= 30 {
		return "medium"
	}
	return "low"
}

func (dr *DrillRunner) generateRecommendations(result *DrillResult) []string {
	var recs []string

	if result.RiskLevel == "critical" {
		recs = append(recs, "Consider splitting large queues before migration")
	}

	for _, violation := range result.Violations {
		switch violation.Type {
		case "large_queue":
			recs = append(recs, "Schedule large queue migrations during off-peak hours")
		case "active_traffic":
			recs = append(recs, "Wait for lower traffic before migrating active queues")
		case "tenant_violation":
			recs = append(recs, "Resolve tenant isolation violations before proceeding")
		}
	}

	for name, impact := range result.TargetNodeImpact {
		if impact.DeltaLoad > 1.0 {
			recs = append(recs, fmt.Sprintf("Node %s will become overloaded after migration, consider different target", name))
		}
	}

	for _, impact := range result.SourceNodeImpact {
		if impact.QueuesAfter == 0 {
			recs = append(recs, fmt.Sprintf("Node %s will have no queues after migration, consider scaling down", impact.NodeName))
		}
	}

	if len(result.TenantViolations) > 0 {
		recs = append(recs, "Fix tenant policy violations before executing migrations")
	}

	if len(recs) == 0 {
		recs = append(recs, "Migration plan looks safe to execute")
	}

	return recs
}

func (dr *DrillRunner) GetHistory() []DrillResult {
	dr.mu.Lock()
	defer dr.mu.Unlock()

	history := make([]DrillResult, len(dr.history))
	copy(history, dr.history)
	return history
}

func (dr *DrillRunner) GetLatestDrill() *DrillResult {
	dr.mu.Lock()
	defer dr.mu.Unlock()

	if len(dr.history) == 0 {
		return nil
	}

	result := dr.history[len(dr.history)-1]
	return &result
}

func GenerateDrillReport(result *DrillResult) string {
	report := fmt.Sprintf("Migration Drill Report: %s\n", result.ID)
	report += fmt.Sprintf("Time: %s\n\n", result.Timestamp.Format(time.RFC3339))
	report += fmt.Sprintf("Risk Level: %s (score: %.1f/100)\n", result.RiskLevel, result.RiskScore)
	report += fmt.Sprintf("Total Plans: %d\n", result.TotalPlans)
	report += fmt.Sprintf("Total Messages: %d\n", result.TotalMessages)
	report += fmt.Sprintf("Estimated Duration: %s\n\n", result.EstimatedDuration)

	if len(result.SimulatedPlans) > 0 {
		report += "Simulated Migrations:\n"
		for i, plan := range result.SimulatedPlans {
			report += fmt.Sprintf("  %d. %s/%s: %s -> %s [%s]\n", i+1, plan.Vhost, plan.QueueName, plan.SourceNode, plan.TargetNode, plan.RiskLevel)
			report += fmt.Sprintf("     Risk: %s\n", plan.RiskReason)
			report += fmt.Sprintf("     Consumer Impact: %s\n", plan.ConsumerImpact)
		}
		report += "\n"
	}

	if len(result.Violations) > 0 {
		report += "Risk Violations:\n"
		for _, v := range result.Violations {
			report += fmt.Sprintf("  [%s] %s: %s\n", v.Severity, v.Type, v.Detail)
		}
		report += "\n"
	}

	if len(result.SourceNodeImpact) > 0 {
		report += "Source Node Impact:\n"
		for _, impact := range result.SourceNodeImpact {
			report += fmt.Sprintf("  %s: queues %d->%d, messages %d->%d, load %.2f->%.2f (delta: %.2f)\n",
				impact.NodeName, impact.QueuesBefore, impact.QueuesAfter,
				impact.MessagesBefore, impact.MessagesAfter,
				impact.LoadScoreBefore, impact.LoadScoreAfter, impact.DeltaLoad)
		}
		report += "\n"
	}

	if len(result.TargetNodeImpact) > 0 {
		report += "Target Node Impact:\n"
		for _, impact := range result.TargetNodeImpact {
			report += fmt.Sprintf("  %s: queues %d->%d, messages %d->%d, load %.2f->%.2f (delta: %.2f)\n",
				impact.NodeName, impact.QueuesBefore, impact.QueuesAfter,
				impact.MessagesBefore, impact.MessagesAfter,
				impact.LoadScoreBefore, impact.LoadScoreAfter, impact.DeltaLoad)
		}
		report += "\n"
	}

	if len(result.Recommendations) > 0 {
		report += "Recommendations:\n"
		for _, rec := range result.Recommendations {
			report += fmt.Sprintf("  - %s\n", rec)
		}
	}

	return report
}

func init() {
	_ = sort.Sort
	_ = rabbitmq.Queue{}
}
