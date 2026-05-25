package cloud

import (
	"context"
	"fmt"
	"sync"
	"time"

	"autoscaler/internal/types"
	"go.uber.org/zap"
)

type MockProvider struct {
	config         ProviderConfig
	instances      map[string]*types.InstanceInfo
	group          *types.InstanceGroup
	flavors        []string
	deployments    map[string]*types.BlueGreenDeployment
	mu             sync.RWMutex
	logger         *zap.Logger
}

func NewMockProvider(config ProviderConfig, logger *zap.Logger) (*MockProvider, error) {
	mockConfig := config.MockData
	if mockConfig == nil {
		mockConfig = &MockProviderConfig{
			Flavors: []string{"ecs.small", "ecs.medium", "ecs.large", "ecs.xlarge", "ecs.2xlarge"},
		}
	}

	instances := make(map[string]*types.InstanceInfo)
	if mockConfig.Instances != nil {
		for i := range mockConfig.Instances {
			inst := &mockConfig.Instances[i]
			inst.Version = "blue"
			inst.Deployment = types.BlueGreenIdle
			inst.Healthy = true
			if inst.ChargeType == "" {
				if i < 2 {
					inst.ChargeType = types.ChargeTypeReserved
				} else {
					inst.ChargeType = types.ChargeTypeOnDemand
				}
			}
			instances[inst.ID] = inst
		}
	}

	group := mockConfig.InstanceGroup
	if group == nil {
		group = &types.InstanceGroup{
			ID:        "mock-group-1",
			Name:      "mock-scaling-group",
			Instances: mockConfig.Instances,
			MinSize:   1,
			MaxSize:   10,
			Desired:   len(mockConfig.Instances),
			Version:   "blue",
		}
	}

	return &MockProvider{
		config:      config,
		instances:   instances,
		group:       group,
		flavors:     mockConfig.Flavors,
		deployments: make(map[string]*types.BlueGreenDeployment),
		logger:      logger,
	}, nil
}

func (m *MockProvider) GetInstanceGroup(ctx context.Context, groupID string) (*types.InstanceGroup, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if m.group == nil {
		return nil, fmt.Errorf("instance group not found: %s", groupID)
	}

	instances := make([]types.InstanceInfo, 0, len(m.instances))
	reservedCount := 0
	onDemandCount := 0
	spotCount := 0
	totalHourlyCost := 0.0

	for _, inst := range m.instances {
		instances = append(instances, *inst)

		switch inst.ChargeType {
		case types.ChargeTypeReserved:
			reservedCount++
		case types.ChargeTypeOnDemand:
			onDemandCount++
		case types.ChargeTypeSpot:
			spotCount++
		}

		if inst.CostInfo.HourlyPrice > 0 {
			totalHourlyCost += inst.CostInfo.HourlyPrice
		} else {
			price := m.getFlavorPrice(inst.Flavor)
			if price != nil {
				chargeType := inst.ChargeType
				if chargeType == "" {
					chargeType = types.ChargeTypeOnDemand
				}
				switch chargeType {
				case types.ChargeTypeReserved:
					totalHourlyCost += price.ReservedPrice
				case types.ChargeTypeSpot:
					totalHourlyCost += price.SpotPrice
				default:
					totalHourlyCost += price.OnDemandPrice
				}
			}
		}
	}

	m.group.Instances = instances
	m.group.Desired = len(instances)
	m.group.ReservedCount = reservedCount
	m.group.OnDemandCount = onDemandCount
	m.group.SpotCount = spotCount
	m.group.TotalHourlyCost = totalHourlyCost

	return &types.InstanceGroup{
		ID:              m.group.ID,
		Name:            m.group.Name,
		Instances:       instances,
		MinSize:         m.group.MinSize,
		MaxSize:         m.group.MaxSize,
		Desired:         m.group.Desired,
		Service:         m.group.Service,
		Version:         m.group.Version,
		ReservedCount:   reservedCount,
		OnDemandCount:   onDemandCount,
		SpotCount:       spotCount,
		TotalHourlyCost: totalHourlyCost,
	}, nil
}

func (m *MockProvider) GetInstance(ctx context.Context, instanceID string) (*types.InstanceInfo, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	inst, exists := m.instances[instanceID]
	if !exists {
		return nil, fmt.Errorf("instance not found: %s", instanceID)
	}

	copy := *inst
	return &copy, nil
}

func (m *MockProvider) ScaleUp(ctx context.Context, action *types.ScalingAction) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	costConfig := m.config.CostConfig
	if costConfig == nil {
		costConfig = &types.CostConfig{
			ReservedInstanceRatio: 0.7,
			Enabled:               true,
		}
	}

	reservedCount := 0
	for _, inst := range m.instances {
		if inst.ChargeType == types.ChargeTypeReserved {
			reservedCount++
		}
	}

	targetReserved := int(float64(len(m.instances)+action.Step) * costConfig.ReservedInstanceRatio)
	needReserved := targetReserved - reservedCount
	if needReserved < 0 {
		needReserved = 0
	}

	for i := 0; i < action.Step; i++ {
		newID := fmt.Sprintf("mock-instance-%d", len(m.instances)+1)
		flavor := "ecs.medium"
		if len(m.instances) > 0 {
			for _, inst := range m.instances {
				flavor = inst.Flavor
				break
			}
		}

		chargeType := types.ChargeTypeOnDemand
		if costConfig.Enabled && needReserved > 0 {
			chargeType = types.ChargeTypeReserved
			needReserved--
		} else if costConfig.SpotInstanceEnabled {
			chargeType = types.ChargeTypeSpot
		}

		cores, mem := m.getFlavorSpec(flavor)

		newInst := &types.InstanceInfo{
			ID:         newID,
			Name:       fmt.Sprintf("auto-scaled-%d", time.Now().Unix()),
			Status:     "running",
			Flavor:     flavor,
			CPUCores:   cores,
			MemoryGB:   mem,
			PrivateIP:  fmt.Sprintf("192.168.1.%d", len(m.instances)+10),
			CreateTime: time.Now(),
			Version:    m.group.Version,
			Deployment: types.BlueGreenIdle,
			Healthy:    true,
			ChargeType: chargeType,
		}

		price := m.getFlavorPrice(flavor)
		if price != nil {
			hourlyPrice := price.OnDemandPrice
			if chargeType == types.ChargeTypeReserved {
				hourlyPrice = price.ReservedPrice
			} else if chargeType == types.ChargeTypeSpot {
				hourlyPrice = price.SpotPrice
			}
			newInst.CostInfo = types.InstanceCostInfo{
				InstanceID:   newID,
				Flavor:       flavor,
				ChargeType:   chargeType,
				HourlyPrice:  hourlyPrice,
				MonthlyPrice: hourlyPrice * 24 * 30,
				StartTime:    time.Now(),
			}
		}

		m.instances[newID] = newInst
		m.logger.Info("mock scale up created instance",
			zap.String("instance_id", newID),
			zap.String("flavor", flavor),
			zap.String("charge_type", string(chargeType)),
		)
	}

	m.group.Desired = len(m.instances)
	return nil
}

func (m *MockProvider) ScaleDown(ctx context.Context, action *types.ScalingAction) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if len(m.instances) <= action.Step {
		return fmt.Errorf("cannot remove %d instances, only %d available", action.Step, len(m.instances))
	}

	var spotInstances []string
	var onDemandInstances []string
	var reservedInstances []string

	for id, inst := range m.instances {
		switch inst.ChargeType {
		case types.ChargeTypeSpot:
			spotInstances = append(spotInstances, id)
		case types.ChargeTypeOnDemand:
			onDemandInstances = append(onDemandInstances, id)
		default:
			reservedInstances = append(reservedInstances, id)
		}
	}

	var toDelete []string
	toDelete = append(toDelete, spotInstances...)
	toDelete = append(toDelete, onDemandInstances...)
	toDelete = append(toDelete, reservedInstances...)

	count := 0
	for _, id := range toDelete {
		if count >= action.Step {
			break
		}
		if _, exists := m.instances[id]; exists {
			inst := m.instances[id]
			delete(m.instances, id)
			m.logger.Info("mock scale down removed instance",
				zap.String("instance_id", id),
				zap.String("instance_name", inst.Name),
				zap.String("charge_type", string(inst.ChargeType)),
			)
			count++
		}
	}

	m.group.Desired = len(m.instances)
	return nil
}

func (m *MockProvider) ScaleVertical(ctx context.Context, action *types.ScalingAction, newSize string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	inst, exists := m.instances[action.InstanceID]
	if !exists {
		return fmt.Errorf("instance not found: %s", action.InstanceID)
	}

	if !m.ValidateFlavor(ctx, newSize) {
		return fmt.Errorf("invalid flavor: %s", newSize)
	}

	oldFlavor := inst.Flavor
	inst.Flavor = newSize

	cores, mem := m.getFlavorSpec(newSize)
	inst.CPUCores = cores
	inst.MemoryGB = mem

	m.logger.Info("mock vertical scale",
		zap.String("instance_id", action.InstanceID),
		zap.String("old_flavor", oldFlavor),
		zap.String("new_flavor", newSize),
	)

	return nil
}

func (m *MockProvider) ValidateFlavor(ctx context.Context, flavor string) bool {
	for _, f := range m.flavors {
		if f == flavor {
			return true
		}
	}
	return false
}

func (m *MockProvider) GetNextFlavor(ctx context.Context, currentFlavor string, direction types.ScalingDirection) (string, error) {
	currentIdx := -1
	for i, f := range m.flavors {
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
		if currentIdx >= len(m.flavors)-1 {
			return "", fmt.Errorf("already at maximum flavor: %s", currentFlavor)
		}
		return m.flavors[currentIdx+1], nil
	case types.ScaleDown:
		if currentIdx <= 0 {
			return "", fmt.Errorf("already at minimum flavor: %s", currentFlavor)
		}
		return m.flavors[currentIdx-1], nil
	default:
		return "", fmt.Errorf("invalid scaling direction: %s", direction)
	}
}

func (m *MockProvider) ListFlavors(ctx context.Context) ([]string, error) {
	return m.flavors, nil
}

func (m *MockProvider) BlueGreenPrepare(ctx context.Context, groupID string, newFlavor string, count int) (*types.BlueGreenDeployment, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	group, err := m.GetInstanceGroup(ctx, groupID)
	if err != nil {
		return nil, fmt.Errorf("failed to get instance group: %w", err)
	}

	currentFlavor := m.flavors[0]
	if len(group.Instances) > 0 {
		currentFlavor = group.Instances[0].Flavor
	}

	deploymentID := fmt.Sprintf("bg-deploy-%d", time.Now().Unix())
	deployment := &types.BlueGreenDeployment{
		ID:             deploymentID,
		Service:        groupID,
		Status:         types.BlueGreenPreparing,
		BlueVersion:    "blue",
		GreenVersion:   "green",
		CurrentVersion: m.group.Version,
		BlueInstances:  make([]types.InstanceInfo, 0),
		GreenInstances: make([]types.InstanceInfo, 0),
		StartTime:      time.Now(),
		TrafficSplit:   100,
		Timeout:        10 * time.Minute,
	}

	for _, inst := range m.instances {
		deployment.BlueInstances = append(deployment.BlueInstances, *inst)
	}

	for i := 0; i < count; i++ {
		newID := fmt.Sprintf("green-%s-%d", groupID, len(m.instances)+i+1)
		cores, mem := m.getFlavorSpec(newFlavor)

		newInst := &types.InstanceInfo{
			ID:         newID,
			Name:       fmt.Sprintf("green-%d", i+1),
			Status:     "running",
			Flavor:     newFlavor,
			CPUCores:   cores,
			MemoryGB:   mem,
			PrivateIP:  fmt.Sprintf("192.168.2.%d", i+10),
			CreateTime: time.Now(),
			Version:    "green",
			Deployment: types.BlueGreenPreparing,
			Healthy:    true,
		}

		m.instances[newID] = newInst
		deployment.GreenInstances = append(deployment.GreenInstances, *newInst)

		m.logger.Info("created green instance for blue-green deployment",
			zap.String("instance_id", newID),
			zap.String("flavor", newFlavor),
		)
	}

	m.deployments[deploymentID] = deployment
	deployment.UpdateStatus(types.BlueGreenPreparing)

	return deployment, nil
}

func (m *MockProvider) BlueGreenWaitReady(ctx context.Context, deployment *types.BlueGreenDeployment, timeout time.Duration) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	deploy, exists := m.deployments[deployment.ID]
	if !exists {
		return fmt.Errorf("deployment not found: %s", deployment.ID)
	}

	deadline := time.Now().Add(timeout)
	checkInterval := 2 * time.Second

	for time.Now().Before(deadline) {
		allReady := true
		for _, inst := range deploy.GreenInstances {
			instance, ok := m.instances[inst.ID]
			if !ok || instance.Status != "running" || !instance.Healthy {
				allReady = false
				break
			}
		}

		if allReady {
			deploy.UpdateStatus(types.BlueGreenReady)
			deploy.ReadyTime = time.Now()
			m.logger.Info("all green instances ready for blue-green deployment",
				zap.String("deployment_id", deploy.ID),
				zap.Int("green_count", len(deploy.GreenInstances)),
			)
			return nil
		}

		m.mu.Unlock()
		time.Sleep(checkInterval)
		m.mu.Lock()

		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}
	}

	deploy.UpdateStatus(types.BlueGreenFailed)
	return fmt.Errorf("timeout waiting for green instances to become ready")
}

func (m *MockProvider) BlueGreenSwitchTraffic(ctx context.Context, deployment *types.BlueGreenDeployment, weight int) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	deploy, exists := m.deployments[deployment.ID]
	if !exists {
		return fmt.Errorf("deployment not found: %s", deployment.ID)
	}

	if weight < 0 || weight > 100 {
		return fmt.Errorf("weight must be between 0 and 100")
	}

	deploy.TrafficSplit = weight
	deploy.UpdateStatus(types.BlueGreenSwitching)
	deploy.SwitchTime = time.Now()

	if weight == 100 {
		m.group.Version = "green"
		for _, inst := range m.instances {
			if inst.Version == "green" {
				inst.Deployment = types.BlueGreenCompleted
			}
		}
	}

	m.logger.Info("switched traffic in blue-green deployment",
		zap.String("deployment_id", deploy.ID),
		zap.Int("green_weight", weight),
		zap.Int("blue_weight", 100-weight),
	)

	return nil
}

func (m *MockProvider) BlueGreenComplete(ctx context.Context, deployment *types.BlueGreenDeployment) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	deploy, exists := m.deployments[deployment.ID]
	if !exists {
		return fmt.Errorf("deployment not found: %s", deployment.ID)
	}

	var toDelete []string
	for _, inst := range deploy.BlueInstances {
		toDelete = append(toDelete, inst.ID)
	}

	for _, id := range toDelete {
		delete(m.instances, id)
		m.logger.Info("removed blue instance after blue-green deployment",
			zap.String("instance_id", id),
		)
	}

	m.group.Desired = len(m.instances)
	m.group.Version = "green"
	deploy.UpdateStatus(types.BlueGreenCompleted)

	m.logger.Info("blue-green deployment completed",
		zap.String("deployment_id", deploy.ID),
		zap.Int("remaining_instances", len(m.instances)),
	)

	return nil
}

func (m *MockProvider) BlueGreenRollback(ctx context.Context, deployment *types.BlueGreenDeployment) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	deploy, exists := m.deployments[deployment.ID]
	if !exists {
		return fmt.Errorf("deployment not found: %s", deployment.ID)
	}

	var toDelete []string
	for _, inst := range deploy.GreenInstances {
		toDelete = append(toDelete, inst.ID)
	}

	for _, id := range toDelete {
		delete(m.instances, id)
		m.logger.Info("removed green instance during rollback",
			zap.String("instance_id", id),
		)
	}

	m.group.Desired = len(m.instances)
	m.group.Version = "blue"
	deploy.UpdateStatus(types.BlueGreenRollingBack)

	m.logger.Info("blue-green deployment rolled back",
		zap.String("deployment_id", deploy.ID),
		zap.Int("remaining_instances", len(m.instances)),
	)

	return nil
}

func (m *MockProvider) getFlavorSpec(flavor string) (int, int) {
	switch flavor {
	case "ecs.small":
		return 1, 1
	case "ecs.medium":
		return 2, 4
	case "ecs.large":
		return 4, 8
	case "ecs.xlarge":
		return 8, 16
	case "ecs.2xlarge":
		return 16, 32
	default:
		return 2, 4
	}
}

func (m *MockProvider) getDefaultPriceList() []FlavorPrice {
	return []FlavorPrice{
		{Flavor: "ecs.small", OnDemandPrice: 0.05, ReservedPrice: 0.03, SpotPrice: 0.02, Region: "cn-beijing"},
		{Flavor: "ecs.medium", OnDemandPrice: 0.10, ReservedPrice: 0.06, SpotPrice: 0.04, Region: "cn-beijing"},
		{Flavor: "ecs.large", OnDemandPrice: 0.20, ReservedPrice: 0.12, SpotPrice: 0.08, Region: "cn-beijing"},
		{Flavor: "ecs.xlarge", OnDemandPrice: 0.40, ReservedPrice: 0.24, SpotPrice: 0.16, Region: "cn-beijing"},
		{Flavor: "ecs.2xlarge", OnDemandPrice: 0.80, ReservedPrice: 0.48, SpotPrice: 0.32, Region: "cn-beijing"},
	}
}

func (m *MockProvider) getFlavorPrice(flavor string) *FlavorPrice {
	priceList := m.config.PriceList
	if len(priceList) == 0 {
		priceList = m.getDefaultPriceList()
	}
	for i := range priceList {
		if priceList[i].Flavor == flavor {
			return &priceList[i]
		}
	}
	return nil
}

func (m *MockProvider) GetInstanceCost(ctx context.Context, instanceID string) (*types.InstanceCostInfo, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	inst, exists := m.instances[instanceID]
	if !exists {
		return nil, fmt.Errorf("instance not found: %s", instanceID)
	}

	price := m.getFlavorPrice(inst.Flavor)
	if price == nil {
		return nil, fmt.Errorf("price not found for flavor: %s", inst.Flavor)
	}

	chargeType := inst.ChargeType
	if chargeType == "" {
		chargeType = types.ChargeTypeOnDemand
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
		ReservedTerm:  12,
		ReservedUsage: 0.85,
		StartTime:     inst.CreateTime,
	}, nil
}

func (m *MockProvider) GetInstancePrice(ctx context.Context, flavor string, chargeType types.InstanceChargeType) (float64, error) {
	price := m.getFlavorPrice(flavor)
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

func (m *MockProvider) ConvertChargeType(ctx context.Context, instanceID string, targetType types.InstanceChargeType) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	inst, exists := m.instances[instanceID]
	if !exists {
		return fmt.Errorf("instance not found: %s", instanceID)
	}

	oldType := inst.ChargeType
	inst.ChargeType = targetType

	m.logger.Info("converted instance charge type",
		zap.String("instance_id", instanceID),
		zap.String("from_type", string(oldType)),
		zap.String("to_type", string(targetType)),
	)

	return nil
}

func (m *MockProvider) ListReservedInstances(ctx context.Context) ([]types.InstanceInfo, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var reserved []types.InstanceInfo
	for _, inst := range m.instances {
		if inst.ChargeType == types.ChargeTypeReserved {
			reserved = append(reserved, *inst)
		}
	}
	return reserved, nil
}

func (m *MockProvider) PurchaseReservedInstance(ctx context.Context, flavor string, termMonths int) (*types.InstanceCostInfo, error) {
	price := m.getFlavorPrice(flavor)
	if price == nil {
		return nil, fmt.Errorf("price not found for flavor: %s", flavor)
	}

	instanceID := fmt.Sprintf("reserved-%s-%d", flavor, time.Now().Unix())

	m.logger.Info("purchased reserved instance",
		zap.String("instance_id", instanceID),
		zap.String("flavor", flavor),
		zap.Int("term_months", termMonths),
		zap.Float64("hourly_price", price.ReservedPrice),
	)

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

func (m *MockProvider) CalculateCostOptimization(ctx context.Context, group *types.InstanceGroup) ([]types.CostOptimizationAction, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var actions []types.CostOptimizationAction
	totalReserved := 0
	totalOnDemand := 0

	for _, inst := range group.Instances {
		if inst.ChargeType == types.ChargeTypeReserved {
			totalReserved++
		} else {
			totalOnDemand++
		}
	}

	costConfig := m.config.CostConfig
	if costConfig == nil {
		costConfig = &types.CostConfig{
			ReservedInstanceRatio: 0.7,
		}
	}

	targetReserved := int(float64(len(group.Instances)) * costConfig.ReservedInstanceRatio)

	if totalReserved < targetReserved {
		needConvert := targetReserved - totalReserved
		converted := 0

		for _, inst := range group.Instances {
			if converted >= needConvert {
				break
			}
			if inst.ChargeType == types.ChargeTypeOnDemand {
				price := m.getFlavorPrice(inst.Flavor)
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

	for _, inst := range group.Instances {
		price := m.getFlavorPrice(inst.Flavor)
		if price != nil {
			flavorIdx := -1
			for i, f := range m.flavors {
				if f == inst.Flavor {
					flavorIdx = i
					break
				}
			}
			if flavorIdx > 0 {
				smallerFlavor := m.flavors[flavorIdx-1]
				smallerPrice := m.getFlavorPrice(smallerFlavor)
				if smallerPrice != nil {
					savings := (price.OnDemandPrice - smallerPrice.OnDemandPrice) * 24 * 30
					actions = append(actions, types.CostOptimizationAction{
						Type:        "downsize",
						InstanceID:  inst.ID,
						FromCharge:  inst.ChargeType,
						ToCharge:    inst.ChargeType,
						FromFlavor:  inst.Flavor,
						ToFlavor:    smallerFlavor,
						CostSavings: savings,
						Reason:      "Instance is oversized based on historical utilization",
						Timestamp:   time.Now(),
					})
				}
			}
		}
	}

	return actions, nil
}
