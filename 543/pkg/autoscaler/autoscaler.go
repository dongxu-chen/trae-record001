package autoscaler

import (
	"context"
	"fmt"
	"sync"
	"time"

	"rabbitmq-lb/pkg/config"
	"rabbitmq-lb/pkg/monitor"
)

type NodeProvider interface {
	ProvisionNode(ctx context.Context, name string) (string, error)
	DeprovisionNode(ctx context.Context, nodeID string) error
	GetNodeStatus(ctx context.Context, nodeID string) (string, error)
	ListManagedNodes(ctx context.Context) ([]string, error)
}

type ScalingEvent struct {
	Timestamp   time.Time
	Action      string
	Reason      string
	NodeID      string
	NodeName    string
	CurrentLoad float64
	TargetLoad  float64
	Success     bool
	Error       string
}

type NodeInfo struct {
	ID          string
	Name        string
	Provisioned time.Time
	Status      string
	Provider    string
}

type AutoScaler struct {
	mu             sync.RWMutex
	config         *config.AutoScalerConfig
	provider       NodeProvider
	managedNodes   map[string]*NodeInfo
	events         []ScalingEvent
	scaleUpCount   int
	scaleDownCount int
	lastScaleUp    time.Time
	lastScaleDown  time.Time
}

func NewAutoScaler(cfg *config.AutoScalerConfig, provider NodeProvider) *AutoScaler {
	return &AutoScaler{
		config:       cfg,
		provider:     provider,
		managedNodes: make(map[string]*NodeInfo),
		events:       make([]ScalingEvent, 0),
	}
}

func (as *AutoScaler) Evaluate(state *monitor.ClusterState) *ScalingDecision {
	as.mu.Lock()
	defer as.mu.Unlock()

	if !as.config.Enabled {
		return nil
	}

	if time.Since(as.lastScaleUp) < as.config.ScaleUpCooldown {
		return nil
	}
	if time.Since(as.lastScaleDown) < as.config.ScaleDownCooldown {
		return nil
	}

	runningNodes := make([]*monitor.NodeState, 0)
	for _, node := range state.Nodes {
		if node.Running {
			runningNodes = append(runningNodes, node)
		}
	}

	if len(runningNodes) == 0 {
		return nil
	}

	avgLoad := calculateAvgLoad(runningNodes)
	maxLoad := 0.0
	for _, node := range runningNodes {
		if node.LoadScore > maxLoad {
			maxLoad = node.LoadScore
		}
	}

	if len(runningNodes) >= as.config.MaxNodes {
		return nil
	}

	if len(runningNodes) <= as.config.MinNodes {
		if len(runningNodes) < as.config.MinNodes {
			return &ScalingDecision{
				Action:       "scale_up",
				Reason:       fmt.Sprintf("Below minimum nodes (%d/%d)", len(runningNodes), as.config.MinNodes),
				CurrentNodes: len(runningNodes),
				TargetNodes:  len(runningNodes) + 1,
				AvgLoad:      avgLoad,
				MaxLoad:      maxLoad,
			}
		}
		return nil
	}

	if avgLoad > as.config.ScaleUpThreshold {
		return &ScalingDecision{
			Action:       "scale_up",
			Reason:       fmt.Sprintf("Average load %.2f exceeds threshold %.2f", avgLoad, as.config.ScaleUpThreshold),
			CurrentNodes: len(runningNodes),
			TargetNodes:  len(runningNodes) + as.config.ScaleUpStep,
			AvgLoad:      avgLoad,
			MaxLoad:      maxLoad,
		}
	}

	if avgLoad < as.config.ScaleDownThreshold && len(runningNodes) > as.config.MinNodes {
		underloadedCount := 0
		for _, node := range runningNodes {
			if node.LoadScore < as.config.ScaleDownThreshold {
				underloadedCount++
			}
		}

		if underloadedCount > 1 {
			return &ScalingDecision{
				Action:       "scale_down",
				Reason:       fmt.Sprintf("Average load %.2f below threshold %.2f with %d underloaded nodes", avgLoad, as.config.ScaleDownThreshold, underloadedCount),
				CurrentNodes: len(runningNodes),
				TargetNodes:  len(runningNodes) - 1,
				AvgLoad:      avgLoad,
				MaxLoad:      maxLoad,
			}
		}
	}

	return nil
}

func (as *AutoScaler) ExecuteScaleUp(ctx context.Context, decision *ScalingDecision) error {
	as.mu.Lock()
	defer as.mu.Unlock()

	if as.provider == nil {
		return fmt.Errorf("no node provider configured")
	}

	nodeName := fmt.Sprintf("rabbit-lb-node-%d", time.Now().Unix())
	nodeID, err := as.provider.ProvisionNode(ctx, nodeName)

	event := ScalingEvent{
		Timestamp:   time.Now(),
		Action:      "scale_up",
		Reason:      decision.Reason,
		NodeID:      nodeID,
		NodeName:    nodeName,
		CurrentLoad: decision.AvgLoad,
		TargetLoad:  as.config.ScaleDownThreshold,
	}

	if err != nil {
		event.Success = false
		event.Error = err.Error()
		as.events = append(as.events, event)
		return err
	}

	event.Success = true
	as.events = append(as.events, event)
	as.scaleUpCount++
	as.lastScaleUp = time.Now()

	as.managedNodes[nodeID] = &NodeInfo{
		ID:          nodeID,
		Name:        nodeName,
		Provisioned: time.Now(),
		Status:      "provisioning",
		Provider:    "auto",
	}

	return nil
}

func (as *AutoScaler) ExecuteScaleDown(ctx context.Context, nodeID string) error {
	as.mu.Lock()
	defer as.mu.Unlock()

	if as.provider == nil {
		return fmt.Errorf("no node provider configured")
	}

	err := as.provider.DeprovisionNode(ctx, nodeID)

	event := ScalingEvent{
		Timestamp: time.Now(),
		Action:    "scale_down",
		Reason:    "Low load, scaling down",
		NodeID:    nodeID,
	}

	if err != nil {
		event.Success = false
		event.Error = err.Error()
		as.events = append(as.events, event)
		return err
	}

	event.Success = true
	as.events = append(as.events, event)
	as.scaleDownCount++
	as.lastScaleDown = time.Now()

	delete(as.managedNodes, nodeID)

	return nil
}

func (as *AutoScaler) GetManagedNodes() map[string]*NodeInfo {
	as.mu.RLock()
	defer as.mu.RUnlock()

	result := make(map[string]*NodeInfo)
	for k, v := range as.managedNodes {
		result[k] = v
	}
	return result
}

func (as *AutoScaler) GetEvents() []ScalingEvent {
	as.mu.RLock()
	defer as.mu.RUnlock()

	events := make([]ScalingEvent, len(as.events))
	copy(events, as.events)
	return events
}

func (as *AutoScaler) GetScalingStats() (int, int) {
	as.mu.RLock()
	defer as.mu.RUnlock()
	return as.scaleUpCount, as.scaleDownCount
}

type ScalingDecision struct {
	Action       string
	Reason       string
	CurrentNodes int
	TargetNodes  int
	AvgLoad      float64
	MaxLoad      float64
}

type MockNodeProvider struct {
	mu        sync.Mutex
	nodes     map[string]string
	nodeCount int
}

func NewMockNodeProvider() *MockNodeProvider {
	return &MockNodeProvider{
		nodes: make(map[string]string),
	}
}

func (p *MockNodeProvider) ProvisionNode(ctx context.Context, name string) (string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	p.nodeCount++
	nodeID := fmt.Sprintf("node-%d", p.nodeCount)
	p.nodes[nodeID] = name
	return nodeID, nil
}

func (p *MockNodeProvider) DeprovisionNode(ctx context.Context, nodeID string) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	if _, exists := p.nodes[nodeID]; !exists {
		return fmt.Errorf("node %s not found", nodeID)
	}
	delete(p.nodes, nodeID)
	return nil
}

func (p *MockNodeProvider) GetNodeStatus(ctx context.Context, nodeID string) (string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	if _, exists := p.nodes[nodeID]; !exists {
		return "", fmt.Errorf("node %s not found", nodeID)
	}
	return "running", nil
}

func (p *MockNodeProvider) ListManagedNodes(ctx context.Context) ([]string, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	var nodes []string
	for id := range p.nodes {
		nodes = append(nodes, id)
	}
	return nodes, nil
}

func calculateAvgLoad(nodes []*monitor.NodeState) float64 {
	if len(nodes) == 0 {
		return 0
	}
	var total float64
	for _, n := range nodes {
		total += n.LoadScore
	}
	return total / float64(len(nodes))
}
