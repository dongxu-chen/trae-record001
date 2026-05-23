package aliyun

import (
	"context"
	"fmt"

	"github.com/aliyun/alibaba-cloud-sdk-go/sdk"
	"github.com/aliyun/alibaba-cloud-sdk-go/sdk/requests"
	"github.com/aliyun/alibaba-cloud-sdk-go/services/ecs"
	"github.com/aliyun/alibaba-cloud-sdk-go/services/ess"
	"github.com/cloud-autoscaler/pkg/cloud"
)

type AliyunProvider struct {
	cfg       cloud.ProviderConfig
	ecsClient *ecs.Client
	essClient *ess.Client
}

func init() {
	cloud.RegisterProvider("aliyun", NewAliyunProvider)
}

func NewAliyunProvider(cfg cloud.ProviderConfig) (cloud.Provider, error) {
	ecsClient, err := ecs.NewClientWithAccessKey(
		cfg.Region,
		cfg.Credentials.AccessKeyID,
		cfg.Credentials.AccessKeySecret,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create ECS client: %w", err)
	}

	essClient, err := ess.NewClientWithAccessKey(
		cfg.Region,
		cfg.Credentials.AccessKeyID,
		cfg.Credentials.AccessKeySecret,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create ESS client: %w", err)
	}

	return &AliyunProvider{
		cfg:       cfg,
		ecsClient: ecsClient,
		essClient: essClient,
	}, nil
}

func (p *AliyunProvider) GetName() string {
	return "aliyun"
}

func (p *AliyunProvider) GetInstances(ctx context.Context) ([]cloud.Instance, error) {
	request := ecs.CreateDescribeInstancesRequest()
	request.PageSize = requests.NewInteger(100)

	response, err := p.ecsClient.DescribeInstances(request)
	if err != nil {
		return nil, fmt.Errorf("failed to describe instances: %w", err)
	}

	var instances []cloud.Instance
	for _, inst := range response.Instances.Instance {
		instance := cloud.Instance{
			ID:           inst.InstanceId,
			Name:         inst.InstanceName,
			Status:       inst.Status,
			Region:       p.cfg.Region,
			InstanceType: inst.InstanceType,
			Provider:     "aliyun",
		}
		if len(inst.VpcAttributes.PrivateIpAddress.IpAddress) > 0 {
			instance.PrivateIP = inst.VpcAttributes.PrivateIpAddress.IpAddress[0]
		}
		if len(inst.PublicIpAddress.IpAddress) > 0 {
			instance.PublicIP = inst.PublicIpAddress.IpAddress[0]
		}
		instances = append(instances, instance)
	}

	return instances, nil
}

func (p *AliyunProvider) GetInstanceCount(ctx context.Context) (int, error) {
	if p.cfg.ScalingGroupID != "" {
		request := ess.CreateDescribeScalingGroupsRequest()
		request.ScalingGroupId = p.cfg.ScalingGroupID

		response, err := p.essClient.DescribeScalingGroups(request)
		if err != nil {
			return 0, fmt.Errorf("failed to describe scaling group: %w", err)
		}
		if len(response.ScalingGroups.ScalingGroup) > 0 {
			return response.ScalingGroups.ScalingGroup[0].TotalCapacity, nil
		}
		return 0, nil
	}

	instances, err := p.GetInstances(ctx)
	if err != nil {
		return 0, err
	}
	return len(instances), nil
}

func (p *AliyunProvider) ScaleUp(ctx context.Context, count int) error {
	if p.cfg.ScalingGroupID != "" {
		request := ess.CreateModifyScalingGroupRequest()
		request.ScalingGroupId = p.cfg.ScalingGroupID

		currentCount, err := p.GetInstanceCount(ctx)
		if err != nil {
			return err
		}
		desiredCount := currentCount + count
		request.DesiredCapacity = requests.NewInteger(desiredCount)

		_, err = p.essClient.ModifyScalingGroup(request)
		if err != nil {
			return fmt.Errorf("failed to modify scaling group: %w", err)
		}
		return nil
	}

	for i := 0; i < count; i++ {
		request := ecs.CreateRunInstancesRequest()
		request.ImageId = p.cfg.Infrastructure.ImageID
		request.InstanceType = p.cfg.Infrastructure.InstanceType
		request.SecurityGroupId = p.cfg.Infrastructure.SecurityGroupID
		request.VSwitchId = p.cfg.Infrastructure.SubnetID
		request.KeyPairName = p.cfg.Infrastructure.KeyID
		request.Amount = requests.NewInteger(1)
		if p.cfg.Infrastructure.UserData != "" {
			request.UserData = p.cfg.Infrastructure.UserData
		}

		_, err := p.ecsClient.RunInstances(request)
		if err != nil {
			return fmt.Errorf("failed to create instance: %w", err)
		}
	}
	return nil
}

func (p *AliyunProvider) ScaleDown(ctx context.Context, count int) error {
	if p.cfg.ScalingGroupID != "" {
		request := ess.CreateModifyScalingGroupRequest()
		request.ScalingGroupId = p.cfg.ScalingGroupID

		currentCount, err := p.GetInstanceCount(ctx)
		if err != nil {
			return err
		}
		desiredCount := currentCount - count
		if desiredCount < 0 {
			desiredCount = 0
		}
		request.DesiredCapacity = requests.NewInteger(desiredCount)

		_, err = p.essClient.ModifyScalingGroup(request)
		if err != nil {
			return fmt.Errorf("failed to modify scaling group: %w", err)
		}
		return nil
	}

	instances, err := p.GetInstances(ctx)
	if err != nil {
		return err
	}

	if len(instances) < count {
		count = len(instances)
	}

	for i := 0; i < count; i++ {
		request := ecs.CreateDeleteInstanceRequest()
		request.InstanceId = instances[i].ID
		request.Force = requests.NewBoolean(true)

		_, err := p.ecsClient.DeleteInstance(request)
		if err != nil {
			return fmt.Errorf("failed to delete instance: %w", err)
		}
	}
	return nil
}

func (p *AliyunProvider) GetMetrics(ctx context.Context) (cpu, memory float64, err error) {
	return 0, 0, fmt.Errorf("metrics should be retrieved via Prometheus")
}

var _ = sdk.NewConfig()
