package redis

import (
	"encoding/json"
	"fmt"
	"time"

	"servicemesh-gateway/pkg/models"
)

const (
	trafficMetricsKeyPrefix = "traffic:metrics:"
	topologyKeyPrefix       = "topology:"
	routingRuleKey          = "routing:rules"
)

type TrafficStore struct {
	client *Client
}

func NewTrafficStore(client *Client) *TrafficStore {
	return &TrafficStore{client: client}
}

func (s *TrafficStore) StoreMetrics(metrics *models.TrafficMetrics) error {
	key := fmt.Sprintf("%s%s:%s:%d",
		trafficMetricsKeyPrefix,
		metrics.Namespace,
		metrics.ServiceName,
		metrics.Timestamp.Unix(),
	)

	return s.client.Set(key, metrics, time.Hour*24*7)
}

func (s *TrafficStore) GetMetrics(namespace, serviceName string, startTime, endTime time.Time) ([]*models.TrafficMetrics, error) {
	pattern := fmt.Sprintf("%s%s:%s:*", trafficMetricsKeyPrefix, namespace, serviceName)
	keys, err := s.client.Keys(pattern)
	if err != nil {
		return nil, err
	}

	var metricsList []*models.TrafficMetrics
	for _, key := range keys {
		var metrics models.TrafficMetrics
		if err := s.client.Get(key, &metrics); err != nil {
			continue
		}
		if metrics.Timestamp.After(startTime) && metrics.Timestamp.Before(endTime) {
			metricsList = append(metricsList, &metrics)
		}
	}

	return metricsList, nil
}

func (s *TrafficStore) StoreTopology(namespace string, topology *models.TrafficTopology) error {
	key := fmt.Sprintf("%s%s", topologyKeyPrefix, namespace)
	return s.client.Set(key, topology, time.Minute*5)
}

func (s *TrafficStore) GetTopology(namespace string) (*models.TrafficTopology, error) {
	key := fmt.Sprintf("%s%s", topologyKeyPrefix, namespace)
	var topology models.TrafficTopology
	err := s.client.Get(key, &topology)
	if err != nil {
		return nil, err
	}
	return &topology, nil
}

func (s *TrafficStore) StoreRoutingRule(rule interface{}) error {
	ruleJSON, err := json.Marshal(rule)
	if err != nil {
		return err
	}

	var id, name, namespace string
	switch r := rule.(type) {
	case *models.WeightRouting:
		id = r.ID
		name = r.Name
		namespace = r.Namespace
	case *models.HeaderRouting:
		id = r.ID
		name = r.Name
		namespace = r.Namespace
	case *models.TrafficMirror:
		id = r.ID
		name = r.Name
		namespace = r.Namespace
	case *models.FaultInjection:
		id = r.ID
		name = r.Name
		namespace = r.Namespace
	default:
		return fmt.Errorf("unsupported rule type")
	}

	field := fmt.Sprintf("%s:%s", namespace, id)
	data := map[string]interface{}{
		"id":        id,
		"name":      name,
		"namespace": namespace,
		"data":      string(ruleJSON),
	}

	return s.client.HSet(routingRuleKey, field, data)
}

func (s *TrafficStore) GetRoutingRules(namespace string) ([]map[string]interface{}, error) {
	all, err := s.client.HGetAll(routingRuleKey)
	if err != nil {
		return nil, err
	}

	var rules []map[string]interface{}
	pattern := fmt.Sprintf("%s:", namespace)

	for field, value := range all {
		if len(pattern) > 0 && len(field) >= len(pattern) && field[:len(pattern)] == pattern {
			var ruleData map[string]interface{}
			if err := json.Unmarshal([]byte(value), &ruleData); err != nil {
				continue
			}
			rules = append(rules, ruleData)
		}
	}

	return rules, nil
}

func (s *TrafficStore) DeleteRoutingRule(namespace, id string) error {
	field := fmt.Sprintf("%s:%s", namespace, id)
	return s.client.HDel(routingRuleKey, field)
}

func (s *TrafficStore) GetServiceList(namespace string) ([]string, error) {
	pattern := fmt.Sprintf("%s%s:*", trafficMetricsKeyPrefix, namespace)
	keys, err := s.client.Keys(pattern)
	if err != nil {
		return nil, err
	}

	serviceSet := make(map[string]bool)
	for _, key := range keys {
		parts := splitKey(key)
		if len(parts) >= 4 {
			serviceSet[parts[2]] = true
		}
	}

	var services []string
	for svc := range serviceSet {
		services = append(services, svc)
	}

	return services, nil
}

func splitKey(key string) []string {
	var parts []string
	start := 0
	for i, c := range key {
		if c == ':' {
			if i > start {
				parts = append(parts, key[start:i])
			}
			start = i + 1
		}
	}
	if start < len(key) {
		parts = append(parts, key[start:])
	}
	return parts
}

func (s *TrafficStore) GenerateReport(report *models.TrafficReport) error {
	for i, service := range report.Services {
		metricsList, err := s.GetMetrics(
			report.Services[0].ServiceName,
			service.ServiceName,
			report.StartDate,
			report.EndDate,
		)
		if err != nil {
			continue
		}

		var totalRequests int64
		var totalLatency float64
		var errorCount int64

		for _, m := range metricsList {
			totalRequests += m.RequestCount
			errorCount += m.ErrorCount
			totalLatency += m.P50Latency * float64(m.RequestCount)
		}

		report.Services[i].TotalRequests = totalRequests
		if totalRequests > 0 {
			report.Services[i].ErrorRate = float64(errorCount) / float64(totalRequests) * 100
			report.Services[i].AvgLatency = totalLatency / float64(totalRequests)
		}
	}

	reportKey := fmt.Sprintf("report:%s", report.ID)
	return s.client.Set(reportKey, report, time.Hour*24*30)
}

func (s *TrafficStore) GetReport(id string) (*models.TrafficReport, error) {
	key := fmt.Sprintf("report:%s", id)
	var report models.TrafficReport
	err := s.client.Get(key, &report)
	if err != nil {
		return nil, err
	}
	return &report, nil
}
