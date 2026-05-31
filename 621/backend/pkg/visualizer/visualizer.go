package visualizer

import (
	"authz-policy-recommender/backend/pkg/models"
)

type PolicyVisualizer struct {
}

func NewPolicyVisualizer() *PolicyVisualizer {
	return &PolicyVisualizer{}
}

func (pv *PolicyVisualizer) GetCoverageVisualization(
	policies []models.AuthorizationPolicy,
	graph *models.ServiceGraph,
) models.CoverageVisualization {
	if graph == nil || len(graph.Edges) == 0 {
		return models.CoverageVisualization{
			ServiceGraph: graph,
		}
	}

	coveredEdgeKeys := make(map[string]bool)
	policyCoverages := make([]models.PolicyCoverage, 0, len(policies))

	for _, policy := range policies {
		policyCoverage := pv.analyzePolicyCoverage(policy, graph)
		policyCoverages = append(policyCoverages, policyCoverage)

		for _, edgeKey := range policyCoverage.CoveredEdges {
			coveredEdgeKeys[edgeKey] = true
		}
	}

	coveredEdgeList := make([]string, 0, len(coveredEdgeKeys))
	for key := range coveredEdgeKeys {
		coveredEdgeList = append(coveredEdgeList, key)
	}

	totalEdges := len(graph.Edges)
	coveredEdges := len(coveredEdgeList)
	overallCoverage := 0.0
	if totalEdges > 0 {
		overallCoverage = float64(coveredEdges) / float64(totalEdges) * 100
	}

	return models.CoverageVisualization{
		TotalServices:   len(graph.Services),
		TotalEdges:      totalEdges,
		CoveredEdges:    coveredEdges,
		UncoveredEdges:  totalEdges - coveredEdges,
		OverallCoverage: overallCoverage,
		PolicyCoverages: policyCoverages,
		ServiceGraph:    graph,
		CoveredEdgeKeys: coveredEdgeList,
	}
}

func (pv *PolicyVisualizer) analyzePolicyCoverage(
	policy models.AuthorizationPolicy,
	graph *models.ServiceGraph,
) models.PolicyCoverage {
	coveredEdges := make([]string, 0)
	uncoveredEdges := make([]string, 0)

	for _, edge := range graph.Edges {
		edgeKey := pv.getEdgeKey(edge)
		covered := false

		for _, rule := range policy.Rules {
			if pv.edgeMatchesRule(edge, rule) {
				covered = true
				break
			}
		}

		if covered {
			coveredEdges = append(coveredEdges, edgeKey)
		} else {
			uncoveredEdges = append(uncoveredEdges, edgeKey)
		}
	}

	totalCalls := len(graph.Edges)
	coverageRate := 0.0
	if totalCalls > 0 {
		coverageRate = float64(len(coveredEdges)) / float64(totalCalls) * 100
	}

	return models.PolicyCoverage{
		PolicyName:     policy.Name,
		CoveredCalls:   len(coveredEdges),
		TotalCalls:     totalCalls,
		CoverageRate:   coverageRate,
		CoveredEdges:   coveredEdges,
		UncoveredEdges: uncoveredEdges,
	}
}

func (pv *PolicyVisualizer) getEdgeKey(edge models.CallEdge) string {
	return edge.Source.Name + "->" + edge.Destination.Name
}

func (pv *PolicyVisualizer) edgeMatchesRule(edge models.CallEdge, rule models.Rule) bool {
	if rule.From != "" {
		if !pv.matchesSource(edge.Source, rule.From) {
			return false
		}
	}

	if rule.To != "" {
		if !pv.matchesDestination(edge.Destination, rule.To) {
			return false
		}
	}

	if len(rule.Methods) > 0 {
		methodMatch := false
		for _, m := range rule.Methods {
			if m == "*" || m == edge.Method {
				methodMatch = true
				break
			}
		}
		if !methodMatch {
			return false
		}
	}

	if len(rule.Paths) > 0 {
		pathMatch := false
		for _, p := range rule.Paths {
			if p == "*" || pv.pathMatches(p, edge.Path) {
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

func (pv *PolicyVisualizer) matchesSource(source models.Service, pattern string) bool {
	if pattern == "*" {
		return true
	}

	if pattern == source.Name {
		return true
	}

	if source.Namespace != "" && pattern == source.Namespace {
		return true
	}

	return false
}

func (pv *PolicyVisualizer) matchesDestination(dest models.Service, pattern string) bool {
	return pv.matchesSource(dest, pattern)
}

func (pv *PolicyVisualizer) pathMatches(pattern, path string) bool {
	if pattern == path {
		return true
	}

	if len(pattern) > 0 && pattern[len(pattern)-1] == '*' {
		prefix := pattern[:len(pattern)-1]
		if len(path) >= len(prefix) && path[:len(prefix)] == prefix {
			return true
		}
	}

	return false
}

func (pv *PolicyVisualizer) GetServiceCoverageMap(
	policies []models.AuthorizationPolicy,
	graph *models.ServiceGraph,
) map[string]bool {
	if graph == nil {
		return nil
	}

	coverageMap := make(map[string]bool)

	for _, service := range graph.Services {
		coverageMap[service.Name] = false
	}

	coverage := pv.GetCoverageVisualization(policies, graph)
	for _, edgeKey := range coverage.CoveredEdgeKeys {
		parts := splitEdgeKey(edgeKey)
		if len(parts) == 2 {
			coverageMap[parts[1]] = true
		}
	}

	return coverageMap
}

func splitEdgeKey(key string) []string {
	for i := 0; i < len(key); i++ {
		if i > 0 && key[i] == '-' && key[i+1] == '>' {
			return []string{key[:i], key[i+2:]}
		}
	}
	return []string{key}
}
