package cloud

import (
	"context"
	"fmt"
	"time"

	"autoscaler/internal/types"
	"go.uber.org/zap"
)

type CloudProvider interface {
	GetInstanceGroup(ctx context.Context, groupID string) (*types.InstanceGroup, error)
	GetInstance(ctx context.Context, instanceID string) (*types.InstanceInfo, error)
	ScaleUp(ctx context.Context, action *types.ScalingAction) error
	ScaleDown(ctx context.Context, action *types.ScalingAction) error
	ScaleVertical(ctx context.Context, action *types.ScalingAction, newSize string) error
	ValidateFlavor(ctx context.Context, flavor string) bool
	GetNextFlavor(ctx context.Context, currentFlavor string, direction types.ScalingDirection) (string, error)
	ListFlavors(ctx context.Context) ([]string, error)

	BlueGreenPrepare(ctx context.Context, groupID string, newFlavor string, count int) (*types.BlueGreenDeployment, error)
	BlueGreenWaitReady(ctx context.Context, deployment *types.BlueGreenDeployment, timeout time.Duration) error
	BlueGreenSwitchTraffic(ctx context.Context, deployment *types.BlueGreenDeployment, weight int) error
	BlueGreenComplete(ctx context.Context, deployment *types.BlueGreenDeployment) error
	BlueGreenRollback(ctx context.Context, deployment *types.BlueGreenDeployment) error

	GetInstanceCost(ctx context.Context, instanceID string) (*types.InstanceCostInfo, error)
	GetInstancePrice(ctx context.Context, flavor string, chargeType types.InstanceChargeType) (float64, error)
	ConvertChargeType(ctx context.Context, instanceID string, targetType types.InstanceChargeType) error
	ListReservedInstances(ctx context.Context) ([]types.InstanceInfo, error)
	PurchaseReservedInstance(ctx context.Context, flavor string, termMonths int) (*types.InstanceCostInfo, error)
	CalculateCostOptimization(ctx context.Context, group *types.InstanceGroup) ([]types.CostOptimizationAction, error)
}

type FlavorPrice struct {
	Flavor         string
	OnDemandPrice  float64
	ReservedPrice  float64
	SpotPrice      float64
	Region         string
}

type ProviderConfig struct {
	Type         types.CloudProvider
	Region       string
	AccessKey    string
	SecretKey    string
	AssumeRole   string
	FlavorMap    map[string][]string
	MockData     *MockProviderConfig
	PriceList    []FlavorPrice
	CostConfig   *types.CostConfig
}

type MockProviderConfig struct {
	Instances     []types.InstanceInfo
	InstanceGroup *types.InstanceGroup
	Flavors       []string
}

func NewCloudProvider(config ProviderConfig, logger *zap.Logger) (CloudProvider, error) {
	switch config.Type {
	case types.ProviderAWS:
		return NewAWSProvider(config, logger)
	case types.ProviderAliyun:
		return NewAliyunProvider(config, logger)
	case types.ProviderMock:
		return NewMockProvider(config, logger)
	default:
		return nil, fmt.Errorf("unsupported cloud provider: %s", config.Type)
	}
}
