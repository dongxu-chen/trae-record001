package xds

import (
	"context"
	"cross-cloud-lb/pkg/model"
	"fmt"
	"net"
	"sync"

	discoveryv3 "github.com/envoyproxy/go-control-plane/envoy/service/discovery/v3"
	serverv3 "github.com/envoyproxy/go-control-plane/pkg/server/v3"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/keepalive"
)

type GRPCServer struct {
	xdsServer  *XDSServerImpl
	grpcServer *grpc.Server
	port       uint32
	logger     *zap.Logger
	wg         sync.WaitGroup
	running    bool
	mu         sync.Mutex
}

func NewGRPCServer(xdsServer *XDSServerImpl, port uint32, logger *zap.Logger) *GRPCServer {
	grpcServer := grpc.NewServer(
		grpc.KeepaliveParams(keepalive.ServerParameters{
			MaxConnectionIdle: 300,
			Time:              120,
			Timeout:           20,
		}),
	)

	return &GRPCServer{
		xdsServer:  xdsServer,
		grpcServer: grpcServer,
		port:       port,
		logger:     logger,
	}
}

func (s *GRPCServer) Start(ctx context.Context) error {
	s.mu.Lock()
	if s.running {
		s.mu.Unlock()
		return fmt.Errorf("server already running")
	}
	s.running = true
	s.mu.Unlock()

	server := serverv3.NewServer(ctx, s.xdsServer.GetSnapshotCache(), &Callbacks{logger: s.logger})

	discoveryv3.RegisterAggregatedDiscoveryServiceServer(s.grpcServer, server)

	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", s.port))
	if err != nil {
		return fmt.Errorf("failed to listen: %w", err)
	}

	s.logger.Info("Starting xDS gRPC server", zap.Uint32("port", s.port))

	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		if err := s.grpcServer.Serve(lis); err != nil {
			s.logger.Error("gRPC server error", zap.Error(err))
		}
	}()

	return nil
}

func (s *GRPCServer) Stop() {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.running {
		return
	}

	s.logger.Info("Stopping xDS gRPC server")
	s.grpcServer.GracefulStop()
	s.wg.Wait()
	s.running = false
}

type Callbacks struct {
	logger *zap.Logger
}

func (cb *Callbacks) OnStreamOpen(ctx context.Context, id int64, typ string) error {
	cb.logger.Debug("Stream opened", zap.Int64("id", id), zap.String("type", typ))
	return nil
}

func (cb *Callbacks) OnStreamClosed(id int64, node *model.Cluster) {
	cb.logger.Debug("Stream closed", zap.Int64("id", id))
}

func (cb *Callbacks) OnStreamRequest(id int64, req *discoveryv3.DiscoveryRequest) error {
	cb.logger.Debug("Stream request",
		zap.Int64("id", id),
		zap.String("type_url", req.GetTypeUrl()),
		zap.String("node", req.GetNode().GetId()))
	return nil
}

func (cb *Callbacks) OnStreamResponse(ctx context.Context, id int64, req *discoveryv3.DiscoveryRequest, resp *discoveryv3.DiscoveryResponse) {
	cb.logger.Debug("Stream response",
		zap.Int64("id", id),
		zap.String("type_url", resp.GetTypeUrl()),
		zap.Int("resource_count", len(resp.GetResources())))
}

func (cb *Callbacks) OnFetchRequest(ctx context.Context, req *discoveryv3.DiscoveryRequest) error {
	cb.logger.Debug("Fetch request",
		zap.String("type_url", req.GetTypeUrl()),
		zap.String("node", req.GetNode().GetId()))
	return nil
}

func (cb *Callbacks) OnFetchResponse(req *discoveryv3.DiscoveryRequest, resp *discoveryv3.DiscoveryResponse) {
	cb.logger.Debug("Fetch response",
		zap.String("type_url", resp.GetTypeUrl()),
		zap.Int("resource_count", len(resp.GetResources())))
}
