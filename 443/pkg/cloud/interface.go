package cloud

import (
	"context"
	"cross-cloud-lb/pkg/model"
)

type Provider interface {
	GetCluster(ctx context.Context, clusterID string) (*model.Cluster, error)
	ListClusters(ctx context.Context) ([]*model.Cluster, error)
	GetClusterEndpoints(ctx context.Context, clusterID string, namespace, serviceName string) ([]*model.Backend, error)
	CheckClusterHealth(ctx context.Context, clusterID string) (bool, error)
	Provider() model.CloudProvider
}

type ProviderConfig struct {
	Provider        model.CloudProvider `json:"provider"`
	Region          string            `json:"region"`
	AccessKeyID     string            `json:"access_key_id,omitempty"`
	AccessKeySecret string            `json:"access_key_secret,omitempty"`
	SubscriptionID  string            `json:"subscription_id,omitempty"`
	TenantID        string            `json:"tenant_id,omitempty"`
	ClientID        string            `json:"client_id,omitempty"`
	ClientSecret    string            `json:"client_secret,omitempty"`
	ProjectID       string            `json:"project_id,omitempty"`
	KubeConfigPath  string            `json:"kube_config_path,omitempty"`
}
