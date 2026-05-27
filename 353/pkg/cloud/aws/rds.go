package aws

import (
	"context"
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/rds"
)

type RDSClient struct {
	client *rds.Client
	region string
}

func NewRDSClient(region string) (*RDSClient, error) {
	cfg, err := config.LoadDefaultConfig(context.TODO(), config.WithRegion(region))
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}

	return &RDSClient{
		client: rds.NewFromConfig(cfg),
		region: region,
	}, nil
}

func (r *RDSClient) GetProviderName() string {
	return "aws"
}

func (r *RDSClient) GetRegion() string {
	return r.region
}

func (r *RDSClient) CreateDBSnapshot(ctx context.Context, dbInstanceID string, snapshotName string) (string, error) {
	resp, err := r.client.CreateDBSnapshot(ctx, &rds.CreateDBSnapshotInput{
		DBInstanceIdentifier: aws.String(dbInstanceID),
		DBSnapshotIdentifier: aws.String(snapshotName),
		Tags: []rds.Tag{
			{Key: aws.String("Migration"), Value: aws.String("true")},
		},
	})
	if err != nil {
		return "", fmt.Errorf("failed to create DB snapshot: %w", err)
	}

	return *resp.DBSnapshot.DBSnapshotIdentifier, nil
}

func (r *RDSClient) WaitForDBSnapshotComplete(ctx context.Context, snapshotID string) error {
	waiter := rds.NewDBSnapshotAvailableWaiter(r.client)
	return waiter.Wait(ctx, &rds.DescribeDBSnapshotsInput{
		DBSnapshotIdentifier: aws.String(snapshotID),
	}, 30*time.Minute)
}

func (r *RDSClient) ExportDBSnapshotToS3(ctx context.Context, snapshotID string, bucketName string, prefix string) error {
	exportTaskID := fmt.Sprintf("export-%s-%d", snapshotID, time.Now().Unix())
	_, err := r.client.StartExportTask(ctx, &rds.StartExportTaskInput{
		ExportTaskIdentifier: aws.String(exportTaskID),
		SourceArn:            aws.String(fmt.Sprintf("arn:aws:rds:%s:snapshot:%s", r.region, snapshotID)),
		S3BucketName:         aws.String(bucketName),
		S3Prefix:             aws.String(prefix),
	})
	if err != nil {
		return fmt.Errorf("failed to start export task: %w", err)
	}

	return nil
}
