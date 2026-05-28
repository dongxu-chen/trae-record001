package xds

import (
	"context"
	"cross-cloud-lb/pkg/model"
	"fmt"
	"sync"

	clusterv3 "github.com/envoyproxy/go-control-plane/envoy/config/cluster/v3"
	corev3 "github.com/envoyproxy/go-control-plane/envoy/config/core/v3"
	endpointv3 "github.com/envoyproxy/go-control-plane/envoy/config/endpoint/v3"
	listenerv3 "github.com/envoyproxy/go-control-plane/envoy/config/listener/v3"
	routev3 "github.com/envoyproxy/go-control-plane/envoy/config/route/v3"
	routerv3 "github.com/envoyproxy/go-control-plane/envoy/extensions/filters/http/router/v3"
	hcmv3 "github.com/envoyproxy/go-control-plane/envoy/extensions/filters/network/http_connection_manager/v3"
	"github.com/envoyproxy/go-control-plane/pkg/cache/types"
	"github.com/envoyproxy/go-control-plane/pkg/cache/v3"
	"github.com/envoyproxy/go-control-plane/pkg/resource/v3"
	"github.com/envoyproxy/go-control-plane/pkg/server/v3"
	"go.uber.org/zap"
	"google.golang.org/protobuf/types/known/anypb"
	"google.golang.org/protobuf/types/known/durationpb"
	"google.golang.org/protobuf/types/known/wrapperspb"
)

type XDSServer interface {
	Start(ctx context.Context) error
	Stop()
	UpdateClusters(clusters []*model.Cluster)
	UpdateBackends(clusterID string, backends []*model.Backend)
	UpdateWeights(weights map[string]int)
	GetSnapshotCache() cache.SnapshotCache
}

type XDSServerImpl struct {
	config       model.LoadBalancerConfig
	snapshotCache cache.SnapshotCache
	xdsServer    server.Server
	clusters     map[string]*model.Cluster
	backends     map[string][]*model.Backend
	weights      map[string]int
	mu           sync.RWMutex
	logger       *zap.Logger
	version      int64
	nodeID       string
}

func NewXDSServer(config model.LoadBalancerConfig, logger *zap.Logger, nodeID string) (*XDSServerImpl, error) {
	snapshotCache := cache.NewSnapshotCache(false, cache.IDHash{}, logger.Sugar())

	return &XDSServerImpl{
		config:        config,
		snapshotCache: snapshotCache,
		clusters:      make(map[string]*model.Cluster),
		backends:      make(map[string][]*model.Backend),
		weights:       make(map[string]int),
		logger:        logger,
		nodeID:        nodeID,
	}, nil
}

func (x *XDSServerImpl) Start(ctx context.Context) error {
	x.logger.Info("Starting xDS control plane server")
	return nil
}

func (x *XDSServerImpl) Stop() {
	x.logger.Info("Stopping xDS control plane server")
}

func (x *XDSServerImpl) UpdateClusters(clusters []*model.Cluster) {
	x.mu.Lock()
	defer x.mu.Unlock()

	for _, cluster := range clusters {
		x.clusters[cluster.ID] = cluster
		if _, exists := x.weights[cluster.ID]; !exists {
			x.weights[cluster.ID] = cluster.Weight
		}
	}

	x.generateSnapshot()
}

func (x *XDSServerImpl) UpdateBackends(clusterID string, backends []*model.Backend) {
	x.mu.Lock()
	defer x.mu.Unlock()

	x.backends[clusterID] = backends
	x.generateSnapshot()
}

func (x *XDSServerImpl) UpdateWeights(weights map[string]int) {
	x.mu.Lock()
	defer x.mu.Unlock()

	for clusterID, weight := range weights {
		x.weights[clusterID] = weight
	}

	x.generateSnapshot()
}

func (x *XDSServerImpl) GetSnapshotCache() cache.SnapshotCache {
	return x.snapshotCache
}

func (x *XDSServerImpl) generateSnapshot() {
	x.version++
	version := fmt.Sprintf("%d", x.version)

	resources := make(map[resource.Type][]types.Resource)

	clusters := x.generateEnvoyClusters()
	resources[resource.ClusterType] = make([]types.Resource, len(clusters))
	for i, c := range clusters {
		resources[resource.ClusterType][i] = c
	}

	endpoints := x.generateEnvoyEndpoints()
	resources[resource.EndpointType] = make([]types.Resource, len(endpoints))
	for i, e := range endpoints {
		resources[resource.EndpointType][i] = e
	}

	listeners := x.generateEnvoyListeners()
	resources[resource.ListenerType] = make([]types.Resource, len(listeners))
	for i, l := range listeners {
		resources[resource.ListenerType][i] = l
	}

	routes := x.generateEnvoyRoutes()
	resources[resource.RouteType] = make([]types.Resource, len(routes))
	for i, r := range routes {
		resources[resource.RouteType][i] = r
	}

	snapshot, err := cache.NewSnapshot(version, resources)
	if err != nil {
		x.logger.Error("Failed to create snapshot", zap.Error(err))
		return
	}

	if err := snapshot.Consistent(); err != nil {
		x.logger.Error("Snapshot inconsistent", zap.Error(err))
		return
	}

	if err := x.snapshotCache.SetSnapshot(context.Background(), x.nodeID, snapshot); err != nil {
		x.logger.Error("Failed to set snapshot", zap.Error(err))
	} else {
		x.logger.Debug("Updated xDS snapshot", zap.String("version", version))
	}
}

func (x *XDSServerImpl) generateEnvoyClusters() []*clusterv3.Cluster {
	clusters := make([]*clusterv3.Cluster, 0, len(x.clusters))

	for clusterID, cluster := range x.clusters {
		if !cluster.Healthy {
			continue
		}

		weight := x.weights[clusterID]
		if weight <= 0 {
			weight = 1
		}

		envoyCluster := &clusterv3.Cluster{
			Name: clusterID,
			ClusterDiscoveryType: &clusterv3.Cluster_Type{
				Type: clusterv3.Cluster_EDS,
			},
			EdsClusterConfig: &clusterv3.Cluster_EdsClusterConfig{
				EdsConfig: &corev3.ConfigSource{
					ResourceApiVersion: corev3.ApiVersion_V3,
					ConfigSourceSpecifier: &corev3.ConfigSource_Ads{
						Ads: &corev3.AggregatedConfigSource{},
					},
				},
				ServiceName: clusterID,
			},
			ConnectTimeout: durationpb.New(5),
			HealthChecks: []*corev3.HealthCheck{
				{
					Timeout:            durationpb.New(x.config.HealthCheck.Timeout),
					Interval:           durationpb.New(x.config.HealthCheck.Interval),
					UnhealthyThreshold: wrapperspb.UInt32(x.config.HealthCheck.UnhealthyThreshold),
					HealthyThreshold:   wrapperspb.UInt32(x.config.HealthCheck.HealthyThreshold),
					HealthChecker: &corev3.HealthCheck_HttpHealthCheck_{
						HttpHealthCheck: &corev3.HealthCheck_HttpHealthCheck{
							Path: x.config.HealthCheck.Path,
						},
					},
				},
			},
			Metadata: &corev3.Metadata{
				FilterMetadata: map[string]*anypb.Any{
					"envoy.lb": x.createLBMetadata(weight),
				},
			},
		}

		clusters = append(clusters, envoyCluster)
	}

	return clusters
}

func (x *XDSServerImpl) createLBMetadata(weight int) *anypb.Any {
	type lbMetadata struct {
		Weight int `protobuf:"varint,1,opt,name=weight,proto3"`
	}
	md := &lbMetadata{Weight: weight}
	data, _ := anypb.New(md)
	return data
}

func (x *XDSServerImpl) generateEnvoyEndpoints() []*endpointv3.ClusterLoadAssignment {
	endpoints := make([]*endpointv3.ClusterLoadAssignment, 0, len(x.backends))

	for clusterID, backends := range x.backends {
		cluster, exists := x.clusters[clusterID]
		if !exists || !cluster.Healthy {
			continue
		}

		lbEndpoints := make([]*endpointv3.LbEndpoint, 0, len(backends))
		for _, backend := range backends {
			if !backend.Healthy {
				continue
			}

			weight := uint32(backend.Weight)
			if weight <= 0 {
				weight = 1
			}

			lbEndpoint := &endpointv3.LbEndpoint{
				HostIdentifier: &endpointv3.LbEndpoint_Endpoint{
					Endpoint: &endpointv3.Endpoint{
						Address: &corev3.Address{
							Address: &corev3.Address_SocketAddress{
								SocketAddress: &corev3.SocketAddress{
									Protocol: corev3.SocketAddress_TCP,
									Address:  backend.Address,
									PortSpecifier: &corev3.SocketAddress_PortValue{
										PortValue: backend.Port,
									},
								},
							},
						},
					},
				},
				HealthStatus: corev3.HealthStatus_HEALTHY,
				LoadBalancingWeight: &wrapperspb.UInt32Value{
					Value: weight,
				},
			}
			lbEndpoints = append(lbEndpoints, lbEndpoint)
		}

		if len(lbEndpoints) > 0 {
			cla := &endpointv3.ClusterLoadAssignment{
				ClusterName: clusterID,
				Endpoints: []*endpointv3.LocalityLbEndpoints{
					{
						LbEndpoints: lbEndpoints,
						LoadBalancingWeight: &wrapperspb.UInt32Value{
							Value: uint32(x.weights[clusterID]),
						},
					},
				},
			}
			endpoints = append(endpoints, cla)
		}
	}

	return endpoints
}

func (x *XDSServerImpl) generateEnvoyListeners() []*listenerv3.Listener {
	listeners := make([]*listenerv3.Listener, 0, len(x.config.Listeners))

	for _, listenerConfig := range x.config.Listeners {
		routerConfig, _ := anypb.New(&routerv3.Router{})

		httpFilter := &hcmv3.HttpFilter{
			Name: "envoy.filters.http.router",
			ConfigType: &hcmv3.HttpFilter_TypedConfig{
				TypedConfig: routerConfig,
			},
		}

		manager := &managerv3.HttpConnectionManager{
			CodecType:  managerv3.HttpConnectionManager_AUTO,
			StatPrefix: "ingress_http",
			RouteSpecifier: &managerv3.HttpConnectionManager_Rds{
				Rds: &managerv3.Rds{
					RouteConfigName: "main_route",
					ConfigSource: &corev3.ConfigSource{
						ResourceApiVersion: corev3.ApiVersion_V3,
						ConfigSourceSpecifier: &corev3.ConfigSource_Ads{
							Ads: &corev3.AggregatedConfigSource{},
						},
					},
				},
			},
			HttpFilters: []*hcmv3.HttpFilter{httpFilter},
		}



		managerAny, _ := anypb.New(manager)

		listener := &listenerv3.Listener{
			Name: fmt.Sprintf("listener_%d", listenerConfig.Port),
			Address: &corev3.Address{
				Address: &corev3.Address_SocketAddress{
					SocketAddress: &corev3.SocketAddress{
						Protocol: corev3.SocketAddress_TCP,
						Address:  "0.0.0.0",
						PortSpecifier: &corev3.SocketAddress_PortValue{
							PortValue: listenerConfig.Port,
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
								TypedConfig: managerAny,
							},
						},
					},
				},
			},
		}

		listeners = append(listeners, listener)
	}

	return listeners
}

func (x *XDSServerImpl) generateEnvoyRoutes() []*routev3.RouteConfiguration {
	var weightedClusters []*routev3.WeightedCluster_ClusterWeight
	totalWeight := 0

	for clusterID, cluster := range x.clusters {
		if !cluster.Healthy {
			continue
		}

		weight := x.weights[clusterID]
		if weight <= 0 {
			weight = 1
		}
		totalWeight += weight

		weightedCluster := &routev3.WeightedCluster_ClusterWeight{
			Name:   clusterID,
			Weight: &wrapperspb.UInt32Value{Value: uint32(weight)},
		}

		if x.config.TrafficMirroring.Enabled && x.config.TrafficMirroring.TargetCluster == clusterID {
			weightedCluster.RequestMirrorPolicies = x.createMirrorPolicies()
		}

		weightedClusters = append(weightedClusters, weightedCluster)
	}

	if len(weightedClusters) == 0 {
		return nil
	}

	routeAction := &routev3.RouteAction{
		ClusterSpecifier: &routev3.RouteAction_WeightedClusters{
			WeightedClusters: &routev3.WeightedCluster{
				Clusters:    weightedClusters,
				TotalWeight: &wrapperspb.UInt32Value{Value: uint32(totalWeight)},
			},
		},
		Timeout: durationpb.New(30),
	}

	if x.config.SessionAffinity.Enabled {
		routeAction.HashPolicy = []*routev3.RouteAction_HashPolicy{
			{
				PolicySpecifier: &routev3.RouteAction_HashPolicy_Header{
					Header: &routev3.RouteAction_HashPolicy_HeaderHash{
						HeaderName: "X-Gateway-ID",
					},
				},
				Terminal: true,
			},
		}
	}

	route := &routev3.Route{
		Name: "main_route",
		Match: &routev3.RouteMatch{
			PathSpecifier: &routev3.RouteMatch_Prefix{
				Prefix: "/",
			},
		},
		Action: &routev3.Route_Route{
			Route: routeAction,
		},
	}

	routeConfig := &routev3.RouteConfiguration{
		Name: "main_route",
		VirtualHosts: []*routev3.VirtualHost{
			{
				Name:    "all_hosts",
				Domains: []string{"*"},
				Routes:  []*routev3.Route{route},
			},
		},
	}

	return []*routev3.RouteConfiguration{routeConfig}
}

func (x *XDSServerImpl) createMirrorPolicies() []*routev3.RouteAction_RequestMirrorPolicy {
	if !x.config.TrafficMirroring.Enabled {
		return nil
	}

	return []*routev3.RouteAction_RequestMirrorPolicy{
		{
			Cluster: x.config.TrafficMirroring.TargetCluster,
			RuntimeFraction: &corev3.RuntimeFractionalPercent{
				DefaultValue: &corev3.FractionalPercent{
					Numerator:   uint32(x.config.TrafficMirroring.Percent * 10000),
					Denominator: corev3.FractionalPercent_MILLION,
				},
			},
		},
	}
}
