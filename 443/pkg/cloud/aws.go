package cloud

import (
	"context"
	"cross-cloud-lb/pkg/model"
	"fmt"
	"sync"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/eks"
)

type AWSProvider struct {
	cfg       aws.Config
	eksClient *eks.Client
	region    string
	mu        sync.RWMutex
	clusters  map[string]*model.Cluster
}

func NewAWSProvider(cfg ProviderConfig) (*AWSProvider, error) {
	awsCfg, err := config.LoadDefaultConfig(context.TODO(),
		config.WithRegion(cfg.Region),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return &AWSProvider{
		cfg:       awsCfg,
		eksClient: eks.NewFromConfig(awsCfg),
		region:    cfg.Region,
		clusters:  make(map[string]*model.Cluster),
	}, nil
}

func (p *AWSProvider) GetCluster(ctx context.Context, clusterID string) (*model.Cluster, error) {
	p.mu.RLock()
	if cluster, exists := p.clusters[clusterID]; exists {
		p.mu.RUnlock()
		return cluster, nil
	}
	p.mu.RUnlock()

	resp, err := p.eksClient.DescribeCluster(ctx, &eks.DescribeClusterInput{
		Name: aws.String(clusterID),
	})
	if err != nil {
		return nil, fmt.Errorf("failed to describe EKS cluster: %w", err)
	}

	cluster := &model.Cluster{
		ID:          aws.ToString(resp.Cluster.Name),
		Name:        aws.ToString(resp.Cluster.Name),
		Provider:    model.AWS,
		Region:      p.region,
		APIEndpoint: aws.ToString(resp.Cluster.Endpoint),
		Status:      model.ClusterStatus(string(resp.Cluster.Status)),
		Healthy:     resp.Cluster.Status == "ACTIVE",
		Labels:      resp.Cluster.Tags,
	}

	p.mu.Lock()
	p.clusters[clusterID] = cluster
	p.mu.Unlock()

	return cluster, nil
}

func (p *AWSProvider) ListClusters(ctx context.Context) ([]*model.Cluster, error) {
	resp, err := p.eksClient.ListClusters(ctx, &eks.ListClustersInput{})
	if err != nil {
		return nil, fmt.Errorf("failed to list EKS clusters: %w", err)
	}

	clusters := make([]*model.Cluster, 0, len(resp.Clusters))
	for _, name := range resp.Clusters {
		cluster, err := p.GetCluster(ctx, name)
		if err != nil {
			continue
		}
		clusters = append(clusters, cluster)
	}

	return clusters, nil
}

func (p *AWSProvider) GetClusterEndpoints(ctx context.Context, clusterID, namespace, serviceName string) ([]*model.Backend, error) {
	return nil, fmt.Errorf("kubernetes client integration required for endpoint discovery")
}

func (p *AWSProvider) CheckClusterHealth(ctx context.Context, clusterID string) (bool, error) {
	cluster, err := p.GetCluster(ctx, clusterID)
	if err != nil {
		return false, err
	}
	return cluster.Healthy, nil
}

func (p *AWSProvider) Provider() model.CloudProvider {
	return model.AWS
}
