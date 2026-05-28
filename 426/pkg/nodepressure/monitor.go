package nodepressure

import (
	"context"
	"fmt"
	"sync"
	"time"

	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"

	"container-autoscaler/pkg/config"
	"container-autoscaler/pkg/types"
	"container-autoscaler/pkg/utils"
)

type NodePressureMonitor struct {
	client          kubernetes.Interface
	config          config.NodePressureConfig
	logger          *utils.Logger
	nodePressures   map[string]*types.NodePressure
	scheduledAdjustments []types.ScheduledAdjustment
	lock            sync.RWMutex
	lastUpdate      time.Time
}

func NewNodePressureMonitor(
	client kubernetes.Interface,
	cfg config.NodePressureConfig,
	logger *utils.Logger,
) *NodePressureMonitor {
	return &NodePressureMonitor{
		client:          client,
		config:          cfg,
		logger:          logger,
		nodePressures:   make(map[string]*types.NodePressure),
		scheduledAdjustments: make([]types.ScheduledAdjustment, 0),
	}
}

func (m *NodePressureMonitor) RefreshNodePressures(ctx context.Context) error {
	nodes, err := m.client.CoreV1().Nodes().List(ctx, metav1.ListOptions{})
	if err != nil {
		return fmt.Errorf("listing nodes: %w", err)
	}

	m.lock.Lock()
	defer m.lock.Unlock()

	for _, node := range nodes.Items {
		pressure := m.analyzeNodePressure(node)
		m.nodePressures[node.Name] = pressure
	}

	now := time.Now()
	activeScheduled := make([]types.ScheduledAdjustment, 0)
	for _, adj := range m.scheduledAdjustments {
		if adj.ScheduledTime.After(now) {
			activeScheduled = append(activeScheduled, adj)
		}
	}
	m.scheduledAdjustments = activeScheduled

	for nodeName, pressure := range m.nodePressures {
		count := 0
		for _, adj := range m.scheduledAdjustments {
			pod, err := m.client.CoreV1().Pods(adj.Namespace).Get(ctx, adj.PodName, metav1.GetOptions{})
			if err == nil && pod.Spec.NodeName == nodeName {
				count++
			}
		}
		pressure.PendingAdjustments = count
	}

	m.lastUpdate = time.Now()
	return nil
}

func (m *NodePressureMonitor) analyzeNodePressure(node corev1.Node) *types.NodePressure {
	pressure := &types.NodePressure{
		NodeName:      node.Name,
		LastUpdate:    time.Now(),
		Unschedulable: node.Spec.Unschedulable,
	}

	allocatable := node.Status.Allocatable
	capacity := node.Status.Capacity

	if cpu, ok := allocatable[corev1.ResourceCPU]; ok {
		pressure.AllocatableCPU = float64(cpu.MilliValue())
	}
	if mem, ok := allocatable[corev1.ResourceMemory]; ok {
		pressure.AllocatableMemory = float64(mem.Value()) / (1024 * 1024)
	}

	if cpu, ok := capacity[corev1.ResourceCPU]; ok {
		pressure.TotalCPU = float64(cpu.MilliValue())
	}
	if mem, ok := capacity[corev1.ResourceMemory]; ok {
		pressure.TotalMemory = float64(mem.Value()) / (1024 * 1024)
	}

	for _, condition := range node.Status.Conditions {
		switch condition.Type {
		case corev1.NodeReady:
		case corev1.NodeMemoryPressure:
			pressure.MemoryPressure = condition.Status == corev1.ConditionTrue
		case corev1.NodeDiskPressure:
			pressure.DiskPressure = condition.Status == corev1.ConditionTrue
		case corev1.NodePIDPressure:
			pressure.PIDPressure = condition.Status == corev1.ConditionTrue
		}
	}

	return pressure
}

func (m *NodePressureMonitor) GetNodePressure(nodeName string) (*types.NodePressure, bool) {
	m.lock.RLock()
	defer m.lock.RUnlock()

	pressure, ok := m.nodePressures[nodeName]
	return pressure, ok
}

func (m *NodePressureMonitor) GetAllNodePressures() map[string]*types.NodePressure {
	m.lock.RLock()
	defer m.lock.RUnlock()

	result := make(map[string]*types.NodePressure)
	for k, v := range m.nodePressures {
		result[k] = v
	}
	return result
}

func (m *NodePressureMonitor) CheckAndScheduleAdjustment(
	ctx context.Context,
	namespace string,
	podName string,
	containerName string,
	nodeName string,
	resourceType corev1.ResourceName,
	newLimit float64,
	newRequest float64,
	currentLimit float64,
	reason string,
	confidence float64,
) (bool, time.Time, string) {
	isUpscale := newLimit > currentLimit

	if !isUpscale {
		return true, time.Time{}, ""
	}

	pressure, ok := m.GetNodePressure(nodeName)
	if !ok {
		return true, time.Time(), "node pressure data not available, allowing adjustment"
	}

	var utilization float64
	switch resourceType {
	case corev1.ResourceCPU:
		utilization = pressure.CPUUtilization
	case corev1.ResourceMemory:
		utilization = pressure.MemoryUtilization
	}

	threshold := m.config.CPUThreshold
	if resourceType == corev1.ResourceMemory {
		threshold = m.config.MemoryThreshold
	}

	if utilization >= threshold || pressure.MemoryPressure || pressure.DiskPressure || pressure.PIDPressure {
		scheduledTime := time.Now().Add(m.config.StaggerDelay)
		adjID := fmt.Sprintf("sched-%d", time.Now().UnixNano())

		m.lock.Lock()
		m.scheduledAdjustments = append(m.scheduledAdjustments, types.ScheduledAdjustment{
			ID:            adjID,
			ScheduledTime: scheduledTime,
			Namespace:     namespace,
			PodName:       podName,
			ContainerName: containerName,
			ResourceType:  resourceType,
			NewLimit:      newLimit,
			NewRequest:    newRequest,
			Reason:        reason,
			Confidence:    confidence,
			Priority:      int(confidence * 100),
		})
		m.lock.Unlock()

		m.logger.Info(
			"Node %s under pressure (utilization: %.0f%%), scheduling upscale for %s/%s/%s at %s",
			nodeName, utilization*100, namespace, podName, containerName,
			scheduledTime.Format(time.RFC3339),
		)

		return false, scheduledTime, adjID
	}

	nodeUpscaleCount := m.countNodePendingUpscales(nodeName, resourceType)
	if nodeUpscaleCount >= m.config.MaxConcurrentUpscales {
		scheduledTime := time.Now().Add(m.config.StaggerDelay * time.Duration(nodeUpscaleCount))
		adjID := fmt.Sprintf("sched-%d", time.Now().UnixNano())

		m.lock.Lock()
		m.scheduledAdjustments = append(m.scheduledAdjustments, types.ScheduledAdjustment{
			ID:            adjID,
			ScheduledTime: scheduledTime,
			Namespace:     namespace,
			PodName:       podName,
			ContainerName: containerName,
			ResourceType:  resourceType,
			NewLimit:      newLimit,
			NewRequest:    newRequest,
			Reason:        reason,
			Confidence:    confidence,
			Priority:      int(confidence * 100),
		})
		m.lock.Unlock()

		m.logger.Info(
			"Node %s has %d pending upscales (max: %d), scheduling %s/%s/%s at %s",
			nodeName, nodeUpscaleCount, m.config.MaxConcurrentUpscales,
			namespace, podName, containerName, scheduledTime.Format(time.RFC3339),
		)

		return false, scheduledTime, adjID
	}

	return true, time.Time{}, ""
}

func (m *NodePressureMonitor) countNodePendingUpscales(nodeName string, resourceType corev1.ResourceName) int {
	m.lock.RLock()
	defer m.lock.RUnlock()

	count := 0
	for _, adj := range m.scheduledAdjustments {
		pod, err := m.client.CoreV1().Pods(adj.Namespace).Get(context.TODO(), adj.PodName, metav1.GetOptions{})
		if err == nil && pod.Spec.NodeName == nodeName && adj.ResourceType == resourceType {
			count++
		}
	}
	return count
}

func (m *NodePressureMonitor) GetScheduledAdjustments(nodeName string) []types.ScheduledAdjustment {
	m.lock.RLock()
	defer m.lock.RUnlock()

	result := make([]types.ScheduledAdjustment, 0)
	for _, adj := range m.scheduledAdjustments {
		if nodeName == "" {
			result = append(result, adj)
			continue
		}
		pod, err := m.client.CoreV1().Pods(adj.Namespace).Get(context.TODO(), adj.PodName, metav1.GetOptions{})
		if err == nil && pod.Spec.NodeName == nodeName {
			result = append(result, adj)
		}
	}
	return result
}

func (m *NodePressureMonitor) GetDueAdjustments() []types.ScheduledAdjustment {
	m.lock.RLock()
	defer m.lock.RUnlock()

	now := time.Now()
	result := make([]types.ScheduledAdjustment, 0)

	for _, adj := range m.scheduledAdjustments {
		if adj.ScheduledTime.Before(now) || adj.ScheduledTime.Equal(now) {
			result = append(result, adj)
		}
	}

	return result
}

func (m *NodePressureMonitor) RemoveScheduledAdjustment(adjID string) bool {
	m.lock.Lock()
	defer m.lock.Unlock()

	for i, adj := range m.scheduledAdjustments {
		if adj.ID == adjID {
			m.scheduledAdjustments = append(m.scheduledAdjustments[:i], m.scheduledAdjustments[i+1:]...)
			return true
		}
	}
	return false
}

func (m *NodePressureMonitor) UpdatePodResourceUsage(
	ctx context.Context,
	namespace string,
	podName string,
	nodeName string,
	cpuUsage float64,
	memoryUsage float64,
	cpuLimit float64,
	memoryLimit float64,
) {
	m.lock.Lock()
	defer m.lock.Unlock()

	pressure, ok := m.nodePressures[nodeName]
	if !ok {
		return
	}

	pressure.UsedCPU += cpuUsage
	pressure.UsedMemory += memoryUsage
	pressure.PodCount++

	if pressure.AllocatableCPU > 0 {
		pressure.CPUUtilization = pressure.UsedCPU / pressure.AllocatableCPU
	}
	if pressure.AllocatableMemory > 0 {
		pressure.MemoryUtilization = pressure.UsedMemory / pressure.AllocatableMemory
	}

	var utilization float64
	if cpuLimit > 0 {
		utilization = cpuUsage / cpuLimit
	}
	if memoryLimit > 0 && memoryUsage/memoryLimit > utilization {
		utilization = memoryUsage / memoryLimit
	}

	if utilization > 0.8 {
		pressure.HighUtilizationPods = append(pressure.HighUtilizationPods, types.PodRef{
			Namespace:       namespace,
			PodName:         podName,
			ContainerName:   "",
			CPUUsage:        cpuUsage,
			MemoryUsage:     memoryUsage,
			CPULimit:        cpuLimit,
			MemoryLimit:     memoryLimit,
		})
	}
}

func (m *NodePressureMonitor) ResetPodUsage() {
	m.lock.Lock()
	defer m.lock.Unlock()

	for _, pressure := range m.nodePressures {
		pressure.UsedCPU = 0
		pressure.UsedMemory = 0
		pressure.PodCount = 0
		pressure.HighUtilizationPods = nil
	}
}

func (m *NodePressureMonitor) IsNodeSafeForUpscale(nodeName string, resourceType corev1.ResourceName) bool {
	pressure, ok := m.GetNodePressure(nodeName)
	if !ok {
		return true
	}

	if pressure.Unschedulable {
		return false
	}

	if pressure.MemoryPressure || pressure.DiskPressure || pressure.PIDPressure {
		return false
	}

	var utilization float64
	var threshold float64

	switch resourceType {
	case corev1.ResourceCPU:
		utilization = pressure.CPUUtilization
		threshold = m.config.CPUThreshold
	case corev1.ResourceMemory:
		utilization = pressure.MemoryUtilization
		threshold = m.config.MemoryThreshold
	default:
		utilization = pressure.CPUUtilization
		threshold = m.config.CPUThreshold
	}

	return utilization < threshold*0.9
}

func (m *NodePressureMonitor) PrintNodePressureSummary() {
	m.lock.RLock()
	defer m.lock.RUnlock()

	m.logger.Info("=== Node Pressure Summary ===")
	for nodeName, pressure := range m.nodePressures {
		status := "HEALTHY"
		if pressure.MemoryPressure || pressure.DiskPressure || pressure.PIDPressure {
			status = "PRESSURE"
		} else if pressure.CPUUtilization > m.config.CPUThreshold || pressure.MemoryUtilization > m.config.MemoryThreshold {
			status = "HIGH_UTIL"
		}

		m.logger.Info(
			"Node %s: %s | CPU: %.0f%% | Memory: %.0f%% | Pods: %d | Pending Adjustments: %d",
			nodeName, status,
			pressure.CPUUtilization*100,
			pressure.MemoryUtilization*100,
			pressure.PodCount,
			pressure.PendingAdjustments,
		)
	}
	m.logger.Info("============================")
}
