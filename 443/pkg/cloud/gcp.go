package cloud

import (
	"context"
	"cross-cloud-lb/pkg/model"
	"fmt"
	"sync"

	container "google.golang.org/api/container/v1"
	"google.golang.org/api/option"
)

type GCPProvider struct {
	projectID string
	service   *container.Service
	mu        sync.RWMutex
	clusters  map[string]*model.Cluster
}

func NewGCPProvider(cfg ProviderConfig) (*GCPProvider, error) {
	ctx := context.Background()
	service, err := container.NewService(ctx, option.WithScopes(container.CloudPlatformScope))
	if err != nil {
		return nil, fmt.Errorf("failed to create GKE client: %w", err)
	}

	return &GCPProvider{
		projectID: cfg.ProjectID,
		service:   service,
		clusters:  make(map[string]*model.Cluster),
	}, nil
}

func (p *GCPProvider) GetCluster(ctx context.Context, clusterID string) (*model.Cluster, error) {
	p.mu.RLock()
	if cluster, exists := p.clusters[clusterID]; exists {
		p.mu.RUnlock()
		return cluster, nil
	}
	p.mu.RUnlock()

	zone, name := parseGCPClusterID(clusterID)
	
	resp, err := p.service.Projects.Zones.Clusters.Get(p.projectID, zone, name).Context(ctx).Do()
	if err != nil {
		return nil, fmt.Errorf("failed to get GKE cluster: %w", err)
	}

	cluster := &model.Cluster{
		ID:          clusterID,
		Name:        resp.Name,
		Provider:    model.GCP,
		Region:      resp.Zone,
		APIEndpoint: resp.Endpoint,
		Status:      model.ClusterStatus(resp.Status),
		Healthy:     resp.Status == "RUNNING",
		Labels:      resp.ResourceLabels,
	}

	p.mu.Lock()
	p.clusters[clusterID] = cluster
	p.mu.Unlock()

	return cluster, nil
}

func (p *GCPProvider) ListClusters(ctx context.Context) ([]*model.Cluster, error) {
	parent := fmt.Sprintf("projects/%s/locations/-", p.projectID)
	resp, err := p.service.Projects.Locations.Clusters.List(parent).Context(ctx).Do()
	if err != nil {
		return nil, fmt.Errorf("failed to list GKE clusters: %w", err)
	}

	clusters := make([]*model.Cluster, 0, len(resp.Clusters))
	for _, c := range resp.Clusters {
		clusterID := fmt.Sprintf("%s/%s", c.Zone, c.Name)
		cluster := &model.Cluster{
			ID:          clusterID,
			Name:        c.Name,
			Provider:    model.GCP,
			Region:      c.Zone,
			APIEndpoint: c.Endpoint,
			Status:      model.ClusterStatus(c.Status),
			Healthy:     c.Status == "RUNNING",
			Labels:      c.ResourceLabels,
		}
		clusters = append(clusters, cluster)
	}

	return clusters, nil
}

func (p *GCPProvider) GetClusterEndpoints(ctx context.Context, clusterID, namespace, serviceName string) ([]*model.Backend, error) {
	return nil, fmt.Errorf("kubernetes client integration required for endpoint discovery")
}

func (p *GCPProvider) CheckClusterHealth(ctx context.Context, clusterID string) (bool, error) {
	cluster, err := p.GetCluster(ctx, clusterID)
	if err != nil {
		return false, err
	}
	return cluster.Healthy, nil
}

func (p *GCPProvider) Provider() model.CloudProvider {
	return model.GCP
}

func parseGCPClusterID(id string) (string, string) {
	return "us-central1-a", id
}
