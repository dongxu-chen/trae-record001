package probe

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
	"health-check/internal/assertion"
	"health-check/internal/model"
	"health-check/internal/ratelimit"
	"health-check/internal/tracing"
)

var globalTracer *tracing.Tracer

func Init(tracer ...*tracing.Tracer) {
	if len(tracer) > 0 {
		globalTracer = tracer[0]
	}
}

type HTTPProber struct {
	client       *http.Client
	assertionEng *assertion.Engine
	rateLimitMgr *ratelimit.Manager
	tracer       *tracing.Tracer
}

func NewHTTPProber(tracer ...*tracing.Tracer) *HTTPProber {
	var t *tracing.Tracer
	if len(tracer) > 0 {
		t = tracer[0]
	}
	return &HTTPProber{
		client: &http.Client{
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				return http.ErrUseLastResponse
			},
		},
		assertionEng: assertion.NewEngine(),
		rateLimitMgr: ratelimit.NewManager(),
		tracer:       t,
	}
}

func (p *HTTPProber) Probe(ctx context.Context, endpoint *model.Endpoint) *model.ProbeResult {
	var spanCtx *tracing.TraceContext
	var tracer *tracing.Tracer

	if p.tracer != nil {
		tracer = p.tracer
	} else if globalTracer != nil {
		tracer = globalTracer
	}

	if tracer != nil && endpoint.Tracing != nil && endpoint.Tracing.Enabled {
		serviceName := endpoint.Tracing.ServiceName
		if serviceName == "" {
			serviceName = endpoint.Name
		}
		spanCtx = tracer.StartSpan(endpoint.ID, "probe", nil)
	}

	result := &model.ProbeResult{
		EndpointID: endpoint.ID,
		Name:       endpoint.Name,
		Protocol:   endpoint.Protocol,
		Timestamp:  time.Now(),
		Status:     model.StatusUp,
	}

	if spanCtx != nil {
		result.TraceID = spanCtx.TraceID
		result.SpanID = spanCtx.SpanID
	}

	if endpoint.RateLimit != nil && endpoint.RateLimit.Enabled {
		limiter := p.rateLimitMgr.GetOrCreate(endpoint.ID, endpoint.RateLimit)
		delay := limiter.Wait()
		if delay > 0 {
			time.Sleep(delay)
		}
		if !limiter.Allow() {
			result.Status = model.StatusDown
			result.Error = "rate limit exceeded"
			if tracer != nil && spanCtx != nil {
				tracer.EndSpan(spanCtx, result.Status, map[string]string{"error": "rate limit exceeded"})
			}
			return result
		}
	}

	cfg := endpoint.HTTPConfig
	if cfg == nil {
		cfg = &model.HTTPConfig{
			Method:       http.MethodGet,
			Path:         "/",
			ExpectedCode: 200,
		}
	}

	method := cfg.Method
	if method == "" {
		method = http.MethodGet
	}

	url := endpoint.Address + cfg.Path

	var body io.Reader
	if cfg.Body != "" {
		body = bytes.NewBufferString(cfg.Body)
	}

	start := time.Now()
	req, err := http.NewRequestWithContext(ctx, method, url, body)
	if err != nil {
		result.Status = model.StatusDown
		result.Error = "failed to create request: " + err.Error()
		if tracer != nil && spanCtx != nil {
			tracer.EndSpan(spanCtx, result.Status, map[string]string{"error": result.Error})
		}
		return result
	}

	for k, v := range cfg.Headers {
		req.Header.Set(k, v)
	}
	if req.Header.Get("Content-Type") == "" && cfg.Body != "" {
		req.Header.Set("Content-Type", "application/json")
	}

	if tracer != nil && spanCtx != nil && endpoint.Tracing != nil {
		traceHeader := endpoint.Tracing.TraceHeader
		if traceHeader == "" {
			traceHeader = "X-Trace-ID"
		}
		req.Header.Set(traceHeader, tracer.GetTraceHeader(spanCtx))
		req.Header.Set("X-Span-ID", spanCtx.SpanID)
	}

	resp, err := p.client.Do(req)
	result.Latency = time.Since(start)

	if err != nil {
		result.Status = model.StatusDown
		result.Error = err.Error()
		if tracer != nil && spanCtx != nil {
			tracer.EndSpan(spanCtx, result.Status, map[string]string{"error": result.Error})
		}
		return result
	}
	defer resp.Body.Close()

	result.HTTPStatus = resp.StatusCode

	bodyBytes, _ := io.ReadAll(resp.Body)
	bodyStr := string(bodyBytes)

	if cfg.ExpectedCode != 0 && resp.StatusCode != cfg.ExpectedCode {
		result.Status = model.StatusDown
		result.Error = "unexpected status code: " + resp.Status
		if tracer != nil && spanCtx != nil {
			tracer.EndSpan(spanCtx, result.Status, map[string]string{"error": result.Error, "http_status": resp.Status})
		}
		return result
	}

	if cfg.ExpectedBody != "" {
		if !strings.Contains(bodyStr, cfg.ExpectedBody) {
			result.Status = model.StatusDown
			result.BodyMatch = false
			result.Error = "body check failed"
			if tracer != nil && spanCtx != nil {
				tracer.EndSpan(spanCtx, result.Status, map[string]string{"error": result.Error})
			}
			return result
		}
		result.BodyMatch = true
	}

	if len(cfg.Assertions) > 0 {
		contentType := resp.Header.Get("Content-Type")
		assertionResults := p.assertionEng.Evaluate(cfg.Assertions, bodyStr, contentType)
		result.Assertions = assertionResults

		for _, ar := range assertionResults {
			if !ar.Passed {
				result.Status = model.StatusDown
				result.Error = "assertion failed: " + ar.Path
				if tracer != nil && spanCtx != nil {
					tracer.EndSpan(spanCtx, result.Status, map[string]string{"error": result.Error, "assertion": ar.Path})
				}
				return result
			}
		}
		result.BodyMatch = true
	}

	if result.Latency > time.Duration(endpoint.Timeout)*time.Second/2 {
		result.Status = model.StatusDegrade
	}

	if tracer != nil && spanCtx != nil {
		tags := map[string]string{
			"http_status": resp.Status,
			"latency_ms":  fmt.Sprintf("%d", result.Latency.Milliseconds()),
		}
		tracer.EndSpan(spanCtx, result.Status, tags)
	}

	return result
}

func Do(ctx context.Context, endpoint *model.Endpoint) *model.ProbeResult {
	switch endpoint.Protocol {
	case model.ProtocolGRPC:
		return NewGRPCProber().Probe(ctx, endpoint)
	case model.ProtocolDubbo:
		return NewDubboProber().Probe(ctx, endpoint)
	default:
		return NewHTTPProber().Probe(ctx, endpoint)
	}
}
