package rollback

import (
	"sync"
	"time"

	"github.com/google/uuid"
	"fault-injection-platform/internal/model"
)

type JaegerClient interface {
	GetServiceMetrics(service string, lookback string) (*model.ServiceMetrics, error)
}

type IstioClient interface {
	StopFaultInjection(faultID string) error
}

type Monitor struct {
	faultID        string
	serviceName    string
	config         *model.RollbackConfig
	jaegerClient   JaegerClient
	istioClient    IstioClient
	stopChan       chan struct{}
	consecutiveFailures int
	lastCheck      time.Time
	status         string
	mu             sync.RWMutex
}

type Manager struct {
	monitors map[string]*Monitor
	mu       sync.RWMutex
}

func NewManager() *Manager {
	return &Manager{
		monitors: make(map[string]*Monitor),
	}
}

func (m *Manager) StartMonitoring(
	faultID string,
	serviceName string,
	config *model.RollbackConfig,
	jaegerClient JaegerClient,
	istioClient IstioClient,
) (*Monitor, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.monitors[faultID]; exists {
		return m.monitors[faultID], nil
	}

	monitor := &Monitor{
		faultID:     faultID,
		serviceName: serviceName,
		config:      config,
		jaegerClient: jaegerClient,
		istioClient:  istioClient,
		stopChan:    make(chan struct{}),
		status:      "monitoring",
		lastCheck:   time.Now(),
	}

	m.monitors[faultID] = monitor
	go monitor.run()

	return monitor, nil
}

func (m *Manager) StopMonitoring(faultID string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if monitor, exists := m.monitors[faultID]; exists {
		close(monitor.stopChan)
		monitor.setStatus("stopped")
		delete(m.monitors, faultID)
	}
}

func (m *Manager) GetMonitorStatus(faultID string) (string, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if monitor, exists := m.monitors[faultID]; exists {
		return monitor.getStatus(), true
	}
	return "", false
}

func (m *Manager) ListActiveMonitors() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]string, 0, len(m.monitors))
	for id := range m.monitors {
		result = append(result, id)
	}
	return result
}

func (mon *Monitor) run() {
	interval := time.Duration(mon.config.CheckIntervalSeconds) * time.Second
	if interval == 0 {
		interval = 10 * time.Second
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-mon.stopChan:
			return
		case <-ticker.C:
			mon.checkAndRollback()
		}
	}
}

func (mon *Monitor) checkAndRollback() *model.RollbackEvent {
	mon.mu.Lock()
	defer mon.mu.Unlock()

	mon.lastCheck = time.Now()

	metrics, err := mon.jaegerClient.GetServiceMetrics(mon.serviceName, "1m")
	if err != nil {
		mon.consecutiveFailures++
		return nil
	}

	if metrics.RequestCount < mon.config.MinRequestCount {
		return nil
	}

	triggered := false
	triggerMetric := ""
	thresholdValue := 0.0
	actualValue := 0.0

	if mon.config.MaxLatencyThreshold > 0 && metrics.P99Latency > mon.config.MaxLatencyThreshold {
		triggered = true
		triggerMetric = "p99_latency"
		thresholdValue = mon.config.MaxLatencyThreshold
		actualValue = metrics.P99Latency
		mon.consecutiveFailures++
	} else if mon.config.MaxErrorRateThreshold > 0 && metrics.ErrorRate > mon.config.MaxErrorRateThreshold {
		triggered = true
		triggerMetric = "error_rate"
		thresholdValue = mon.config.MaxErrorRateThreshold
		actualValue = metrics.ErrorRate
		mon.consecutiveFailures++
	} else {
		mon.consecutiveFailures = 0
	}

	if triggered && mon.consecutiveFailures >= mon.config.ConsecutiveFailures {
		event := mon.performRollback(triggerMetric, thresholdValue, actualValue)
		return event
	}

	return nil
}

func (mon *Monitor) performRollback(triggerMetric string, thresholdValue, actualValue float64) *model.RollbackEvent {
	mon.status = "rolling_back"

	err := mon.istioClient.StopFaultInjection(mon.faultID)
	success := err == nil

	if success {
		mon.status = "rolled_back"
	} else {
		mon.status = "rollback_failed"
	}

	event := &model.RollbackEvent{
		ID:             uuid.New().String(),
		FaultID:        mon.faultID,
		Reason:         "Threshold exceeded",
		TriggerMetric:  triggerMetric,
		ThresholdValue: thresholdValue,
		ActualValue:    actualValue,
		RollbackTime:   time.Now(),
		RollbackSuccess: success,
	}

	close(mon.stopChan)

	return event
}

func (mon *Monitor) getStatus() string {
	mon.mu.RLock()
	defer mon.mu.RUnlock()
	return mon.status
}

func (mon *Monitor) setStatus(status string) {
	mon.mu.Lock()
	defer mon.mu.Unlock()
	mon.status = status
}

func (mon *Monitor) ManualCheck() *model.RollbackEvent {
	return mon.checkAndRollback()
}

func GetDefaultRollbackConfig() *model.RollbackConfig {
	return &model.RollbackConfig{
		Enabled:               true,
		MaxLatencyThreshold:   5000,
		MaxErrorRateThreshold: 20,
		MinRequestCount:       10,
		ConsecutiveFailures:   3,
		CheckIntervalSeconds:  10,
	}
}
