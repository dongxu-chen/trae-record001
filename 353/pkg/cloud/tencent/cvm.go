package tencent

import (
	"context"
	"fmt"
	"time"

	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common"
	"github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/common/profile"
	cvm "github.com/tencentcloud/tencentcloud-sdk-go/tencentcloud/cvm/v20170312"
)

type CVMClient struct {
	client *cvm.Client
	region string
}

func NewCVMClient(region, secretID, secretKey string) (*CVMClient, error) {
	credential := common.NewCredential(secretID, secretKey)
	cpf := profile.NewClientProfile()
	cpf.HttpProfile.Endpoint = "cvm.tencentcloudapi.com"
	client, err := cvm.NewClient(credential, region, cpf)
	if err != nil {
		return nil, fmt.Errorf("failed to create CVM client: %w", err)
	}
	return &CVMClient{
		client: client,
		region: region,
	}, nil
}

func (c *CVMClient) GetProviderName() string {
	return "tencent"
}

func (c *CVMClient) GetRegion() string {
	return c.region
}

func (c *CVMClient) CreateSnapshot(ctx context.Context, instanceID string, snapshotName string) (string, error) {
	descReq := cvm.NewDescribeInstancesRequest()
	descReq.InstanceIds = common.StringPtrs([]string{instanceID})
	descResp, err := c.client.DescribeInstances(descReq)
	if err != nil {
		return "", fmt.Errorf("failed to describe instance: %w", err)
	}

	if *descResp.Response.TotalCount == 0 {
		return "", fmt.Errorf("instance not found: %s", instanceID)
	}

	instance := descResp.Response.InstanceSet[0]
	var diskID string
	if len(instance.DataDisks) > 0 {
		diskID = *instance.DataDisks[0].DiskId
	} else if instance.SystemDisk != nil && instance.SystemDisk.DiskId != nil {
		diskID = *instance.SystemDisk.DiskId
	}

	if diskID == "" {
		return "", fmt.Errorf("no disk found for instance: %s", instanceID)
	}

	snapReq := cvm.NewCreateSnapshotRequest()
	snapReq.DiskId = common.StringPtr(diskID)
	snapReq.SnapshotName = common.StringPtr(snapshotName)

	snapResp, err := c.client.CreateSnapshot(snapReq)
	if err != nil {
		return "", fmt.Errorf("failed to create snapshot: %w", err)
	}

	return *snapResp.Response.SnapshotId, nil
}

func (c *CVMClient) WaitForSnapshotComplete(ctx context.Context, snapshotID string) error {
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
			req := cvm.NewDescribeSnapshotsRequest()
			req.SnapshotIds = common.StringPtrs([]string{snapshotID})
			resp, err := c.client.DescribeSnapshots(req)
			if err != nil {
				continue
			}

			if *resp.Response.TotalCount > 0 {
				status := *resp.Response.SnapshotSet[0].SnapshotState
				if status == "NORMAL" {
					return nil
				}
			}
		}
	}
}

func (c *CVMClient) CreateImageFromSnapshot(ctx context.Context, snapshotID string, imageName string) (string, error) {
	req := cvm.NewCreateImageRequest()
	req.ImageName = common.StringPtr(imageName)
	req.SnapshotIds = common.StringPtrs([]string{snapshotID})
	req.ImageDescription = common.StringPtr(fmt.Sprintf("Migrated image from snapshot: %s", snapshotID))

	resp, err := c.client.CreateImage(req)
	if err != nil {
		return "", fmt.Errorf("failed to create image: %w", err)
	}

	return *resp.Response.ImageId, nil
}

func (c *CVMClient) WaitForImageComplete(ctx context.Context, imageID string) error {
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
			req := cvm.NewDescribeImagesRequest()
			req.ImageIds = common.StringPtrs([]string{imageID})
			resp, err := c.client.DescribeImages(req)
			if err != nil {
				continue
			}

			if *resp.Response.TotalCount > 0 {
				status := *resp.Response.ImageSet[0].ImageState
				if status == "NORMAL" {
					return nil
				}
			}
		}
	}
}

func (c *CVMClient) RunInstances(ctx context.Context, imageID, instanceType, zone string) (string, error) {
	req := cvm.NewRunInstancesRequest()
	req.ImageId = common.StringPtr(imageID)
	req.InstanceType = common.StringPtr(instanceType)
	req.Placement = &cvm.Placement{
		Zone: common.StringPtr(zone),
	}
	req.InstanceCount = common.Int64Ptr(1)

	resp, err := c.client.RunInstances(req)
	if err != nil {
		return "", fmt.Errorf("failed to run instances: %w", err)
	}

	if len(resp.Response.InstanceIdSet) > 0 {
		return *resp.Response.InstanceIdSet[0], nil
	}

	return "", fmt.Errorf("no instance ID returned")
}
