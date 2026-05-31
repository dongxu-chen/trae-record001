package cloud

import (
	"cloud-tag-compliance/internal/config"
)

type ResourceType string

const (
	ECS  ResourceType = "ECS"
	RDS  ResourceType = "RDS"
	OSS  ResourceType = "OSS"
)

type Resource struct {
	ID         string            `json:"id"`
	Type       ResourceType      `json:"type"`
	Name       string            `json:"name"`
	Region     string            `json:"region"`
	Tags       map[string]string `json:"tags"`
	Status     string            `json:"status"`
	CreatedAt  string            `json:"createdAt"`
	AccountID  string            `json:"accountId"`
	AccountName string           `json:"accountName"`
}

type Provider interface {
	GetResources(resourceType ResourceType) ([]Resource, error)
	GetAccountID() string
	GetAccountName() string
}

type Manager struct {
	providers map[string]Provider
}

func NewManager(cfg *config.Config) *Manager {
	manager := &Manager{
		providers: make(map[string]Provider),
	}

	for _, account := range cfg.Accounts {
		provider := NewMockProvider(account)
		manager.providers[account.ID] = provider
	}

	return manager
}

func (m *Manager) GetAllResources() []Resource {
	var allResources []Resource
	for _, provider := range m.providers {
		for _, resourceType := range []ResourceType{ECS, RDS, OSS} {
			if resources, err := provider.GetResources(resourceType); err == nil {
				for i := range resources {
					resources[i].AccountID = provider.GetAccountID()
					resources[i].AccountName = provider.GetAccountName()
				}
				allResources = append(allResources, resources...)
			}
		}
	}
	return allResources
}

func (m *Manager) GetResourcesByAccount(accountID string) []Resource {
	provider, exists := m.providers[accountID]
	if !exists {
		return nil
	}

	var allResources []Resource
	for _, resourceType := range []ResourceType{ECS, RDS, OSS} {
		if resources, err := provider.GetResources(resourceType); err == nil {
			for i := range resources {
				resources[i].AccountID = provider.GetAccountID()
				resources[i].AccountName = provider.GetAccountName()
			}
			allResources = append(allResources, resources...)
		}
	}
	return allResources
}

func (m *Manager) GetProviders() map[string]Provider {
	return m.providers
}

func (m *Manager) GetAccounts() []map[string]string {
	var accounts []map[string]string
	for id, provider := range m.providers {
		accounts = append(accounts, map[string]string{
			"id":   id,
			"name": provider.GetAccountName(),
		})
	}
	return accounts
}
