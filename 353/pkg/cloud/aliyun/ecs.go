package aliyun

import (
	"context"
	"fmt"
	"time"

	"github.com/aliyun/alibaba-cloud-sdk-go/sdk"
	"github.com/aliyun/alibaba-cloud-sdk-go/sdk/requests"
	"github.com/aliyun/alibaba-cloud-sdk-go/services/ecs"
)

type ECSClient struct {
	client *ecs.Client
	region string
}

func NewECSClient(region, accessKeyID, accessKeySecret string) (*ECSClient, error) {
	client, err := ecs.NewClientWithAccessKey(region, accessKeyID, accessKeySecret)
	if err != nil {
		return nil, fmt.Errorf("failed to create ECS client: %w", err)
	}
	return &ECSClient{
		client: client,
		region: region,
	}, nil
}

func (e *ECSClient) GetProviderName() string {
	return "aliyun"
}

func (e *ECSClient) GetRegion() string {
	return e.region
}

func (e *ECSClient) CreateSnapshot(ctx context.Context, instanceID string, snapshotName string) (string, error) {
	descReq := ecs.CreateDescribeInstancesRequest()
	descReq.InstanceIds = fmt.Sprintf(`["%s"]`, instanceID)
	descResp, err := e.client.DescribeInstances(descReq)
	if err != nil {
		return "", fmt.Errorf("failed to describe instance: %w", err)
	}

	if len(descResp.Instances.Instance) == 0 {
		return "", fmt.Errorf("instance not found: %s", instanceID)
	}

	instance := descResp.Instances.Instance[0]
	var diskID string
	if len(instance.Disks.Disk) > 0 {
		diskID = instance.Disks.Disk[0].DiskId
	}

	if diskID == "" {
		return "", fmt.Errorf("no disk found for instance: %s", instanceID)
	}

	snapReq := ecs.CreateCreateSnapshotRequest()
	snapReq.DiskId = diskID
	snapReq.SnapshotName = snapshotName
	snapReq.Description = fmt.Sprintf("Snapshot for migration: %s", snapshotName)
	snapReq.Tag = &[]ecs.CreateSnapshotTag{
		{Key: "Migration", Value: "true"},
	}

	snapResp, err := e.client.CreateSnapshot(snapReq)
	if err != nil {
		return "", fmt.Errorf("failed to create snapshot: %w", err)
	}

	return snapResp.SnapshotId, nil
}

func (e *ECSClient) WaitForSnapshotComplete(ctx context.Context, snapshotID string) error {
	timeout := time.After(30 * time.Minute)
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-timeout:
			return fmt.Errorf("timeout waiting for snapshot %s", snapshotID)
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			req := ecs.CreateDescribeSnapshotsRequest()
			req.SnapshotIds = fmt.Sprintf(`["%s"]`, snapshotID)
			resp, err := e.client.DescribeSnapshots(req)
			if err != nil {
				continue
			}

			if len(resp.Snapshots.Snapshot) > 0 {
				status := resp.Snapshots.Snapshot[0].Status
				if status == "accomplished" {
					return nil
				}
			}
		}
	}
}

func (e *ECSClient) ImportImage(ctx context.Context, snapshotID string, imageName string, osType string) (string, error) {
	req := ecs.CreateImportImageRequest()
	req.Scheme = "https"
	req.ImageName = imageName
	req.Description = fmt.Sprintf("Migrated image from snapshot: %s", snapshotID)
	req.OSType = osType
	req.Platform = "CentOS"
	req.Architecture = "x86_64"

	resp, err := e.client.ImportImage(req)
	if err != nil {
		return "", fmt.Errorf("failed to import image: %w", err)
	}

	return resp.ImageId, nil
}

func (e *ECSClient) WaitForImageComplete(ctx context.Context, imageID string) error {
	timeout := time.After(60 * time.Minute)
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-timeout:
			return fmt.Errorf("timeout waiting for image %s", imageID)
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			req := ecs.CreateDescribeImagesRequest()
			req.ImageId = imageID
			resp, err := e.client.DescribeImages(req)
			if err != nil {
				continue
			}

			if len(resp.Images.Image) > 0 {
				status := resp.Images.Image[0].Status
				if status == "Available" {
					return nil
				}
			}
		}
	}
}

func (e *ECSClient) CreateInstanceFromImage(ctx context.Context, imageID, instanceType, zoneID string) (string, error) {
	req := ecs.CreateRunInstancesRequest()
	req.ImageId = imageID
	req.InstanceType = instanceType
	req.ZoneId = zoneID
	req.SecurityGroupId = ""
	req.VSwitchId = ""
	req.InstanceName = fmt.Sprintf("migrated-%d", time.Now().Unix())
	req.Amount = requests.NewInteger(1)

	resp, err := e.client.RunInstances(req)
	if err != nil {
		return "", fmt.Errorf("failed to create instance: %w", err)
	}

	if len(resp.InstanceIdSets.InstanceIdSet) > 0 {
		return resp.InstanceIdSets.InstanceIdSet[0], nil
	}

	return "", fmt.Errorf("no instance ID returned")
}

func (e *ECSClient) GetClientConfig() *sdk.Client {
	return e.client.Client
}
