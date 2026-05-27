package aliyun

import (
	"context"
	"fmt"
	"time"

	"github.com/aliyun/alibaba-cloud-sdk-go/services/rds"
)

type RDSClient struct {
	client *rds.Client
	region string
}

func NewRDSClient(region, accessKeyID, accessKeySecret string) (*RDSClient, error) {
	client, err := rds.NewClientWithAccessKey(region, accessKeyID, accessKeySecret)
	if err != nil {
		return nil, fmt.Errorf("failed to create RDS client: %w", err)
	}
	return &RDSClient{
		client: client,
		region: region,
	}, nil
}

func (r *RDSClient) GetProviderName() string {
	return "aliyun"
}

func (r *RDSClient) GetRegion() string {
	return r.region
}

func (r *RDSClient) CreateDBSnapshot(ctx context.Context, dbInstanceID string, snapshotName string) (string, error) {
	req := rds.CreateCreateBackupRequest()
	req.DBInstanceId = dbInstanceID
	req.BackupMethod = "Physical"
	req.BackupType = "FullBackup"

	resp, err := r.client.CreateBackup(req)
	if err != nil {
		return "", fmt.Errorf("failed to create DB backup: %w", err)
	}

	return resp.BackupJobId, nil
}

func (r *RDSClient) WaitForDBSnapshotComplete(ctx context.Context, backupJobID string) error {
	timeout := time.After(60 * time.Minute)
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-timeout:
			return fmt.Errorf("timeout waiting for backup %s", backupJobID)
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			req := rds.CreateDescribeBackupTasksRequest()
			req.BackupJobId = backupJobID
			resp, err := r.client.DescribeBackupTasks(req)
			if err != nil {
				continue
			}

			if len(resp.Items) > 0 {
				status := resp.Items[0].BackupStatus
				if status == "Success" {
					return nil
				}
			}
		}
	}
}

func (r *RDSClient) RestoreFromSnapshot(ctx context.Context, snapshotID, targetDBInstanceID string) error {
	req := rds.CreateRestoreDBInstanceRequest()
	req.DBInstanceId = targetDBInstanceID
	req.BackupId = snapshotID

	_, err := r.client.RestoreDBInstance(req)
	if err != nil {
		return fmt.Errorf("failed to restore DB instance: %w", err)
	}

	return nil
}

func (r *RDSClient) CreateDBInstance(ctx context.Context, dbName, dbType, engineVersion string, storage int) (string, error) {
	req := rds.CreateCreateDBInstanceRequest()
	req.DBInstanceClass = "rds.mysql.s2.large"
	req.DBInstanceStorage = fmt.Sprintf("%d", storage)
	req.Engine = dbType
	req.EngineVersion = engineVersion
	req.DBInstanceNetType = "Intranet"
	req.SecurityIPList = "0.0.0.0/0"
	req.DBInstanceDescription = fmt.Sprintf("Migrated from snapshot: %s", dbName)

	resp, err := r.client.CreateDBInstance(req)
	if err != nil {
		return "", fmt.Errorf("failed to create DB instance: %w", err)
	}

	return resp.DBInstanceId, nil
}
