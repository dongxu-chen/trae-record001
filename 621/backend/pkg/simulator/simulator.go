package simulator

import (
	"authz-policy-recommender/backend/pkg/models"
	"crypto/sha256"
	"encoding/hex"
	"strings"
	"sync"
)

type PolicySimulator struct {
	mu           sync.RWMutex
	baselineCache map[string]models.SimulationResult
}

type BaselineSimulation struct {
	RequestHash string
	Result      models.SimulationResult
	Timestamp   int64
}

func NewPolicySimulator() *PolicySimulator {
	return &PolicySimulator{
		baselineCache: make(map[string]models.SimulationResult),
	}
}

func (ps *PolicySimulator) Simulate(req models.SimulationRequest) models.SimulationResult {
	for _, policy := range req.Policies {
		for _, rule := range policy.Rules {
			if ps.ruleMatches(rule, req) {
				if policy.Action == "ALLOW" {
					return models.SimulationResult{
						Allowed:       true,
						Reason:        "Matched ALLOW policy",
						MatchedPolicy: policy.Name,
					}
				} else if policy.Action == "DENY" {
					return models.SimulationResult{
						Allowed:       false,
						Reason:        "Matched DENY policy",
						MatchedPolicy: policy.Name,
					}
				}
			}
		}
	}

	return models.SimulationResult{
		Allowed: false,
		Reason:  "No matching policy found (default deny)",
	}
}

func (ps *PolicySimulator) ruleMatches(rule models.Rule, req models.SimulationRequest) bool {
	fromMatch := rule.From == "*" || rule.From == req.Source
	if !fromMatch {
		return false
	}

	toMatch := rule.To == "*" || rule.To == req.Dest
	if !toMatch {
		return false
	}

	methodMatch := false
	for _, m := range rule.Methods {
		if m == "*" || strings.EqualFold(m, req.Method) {
			methodMatch = true
			break
		}
	}
	if !methodMatch {
		return false
	}

	if len(rule.Paths) > 0 {
		pathMatch := false
		for _, p := range rule.Paths {
			if ps.pathMatches(p, req.Path) {
				pathMatch = true
				break
			}
		}
		if !pathMatch {
			return false
		}
	}

	return true
}

func (ps *PolicySimulator) pathMatches(pattern, path string) bool {
	if pattern == path {
		return true
	}

	patternParts := strings.Split(strings.Trim(pattern, "/"), "/")
	pathParts := strings.Split(strings.Trim(path, "/"), "/")

	if len(patternParts) != len(pathParts) {
		return false
	}

	for i, pp := range patternParts {
		if pp == "{id}" || pp == "*" {
			continue
		}
		if pp != pathParts[i] {
			return false
		}
	}

	return true
}

type BatchSimulationRequest struct {
	Policies []models.AuthorizationPolicy `json:"policies"`
	Calls    []models.CallEdge            `json:"calls"`
}

type BatchSimulationResult struct {
	Total     int                  `json:"total"`
	Allowed   int                  `json:"allowed"`
	Denied    int                  `json:"denied"`
	Results   []SimulatedCallResult `json:"results"`
}

type SimulatedCallResult struct {
	Call    models.CallEdge       `json:"call"`
	Result  models.SimulationResult `json:"result"`
}

func (ps *PolicySimulator) SimulateBatch(req BatchSimulationRequest) BatchSimulationResult {
	results := make([]SimulatedCallResult, 0, len(req.Calls))
	allowed := 0
	denied := 0

	for _, call := range req.Calls {
		simReq := models.SimulationRequest{
			Policies: req.Policies,
			Source:   call.Source.Name,
			Dest:     call.Destination.Name,
			Method:   call.Method,
			Path:     call.Path,
		}
		result := ps.Simulate(simReq)
		if result.Allowed {
			allowed++
		} else {
			denied++
		}
		results = append(results, SimulatedCallResult{
			Call:   call,
			Result: result,
		})
	}

	return BatchSimulationResult{
		Total:   len(req.Calls),
		Allowed: allowed,
		Denied:  denied,
		Results: results,
	}
}

func (ps *PolicySimulator) GenerateCoverageReport(policies []models.AuthorizationPolicy, calls []models.CallEdge) map[string]interface{} {
	batchResult := ps.SimulateBatch(BatchSimulationRequest{
		Policies: policies,
		Calls:    calls,
	})

	uncoveredCalls := make([]models.CallEdge, 0)
	for _, r := range batchResult.Results {
		if !r.Result.Allowed {
			uncoveredCalls = append(uncoveredCalls, r.Call)
		}
	}

	coveragePercent := 0
	if batchResult.Total > 0 {
		coveragePercent = (batchResult.Allowed * 100) / batchResult.Total
	}

	return map[string]interface{}{
		"coveragePercent": coveragePercent,
		"totalCalls":      batchResult.Total,
		"coveredCalls":    batchResult.Allowed,
		"uncoveredCalls":  uncoveredCalls,
		"details":         batchResult.Results,
	}
}

func (ps *PolicySimulator) hashRequest(req models.SimulationRequest) string {
	data := req.Source + "|" + req.Dest + "|" + req.Method + "|" + req.Path
	hash := sha256.Sum256([]byte(data))
	return hex.EncodeToString(hash[:])
}

func (ps *PolicySimulator) SetBaseline(req models.SimulationRequest, result models.SimulationResult) {
	ps.mu.Lock()
	defer ps.mu.Unlock()
	key := ps.hashRequest(req)
	ps.baselineCache[key] = result
}

func (ps *PolicySimulator) GetBaseline(req models.SimulationRequest) (models.SimulationResult, bool) {
	ps.mu.RLock()
	defer ps.mu.RUnlock()
	key := ps.hashRequest(req)
	result, exists := ps.baselineCache[key]
	return result, exists
}

func (ps *PolicySimulator) ClearBaseline() {
	ps.mu.Lock()
	defer ps.mu.Unlock()
	ps.baselineCache = make(map[string]models.SimulationResult)
}

func (ps *PolicySimulator) GetAffectedServices(changes []models.PolicyChange) map[string]bool {
	affected := make(map[string]bool)

	for _, change := range changes {
		policies := []*models.AuthorizationPolicy{change.NewPolicy, change.OldPolicy}
		for _, policy := range policies {
			if policy == nil {
				continue
			}
			for _, rule := range policy.Rules {
				if rule.From != "*" {
					affected[rule.From] = true
				}
				if rule.To != "*" {
					affected[rule.To] = true
				}
			}
		}
	}

	return affected
}

func (ps *PolicySimulator) IsRequestAffected(req models.SimulationRequest, changes []models.PolicyChange) bool {
	affectedServices := ps.GetAffectedServices(changes)

	if len(affectedServices) == 0 {
		return true
	}

	return affectedServices[req.Source] || affectedServices[req.Dest]
}

func (ps *PolicySimulator) SimulateIncremental(req models.IncrementalSimulationRequest) models.IncrementalSimulationResult {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	var policies []models.AuthorizationPolicy
	if len(req.BasePolicies) > 0 {
		policies = req.BasePolicies
	}

	for _, change := range req.Changes {
		policies = ps.applyChange(policies, change)
	}

	results := make([]models.SimulationResult, 0, len(req.TestRequests))
	changedResults := make([]models.SimulationResult, 0)
	affectedCount := 0
	skippedCount := 0

	for _, testReq := range req.TestRequests {
		testReq.Policies = policies

		isAffected := ps.IsRequestAffected(testReq, req.Changes)

		if req.OnlyAffected && !isAffected {
			skippedCount++
			continue
		}

		if !isAffected {
			if baseline, exists := ps.GetBaseline(testReq); exists {
				results = append(results, baseline)
				skippedCount++
				continue
			}
		}

		affectedCount++
		result := ps.Simulate(testReq)

		if baseline, exists := ps.GetBaseline(testReq); exists {
			if baseline.Allowed != result.Allowed || baseline.MatchedPolicy != result.MatchedPolicy {
				changedResults = append(changedResults, result)
			}
		}

		results = append(results, result)
		ps.baselineCache[ps.hashRequest(testReq)] = result
	}

	return models.IncrementalSimulationResult{
		TotalRequests:    len(req.TestRequests),
		AffectedRequests: affectedCount,
		SkippedRequests:  skippedCount,
		Results:          results,
		ChangedResults:   changedResults,
	}
}

func (ps *PolicySimulator) applyChange(policies []models.AuthorizationPolicy, change models.PolicyChange) []models.AuthorizationPolicy {
	switch change.Type {
	case models.PolicyChangeAdded:
		if change.NewPolicy != nil {
			policies = append(policies, *change.NewPolicy)
		}
	case models.PolicyChangeRemoved:
		for i, p := range policies {
			if p.Name == change.PolicyName {
				policies = append(policies[:i], policies[i+1:]...)
				break
			}
		}
	case models.PolicyChangeModified:
		for i, p := range policies {
			if p.Name == change.PolicyName && change.NewPolicy != nil {
				policies[i] = *change.NewPolicy
				break
			}
		}
	}
	return policies
}

func (ps *PolicySimulator) BuildBaseline(policies []models.AuthorizationPolicy, requests []models.SimulationRequest) {
	ps.mu.Lock()
	defer ps.mu.Unlock()

	for _, req := range requests {
		req.Policies = policies
		result := ps.Simulate(req)
		ps.baselineCache[ps.hashRequest(req)] = result
	}
}

func (ps *PolicySimulator) GenerateChangeReport(oldPolicies, newPolicies []models.AuthorizationPolicy) []models.PolicyChange {
	changes := make([]models.PolicyChange, 0)

	oldMap := make(map[string]models.AuthorizationPolicy)
	for _, p := range oldPolicies {
		oldMap[p.Name] = p
	}

	newMap := make(map[string]models.AuthorizationPolicy)
	for _, p := range newPolicies {
		newMap[p.Name] = p
	}

	for name, newPolicy := range newMap {
		if oldPolicy, exists := oldMap[name]; exists {
			if !ps.policiesEqual(oldPolicy, newPolicy) {
				oldCopy := oldPolicy
				newCopy := newPolicy
				changes = append(changes, models.PolicyChange{
					Type:       models.PolicyChangeModified,
					PolicyName: name,
					OldPolicy:  &oldCopy,
					NewPolicy:  &newCopy,
				})
			}
		} else {
			newCopy := newPolicy
			changes = append(changes, models.PolicyChange{
				Type:       models.PolicyChangeAdded,
				PolicyName: name,
				NewPolicy:  &newCopy,
			})
		}
	}

	for name, oldPolicy := range oldMap {
		if _, exists := newMap[name]; !exists {
			oldCopy := oldPolicy
			changes = append(changes, models.PolicyChange{
				Type:       models.PolicyChangeRemoved,
				PolicyName: name,
				OldPolicy:  &oldCopy,
			})
		}
	}

	return changes
}

func (ps *PolicySimulator) policiesEqual(a, b models.AuthorizationPolicy) bool {
	if a.Name != b.Name || a.Action != b.Action || len(a.Rules) != len(b.Rules) {
		return false
	}
	for i := range a.Rules {
		if !ps.rulesEqual(a.Rules[i], b.Rules[i]) {
			return false
		}
	}
	return true
}

func (ps *PolicySimulator) rulesEqual(a, b models.Rule) bool {
	if a.From != b.From || a.To != b.To {
		return false
	}
	if len(a.Methods) != len(b.Methods) || len(a.Paths) != len(b.Paths) {
		return false
	}
	for i := range a.Methods {
		if a.Methods[i] != b.Methods[i] {
			return false
		}
	}
	for i := range a.Paths {
		if a.Paths[i] != b.Paths[i] {
			return false
		}
	}
	return true
}
