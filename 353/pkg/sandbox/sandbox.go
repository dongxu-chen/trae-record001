package sandbox

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/cloud-migration-tool/config"
	awscloud "github.com/cloud-migration-tool/pkg/cloud/aws"
	aliyuncloud "github.com/cloud-migration-tool/pkg/cloud/aliyun"
	tencentcloud "github.com/cloud-migration-tool/pkg/cloud/tencent"
)

type SandboxStatus string

const (
	SandboxStatusCreating  SandboxStatus = "creating"
	SandboxStatusReady     SandboxStatus = "ready"
	SandboxStatusInUse     SandboxStatus = "in_use"
	SandboxStatusCleaning  SandboxStatus = "cleaning"
	SandboxStatusDestroyed SandboxStatus = "destroyed"
	SandboxStatusFailed    SandboxStatus = "failed"
)

type SandboxConfig struct {
	SandboxID        string
	Name             string
	Provider         string
	Region           string
	VpcCidr          string
	SubnetCidr       string
	EnableSubAccount bool
	MaxDuration      time.Duration
	Tags             map[string]string
}

type SandboxInfo struct {
	SandboxID     string
	Name          string
	Status        SandboxStatus
	Provider      string
	Region        string
	VpcID         string
	VpcCidr       string
	SubnetID      string
	SubnetCidr    string
	SecurityGroupID string
	SubAccount    *SubAccountInfo
	CreatedAt     time.Time
	ExpiresAt     time.Time
	Resources     []SandboxResource
}

type SubAccountInfo struct {
	AccountID   string
	UserName    string
	AccessKeyID string
	Permissions []string
}

type SandboxResource struct {
	ResourceID   string
	ResourceType string
	ResourceName string
	CreatedAt    time.Time
}

type SandboxManager struct {
	sandboxes map[string]*SandboxInfo
	mu        sync.RWMutex
	awsClient *awscloud.EC2Client
	aliyunClient *aliyuncloud.ECSClient
	tencentClient *tencentcloud.CVMClient
}

func NewSandboxManager() *SandboxManager {
	return &SandboxManager{
		sandboxes: make(map[string]*SandboxInfo),
	}
}

func (sm *SandboxManager) CreateSandbox(ctx context.Context, cfg SandboxConfig) (*SandboxInfo, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	if cfg.SandboxID == "" {
		cfg.SandboxID = fmt.Sprintf("sandbox-%d", time.Now().Unix())
	}
	if cfg.VpcCidr == "" {
		cfg.VpcCidr = "10.0.0.0/16"
	}
	if cfg.SubnetCidr == "" {
		cfg.SubnetCidr = "10.0.1.0/24"
	}
	if cfg.MaxDuration == 0 {
		cfg.MaxDuration = 4 * time.Hour
	}

	info := &SandboxInfo{
		SandboxID:  cfg.SandboxID,
		Name:       cfg.Name,
		Status:     SandboxStatusCreating,
		Provider:   cfg.Provider,
		Region:     cfg.Region,
		VpcCidr:    cfg.VpcCidr,
		SubnetCidr: cfg.SubnetCidr,
		CreatedAt:  time.Now(),
		ExpiresAt:  time.Now().Add(cfg.MaxDuration),
		Resources:  make([]SandboxResource, 0),
	}

	sm.sandboxes[cfg.SandboxID] = info

	if err := sm.createSandboxInfrastructure(ctx, info, cfg); err != nil {
		info.Status = SandboxStatusFailed
		return info, err
	}

	if cfg.EnableSubAccount {
		if err := sm.createSubAccount(ctx, info, cfg); err != nil {
			info.Status = SandboxStatusFailed
			return info, err
		}
	}

	info.Status = SandboxStatusReady
	return info, nil
}

func (sm *SandboxManager) createSandboxInfrastructure(ctx context.Context, info *SandboxInfo, cfg SandboxConfig) error {
	switch cfg.Provider {
	case "aws":
		return sm.createAWSSandbox(ctx, info, cfg)
	case "aliyun":
		return sm.createAliyunSandbox(ctx, info, cfg)
	case "tencent":
		return sm.createTencentSandbox(ctx, info, cfg)
	default:
		return fmt.Errorf("unsupported provider: %s", cfg.Provider)
	}
}

func (sm *SandboxManager) createAWSSandbox(ctx context.Context, info *SandboxInfo, cfg SandboxConfig) error {
	if sm.awsClient == nil {
		client, err := awscloud.NewEC2Client(cfg.Region)
		if err != nil {
			return fmt.Errorf("failed to create AWS client: %w", err)
		}
		sm.awsClient = client
	}

	vpcID, err := sm.createAWSVPC(ctx, cfg.VpcCidr, cfg.Name)
	if err != nil {
		return fmt.Errorf("failed to create VPC: %w", err)
	}
	info.VpcID = vpcID
	info.Resources = append(info.Resources, SandboxResource{
		ResourceID:   vpcID,
		ResourceType: "vpc",
		ResourceName: fmt.Sprintf("%s-vpc", cfg.Name),
		CreatedAt:    time.Now(),
	})

	subnetID, err := sm.createAWSSubnet(ctx, vpcID, cfg.SubnetCidr, cfg.Region)
	if err != nil {
		return fmt.Errorf("failed to create subnet: %w", err)
	}
	info.SubnetID = subnetID
	info.Resources = append(info.Resources, SandboxResource{
		ResourceID:   subnetID,
		ResourceType: "subnet",
		ResourceName: fmt.Sprintf("%s-subnet", cfg.Name),
		CreatedAt:    time.Now(),
	})

	sgID, err := sm.createAWSSecurityGroup(ctx, vpcID, cfg.Name)
	if err != nil {
		return fmt.Errorf("failed to create security group: %w", err)
	}
	info.SecurityGroupID = sgID
	info.Resources = append(info.Resources, SandboxResource{
		ResourceID:   sgID,
		ResourceType: "security_group",
		ResourceName: fmt.Sprintf("%s-sg", cfg.Name),
		CreatedAt:    time.Now(),
	})

	return nil
}

func (sm *SandboxManager) createAWSVPC(ctx context.Context, cidr, name string) (string, error) {
	return fmt.Sprintf("vpc-%s-sandbox", name), nil
}

func (sm *SandboxManager) createAWSSubnet(ctx context.Context, vpcID, cidr, zone string) (string, error) {
	return fmt.Sprintf("subnet-%s-sandbox", vpcID), nil
}

func (sm *SandboxManager) createAWSSecurityGroup(ctx context.Context, vpcID, name string) (string, error) {
	return fmt.Sprintf("sg-%s-sandbox", name), nil
}

func (sm *SandboxManager) createAliyunSandbox(ctx context.Context, info *SandboxInfo, cfg SandboxConfig) error {
	if sm.aliyunClient == nil {
		client, err := aliyuncloud.NewECSClient(cfg.Region, "", "")
		if err != nil {
			return fmt.Errorf("failed to create Aliyun client: %w", err)
		}
		sm.aliyunClient = client
	}

	info.VpcID = fmt.Sprintf("vpc-%s-sandbox", cfg.Name)
	info.SubnetID = fmt.Sprintf("vswitch-%s-sandbox", cfg.Name)
	info.SecurityGroupID = fmt.Sprintf("sg-%s-sandbox", cfg.Name)

	return nil
}

func (sm *SandboxManager) createTencentSandbox(ctx context.Context, info *SandboxInfo, cfg SandboxConfig) error {
	if sm.tencentClient == nil {
		client, err := tencentcloud.NewCVMClient(cfg.Region, "", "")
		if err != nil {
			return fmt.Errorf("failed to create Tencent client: %w", err)
		}
		sm.tencentClient = client
	}

	info.VpcID = fmt.Sprintf("vpc-%s-sandbox", cfg.Name)
	info.SubnetID = fmt.Sprintf("subnet-%s-sandbox", cfg.Name)
	info.SecurityGroupID = fmt.Sprintf("sg-%s-sandbox", cfg.Name)

	return nil
}

func (sm *SandboxManager) createSubAccount(ctx context.Context, info *SandboxInfo, cfg SandboxConfig) error {
	info.SubAccount = &SubAccountInfo{
		AccountID:   fmt.Sprintf("sub-%s", cfg.SandboxID),
		UserName:    fmt.Sprintf("sandbox-user-%s", cfg.Name),
		AccessKeyID: fmt.Sprintf("AKIA%s", cfg.SandboxID),
		Permissions: []string{
			"ec2:Describe*",
			"ec2:RunInstances",
			"ec2:TerminateInstances",
			"s3:Get*",
			"s3:Put*",
			"s3:List*",
		},
	}

	info.Resources = append(info.Resources, SandboxResource{
		ResourceID:   info.SubAccount.AccountID,
		ResourceType: "sub_account",
		ResourceName: info.SubAccount.UserName,
		CreatedAt:    time.Now(),
	})

	return nil
}

func (sm *SandboxManager) GetSandbox(sandboxID string) (*SandboxInfo, bool) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	info, exists := sm.sandboxes[sandboxID]
	return info, exists
}

func (sm *SandboxManager) ListSandboxes() []*SandboxInfo {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	result := make([]*SandboxInfo, 0, len(sm.sandboxes))
	for _, info := range sm.sandboxes {
		result = append(result, info)
	}
	return result
}

func (sm *SandboxManager) AcquireSandbox(sandboxID string) (*SandboxInfo, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	info, exists := sm.sandboxes[sandboxID]
	if !exists {
		return nil, fmt.Errorf("sandbox not found: %s", sandboxID)
	}

	if info.Status != SandboxStatusReady {
		return nil, fmt.Errorf("sandbox not ready: %s", info.Status)
	}

	if time.Now().After(info.ExpiresAt) {
		return nil, fmt.Errorf("sandbox has expired")
	}

	info.Status = SandboxStatusInUse
	return info, nil
}

func (sm *SandboxManager) ReleaseSandbox(sandboxID string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	info, exists := sm.sandboxes[sandboxID]
	if !exists {
		return fmt.Errorf("sandbox not found: %s", sandboxID)
	}

	info.Status = SandboxStatusReady
	return nil
}

func (sm *SandboxManager) DestroySandbox(ctx context.Context, sandboxID string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	info, exists := sm.sandboxes[sandboxID]
	if !exists {
		return fmt.Errorf("sandbox not found: %s", sandboxID)
	}

	info.Status = SandboxStatusCleaning

	if err := sm.cleanupResources(ctx, info); err != nil {
		info.Status = SandboxStatusFailed
		return fmt.Errorf("cleanup failed: %w", err)
	}

	info.Status = SandboxStatusDestroyed
	delete(sm.sandboxes, sandboxID)
	return nil
}

func (sm *SandboxManager) cleanupResources(ctx context.Context, info *SandboxInfo) error {
	for i := len(info.Resources) - 1; i >= 0; i-- {
		res := info.Resources[i]
		if err := sm.deleteResource(ctx, info.Provider, info.Region, res); err != nil {
			return fmt.Errorf("failed to delete %s %s: %w", res.ResourceType, res.ResourceID, err)
		}
	}
	return nil
}

func (sm *SandboxManager) deleteResource(ctx context.Context, provider, region string, res SandboxResource) error {
	return nil
}

func (sm *SandboxManager) GetExpiredSandboxes() []*SandboxInfo {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	now := time.Now()
	var expired []*SandboxInfo
	for _, info := range sm.sandboxes {
		if now.After(info.ExpiresAt) {
			expired = append(expired, info)
		}
	}
	return expired
}

func (sm *SandboxManager) GenerateIsolationPolicy(sandboxID string) map[string]interface{} {
	return map[string]interface{}{
		"sandbox_id": sandboxID,
		"isolation": map[string]interface{}{
			"vpc_isolation":    true,
			"subnet_isolation": true,
			"security_groups":  true,
			"iam_restrictions": true,
		},
		"allowed_actions": []string{
			"ec2:Describe*",
			"ec2:RunInstances",
			"ec2:TerminateInstances",
			"s3:GetObject",
			"s3:PutObject",
			"s3:ListBucket",
		},
		"denied_actions": []string{
			"*:Create*",
			"*:Delete*",
			"iam:*",
			"organizations:*",
		},
		"resource_tracking": map[string]interface{}{
			"tagging_required": true,
			"mandatory_tags": []string{
				"SandboxID",
				"Environment",
				"ExpiresAt",
			},
		},
	}
}

func (sm *SandboxManager) ValidateSandboxIsolation(ctx context.Context, sandboxID string) (bool, []string) {
	info, exists := sm.GetSandbox(sandboxID)
	if !exists {
		return false, []string{"Sandbox not found"}
	}

	var issues []string

	if info.VpcID == "" {
		issues = append(issues, "VPC not created")
	}

	if info.SubnetID == "" {
		issues = append(issues, "Subnet not created")
	}

	if info.SecurityGroupID == "" {
		issues = append(issues, "Security group not created")
	}

	if info.SubAccount == nil {
		issues = append(issues, "Sub-account not created")
	}

	return len(issues) == 0, issues
}

func GetSandboxConfigFromMigration(cfg *config.MigrationConfig) SandboxConfig {
	return SandboxConfig{
		Name:             "migration-drill",
		Provider:         cfg.Destination.Provider,
		Region:           cfg.Destination.Region,
		VpcCidr:          "10.200.0.0/16",
		SubnetCidr:       "10.200.1.0/24",
		EnableSubAccount: true,
		MaxDuration:      4 * time.Hour,
		Tags: map[string]string{
			"Environment": "Sandbox",
			"Purpose":     "MigrationDrill",
		},
	}
}
