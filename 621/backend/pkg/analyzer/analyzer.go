package analyzer

import (
	"authz-policy-recommender/backend/pkg/models"
	"sort"
	"strings"
	"sync"
	"time"
)

type CallAnalyzer struct {
	mu               sync.RWMutex
	traces           map[string]*models.Trace
	edges            map[string]*models.CallEdge
	samplingStrategy models.SamplingStrategy
	edgeServices     map[string]bool
	ingressServices  map[string]bool
	egressServices   map[string]bool
}

type AnalyzerConfig struct {
	SamplingStrategy models.SamplingStrategy
	EdgeServices     []string
	IngressServices  []string
	EgressServices   []string
}

func NewCallAnalyzer() *CallAnalyzer {
	return NewCallAnalyzerWithConfig(AnalyzerConfig{
		SamplingStrategy: models.SamplingFull,
	})
}

func NewCallAnalyzerWithConfig(config AnalyzerConfig) *CallAnalyzer {
	edgeServices := make(map[string]bool)
	for _, svc := range config.EdgeServices {
		edgeServices[svc] = true
	}
	ingressServices := make(map[string]bool)
	for _, svc := range config.IngressServices {
		ingressServices[svc] = true
	}
	egressServices := make(map[string]bool)
	for _, svc := range config.EgressServices {
		egressServices[svc] = true
	}

	return &CallAnalyzer{
		traces:           make(map[string]*models.Trace),
		edges:            make(map[string]*models.CallEdge),
		samplingStrategy: config.SamplingStrategy,
		edgeServices:     edgeServices,
		ingressServices:  ingressServices,
		egressServices:   egressServices,
	}
}

func (ca *CallAnalyzer) SetSamplingStrategy(strategy models.SamplingStrategy) {
	ca.mu.Lock()
	defer ca.mu.Unlock()
	ca.samplingStrategy = strategy
}

func (ca *CallAnalyzer) SetEdgeServices(ingress, egress []string) {
	ca.mu.Lock()
	defer ca.mu.Unlock()

	ca.ingressServices = make(map[string]bool)
	for _, svc := range ingress {
		ca.ingressServices[svc] = true
	}

	ca.egressServices = make(map[string]bool)
	for _, svc := range egress {
		ca.egressServices[svc] = true
	}

	ca.edgeServices = make(map[string]bool)
	for _, svc := range ingress {
		ca.edgeServices[svc] = true
	}
	for _, svc := range egress {
		ca.edgeServices[svc] = true
	}
}

func (ca *CallAnalyzer) shouldSample(source, dest string) (bool, string, models.EdgeType) {
	switch ca.samplingStrategy {
	case models.SamplingFull:
		edgeType := ca.detectEdgeType(source, dest)
		return true, "FULL_SAMPLING", edgeType

	case models.SamplingEdge:
		edgeType := ca.detectEdgeType(source, dest)
		if edgeType == models.EdgeTypeIngress || edgeType == models.EdgeTypeEgress {
			return true, "EDGE_SAMPLING", edgeType
		}
		return false, "INTERNAL_SKIPPED", edgeType

	case models.SamplingAdaptive:
		edgeType := ca.detectEdgeType(source, dest)
		if edgeType == models.EdgeTypeIngress || edgeType == models.EdgeTypeEgress {
			return true, "ADAPTIVE_EDGE", edgeType
		}
		return ca.adaptiveSample(source, dest), edgeType

	default:
		edgeType := ca.detectEdgeType(source, dest)
		return true, "DEFAULT_FULL", edgeType
	}
}

func (ca *CallAnalyzer) detectEdgeType(source, dest string) models.EdgeType {
	isSourceIngress := ca.ingressServices[source] || strings.HasPrefix(source, "gateway") || strings.HasPrefix(source, "ingress")
	isDestEgress := ca.egressServices[dest] || strings.HasPrefix(dest, "external") || strings.HasSuffix(dest, "-external")

	if isSourceIngress {
		return models.EdgeTypeIngress
	}
	if isDestEgress {
		return models.EdgeTypeEgress
	}
	return models.EdgeTypeInternal
}

func (ca *CallAnalyzer) adaptiveSample(source, dest string) (bool, string) {
	key := source + "->" + dest
	edge, exists := ca.edges[key]
	if !exists {
		return true, "ADAPTIVE_NEW_EDGE"
	}

	if edge.Count > 100 {
		return edge.Count%10 == 0, "ADAPTIVE_HIGH_VOLUME"
	}

	return true, "ADAPTIVE_LOW_VOLUME"
}

func (ca *CallAnalyzer) AddTrace(trace models.Trace) {
	ca.mu.Lock()
	defer ca.mu.Unlock()

	ca.traces[trace.TraceID] = &trace

	spanMap := make(map[string]*models.Span)
	for i := range trace.Spans {
		spanMap[trace.Spans[i].SpanID] = &trace.Spans[i]
	}

	for _, span := range trace.Spans {
		if span.ParentID != "" {
			if parentSpan, ok := spanMap[span.ParentID]; ok {
				ca.addEdge(parentSpan, &span)
			}
		}
	}
}

func (ca *CallAnalyzer) addEdge(parent, child *models.Span) {
	sampled, reason, edgeType := ca.shouldSample(parent.Service, child.Service)

	key := ca.edgeKey(parent.Service, child.Service, child.Method, child.Path)

	if edge, ok := ca.edges[key]; ok {
		edge.Count++
		edge.LastSeen = child.StartTime
		if sampled {
			edge.Sampled = true
			edge.SamplingReason = reason
		}
	} else {
		ca.edges[key] = &models.CallEdge{
			Source: models.Service{
				Name:      parent.Service,
				Namespace: "default",
			},
			Destination: models.Service{
				Name:      child.Service,
				Namespace: "default",
			},
			Method:         child.Method,
			Path:           child.Path,
			Count:          1,
			LastSeen:       child.StartTime,
			EdgeType:       edgeType,
			Sampled:        sampled,
			SamplingReason: reason,
		}
	}
}

func (ca *CallAnalyzer) edgeKey(source, dest, method, path string) string {
	return strings.Join([]string{source, dest, method, path}, "|")
}

func (ca *CallAnalyzer) GetServiceGraph() *models.ServiceGraph {
	return ca.GetServiceGraphWithSampling(false)
}

func (ca *CallAnalyzer) GetServiceGraphWithSampling(onlySampled bool) *models.ServiceGraph {
	ca.mu.RLock()
	defer ca.mu.RUnlock()

	serviceSet := make(map[string]models.Service)
	edges := make([]models.CallEdge, 0, len(ca.edges))

	for _, edge := range ca.edges {
		if onlySampled && !edge.Sampled {
			continue
		}
		serviceSet[edge.Source.Name] = edge.Source
		serviceSet[edge.Destination.Name] = edge.Destination
		edges = append(edges, *edge)
	}

	services := make([]models.Service, 0, len(serviceSet))
	for _, svc := range serviceSet {
		services = append(services, svc)
	}

	sort.Slice(services, func(i, j int) bool {
		return services[i].Name < services[j].Name
	})

	sort.Slice(edges, func(i, j int) bool {
		if edges[i].Source.Name != edges[j].Source.Name {
			return edges[i].Source.Name < edges[j].Source.Name
		}
		return edges[i].Destination.Name < edges[j].Destination.Name
	})

	return &models.ServiceGraph{
		Services: services,
		Edges:    edges,
	}
}

func (ca *CallAnalyzer) GetCallRelations() []models.CallEdge {
	return ca.GetCallRelationsWithSampling(false)
}

func (ca *CallAnalyzer) GetCallRelationsWithSampling(onlySampled bool) []models.CallEdge {
	ca.mu.RLock()
	defer ca.mu.RUnlock()

	edges := make([]models.CallEdge, 0, len(ca.edges))
	for _, edge := range ca.edges {
		if onlySampled && !edge.Sampled {
			continue
		}
		edges = append(edges, *edge)
	}

	sort.Slice(edges, func(i, j int) bool {
		if edges[i].Source.Name != edges[j].Source.Name {
			return edges[i].Source.Name < edges[j].Source.Name
		}
		if edges[i].Destination.Name != edges[j].Destination.Name {
			return edges[i].Destination.Name < edges[j].Destination.Name
		}
		return edges[i].Method < edges[j].Method
	})

	return edges
}

func (ca *CallAnalyzer) GetEdgesByType(edgeType models.EdgeType) []models.CallEdge {
	ca.mu.RLock()
	defer ca.mu.RUnlock()

	edges := make([]models.CallEdge, 0)
	for _, edge := range ca.edges {
		if edge.EdgeType == edgeType {
			edges = append(edges, *edge)
		}
	}
	return edges
}

func (ca *CallAnalyzer) GetSamplingStats() map[string]interface{} {
	ca.mu.RLock()
	defer ca.mu.RUnlock()

	totalEdges := len(ca.edges)
	sampledEdges := 0
	ingressEdges := 0
	egressEdges := 0
	internalEdges := 0

	for _, edge := range ca.edges {
		if edge.Sampled {
			sampledEdges++
		}
		switch edge.EdgeType {
		case models.EdgeTypeIngress:
			ingressEdges++
		case models.EdgeTypeEgress:
			egressEdges++
		case models.EdgeTypeInternal:
			internalEdges++
		}
	}

	return map[string]interface{}{
		"strategy":       ca.samplingStrategy,
		"totalEdges":     totalEdges,
		"sampledEdges":   sampledEdges,
		"ingressEdges":   ingressEdges,
		"egressEdges":    egressEdges,
		"internalEdges":  internalEdges,
		"samplingRate":   float64(sampledEdges) / float64(totalEdges),
	}
}

func (ca *CallAnalyzer) GetUniqueServicePairs() []map[string]string {
	ca.mu.RLock()
	defer ca.mu.RUnlock()

	pairSet := make(map[string]map[string]string)

	for _, edge := range ca.edges {
		key := edge.Source.Name + "->" + edge.Destination.Name
		if _, ok := pairSet[key]; !ok {
			pairSet[key] = map[string]string{
				"source":      edge.Source.Name,
				"destination": edge.Destination.Name,
				"edgeType":    string(edge.EdgeType),
			}
		}
	}

	pairs := make([]map[string]string, 0, len(pairSet))
	for _, pair := range pairSet {
		pairs = append(pairs, pair)
	}

	sort.Slice(pairs, func(i, j int) bool {
		if pairs[i]["source"] != pairs[j]["source"] {
			return pairs[i]["source"] < pairs[j]["source"]
		}
		return pairs[i]["destination"] < pairs[j]["destination"]
	})

	return pairs
}

func (ca *CallAnalyzer) GetMethodsForPair(source, dest string) []map[string]interface{} {
	ca.mu.RLock()
	defer ca.mu.RUnlock()

	result := make([]map[string]interface{}, 0)

	for _, edge := range ca.edges {
		if edge.Source.Name == source && edge.Destination.Name == dest {
			result = append(result, map[string]interface{}{
				"method":  edge.Method,
				"path":    edge.Path,
				"count":   edge.Count,
				"sampled": edge.Sampled,
				"edgeType": string(edge.EdgeType),
			})
		}
	}

	sort.Slice(result, func(i, j int) bool {
		mi := result[i]["method"].(string)
		mj := result[j]["method"].(string)
		if mi != mj {
			return mi < mj
		}
		return result[i]["path"].(string) < result[j]["path"].(string)
	})

	return result
}

func (ca *CallAnalyzer) Clear() {
	ca.mu.Lock()
	defer ca.mu.Unlock()
	ca.traces = make(map[string]*models.Trace)
	ca.edges = make(map[string]*models.CallEdge)
}

func (ca *CallAnalyzer) LoadSampleData() {
	ca.Clear()

	ca.SetEdgeServices(
		[]string{"frontend", "api-gateway"},
		[]string{"payment-service", "external-api"},
	)

	now := time.Now()

	sampleTraces := []models.Trace{
		{
			TraceID: "trace-001",
			Spans: []models.Span{
				{
					TraceID:   "trace-001",
					SpanID:    "span-001",
					Service:   "frontend",
					Operation: "GET /api/products",
					Method:    "GET",
					Path:      "/api/products",
					StartTime: now.Add(-10 * time.Minute),
					Duration:  150 * time.Millisecond,
				},
				{
					TraceID:   "trace-001",
					SpanID:    "span-002",
					ParentID:  "span-001",
					Service:   "product-service",
					Operation: "GET /products",
					Method:    "GET",
					Path:      "/products",
					StartTime: now.Add(-10 * time.Minute).Add(10 * time.Millisecond),
					Duration:  100 * time.Millisecond,
				},
				{
					TraceID:   "trace-001",
					SpanID:    "span-003",
					ParentID:  "span-002",
					Service:   "database",
					Operation: "SELECT products",
					Method:    "QUERY",
					Path:      "/db/query",
					StartTime: now.Add(-10 * time.Minute).Add(30 * time.Millisecond),
					Duration:  60 * time.Millisecond,
				},
			},
		},
		{
			TraceID: "trace-002",
			Spans: []models.Span{
				{
					TraceID:   "trace-002",
					SpanID:    "span-004",
					Service:   "frontend",
					Operation: "POST /api/orders",
					Method:    "POST",
					Path:      "/api/orders",
					StartTime: now.Add(-8 * time.Minute),
					Duration:  200 * time.Millisecond,
				},
				{
					TraceID:   "trace-002",
					SpanID:    "span-005",
					ParentID:  "span-004",
					Service:   "order-service",
					Operation: "POST /orders",
					Method:    "POST",
					Path:      "/orders",
					StartTime: now.Add(-8 * time.Minute).Add(15 * time.Millisecond),
					Duration:  150 * time.Millisecond,
				},
				{
					TraceID:   "trace-002",
					SpanID:    "span-006",
					ParentID:  "span-005",
					Service:   "payment-service",
					Operation: "POST /payments",
					Method:    "POST",
					Path:      "/payments",
					StartTime: now.Add(-8 * time.Minute).Add(50 * time.Millisecond),
					Duration:  80 * time.Millisecond,
				},
				{
					TraceID:   "trace-002",
					SpanID:    "span-007",
					ParentID:  "span-005",
					Service:   "database",
					Operation: "INSERT orders",
					Method:    "EXEC",
					Path:      "/db/exec",
					StartTime: now.Add(-8 * time.Minute).Add(60 * time.Millisecond),
					Duration:  40 * time.Millisecond,
				},
			},
		},
		{
			TraceID: "trace-003",
			Spans: []models.Span{
				{
					TraceID:   "trace-003",
					SpanID:    "span-008",
					Service:   "frontend",
					Operation: "GET /api/users/profile",
					Method:    "GET",
					Path:      "/api/users/profile",
					StartTime: now.Add(-5 * time.Minute),
					Duration:  120 * time.Millisecond,
				},
				{
					TraceID:   "trace-003",
					SpanID:    "span-009",
					ParentID:  "span-008",
					Service:   "user-service",
					Operation: "GET /users/profile",
					Method:    "GET",
					Path:      "/users/profile",
					StartTime: now.Add(-5 * time.Minute).Add(8 * time.Millisecond),
					Duration:  80 * time.Millisecond,
				},
				{
					TraceID:   "trace-003",
					SpanID:    "span-010",
					ParentID:  "span-009",
					Service:   "database",
					Operation: "SELECT users",
					Method:    "QUERY",
					Path:      "/db/query",
					StartTime: now.Add(-5 * time.Minute).Add(20 * time.Millisecond),
					Duration:  50 * time.Millisecond,
				},
			},
		},
		{
			TraceID: "trace-004",
			Spans: []models.Span{
				{
					TraceID:   "trace-004",
					SpanID:    "span-011",
					Service:   "order-service",
					Operation: "GET /orders/{id}",
					Method:    "GET",
					Path:      "/orders/123",
					StartTime: now.Add(-3 * time.Minute),
					Duration:  90 * time.Millisecond,
				},
				{
					TraceID:   "trace-004",
					SpanID:    "span-012",
					ParentID:  "span-011",
					Service:   "product-service",
					Operation: "GET /products/{id}",
					Method:    "GET",
					Path:      "/products/456",
					StartTime: now.Add(-3 * time.Minute).Add(10 * time.Millisecond),
					Duration:  50 * time.Millisecond,
				},
			},
		},
		{
			TraceID: "trace-005",
			Spans: []models.Span{
				{
					TraceID:   "trace-005",
					SpanID:    "span-013",
					Service:   "frontend",
					Operation: "PUT /api/users/settings",
					Method:    "PUT",
					Path:      "/api/users/settings",
					StartTime: now.Add(-1 * time.Minute),
					Duration:  180 * time.Millisecond,
				},
				{
					TraceID:   "trace-005",
					SpanID:    "span-014",
					ParentID:  "span-013",
					Service:   "user-service",
					Operation: "PUT /users/settings",
					Method:    "PUT",
					Path:      "/users/settings",
					StartTime: now.Add(-1 * time.Minute).Add(12 * time.Millisecond),
					Duration:  120 * time.Millisecond,
				},
				{
					TraceID:   "trace-005",
					SpanID:    "span-015",
					ParentID:  "span-014",
					Service:   "database",
					Operation: "UPDATE users",
					Method:    "EXEC",
					Path:      "/db/exec",
					StartTime: now.Add(-1 * time.Minute).Add(30 * time.Millisecond),
					Duration:  70 * time.Millisecond,
				},
			},
		},
		{
			TraceID: "trace-006",
			Spans: []models.Span{
				{
					TraceID:   "trace-006",
					SpanID:    "span-016",
					Service:   "payment-service",
					Operation: "POST /external/charge",
					Method:    "POST",
					Path:      "/external/charge",
					StartTime: now.Add(-2 * time.Minute),
					Duration:  300 * time.Millisecond,
				},
				{
					TraceID:   "trace-006",
					SpanID:    "span-017",
					ParentID:  "span-016",
					Service:   "external-payment-gateway",
					Operation: "POST /charge",
					Method:    "POST",
					Path:      "/charge",
					StartTime: now.Add(-2 * time.Minute).Add(20 * time.Millisecond),
					Duration:  250 * time.Millisecond,
				},
			},
		},
	}

	for _, trace := range sampleTraces {
		ca.AddTrace(trace)
	}
}
