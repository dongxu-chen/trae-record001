package balancer

import (
	"sync"
	"time"

	"rabbitmq-lb/pkg/monitor"
)

type FailureDetector struct {
	mu                sync.RWMutex
	nodeStatus        map[string]*NodeStatus
	failureTimeout    time.Duration
	failureListeners  []func(failedNodes []string)
	recoveryListeners []func(recoveredNodes []string)
}

type NodeStatus struct {
	Name             string
	Running          bool
	LastSeen         time.Time
	LastStateChange  time.Time
	FailureCount     int
	IsFailed         bool
	ConsecutiveFailures int
}

func NewFailureDetector(failureTimeout time.Duration) *FailureDetector {
	return &FailureDetector{
		nodeStatus:        make(map[string]*NodeStatus),
		failureTimeout:    failureTimeout,
		failureListeners:  make([]func(failedNodes []string), 0),
		recoveryListeners: make([]func(recoveredNodes []string), 0),
	}
}

func (fd *FailureDetector) Update(state *monitor.ClusterState) {
	fd.mu.Lock()
	defer fd.mu.Unlock()

	now := time.Now()

	for nodeName, nodeState := range state.Nodes {
		status, exists := fd.nodeStatus[nodeName]
		if !exists {
			status = &NodeStatus{
				Name:      nodeName,
				Running:   nodeState.Running,
				LastSeen:  now,
				IsFailed:  false,
			}
			fd.nodeStatus[nodeName] = status
		}

		if nodeState.Running {
			status.LastSeen = now
			status.ConsecutiveFailures = 0

			if status.IsFailed {
				status.IsFailed = false
				status.LastStateChange = now
				go fd.notifyRecovery([]string{nodeName})
			}
		} else {
			status.ConsecutiveFailures++
		}

		status.Running = nodeState.Running
	}

	var newlyFailed []string
	for nodeName, status := range fd.nodeStatus {
		if !status.IsFailed && !status.Running {
			if time.Since(status.LastSeen) > fd.failureTimeout {
				status.IsFailed = true
				status.FailureCount++
				status.LastStateChange = now
				newlyFailed = append(newlyFailed, nodeName)
			}
		}
	}

	if len(newlyFailed) > 0 {
		go fd.notifyFailure(newlyFailed)
	}
}

func (fd *FailureDetector) GetFailedNodes() []string {
	fd.mu.RLock()
	defer fd.mu.RUnlock()

	var failed []string
	for nodeName, status := range fd.nodeStatus {
		if status.IsFailed {
			failed = append(failed, nodeName)
		}
	}
	return failed
}

func (fd *FailureDetector) GetNodeStatus(nodeName string) (*NodeStatus, bool) {
	fd.mu.RLock()
	defer fd.mu.RUnlock()

	status, exists := fd.nodeStatus[nodeName]
	if !exists {
		return nil, false
	}

	result := *status
	return &result, true
}

func (fd *FailureDetector) GetAllNodeStatus() map[string]NodeStatus {
	fd.mu.RLock()
	defer fd.mu.RUnlock()

	result := make(map[string]NodeStatus)
	for name, status := range fd.nodeStatus {
		result[name] = *status
	}
	return result
}

func (fd *FailureDetector) AddFailureListener(listener func(failedNodes []string)) {
	fd.mu.Lock()
	defer fd.mu.Unlock()
	fd.failureListeners = append(fd.failureListeners, listener)
}

func (fd *FailureDetector) AddRecoveryListener(listener func(recoveredNodes []string)) {
	fd.mu.Lock()
	defer fd.mu.Unlock()
	fd.recoveryListeners = append(fd.recoveryListeners, listener)
}

func (fd *FailureDetector) notifyFailure(failedNodes []string) {
	fd.mu.RLock()
	listeners := make([]func([]string), len(fd.failureListeners))
	copy(listeners, fd.failureListeners)
	fd.mu.RUnlock()

	for _, listener := range listeners {
		listener(failedNodes)
	}
}

func (fd *FailureDetector) notifyRecovery(recoveredNodes []string) {
	fd.mu.RLock()
	listeners := make([]func([]string), len(fd.recoveryListeners))
	copy(listeners, fd.recoveryListeners)
	fd.mu.RUnlock()

	for _, listener := range listeners {
		listener(recoveredNodes)
	}
}

func (fd *FailureDetector) ResetNode(nodeName string) {
	fd.mu.Lock()
	defer fd.mu.Unlock()

	if status, exists := fd.nodeStatus[nodeName]; exists {
		status.IsFailed = false
		status.ConsecutiveFailures = 0
		status.FailureCount = 0
		status.LastStateChange = time.Now()
	}
}
