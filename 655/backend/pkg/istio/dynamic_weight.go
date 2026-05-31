package istio

import (
	"context"
	"fmt"
	"math"
	"sync"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/kubernetes"

	"servicemesh-gateway/pkg/models"
)

const (
	targetAccuracy = 0.03
	adjustInterval = 10 * time.Second
)

type DynamicWeightRouter struct {
	istioClient *Client
	kubeClient  *kubernetes.Clientset
	weightRules map[string]*DynamicWeightRule
	mu          sync.RWMutex
	stopCh      chan struct{}
}

type DynamicWeightRule struct {
	ID          string
	Name        string
	Namespace   string
	ServiceName string
	Subsets     []DynamicSubset
	AutoAdjust  bool
	LastUpdated time.Time
}

type DynamicSubset struct {
	Name          string
	Version       string
	InstanceCount int
	TargetWeight  int
	CurrentWeight int
	MinWeight     int
	MaxWeight     int
}

func NewDynamicWeightRouter(istioClient *Client, kubeClient *kubernetes.Clientset) *DynamicWeightRouter {
	dwr := &DynamicWeightRouter{
		istioClient: istioClient,
		kubeClient:  kubeClient,
		weightRules: make(map[string]*DynamicWeightRule),
		stopCh:      make(chan struct{}),
	}

	go dwr.autoAdjustLoop()

	return dwr
}

func (dwr *DynamicWeightRouter) AddDynamicRule(rule *models.WeightRouting, autoAdjust bool) error {
	dr := &DynamicWeightRule{
		ID:          rule.ID,
		Name:        rule.Name,
		Namespace:   rule.Namespace,
		ServiceName: rule.ServiceName,
		Subsets:     make([]DynamicSubset, len(rule.Subsets)),
		AutoAdjust:  autoAdjust,
		LastUpdated: time.Now(),
	}

	for i, s := range rule.Subsets {
		dr.Subsets[i] = DynamicSubset{
			Name:          s.SubsetName,
			Version:       s.Version,
			InstanceCount: 1,
			TargetWeight:  s.Weight,
			CurrentWeight: s.Weight,
			MinWeight:     5,
			MaxWeight:     95,
		}
	}

	dwr.mu.Lock()
	dwr.weightRules[rule.ID] = dr
	dwr.mu.Unlock()

	if autoAdjust {
		go dwr.adjustWeightsForRule(dr)
	}

	return nil
}

func (dwr *DynamicWeightRouter) RemoveDynamicRule(id string) {
	dwr.mu.Lock()
	delete(dwr.weightRules, id)
	dwr.mu.Unlock()
}

func (dwr *DynamicWeightRouter) autoAdjustLoop() {
	ticker := time.NewTicker(adjustInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			dwr.adjustAllRules()
		case <-dwr.stopCh:
			return
		}
	}
}

func (dwr *DynamicWeightRouter) adjustAllRules() {
	dwr.mu.RLock()
	rules := make([]*DynamicWeightRule, 0, len(dwr.weightRules))
	for _, r := range dwr.weightRules {
		if r.AutoAdjust {
			rules = append(rules, r)
		}
	}
	dwr.mu.RUnlock()

	for _, rule := range rules {
		if err := dwr.adjustWeightsForRule(rule); err != nil {
			fmt.Printf("Failed to adjust weights for rule %s: %v\n", rule.ID, err)
		}
	}
}

func (dwr *DynamicWeightRouter) adjustWeightsForRule(rule *DynamicWeightRule) error {
	instanceCounts, err := dwr.getInstanceCounts(rule)
	if err != nil {
		return fmt.Errorf("failed to get instance counts: %w", err)
	}

	totalInstances := 0
	for _, count := range instanceCounts {
		totalInstances += count
	}

	if totalInstances == 0 {
		return fmt.Errorf("no instances found for service %s", rule.ServiceName)
	}

	targetWeights := make(map[string]int)
	for i, subset := range rule.Subsets {
		count := instanceCounts[subset.Name]
		rule.Subsets[i].InstanceCount = count

		if count == 0 {
			targetWeights[subset.Name] = subset.MinWeight
		} else {
			weight := int(math.Round(float64(count) / float64(totalInstances) * 100))
			weight = dwr.clampWeight(weight, subset.MinWeight, subset.MaxWeight)
			targetWeights[subset.Name] = weight
		}
	}

	normalizedWeights := dwr.normalizeWeights(targetWeights)

	needsUpdate := false
	for i, subset := range rule.Subsets {
		target := normalizedWeights[subset.Name]
		diff := math.Abs(float64(target - subset.CurrentWeight))

		if diff > targetAccuracy*100 {
			rule.Subsets[i].CurrentWeight = target
			needsUpdate = true
		}
	}

	if needsUpdate {
		if err := dwr.applyWeightsToIstio(rule); err != nil {
			return fmt.Errorf("failed to apply weights: %w", err)
		}
		rule.LastUpdated = time.Now()
	}

	return nil
}

func (dwr *DynamicWeightRouter) getInstanceCounts(rule *DynamicWeightRule) (map[string]int, error) {
	counts := make(map[string]int)

	for _, subset := range rule.Subsets {
		labelSelector := fmt.Sprintf("app=%s,version=%s", rule.ServiceName, subset.Version)
		pods, err := dwr.kubeClient.CoreV1().Pods(rule.Namespace).List(
			context.Background(),
			metav1.ListOptions{
				LabelSelector: labelSelector,
				FieldSelector: "status.phase=Running",
			},
		)
		if err != nil {
			return nil, err
		}

		readyCount := 0
		for _, pod := range pods.Items {
			for _, cond := range pod.Status.Conditions {
				if cond.Type == "Ready" && cond.Status == "True" {
					readyCount++
					break
				}
			}
		}
		counts[subset.Name] = readyCount
	}

	return counts, nil
}

func (dwr *DynamicWeightRouter) normalizeWeights(weights map[string]int) map[string]int {
	total := 0
	for _, w := range weights {
		total += w
	}

	if total == 0 {
		equalWeight := 100 / len(weights)
		result := make(map[string]int)
		for name := range weights {
			result[name] = equalWeight
		}
		return result
	}

	if total == 100 {
		return weights
	}

	result := make(map[string]int)
	remaining := 100
	names := make([]string, 0, len(weights))

	for name := range weights {
		names = append(names, name)
	}

	for i, name := range names {
		if i == len(names)-1 {
			result[name] = remaining
		} else {
			normalized := int(math.Round(float64(weights[name]) / float64(total) * 100))
			result[name] = normalized
			remaining -= normalized
		}
	}

	return result
}

func (dwr *DynamicWeightRouter) clampWeight(weight, min, max int) int {
	if weight < min {
		return min
	}
	if weight > max {
		return max
	}
	return weight
}

func (dwr *DynamicWeightRouter) applyWeightsToIstio(rule *DynamicWeightRule) error {
	weightRouting := &models.WeightRouting{
		RoutingRule: models.RoutingRule{
			ID:          rule.ID,
			Name:        rule.Name,
			Namespace:   rule.Namespace,
			Type:        "weight",
			ServiceName: rule.ServiceName,
			Status:      "active",
		},
		Subsets: make([]models.SubsetWeight, len(rule.Subsets)),
	}

	for i, s := range rule.Subsets {
		weightRouting.Subsets[i] = models.SubsetWeight{
			SubsetName: s.Name,
			Weight:     s.CurrentWeight,
			Version:    s.Version,
		}
	}

	return dwr.istioClient.ApplyWeightRouting(weightRouting)
}

func (dwr *DynamicWeightRouter) GetRule(id string) (*DynamicWeightRule, bool) {
	dwr.mu.RLock()
	defer dwr.mu.RUnlock()
	rule, ok := dwr.weightRules[id]
	return rule, ok
}

func (dwr *DynamicWeightRouter) GetAllRules() []*DynamicWeightRule {
	dwr.mu.RLock()
	defer dwr.mu.RUnlock()

	rules := make([]*DynamicWeightRule, 0, len(dwr.weightRules))
	for _, r := range dwr.weightRules {
		rules = append(rules, r)
	}
	return rules
}

func (dwr *DynamicWeightRouter) Stop() {
	close(dwr.stopCh)
}
