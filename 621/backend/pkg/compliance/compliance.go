package compliance

import (
	"authz-policy-recommender/backend/pkg/models"
)

type ComplianceChecker struct {
	rules []models.ComplianceRule
}

func NewComplianceChecker() *ComplianceChecker {
	return &ComplianceChecker{
		rules: []models.ComplianceRule{
			{
				ID:          "CIS-001",
				Name:        "Deny-All Default Policy",
				Description: "Ensure a default deny-all policy exists for each namespace",
				Severity:    "HIGH",
			},
			{
				ID:          "CIS-002",
				Name:        "No Wildcard Sources",
				Description: "Avoid using wildcard (*) in source principals for ALLOW policies",
				Severity:    "HIGH",
			},
			{
				ID:          "CIS-003",
				Name:        "Least Privilege Methods",
				Description: "Avoid using wildcard (*) for HTTP methods in ALLOW policies",
				Severity:    "MEDIUM",
			},
			{
				ID:          "CIS-004",
				Name:        "Path Restrictions",
				Description: "Policies should specify paths rather than allowing all paths",
				Severity:    "MEDIUM",
			},
			{
				ID:          "CIS-005",
				Name:        "No Empty Selector",
				Description: "Policies should have a selector to target specific workloads",
				Severity:    "MEDIUM",
			},
			{
				ID:          "CIS-006",
				Name:        "Avoid Namespace-Wide Policies",
				Description: "Avoid policies that apply to all services in a namespace",
				Severity:    "LOW",
			},
			{
				ID:          "CIS-007",
				Name:        "Principle of Least Privilege",
				Description: "Each service should have minimal necessary permissions",
				Severity:    "HIGH",
			},
			{
				ID:          "CIS-008",
				Name:        "Mutual TLS Enabled",
				Description: "Policies should work with mTLS (use principals, not IPs)",
				Severity:    "HIGH",
			},
		},
	}
}

func (cc *ComplianceChecker) GetRules() []models.ComplianceRule {
	return cc.rules
}

func (cc *ComplianceChecker) CheckCompliance(policies []models.AuthorizationPolicy, graph *models.ServiceGraph) models.ComplianceReport {
	results := make([]models.ComplianceResult, 0, len(cc.rules))
	totalScore := 0
	maxScore := 0

	for _, rule := range cc.rules {
		result := cc.checkRule(rule, policies, graph)
		results = append(results, result)

		scoreWeight := cc.getScoreWeight(rule.Severity)
		maxScore += scoreWeight
		if result.Passed {
			totalScore += scoreWeight
		}
	}

	overallScore := 0
	if maxScore > 0 {
		overallScore = (totalScore * 100) / maxScore
	}

	return models.ComplianceReport{
		OverallScore: overallScore,
		Results:      results,
	}
}

func (cc *ComplianceChecker) getScoreWeight(severity string) int {
	switch severity {
	case "CRITICAL":
		return 30
	case "HIGH":
		return 20
	case "MEDIUM":
		return 10
	case "LOW":
		return 5
	default:
		return 5
	}
}

func (cc *ComplianceChecker) checkRule(rule models.ComplianceRule, policies []models.AuthorizationPolicy, graph *models.ServiceGraph) models.ComplianceResult {
	switch rule.ID {
	case "CIS-001":
		return cc.checkDenyAll(rule, policies)
	case "CIS-002":
		return cc.checkNoWildcardSources(rule, policies)
	case "CIS-003":
		return cc.checkNoWildcardMethods(rule, policies)
	case "CIS-004":
		return cc.checkPathRestrictions(rule, policies)
	case "CIS-005":
		return cc.checkNoEmptySelector(rule, policies)
	case "CIS-006":
		return cc.checkNoNamespaceWide(rule, policies)
	case "CIS-007":
		return cc.checkLeastPrivilege(rule, policies, graph)
	case "CIS-008":
		return cc.checkMTLS(rule, policies)
	default:
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "No check implemented for this rule",
		}
	}
}

func (cc *ComplianceChecker) checkDenyAll(rule models.ComplianceRule, policies []models.AuthorizationPolicy) models.ComplianceResult {
	hasDenyAll := false
	for _, p := range policies {
		if p.Action == "DENY" {
			for _, r := range p.Rules {
				if r.From == "*" && r.To == "*" {
					hasWildcardMethod := false
					for _, m := range r.Methods {
						if m == "*" {
							hasWildcardMethod = true
							break
						}
					}
					if hasWildcardMethod {
						hasDenyAll = true
						break
					}
				}
			}
		}
	}

	if hasDenyAll {
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "Default deny-all policy found",
		}
	}

	return models.ComplianceResult{
		Rule:      rule,
		Passed:    false,
		Details:   "No default deny-all policy found. Consider adding a DENY policy that matches all traffic.",
		Violations: []string{"Missing deny-all policy in default namespace"},
	}
}

func (cc *ComplianceChecker) checkNoWildcardSources(rule models.ComplianceRule, policies []models.AuthorizationPolicy) models.ComplianceResult {
	violations := make([]string, 0)

	for _, p := range policies {
		if p.Action != "ALLOW" {
			continue
		}
		for _, r := range p.Rules {
			if r.From == "*" {
				violations = append(violations,
					"Policy '"+p.Name+"' has wildcard source (*) for destination '"+r.To+"'")
			}
		}
	}

	if len(violations) == 0 {
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "No wildcard sources found in ALLOW policies",
		}
	}

	return models.ComplianceResult{
		Rule:       rule,
		Passed:     false,
		Details:    "Wildcard sources found in ALLOW policies. This violates least privilege principle.",
		Violations: violations,
	}
}

func (cc *ComplianceChecker) checkNoWildcardMethods(rule models.ComplianceRule, policies []models.AuthorizationPolicy) models.ComplianceResult {
	violations := make([]string, 0)

	for _, p := range policies {
		if p.Action != "ALLOW" {
			continue
		}
		for _, r := range p.Rules {
			for _, m := range r.Methods {
				if m == "*" {
					violations = append(violations,
						"Policy '"+p.Name+"' has wildcard method (*) for "+r.From+" -> "+r.To)
					break
				}
			}
		}
	}

	if len(violations) == 0 {
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "No wildcard methods found in ALLOW policies",
		}
	}

	return models.ComplianceResult{
		Rule:       rule,
		Passed:     false,
		Details:    "Wildcard HTTP methods found. Consider specifying exact methods.",
		Violations: violations,
	}
}

func (cc *ComplianceChecker) checkPathRestrictions(rule models.ComplianceRule, policies []models.AuthorizationPolicy) models.ComplianceResult {
	violations := make([]string, 0)

	for _, p := range policies {
		if p.Action != "ALLOW" {
			continue
		}
		for _, r := range p.Rules {
			if len(r.Paths) == 0 {
				violations = append(violations,
					"Policy '"+p.Name+"' has no path restrictions for "+r.From+" -> "+r.To)
			}
		}
	}

	if len(violations) == 0 {
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "All policies specify path restrictions",
		}
	}

	return models.ComplianceResult{
		Rule:       rule,
		Passed:     false,
		Details:    "Some policies allow all paths. Consider specifying exact paths.",
		Violations: violations,
	}
}

func (cc *ComplianceChecker) checkNoEmptySelector(rule models.ComplianceRule, policies []models.AuthorizationPolicy) models.ComplianceResult {
	violations := make([]string, 0)

	for _, p := range policies {
		if p.Selector == nil || len(p.Selector) == 0 {
			violations = append(violations,
				"Policy '"+p.Name+"' has no selector (applies to all workloads in namespace)")
		}
	}

	if len(violations) == 0 {
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "All policies have proper selectors",
		}
	}

	return models.ComplianceResult{
		Rule:       rule,
		Passed:     false,
		Details:    "Some policies have empty selectors. Add matchLabels to target specific workloads.",
		Violations: violations,
	}
}

func (cc *ComplianceChecker) checkNoNamespaceWide(rule models.ComplianceRule, policies []models.AuthorizationPolicy) models.ComplianceResult {
	violations := make([]string, 0)

	for _, p := range policies {
		for _, r := range p.Rules {
			if r.To == "*" && p.Action == "ALLOW" {
				violations = append(violations,
					"Policy '"+p.Name+"' allows access to all services (*) from '"+r.From+"'")
			}
		}
	}

	if len(violations) == 0 {
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "No namespace-wide ALLOW policies found",
		}
	}

	return models.ComplianceResult{
		Rule:       rule,
		Passed:     false,
		Details:    "Some policies allow access to all services. Consider restricting to specific destinations.",
		Violations: violations,
	}
}

func (cc *ComplianceChecker) checkLeastPrivilege(rule models.ComplianceRule, policies []models.AuthorizationPolicy, graph *models.ServiceGraph) models.ComplianceResult {
	violations := make([]string, 0)

	if graph == nil {
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "No service graph available for least privilege check",
		}
	}

	servicePermissions := make(map[string]map[string]bool)
	for _, edge := range graph.Edges {
		if _, ok := servicePermissions[edge.Source.Name]; !ok {
			servicePermissions[edge.Source.Name] = make(map[string]bool)
		}
		servicePermissions[edge.Source.Name][edge.Destination.Name] = true
	}

	for _, p := range policies {
		if p.Action != "ALLOW" {
			continue
		}
		for _, r := range p.Rules {
			if r.From == "*" {
				continue
			}
			allowedDests := r.To
			if allowedDests == "*" {
				continue
			}
			if perms, ok := servicePermissions[r.From]; ok {
				if !perms[allowedDests] {
					violations = append(violations,
						"Policy '"+p.Name+"' allows "+r.From+" -> "+allowedDests+", but no such traffic observed")
				}
			}
		}
	}

	if len(violations) == 0 {
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "All permissions align with observed traffic patterns",
		}
	}

	return models.ComplianceResult{
		Rule:       rule,
		Passed:     false,
		Details:    "Some permissions are not backed by observed traffic patterns.",
		Violations: violations,
	}
}

func (cc *ComplianceChecker) checkMTLS(rule models.ComplianceRule, policies []models.AuthorizationPolicy) models.ComplianceResult {
	violations := make([]string, 0)

	for _, p := range policies {
		if p.Action != "ALLOW" {
			continue
		}
		for _, r := range p.Rules {
			if r.From != "*" && !looksLikeServiceAccount(r.From) {
				violations = append(violations,
					"Policy '"+p.Name+"' source '"+r.From+"' does not appear to be a service account identity")
			}
		}
	}

	if len(violations) == 0 {
		return models.ComplianceResult{
			Rule:    rule,
			Passed:  true,
			Details: "All policies use service account identities compatible with mTLS",
		}
	}

	return models.ComplianceResult{
		Rule:       rule,
		Passed:     false,
		Details:    "Some policies may not work correctly with mTLS. Use service account identities.",
		Violations: violations,
	}
}

func looksLikeServiceAccount(s string) bool {
	if s == "*" {
		return false
	}
	return true
}
