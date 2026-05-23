package aws

import (
	"context"
	"fmt"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/autoscaling"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	ec2Types "github.com/aws/aws-sdk-go-v2/service/ec2/types"
	"github.com/cloud-autoscaler/pkg/cloud"
)

type AWSProvider struct {
	cfg       cloud.ProviderConfig
	awsCfg    aws.Config
	ec2Client *ec2.Client
	asgClient *autoscaling.Client
}

func init() {
	cloud.RegisterProvider("aws", NewAWSProvider)
}

func NewAWSProvider(cfg cloud.ProviderConfig) (cloud.Provider, error) {
	var awsCfg aws.Config
	var err error

	if cfg.Credentials.AccessKeyID != "" && cfg.Credentials.AccessKeySecret != "" {
		awsCfg, err = config.LoadDefaultConfig(context.TODO(),
			config.WithRegion(cfg.Region),
			config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(
				cfg.Credentials.AccessKeyID,
				cfg.Credentials.AccessKeySecret,
				"",
			)),
		)
	} else {
		awsCfg, err = config.LoadDefaultConfig(context.TODO(),
			config.WithRegion(cfg.Region),
		)
	}

	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return &AWSProvider{
		cfg:       cfg,
		awsCfg:    awsCfg,
		ec2Client: ec2.NewFromConfig(awsCfg),
		asgClient: autoscaling.NewFromConfig(awsCfg),
	}, nil
}

func (p *AWSProvider) GetName() string {
	return "aws"
}

func (p *AWSProvider) GetInstances(ctx context.Context) ([]cloud.Instance, error) {
	input := &ec2.DescribeInstancesInput{}
	result, err := p.ec2Client.DescribeInstances(ctx, input)
	if err != nil {
		return nil, fmt.Errorf("failed to describe instances: %w", err)
	}

	var instances []cloud.Instance
	for _, reservation := range result.Reservations {
		for _, inst := range reservation.Instances {
			instance := cloud.Instance{
				ID:           aws.ToString(inst.InstanceId),
				Name:         getNameTag(inst.Tags),
				Status:       string(inst.State.Name),
				Region:       p.cfg.Region,
				InstanceType: string(inst.InstanceType),
				Provider:     "aws",
			}
			if inst.PrivateIpAddress != nil {
				instance.PrivateIP = *inst.PrivateIpAddress
			}
			if inst.PublicIpAddress != nil {
				instance.PublicIP = *inst.PublicIpAddress
			}
			if inst.LaunchTime != nil {
				instance.CreationTime = *inst.LaunchTime
			}
			instances = append(instances, instance)
		}
	}

	return instances, nil
}

func (p *AWSProvider) GetInstanceCount(ctx context.Context) (int, error) {
	if p.cfg.ScalingGroupID != "" {
		input := &autoscaling.DescribeAutoScalingGroupsInput{
			AutoScalingGroupNames: []string{p.cfg.ScalingGroupID},
		}
		result, err := p.asgClient.DescribeAutoScalingGroups(ctx, input)
		if err != nil {
			return 0, fmt.Errorf("failed to describe ASG: %w", err)
		}
		if len(result.AutoScalingGroups) > 0 {
			return len(result.AutoScalingGroups[0].Instances), nil
		}
		return 0, nil
	}

	instances, err := p.GetInstances(ctx)
	if err != nil {
		return 0, err
	}
	return len(instances), nil
}

func (p *AWSProvider) ScaleUp(ctx context.Context, count int) error {
	if p.cfg.ScalingGroupID != "" {
		currentCount, err := p.GetInstanceCount(ctx)
		if err != nil {
			return err
		}
		desiredCount := int32(currentCount + count)
		input := &autoscaling.UpdateAutoScalingGroupInput{
			AutoScalingGroupName: aws.String(p.cfg.ScalingGroupID),
			DesiredCapacity:      aws.Int32(desiredCount),
		}
		_, err = p.asgClient.UpdateAutoScalingGroup(ctx, input)
		if err != nil {
			return fmt.Errorf("failed to update ASG desired capacity: %w", err)
		}
		return nil
	}

	for i := 0; i < count; i++ {
		input := &ec2.RunInstancesInput{
			ImageId:      aws.String(p.cfg.Infrastructure.ImageID),
			InstanceType: p.cfg.Infrastructure.InstanceType,
			MinCount:     aws.Int32(1),
			MaxCount:     aws.Int32(1),
			SecurityGroupIds: []string{
				p.cfg.Infrastructure.SecurityGroupID,
			},
			SubnetId: aws.String(p.cfg.Infrastructure.SubnetID),
			KeyName:  aws.String(p.cfg.Infrastructure.KeyID),
		}
		if p.cfg.Infrastructure.UserData != "" {
			input.UserData = aws.String(p.cfg.Infrastructure.UserData)
		}
		_, err := p.ec2Client.RunInstances(ctx, input)
		if err != nil {
			return fmt.Errorf("failed to launch instance: %w", err)
		}
	}
	return nil
}

func (p *AWSProvider) ScaleDown(ctx context.Context, count int) error {
	if p.cfg.ScalingGroupID != "" {
		currentCount, err := p.GetInstanceCount(ctx)
		if err != nil {
			return err
		}
		desiredCount := int32(currentCount - count)
		if desiredCount < 0 {
			desiredCount = 0
		}
		input := &autoscaling.UpdateAutoScalingGroupInput{
			AutoScalingGroupName: aws.String(p.cfg.ScalingGroupID),
			DesiredCapacity:      aws.Int32(desiredCount),
		}
		_, err = p.asgClient.UpdateAutoScalingGroup(ctx, input)
		if err != nil {
			return fmt.Errorf("failed to update ASG desired capacity: %w", err)
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
		input := &ec2.TerminateInstancesInput{
			InstanceIds: []string{instances[i].ID},
		}
		_, err := p.ec2Client.TerminateInstances(ctx, input)
		if err != nil {
			return fmt.Errorf("failed to terminate instance: %w", err)
		}
	}
	return nil
}

func (p *AWSProvider) GetMetrics(ctx context.Context) (cpu, memory float64, err error) {
	return 0, 0, fmt.Errorf("metrics should be retrieved via Prometheus")
}

func getNameTag(tags []ec2Types.Tag) string {
	for _, tag := range tags {
		if aws.ToString(tag.Key) == "Name" {
			return aws.ToString(tag.Value)
		}
	}
	return ""
}
