package cilium

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math/rand"
	"net/http"
	"sync"
	"time"

	"k8s-network-policy-recommender/pkg/config"
	"k8s-network-policy-recommender/pkg/neo4jclient"
)

type HubbleClient struct {
	config   config.CiliumConfig
	neo4j    *neo4jclient.Client
	sampler  *FlowSampler
}

type FlowSampler struct {
	mu           sync.RWMutex
	sampleRate   float64
	windowSize   time.Duration
	aggregations map[string]*FlowAggregate
	maxEntries   int
	totalSeen    int64
	totalSampled int64
}

type FlowAggregate struct {
	SourceName      string
	SourceNamespace string
	DestName        string
	DestNamespace   string
	Protocol        string
	Port            int32
	TotalCount      int64
	SampleCount     int64
	FirstSeen       time.Time
	LastSeen        time.Time
}

func NewFlowSampler(sampleRate float64, windowSize time.Duration, maxEntries int) *FlowSampler {
	return &FlowSampler{
		sampleRate:   sampleRate,
		windowSize:   windowSize,
		aggregations: make(map[string]*FlowAggregate),
		maxEntries:   maxEntries,
	}
}

func (s *FlowSampler) ShouldSample() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.totalSeen++
	if rand.Float64() <= s.sampleRate {
		s.totalSampled++
		return true
	}
	return false
}

func (s *FlowSampler) Aggregate(flow neo4jclient.FlowEdge) {
	key := fmt.Sprintf("%s/%s->%s/%s|%s:%d",
		flow.SourceNamespace, flow.SourceName,
		flow.DestNamespace, flow.DestName,
		flow.Protocol, flow.Port)

	now := time.Now()

	s.mu.Lock()
	defer s.mu.Unlock()

	if agg, exists := s.aggregations[key]; exists {
		agg.SampleCount += flow.Count
		agg.TotalCount = int64(float64(agg.SampleCount) / s.sampleRate)
		agg.LastSeen = now
	} else {
		if len(s.aggregations) >= s.maxEntries {
			s.evictOldest()
		}
		s.aggregations[key] = &FlowAggregate{
			SourceName:      flow.SourceName,
			SourceNamespace: flow.SourceNamespace,
			DestName:        flow.DestName,
			DestNamespace:   flow.DestNamespace,
			Protocol:        flow.Protocol,
			Port:            flow.Port,
			SampleCount:     flow.Count,
			TotalCount:      int64(float64(flow.Count) / s.sampleRate),
			FirstSeen:       now,
			LastSeen:        now,
		}
	}
}

func (s *FlowSampler) evictOldest() {
	var oldestKey string
	var oldestTime time.Time
	for k, agg := range s.aggregations {
		if oldestKey == "" || agg.LastSeen.Before(oldestTime) {
			oldestKey = k
			oldestTime = agg.LastSeen
		}
	}
	if oldestKey != "" {
		delete(s.aggregations, oldestKey)
	}
}

func (s *FlowSampler) Flush() []neo4jclient.FlowEdge {
	s.mu.Lock()
	defer s.mu.Unlock()

	var flows []neo4jclient.FlowEdge
	for _, agg := range s.aggregations {
		flows = append(flows, neo4jclient.FlowEdge{
			SourceName:      agg.SourceName,
			SourceNamespace: agg.SourceNamespace,
			DestName:        agg.DestName,
			DestNamespace:   agg.DestNamespace,
			Protocol:        agg.Protocol,
			Port:           agg.Port,
			Count:          agg.TotalCount,
			LastSeen:      agg.LastSeen.Format(time.RFC3339),
		})
	}
	s.aggregations = make(map[string]*FlowAggregate)
	return flows
}

func (s *FlowSampler) Stats() SamplerStats {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return SamplerStats{
		SampleRate:     s.sampleRate,
		TotalSeen:      s.totalSeen,
		TotalSampled:   s.totalSampled,
		ActiveEntries:  len(s.aggregations),
		MaxEntries:     s.maxEntries,
		EffectiveRate:  float64(s.totalSampled) / float64(max(s.totalSeen, 1)),
	}
}

type SamplerStats struct {
	SampleRate    float64 `json:"sampleRate"`
	TotalSeen     int64   `json:"totalSeen"`
	TotalSampled  int64   `json:"totalSampled"`
	ActiveEntries int     `json:"activeEntries"`
	MaxEntries    int     `json:"maxEntries"`
	EffectiveRate float64 `json:"effectiveRate"`
}

type HubbleFlow struct {
	Time        time.Time  `json:"time"`
	Source      Endpoint   `json:"source"`
	Destination Endpoint   `json:"destination"`
	Verdict     string     `json:"verdict"`
	DropReason  string     `json:"drop_reason,omitempty"`
	L4          L4Protocol `json:"l4"`
}

type Endpoint struct {
	Namespace string   `json:"namespace"`
	PodName   string   `json:"pod_name"`
	Labels    []string `json:"labels"`
}

type L4Protocol struct {
	Protocol        string `json:"protocol"`
	SourcePort      uint16 `json:"source_port"`
	DestinationPort uint16 `json:"destination_port"`
}

func NewHubbleClient(cfg config.CiliumConfig, neo4j *neo4jclient.Client) *HubbleClient {
	return &HubbleClient{
		config:  cfg,
		neo4j:   neo4j,
		sampler: NewFlowSampler(0.1, 30*time.Second, 10000),
	}
}

func (h *HubbleClient) StartFlowCollector(ctx context.Context) error {
	collectTicker := time.NewTicker(10 * time.Second)
	defer collectTicker.Stop()

	flushTicker := time.NewTicker(h.sampler.windowSize)
	defer flushTicker.Stop()

	go func() {
		for {
			select {
			case <-ctx.Done():
				h.flushToNeo4j(ctx)
				return
			case <-collectTicker.C:
				if err := h.collectFlows(ctx); err != nil {
					fmt.Printf("Error collecting flows: %v\n", err)
				}
			case <-flushTicker.C:
				h.flushToNeo4j(ctx)
			}
		}
	}()

	return nil
}

func (h *HubbleClient) collectFlows(ctx context.Context) error {
	url := fmt.Sprintf("http://%s/api/v1/flows", h.config.HubbleRelay)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return err
	}

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	var flows struct {
		Flows []HubbleFlow `json:"flows"`
	}
	if err := json.Unmarshal(body, &flows); err != nil {
		return err
	}

	for _, flow := range flows.Flows {
		if flow.Verdict != "FORWARDED" {
			continue
		}

		if flow.Source.PodName == "" || flow.Destination.PodName == "" {
			continue
		}

		if !h.sampler.ShouldSample() {
			continue
		}

		neo4jFlow := neo4jclient.FlowEdge{
			SourceName:      flow.Source.PodName,
			SourceNamespace: flow.Source.Namespace,
			DestName:        flow.Destination.PodName,
			DestNamespace:   flow.Destination.Namespace,
			Protocol:        flow.L4.Protocol,
			Port:           int32(flow.L4.DestinationPort),
			LastSeen:      time.Now().Format(time.RFC3339),
			Count:          1,
		}

		h.sampler.Aggregate(neo4jFlow)
	}

	return nil
}

func (h *HubbleClient) flushToNeo4j(ctx context.Context) {
	flows := h.sampler.Flush()
	for _, flow := range flows {
		if err := h.neo4j.AddFlow(ctx, flow); err != nil {
			fmt.Printf("Error flushing flow to Neo4j: %v\n", err)
		}
	}
	if len(flows) > 0 {
		fmt.Printf("Flushed %d aggregated flows to Neo4j\n", len(flows))
	}
}

func (h *HubbleClient) GetSamplerStats() SamplerStats {
	return h.sampler.Stats()
}

func (h *HubbleClient) SetSampleRate(rate float64) {
	h.sampler.mu.Lock()
	defer h.sampler.mu.Unlock()
	h.sampler.sampleRate = rate
}

func (h *HubbleClient) ImportMockFlows(ctx context.Context, flows []neo4jclient.FlowEdge) error {
	for _, flow := range flows {
		if flow.LastSeen == "" {
			flow.LastSeen = time.Now().Format(time.RFC3339)
		}
		if err := h.neo4j.AddFlow(ctx, flow); err != nil {
			return err
		}
	}
	return nil
}

func GenerateMockFlows() []neo4jclient.FlowEdge {
	return []neo4jclient.FlowEdge{
		{
			SourceName:      "frontend-abc123",
			SourceNamespace: "default",
			DestName:        "backend-def456",
			DestNamespace:   "default",
			Protocol:        "TCP",
			Port:           8080,
			Count:          100,
		},
		{
			SourceName:      "backend-def456",
			SourceNamespace: "default",
			DestName:        "database-ghi789",
			DestNamespace:   "default",
			Protocol:        "TCP",
			Port:           5432,
			Count:          75,
		},
		{
			SourceName:      "frontend-abc123",
			SourceNamespace: "default",
			DestName:        "redis-jkl012",
			DestNamespace:   "default",
			Protocol:        "TCP",
			Port:           6379,
			Count:          50,
		},
		{
			SourceName:      "backend-def456",
			SourceNamespace: "default",
			DestName:        "cache-mno345",
			DestNamespace:   "default",
			Protocol:        "UDP",
			Port:           53,
			Count:          200,
		},
		{
			SourceName:      "monitoring-pqr678",
			SourceNamespace: "monitoring",
			DestName:        "backend-def456",
			DestNamespace:   "default",
			Protocol:        "TCP",
			Port:           9090,
			Count:          30,
		},
	}
}
