package monitor

import (
	"context"
	"sync"
	"time"

	"rabbitmq-lb/pkg/rabbitmq"
)

type ClusterState struct {
	Nodes       map[string]*NodeState
	Queues      []rabbitmq.Queue
	Timestamp   time.Time
	TotalQueues int
	TotalNodes  int
}

type NodeState struct {
	Name          string
	Running       bool
	QueueCount    int
	TotalMessages int64
	TotalMemory   int64
	LoadScore     float64
	LastSeen      time.Time
	MemUsed       int64
	MemLimit      int64
	DiskFree      int64
}

type Monitor struct {
	client    *rabbitmq.Client
	mu        sync.RWMutex
	state     *ClusterState
	listeners []func(*ClusterState)
}

func NewMonitor(client *rabbitmq.Client) *Monitor {
	return &Monitor{
		client: client,
		state: &ClusterState{
			Nodes:  make(map[string]*NodeState),
			Queues: make([]rabbitmq.Queue, 0),
		},
		listeners: make([]func(*ClusterState), 0),
	}
}

func (m *Monitor) Start(ctx context.Context, interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	m.Collect()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			m.Collect()
		}
	}
}

func (m *Monitor) Collect() {
	nodes, err := m.client.GetNodes()
	if err != nil {
		return
	}

	queues, err := m.client.GetQueues()
	if err != nil {
		return
	}

	m.mu.Lock()
	defer m.mu.Unlock()

	nodeStates := make(map[string]*NodeState)
	for _, node := range nodes {
		ns := &NodeState{
			Name:     node.Name,
			Running:  node.Running,
			LastSeen: time.Now(),
			MemUsed:  node.MemUsed,
			MemLimit: node.MemLimit,
			DiskFree: node.DiskFree,
		}
		if oldState, exists := m.state.Nodes[node.Name]; exists {
			ns.QueueCount = oldState.QueueCount
			ns.TotalMessages = oldState.TotalMessages
			ns.TotalMemory = oldState.TotalMemory
			ns.LoadScore = oldState.LoadScore
		}
		nodeStates[node.Name] = ns
	}

	for _, node := range nodeStates {
		node.QueueCount = 0
		node.TotalMessages = 0
		node.TotalMemory = 0
	}

	for _, queue := range queues {
		if node, exists := nodeStates[queue.Node]; exists {
			node.QueueCount++
			node.TotalMessages += queue.Messages
			node.TotalMemory += queue.Memory
		}
	}

	var totalQueues int
	var totalMessages int64
	for _, node := range nodeStates {
		totalQueues += node.QueueCount
		totalMessages += node.TotalMessages
	}

	if totalQueues > 0 {
		avgQueues := float64(totalQueues) / float64(len(nodeStates))
		avgMessages := float64(totalMessages) / float64(len(nodeStates))

		for _, node := range nodeStates {
			queueScore := float64(node.QueueCount) / avgQueues
			messageScore := float64(0)
			if avgMessages > 0 {
				messageScore = float64(node.TotalMessages) / avgMessages
			}
			memScore := float64(0)
			if node.MemLimit > 0 {
				memScore = float64(node.MemUsed) / float64(node.MemLimit)
			}
			node.LoadScore = queueScore*0.4 + messageScore*0.4 + memScore*0.2
		}
	}

	m.state = &ClusterState{
		Nodes:       nodeStates,
		Queues:      queues,
		Timestamp:   time.Now(),
		TotalQueues: len(queues),
		TotalNodes:  len(nodes),
	}

	for _, listener := range m.listeners {
		listener(m.state)
	}
}

func (m *Monitor) GetState() *ClusterState {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.state
}

func (m *Monitor) AddListener(listener func(*ClusterState)) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.listeners = append(m.listeners, listener)
}
