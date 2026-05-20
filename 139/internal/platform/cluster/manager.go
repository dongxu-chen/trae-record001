package cluster

import (
	"fmt"
	"sync"
	"time"
)

type Manager struct {
	clusters map[string]*Cluster
	mu       sync.RWMutex
}

type Cluster struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Description string            `json:"description,omitempty"`
	Endpoint    string            `json:"endpoint"`
	Status      string            `json:"status"`
	Labels      map[string]string `json:"labels,omitempty"`
	Enabled     bool              `json:"enabled"`
	CreatedAt   time.Time         `json:"created_at"`
	Health      *ClusterHealth    `json:"health,omitempty"`
}

type ClusterHealth struct {
	Status        string    `json:"status"`
	LastChecked   time.Time `json:"last_checked"`
	UptimeSeconds float64   `json:"uptime_seconds,omitempty"`
	ErrorCount    int       `json:"error_count,omitempty"`
	MetricsCount  int       `json:"metrics_count,omitempty"`
}

type Config struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Description string            `json:"description,omitempty"`
	Endpoint    string            `json:"endpoint"`
	Labels      map[string]string `json:"labels,omitempty"`
	Enabled     bool              `json:"enabled,omitempty"`
}

func NewManager() *Manager {
	return &Manager{
		clusters: make(map[string]*Cluster),
	}
}

func (m *Manager) AddCluster(cfg *Config) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if cfg.ID == "" {
		cfg.ID = fmt.Sprintf("cluster-%s", cfg.Name)
	}

	if _, exists := m.clusters[cfg.ID]; exists {
		return fmt.Errorf("cluster already exists: %s", cfg.ID)
	}

	cluster := &Cluster{
		ID:          cfg.ID,
		Name:        cfg.Name,
		Description: cfg.Description,
		Endpoint:    cfg.Endpoint,
		Status:      "stopped",
		Labels:      cfg.Labels,
		Enabled:     cfg.Enabled,
		CreatedAt:   time.Now(),
	}

	m.clusters[cfg.ID] = cluster
	return nil
}

func (m *Manager) RemoveCluster(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, exists := m.clusters[id]; !exists {
		return fmt.Errorf("cluster not found: %s", id)
	}

	delete(m.clusters, id)
	return nil
}

func (m *Manager) GetCluster(id string) (*Cluster, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	c, ok := m.clusters[id]
	return c, ok
}

func (m *Manager) GetAllClusters() []*Cluster {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*Cluster, 0, len(m.clusters))
	for _, c := range m.clusters {
		result = append(result, c)
	}
	return result
}

func (m *Manager) GetEnabledClusters() []*Cluster {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*Cluster, 0)
	for _, c := range m.clusters {
		if c.Enabled {
			result = append(result, c)
		}
	}
	return result
}

func (m *Manager) StartCluster(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	c, exists := m.clusters[id]
	if !exists {
		return fmt.Errorf("cluster not found: %s", id)
	}

	c.Status = "running"
	c.Health = &ClusterHealth{
		Status:      "healthy",
		LastChecked: time.Now(),
	}

	return nil
}

func (m *Manager) StopCluster(id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	c, exists := m.clusters[id]
	if !exists {
		return fmt.Errorf("cluster not found: %s", id)
	}

	c.Status = "stopped"
	return nil
}

func (m *Manager) GetClusterHealth(id string) (*ClusterHealth, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	c, exists := m.clusters[id]
	if !exists {
		return nil, fmt.Errorf("cluster not found: %s", id)
	}

	if c.Health == nil {
		c.Health = &ClusterHealth{
			Status:      "unknown",
			LastChecked: time.Now(),
		}
	}

	return c.Health, nil
}

func (m *Manager) UpdateClusterHealth(id string, health *ClusterHealth) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	c, exists := m.clusters[id]
	if !exists {
		return fmt.Errorf("cluster not found: %s", id)
	}

	health.LastChecked = time.Now()
	c.Health = health

	if health.Status == "critical" {
		c.Status = "degraded"
	} else if health.Status == "healthy" {
		c.Status = "running"
	}

	return nil
}

func CreateDefaultClusters(mgr *Manager) {
	productionClusters := []Config{
		{
			ID:          "us-east-1",
			Name:        "US East (Virginia)",
			Description: "Primary production cluster",
			Endpoint:    "http://prometheus-us-east-1:9090",
			Labels: map[string]string{
				"region": "us-east-1",
				"env":    "production",
				"cloud":  "aws",
			},
			Enabled: true,
		},
		{
			ID:          "eu-west-1",
			Name:        "EU West (Ireland)",
			Description: "European production cluster",
			Endpoint:    "http://prometheus-eu-west-1:9090",
			Labels: map[string]string{
				"region": "eu-west-1",
				"env":    "production",
				"cloud":  "aws",
			},
			Enabled: true,
		},
		{
			ID:          "ap-southeast-1",
			Name:        "APAC (Singapore)",
			Description: "Asia Pacific production cluster",
			Endpoint:    "http://prometheus-ap-southeast-1:9090",
			Labels: map[string]string{
				"region": "ap-southeast-1",
				"env":    "production",
				"cloud":  "aws",
			},
			Enabled: true,
		},
	}

	for _, cfg := range productionClusters {
		mgr.AddCluster(&cfg)
	}
}
