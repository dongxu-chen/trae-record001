package conflict

import (
	"authz-policy-recommender/backend/pkg/models"
	"sort"
	"strings"
)

type ConflictDetector struct {
}

func NewConflictDetector() *ConflictDetector {
	return &ConflictDetector{}
}

func (cd *ConflictDetector) DetectConflicts(policies []models.AuthorizationPolicy) []models.PolicyConflict {
	conflicts := make([]models.PolicyConflict, 0)

	conflicts = append(conflicts, cd.detectShadowingConflicts(policies)...)
	conflicts = append(conflicts, cd.detectOverlapConflicts(policies)...)
	conflicts = append(conflicts, cd.detectContradictionConflicts(policies)...)
	conflicts = append(conflicts, cd.detectOverlyBroadPolicies(policies)...)

	return conflicts
}

func (cd *ConflictDetector) detectShadowingConflicts(policies []models.AuthorizationPolicy) []models.PolicyConflict {
	conflicts := make([]models.PolicyConflict, 0)

	for i := range policies {
		for j := i + 1; j < len(policies); j++ {
			pA := policies[i]
			pB := policies[j]

			if pA.Namespace != pB.Namespace {
				continue
			}

			if pA.Action == pB.Action {
				continue
			}

			for _, ruleA := range pA.Rules {
				for _, ruleB := range pB.Rules {
					if cd.isRuleShadowed(ruleA, ruleB) {
						affected := cd.getAffectedServices(ruleA, ruleB)
						conflicts = append(conflicts, models.PolicyConflict{
							Type:        "SHADOWING",
							Severity:    "HIGH",
							Description: cd.describeShadowing(pA, pB, ruleA, ruleB),
							PolicyA:     pA.Name,
							PolicyB:     pB.Name,
							AffectedServices: affected,
						})
					}
				}
			}
		}
	}

	return conflicts
}

func (cd *ConflictDetector) isRuleShadowed(rA, rB models.Rule) bool {
	if rA.To != rB.To && rA.To != "*" && rB.To != "*" {
		return false
	}

	fromMatches := rA.From == "*" || rB.From == "*" || rA.From == rB.From
	if !fromMatches {
		return false
	}

	methodsASet := make(map[string]bool)
	for _, m := range rA.Methods {
		methodsASet[m] = true
	}
	methodsBSet := make(map[string]bool)
	for _, m := range rB.Methods {
		methodsBSet[m] = true
	}

	if methodsASet["*"] || methodsBSet["*"] {
		return true
	}

	for m := range methodsASet {
		if methodsBSet[m] {
			return true
		}
	}

	return false
}

func (cd *ConflictDetector) detectOverlapConflicts(policies []models.AuthorizationPolicy) []models.PolicyConflict {
	conflicts := make([]models.PolicyConflict, 0)

	for i := range policies {
		for j := i + 1; j < len(policies); j++ {
			pA := policies[i]
			pB := policies[j]

			if pA.Namespace != pB.Namespace {
				continue
			}

			if pA.Action != pB.Action {
				continue
			}

			for _, ruleA := range pA.Rules {
				for _, ruleB := range pB.Rules {
					overlap := cd.findRuleOverlap(ruleA, ruleB)
					if len(overlap) > 0 {
						affected := cd.getAffectedServices(ruleA, ruleB)
						conflicts = append(conflicts, models.PolicyConflict{
							Type:        "OVERLAP",
							Severity:    "MEDIUM",
							Description: cd.describeOverlap(pA, pB, ruleA, ruleB, overlap),
							PolicyA:     pA.Name,
							PolicyB:     pB.Name,
							AffectedServices: affected,
						})
					}
				}
			}
		}
	}

	return conflicts
}

func (cd *ConflictDetector) findRuleOverlap(rA, rB models.Rule) []string {
	if rA.To != rB.To {
		return nil
	}
	if rA.From != rB.From {
		return nil
	}

	overlap := make([]string, 0)
	methodsA := make(map[string]bool)
	for _, m := range rA.Methods {
		methodsA[m] = true
	}
	for _, m := range rB.Methods {
		if methodsA[m] || methodsA["*"] || m == "*" {
			overlap = append(overlap, m)
		}
	}

	return overlap
}

func (cd *ConflictDetector) detectContradictionConflicts(policies []models.AuthorizationPolicy) []models.PolicyConflict {
	conflicts := make([]models.PolicyConflict, 0)

	allowMap := make(map[string][]models.Rule)
	denyMap := make(map[string][]models.Rule)

	for _, p := range policies {
		for _, rule := range p.Rules {
			key := rule.To
			if p.Action == "ALLOW" {
				allowMap[key] = append(allowMap[key], rule)
			} else if p.Action == "DENY" {
				denyMap[key] = append(denyMap[key], rule)
			}
		}
	}

	for dest, allowRules := range allowMap {
		if denyRules, ok := denyMap[dest]; ok {
			for _, ar := range allowRules {
				for _, dr := range denyRules {
					if cd.rulesContradict(ar, dr) {
						affected := []string{dest}
						if ar.From != "*" {
							affected = append(affected, ar.From)
						}
						conflicts = append(conflicts, models.PolicyConflict{
							Type:             "CONTRADICTION",
							Severity:         "CRITICAL",
							Description:      cd.describeContradiction(ar, dr),
							PolicyA:          "allow-rules",
							PolicyB:          "deny-rules",
							AffectedServices: affected,
						})
					}
				}
			}
		}
	}

	return conflicts
}

func (cd *ConflictDetector) rulesContradict(rA, rB models.Rule) bool {
	if rA.To != rB.To && rA.To != "*" && rB.To != "*" {
		return false
	}

	fromMatch := rA.From == "*" || rB.From == "*" || rA.From == rB.From
	if !fromMatch {
		return false
	}

	for _, mA := range rA.Methods {
		for _, mB := range rB.Methods {
			if mA == "*" || mB == "*" || mA == mB {
				return true
			}
		}
	}

	return false
}

func (cd *ConflictDetector) detectOverlyBroadPolicies(policies []models.AuthorizationPolicy) []models.PolicyConflict {
	conflicts := make([]models.PolicyConflict, 0)

	for _, p := range policies {
		for _, rule := range p.Rules {
			if rule.From == "*" && p.Action == "ALLOW" {
				conflicts = append(conflicts, models.PolicyConflict{
					Type:             "OVERLY_BROAD",
					Severity:         "MEDIUM",
					Description:      cd.describeOverlyBroad(p, rule),
					PolicyA:          p.Name,
					AffectedServices: []string{rule.To},
				})
			}

			hasWildcardMethod := false
			for _, m := range rule.Methods {
				if m == "*" {
					hasWildcardMethod = true
					break
				}
			}
			if hasWildcardMethod && p.Action == "ALLOW" && rule.From != "*" {
				conflicts = append(conflicts, models.PolicyConflict{
					Type:             "WILDCARD_METHOD",
					Severity:         "LOW",
					Description:      cd.describeWildcardMethod(p, rule),
					PolicyA:          p.Name,
					AffectedServices: []string{rule.To},
				})
			}
		}
	}

	return conflicts
}

func (cd *ConflictDetector) getAffectedServices(rA, rB models.Rule) []string {
	services := make(map[string]bool)
	if rA.From != "*" {
		services[rA.From] = true
	}
	if rB.From != "*" {
		services[rB.From] = true
	}
	if rA.To != "*" {
		services[rA.To] = true
	}
	if rB.To != "*" {
		services[rB.To] = true
	}

	result := make([]string, 0, len(services))
	for s := range services {
		result = append(result, s)
	}
	sort.Strings(result)
	return result
}

func (cd *ConflictDetector) describeShadowing(pA, pB models.AuthorizationPolicy, rA, rB models.Rule) string {
	shadowed := pA
	shadowing := pB
	if pA.Action == "DENY" {
		shadowed = pB
		shadowing = pA
	}
	return strings.Join([]string{
		"Policy '", shadowing.Name, "' (", shadowing.Action, ") shadows '",
		shadowed.Name, "' (", shadowed.Action, ") for traffic from ",
		rA.From, " to ", rA.To,
	}, "")
}

func (cd *ConflictDetector) describeOverlap(pA, pB models.AuthorizationPolicy, rA, rB models.Rule, overlap []string) string {
	return strings.Join([]string{
		"Policies '", pA.Name, "' and '", pB.Name, "' have overlapping rules for ",
		rA.From, " -> ", rA.To, " on methods: ", strings.Join(overlap, ", "),
	}, "")
}

func (cd *ConflictDetector) describeContradiction(ar, dr models.Rule) string {
	return strings.Join([]string{
		"Contradiction: ALLOW and DENY rules both match traffic from ",
		ar.From, " to ", ar.To, ". This may cause unexpected behavior.",
	}, "")
}

func (cd *ConflictDetector) describeOverlyBroad(p models.AuthorizationPolicy, r models.Rule) string {
	return strings.Join([]string{
		"Policy '", p.Name, "' allows traffic from ANY source (from: *) to ",
		r.To, ". Consider restricting to specific source services.",
	}, "")
}

func (cd *ConflictDetector) describeWildcardMethod(p models.AuthorizationPolicy, r models.Rule) string {
	return strings.Join([]string{
		"Policy '", p.Name, "' allows ALL HTTP methods (method: *) from ",
		r.From, " to ", r.To, ". Consider restricting to specific methods.",
	}, "")
}
