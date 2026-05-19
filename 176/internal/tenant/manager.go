package tenant

import (
	"fmt"
	"sync"

	"ssl-manager/internal/config"
)

type Manager struct {
	cfg     *config.Config
	tenants map[string]*config.TenantConfig
	mu      sync.RWMutex
}

func NewManager(cfg *config.Config) *Manager {
	manager := &Manager{
		cfg:     cfg,
		tenants: make(map[string]*config.TenantConfig),
	}

	for i := range cfg.Tenants {
		tenant := &cfg.Tenants[i]
		manager.tenants[tenant.ID] = tenant
	}

	return manager
}

func (m *Manager) GetTenant(tenantID string) (*config.TenantConfig, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	tenant, exists := m.tenants[tenantID]
	if !exists {
		return nil, fmt.Errorf("tenant %s not found", tenantID)
	}
	return tenant, nil
}

func (m *Manager) ListTenants() []*config.TenantConfig {
	m.mu.RLock()
	defer m.mu.RUnlock()

	tenants := make([]*config.TenantConfig, 0, len(m.tenants))
	for _, tenant := range m.tenants {
		tenants = append(tenants, tenant)
	}
	return tenants
}

func (m *Manager) HasPermission(tenantID, permission string) bool {
	tenant, err := m.GetTenant(tenantID)
	if err != nil {
		return false
	}

	for _, p := range tenant.Permissions {
		if p == "*" || p == permission {
			return true
		}
	}
	return false
}

func (m *Manager) GetTenantCertificates(tenantID string) ([]config.CertificateConfig, error) {
	tenant, err := m.GetTenant(tenantID)
	if err != nil {
		return nil, err
	}
	return tenant.Certificates, nil
}

func (m *Manager) GetEffectiveACME(tenantID string) (config.ACMEConfig, error) {
	tenant, err := m.GetTenant(tenantID)
	if err != nil {
		return config.ACMEConfig{}, err
	}
	return tenant.GetACME(m.cfg.ACME), nil
}

func (m *Manager) GetEffectiveDNS(tenantID string) (config.DNSConfig, error) {
	tenant, err := m.GetTenant(tenantID)
	if err != nil {
		return config.DNSConfig{}, err
	}
	return tenant.GetDNS(m.cfg.DNS), nil
}

func (m *Manager) GetEffectiveDeploy(tenantID string) (config.DeployConfig, error) {
	tenant, err := m.GetTenant(tenantID)
	if err != nil {
		return config.DeployConfig{}, err
	}
	return tenant.GetDeploy(m.cfg.Deploy), nil
}
