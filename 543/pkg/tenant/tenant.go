package tenant

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"rabbitmq-lb/pkg/config"
	"rabbitmq-lb/pkg/monitor"
	"rabbitmq-lb/pkg/rabbitmq"
)

type Tenant struct {
	Name           string
	Vhost          string
	Queues         []string
	ExclusiveNodes []string
	Priority       int
	MaxLoadScore   float64
}

type DedicatedQueue struct {
	QueueName  string
	Vhost      string
	Nodes      []string
	Priority   int
	MinNodes   int
}

type TenantManager struct {
	mu              sync.RWMutex
	config          *config.TenantConfig
	tenants         map[string]*Tenant
	dedicatedQueues map[string]*DedicatedQueue
	nodeAssignments map[string]string
	client          *rabbitmq.Client
}

func NewTenantManager(cfg *config.TenantConfig, client *rabbitmq.Client) *TenantManager {
	tm := &TenantManager{
		config:          cfg,
		tenants:         make(map[string]*Tenant),
		dedicatedQueues: make(map[string]*DedicatedQueue),
		nodeAssignments: make(map[string]string),
		client:          client,
	}

	for _, t := range cfg.Tenants {
		tm.tenants[t.Name] = &Tenant{
			Name:           t.Name,
			Vhost:          t.Vhost,
			Queues:         t.Queues,
			ExclusiveNodes: t.ExclusiveNodes,
			Priority:       t.Priority,
			MaxLoadScore:   t.MaxLoadScore,
		}
	}

	for _, dq := range cfg.DedicatedQueues {
		key := dq.Vhost + ":" + dq.QueueName
		tm.dedicatedQueues[key] = &DedicatedQueue{
			QueueName: dq.QueueName,
			Vhost:     dq.Vhost,
			Nodes:     dq.Nodes,
			Priority:  dq.Priority,
			MinNodes:  dq.MinNodes,
		}
	}

	return tm
}

func (tm *TenantManager) GetTenantForQueue(queueName, vhost string) *Tenant {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	for _, tenant := range tm.tenants {
		if tenant.Vhost == vhost || tenant.Vhost == "*" {
			for _, pattern := range tenant.Queues {
				if pattern == "*" || pattern == queueName {
					return tenant
				}
				if matched, _ := matchSimplePattern(pattern, queueName); matched {
					return tenant
				}
			}
		}
	}
	return nil
}

func (tm *TenantManager) IsDedicatedQueue(queueName, vhost string) bool {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	key := vhost + ":" + queueName
	_, exists := tm.dedicatedQueues[key]
	return exists
}

func (tm *TenantManager) GetDedicatedQueue(queueName, vhost string) *DedicatedQueue {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	key := vhost + ":" + queueName
	return tm.dedicatedQueues[key]
}

func (tm *TenantManager) GetAllowedTargetNodes(queueName, vhost string, allNodes []*monitor.NodeState) []*monitor.NodeState {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	tenant := tm.getTenantForQueueInternal(queueName, vhost)

	if dq, exists := tm.dedicatedQueues[vhost+":"+queueName]; exists {
		return filterNodesByNames(allNodes, dq.Nodes)
	}

	if tenant != nil && len(tenant.ExclusiveNodes) > 0 {
		return filterNodesByNames(allNodes, tenant.ExclusiveNodes)
	}

	return allNodes
}

func (tm *TenantManager) GetExclusiveNodes() map[string][]string {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	result := make(map[string][]string)
	for name, tenant := range tm.tenants {
		if len(tenant.ExclusiveNodes) > 0 {
			result[name] = tenant.ExclusiveNodes
		}
	}
	return result
}

func (tm *TenantManager) GetDedicatedNodes() map[string]bool {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	result := make(map[string]bool)
	for _, dq := range tm.dedicatedQueues {
		for _, node := range dq.Nodes {
			result[node] = true
		}
	}
	for _, tenant := range tm.tenants {
		if len(tenant.ExclusiveNodes) > 0 {
			for _, node := range tenant.ExclusiveNodes {
				result[node] = true
			}
		}
	}
	return result
}

func (tm *TenantManager) IsNodeDedicated(nodeName string) bool {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	for _, dq := range tm.dedicatedQueues {
		for _, node := range dq.Nodes {
			if node == nodeName {
				return true
			}
		}
	}
	return false
}

func (tm *TenantManager) ValidateMigration(queueName, vhost, targetNode string, state *monitor.ClusterState) error {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	key := vhost + ":" + queueName

	if dq, exists := tm.dedicatedQueues[key]; exists {
		found := false
		for _, node := range dq.Nodes {
			if node == targetNode {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("queue %s is dedicated and can only be on nodes: %v", queueName, dq.Nodes)
		}
	}

	tenant := tm.getTenantForQueueInternal(queueName, vhost)
	if tenant != nil && len(tenant.ExclusiveNodes) > 0 {
		found := false
		for _, node := range tenant.ExclusiveNodes {
			if node == targetNode {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("tenant %s queue %s can only be on exclusive nodes: %v", tenant.Name, queueName, tenant.ExclusiveNodes)
		}

		if tenant.MaxLoadScore > 0 {
			for _, nodeState := range state.Nodes {
				if nodeState.Name == targetNode && nodeState.LoadScore > tenant.MaxLoadScore {
					return fmt.Errorf("target node %s load %.2f exceeds tenant %s max load %.2f", targetNode, nodeState.LoadScore, tenant.Name, tenant.MaxLoadScore)
				}
			}
		}
	}

	for _, dq := range tm.dedicatedQueues {
		if vhost+":"+queueName != dq.Vhost+":"+dq.QueueName {
			for _, node := range dq.Nodes {
				if node == targetNode {
					return fmt.Errorf("target node %s is dedicated to queue %s", targetNode, dq.QueueName)
				}
			}
		}
	}

	return nil
}

func (tm *TenantManager) EnforceTenantPolicies(state *monitor.ClusterState) []Violation {
	tm.mu.RLock()
	defer tm.mu.RUnlock()

	var violations []Violation

	for _, queue := range getQueuesFromState(state) {
		key := queue.Vhost + ":" + queue.Name

		if dq, exists := tm.dedicatedQueues[key]; exists {
			validNode := false
			for _, node := range dq.Nodes {
				if queue.Node == node {
					validNode = true
					break
				}
			}
			if !validNode {
				violations = append(violations, Violation{
					Type:        "dedicated_queue_misplaced",
					QueueName:   queue.Name,
					Vhost:       queue.Vhost,
					CurrentNode: queue.Node,
					AllowedNodes: dq.Nodes,
					Severity:    "high",
					Timestamp:   time.Now(),
				})
			}
		}

		tenant := tm.getTenantForQueueInternal(queue.Name, queue.Vhost)
		if tenant != nil && len(tenant.ExclusiveNodes) > 0 {
			validNode := false
			for _, node := range tenant.ExclusiveNodes {
				if queue.Node == node {
					validNode = true
					break
				}
			}
			if !validNode {
				violations = append(violations, Violation{
					Type:        "tenant_isolation_violated",
					QueueName:   queue.Name,
					Vhost:       queue.Vhost,
					CurrentNode: queue.Node,
					AllowedNodes: tenant.ExclusiveNodes,
					Severity:    "high",
					Tenant:      tenant.Name,
					Timestamp:   time.Now(),
				})
			}

			if tenant.MaxLoadScore > 0 {
				if nodeState, exists := state.Nodes[queue.Node]; exists {
					if nodeState.LoadScore > tenant.MaxLoadScore {
						violations = append(violations, Violation{
							Type:         "tenant_load_exceeded",
							QueueName:    queue.Name,
							Vhost:        queue.Vhost,
							CurrentNode:  queue.Node,
							CurrentLoad:  nodeState.LoadScore,
							MaxLoad:      tenant.MaxLoadScore,
							Severity:     "medium",
							Tenant:       tenant.Name,
							Timestamp:    time.Now(),
						})
					}
				}
			}
		}
	}

	return violations
}

func (tm *TenantManager) GetSharedNodes(allNodes []*monitor.NodeState) []*monitor.NodeState {
	dedicatedNodes := tm.GetDedicatedNodes()

	var shared []*monitor.NodeState
	for _, node := range allNodes {
		if !dedicatedNodes[node.Name] {
			shared = append(shared, node)
		}
	}
	return shared
}

type Violation struct {
	Type         string    `json:"type"`
	QueueName    string    `json:"queue_name"`
	Vhost        string    `json:"vhost"`
	CurrentNode  string    `json:"current_node"`
	AllowedNodes []string  `json:"allowed_nodes"`
	CurrentLoad  float64   `json:"current_load,omitempty"`
	MaxLoad      float64   `json:"max_load,omitempty"`
	Severity     string    `json:"severity"`
	Tenant       string    `json:"tenant,omitempty"`
	Timestamp    time.Time `json:"timestamp"`
}

func (tm *TenantManager) getTenantForQueueInternal(queueName, vhost string) *Tenant {
	for _, tenant := range tm.tenants {
		if tenant.Vhost == vhost || tenant.Vhost == "*" {
			for _, pattern := range tenant.Queues {
				if pattern == "*" || pattern == queueName {
					return tenant
				}
				if matched, _ := matchSimplePattern(pattern, queueName); matched {
					return tenant
				}
			}
		}
	}
	return nil
}

func filterNodesByNames(nodes []*monitor.NodeState, names []string) []*monitor.NodeState {
	nameSet := make(map[string]bool)
	for _, n := range names {
		nameSet[n] = true
	}

	var result []*monitor.NodeState
	for _, node := range nodes {
		if nameSet[node.Name] {
			result = append(result, node)
		}
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].LoadScore < result[j].LoadScore
	})

	return result
}

func getQueuesFromState(state *monitor.ClusterState) []rabbitmq.Queue {
	if state == nil {
		return nil
	}
	return state.Queues
}

func matchSimplePattern(pattern, str string) (bool, error) {
	if pattern == str {
		return true, nil
	}

	if strings.Contains(pattern, "*") {
		parts := strings.Split(pattern, "*")
		if len(parts) == 2 {
			if parts[0] == "" {
				return strings.HasSuffix(str, parts[1]), nil
			}
			if parts[1] == "" {
				return strings.HasPrefix(str, parts[0]), nil
			}
			return strings.HasPrefix(str, parts[0]) && strings.HasSuffix(str, parts[1]), nil
		}
	}

	return false, nil
}
