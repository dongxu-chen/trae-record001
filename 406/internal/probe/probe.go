package probe

import (
	"context"
	"health-check/internal/model"
	"health-check/internal/tracing"
)

type Prober interface {
	Probe(ctx context.Context, endpoint *model.Endpoint) *model.ProbeResult
}

var (
	httpProber  Prober
	grpcProber Prober
	dubboProber Prober
)

func Init(tracer ...*tracing.Tracer) {
	if len(tracer) > 0 {
		globalTracer = tracer[0]
	}
	httpProber = NewHTTPProber()
	grpcProber = NewGRPCProber()
	dubboProber = NewDubboProber()
}

func Do(ctx context.Context, endpoint *model.Endpoint) *model.ProbeResult {
	switch endpoint.Protocol {
	case model.ProtocolHTTP:
		return httpProber.Probe(ctx, endpoint)
	case model.ProtocolGRPC:
		return grpcProber.Probe(ctx, endpoint)
	case model.ProtocolDubbo:
		return dubboProber.Probe(ctx, endpoint)
	default:
		return &model.ProbeResult{
			EndpointID: endpoint.ID,
			Name:       endpoint.Name,
			Protocol:   endpoint.Protocol,
			Status:     model.StatusDown,
			Error:      "unsupported protocol",
		}
	}
}
