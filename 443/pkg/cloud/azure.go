package cloud

import (
	"context"
	"cross-cloud-lb/pkg/model"
	"fmt"
	"sync"

	"github.com/Azure/azure-sdk-for-go/sdk/azcore"
	"github.com/Azure/azure-sdk-for-go/sdk/azidentity"
	"github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/containerservice/armcontainerservice/v4"
)

type AzureProvider struct {
	cred           azcore.TokenCredential
	subscriptionID string
	clustersClient *armcontainerservice.ManagedClustersClient
	mu             sync.RWMutex
	clusters       map[string]*model.Cluster
}

func NewAzureProvider(cfg ProviderConfig) (*AzureProvider, error) {
	cred, err := azidentity.NewDefaultAzureCredential(nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create Azure credential: %w", err)
	}

	clustersClient, err := armcontainerservice.NewManagedClustersClient(cfg.SubscriptionID, cred, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create AKS client: %w", err)
	}

	return &AzureProvider{
		cred:           cred,
		subscriptionID: cfg.SubscriptionID,
		clustersClient: clustersClient,
		clusters:       make(map[string]*model.Cluster),
	}, nil
}

func (p *AzureProvider) GetCluster(ctx context.Context, clusterID string) (*model.Cluster, error) {
	p.mu.RLock()
	if cluster, exists := p.clusters[clusterID]; exists {
		p.mu.RUnlock()
		return cluster, nil
	}
	p.mu.RUnlock()

	resourceGroup, clusterName := parseAzureResourceID(clusterID)
	
	resp, err := p.clustersClient.Get(ctx, resourceGroup, clusterName, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to get AKS cluster: %w", err)
	}

	cluster := &model.Cluster{
		ID:          clusterID,
		Name:        *resp.ManagedCluster.Name,
		Provider:    model.Azure,
		Region:      *resp.ManagedCluster.Location,
		APIEndpoint: *resp.ManagedCluster.Properties.Fqdn,
		Status:      model.ClusterStatus(string(*resp.ManagedCluster.Properties.ProvisioningState)),
		Healthy:     *resp.ManagedCluster.Properties.ProvisioningState == "Succeeded",
	}

	p.mu.Lock()
	p.clusters[clusterID] = cluster
	p.mu.Unlock()

	return cluster, nil
}

func (p *AzureProvider) ListClusters(ctx context.Context) ([]*model.Cluster, error) {
	pager := p.clustersClient.NewListPager(nil)
	clusters := make([]*model.Cluster, 0)

	for pager.More() {
		page, err := pager.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to list AKS clusters: %w", err)
		}

		for _, cluster := range page.Value {
			clusterID := *cluster.ID
			c, err := p.GetCluster(ctx, clusterID)
			if err != nil {
				continue
			}
			clusters = append(clusters, c)
		}
	}

	return clusters, nil
}

func (p *AzureProvider) GetClusterEndpoints(ctx context.Context, clusterID, namespace, serviceName string) ([]*model.Backend, error) {
	return nil, fmt.Errorf("kubernetes client integration required for endpoint discovery")
}

func (p *AzureProvider) CheckClusterHealth(ctx context.Context, clusterID string) (bool, error) {
	cluster, err := p.GetCluster(ctx, clusterID)
	if err != nil {
		return false, err
	}
	return cluster.Healthy, nil
}

func (p *AzureProvider) Provider() model.CloudProvider {
	return model.Azure
}

func parseAzureResourceID(id string) (string, string) {
	return "default", id
}
