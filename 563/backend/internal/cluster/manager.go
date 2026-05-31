package cluster

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"os"
	"sync"
	"time"

	clientv3 "go.etcd.io/etcd/client/v3"
	"etcd-backup-manager/pkg/models"
)

type Manager struct {
	clusters map[string]*models.Cluster
	clients  map[string]*clientv3.Client
	mu       sync.RWMutex
}

func NewManager() *Manager {
	return &Manager{
		clusters: make(map[string]*models.Cluster),
		clients:  make(map[string]*clientv3.Client),
	}
}

func (m *Manager) AddCluster(cluster *models.Cluster) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.clusters[cluster.ID]; exists {
		return fmt.Errorf("cluster %s already exists", cluster.ID)
	}

	client, err := m.createClient(cluster)
	if err != nil {
		return fmt.Errorf("failed to create etcd client: %w", err)
	}

	m.clusters[cluster.ID] = cluster
	m.clients[cluster.ID] = client
	return nil
}

func (m *Manager) UpdateCluster(cluster *models.Cluster) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.clusters[cluster.ID]; !exists {
		return fmt.Errorf("cluster %s not found", cluster.ID)
	}

	if client, exists := m.clients[cluster.ID]; exists {
		client.Close()
	}

	client, err := m.createClient(cluster)
	if err != nil {
		return fmt.Errorf("failed to create etcd client: %w", err)
	}

	cluster.UpdatedAt = time.Now()
	m.clusters[cluster.ID] = cluster
	m.clients[cluster.ID] = client
	return nil
}

func (m *Manager) RemoveCluster(clusterID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.clusters[clusterID]; !exists {
		return fmt.Errorf("cluster %s not found", clusterID)
	}

	if client, exists := m.clients[clusterID]; exists {
		client.Close()
	}

	delete(m.clusters, clusterID)
	delete(m.clients, clusterID)
	return nil
}

func (m *Manager) GetCluster(clusterID string) (*models.Cluster, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	cluster, exists := m.clusters[clusterID]
	if !exists {
		return nil, fmt.Errorf("cluster %s not found", clusterID)
	}
	return cluster, nil
}

func (m *Manager) ListClusters() []*models.Cluster {
	m.mu.RLock()
	defer m.mu.RUnlock()

	clusters := make([]*models.Cluster, 0, len(m.clusters))
	for _, cluster := range m.clusters {
		clusters = append(clusters, cluster)
	}
	return clusters
}

func (m *Manager) GetClient(clusterID string) (*clientv3.Client, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	client, exists := m.clients[clusterID]
	if !exists {
		return nil, fmt.Errorf("client for cluster %s not found", clusterID)
	}
	return client, nil
}

func (m *Manager) createClient(cluster *models.Cluster) (*clientv3.Client, error) {
	config := clientv3.Config{
		Endpoints:   cluster.Endpoints,
		DialTimeout: 5 * time.Second,
		Username:    cluster.Username,
		Password:    cluster.Password,
	}

	if cluster.TLS {
		tlsConfig, err := m.createTLSConfig(cluster)
		if err != nil {
			return nil, err
		}
		config.TLS = tlsConfig
	}

	return clientv3.New(config)
}

func (m *Manager) createTLSConfig(cluster *models.Cluster) (*tls.Config, error) {
	tlsConfig := &tls.Config{}

	if cluster.CAFile != "" {
		caCert, err := os.ReadFile(cluster.CAFile)
		if err != nil {
			return nil, fmt.Errorf("failed to read CA file: %w", err)
		}
		caCertPool := x509.NewCertPool()
		caCertPool.AppendCertsFromPEM(caCert)
		tlsConfig.RootCAs = caCertPool
	}

	if cluster.CertFile != "" && cluster.KeyFile != "" {
		cert, err := tls.LoadX509KeyPair(cluster.CertFile, cluster.KeyFile)
		if err != nil {
			return nil, fmt.Errorf("failed to load client cert/key: %w", err)
		}
		tlsConfig.Certificates = []tls.Certificate{cert}
	}

	return tlsConfig, nil
}

func (m *Manager) GetClusterStatus(ctx context.Context, clusterID string) (*models.ClusterStatus, error) {
	client, err := m.GetClient(clusterID)
	if err != nil {
		return nil, err
	}

	cluster, err := m.GetCluster(clusterID)
	if err != nil {
		return nil, err
	}

	status := &models.ClusterStatus{
		ID:      cluster.ID,
		Name:    cluster.Name,
		Healthy: true,
		Members: make([]models.Member, 0),
	}

	resp, err := client.MemberList(ctx)
	if err != nil {
		status.Healthy = false
		status.Message = fmt.Sprintf("Failed to list members: %v", err)
		return status, nil
	}

	memberMap := make(map[uint64]*clientv3.StatusResponse)
	var leaderID uint64

	for _, member := range resp.Members {
		for _, ep := range member.ClientURLs {
			statResp, err := client.Status(ctx, ep)
			if err == nil {
				memberMap[member.ID] = statResp
				if statResp.Leader == member.ID {
					leaderID = member.ID
					status.Revision = statResp.Header.Revision
					status.DBSize = statResp.DbSize
					status.Version = statResp.Version
					status.Leader = member.Name
				}
			}
		}
	}

	for _, member := range resp.Members {
		m := models.Member{
			ID:        fmt.Sprintf("%x", member.ID),
			Name:      member.Name,
			Endpoints: member.ClientURLs,
			IsLeader:  member.ID == leaderID,
			IsHealthy: true,
		}
		if _, exists := memberMap[member.ID]; !exists {
			m.IsHealthy = false
			status.Healthy = false
		}
		status.Members = append(status.Members, m)
	}

	return status, nil
}

func (m *Manager) GetAllKeys(ctx context.Context, clusterID string) ([]string, error) {
	client, err := m.GetClient(clusterID)
	if err != nil {
		return nil, err
	}

	resp, err := client.Get(ctx, "", clientv3.WithPrefix(), clientv3.WithKeysOnly())
	if err != nil {
		return nil, err
	}

	keys := make([]string, len(resp.Kvs))
	for i, kv := range resp.Kvs {
		keys[i] = string(kv.Key)
	}
	return keys, nil
}

func (m *Manager) GetKVCount(ctx context.Context, clusterID string) (int64, error) {
	client, err := m.GetClient(clusterID)
	if err != nil {
		return 0, err
	}

	resp, err := client.Get(ctx, "", clientv3.WithPrefix(), clientv3.WithCountOnly())
	if err != nil {
		return 0, err
	}
	return resp.Count, nil
}

func (m *Manager) Close() {
	m.mu.Lock()
	defer m.mu.Unlock()

	for _, client := range m.clients {
		client.Close()
	}
	m.clients = make(map[string]*clientv3.Client)
}
