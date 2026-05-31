package cloud

import (
	"cloud-tag-compliance/internal/config"
	"fmt"
	"time"
)

type MockProvider struct {
	account config.AccountConfig
}

func NewMockProvider(account config.AccountConfig) *MockProvider {
	return &MockProvider{
		account: account,
	}
}

func (p *MockProvider) GetAccountID() string {
	return p.account.ID
}

func (p *MockProvider) GetAccountName() string {
	return p.account.Name
}

func (p *MockProvider) GetResources(resourceType ResourceType) ([]Resource, error) {
	switch resourceType {
	case ECS:
		return p.getMockECSResources(), nil
	case RDS:
		return p.getMockRDSResources(), nil
	case OSS:
		return p.getMockOSSResources(), nil
	default:
		return nil, fmt.Errorf("unsupported resource type: %s", resourceType)
	}
}

func (p *MockProvider) getMockECSResources() []Resource {
	return []Resource{
		{
			ID:        fmt.Sprintf("ecs-%s-001", p.account.ID),
			Type:      ECS,
			Name:      "web-server-01",
			Region:    p.account.Region,
			Tags:      map[string]string{"Environment": "Production", "Department": "Engineering", "CostCenter": "CC001"},
			Status:    "Running",
			CreatedAt: time.Now().AddDate(0, -3, 0).Format(time.RFC3339),
		},
		{
			ID:        fmt.Sprintf("ecs-%s-002", p.account.ID),
			Type:      ECS,
			Name:      "database-server",
			Region:    p.account.Region,
			Tags:      map[string]string{"Environment": "Production", "Department": "Data"},
			Status:    "Running",
			CreatedAt: time.Now().AddDate(0, -6, 0).Format(time.RFC3339),
		},
		{
			ID:        fmt.Sprintf("ecs-%s-003", p.account.ID),
			Type:      ECS,
			Name:      "dev-server-01",
			Region:    p.account.Region,
			Tags:      map[string]string{"env": "dev", "team": "backend"},
			Status:    "Stopped",
			CreatedAt: time.Now().AddDate(0, -1, 0).Format(time.RFC3339),
		},
		{
			ID:        fmt.Sprintf("ecs-%s-004", p.account.ID),
			Type:      ECS,
			Name:      "untagged-server",
			Region:    p.account.Region,
			Tags:      map[string]string{},
			Status:    "Running",
			CreatedAt: time.Now().AddDate(0, 0, -15).Format(time.RFC3339),
		},
	}
}

func (p *MockProvider) getMockRDSResources() []Resource {
	return []Resource{
		{
			ID:        fmt.Sprintf("rds-%s-001", p.account.ID),
			Type:      RDS,
			Name:      "prod-mysql",
			Region:    p.account.Region,
			Tags:      map[string]string{"Environment": "Production", "Department": "Data", "CostCenter": "CC002"},
			Status:    "Running",
			CreatedAt: time.Now().AddDate(0, -4, 0).Format(time.RFC3339),
		},
		{
			ID:        fmt.Sprintf("rds-%s-002", p.account.ID),
			Type:      RDS,
			Name:      "test-postgres",
			Region:    p.account.Region,
			Tags:      map[string]string{"Environment": "Testing"},
			Status:    "Running",
			CreatedAt: time.Now().AddDate(0, -2, 0).Format(time.RFC3339),
		},
		{
			ID:        fmt.Sprintf("rds-%s-003", p.account.ID),
			Type:      RDS,
			Name:      "legacy-oracle",
			Region:    p.account.Region,
			Tags:      map[string]string{"Owner": "admin"},
			Status:    "Running",
			CreatedAt: time.Now().AddDate(-1, 0, 0).Format(time.RFC3339),
		},
	}
}

func (p *MockProvider) getMockOSSResources() []Resource {
	return []Resource{
		{
			ID:        fmt.Sprintf("oss-%s-001", p.account.ID),
			Type:      OSS,
			Name:      "prod-backup-bucket",
			Region:    p.account.Region,
			Tags:      map[string]string{"Environment": "Production", "Department": "Engineering", "CostCenter": "CC001"},
			Status:    "Active",
			CreatedAt: time.Now().AddDate(0, -5, 0).Format(time.RFC3339),
		},
		{
			ID:        fmt.Sprintf("oss-%s-002", p.account.ID),
			Type:      OSS,
			Name:      "dev-assets",
			Region:    p.account.Region,
			Tags:      map[string]string{"Environment": "Development", "Department": "Engineering"},
			Status:    "Active",
			CreatedAt: time.Now().AddDate(0, -1, 0).Format(time.RFC3339),
		},
		{
			ID:        fmt.Sprintf("oss-%s-003", p.account.ID),
			Type:      OSS,
			Name:      "public-static",
			Region:    p.account.Region,
			Tags:      map[string]string{},
			Status:    "Active",
			CreatedAt: time.Now().AddDate(0, -8, 0).Format(time.RFC3339),
		},
	}
}
