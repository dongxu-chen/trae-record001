package analysis

import (
	"fmt"
	"reflect"
	"sort"
	"strings"

	"mesh-security-platform/internal/models"
)

const (
	priorityGlobalNamespace   = 100
	priorityMeshPolicy        = 90
	priorityRootNamespace     = 80
	priorityRegularNamespace  = 50
	prioritySpecificSelector  = 30
	priorityWildcardSelector  = 10
)

type ConflictDetector struct {
	policies []models.Policy
}

func NewConflictDetector(policies []models.Policy) *ConflictDetector {
	return &ConflictDetector{
		policies: policies,
	}
}

func (cd *ConflictDetector) Detect(policy *models.Policy) (*models.ConflictDetectionResult, error) {
	result := &models.ConflictDetectionResult{
		HasConflict: false,
		Conflicts:   []models.ConflictInfo{},
		Severity:    "low",
	}

	for _, existingPolicy := range cd.policies {
		if existingPolicy.ID == policy.ID {
			continue
		}

		conflicts := cd.checkConflict(policy, &existingPolicy)
		for _, conflict := range conflicts {
			result.HasConflict = true
			result.Conflicts = append(result.Conflicts, conflict)
		}
	}

	implicitConflicts := cd.detectImplicitConflicts(policy)
	for _, conflict := range implicitConflicts {
		result.HasConflict = true
		result.Conflicts = append(result.Conflicts, conflict)
	}

	sort.Slice(result.Conflicts, func(i, j int) bool {
		severityOrder := map[string]int{"critical": 0, "high": 1, "medium": 2, "low": 3}
		return severityOrder[result.Conflicts[i].Severity] < severityOrder[result.Conflicts[j].Severity]
	})

	if result.HasConflict {
		result.Severity = cd.calculateSeverity(result.Conflicts)
		result.Recommendation = cd.generateRecommendation(result)
	}

	return result, nil
}

func (cd *ConflictDetector) calculatePolicyPriority(policy *models.Policy) int {
	priority := 0

	if policy.Namespace == "istio-system" {
		priority += priorityGlobalNamespace
	} else if policy.Namespace == "default" {
		priority += priorityRootNamespace
	} else {
		priority += priorityRegularNamespace
	}

	selectorSpecificity := cd.calculateSelectorSpecificity(policy)
	priority += selectorSpecificity

	labels := policy.Labels
	if labels["priority"] == "high" {
		priority += 20
	} else if labels["priority"] == "critical" {
		priority += 40
	}

	return priority
}

func (cd *ConflictDetector) calculateSelectorSpecificity(policy *models.Policy) int {
	switch policy.Type {
	case models.PolicyTypeMTLS:
		if targets, ok := policy.Spec["target_services"].([]interface{}); ok {
			if len(targets) == 1 {
				if t, ok := targets[0].(string); ok && t == "*" {
					return priorityWildcardSelector
				}
			}
			return prioritySpecificSelector
		}
	case models.PolicyTypeAuthorization:
		if rules, ok := policy.Spec["rules"].([]interface{}); ok && len(rules) > 0 {
			return prioritySpecificSelector
		}
		return priorityWildcardSelector
	case models.PolicyTypeRequestAuth:
		if selectors, ok := policy.Spec["selectors"].(map[string]interface{}); ok && len(selectors) > 0 {
			return prioritySpecificSelector
		}
		return priorityWildcardSelector
	}
	return 0
}

func (cd *ConflictDetector) determineWinningPolicy(policyA, policyB *models.Policy) string {
	priorityA := cd.calculatePolicyPriority(policyA)
	priorityB := cd.calculatePolicyPriority(policyB)

	if priorityA > priorityB {
		return policyA.Name
	} else if priorityB > priorityA {
		return policyB.Name
	}

	if policyA.CreatedAt.After(policyB.CreatedAt) {
		return policyA.Name
	}
	return policyB.Name
}

func (cd *ConflictDetector) checkConflict(policyA, policyB *models.Policy) []models.ConflictInfo {
	var conflicts []models.ConflictInfo

	if policyA.Type != policyB.Type {
		return conflicts
	}

	priorityA := cd.calculatePolicyPriority(policyA)
	priorityB := cd.calculatePolicyPriority(policyB)
	winner := cd.determineWinningPolicy(policyA, policyB)

	switch policyA.Type {
	case models.PolicyTypeMTLS:
		conflicts = append(conflicts, cd.checkMTLSConflict(policyA, policyB, priorityA, priorityB, winner)...)
	case models.PolicyTypeAuthorization:
		conflicts = append(conflicts, cd.checkAuthorizationConflict(policyA, policyB, priorityA, priorityB, winner)...)
	case models.PolicyTypeRequestAuth:
		conflicts = append(conflicts, cd.checkRequestAuthConflict(policyA, policyB, priorityA, priorityB, winner)...)
	}

	return conflicts
}

func (cd *ConflictDetector) checkMTLSConflict(policyA, policyB *models.Policy, priorityA, priorityB int, winner string) []models.ConflictInfo {
	var conflicts []models.ConflictInfo

	targetsA := cd.getTargetServices(policyA)
	targetsB := cd.getTargetServices(policyB)

	overlap := findOverlap(targetsA, targetsB)
	if len(overlap) > 0 {
		modeA := cd.getMTLSMode(policyA)
		modeB := cd.getMTLSMode(policyB)

		if modeA != modeB {
			severity := "high"
			if modeA == "PERMISSIVE" || modeB == "PERMISSIVE" {
				severity = "medium"
			}
			if (modeA == "STRICT" && modeB == "DISABLE") || (modeA == "DISABLE" && modeB == "STRICT") {
				severity = "critical"
			}

			conflicts = append(conflicts, models.ConflictInfo{
				ConflictType:      "mtls_mode_conflict",
				PolicyA:           policyA.Name,
				PolicyB:           policyB.Name,
				Description:       fmt.Sprintf("mTLS mode mismatch: %s uses %s, %s uses %s. Winning policy: %s", policyA.Name, modeA, policyB.Name, modeB, winner),
				AffectedResources: overlap,
				IsImplicit:        false,
				PriorityA:         priorityA,
				PriorityB:         priorityB,
				WinningPolicy:     winner,
				Severity:          severity,
			})
		}
	}

	return conflicts
}

func (cd *ConflictDetector) checkAuthorizationConflict(policyA, policyB *models.Policy, priorityA, priorityB int, winner string) []models.ConflictInfo {
	var conflicts []models.ConflictInfo

	targetsA := cd.getAuthPolicyTargets(policyA)
	targetsB := cd.getAuthPolicyTargets(policyB)

	overlap := findOverlap(targetsA, targetsB)
	if len(overlap) > 0 {
		actionA := cd.getAuthPolicyAction(policyA)
		actionB := cd.getAuthPolicyAction(policyB)

		if actionA != actionB {
			severity := "high"
			if actionA == "AUDIT" || actionB == "AUDIT" {
				severity = "medium"
			}
			if (actionA == "ALLOW" && actionB == "DENY") || (actionA == "DENY" && actionB == "ALLOW") {
				severity = "critical"
			}

			conflicts = append(conflicts, models.ConflictInfo{
				ConflictType:      "authorization_action_conflict",
				PolicyA:           policyA.Name,
				PolicyB:           policyB.Name,
				Description:       fmt.Sprintf("Authorization action mismatch: %s is %s, %s is %s. Winning policy: %s", policyA.Name, actionA, policyB.Name, actionB, winner),
				AffectedResources: overlap,
				IsImplicit:        false,
				PriorityA:         priorityA,
				PriorityB:         priorityB,
				WinningPolicy:     winner,
				Severity:          severity,
			})
		}

		rulesConflict := cd.checkRulesConflict(policyA, policyB)
		if rulesConflict {
			conflicts = append(conflicts, models.ConflictInfo{
				ConflictType:      "authorization_rules_overlap",
				PolicyA:           policyA.Name,
				PolicyB:           policyB.Name,
				Description:       "Authorization rules have overlapping conditions that may cause undefined behavior",
				AffectedResources: overlap,
				IsImplicit:        false,
				PriorityA:         priorityA,
				PriorityB:         priorityB,
				WinningPolicy:     winner,
				Severity:          "medium",
			})
		}
	}

	return conflicts
}

func (cd *ConflictDetector) checkRequestAuthConflict(policyA, policyB *models.Policy, priorityA, priorityB int, winner string) []models.ConflictInfo {
	var conflicts []models.ConflictInfo

	selectorsA := cd.getRequestAuthSelectors(policyA)
	selectorsB := cd.getRequestAuthSelectors(policyB)

	if cd.haveOverlappingSelectors(selectorsA, selectorsB) {
		jwtIssuersA := cd.getJWTIssuers(policyA)
		jwtIssuersB := cd.getJWTIssuers(policyB)

		if len(jwtIssuersA) > 0 && len(jwtIssuersB) > 0 {
			issuerOverlap := findOverlap(jwtIssuersA, jwtIssuersB)
			if len(issuerOverlap) > 0 {
				conflicts = append(conflicts, models.ConflictInfo{
					ConflictType: "jwt_issuer_duplicate",
					PolicyA:      policyA.Name,
					PolicyB:      policyB.Name,
					Description:  fmt.Sprintf("Duplicate JWT issuers configured: %v. Winning policy: %s", issuerOverlap, winner),
					IsImplicit:   false,
					PriorityA:    priorityA,
					PriorityB:    priorityB,
					WinningPolicy: winner,
					Severity:     "high",
				})
			}
		}

		jwksOverlap := cd.checkJWKSURIOverlap(policyA, policyB)
		if jwksOverlap {
			conflicts = append(conflicts, models.ConflictInfo{
				ConflictType: "jwt_jwks_conflict",
				PolicyA:      policyA.Name,
				PolicyB:      policyB.Name,
				Description:  "Same JWT issuer configured with different JWKS URIs",
				IsImplicit:   false,
				PriorityA:    priorityA,
				PriorityB:    priorityB,
				WinningPolicy: winner,
				Severity:     "high",
			})
		}
	}

	return conflicts
}

func (cd *ConflictDetector) detectImplicitConflicts(policy *models.Policy) []models.ConflictInfo {
	var conflicts []models.ConflictInfo

	priority := cd.calculatePolicyPriority(policy)

	conflicts = append(conflicts, cd.detectNamespaceOverrideConflicts(policy, priority)...)
	conflicts = append(conflicts, cd.detectSelectorShadowingConflicts(policy, priority)...)
	conflicts = append(conflicts, cd.detectOrderDependencyConflicts(policy, priority)...)

	return conflicts
}

func (cd *ConflictDetector) detectNamespaceOverrideConflicts(policy *models.Policy, priority int) []models.ConflictInfo {
	var conflicts []models.ConflictInfo

	if policy.Namespace == "istio-system" {
		for _, existing := range cd.policies {
			if existing.ID == policy.ID || existing.Type != policy.Type {
				continue
			}
			if existing.Namespace != "istio-system" && existing.Namespace != "default" {
				winner := cd.determineWinningPolicy(policy, &existing)
				conflicts = append(conflicts, models.ConflictInfo{
					ConflictType: "namespace_override",
					PolicyA:      policy.Name,
					PolicyB:      existing.Name,
					Description:  fmt.Sprintf("Global policy %s may be overridden by namespace-specific policy %s in namespace %s", policy.Name, existing.Name, existing.Namespace),
					IsImplicit:   true,
					PriorityA:    priority,
					PriorityB:    cd.calculatePolicyPriority(&existing),
					WinningPolicy: winner,
					Severity:     "medium",
				})
			}
		}
	} else {
		for _, existing := range cd.policies {
			if existing.ID == policy.ID || existing.Type != policy.Type {
				continue
			}
			if existing.Namespace == "istio-system" {
				winner := cd.determineWinningPolicy(policy, &existing)
				conflicts = append(conflicts, models.ConflictInfo{
					ConflictType: "namespace_override",
					PolicyA:      policy.Name,
					PolicyB:      existing.Name,
					Description:  fmt.Sprintf("Namespace policy %s may override global policy %s", policy.Name, existing.Name),
					IsImplicit:   true,
					PriorityA:    priority,
					PriorityB:    cd.calculatePolicyPriority(&existing),
					WinningPolicy: winner,
					Severity:     "medium",
				})
			}
		}
	}

	return conflicts
}

func (cd *ConflictDetector) detectSelectorShadowingConflicts(policy *models.Policy, priority int) []models.ConflictInfo {
	var conflicts []models.ConflictInfo

	policySelectorCount := cd.getSelectorCount(policy)

	for _, existing := range cd.policies {
		if existing.ID == policy.ID || existing.Type != policy.Type {
			continue
		}

		existingSelectorCount := cd.getSelectorCount(&existing)

		if policySelectorCount > 0 && existingSelectorCount == 0 {
			winner := cd.determineWinningPolicy(policy, &existing)
			conflicts = append(conflicts, models.ConflictInfo{
				ConflictType: "selector_shadowing",
				PolicyA:      policy.Name,
				PolicyB:      existing.Name,
				Description:  fmt.Sprintf("Policy %s with specific selectors may be shadowed by policy %s with wildcard selectors", policy.Name, existing.Name),
				IsImplicit:   true,
				PriorityA:    priority,
				PriorityB:    cd.calculatePolicyPriority(&existing),
				WinningPolicy: winner,
				Severity:     "medium",
			})
		} else if existingSelectorCount > 0 && policySelectorCount == 0 {
			winner := cd.determineWinningPolicy(policy, &existing)
			conflicts = append(conflicts, models.ConflictInfo{
				ConflictType: "selector_shadowing",
				PolicyA:      policy.Name,
				PolicyB:      existing.Name,
				Description:  fmt.Sprintf("Wildcard policy %s may shadow specific policy %s", policy.Name, existing.Name),
				IsImplicit:   true,
				PriorityA:    priority,
				PriorityB:    cd.calculatePolicyPriority(&existing),
				WinningPolicy: winner,
				Severity:     "high",
			})
		}
	}

	return conflicts
}

func (cd *ConflictDetector) detectOrderDependencyConflicts(policy *models.Policy, priority int) []models.ConflictInfo {
	var conflicts []models.ConflictInfo

	for _, existing := range cd.policies {
		if existing.ID == policy.ID || existing.Type != policy.Type {
			continue
		}

		if cd.haveMutuallyExclusiveConditions(policy, &existing) {
			winner := cd.determineWinningPolicy(policy, &existing)
			conflicts = append(conflicts, models.ConflictInfo{
				ConflictType: "order_dependency",
				PolicyA:      policy.Name,
				PolicyB:      existing.Name,
				Description:  fmt.Sprintf("Policies %s and %s have mutually exclusive conditions that create order-dependent behavior", policy.Name, existing.Name),
				IsImplicit:   true,
				PriorityA:    priority,
				PriorityB:    cd.calculatePolicyPriority(&existing),
				WinningPolicy: winner,
				Severity:     "high",
			})
		}
	}

	return conflicts
}

func (cd *ConflictDetector) getSelectorCount(policy *models.Policy) int {
	switch policy.Type {
	case models.PolicyTypeMTLS:
		if targets, ok := policy.Spec["target_services"].([]interface{}); ok {
			for _, t := range targets {
				if ts, ok := t.(string); ok && ts == "*" {
					return 0
				}
			}
			return len(targets)
		}
	case models.PolicyTypeAuthorization:
		if rules, ok := policy.Spec["rules"].([]interface{}); ok {
			count := 0
			for _, rule := range rules {
				if ruleMap, ok := rule.(map[string]interface{}); ok {
					if from, ok := ruleMap["from"].([]interface{}); ok {
						count += len(from)
					}
					if to, ok := ruleMap["to"].([]interface{}); ok {
						count += len(to)
					}
				}
			}
			return count
		}
	case models.PolicyTypeRequestAuth:
		if selectors, ok := policy.Spec["selectors"].(map[string]interface{}); ok {
			return len(selectors)
		}
	}
	return 0
}

func (cd *ConflictDetector) haveMutuallyExclusiveConditions(policyA, policyB *models.Policy) bool {
	if policyA.Type != models.PolicyTypeAuthorization {
		return false
	}

	rulesA := cd.getAuthRules(policyA)
	rulesB := cd.getAuthRules(policyB)

	for _, ruleA := range rulesA {
		for _, ruleB := range rulesB {
			if cd.areRulesMutuallyExclusive(ruleA, ruleB) {
				return true
			}
		}
	}
	return false
}

func (cd *ConflictDetector) getAuthRules(policy *models.Policy) []map[string]interface{} {
	if rules, ok := policy.Spec["rules"].([]interface{}); ok {
		result := make([]map[string]interface{}, 0, len(rules))
		for _, r := range rules {
			if rm, ok := r.(map[string]interface{}); ok {
				result = append(result, rm)
			}
		}
		return result
	}
	return nil
}

func (cd *ConflictDetector) areRulesMutuallyExclusive(ruleA, ruleB map[string]interface{}) bool {
	fromA, _ := ruleA["from"].([]interface{})
	fromB, _ := ruleB["from"].([]interface{})

	if len(fromA) > 0 && len(fromB) > 0 {
		aSet := make(map[string]bool)
		bSet := make(map[string]bool)

		for _, f := range fromA {
			if fm, ok := f.(map[string]interface{}); ok {
				if principals, ok := fm["principals"].([]interface{}); ok {
					for _, p := range principals {
						if ps, ok := p.(string); ok {
							aSet[ps] = true
						}
					}
				}
			}
		}

		for _, f := range fromB {
			if fm, ok := f.(map[string]interface{}); ok {
				if principals, ok := fm["principals"].([]interface{}); ok {
					for _, p := range principals {
						if ps, ok := p.(string); ok {
							bSet[ps] = true
						}
					}
				}
			}
		}

		hasOverlap := false
		for k := range aSet {
			if bSet[k] {
				hasOverlap = true
				break
			}
		}

		if !hasOverlap && len(aSet) > 0 && len(bSet) > 0 {
			return true
		}
	}

	return false
}

func (cd *ConflictDetector) checkJWKSURIOverlap(policyA, policyB *models.Policy) bool {
	issuersA := cd.getJWTIssuersWithJWKS(policyA)
	issuersB := cd.getJWTIssuersWithJWKS(policyB)

	for issuerA, jwksA := range issuersA {
		if jwksB, exists := issuersB[issuerA]; exists {
			if jwksA != jwksB {
				return true
			}
		}
	}
	return false
}

func (cd *ConflictDetector) getJWTIssuersWithJWKS(policy *models.Policy) map[string]string {
	result := make(map[string]string)
	if jwtRules, ok := policy.Spec["jwt_rules"].([]interface{}); ok {
		for _, rule := range jwtRules {
			if ruleMap, ok := rule.(map[string]interface{}); ok {
				issuer, _ := ruleMap["issuer"].(string)
				jwksURI, _ := ruleMap["jwks_uri"].(string)
				if issuer != "" {
					result[issuer] = jwksURI
				}
			}
		}
	}
	return result
}

func (cd *ConflictDetector) getTargetServices(policy *models.Policy) []string {
	if spec, ok := policy.Spec["target_services"].([]interface{}); ok {
		services := make([]string, 0, len(spec))
		for _, s := range spec {
			if str, ok := s.(string); ok {
				services = append(services, str)
			}
		}
		return services
	}
	return []string{"*"}
}

func (cd *ConflictDetector) getMTLSMode(policy *models.Policy) string {
	if spec, ok := policy.Spec["mtls"].(map[string]interface{}); ok {
		if mode, ok := spec["mode"].(string); ok {
			return mode
		}
	}
	if mode, ok := policy.Spec["mode"].(string); ok {
		return mode
	}
	return "UNKNOWN"
}

func (cd *ConflictDetector) getAuthPolicyTargets(policy *models.Policy) []string {
	if rules, ok := policy.Spec["rules"].([]interface{}); ok {
		targets := make([]string, 0)
		for _, rule := range rules {
			if ruleMap, ok := rule.(map[string]interface{}); ok {
				if to, ok := ruleMap["to"].([]interface{}); ok {
					for _, t := range to {
						if tMap, ok := t.(map[string]interface{}); ok {
							if hosts, ok := tMap["hosts"].([]interface{}); ok {
								for _, h := range hosts {
									if str, ok := h.(string); ok {
										targets = append(targets, str)
									}
								}
							}
						}
					}
				}
			}
		}
		return targets
	}
	return []string{"*"}
}

func (cd *ConflictDetector) getAuthPolicyAction(policy *models.Policy) string {
	if action, ok := policy.Spec["action"].(string); ok {
		return action
	}
	return "ALLOW"
}

func (cd *ConflictDetector) checkRulesConflict(policyA, policyB *models.Policy) bool {
	rulesA := policyA.Spec["rules"]
	rulesB := policyB.Spec["rules"]
	return reflect.DeepEqual(rulesA, rulesB)
}

func (cd *ConflictDetector) getRequestAuthSelectors(policy *models.Policy) map[string]string {
	if selectors, ok := policy.Spec["selectors"].(map[string]string); ok {
		return selectors
	}
	if selectors, ok := policy.Spec["selectors"].(map[string]interface{}); ok {
		result := make(map[string]string)
		for k, v := range selectors {
			if vs, ok := v.(string); ok {
				result[k] = vs
			}
		}
		return result
	}
	return make(map[string]string)
}

func (cd *ConflictDetector) haveOverlappingSelectors(a, b map[string]string) bool {
	if len(a) == 0 || len(b) == 0 {
		return true
	}

	for k, v := range a {
		if bv, ok := b[k]; ok && bv == v {
			return true
		}
	}
	return false
}

func (cd *ConflictDetector) getJWTIssuers(policy *models.Policy) []string {
	if jwtRules, ok := policy.Spec["jwt_rules"].([]interface{}); ok {
		issuers := make([]string, 0, len(jwtRules))
		for _, rule := range jwtRules {
			if ruleMap, ok := rule.(map[string]interface{}); ok {
				if issuer, ok := ruleMap["issuer"].(string); ok {
					issuers = append(issuers, issuer)
				}
			}
		}
		return issuers
	}
	return []string{}
}

func (cd *ConflictDetector) calculateSeverity(conflicts []models.ConflictInfo) string {
	for _, c := range conflicts {
		if c.Severity == "critical" {
			return "critical"
		}
	}

	highPriorityTypes := map[string]bool{
		"mtls_mode_conflict":            true,
		"authorization_action_conflict": true,
	}

	for _, c := range conflicts {
		if highPriorityTypes[c.ConflictType] {
			return "high"
		}
	}

	hasImplicit := false
	for _, c := range conflicts {
		if c.IsImplicit {
			hasImplicit = true
			break
		}
	}

	if hasImplicit {
		return "medium"
	}

	return "low"
}

func (cd *ConflictDetector) generateRecommendation(result *models.ConflictDetectionResult) string {
	var recommendations []string

	for _, conflict := range result.Conflicts {
		switch conflict.ConflictType {
		case "mtls_mode_conflict":
			recommendations = append(recommendations,
				fmt.Sprintf("Resolve mTLS mode conflict between '%s' (priority: %d) and '%s' (priority: %d). '%s' will take effect. Consider setting explicit priority labels.",
					conflict.PolicyA, conflict.PriorityA, conflict.PolicyB, conflict.PriorityB, conflict.WinningPolicy))
		case "authorization_action_conflict":
			recommendations = append(recommendations,
				fmt.Sprintf("Critical: Resolve authorization action conflict between '%s' and '%s'. '%s' wins. Review access control rules immediately.",
					conflict.PolicyA, conflict.PolicyB, conflict.WinningPolicy))
		case "authorization_rules_overlap":
			recommendations = append(recommendations,
				fmt.Sprintf("Consolidate overlapping authorization rules in '%s' and '%s' to avoid undefined behavior.",
					conflict.PolicyA, conflict.PolicyB))
		case "jwt_issuer_duplicate":
			recommendations = append(recommendations,
				fmt.Sprintf("Remove duplicate JWT issuer configurations between '%s' and '%s'. '%s' takes precedence.",
					conflict.PolicyA, conflict.PolicyB, conflict.WinningPolicy))
		case "jwt_jwks_conflict":
			recommendations = append(recommendations,
				fmt.Sprintf("Same JWT issuer configured with different JWKS URIs in '%s' and '%s'. Align JWKS configuration.",
					conflict.PolicyA, conflict.PolicyB))
		case "namespace_override":
			recommendations = append(recommendations,
				fmt.Sprintf("Implicit: Namespace policy '%s' may override global policy '%s'. Verify this is intentional.",
					conflict.PolicyB, conflict.PolicyA))
		case "selector_shadowing":
			recommendations = append(recommendations,
				fmt.Sprintf("Implicit: Policy shadowing detected - '%s' may be shadowed by '%s'. Use specific selectors to avoid ambiguity.",
					conflict.PolicyA, conflict.PolicyB))
		case "order_dependency":
			recommendations = append(recommendations,
				fmt.Sprintf("Warning: '%s' and '%s' have order-dependent mutually exclusive conditions. Merge or reorder policies.",
					conflict.PolicyA, conflict.PolicyB))
		}
	}

	return strings.Join(recommendations, " ")
}

func findOverlap(a, b []string) []string {
	set := make(map[string]bool)
	for _, s := range a {
		set[s] = true
	}

	var overlap []string
	for _, s := range b {
		if set[s] || s == "*" || set["*"] {
			overlap = append(overlap, s)
		}
	}
	return overlap
}
