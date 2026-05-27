package aws

import (
	"context"
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	"github.com/aws/aws-sdk-go-v2/service/ec2/types"
)

type EC2Client struct {
	client *ec2.Client
	region string
}

func NewEC2Client(region string) (*EC2Client, error) {
	cfg, err := config.LoadDefaultConfig(context.TODO(), config.WithRegion(region))
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return &EC2Client{
		client: ec2.NewFromConfig(cfg),
		region: region,
	}, nil
}

func (e *EC2Client) GetProviderName() string {
	return "aws"
}

func (e *EC2Client) GetRegion() string {
	return e.region
}

func (e *EC2Client) CreateSnapshot(ctx context.Context, instanceID string, snapshotName string) (string, error) {
	descResp, err := e.client.DescribeInstances(ctx, &ec2.DescribeInstancesInput{
		InstanceIds: []string{instanceID},
	})
	if err != nil {
		return "", fmt.Errorf("failed to describe instance: %w", err)
	}

	if len(descResp.Reservations) == 0 || len(descResp.Reservations[0].Instances) == 0 {
		return "", fmt.Errorf("instance not found: %s", instanceID)
	}

	instance := descResp.Reservations[0].Instances[0]
	var volumeID string
	for _, blockDevice := range instance.BlockDeviceMappings {
		if blockDevice.Ebs != nil {
			volumeID = *blockDevice.Ebs.VolumeId
			break
		}
	}

	if volumeID == "" {
		return "", fmt.Errorf("no EBS volume found for instance: %s", instanceID)
	}

	snapResp, err := e.client.CreateSnapshot(ctx, &ec2.CreateSnapshotInput{
		VolumeId:    aws.String(volumeID),
		Description: aws.String(fmt.Sprintf("Snapshot for migration: %s", snapshotName)),
		TagSpecifications: []types.TagSpecification{
			{
				ResourceType: types.ResourceTypeSnapshot,
				Tags: []types.Tag{
					{Key: aws.String("Name"), Value: aws.String(snapshotName)},
					{Key: aws.String("Migration"), Value: aws.String("true")},
				},
			},
		},
	})
	if err != nil {
		return "", fmt.Errorf("failed to create snapshot: %w", err)
	}

	return *snapResp.SnapshotId, nil
}

func (e *EC2Client) WaitForSnapshotComplete(ctx context.Context, snapshotID string) error {
	waiter := ec2.NewSnapshotCompletedWaiter(e.client)
	return waiter.Wait(ctx, &ec2.DescribeSnapshotsInput{
		SnapshotIds: []string{snapshotID},
	}, 5*time.Minute)
}

func (e *EC2Client) CreateImageFromSnapshot(ctx context.Context, snapshotID string, imageName string) (string, error) {
	resp, err := e.client.RegisterImage(ctx, &ec2.RegisterImageInput{
		Name:        aws.String(imageName),
		Description: aws.String(fmt.Sprintf("Migrated image from snapshot: %s", snapshotID)),
		Architecture: types.ArchitectureValuesX8664,
		RootDeviceName: aws.String("/dev/sda1"),
		BlockDeviceMappings: []types.BlockDeviceMapping{
			{
				DeviceName: aws.String("/dev/sda1"),
				Ebs: &types.EbsBlockDevice{
					SnapshotId: aws.String(snapshotID),
					VolumeType: types.VolumeTypeGp3,
				},
			},
		},
		VirtualizationType: types.VirtualizationTypeHvm,
	})
	if err != nil {
		return "", fmt.Errorf("failed to register image: %w", err)
	}

	return *resp.ImageId, nil
}

func (e *EC2Client) WaitForImageComplete(ctx context.Context, imageID string) error {
	waiter := ec2.NewImageAvailableWaiter(e.client)
	return waiter.Wait(ctx, &ec2.DescribeImagesInput{
		ImageIds: []string{imageID},
	}, 10*time.Minute)
}

func (e *EC2Client) ExportImage(ctx context.Context, imageID string, bucketName string, objectKey string) error {
	_, err := e.client.ExportImage(ctx, &ec2.ExportImageInput{
		ImageId: aws.String(imageID),
		DiskImageFormat: types.DiskImageFormatVmdk,
		S3ExportLocation: &types.ExportTaskS3LocationRequest{
			S3Bucket: aws.String(bucketName),
			S3Prefix: aws.String(objectKey),
		},
	})
	if err != nil {
		return fmt.Errorf("failed to export image: %w", err)
	}

	return nil
}
