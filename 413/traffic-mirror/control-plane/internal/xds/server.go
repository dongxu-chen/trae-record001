package xds

import (
	"context"
	"fmt"
	"log"
	"sync"

	discovery "github.com/envoyproxy/go-control-plane/envoy/service/discovery/v3"
	"github.com/envoyproxy/go-control-plane/pkg/cache/v3"
	"github.com/envoyproxy/go-control-plane/pkg/resource/v3"
	"github.com/envoyproxy/go-control-plane/pkg/server/v3"
	"google.golang.org/grpc"

	corev3 "github.com/envoyproxy/go-control-plane/envoy/config/core/v3"
	listenerv3 "github.com/envoyproxy/go-control-plane/envoy/config/listener/v3"
	routev3 "github.com/envoyproxy/go-control-plane/envoy/config/route/v3"
	clusterv3 "github.com/envoyproxy/go-control-plane/envoy/config/cluster/v3"
	endpointv3 "github.com/envoyproxy/go-control-plane/envoy/config/endpoint/v3"
	hcmv3 "github.com/envoyproxy/go-control-plane/envoy/extensions/filters/network/http_connection_manager/v3"
	wasmv3 "github.com/envoyproxy/go-control-plane/envoy/extensions/filters/http/wasm/v3"
	wasmcfgv3 "github.com/envoyproxy/go-control-plane/envoy/extensions/wasm/v3"
)

type XDSServer struct {
	mu          sync.RWMutex
	cache       cache.SnapshotCache
	nodeID      string
	version     int64
	listeners   []*listenerv3.Listener
	routes      []*routev3.RouteConfiguration
	clusters    []*clusterv3.Cluster
	endpoints   []*endpointv3.ClusterLoadAssignment
	prodPort    uint32
	testPort    uint32
	prodHost    string
	testHost    string
	wasmPlugin  string
}

func NewXDSServer(nodeID string, prodHost string, prodPort uint32, testHost string, testPort uint32, wasmPlugin string) *XDSServer {
	snapshotCache := cache.NewSnapshotCache(false, cache.IDHash{}, nil)

	return &XDSServer{
		cache:      snapshotCache,
		nodeID:     nodeID,
		prodHost:   prodHost,
		prodPort:   prodPort,
		testHost:   testHost,
		testPort:   testPort,
		wasmPlugin: wasmPlugin,
	}
}

func (s *XDSServer) RegisterGRPC(grpcServer *grpc.Server) {
	srv := server.NewServer(context.Background(), s.cache, nil)
	discovery.RegisterAggregatedDiscoveryServiceServer(grpcServer, srv)
}

func (s *XDSServer) UpdateConfig(wasmConfigJSON string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.version++
	version := fmt.Sprintf("v%d", s.version)

	listener := s.buildListener(wasmConfigJSON)
	routeConfig := s.buildRouteConfig()
	cluster := s.buildCluster()
	endpoint := s.buildEndpoint()

	s.listeners = []*listenerv3.Listener{listener}
	s.routes = []*routev3.RouteConfiguration{routeConfig}
	s.clusters = []*clusterv3.Cluster{cluster}
	s.endpoints = []*endpointv3.ClusterLoadAssignment{endpoint}

	resources := cache.NewResources(
		version,
		[]resource.Resource{
			listener,
			routeConfig,
			cluster,
			endpoint,
		},
	)

	snapshot := cache.NewSnapshot(version, resources)
	if err := snapshot.Consistent(); err != nil {
		return fmt.Errorf("snapshot inconsistent: %w", err)
	}

	return s.cache.SetSnapshot(s.nodeID, snapshot)
}

func (s *XDSServer) buildListener(wasmConfigJSON string) *listenerv3.Listener {
	wasmFilter := &wasmv3.Wasm{
		Config: &wasmcfgv3.PluginConfig{
			Name: "traffic_mirror",
			VmConfig: &wasmcfgv3.PluginVmConfig{
				VmId: "traffic_mirror_vm",
				Runtime: "envoy.wasm.runtime.v8",
				Code: &corev3.AsyncDataSource{
					Specifier: &corev3.AsyncDataSource_Local{
						Local: &corev3.DataSource{
							Specifier: &corev3.DataSource_Filename{
								Filename: s.wasmPlugin,
							},
						},
					},
				},
				Configuration: &corev3.DataSource{
					Specifier: &corev3.DataSource_InlineString{
						InlineString: wasmConfigJSON,
					},
				},
			},
		},
	}

	hcm := &hcmv3.HttpConnectionManager{
		CodecType:  hcmv3.HttpConnectionManager_AUTO,
		StatPrefix: "ingress_http",
		RouteSpecifier: &hcmv3.HttpConnectionManager_Rds{
			Rds: &hcmv3.Rds{
				RouteConfigName: "local_route",
				ConfigSource: &corev3.ConfigSource{
					ResourceApiVersion: corev3.ApiVersion_V3,
					ConfigSourceSpecifier: &corev3.ConfigSource_Ads{
						Ads: &corev3.AggregatedConfigSource{},
					},
				},
			},
		},
		HttpFilters: []*hcmv3.HttpFilter{
			{
				Name: "envoy.filters.http.wasm",
				ConfigType: &hcmv3.HttpFilter_TypedConfig{
					TypedConfig: mustAny(wasmFilter),
				},
			},
			{
				Name: "envoy.filters.http.router",
			},
		},
	}

	return &listenerv3.Listener{
		Name: "listener_0",
		Address: &corev3.Address{
			Address: &corev3.Address_SocketAddress{
				SocketAddress: &corev3.SocketAddress{
					Protocol: corev3.SocketAddress_TCP,
					Address:  "0.0.0.0",
					PortSpecifier: &corev3.SocketAddress_PortValue{
						PortValue: 10000,
					},
				},
			},
		},
		FilterChains: []*listenerv3.FilterChain{
			{
				Filters: []*listenerv3.Filter{
					{
						Name: "envoy.filters.network.http_connection_manager",
						ConfigType: &listenerv3.Filter_TypedConfig{
							TypedConfig: mustAny(hcm),
						},
					},
				},
			},
		},
	}
}

func (s *XDSServer) buildRouteConfig() *routev3.RouteConfiguration {
	return &routev3.RouteConfiguration{
		Name: "local_route",
		VirtualHosts: []*routev3.VirtualHost{
			{
				Name:    "all",
				Domains: []string{"*"},
				Routes: []*routev3.Route{
					{
						Match: &routev3.RouteMatch{
							PathSpecifier: &routev3.RouteMatch_Prefix{
								Prefix: "/",
							},
						},
						Action: &routev3.Route_Route{
							Route: &routev3.RouteAction{
								ClusterSpecifier: &routev3.RouteAction_Cluster{
									Cluster: "production_service",
								},
							},
						},
					},
				},
			},
		},
	}
}

func (s *XDSServer) buildCluster() *clusterv3.Cluster {
	return &clusterv3.Cluster{
		Name: "production_service",
		ClusterDiscoveryType: &clusterv3.Cluster_Type{
			Type: clusterv3.Cluster_STRICT_DNS,
		},
		ConnectTimeout: &durationProto(5),
		LoadAssignment: &endpointv3.ClusterLoadAssignment{
			ClusterName: "production_service",
			Endpoints: []*endpointv3.LocalityLbEndpoints{
				{
					LbEndpoints: []*endpointv3.LbEndpoint{
						{
							HostIdentifier: &endpointv3.LbEndpoint_Endpoint{
								Endpoint: &endpointv3.Endpoint{
									Address: &corev3.Address{
										Address: &corev3.Address_SocketAddress{
											SocketAddress: &corev3.SocketAddress{
												Protocol: corev3.SocketAddress_TCP,
												Address:  s.prodHost,
												PortSpecifier: &corev3.SocketAddress_PortValue{
													PortValue: s.prodPort,
												},
											},
										},
									},
								},
							},
						},
					},
				},
			},
		},
	}
}

func (s *XDSServer) buildEndpoint() *endpointv3.ClusterLoadAssignment {
	return &endpointv3.ClusterLoadAssignment{
		ClusterName: "production_service",
		Endpoints: []*endpointv3.LocalityLbEndpoints{
			{
				LbEndpoints: []*endpointv3.LbEndpoint{
					{
						HostIdentifier: &endpointv3.LbEndpoint_Endpoint{
							Endpoint: &endpointv3.Endpoint{
								Address: &corev3.Address{
									Address: &corev3.Address_SocketAddress{
										SocketAddress: &corev3.SocketAddress{
											Protocol: corev3.SocketAddress_TCP,
											Address:  s.prodHost,
											PortSpecifier: &corev3.SocketAddress_PortValue{
												PortValue: s.prodPort,
											},
										},
									},
								},
							},
						},
					},
				},
			},
		},
	}
}

func (s *XDSServer) RunDiscoveryServer() {
	log.Println("xDS discovery server ready")
}
