package generator

import (
	"authz-policy-recommender/backend/pkg/models"
	"fmt"
	"sort"
	"strings"
)

type PolicyGenerator struct {
}

func NewPolicyGenerator() *PolicyGenerator {
	return &PolicyGenerator{}
}

type MethodPathKey struct {
	Method string
	Path   string
}

func (pg *PolicyGenerator) GeneratePolicies(edges []models.CallEdge) []models.AuthorizationPolicy {
	policies := make([]models.AuthorizationPolicy, 0)

	destMap := make(map[string]map[string]map[MethodPathKey]bool)

	for _, edge := range edges {
		dest := edge.Destination.Name
		source := edge.Source.Name
		key := MethodPathKey{Method: edge.Method, Path: edge.Path}

		if _, ok := destMap[dest]; !ok {
			destMap[dest] = make(map[string]map[MethodPathKey]bool)
		}
		if _, ok := destMap[dest][source]; !ok {
			destMap[dest][source] = make(map[MethodPathKey]bool)
		}
		destMap[dest][source][key] = true
	}

	destNames := make([]string, 0, len(destMap))
	for dest := range destMap {
		destNames = append(destNames, dest)
	}
	sort.Strings(destNames)

	for _, dest := range destNames {
		rules := make([]models.Rule, 0)

		sourceNames := make([]string, 0, len(destMap[dest]))
		for src := range destMap[dest] {
			sourceNames = append(sourceNames, src)
		}
		sort.Strings(sourceNames)

		for _, source := range sourceNames {
			methodsSet := make(map[string]bool)
			pathsSet := make(map[string]bool)

			for k := range destMap[dest][source] {
				methodsSet[k.Method] = true
				normalizedPath := normalizePath(k.Path)
				if normalizedPath != "" {
					pathsSet[normalizedPath] = true
				}
			}

			methods := make([]string, 0, len(methodsSet))
			for m := range methodsSet {
				methods = append(methods, m)
			}
			sort.Strings(methods)

			paths := make([]string, 0, len(pathsSet))
			for p := range pathsSet {
				paths = append(paths, p)
			}
			sort.Strings(paths)

			rules = append(rules, models.Rule{
				From:    source,
				To:      dest,
				Methods: methods,
				Paths:   paths,
			})
		}

		policy := models.AuthorizationPolicy{
			Name:      fmt.Sprintf("allow-%s", dest),
			Namespace: "default",
			Action:    "ALLOW",
			Rules:     rules,
			Selector: map[string]string{
				"app": dest,
			},
		}

		policies = append(policies, policy)
	}

	return policies
}

func normalizePath(path string) string {
	if path == "" {
		return ""
	}

	parts := strings.Split(path, "/")
	normalizedParts := make([]string, 0)

	for _, part := range parts {
		if part == "" {
			continue
		}
		if looksLikeID(part) {
			normalizedParts = append(normalizedParts, "{id}")
		} else {
			normalizedParts = append(normalizedParts, part)
		}
	}

	if len(normalizedParts) == 0 {
		return "/"
	}

	return "/" + strings.Join(normalizedParts, "/")
}

func looksLikeID(s string) bool {
	if len(s) == 0 {
		return false
	}

	hasDigit := false
	for _, c := range s {
		if c >= '0' && c <= '9' {
			hasDigit = true
			break
		}
	}

	if hasDigit && len(s) >= 2 {
		return true
	}

	uuidLike := len(s) == 36 && strings.Count(s, "-") == 4
	return uuidLike
}

func (pg *PolicyGenerator) GenerateIstioYAML(policy models.AuthorizationPolicy) (string, error) {
	var rulesYAML strings.Builder

	for _, rule := range policy.Rules {
		var fromSources strings.Builder
		fromSources.WriteString(fmt.Sprintf("            - principals: [\"cluster.local/ns/default/sa/%s\"]\n", rule.From))

		var toOperations strings.Builder
		for _, method := range rule.Methods {
			toOperations.WriteString(fmt.Sprintf("              - methods: [\"%s\"]\n", method))
		}
		if len(rule.Paths) > 0 {
			pathsStr := strings.Join(quoteAll(rule.Paths), ", ")
			toOperations.WriteString(fmt.Sprintf("                paths: [%s]\n", pathsStr))
		}

		rulesYAML.WriteString("          - from:\n")
		rulesYAML.WriteString(fromSources.String())
		rulesYAML.WriteString("            to:\n")
		rulesYAML.WriteString(toOperations.String())
	}

	selectorStr := ""
	for k, v := range policy.Selector {
		selectorStr += fmt.Sprintf("      %s: \"%s\"\n", k, v)
	}

	yaml := fmt.Sprintf(`apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: %s
  namespace: %s
spec:
  selector:
    matchLabels:
%s  action: %s
  rules:
%s`, policy.Name, policy.Namespace, selectorStr, policy.Action, rulesYAML.String())

	return yaml, nil
}

func quoteAll(strs []string) []string {
	quoted := make([]string, len(strs))
	for i, s := range strs {
		quoted[i] = fmt.Sprintf("\"%s\"", s)
	}
	return quoted
}

func (pg *PolicyGenerator) GenerateDenyAllPolicy(namespace string) models.AuthorizationPolicy {
	return models.AuthorizationPolicy{
		Name:      "deny-all",
		Namespace: namespace,
		Action:    "DENY",
		Rules: []models.Rule{
			{
				From:    "*",
				To:      "*",
				Methods: []string{"*"},
			},
		},
	}
}

func (pg *PolicyGenerator) OptimizePolicies(policies []models.AuthorizationPolicy) []models.AuthorizationPolicy {
	optimized := make([]models.AuthorizationPolicy, 0, len(policies))

	for _, policy := range policies {
		if len(policy.Rules) <= 1 {
			optimized = append(optimized, policy)
			continue
		}

		mergedRules := pg.mergeRules(policy.Rules)
		optimized = append(optimized, models.AuthorizationPolicy{
			Name:      policy.Name,
			Namespace: policy.Namespace,
			Action:    policy.Action,
			Rules:     mergedRules,
			Selector:  policy.Selector,
		})
	}

	return optimized
}

func (pg *PolicyGenerator) mergeRules(rules []models.Rule) []models.Rule {
	type ruleKey struct {
		From string
		To   string
	}

	ruleMap := make(map[ruleKey]models.Rule)

	for _, rule := range rules {
		key := ruleKey{From: rule.From, To: rule.To}
		if existing, ok := ruleMap[key]; ok {
			methods := union(existing.Methods, rule.Methods)
			paths := union(existing.Paths, rule.Paths)
			existing.Methods = methods
			existing.Paths = paths
			ruleMap[key] = existing
		} else {
			ruleMap[key] = rule
		}
	}

	merged := make([]models.Rule, 0, len(ruleMap))
	for _, r := range ruleMap {
		merged = append(merged, r)
	}

	sort.Slice(merged, func(i, j int) bool {
		if merged[i].From != merged[j].From {
			return merged[i].From < merged[j].From
		}
		return merged[i].To < merged[j].To
	})

	return merged
}

func union(a, b []string) []string {
	set := make(map[string]bool)
	for _, s := range a {
		set[s] = true
	}
	for _, s := range b {
		set[s] = true
	}
	result := make([]string, 0, len(set))
	for s := range set {
		result = append(result, s)
	}
	sort.Strings(result)
	return result
}
