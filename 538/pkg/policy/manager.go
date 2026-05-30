package policy

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"sync"
	"time"

	v1 "k8s.io/api/networking/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s-network-policy-recommender/pkg/k8s"
	"k8s-network-policy-recommender/pkg/neo4jclient"
)

type PolicyBackup struct {
	ID         string              `json:"id"`
	Name       string              `json:"name"`
	Namespace  string              `json:"namespace"`
	CreatedAt  time.Time           `json:"createdAt"`
	Reason     string              `json:"reason"`
	Policies   []v1.NetworkPolicy  `json:"policies"`
	FlowSnapshot *FlowSnapshot     `json:"flowSnapshot,omitempty"`
	PolicyHash string              `json:"policyHash"`
}

type FlowSnapshot struct {
	Timestamp time.Time          `json:"timestamp"`
	Flows     []neo4jclient.FlowEdge `json:"flows"`
	FlowHash  string             `json:"flowHash"`
}

type ApplyResult struct {
	PolicyName string `json:"policyName"`
	Status     string `json:"status"`
	Error      string `json:"error,omitempty"`
}

type BatchApplyResult struct {
	BackupID      string        `json:"backupId"`
	TotalPolicies int           `json:"totalPolicies"`
	SuccessCount  int           `json:"successCount"`
	FailedCount   int           `json:"failedCount"`
	Results       []ApplyResult `json:"results"`
}

type EffectEvaluation struct {
	BackupID          string           `json:"backupId"`
	BeforeSnapshot    *FlowSnapshot    `json:"beforeSnapshot"`
	AfterSnapshot     *FlowSnapshot    `json:"afterSnapshot"`
	NewFlows          []TrafficSummary `json:"newFlows"`
	LostFlows         []TrafficSummary `json:"lostFlows"`
	ChangedFlows      []TrafficDelta   `json:"changedFlows"`
	TotalFlowsBefore  int              `json:"totalFlowsBefore"`
	TotalFlowsAfter   int              `json:"totalFlowsAfter"`
	BlockedFlowCount  int              `json:"blockedFlowCount"`
	NewFlowCount      int              `json:"newFlowCount"`
	EvaluationTime    time.Time        `json:"evaluationTime"`
}

type TrafficSummary struct {
	Source      string `json:"source"`
	Destination string `json:"destination"`
	Protocol    string `json:"protocol"`
	Port        int    `json:"port"`
	Count       int    `json:"count"`
	LastSeen    string `json:"lastSeen"`
}

type TrafficDelta struct {
	TrafficSummary
	CountBefore int `json:"countBefore"`
	CountAfter  int `json:"countAfter"`
	Delta       int `json:"delta"`
}

type PolicyManager struct {
	k8sClient *k8s.Client
	neo4j     *neo4jclient.Client
	backups   map[string]*PolicyBackup
	mu        sync.RWMutex
}

func NewPolicyManager(k8sClient *k8s.Client, neo4j *neo4jclient.Client) *PolicyManager {
	return &PolicyManager{
		k8sClient: k8sClient,
		neo4j:     neo4j,
		backups:   make(map[string]*PolicyBackup),
	}
}

func (pm *PolicyManager) CreateBackup(ctx context.Context, namespace, reason string) (*PolicyBackup, error) {
	policies, err := pm.k8sClient.GetNetworkPolicies(ctx, namespace)
	if err != nil {
		return nil, fmt.Errorf("failed to get policies: %w", err)
	}

	flows, err := pm.neo4j.GetFlowsByNamespace(ctx, namespace)
	if err != nil {
		return nil, fmt.Errorf("failed to get flows: %w", err)
	}

	policyHash, err := hashPolicies(policies)
	if err != nil {
		return nil, fmt.Errorf("failed to hash policies: %w", err)
	}

	flowHash := hashFlows(flows)

	backupID := fmt.Sprintf("backup-%d-%s", time.Now().Unix(), policyHash[:8])

	snapshot := &FlowSnapshot{
		Timestamp: time.Now(),
		Flows:     flows,
		FlowHash:  flowHash,
	}

	backup := &PolicyBackup{
		ID:           backupID,
		Name:         fmt.Sprintf("%s-%s", namespace, time.Now().Format("20060102-150405")),
		Namespace:    namespace,
		CreatedAt:    time.Now(),
		Reason:       reason,
		Policies:     policies,
		FlowSnapshot: snapshot,
		PolicyHash:   policyHash,
	}

	pm.mu.Lock()
	pm.backups[backupID] = backup
	pm.mu.Unlock()

	return backup, nil
}

func (pm *PolicyManager) GetBackups(namespace string) []*PolicyBackup {
	pm.mu.RLock()
	defer pm.mu.RUnlock()

	var result []*PolicyBackup
	for _, b := range pm.backups {
		if namespace == "" || b.Namespace == namespace {
			result = append(result, b)
		}
	}

	sort.Slice(result, func(i, j int) bool {
		return result[i].CreatedAt.After(result[j].CreatedAt)
	})

	return result
}

func (pm *PolicyManager) GetBackup(backupID string) (*PolicyBackup, bool) {
	pm.mu.RLock()
	defer pm.mu.RUnlock()
	b, ok := pm.backups[backupID]
	return b, ok
}

func (pm *PolicyManager) Rollback(ctx context.Context, backupID string) error {
	pm.mu.RLock()
	backup, ok := pm.backups[backupID]
	pm.mu.RUnlock()

	if !ok {
		return fmt.Errorf("backup %s not found", backupID)
	}

	currentPolicies, err := pm.k8sClient.GetNetworkPolicies(ctx, backup.Namespace)
	if err != nil {
		return fmt.Errorf("failed to get current policies: %w", err)
	}

	currentPolicyNames := make(map[string]bool)
	for _, p := range currentPolicies {
		currentPolicyNames[p.Name] = true
	}

	backupPolicyNames := make(map[string]bool)
	for _, p := range backup.Policies {
		backupPolicyNames[p.Name] = true
	}

	for name := range currentPolicyNames {
		if !backupPolicyNames[name] {
			if err := pm.k8sClient.DeleteNetworkPolicy(ctx, backup.Namespace, name); err != nil {
				return fmt.Errorf("failed to delete policy %s: %w", name, err)
			}
		}
	}

	for _, policy := range backup.Policies {
		p := policy
		p.ResourceVersion = ""
		p.UID = ""
		p.Generation = 0
		p.CreationTimestamp = metav1.Time{}
		p.ManagedFields = nil

		if err := pm.k8sClient.ApplyNetworkPolicy(ctx, backup.Namespace, &p); err != nil {
			return fmt.Errorf("failed to restore policy %s: %w", p.Name, err)
		}
	}

	return nil
}

func (pm *PolicyManager) BatchApply(ctx context.Context, namespace string, recommendations []PolicyRecommendation) (*BatchApplyResult, error) {
	backup, err := pm.CreateBackup(ctx, namespace, "pre-batch-apply")
	if err != nil {
		return nil, fmt.Errorf("failed to create backup: %w", err)
	}

	result := &BatchApplyResult{
		BackupID:      backup.ID,
		TotalPolicies: len(recommendations),
		Results:       make([]ApplyResult, 0, len(recommendations)),
	}

	for _, rec := range recommendations {
		policy := rec.Policy
		policy.Namespace = namespace

		applyRes := ApplyResult{
			PolicyName: rec.Name,
			Status:     "success",
		}

		if err := pm.k8sClient.ApplyNetworkPolicy(ctx, namespace, &policy); err != nil {
			applyRes.Status = "failed"
			applyRes.Error = err.Error()
			result.FailedCount++
		} else {
			result.SuccessCount++
		}

		result.Results = append(result.Results, applyRes)
	}

	return result, nil
}

func (pm *PolicyManager) TakeFlowSnapshot(ctx context.Context, namespace string) (*FlowSnapshot, error) {
	flows, err := pm.neo4j.GetFlowsByNamespace(ctx, namespace)
	if err != nil {
		return nil, fmt.Errorf("failed to get flows: %w", err)
	}

	return &FlowSnapshot{
		Timestamp: time.Now(),
		Flows:     flows,
		FlowHash:  hashFlows(flows),
	}, nil
}

func (pm *PolicyManager) EvaluateEffect(ctx context.Context, namespace, backupID string, waitSeconds int) (*EffectEvaluation, error) {
	pm.mu.RLock()
	backup, ok := pm.backups[backupID]
	pm.mu.RUnlock()

	if !ok {
		return nil, fmt.Errorf("backup %s not found", backupID)
	}

	if backup.FlowSnapshot == nil {
		return nil, fmt.Errorf("backup %s has no flow snapshot", backupID)
	}

	if waitSeconds > 0 {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(time.Duration(waitSeconds) * time.Second):
		}
	}

	afterSnapshot, err := pm.TakeFlowSnapshot(ctx, namespace)
	if err != nil {
		return nil, fmt.Errorf("failed to take after snapshot: %w", err)
	}

	return compareSnapshots(backup.FlowSnapshot, afterSnapshot, backupID), nil
}

func (pm *PolicyManager) EvaluateWithBeforeSnapshot(ctx context.Context, namespace string, before *FlowSnapshot, waitSeconds int) (*EffectEvaluation, error) {
	if waitSeconds > 0 {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(time.Duration(waitSeconds) * time.Second):
		}
	}

	afterSnapshot, err := pm.TakeFlowSnapshot(ctx, namespace)
	if err != nil {
		return nil, fmt.Errorf("failed to take after snapshot: %w", err)
	}

	return compareSnapshots(before, afterSnapshot, ""), nil
}

func compareSnapshots(before, after *FlowSnapshot, backupID string) *EffectEvaluation {
	beforeMap := make(map[string]TrafficSummary)
	for _, f := range before.Flows {
		key := flowKey(f)
		beforeMap[key] = TrafficSummary{
			Source:      fmt.Sprintf("%s/%s", f.SourceNamespace, f.SourceName),
			Destination: fmt.Sprintf("%s/%s", f.DestNamespace, f.DestName),
			Protocol:    f.Protocol,
			Port:        f.Port,
			Count:       f.Count,
			LastSeen:    f.LastSeen,
		}
	}

	afterMap := make(map[string]TrafficSummary)
	for _, f := range after.Flows {
		key := flowKey(f)
		afterMap[key] = TrafficSummary{
			Source:      fmt.Sprintf("%s/%s", f.SourceNamespace, f.SourceName),
			Destination: fmt.Sprintf("%s/%s", f.DestNamespace, f.DestName),
			Protocol:    f.Protocol,
			Port:        f.Port,
			Count:       f.Count,
			LastSeen:    f.LastSeen,
		}
	}

	eval := &EffectEvaluation{
		BackupID:         backupID,
		BeforeSnapshot:   before,
		AfterSnapshot:    after,
		TotalFlowsBefore: len(beforeMap),
		TotalFlowsAfter:  len(afterMap),
		EvaluationTime:   time.Now(),
	}

	for key, beforeFlow := range beforeMap {
		if afterFlow, ok := afterMap[key]; ok {
			if beforeFlow.Count != afterFlow.Count {
				delta := afterFlow.Count - beforeFlow.Count
				if delta < 0 {
					eval.BlockedFlowCount++
				}
				eval.ChangedFlows = append(eval.ChangedFlows, TrafficDelta{
					TrafficSummary: afterFlow,
					CountBefore:    beforeFlow.Count,
					CountAfter:     afterFlow.Count,
					Delta:          delta,
				})
			}
		} else {
			eval.LostFlows = append(eval.LostFlows, beforeFlow)
			eval.BlockedFlowCount++
		}
	}

	for key, afterFlow := range afterMap {
		if _, ok := beforeMap[key]; !ok {
			eval.NewFlows = append(eval.NewFlows, afterFlow)
			eval.NewFlowCount++
		}
	}

	sort.Slice(eval.LostFlows, func(i, j int) bool {
		return eval.LostFlows[i].Count > eval.LostFlows[j].Count
	})
	sort.Slice(eval.NewFlows, func(i, j int) bool {
		return eval.NewFlows[i].Count > eval.NewFlows[j].Count
	})
	sort.Slice(eval.ChangedFlows, func(i, j int) bool {
		return abs(eval.ChangedFlows[i].Delta) > abs(eval.ChangedFlows[j].Delta)
	})

	return eval
}

func flowKey(f neo4jclient.FlowEdge) string {
	return fmt.Sprintf("%s/%s->%s/%s|%s:%d",
		f.SourceNamespace, f.SourceName,
		f.DestNamespace, f.DestName,
		f.Protocol, f.Port)
}

func hashPolicies(policies []v1.NetworkPolicy) (string, error) {
	sorted := make([]v1.NetworkPolicy, len(policies))
	copy(sorted, policies)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].Name < sorted[j].Name
	})

	data, err := json.Marshal(sorted)
	if err != nil {
		return "", err
	}

	h := sha256.Sum256(data)
	return hex.EncodeToString(h[:]), nil
}

func hashFlows(flows []neo4jclient.FlowEdge) string {
	sorted := make([]neo4jclient.FlowEdge, len(flows))
	copy(sorted, flows)
	sort.Slice(sorted, func(i, j int) bool {
		return flowKey(sorted[i]) < flowKey(sorted[j])
	})

	h := sha256.New()
	for _, f := range sorted {
		fmt.Fprintf(h, "%s=%d;", flowKey(f), f.Count)
	}
	return hex.EncodeToString(h.Sum(nil))
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
