package cloud

import (
	"context"
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/autoscaling"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	"github.com/aws/aws-sdk-go-v2/service/ec2/types"
	"go.uber.org/zap"

	"autoscaler/internal/types"
)

type AWSProvider struct {
	config     ProviderConfig
	awsConfig  aws.Config
	asgClient  *autoscaling.Client
	ec2Client  *ec2.Client
	logger     *zap.Logger
}

func NewAWSProvider(config ProviderConfig, logger *zap.Logger) (*AWSProvider, error) {
	cfg, err := config.LoadDefaultConfig(context.TODO(),
		config.WithRegion(config.Region),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return &AWSProvider{
		config:    config,
		awsConfig: cfg,
		asgClient: autoscaling.NewFromConfig(cfg),
		ec2Client: ec2.NewFromConfig(cfg),
		logger:    logger,
	}, nil
}

func (a *AWSProvider) GetInstanceGroup(ctx context.Context, groupID string) (*types.InstanceGroup, error) {
	input := &autoscaling.DescribeAutoScalingGroupsInput{
		AutoScalingGroupNames: []string{groupID},
	}

	output, err := a.asgClient.DescribeAutoScalingGroups(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to describe ASG: %w", err)
	}

	if len(output.AutoScalingGroups) == 0 {
		return nil, fmt.Errorf("ASG not found: %s", groupID)
	}

	asg := output.AutoScalingGroups[0]

	instances := make([]types.InstanceInfo, 0, len(asg.Instances))
	for _, inst := range asg.Instances {
		if inst.InstanceId == nil {
			continue
		}

		instanceInfo, err := a.GetInstance(ctx, *inst.InstanceId)
		if err != nil {
			a.logger.Warn("failed to get instance details",
				zap.String("instance_id", *inst.InstanceId),
				zap.Error(err),
			)
			continue
		}
		instances = append(instances, *instanceInfo)
	}

	return &types.InstanceGroup{
		ID:        groupID,
		Name:      *asg.AutoScalingGroupName,
		Instances: instances,
		MinSize:   int(asg.MinSize),
		MaxSize:   int(asg.MaxSize),
		Desired:   int(asg.DesiredCapacity),
	}, nil
}

func (a *AWSProvider) GetInstance(ctx context.Context, instanceID string) (*types.InstanceInfo, error) {
	input := &ec2.DescribeInstancesInput{
		InstanceIds: []string{instanceID},
	}

	output, err := a.ec2Client.DescribeInstances(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to describe instance: %w", err)
	}

	if len(output.Reservations) == 0 || len(output.Reservations[0].Instances) == 0 {
		return nil, fmt.Errorf("instance not found: %s", instanceID)
	}

	inst := output.Reservations[0].Instances[0]

	cores := 0
	if inst.CpuOptions != nil && inst.CpuOptions.CoreCount != nil {
		cores = int(*inst.CpuOptions.CoreCount)
	}

	memGB := 0
	if inst.MemoryInfo != nil && inst.MemoryInfo.SizeInMiB != nil {
		memGB = int(*inst.MemoryInfo.SizeInMiB / 1024)
	}

	privateIP := ""
	if inst.PrivateIpAddress != nil {
		privateIP = *inst.PrivateIpAddress
	}

	publicIP := ""
	if inst.PublicIpAddress != nil {
		publicIP = *inst.PublicIpAddress
	}

	name := ""
	for _, tag := range inst.Tags {
		if tag.Key != nil && *tag.Key == "Name" {
			name = *tag.Value
			break
		}
	}

	return &types.InstanceInfo{
		ID:         instanceID,
		Name:       name,
		Status:     string(inst.State.Name),
		Flavor:     string(inst.InstanceType),
		CPUCores:   cores,
		MemoryGB:   memGB,
		PrivateIP:  privateIP,
		PublicIP:   publicIP,
		CreateTime: *inst.LaunchTime,
	}, nil
}

func (a *AWSProvider) ScaleUp(ctx context.Context, action *types.ScalingAction) error {
	group, err := a.GetInstanceGroup(ctx, action.InstanceID)
	if err != nil {
		return fmt.Errorf("failed to get current ASG state: %w", err)
	}

	newDesired := group.Desired + action.Step
	if newDesired > group.MaxSize {
		newDesired = group.MaxSize
	}

	input := &autoscaling.SetDesiredCapacityInput{
		AutoScalingGroupName: aws.String(action.InstanceID),
		DesiredCapacity:      aws.Int32(int32(newDesired)),
		HonorCooldown:        aws.Bool(true),
	}

	_, err = a.asgClient.SetDesiredCapacity(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to set desired capacity: %w", err)
	}

	a.logger.Info("AWS scale up successful",
		zap.String("asg", action.InstanceID),
		zap.Int("old_desired", group.Desired),
		zap.Int("new_desired", newDesired),
		zap.Int("step", action.Step),
	)

	return nil
}

func (a *AWSProvider) ScaleDown(ctx context.Context, action *types.ScalingAction) error {
	group, err := a.GetInstanceGroup(ctx, action.InstanceID)
	if err != nil {
		return fmt.Errorf("failed to get current ASG state: %w", err)
	}

	newDesired := group.Desired - action.Step
	if newDesired < group.MinSize {
		newDesired = group.MinSize
	}

	input := &autoscaling.SetDesiredCapacityInput{
		AutoScalingGroupName: aws.String(action.InstanceID),
		DesiredCapacity:      aws.Int32(int32(newDesired)),
		HonorCooldown:        aws.Bool(true),
	}

	_, err = a.asgClient.SetDesiredCapacity(ctx, input)
	if err != nil {
		return fmt.Errorf("failed to set desired capacity: %w", err)
	}

	a.logger.Info("AWS scale down successful",
		zap.String("asg", action.InstanceID),
		zap.Int("old_desired", group.Desired),
		zap.Int("new_desired", newDesired),
		zap.Int("step", action.Step),
	)

	return nil
}

func (a *AWSProvider) ScaleVertical(ctx context.Context, action *types.ScalingAction, newSize string) error {
	if !a.ValidateFlavor(ctx, newSize) {
		return fmt.Errorf("invalid instance type: %s", newSize)
	}

	instance, err := a.GetInstance(ctx, action.InstanceID)
	if err != nil {
		return fmt.Errorf("failed to get instance: %w", err)
	}

	a.logger.Info("Initiating AWS vertical scaling",
		zap.String("instance_id", action.InstanceID),
		zap.String("current_type", instance.Flavor),
		zap.String("new_type", newSize),
	)

	stopInput := &ec2.StopInstancesInput{
		InstanceIds: []string{action.InstanceID},
	}
	_, err = a.ec2Client.StopInstances(ctx, stopInput)
	if err != nil {
		return fmt.Errorf("failed to stop instance: %w", err)
	}

	waiter := ec2.NewInstanceStoppedWaiter(a.ec2Client)
	err = waiter.Wait(ctx, &ec2.DescribeInstancesInput{
		InstanceIds: []string{action.InstanceID},
	}, 5*60)
	if err != nil {
		return fmt.Errorf("timed out waiting for instance to stop: %w", err)
	}

	modifyInput := &ec2.ModifyInstanceAttributeInput{
		InstanceId: aws.String(action.InstanceID),
		InstanceType: &types.AttributeValue{
			Value: aws.String(newSize),
		},
	}
	_, err = a.ec2Client.ModifyInstanceAttribute(ctx, modifyInput)
	if err != nil {
		return fmt.Errorf("failed to modify instance type: %w", err)
	}

	startInput := &ec2.StartInstancesInput{
		InstanceIds: []string{action.InstanceID},
	}
	_, err = a.ec2Client.StartInstances(ctx, startInput)
	if err != nil {
		return fmt.Errorf("failed to start instance: %w", err)
	}

	a.logger.Info("AWS vertical scaling completed",
		zap.String("instance_id", action.InstanceID),
		zap.String("new_type", newSize),
	)

	return nil
}

func (a *AWSProvider) ValidateFlavor(ctx context.Context, flavor string) bool {
	input := &ec2.DescribeInstanceTypesInput{
		InstanceTypes: []types.InstanceType{types.InstanceType(flavor)},
	}

	output, err := a.ec2Client.DescribeInstanceTypes(ctx, input)
	if err != nil {
		a.logger.Warn("failed to validate instance type", zap.Error(err))
		return false
	}

	return len(output.InstanceTypes) > 0
}

func (a *AWSProvider) GetNextFlavor(ctx context.Context, currentFlavor string, direction types.ScalingDirection) (string, error) {
	if a.config.FlavorMap == nil {
		return "", fmt.Errorf("flavor map not configured")
	}

	flavors, exists := a.config.FlavorMap["aws"]
	if !exists {
		return "", fmt.Errorf("aws flavors not found in map")
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

func (a *AWSProvider) ListFlavors(ctx context.Context) ([]string, error) {
	input := &ec2.DescribeInstanceTypesInput{}
	var flavors []string

	paginator := ec2.NewDescribeInstanceTypesPaginator(a.ec2Client, input)
	for paginator.HasMorePages() {
		output, err := paginator.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to list instance types: %w", err)
		}

		for _, it := range output.InstanceTypes {
			flavors = append(flavors, string(it.InstanceType))
		}
	}

	return flavors, nil
}

func (a *AWSProvider) BlueGreenPrepare(ctx context.Context, groupID string, newFlavor string, count int) (*types.BlueGreenDeployment, error) {
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
		runInput := &ec2.RunInstancesInput{
			InstanceType: types.InstanceType(newFlavor),
			MinCount:     aws.Int32(1),
			MaxCount:     aws.Int32(1),
		}

		runOutput, err := a.ec2Client.RunInstances(ctx, runInput)
		if err != nil {
			return nil, fmt.Errorf("failed to create green instance: %w", err)
		}

		if len(runOutput.Instances) > 0 {
			inst := runOutput.Instances[0]
			newInst := types.InstanceInfo{
				ID:         *inst.InstanceId,
				Status:     string(inst.State.Name),
				Flavor:     string(inst.InstanceType),
				Version:    "green",
				Deployment: types.BlueGreenPreparing,
				Healthy:    false,
				CreateTime: *inst.LaunchTime,
			}
			deployment.GreenInstances = append(deployment.GreenInstances, newInst)
		}
	}

	a.logger.Info("AWS blue-green deployment prepared",
		zap.String("deployment_id", deploymentID),
		zap.Int("green_count", len(deployment.GreenInstances)),
	)

	return deployment, nil
}

func (a *AWSProvider) BlueGreenWaitReady(ctx context.Context, deployment *types.BlueGreenDeployment, timeout time.Duration) error {
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
			a.logger.Info("AWS blue-green deployment ready",
				zap.String("deployment_id", deployment.ID),
			)
			return nil
		}

		time.Sleep(checkInterval)
	}

	deployment.UpdateStatus(types.BlueGreenFailed)
	return fmt.Errorf("timeout waiting for green instances to become ready")
}

func (a *AWSProvider) BlueGreenSwitchTraffic(ctx context.Context, deployment *types.BlueGreenDeployment, weight int) error {
	if weight < 0 || weight > 100 {
		return fmt.Errorf("weight must be between 0 and 100")
	}

	deployment.TrafficSplit = weight
	deployment.UpdateStatus(types.BlueGreenSwitching)
	deployment.SwitchTime = time.Now()

	a.logger.Info("AWS blue-green traffic switched",
		zap.String("deployment_id", deployment.ID),
		zap.Int("green_weight", weight),
	)

	return nil
}

func (a *AWSProvider) BlueGreenComplete(ctx context.Context, deployment *types.BlueGreenDeployment) error {
	var toDelete []string
	for _, inst := range deployment.BlueInstances {
		toDelete = append(toDelete, inst.ID)
	}

	if len(toDelete) > 0 {
		input := &ec2.TerminateInstancesInput{
			InstanceIds: toDelete,
		}
		_, err := a.ec2Client.TerminateInstances(ctx, input)
		if err != nil {
			return fmt.Errorf("failed to terminate blue instances: %w", err)
		}
	}

	deployment.UpdateStatus(types.BlueGreenCompleted)
	a.logger.Info("AWS blue-green deployment completed",
		zap.String("deployment_id", deployment.ID),
	)

	return nil
}

func (a *AWSProvider) BlueGreenRollback(ctx context.Context, deployment *types.BlueGreenDeployment) error {
	var toDelete []string
	for _, inst := range deployment.GreenInstances {
		toDelete = append(toDelete, inst.ID)
	}

	if len(toDelete) > 0 {
		input := &ec2.TerminateInstancesInput{
			InstanceIds: toDelete,
		}
		_, err := a.ec2Client.TerminateInstances(ctx, input)
		if err != nil {
			return fmt.Errorf("failed to terminate green instances: %w", err)
		}
	}

	deployment.UpdateStatus(types.BlueGreenRollingBack)
	a.logger.Info("AWS blue-green deployment rolled back",
		zap.String("deployment_id", deployment.ID),
	)

	return nil
}

func (a *AWSProvider) getAWSPriceList() []FlavorPrice {
	return []FlavorPrice{
		{Flavor: "t3.small", OnDemandPrice: 0.02, ReservedPrice: 0.01, SpotPrice: 0.007, Region: a.config.Region},
		{Flavor: "t3.medium", OnDemandPrice: 0.04, ReservedPrice: 0.02, SpotPrice: 0.014, Region: a.config.Region},
		{Flavor: "t3.large", OnDemandPrice: 0.08, ReservedPrice: 0.04, SpotPrice: 0.028, Region: a.config.Region},
		{Flavor: "t3.xlarge", OnDemandPrice: 0.17, ReservedPrice: 0.08, SpotPrice: 0.056, Region: a.config.Region},
		{Flavor: "t3.2xlarge", OnDemandPrice: 0.33, ReservedPrice: 0.17, SpotPrice: 0.112, Region: a.config.Region},
	}
}

func (a *AWSProvider) getFlavorPrice(flavor string) *FlavorPrice {
	priceList := a.config.PriceList
	if len(priceList) == 0 {
		priceList = a.getAWSPriceList()
	}
	for i := range priceList {
		if priceList[i].Flavor == flavor {
			return &priceList[i]
		}
	}
	return nil
}

func (a *AWSProvider) GetInstanceCost(ctx context.Context, instanceID string) (*types.InstanceCostInfo, error) {
	inst, err := a.GetInstance(ctx, instanceID)
	if err != nil {
		return nil, err
	}

	price := a.getFlavorPrice(inst.Flavor)
	if price == nil {
		return nil, fmt.Errorf("price not found for flavor: %s", inst.Flavor)
	}

	input := &ec2.DescribeInstancesInput{
		InstanceIds: []string{instanceID},
	}
	output, err := a.ec2Client.DescribeInstances(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to describe instance: %w", err)
	}

	chargeType := types.ChargeTypeOnDemand
	reservedTerm := 0
	reservedUsage := 0.0

	if len(output.Reservations) > 0 {
		res := output.Reservations[0]
		if len(res.Instances) > 0 {
			inst := res.Instances[0]
			if inst.InstanceLifecycle == types.InstanceLifecycleSpot {
				chargeType = types.ChargeTypeSpot
			} else if res.ReservationId != nil {
				chargeType = types.ChargeTypeReserved
				reservedTerm = 12
				reservedUsage = 0.8
			}
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

func (a *AWSProvider) GetInstancePrice(ctx context.Context, flavor string, chargeType types.InstanceChargeType) (float64, error) {
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

func (a *AWSProvider) ConvertChargeType(ctx context.Context, instanceID string, targetType types.InstanceChargeType) error {
	a.logger.Info("converting AWS instance charge type",
		zap.String("instance_id", instanceID),
		zap.String("target_type", string(targetType)),
	)
	return fmt.Errorf("charge type conversion requires AWS Marketplace or API integration")
}

func (a *AWSProvider) ListReservedInstances(ctx context.Context) ([]types.InstanceInfo, error) {
	input := &ec2.DescribeInstancesInput{}
	var reserved []types.InstanceInfo

	paginator := ec2.NewDescribeInstancesPaginator(a.ec2Client, input)
	for paginator.HasMorePages() {
		output, err := paginator.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to describe instances: %w", err)
		}

		for _, res := range output.Reservations {
			if res.ReservationId != nil && len(res.Instances) > 0 {
				for _, inst := range res.Instances {
					if inst.InstanceLifecycle != types.InstanceLifecycleSpot {
						info, err := a.GetInstance(ctx, *inst.InstanceId)
						if err == nil {
							reserved = append(reserved, *info)
						}
					}
				}
			}
		}
	}

	return reserved, nil
}

func (a *AWSProvider) PurchaseReservedInstance(ctx context.Context, flavor string, termMonths int) (*types.InstanceCostInfo, error) {
	a.logger.Info("purchasing AWS reserved instance",
		zap.String("flavor", flavor),
		zap.Int("term_months", termMonths),
	)

	price := a.getFlavorPrice(flavor)
	if price == nil {
		return nil, fmt.Errorf("price not found for flavor: %s", flavor)
	}

	instanceID := fmt.Sprintf("aws-reserved-%s-%d", flavor, time.Now().Unix())

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

func (a *AWSProvider) CalculateCostOptimization(ctx context.Context, group *types.InstanceGroup) ([]types.CostOptimizationAction, error) {
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
