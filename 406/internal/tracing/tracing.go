package tracing

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sync"
	"time"
	"health-check/internal/config"
	"health-check/internal/model"
)

type Tracer struct {
	cfg        *config.TracingConfig
	spans      map[string][]*model.TraceSpan
	traceIndex map[string]string
	mu         sync.RWMutex
}

type TraceContext struct {
	TraceID      string
	SpanID       string
	ParentSpanID string
	ServiceName  string
}

func NewTracer(cfg *config.TracingConfig) *Tracer {
	return &Tracer{
		cfg:        cfg,
		spans:      make(map[string][]*model.TraceSpan),
		traceIndex: make(map[string]string),
	}
}

func GenerateTraceID() string {
	b := make([]byte, 16)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func GenerateSpanID() string {
	b := make([]byte, 8)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func (t *Tracer) StartSpan(endpointID, operation string, parentCtx ...*TraceContext) *TraceContext {
	if !t.cfg.Enabled {
		return &TraceContext{
			TraceID:     GenerateTraceID(),
			SpanID:      GenerateSpanID(),
			ServiceName: "health-check",
		}
	}

	var traceID, parentSpanID string
	var serviceName string

	if len(parentCtx) > 0 && parentCtx[0] != nil {
		traceID = parentCtx[0].TraceID
		parentSpanID = parentCtx[0].SpanID
		serviceName = parentCtx[0].ServiceName
	}

	if traceID == "" {
		traceID = GenerateTraceID()
	}

	spanID := GenerateSpanID()

	if serviceName == "" {
		serviceName = "health-check"
	}

	span := &model.TraceSpan{
		TraceID:      traceID,
		SpanID:       spanID,
		ParentSpanID: parentSpanID,
		ServiceName:  serviceName,
		Operation:    operation,
		EndpointID:   endpointID,
		StartTime:    time.Now(),
		Tags:         make(map[string]string),
	}

	t.mu.Lock()
	t.spans[traceID] = append(t.spans[traceID], span)
	t.traceIndex[spanID] = traceID
	t.mu.Unlock()

	return &TraceContext{
		TraceID:      traceID,
		SpanID:       spanID,
		ParentSpanID: parentSpanID,
		ServiceName:  serviceName,
	}
}

func (t *Tracer) EndSpan(ctx *TraceContext, status model.Status, tags map[string]string) {
	if !t.cfg.Enabled || ctx == nil {
		return
	}

	t.mu.Lock()
	defer t.mu.Unlock()

	spans, ok := t.spans[ctx.TraceID]
	if !ok {
		return
	}

	for _, span := range spans {
		if span.SpanID == ctx.SpanID {
			span.EndTime = time.Now()
			span.Latency = span.EndTime.Sub(span.StartTime)
			span.Status = status
			if tags != nil {
				for k, v := range tags {
					span.Tags[k] = v
				}
			}
			break
		}
	}
}

func (t *Tracer) AddTag(spanID, key, value string) {
	if !t.cfg.Enabled {
		return
	}

	t.mu.Lock()
	defer t.mu.Unlock()

	traceID, ok := t.traceIndex[spanID]
	if !ok {
		return
	}

	spans := t.spans[traceID]
	for _, span := range spans {
		if span.SpanID == spanID {
			span.Tags[key] = value
			break
		}
	}
}

func (t *Tracer) GetTrace(traceID string) []*model.TraceSpan {
	t.mu.RLock()
	defer t.mu.RUnlock()

	spans, ok := t.spans[traceID]
	if !ok {
		return nil
	}

	result := make([]*model.TraceSpan, len(spans))
	copy(result, spans)
	return result
}

func (t *Tracer) GetTraceTree(traceID string) []*model.TraceSpan {
	spans := t.GetTrace(traceID)
	if spans == nil {
		return nil
	}

	spanMap := make(map[string]*model.TraceSpan)
	for _, span := range spans {
		spanMap[span.SpanID] = span
	}

	var roots []*model.TraceSpan
	for _, span := range spans {
		if span.ParentSpanID == "" {
			roots = append(roots, span)
		} else if parent, ok := spanMap[span.ParentSpanID]; ok {
			parent.Children = append(parent.Children, span)
		} else {
			roots = append(roots, span)
		}
	}

	return roots
}

func (t *Tracer) GetSpansByEndpoint(endpointID string, limit int) []*model.TraceSpan {
	t.mu.RLock()
	defer t.mu.RUnlock()

	var result []*model.TraceSpan
	for _, spans := range t.spans {
		for _, span := range spans {
			if span.EndpointID == endpointID {
				result = append(result, span)
				if limit > 0 && len(result) >= limit {
					return result
				}
			}
		}
	}

	return result
}

func (t *Tracer) GetRecentSpans(limit int) []*model.TraceSpan {
	t.mu.RLock()
	defer t.mu.RUnlock()

	var allSpans []*model.TraceSpan
	for _, spans := range t.spans {
		allSpans = append(allSpans, spans...)
	}

	for i := len(allSpans) - 1; i > 0; i-- {
		for j := 0; j < i; j++ {
			if allSpans[j].StartTime.Before(allSpans[j+1].StartTime) {
				allSpans[j], allSpans[j+1] = allSpans[j+1], allSpans[j]
			}
		}
	}

	if limit > 0 && len(allSpans) > limit {
		allSpans = allSpans[:limit]
	}

	return allSpans
}

func (t *Tracer) CleanupOldSpans(maxAge time.Duration) {
	t.mu.Lock()
	defer t.mu.Unlock()

	cutoff := time.Now().Add(-maxAge)

	for traceID, spans := range t.spans {
		var newSpans []*model.TraceSpan
		for _, span := range spans {
			if span.EndTime.After(cutoff) || span.StartTime.After(cutoff) {
				newSpans = append(newSpans, span)
			} else {
				delete(t.traceIndex, span.SpanID)
			}
		}
		if len(newSpans) > 0 {
			t.spans[traceID] = newSpans
		} else {
			delete(t.spans, traceID)
		}
	}
}

func (t *Tracer) GetTraceCount() int {
	t.mu.RLock()
	defer t.mu.RUnlock()

	return len(t.spans)
}

func (t *Tracer) GetSpanCount() int {
	t.mu.RLock()
	defer t.mu.RUnlock()

	count := 0
	for _, spans := range t.spans {
		count += len(spans)
	}
	return count
}

func (t *Tracer) BuildDependencyChain(endpointID string, depth int) []string {
	t.mu.RLock()
	defer t.mu.RUnlock()

	visited := make(map[string]bool)
	chain := []string{endpointID}

	if depth <= 0 {
		return chain
	}

	queue := []string{endpointID}
	visited[endpointID] = true

	currentDepth := 0
	for len(queue) > 0 && currentDepth < depth {
		levelSize := len(queue)
		for i := 0; i < levelSize; i++ {
			current := queue[i]
			deps := t.findDependencies(current)
			for _, dep := range deps {
				if !visited[dep] {
					visited[dep] = true
					chain = append(chain, dep)
					queue = append(queue, dep)
				}
			}
		}
		queue = queue[levelSize:]
		currentDepth++
	}

	return chain
}

func (t *Tracer) findDependencies(endpointID string) []string {
	var deps []string
	for _, spans := range t.spans {
		for _, span := range spans {
			if span.EndpointID == endpointID {
				if span.ParentSpanID != "" {
					if parentTraceID, ok := t.traceIndex[span.ParentSpanID]; ok {
						if parentSpans, ok := t.spans[parentTraceID]; ok {
							for _, parentSpan := range parentSpans {
								if parentSpan.SpanID == span.ParentSpanID && parentSpan.EndpointID != endpointID {
									deps = append(deps, parentSpan.EndpointID)
								}
							}
						}
					}
				}
			}
		}
	}

	return uniqueStrings(deps)
}

func uniqueStrings(s []string) []string {
	seen := make(map[string]bool)
	var result []string
	for _, str := range s {
		if !seen[str] {
			seen[str] = true
			result = append(result, str)
		}
	}
	return result
}

func (t *Tracer) GetTraceHeader(ctx *TraceContext) string {
	if ctx == nil {
		return ""
	}
	return fmt.Sprintf("%s-%s", ctx.TraceID, ctx.SpanID)
}

func (t *Tracer) ParseTraceHeader(header string) *TraceContext {
	if header == "" {
		return nil
	}

	var traceID, spanID string
	_, err := fmt.Sscanf(header, "%s-%s", &traceID, &spanID)
	if err != nil {
		return nil
	}

	return &TraceContext{
		TraceID: traceID,
		SpanID:  spanID,
	}
}

func (t *Tracer) GetHTTPHeaders(ctx *TraceContext) map[string]string {
	if !t.cfg.Enabled || ctx == nil {
		return nil
	}

	return map[string]string{
		t.cfg.TraceHeader: t.GetTraceHeader(ctx),
		"X-Span-ID":       ctx.SpanID,
		"X-Parent-Span-ID": ctx.ParentSpanID,
	}
}

func (t *Tracer) RecordProbeResult(result *model.ProbeResult, ctx *TraceContext) {
	if ctx == nil {
		return
	}

	tags := map[string]string{
		"http.status": fmt.Sprintf("%d", result.HTTPStatus),
		"protocol":    string(result.Protocol),
		"endpoint":    result.Name,
	}
	if result.Error != "" {
		tags["error"] = result.Error
	}

	t.EndSpan(ctx, result.Status, tags)
}
