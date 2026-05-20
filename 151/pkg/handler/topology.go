package handler

import (
	"context"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"go.opentelemetry.io/otel/attribute"
	"servicemesh-console/pkg/tracing"
)

var (
	trafficDataMap = make(map[string]*TrafficMetrics)
	trafficDataMu  sync.RWMutex
)

type TrafficMetrics struct {
	RequestCount    int64
	ErrorCount      int64
	TotalLatency    int64
	MinLatency      int64
	MaxLatency      int64
	LastRequestTime time.Time
	LatencyBuckets  []int64
}

type EdgeMetrics struct {
	Source       string
	Destination  string
	RequestRate  float64
	ErrorRate    float64
	AvgLatency   float64
	P50Latency   float64
	P95Latency   float64
	TrafficType  string
}

func (h *Handlers) GetTrafficTopology(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetTrafficTopology")
	defer span.End()

	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}
	service := c.Query("service")
	timeRange := c.Query("time_range")
	if timeRange == "" {
		timeRange = "5m"
	}

	tracing.AddSpanAttributes(span,
		attribute.String("namespace", namespace),
		attribute.String("service", service),
		attribute.String("time_range", timeRange),
	)

	nodes, edges := h.generateTopologyData(namespace, service)

	response := TrafficTopologyResponse{
		Nodes:    nodes,
		Edges:    edges,
		Metadata: TopologyMeta{
			GeneratedAt: time.Now().Format(time.RFC3339),
			TimeRange:   timeRange,
			NodeCount:   len(nodes),
			EdgeCount:   len(edges),
		},
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Traffic topology retrieved successfully",
		Data:    response,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) generateTopologyData(namespace, service string) ([]TopologyNode, []TopologyEdge) {
	trafficDataMu.RLock()
	defer trafficDataMu.RUnlock()

	nodeMap := make(map[string]*TopologyNode)
	edgeMap := make(map[string]*TopologyEdge)

	for key, metrics := range trafficDataMap {
		parts := splitKey(key)
		if len(parts) < 2 {
			continue
		}

		sourceSvc := parts[0]
		destSvc := parts[1]

		if service != "" && sourceSvc != service && destSvc != service {
			continue
		}

		if _, exists := nodeMap[sourceSvc]; !exists {
			nodeMap[sourceSvc] = &TopologyNode{
				ID:           sourceSvc,
				Name:         sourceSvc,
				Type:         "service",
				Service:      sourceSvc,
				Namespace:    namespace,
				HealthStatus: "healthy",
			}
		}

		if _, exists := nodeMap[destSvc]; !exists {
			nodeMap[destSvc] = &TopologyNode{
				ID:           destSvc,
				Name:         destSvc,
				Type:         "service",
				Service:      destSvc,
				Namespace:    namespace,
				HealthStatus: "healthy",
			}
		}

		edgeKey := sourceSvc + "->" + destSvc
		if _, exists := edgeMap[edgeKey]; !exists {
			edgeMap[edgeKey] = &TopologyEdge{
				Source:      sourceSvc,
				Target:      destSvc,
				TrafficType: "http",
			}
		}

		nodeMap[sourceSvc].RequestRate += float64(metrics.RequestCount) / 300.0
		nodeMap[destSvc].RequestRate += float64(metrics.RequestCount) / 300.0

		if metrics.RequestCount > 0 {
			errorRate := float64(metrics.ErrorCount) / float64(metrics.RequestCount)
			nodeMap[destSvc].ErrorRate = errorRate
			edgeMap[edgeKey].ErrorRate = errorRate

			if errorRate > 0.1 {
				nodeMap[destSvc].HealthStatus = "degraded"
			}
			if errorRate > 0.3 {
				nodeMap[destSvc].HealthStatus = "unhealthy"
			}
		}

		if metrics.RequestCount > 0 {
			avgLatency := float64(metrics.TotalLatency) / float64(metrics.RequestCount)
			nodeMap[destSvc].LatencyP50 = avgLatency
			nodeMap[destSvc].LatencyP95 = float64(metrics.MaxLatency)
			edgeMap[edgeKey].LatencyP50 = avgLatency
		}

		edgeMap[edgeKey].RequestRate = float64(metrics.RequestCount) / 300.0
	}

	nodes := make([]TopologyNode, 0, len(nodeMap))
	for _, node := range nodeMap {
		nodes = append(nodes, *node)
	}

	edges := make([]TopologyEdge, 0, len(edgeMap))
	for _, edge := range edgeMap {
		edges = append(edges, *edge)
	}

	return nodes, edges
}

func splitKey(key string) []string {
	var parts []string
	current := ""
	for _, char := range key {
		if char == '/' || char == '-' {
			if current != "" {
				parts = append(parts, current)
				current = ""
			}
		} else {
			current += string(char)
		}
	}
	if current != "" {
		parts = append(parts, current)
	}
	return parts
}

func (h *Handlers) GetServiceMetrics(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "GetServiceMetrics")
	defer span.End()

	serviceName := c.Param("service")
	namespace := c.Query("namespace")
	if namespace == "" {
		namespace = h.namespace
	}

	trafficDataMu.RLock()
	defer trafficDataMu.RUnlock()

	metricsMap := make(map[string]interface{})
	for key, metrics := range trafficDataMap {
		if len(key) > len(serviceName) && key[:len(serviceName)] == serviceName {
			var requestRate float64
			if metrics.RequestCount > 0 {
				requestRate = float64(metrics.RequestCount) / 300.0
			}

			var errorRate float64
			if metrics.RequestCount > 0 {
				errorRate = float64(metrics.ErrorCount) / float64(metrics.RequestCount)
			}

			var avgLatency float64
			if metrics.RequestCount > 0 {
				avgLatency = float64(metrics.TotalLatency) / float64(metrics.RequestCount)
			}

			metricsMap[key] = map[string]interface{}{
				"request_count":   metrics.RequestCount,
				"error_count":     metrics.ErrorCount,
				"request_rate":    requestRate,
				"error_rate":      errorRate,
				"avg_latency_ms":  avgLatency,
				"min_latency_ms":  metrics.MinLatency,
				"max_latency_ms":  metrics.MaxLatency,
				"last_request_at": metrics.LastRequestTime,
			}
		}
	}

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Service metrics retrieved successfully",
		Data:    metricsMap,
		TraceID: tracing.GetTraceID(ctx),
	})
}

func (h *Handlers) RecordTrafficData(c *gin.Context) {
	startTime := time.Now()

	c.Next()

	duration := time.Since(startTime).Milliseconds()
	statusCode := c.Writer.Status()

	sourceService := c.GetHeader("X-Source-Service")
	if sourceService == "" {
		sourceService = "unknown"
	}

	destService := c.Request.Host
	if idx := stringIndexOf(destService, ":"); idx != -1 {
		destService = destService[:idx]
	}

	key := sourceService + "/" + destService

	trafficDataMu.Lock()
	defer trafficDataMu.Unlock()

	if _, exists := trafficDataMap[key]; !exists {
		trafficDataMap[key] = &TrafficMetrics{
			MinLatency: 1000000,
		}
	}

	metrics := trafficDataMap[key]
	metrics.RequestCount++
	metrics.TotalLatency += duration
	metrics.LastRequestTime = time.Now()

	if duration < metrics.MinLatency {
		metrics.MinLatency = duration
	}
	if duration > metrics.MaxLatency {
		metrics.MaxLatency = duration
	}

	if statusCode >= 500 {
		metrics.ErrorCount++
	}
}

func stringIndexOf(s string, char byte) int {
	for i := 0; i < len(s); i++ {
		if s[i] == char {
			return i
		}
	}
	return -1
}

func (h *Handlers) ClearTrafficData(c *gin.Context) {
	ctx, span := tracing.StartSpan(c.Request.Context(), "ClearTrafficData")
	defer span.End()

	trafficDataMu.Lock()
	trafficDataMap = make(map[string]*TrafficMetrics)
	trafficDataMu.Unlock()

	c.JSON(http.StatusOK, ApiResponse{
		Success: true,
		Message: "Traffic data cleared successfully",
		TraceID: tracing.GetTraceID(ctx),
	})
}

func TrafficRecordingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		startTime := time.Now()

		c.Next()

		duration := time.Since(startTime).Milliseconds()
		statusCode := c.Writer.Status()

		sourceService := c.GetHeader("X-Source-Service")
		if sourceService == "" {
			sourceService = "client"
		}

		destService := c.Request.Host
		if idx := stringIndexOf(destService, ":"); idx != -1 {
			destService = destService[:idx]
		}

		key := sourceService + "/" + destService

		trafficDataMu.Lock()
		defer trafficDataMu.Unlock()

		if _, exists := trafficDataMap[key]; !exists {
			trafficDataMap[key] = &TrafficMetrics{
				MinLatency: 1000000,
			}
		}

		metrics := trafficDataMap[key]
		metrics.RequestCount++
		metrics.TotalLatency += duration
		metrics.LastRequestTime = time.Now()

		if duration < metrics.MinLatency {
			metrics.MinLatency = duration
		}
		if duration > metrics.MaxLatency {
			metrics.MaxLatency = duration
		}

		if statusCode >= 500 {
			metrics.ErrorCount++
		}
	}
}
