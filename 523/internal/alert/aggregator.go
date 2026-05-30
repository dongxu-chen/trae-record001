package alert

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/security/container-escape-detector/pkg/types"
)

type AggregationConfig struct {
	Enabled          bool          `yaml:"enabled"`
	WindowSeconds    int           `yaml:"window_seconds"`
	MaxEventsPerGroup int          `yaml:"max_events_per_group"`
	SendInterval     int           `yaml:"send_interval"`
}

type AlertAggregator struct {
	config       *AggregationConfig
	alertGroups  map[string]*AlertGroup
	mu           sync.RWMutex
	stopChan     chan struct{}
	wg           sync.WaitGroup
	sendCallback func(*AggregatedAlert)
	logger       interface {
		Infof(format string, args ...interface{})
		Debugf(format string, args ...interface{})
	}
}

type AlertGroup struct {
	Key          string
	RuleID       string
	ContainerID  string
	Severity     types.RiskLevel
	Alerts       []*types.Alert
	FirstSeen    time.Time
	LastSeen     time.Time
	TotalCount   int
	UniquePIDs   map[int]bool
	UniqueComms  map[string]bool
	mu           sync.Mutex
}

type AggregatedAlert struct {
	ID             string
	Timestamp      time.Time
	GroupKey       string
	RuleID         string
	RuleName       string
	Severity       types.RiskLevel
	ContainerID    string
	ContainerName  string
	AlertCount     int
	FirstSeen      time.Time
	LastSeen       time.Time
	UniquePIDs     []int
	UniqueComms    []string
	Representative *types.Alert
	AllAlerts      []*types.Alert
	AggregatedEvidence []string
	AggregatedDescription string
}

func NewAlertAggregator(config *AggregationConfig) *AlertAggregator {
	if config == nil {
		config = &AggregationConfig{
			Enabled:          true,
			WindowSeconds:    300,
			MaxEventsPerGroup: 100,
			SendInterval:     60,
		}
	}

	return &AlertAggregator{
		config:      config,
		alertGroups: make(map[string]*AlertGroup),
		stopChan:    make(chan struct{}),
	}
}

func (a *AlertAggregator) SetLogger(logger interface {
	Infof(format string, args ...interface{})
	Debugf(format string, args ...interface{})
}) {
	a.logger = logger
}

func (a *AlertAggregator) SetSendCallback(callback func(*AggregatedAlert)) {
	a.sendCallback = callback
}

func (a *AlertAggregator) Start() {
	if !a.config.Enabled {
		return
	}

	a.wg.Add(1)
	go a.aggregationLoop()

	if a.logger != nil {
		a.logger.Infof("Alert aggregator started with window %ds, send interval %ds",
			a.config.WindowSeconds, a.config.SendInterval)
	}
}

func (a *AlertAggregator) Stop() {
	close(a.stopChan)
	a.wg.Wait()

	a.flushAll()
}

func (a *AlertAggregator) AddAlert(alert *types.Alert) bool {
	if !a.config.Enabled {
		return false
	}

	key := a.buildGroupKey(alert)

	a.mu.Lock()
	group, exists := a.alertGroups[key]
	if !exists {
		group = &AlertGroup{
			Key:         key,
			RuleID:      alert.RuleID,
			ContainerID: alert.ContainerID,
			Severity:    alert.Severity,
			UniquePIDs:  make(map[int]bool),
			UniqueComms: make(map[string]bool),
			FirstSeen:   alert.Timestamp,
		}
		a.alertGroups[key] = group
	}
	a.mu.Unlock()

	group.mu.Lock()
	defer group.mu.Unlock()

	group.Alerts = append(group.Alerts, alert)
	group.TotalCount++
	group.LastSeen = alert.Timestamp
	group.UniquePIDs[alert.ProcessPID] = true
	group.UniqueComms[alert.ProcessComm] = true

	if len(group.Alerts) > a.config.MaxEventsPerGroup {
		group.Alerts = group.Alerts[len(group.Alerts)-a.config.MaxEventsPerGroup:]
	}

	return true
}

func (a *AlertAggregator) buildGroupKey(alert *types.Alert) string {
	return fmt.Sprintf("%s-%s-%s", alert.RuleID, alert.ContainerID, string(alert.Severity))
}

func (a *AlertAggregator) aggregationLoop() {
	defer a.wg.Done()

	ticker := time.NewTicker(time.Duration(a.config.SendInterval) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-a.stopChan:
			return
		case <-ticker.C:
			a.flushExpired()
		}
	}
}

func (a *AlertAggregator) flushExpired() {
	a.mu.Lock()
	defer a.mu.Unlock()

	now := time.Now()
	window := time.Duration(a.config.WindowSeconds) * time.Second

	for key, group := range a.alertGroups {
		group.mu.Lock()

		if now.Sub(group.LastSeen) > window && group.TotalCount > 0 {
			aggregated := a.buildAggregatedAlert(group)
			group.mu.Unlock()

			if a.sendCallback != nil {
				a.sendCallback(aggregated)
			}

			a.mu.Lock()
			delete(a.alertGroups, key)
			a.mu.Unlock()
		} else {
			group.mu.Unlock()
		}
	}
}

func (a *AlertAggregator) flushAll() {
	a.mu.Lock()
	defer a.mu.Unlock()

	for key, group := range a.alertGroups {
		group.mu.Lock()

		if group.TotalCount > 0 {
			aggregated := a.buildAggregatedAlert(group)
			group.mu.Unlock()

			if a.sendCallback != nil {
				a.sendCallback(aggregated)
			}
		} else {
			group.mu.Unlock()
		}

		delete(a.alertGroups, key)
	}
}

func (a *AlertAggregator) buildAggregatedAlert(group *AlertGroup) *AggregatedAlert {
	if len(group.Alerts) == 0 {
		return nil
	}

	representative := group.Alerts[0]
	for _, alert := range group.Alerts {
		if alert.RiskScore > representative.RiskScore {
			representative = alert
		}
	}

	uniquePIDs := make([]int, 0, len(group.UniquePIDs))
	for pid := range group.UniquePIDs {
		uniquePIDs = append(uniquePIDs, pid)
	}
	sort.Ints(uniquePIDs)

	uniqueComms := make([]string, 0, len(group.UniqueComms))
	for comm := range group.UniqueComms {
		uniqueComms = append(uniqueComms, comm)
	}
	sort.Strings(uniqueComms)

	aggregated := &AggregatedAlert{
		ID:             fmt.Sprintf("agg-%s-%d", group.Key, time.Now().Unix()),
		Timestamp:      time.Now(),
		GroupKey:       group.Key,
		RuleID:         group.RuleID,
		RuleName:       representative.Title,
		Severity:       group.Severity,
		ContainerID:    group.ContainerID,
		ContainerName:  representative.ContainerName,
		AlertCount:     group.TotalCount,
		FirstSeen:      group.FirstSeen,
		LastSeen:       group.LastSeen,
		UniquePIDs:     uniquePIDs,
		UniqueComms:    uniqueComms,
		Representative: representative,
		AllAlerts:      make([]*types.Alert, len(group.Alerts)),
	}

	copy(aggregated.AllAlerts, group.Alerts)

	aggregated.AggregatedEvidence = a.buildAggregatedEvidence(group, aggregated)
	aggregated.AggregatedDescription = a.buildAggregatedDescription(group, aggregated)

	return aggregated
}

func (a *AlertAggregator) buildAggregatedEvidence(group *AlertGroup, aggregated *AggregatedAlert) []string {
	var evidence []string

	evidence = append(evidence,
		fmt.Sprintf("Aggregated %d alerts in %v window (from %s to %s)",
			aggregated.AlertCount,
			aggregated.LastSeen.Sub(aggregated.FirstSeen),
			aggregated.FirstSeen.Format(time.RFC3339),
			aggregated.LastSeen.Format(time.RFC3339)))

	if len(aggregated.UniquePIDs) > 1 {
		evidence = append(evidence,
			fmt.Sprintf("Involved PIDs (%d total): %v", len(aggregated.UniquePIDs), aggregated.UniquePIDs))
	}

	if len(aggregated.UniqueComms) > 1 {
		evidence = append(evidence,
			fmt.Sprintf("Involved processes (%d total): %v", len(aggregated.UniqueComms), aggregated.UniqueComms))
	}

	for i, alert := range group.Alerts {
		if i >= 5 {
			evidence = append(evidence, fmt.Sprintf("... and %d more alerts", len(group.Alerts)-5))
			break
		}
		evidence = append(evidence, fmt.Sprintf("Alert #%d: %s (PID: %d, Score: %.1f)",
			i+1, alert.ProcessComm, alert.ProcessPID, alert.RiskScore))
	}

	if aggregated.Representative.Evidence != nil && len(aggregated.Representative.Evidence) > 0 {
		evidence = append(evidence, "Key evidence:")
		for i, ev := range aggregated.Representative.Evidence {
			if i >= 3 {
				break
			}
			evidence = append(evidence, "  - "+ev)
		}
	}

	return evidence
}

func (a *AlertAggregator) buildAggregatedDescription(group *AlertGroup, aggregated *AggregatedAlert) string {
	var parts []string

	parts = append(parts, fmt.Sprintf("%d occurrence(s) of %s",
		aggregated.AlertCount, aggregated.RuleName))

	if len(aggregated.UniquePIDs) > 1 {
		parts = append(parts, fmt.Sprintf("affecting %d PIDs", len(aggregated.UniquePIDs)))
	}

	if len(aggregated.UniqueComms) > 1 {
		parts = append(parts, fmt.Sprintf("across %d processes", len(aggregated.UniqueComms)))
	}

	duration := aggregated.LastSeen.Sub(aggregated.FirstSeen)
	if duration > 10*time.Second {
		parts = append(parts, fmt.Sprintf("over %v", duration))
	}

	return strings.Join(parts, " ")
}

func (a *AlertAggregator) GetGroupStats() map[string]interface{} {
	a.mu.RLock()
	defer a.mu.RUnlock()

	stats := make(map[string]interface{})
	stats["active_groups"] = len(a.alertGroups)

	bySeverity := make(map[types.RiskLevel]int)
	totalAlerts := 0

	for _, group := range a.alertGroups {
		group.mu.Lock()
		bySeverity[group.Severity]++
		totalAlerts += group.TotalCount
		group.mu.Unlock()
	}

	stats["by_severity"] = bySeverity
	stats["total_queued_alerts"] = totalAlerts

	return stats
}
