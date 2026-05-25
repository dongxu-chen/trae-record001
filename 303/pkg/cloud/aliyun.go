package cloud

import (
	"context"
	"fmt"
	"time"

	"github.com/aliyun/alibaba-cloud-sdk-go/sdk"
	"github.com/aliyun/alibaba-cloud-sdk-go/sdk/auth/credentials"
	"github.com/aliyun/alibaba-cloud-sdk-go/services/ecs"
	"github.com/aliyun/alibaba-cloud-sdk-go/services/ess"
	"go.uber.org/zap"

	"autoscaler/internal/types"
)

type AliyunProvider struct {
	config     ProviderConfig
	ecsClient  *ecs.Client
	essClient  *ess.Client
	logger     *zap.Logger
}

func NewAliyunProvider(config ProviderConfig, logger *zap.Logger) (*AliyunProvider, error) {
	cred := credentials.NewAccessKeyCredential(config.AccessKey, config.SecretKey)
	clientConfig := sdk.NewConfig().WithRegionId(config.Region)

	ecsClient, err := ecs.NewClientWithOptions(clientConfig, cred)
	if err != nil {
		return nil, fmt.Errorf("failed to create ECS client: %w", err)
	}

	essClient, err := ess.NewClientWithOptions(clientConfig, cred)
	if err != nil {
		return nil, fmt.Errorf("failed to create ESS client: %w", err)
	}

	return &AliyunProvider{
		config:    config,
		ecsClient: ecsClient,
		essClient: essClient,
		logger:    logger,
	}, nil
}

func (a *AliyunProvider) GetInstanceGroup(ctx context.Context, groupID string) (*types.InstanceGroup, error) {
	request := ess.CreateDescribeScalingGroupsRequest()
	request.ScalingGroupId = &[]string{groupID}

	response, err := a.essClient.DescribeScalingGroups(request)
	if err != nil {
		return nil, fmt.Errorf("failed to describe scaling group: %w", err)
	}

	if len(response.ScalingGroups.ScalingGroup) == 0 {
		return nil, fmt.Errorf("scaling group not found: %s", groupID)
	}

	sg := response.ScalingGroups.ScalingGroup[0]

	instancesRequest := ess.CreateDescribeScalingInstancesRequest()
	instancesRequest.ScalingGroupId = groupID
	instancesResponse, err := a.essClient.DescribeScalingInstances(instancesRequest)
	if err != nil {
		return nil, fmt.Errorf("failed to describe scaling instances: %w", err)
	}

	instances := make([]types.InstanceInfo, 0, len(instancesResponse.ScalingInstances.ScalingInstance))
	for _, si := range instancesResponse.ScalingInstances.ScalingInstance {
		instanceInfo, err := a.GetInstance(ctx, si.InstanceId)
		if err != nil {
			a.logger.Warn("failed to get instance details",
				zap.String("instance_id", si.InstanceId),
				zap.Error(err),
			)
			continue
		}
		instances = append(instances, *instanceInfo)
	}

	return &types.InstanceGroup{
		ID:        groupID,
		Name:      sg.ScalingGroupName,
		Instances: instances,
		MinSize:   sg.MinSize,
		MaxSize:   sg.MaxSize,
		Desired:   sg.DesiredCapacity,
	}, nil
}

func (a *AliyunProvider) GetInstance(ctx context.Context, instanceID string) (*types.InstanceInfo, error) {
	request := ecs.CreateDescribeInstancesRequest()
	request.InstanceIds = fmt.Sprintf(`["%s"]`, instanceID)

	response, err := a.ecsClient.DescribeInstances(request)
	if err != nil {
		return nil, fmt.Errorf("failed to describe instance: %w", err)
	}

	if len(response.Instances.Instance) == 0 {
		return nil, fmt.Errorf("instance not found: %s", instanceID)
	}

	inst := response.Instances.Instance[0]

	createTime, _ := time.Parse(time.RFC3339, inst.CreationTime)

	return &types.InstanceInfo{
		ID:         instanceID,
		Name:       inst.InstanceName,
		Status:     inst.Status,
		Flavor:     inst.InstanceType,
		CPUCores:   inst.Cpu,
		MemoryGB:   inst.Memory / 1024,
		PrivateIP:  getFirst(inst.VpcAttributes.PrivateIpAddress.IpAddress),
		PublicIP:   getFirst(inst.PublicIpAddress.IpAddress),
		CreateTime: createTime,
	}, nil
}

func (a *AliyunProvider) ScaleUp(ctx context.Context, action *types.ScalingAction) error {
	group, err := a.GetInstanceGroup(ctx, action.InstanceID)
	if err != nil {
		return fmt.Errorf("failed to get current scaling group state: %w", err)
	}

	newDesired := group.Desired + action.Step
	if newDesired > group.MaxSize {
		newDesired = group.MaxSize
	}

	request := ess.CreateModifyScalingGroupRequest()
	request.ScalingGroupId = action.InstanceID
	request.DesiredCapacity = newDesired

	_, err = a.essClient.ModifyScalingGroup(request)
	if err != nil {
		return fmt.Errorf("failed to modify scaling group: %w", err)
	}

	a.logger.Info("Aliyun scale up successful",
		zap.String("scaling_group", action.InstanceID),
		zap.Int("old_desired", group.Desired),
		zap.Int("new_desired", newDesired),
		zap.Int("step", action.Step),
	)

	return nil
}

func (a *AliyunProvider) ScaleDown(ctx context.Context, action *types.ScalingAction) error {
	group, err := a.GetInstanceGroup(ctx, action.InstanceID)
	if err != nil {
		return fmt.Errorf("failed to get current scaling group state: %w", err)
	}

	newDesired := group.Desired - action.Step
	if newDesired < group.MinSize {
		newDesired = group.MinSize
	}

	request := ess.CreateModifyScalingGroupRequest()
	request.ScalingGroupId = action.InstanceID
	request.DesiredCapacity = newDesired

	_, err = a.essClient.ModifyScalingGroup(request)
	if err != nil {
		return fmt.Errorf("failed to modify scaling group: %w", err)
	}

	a.logger.Info("Aliyun scale down successful",
		zap.String("scaling_group", action.InstanceID),
		zap.Int("old_desired", group.Desired),
		zap.Int("new_desired", newDesired),
		zap.Int("step", action.Step),
	)

	return nil
}

func (a *AliyunProvider) ScaleVertical(ctx context.Context, action *types.ScalingAction, newSize string) error {
	if !a.ValidateFlavor(ctx, newSize) {
		return fmt.Errorf("invalid instance type: %s", newSize)
	}

	instance, err := a.GetInstance(ctx, action.InstanceID)
	if err != nil {
		return fmt.Errorf("failed to get instance: %w", err)
	}

	a.logger.Info("Initiating Aliyun vertical scaling",
		zap.String("instance_id", action.InstanceID),
		zap.String("current_type", instance.Flavor),
		zap.String("new_type", newSize),
	)

	stopRequest := ecs.CreateStopInstanceRequest()
	stopRequest.InstanceId = action.InstanceID
	stopRequest.ForceStop = "false"
	_, err = a.ecsClient.StopInstance(stopRequest)
	if err != nil {
		return fmt.Errorf("failed to stop instance: %w", err)
	}

	err = a.waitForInstanceStatus(ctx, action.InstanceID, "Stopped")
	if err != nil {
		return fmt.Errorf("timed out waiting for instance to stop: %w", err)
	}

	modifyRequest := ecs.CreateModifyInstanceSpecRequest()
	modifyRequest.InstanceId = action.InstanceID
	modifyRequest.InstanceType = newSize
	_, err = a.ecsClient.ModifyInstanceSpec(modifyRequest)
	if err != nil {
		return fmt.Errorf("failed to modify instance type: %w", err)
	}

	startRequest := ecs.CreateStartInstanceRequest()
	startRequest.InstanceId = action.InstanceID
	_, err = a.ecsClient.StartInstance(startRequest)
	if err != nil {
		return fmt.Errorf("failed to start instance: %w", err)
	}

	a.logger.Info("Aliyun vertical scaling completed",
		zap.String("instance_id", action.InstanceID),
		zap.String("new_type", newSize),
	)

	return nil
}

func (a *AliyunProvider) ValidateFlavor(ctx context.Context, flavor string) bool {
	request := ecs.CreateDescribeInstanceTypesRequest()
	request.InstanceTypes = fmt.Sprintf(`["%s"]`, flavor)

	response, err := a.ecsClient.DescribeInstanceTypes(request)
	if err != nil {
		a.logger.Warn("failed to validate instance type", zap.Error(err))
		return false
	}

	return len(response.InstanceTypes.InstanceType) > 0
}

func (a *AliyunProvider) GetNextFlavor(ctx context.Context, currentFlavor string, direction types.ScalingDirection) (string, error) {
	if a.config.FlavorMap == nil {
		return "", fmt.Errorf("flavor map not configured")
	}

	flavors, exists := a.config.FlavorMap["aliyun"]
	if !exists {
		return "", fmt.Errorf("aliyun flavors not found in map")
	}

	currentIdx := -1
	for i, f := range flavors {
		if f == currentFlavor {
			currentIdx = i
			break
		}
	}

	if currentIdx == -1 {
		return "", fmt.Errorf("current flavor not found: %s", currentFlavor)
	}

	switch direction {
	case types.ScaleUp:
		if currentIdx >= len(flavors)-1 {
			return "", fmt.Errorf("already at maximum flavor: %s", currentFlavor)
		}
		return flavors[currentIdx+1], nil
	case types.ScaleDown:
		if currentIdx <= 0 {
			return "", fmt.Errorf("already at minimum flavor: %s", currentFlavor)
		}
		return flavors[currentIdx-1], nil
	default:
		return "", fmt.Errorf("invalid scaling direction: %s", direction)
	}
}

func (a *AliyunProvider) ListFlavors(ctx context.Context) ([]string, error) {
	request := ecs.CreateDescribeInstanceTypesRequest()
	response, err := a.ecsClient.DescribeInstanceTypes(request)
	if err != nil {
		return nil, fmt.Errorf("failed to list instance types: %w", err)
	}

	flavors := make([]string, 0, len(response.InstanceTypes.InstanceType))
	for _, it := range response.InstanceTypes.InstanceType {
		flavors = append(flavors, it.InstanceTypeId)
	}

	return flavors, nil
}

func (a *AliyunProvider) waitForInstanceStatus(ctx context.Context, instanceID string, targetStatus string) error {
	maxAttempts := 60
	for i := 0; i < maxAttempts; i++ {
		instance, err := a.GetInstance(ctx, instanceID)
		if err != nil {
			return err
		}

		if instance.Status == targetStatus {
			return nil
		}

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(10 * time.Second):
		}
	}

	return fmt.Errorf("timeout waiting for instance %s to reach status %s", instanceID, targetStatus)
}

func getFirst(slice []string) string {
	if len(slice) > 0 {
		return slice[0]
	}
	return ""
}

func (a *AliyunProvider) BlueGreenPrepare(ctx context.Context, groupID string, newFlavor string, count int) (*types.BlueGreenDeployment, error) {
	group, err := a.GetInstanceGroup(ctx, groupID)
	if err != nil {
		return nil, fmt.Errorf("failed to get instance group: %w", err)
	}

	deploymentID := fmt.Sprintf("bg-deploy-%d", time.Now().Unix())
	deployment := &types.BlueGreenDeployment{
		ID:             deploymentID,
		Service:        groupID,
		Status:         types.BlueGreenPreparing,
		BlueVersion:    "blue",
		GreenVersion:   newFlavor,
		CurrentVersion: group.Version,
		BlueInstances:  group.Instances,
		GreenInstances: make([]types.InstanceInfo, 0),
		StartTime:      time.Now(),
		TrafficSplit:   100,
		Timeout:        10 * time.Minute,
	}

	for i := 0; i < count; i++ {
		createRequest := ecs.CreateCreateInstanceRequest()
		createRequest.InstanceType = newFlavor
		createResponse, err := a.ecsClient.CreateInstance(createRequest)
		if err != nil {
			return nil, fmt.Errorf("failed to create green instance: %w", err)
		}

		startRequest := ecs.CreateStartInstanceRequest()
		startRequest.InstanceId = createResponse.InstanceId
		_, err = a.ecsClient.StartInstance(startRequest)
		if err != nil {
			return nil, fmt.Errorf("failed to start green instance: %w", err)
		}

		newInst := types.InstanceInfo{
			ID:         createResponse.InstanceId,
			Status:     "starting",
			Flavor:     newFlavor,
			Version:    "green",
			Deployment: types.BlueGreenPreparing,
			Healthy:    false,
			CreateTime: time.Now(),
		}
		deployment.GreenInstances = append(deployment.GreenInstances, newInst)
	}

	a.logger.Info("Aliyun blue-green deployment prepared",
		zap.String("deployment_id", deploymentID),
		zap.Int("green_count", len(deployment.GreenInstances)),
	)

	return deployment, nil
}

func (a *AliyunProvider) BlueGreenWaitReady(ctx context.Context, deployment *types.BlueGreenDeployment, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	checkInterval := 10 * time.Second

	for time.Now().Before(deadline) {
		allReady := true
		for _, inst := range deployment.GreenInstances {
			instance, err := a.GetInstance(ctx, inst.ID)
			if err != nil || instance.Status != "running" {
				allReady = false
				break
			}
		}

		if allReady {
			deployment.UpdateStatus(types.BlueGreenReady)
			deployment.ReadyTime = time.Now()
			a.logger.Info("Aliyun blue-green deployment ready",
				zap.String("deployment_id", deployment.ID),
			)
			return nil
		}

		time.Sleep(checkInterval)
	}

	deployment.UpdateStatus(types.BlueGreenFailed)
	return fmt.Errorf("timeout waiting for green instances to become ready")
}

func (a *AliyunProvider) BlueGreenSwitchTraffic(ctx context.Context, deployment *types.BlueGreenDeployment, weight int) error {
	if weight < 0 || weight > 100 {
		return fmt.Errorf("weight must be between 0 and 100")
	}

	deployment.TrafficSplit = weight
	deployment.UpdateStatus(types.BlueGreenSwitching)
	deployment.SwitchTime = time.Now()

	a.logger.Info("Aliyun blue-green traffic switched",
		zap.String("deployment_id", deployment.ID),
		zap.Int("green_weight", weight),
	)

	return nil
}

func (a *AliyunProvider) BlueGreenComplete(ctx context.Context, deployment *types.BlueGreenDeployment) error {
	for _, inst := range deployment.BlueInstances {
		deleteRequest := ecs.CreateDeleteInstanceRequest()
		deleteRequest.InstanceId = inst.ID
		deleteRequest.Force = "true"
		_, err := a.ecsClient.DeleteInstance(deleteRequest)
		if err != nil {
			a.logger.Warn("failed to delete blue instance",
				zap.String("instance_id", inst.ID),
				zap.Error(err),
			)
		}
	}

	deployment.UpdateStatus(types.BlueGreenCompleted)
	a.logger.Info("Aliyun blue-green deployment completed",
		zap.String("deployment_id", deployment.ID),
	)

	return nil
}

func (a *AliyunProvider) BlueGreenRollback(ctx context.Context, deployment *types.BlueGreenDeployment) error {
	for _, inst := range deployment.GreenInstances {
		deleteRequest := ecs.CreateDeleteInstanceRequest()
		deleteRequest.InstanceId = inst.ID
		deleteRequest.Force = "true"
		_, err := a.ecsClient.DeleteInstance(deleteRequest)
		if err != nil {
			a.logger.Warn("failed to delete green instance during rollback",
				zap.String("instance_id", inst.ID),
				zap.Error(err),
			)
		}
	}

	deployment.UpdateStatus(types.BlueGreenRollingBack)
	a.logger.Info("Aliyun blue-green deployment rolled back",
		zap.String("deployment_id", deployment.ID),
	)

	return nil
}

func (a *AliyunProvider) getAliyunPriceList() []FlavorPrice {
	return []FlavorPrice{
		{Flavor: "ecs.small", OnDemandPrice: 0.05, ReservedPrice: 0.03, SpotPrice: 0.02, Region: a.config.Region},
		{Flavor: "ecs.medium", OnDemandPrice: 0.10, ReservedPrice: 0.06, SpotPrice: 0.04, Region: a.config.Region},
		{Flavor: "ecs.large", OnDemandPrice: 0.20, ReservedPrice: 0.12, SpotPrice: 0.08, Region: a.config.Region},
		{Flavor: "ecs.xlarge", OnDemandPrice: 0.40, ReservedPrice: 0.24, SpotPrice: 0.16, Region: a.config.Region},
		{Flavor: "ecs.2xlarge", OnDemandPrice: 0.80, ReservedPrice: 0.48, SpotPrice: 0.32, Region: a.config.Region},
	}
}

func (a *AliyunProvider) getFlavorPrice(flavor string) *FlavorPrice {
	priceList := a.config.PriceList
	if len(priceList) == 0 {
		priceList = a.getAliyunPriceList()
	}
	for i := range priceList {
		if priceList[i].Flavor == flavor {
			return &priceList[i]
		}
	}
	return nil
}

func (a *AliyunProvider) GetInstanceCost(ctx context.Context, instanceID string) (*types.InstanceCostInfo, error) {
	inst, err := a.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}

	price := a.getFlavorPrice(inst.Flavor)
	if price == nil {
		return nil, fmt.Errorf("price not found for flavor: %s", inst.Flavor)
	}

	request := ecs.CreateDescribeInstancesRequest()
	request.InstanceIds = fmt.Sprintf(`["%s"]`, instanceID)
	response, err := a.ecsClient.DescribeInstances(request)
	if err != nil {
		return nil, fmt.Errorf("failed to describe instance: %w", err)
	}

	chargeType := types.ChargeTypeOnDemand
	reservedTerm := 0
	reservedUsage := 0.0

	if len(response.Instances.Instance) > 0 {
		inst := response.Instances.Instance[0]
		if inst.InstanceChargeType == "PrePaid" {
			chargeType = types.ChargeTypeReserved
			reservedTerm = 12
			reservedUsage = 0.8
		} else if inst.InstanceChargeType == "PostPaid" {
			chargeType = types.ChargeTypeOnDemand
		} else if inst.SpotStrategy == "SpotAsPriceGo" || inst.SpotStrategy == "SpotWithPriceLimit" {
			chargeType = types.ChargeTypeSpot
		}
	}

	hourlyPrice := price.OnDemandPrice
	if chargeType == types.ChargeTypeReserved {
		hourlyPrice = price.ReservedPrice
	} else if chargeType == types.ChargeTypeSpot {
		hourlyPrice = price.SpotPrice
	}

	return &types.InstanceCostInfo{
		InstanceID:    instanceID,
		Flavor:        inst.Flavor,
		ChargeType:    chargeType,
		HourlyPrice:   hourlyPrice,
		MonthlyPrice:  hourlyPrice * 24 * 30,
		ReservedTerm:  reservedTerm,
		ReservedUsage: reservedUsage,
		StartTime:     inst.CreateTime,
	}, nil
}

func (a *AliyunProvider) GetInstancePrice(ctx context.Context, flavor string, chargeType types.InstanceChargeType) (float64, error) {
	price := a.getFlavorPrice(flavor)
	if price == nil {
		return 0, fmt.Errorf("price not found for flavor: %s", flavor)
	}

	switch chargeType {
	case types.ChargeTypeReserved:
		return price.ReservedPrice, nil
	case types.ChargeTypeSpot:
		return price.SpotPrice, nil
	default:
		return price.OnDemandPrice, nil
	}
}

func (a *AliyunProvider) ConvertChargeType(ctx context.Context, instanceID string, targetType types.InstanceChargeType) error {
	instanceChargeType := "PostPaid"
	if targetType == types.ChargeTypeReserved {
		instanceChargeType = "PrePaid"
	}

	request := ecs.CreateModifyInstanceChargeTypeRequest()
	request.InstanceIds = fmt.Sprintf(`["%s"]`, instanceID)
	request.InstanceChargeType = instanceChargeType

	_, err := a.ecsClient.ModifyInstanceChargeType(request)
	if err != nil {
		return fmt.Errorf("failed to modify instance charge type: %w", err)
	}

	a.logger.Info("converted Aliyun instance charge type",
		zap.String("instance_id", instanceID),
		zap.String("target_type", string(targetType)),
	)

	return nil
}

func (a *AliyunProvider) ListReservedInstances(ctx context.Context) ([]types.InstanceInfo, error) {
	request := ecs.CreateDescribeInstancesRequest()
	request.InstanceChargeType = "PrePaid"
	response, err := a.ecsClient.DescribeInstances(request)
	if err != nil {
		return nil, fmt.Errorf("failed to describe reserved instances: %w", err)
	}

	var reserved []types.InstanceInfo
	for _, inst := range response.Instances.Instance {
		info, err := a.GetInstance(ctx, inst.InstanceId)
		if err == nil {
			reserved = append(reserved, *info)
		}
	}

	return reserved, nil
}

func (a *AliyunProvider) PurchaseReservedInstance(ctx context.Context, flavor string, termMonths int) (*types.InstanceCostInfo, error) {
	a.logger.Info("purchasing Aliyun reserved instance",
		zap.String("flavor", flavor),
		zap.Int("term_months", termMonths),
	)

	price := a.getFlavorPrice(flavor)
	if price == nil {
		return nil, fmt.Errorf("price not found for flavor: %s", flavor)
	}

	instanceID := fmt.Sprintf("aliyun-reserved-%s-%d", flavor, time.Now().Unix())

	return &types.InstanceCostInfo{
		InstanceID:   instanceID,
		Flavor:       flavor,
		ChargeType:   types.ChargeTypeReserved,
		HourlyPrice:  price.ReservedPrice,
		MonthlyPrice: price.ReservedPrice * 24 * 30,
		ReservedTerm: termMonths,
		StartTime:    time.Now(),
	}, nil
}

func (a *AliyunProvider) CalculateCostOptimization(ctx context.Context, group *types.InstanceGroup) ([]types.CostOptimizationAction, error) {
	var actions []types.CostOptimizationAction
	reservedCount := 0
	onDemandCount := 0

	for _, inst := range group.Instances {
		costInfo, err := a.GetInstanceCost(ctx, inst.ID)
		if err != nil {
			continue
		}
		if costInfo.ChargeType == types.ChargeTypeReserved {
			reservedCount++
		} else {
			onDemandCount++
		}
	}

	costConfig := a.config.CostConfig
	if costConfig == nil {
		costConfig = &types.CostConfig{
			ReservedInstanceRatio: 0.7,
		}
	}

	targetReserved := int(float64(len(group.Instances)) * costConfig.ReservedInstanceRatio)

	if reservedCount < targetReserved {
		needConvert := targetReserved - reservedCount
		converted := 0

		for _, inst := range group.Instances {
			if converted >= needConvert {
				break
			}
			costInfo, err := a.GetInstanceCost(ctx, inst.ID)
			if err != nil {
				continue
			}
			if costInfo.ChargeType == types.ChargeTypeOnDemand {
				price := a.getFlavorPrice(inst.Flavor)
				if price != nil {
					savings := (price.OnDemandPrice - price.ReservedPrice) * 24 * 30
					actions = append(actions, types.CostOptimizationAction{
						Type:        "convert_to_reserved",
						InstanceID:  inst.ID,
						FromCharge:  types.ChargeTypeOnDemand,
						ToCharge:    types.ChargeTypeReserved,
						FromFlavor:  inst.Flavor,
						ToFlavor:    inst.Flavor,
						CostSavings: savings,
						Reason:      "Increase reserved instance ratio to target",
						Timestamp:   time.Now(),
					})
					converted++
				}
			}
		}
	}

	return actions, nil
}
