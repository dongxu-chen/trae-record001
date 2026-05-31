package dependency

import (
	"capacity-planner/pkg/models"
	"capacity-planner/pkg/queueing"
	"math"
)

type ServiceNode struct {
	ID             string
	Name           string
	Dependencies   []*ServiceNode
	Downstream     []*ServiceNode
	TrafficFactor  float64
	RequestWeight  float64
}

type TrafficPropagationMatrix struct {
	Matrix       map[string]map[string]float64
	ServiceOrder []string
}

type ChainImpact struct {
	Chain        []string
	ImpactFactor float64
	TrafficRatio float64
}

type SensitivityAnalysis struct {
	ServiceID        string
	SensitivityIndex float64
	CriticalityScore float64
	FailureImpact    float64
}

func BuildDependencyGraph(services []models.Service) map[string]*ServiceNode {
	nodes := make(map[string]*ServiceNode)

	for _, svc := range services {
		nodes[svc.ID] = &ServiceNode{
			ID:             svc.ID,
			Name:           svc.Name,
			Dependencies:   make([]*ServiceNode, 0),
			Downstream:     make([]*ServiceNode, 0),
			TrafficFactor:  1.0,
			RequestWeight:  1.0,
		}
	}

	for _, svc := range services {
		node := nodes[svc.ID]
		for _, depID := range svc.Dependencies {
			if depNode, exists := nodes[depID]; exists {
				node.Dependencies = append(node.Dependencies, depNode)
				depNode.Downstream = append(depNode.Downstream, node)
			}
		}
	}

	return nodes
}

func BuildTrafficPropagationMatrix(
	graph map[string]*ServiceNode,
	services []models.Service,
) TrafficPropagationMatrix {
	serviceOrder := make([]string, 0, len(services))
	for _, svc := range services {
		serviceOrder = append(serviceOrder, svc.ID)
	}

	matrix := make(map[string]map[string]float64)
	for _, from := range serviceOrder {
		matrix[from] = make(map[string]float64)
		for _, to := range serviceOrder {
			matrix[from][to] = 0.0
		}
		matrix[from][from] = 1.0
	}

	for _, from := range serviceOrder {
		visited := make(map[string]bool)
		var propagate func(string, float64)
		propagate = func(current string, factor float64) {
			if visited[current] {
				return
			}
			visited[current] = true

			node := graph[current]
			if node == nil {
				return
			}

			for _, dep := range node.Dependencies {
				edgeFactor := 1.2 + node.RequestWeight*0.1
				newFactor := factor * edgeFactor
				matrix[from][dep.ID] += newFactor
				propagate(dep.ID, newFactor)
			}
		}
		propagate(from, 1.0)
	}

	return TrafficPropagationMatrix{
		Matrix:       matrix,
		ServiceOrder: serviceOrder,
	}
}

func CalculateTrafficWithMatrix(
	tpm TrafficPropagationMatrix,
	entryTraffic map[string]float64,
) map[string]float64 {
	result := make(map[string]float64)

	for _, to := range tpm.ServiceOrder {
		total := 0.0
		for from, traffic := range entryTraffic {
			if factor, exists := tpm.Matrix[from][to]; exists {
				total += traffic * factor
			}
		}
		result[to] = total
	}

	return result
}

func CalculateTrafficPropagation(
	graph map[string]*ServiceNode,
	entryTraffic map[string]float64,
) map[string]float64 {
	serviceTraffic := make(map[string]float64)

	for id, traffic := range entryTraffic {
		serviceTraffic[id] = traffic
	}

	visited := make(map[string]bool)
	var dfs func(string)
	dfs = func(id string) {
		if visited[id] {
			return
		}
		visited[id] = true

		node := graph[id]
		if node == nil {
			return
		}

		currentTraffic := serviceTraffic[id]

		for _, dep := range node.Dependencies {
			factor := 1.5
			depTraffic := currentTraffic * factor
			if existing, exists := serviceTraffic[dep.ID]; exists {
				serviceTraffic[dep.ID] = existing + depTraffic
			} else {
				serviceTraffic[dep.ID] = depTraffic
			}
			dfs(dep.ID)
		}
	}

	for id := range entryTraffic {
		dfs(id)
	}

	return serviceTraffic
}

func AnalyzeChainImpact(
	graph map[string]*ServiceNode,
	entryServiceID string,
	baseTraffic float64,
) []ChainImpact {
	chains := findAllChains(graph, entryServiceID)

	impacts := make([]ChainImpact, 0, len(chains))
	for _, chain := range chains {
		impactFactor := 1.0
		for i := 0; i < len(chain)-1; i++ {
			node := graph[chain[i]]
			if node != nil {
				impactFactor *= 1.2 + node.RequestWeight*0.1
			}
		}
		impacts = append(impacts, ChainImpact{
			Chain:        chain,
			ImpactFactor: impactFactor,
			TrafficRatio: (baseTraffic * impactFactor) / baseTraffic,
		})
	}

	return impacts
}

func findAllChains(graph map[string]*ServiceNode, startID string) [][]string {
	var result [][]string
	var dfs func(string, []string)
	visited := make(map[string]bool)

	dfs = func(id string, path []string) {
		if visited[id] {
			return
		}
		visited[id] = true
		defer func() { visited[id] = false }()

		currentPath := append(path, id)

		node := graph[id]
		if node == nil || len(node.Dependencies) == 0 {
			chainCopy := make([]string, len(currentPath))
			copy(chainCopy, currentPath)
			result = append(result, chainCopy)
			return
		}

		for _, dep := range node.Dependencies {
			dfs(dep.ID, currentPath)
		}
	}

	dfs(startID, []string{})
	return result
}

func CalculateSensitivity(
	graph map[string]*ServiceNode,
	trafficMap map[string]float64,
	serverConfig models.ServerConfig,
) []SensitivityAnalysis {
	results := make([]SensitivityAnalysis, 0)

	for id := range graph {
		traffic := trafficMap[id]
		if traffic == 0 {
			traffic = 100
		}

		result := queueing.CalculateCapacity(id, traffic, serverConfig, 0.7, 200)
		baseServers := result.RecommendedServers

		increasedTraffic := traffic * 1.1
		increasedResult := queueing.CalculateCapacity(id, increasedTraffic, serverConfig, 0.7, 200)
		increasedServers := increasedResult.RecommendedServers

		sensitivityIndex := 0.0
		if baseServers > 0 {
			sensitivityIndex = float64(increasedServers-baseServers) / float64(baseServers) / 0.1
		}

		downstreamCount := len(graph[id].Downstream)
		criticalityScore := sensitivityIndex * (1.0 + float64(downstreamCount)*0.5)
		failureImpact := float64(downstreamCount) * traffic

		results = append(results, SensitivityAnalysis{
			ServiceID:        id,
			SensitivityIndex: sensitivityIndex,
			CriticalityScore: criticalityScore,
			FailureImpact:    failureImpact,
		})
	}

	return results
}

func FindCriticalPath(
	graph map[string]*ServiceNode,
	entryServiceID string,
	trafficMap map[string]float64,
	serverConfig models.ServerConfig,
) []string {
	chains := findAllChains(graph, entryServiceID)

	maxCriticality := 0.0
	criticalPath := []string{}

	for _, chain := range chains {
		totalCriticality := 0.0
		for _, id := range chain {
			traffic := trafficMap[id]
			if traffic == 0 {
				traffic = 100
			}
			result := queueing.CalculateCapacity(id, traffic, serverConfig, 0.7, 200)
			totalCriticality += result.Utilization
		}
		avgCriticality := totalCriticality / float64(len(chain))

		if avgCriticality > maxCriticality {
			maxCriticality = avgCriticality
			criticalPath = chain
		}
	}

	return criticalPath
}

func AnalyzeDependencies(
	services []models.Service,
	entryServiceID string,
	entryTraffic float64,
	serverConfig models.ServerConfig,
	targetUtilization float64,
	maxLatency float64,
) models.DependencyResult {
	graph := BuildDependencyGraph(services)

	entryTrafficMap := map[string]float64{entryServiceID: entryTraffic}
	serviceTraffic := CalculateTrafficPropagation(graph, entryTrafficMap)

	totalServers := 0
	dependencyImpact := make(map[string]float64)

	for svcID, traffic := range serviceTraffic {
		result := queueing.CalculateCapacity(svcID, traffic, serverConfig, targetUtilization, maxLatency)
		totalServers += result.RecommendedServers

		if svcID != entryServiceID {
			impact := float64(result.RecommendedServers) / float64(totalServers)
			dependencyImpact[svcID] = impact
		}
	}

	entryResult := queueing.CalculateCapacity(entryServiceID, entryTraffic, serverConfig, targetUtilization, maxLatency)

	return models.DependencyResult{
		ServiceID:        entryServiceID,
		RequiredServers:  entryResult.RecommendedServers,
		DependencyImpact: dependencyImpact,
		TotalCapacity:    totalServers,
	}
}

func FindBottlenecks(
	graph map[string]*ServiceNode,
	serviceTraffic map[string]float64,
	serverConfig models.ServerConfig,
	targetUtilization float64,
) []string {
	bottlenecks := make([]string, 0)

	for svcID, traffic := range serviceTraffic {
		result := queueing.CalculateCapacity(svcID, traffic, serverConfig, targetUtilization, 0)
		if result.Utilization > 0.85 {
			bottlenecks = append(bottlenecks, svcID)
		}
	}

	return bottlenecks
}

func CalculateTotalCapacityWithDependencies(
	services []models.Service,
	servicePeakTraffic map[string]float64,
	serverConfigs []models.ServerConfig,
	targetUtilization float64,
	maxLatency float64,
	useMatrix bool,
) ([]models.CapacityResult, float64) {
	results := make([]models.CapacityResult, 0)
	totalMonthlyCost := 0.0

	var trafficMap map[string]float64
	if useMatrix {
		graph := BuildDependencyGraph(services)
		tpm := BuildTrafficPropagationMatrix(graph, services)
		trafficMap = CalculateTrafficWithMatrix(tpm, servicePeakTraffic)
	} else {
		graph := BuildDependencyGraph(services)
		trafficMap = CalculateTrafficPropagation(graph, servicePeakTraffic)
	}

	for _, svc := range services {
		traffic := trafficMap[svc.ID]
		if traffic == 0 {
			traffic = 100
		}

		bestConfig, result := queueing.OptimizeServerConfig(traffic, serverConfigs, targetUtilization, maxLatency)
		result.ServiceID = svc.ID
		result.ServerConfig = bestConfig
		results = append(results, result)
		totalMonthlyCost += result.MonthlyCost
	}

	return results, totalMonthlyCost
}

func GetDependencyChain(graph map[string]*ServiceNode, serviceID string) []string {
	chain := make([]string, 0)
	visited := make(map[string]bool)

	var dfs func(string)
	dfs = func(id string) {
		if visited[id] {
			return
		}
		visited[id] = true
		chain = append(chain, id)

		node := graph[id]
		if node == nil {
			return
		}

		for _, dep := range node.Dependencies {
			dfs(dep.ID)
		}
	}

	dfs(serviceID)
	return chain
}

func CalculateFailureImpactScore(
	graph map[string]*ServiceNode,
	serviceID string,
	trafficMap map[string]float64,
) float64 {
	impact := 0.0
	visited := make(map[string]bool)

	var dfs func(string, float64)
	dfs = func(id string, multiplier float64) {
		if visited[id] {
			return
		}
		visited[id] = true

		node := graph[id]
		if node == nil {
			return
		}

		traffic := trafficMap[id]
		impact += traffic * multiplier

		for _, downstream := range node.Downstream {
			dfs(downstream.ID, multiplier*0.8)
		}
	}

	dfs(serviceID, 1.0)
	return impact
}

func CalculateRedundancyRequirement(
	serviceID string,
	sensitivity SensitivityAnalysis,
	availabilityTarget float64,
) int {
	baseServers := 2

	baseAvailability := 0.99
	if availabilityTarget <= baseAvailability {
		return baseServers
	}

	sensitivityFactor := 1.0 + sensitivity.CriticalityScore*0.5
	requiredNines := -math.Log10(1.0 - availabilityTarget)

	additionalServers := int(math.Ceil((requiredNines - 2) * sensitivityFactor))

	return baseServers + additionalServers
}
