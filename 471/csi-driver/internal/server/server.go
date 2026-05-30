package server

import (
	"context"
	"net"
	"os"
	"strings"

	"github.com/container-storage-interface/spec/lib/go/csi"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"
)

type Server struct {
	endpoint string
	driver   csi.IdentityServer
	controller csi.ControllerServer
	node      csi.NodeServer
	log       *logrus.Logger
	server    *grpc.Server
}

func NewServer(endpoint string, driver csi.IdentityServer, controller csi.ControllerServer, node csi.NodeServer, log *logrus.Logger) *Server {
	return &Server{
		endpoint:   endpoint,
		driver:     driver,
		controller: controller,
		node:       node,
		log:        log,
	}
}

func (s *Server) Start(ctx context.Context) error {
	s.log.Infof("Starting CSI server on endpoint: %s", s.endpoint)

	proto, addr, err := parseEndpoint(s.endpoint)
	if err != nil {
		return err
	}

	if proto == "unix" {
		if err := os.Remove(addr); err != nil && !os.IsNotExist(err) {
			s.log.Warnf("Failed to remove existing socket: %v", err)
		}
	}

	listener, err := net.Listen(proto, addr)
	if err != nil {
		return err
	}

	opts := []grpc.ServerOption{
		grpc.UnaryInterceptor(s.logInterceptor),
	}

	s.server = grpc.NewServer(opts...)

	csi.RegisterIdentityServer(s.server, s.driver)
	csi.RegisterControllerServer(s.server, s.controller)
	csi.RegisterNodeServer(s.server, s.node)

	s.log.Infof("CSI server listening on %s://%s", proto, addr)

	go func() {
		if err := s.server.Serve(listener); err != nil {
			s.log.Errorf("Server error: %v", err)
		}
	}()

	<-ctx.Done()
	s.log.Info("Stopping CSI server")
	s.server.GracefulStop()

	return nil
}

func (s *Server) logInterceptor(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
	s.log.Infof("CSI call: %s", info.FullMethod)
	resp, err := handler(ctx, req)
	if err != nil {
		s.log.Errorf("CSI call error %s: %v", info.FullMethod, err)
	}
	return resp, err
}

func parseEndpoint(endpoint string) (string, string, error) {
	parts := strings.SplitN(endpoint, "://", 2)
	if len(parts) != 2 {
		return "unix", endpoint, nil
	}
	return parts[0], parts[1], nil
}
