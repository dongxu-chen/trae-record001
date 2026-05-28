package probe

import (
	"context"
	"time"
	"health-check/internal/model"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"
)

type GRPCProber struct{}

func NewGRPCProber() *GRPCProber {
	return &GRPCProber{}
}

func (p *GRPCProber) Probe(ctx context.Context, endpoint *model.Endpoint) *model.ProbeResult {
	result := &model.ProbeResult{
		EndpointID: endpoint.ID,
		Name:       endpoint.Name,
		Protocol:   endpoint.Protocol,
		Timestamp:  time.Now(),
		Status:     model.StatusUp,
	}

	cfg := endpoint.GRPCConfig
	if cfg == nil {
		result.Status = model.StatusDown
		result.Error = "grpc config is required"
		return result
	}

	opts := []grpc.DialOption{
		grpc.WithBlock(),
	}

	if cfg.TLS {
		result.Status = model.StatusDown
		result.Error = "TLS not implemented in this version"
		return result
	}
	opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))

	start := time.Now()
	conn, err := grpc.DialContext(ctx, endpoint.Address, opts...)
	result.Latency = time.Since(start)

	if err != nil {
		result.Status = model.StatusDown
		result.Error = "connection failed: " + err.Error()
		return result
	}
	defer conn.Close()

	if cfg.Service == "" || cfg.Method == "" {
		result.Status = model.StatusUp
		return result
	}

	method := "/" + cfg.Service + "/" + cfg.Method

	req := cfg.Request
	if req == "" {
		req = "{}"
	}

	md := metadata.New(cfg.Metadata)
	ctx = metadata.NewOutgoingContext(ctx, md)

	var resp string
	start = time.Now()
	err = conn.Invoke(ctx, method, req, &resp)
	invokeLatency := time.Since(start)
	result.Latency += invokeLatency

	if err != nil {
		st, ok := status.FromError(err)
		if ok {
			result.HTTPStatus = int(st.Code())
			result.Status = model.StatusDown
			result.Error = "rpc error: " + st.Message()
		} else {
			result.Status = model.StatusDown
			result.Error = err.Error()
		}
		return result
	}

	if result.Latency > time.Duration(endpoint.Timeout)*time.Second/2 {
		result.Status = model.StatusDegrade
	}

	return result
}
