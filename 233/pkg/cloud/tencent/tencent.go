package tencent

import (
	"context"
	"fmt"

	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common/profile"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/cvm/v20170312"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/as/v20180419"
	"github.com/cloud-autoscaler/pkg/cloud"
)

type TencentProvider struct {
	cfg       cloud.ProviderConfig
	cvmClient *cvm.Client
	asClient  *as.Client
}

func init() {
	cloud.RegisterProvider("tencent", NewTencentProvider)
}

func NewTencentProvider(cfg cloud.ProviderConfig) (cloud.Provider, error) {
	credential := common.NewCredential(
		cfg.Credentials.SecretID,
		cfg.Credentials.SecretKey,
	)
	cpf := profile.NewClientProfile()

	cvmClient, err := cvm.NewClient(credential, cfg.Region, cpf)
	if err != nil {
		return nil, fmt.Errorf("failed to create CVM client: %w", err)
	}

	asClient, err := as.NewClient(credential, cfg.Region, cpf)
	if err != nil {
		return nil, fmt.Errorf("failed to create AS client: %w", err)
	}

	return &TencentProvider{
		cfg:       cfg,
		cvmClient: cvmClient,
		asClient:  asClient,
	}, nil
}

func (p *TencentProvider) GetName() string {
	return "tencent"
}

func (p *TencentProvider) GetInstances(ctx context.Context) ([]cloud.Instance, error) {
	request := cvm.NewDescribeInstancesRequest()
	request.Limit = common.Int64Ptr(100)

	response, err := p.cvmClient.DescribeInstances(request)
	if err != nil {
		return nil, fmt.Errorf("failed to describe instances: %w", err)
	}

	var instances []cloud.Instance
	for _, inst := range response.Response.InstanceSet {
		instance := cloud.Instance{
			ID:           *inst.InstanceId,
			Name:         *inst.InstanceName,
			Status:       *inst.InstanceState,
			Region:       p.cfg.Region,
			InstanceType: *inst.InstanceType,
			Provider:     "tencent",
		}
		if len(inst.PrivateIpAddresses) > 0 {
			instance.PrivateIP = *inst.PrivateIpAddresses[0]
		}
		if len(inst.PublicIpAddresses) > 0 {
			instance.PublicIP = *inst.PublicIpAddresses[0]
		}
		instances = append(instances, instance)
	}

	return instances, nil
}

func (p *TencentProvider) GetInstanceCount(ctx context.Context) (int, error) {
	if p.cfg.ScalingGroupID != "" {
		request := as.NewDescribeAutoScalingGroupsRequest()
		request.AutoScalingGroupIds = common.StringPtrs([]string{p.cfg.ScalingGroupID})

		response, err := p.asClient.DescribeAutoScalingGroups(request)
		if err != nil {
			return 0, fmt.Errorf("failed to describe scaling group: %w", err)
		}
		if len(response.Response.AutoScalingGroupSet) > 0 {
			return int(*response.Response.AutoScalingGroupSet[0].DesiredCapacity), nil
		}
		return 0, nil
	}

	instances, err := p.GetInstances(ctx)
	if err != nil {
		return 0, err
	}
	return len(instances), nil
}

func (p *TencentProvider) ScaleUp(ctx context.Context, count int) error {
	if p.cfg.ScalingGroupID != "" {
		request := as.NewModifyAutoScalingGroupRequest()
		request.AutoScalingGroupId = common.StringPtr(p.cfg.ScalingGroupID)

		currentCount, err := p.GetInstanceCount(ctx)
		if err != nil {
			return err
		}
		desiredCount := int64(currentCount + count)
		request.DesiredCapacity = common.Int64Ptr(desiredCount)

		_, err = p.asClient.ModifyAutoScalingGroup(request)
		if err != nil {
			return fmt.Errorf("failed to modify scaling group: %w", err)
		}
		return nil
	}

	for i := 0; i < count; i++ {
		request := cvm.NewRunInstancesRequest()
		request.ImageId = common.StringPtr(p.cfg.Infrastructure.ImageID)
		request.InstanceType = common.StringPtr(p.cfg.Infrastructure.InstanceType)
		request.SecurityGroupIds = common.StringPtrs([]string{p.cfg.Infrastructure.SecurityGroupID})
		request.VirtualPrivateCloud = &cvm.VirtualPrivateCloud{
			SubnetId: common.StringPtr(p.cfg.Infrastructure.SubnetID),
		}
		request.LoginSettings = &cvm.LoginSettings{
			KeyIds: common.StringPtrs([]string{p.cfg.Infrastructure.KeyID}),
		}
		request.InstanceCount = common.Int64Ptr(1)
		if p.cfg.Infrastructure.UserData != "" {
			request.UserData = common.StringPtr(p.cfg.Infrastructure.UserData)
		}

		_, err := p.cvmClient.RunInstances(request)
		if err != nil {
			return fmt.Errorf("failed to create instance: %w", err)
		}
	}
	return nil
}

func (p *TencentProvider) ScaleDown(ctx context.Context, count int) error {
	if p.cfg.ScalingGroupID != "" {
		request := as.NewModifyAutoScalingGroupRequest()
		request.AutoScalingGroupId = common.StringPtr(p.cfg.ScalingGroupID)

		currentCount, err := p.GetInstanceCount(ctx)
		if err != nil {
			return err
		}
		desiredCount := int64(currentCount - count)
		if desiredCount < 0 {
			desiredCount = 0
		}
		request.DesiredCapacity = common.Int64Ptr(desiredCount)

		_, err = p.asClient.ModifyAutoScalingGroup(request)
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
		request := cvm.NewTerminateInstancesRequest()
		request.InstanceIds = common.StringPtrs([]string{instances[i].ID})

		_, err := p.cvmClient.TerminateInstances(request)
		if err != nil {
			return fmt.Errorf("failed to terminate instance: %w", err)
		}
	}
	return nil
}

func (p *TencentProvider) GetMetrics(ctx context.Context) (cpu, memory float64, err error) {
	return 0, 0, fmt.Errorf("metrics should be retrieved via Prometheus")
}
