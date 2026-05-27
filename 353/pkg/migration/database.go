package migration

import (
	"context"
	"fmt"
	"time"

	"github.com/cloud-migration-tool/config"
	"github.com/cloud-migration-tool/pkg/cloud"
	awscloud "github.com/cloud-migration-tool/pkg/cloud/aws"
	aliyuncloud "github.com/cloud-migration-tool/pkg/cloud/aliyun"
)

type DatabaseMigration struct {
	sourceDB cloud.DatabaseProvider
	destDB   interface{}
	status   *cloud.MigrationStatus
}

func NewDatabaseMigration(sourceCfg, destCfg config.CloudConfig) (*DatabaseMigration, error) {
	dm := &DatabaseMigration{
		status: &cloud.MigrationStatus{
			TaskID:     fmt.Sprintf("database-%d", time.Now().Unix()),
			Status:     "initialized",
			Progress:   0,
			StartTime:  time.Now().Unix(),
			SourceInfo: make(map[string]interface{}),
			TargetInfo: make(map[string]interface{}),
		},
	}

	switch sourceCfg.Provider {
	case "aws":
		rdsClient, err := awscloud.NewRDSClient(sourceCfg.Region)
		if err != nil {
			return nil, fmt.Errorf("failed to create AWS RDS client: %w", err)
		}
		dm.sourceDB = rdsClient
	default:
		return nil, fmt.Errorf("unsupported source provider: %s", sourceCfg.Provider)
	}

	switch destCfg.Provider {
	case "aliyun":
		rdsClient, err := aliyuncloud.NewRDSClient(destCfg.Region, "", "")
		if err != nil {
			return nil, fmt.Errorf("failed to create Aliyun RDS client: %w", err)
		}
		dm.destDB = rdsClient
	default:
		return nil, fmt.Errorf("unsupported destination provider: %s", destCfg.Provider)
	}

	return dm, nil
}

func (dm *DatabaseMigration) MigrateDatabase(ctx context.Context, resource config.RDSResource) error {
	dm.status.Status = "running"
	dm.status.Message = fmt.Sprintf("Starting migration of database %s", resource.DBInstanceID)
	dm.status.SourceInfo["db_instance_id"] = resource.DBInstanceID

	snapshotName := fmt.Sprintf("migrate-db-snap-%s-%d", resource.DBInstanceID, time.Now().Unix())
	dm.status.Progress = 15
	dm.status.Message = fmt.Sprintf("Creating DB snapshot: %s", snapshotName)

	snapshotID, err := dm.sourceDB.CreateDBSnapshot(ctx, resource.DBInstanceID, snapshotName)
	if err != nil {
		dm.status.Status = "failed"
		dm.status.Message = fmt.Sprintf("Failed to create DB snapshot: %v", err)
		return fmt.Errorf("create DB snapshot failed: %w", err)
	}
	dm.status.SourceInfo["snapshot_id"] = snapshotID
	dm.status.Progress = 30

	dm.status.Message = fmt.Sprintf("Waiting for DB snapshot %s to complete", snapshotName)
	if err := dm.sourceDB.WaitForDBSnapshotComplete(ctx, snapshotID); err != nil {
		dm.status.Status = "failed"
		dm.status.Message = fmt.Sprintf("DB snapshot failed: %v", err)
		return fmt.Errorf("DB snapshot wait failed: %w", err)
	}
	dm.status.Progress = 50

	dm.status.Message = "Creating target RDS instance"
	if err := dm.createTargetDBInstance(ctx, resource); err != nil {
		dm.status.Status = "failed"
		dm.status.Message = fmt.Sprintf("Target DB creation failed: %v", err)
		return fmt.Errorf("create target DB failed: %w", err)
	}
	dm.status.Progress = 75

	dm.status.Message = "Restoring database to target instance"
	if err := dm.restoreToTarget(ctx, snapshotID, resource.TargetDBName); err != nil {
		dm.status.Status = "failed"
		dm.status.Message = fmt.Sprintf("DB restore failed: %v", err)
		return fmt.Errorf("DB restore failed: %w", err)
	}
	dm.status.Progress = 90

	dm.status.Progress = 100
	dm.status.Status = "completed"
	dm.status.EndTime = time.Now().Unix()
	dm.status.Message = "Database migration completed successfully"

	return nil
}

func (dm *DatabaseMigration) createTargetDBInstance(ctx context.Context, resource config.RDSResource) error {
	switch dest := dm.destDB.(type) {
	case *aliyuncloud.RDSClient:
		dbInstanceID, err := dest.CreateDBInstance(ctx, resource.TargetDBName, resource.DBType, "8.0", 100)
		if err != nil {
			return fmt.Errorf("create Aliyun RDS failed: %w", err)
		}
		dm.status.TargetInfo["db_instance_id"] = dbInstanceID
	default:
		return fmt.Errorf("unsupported destination DB type")
	}
	return nil
}

func (dm *DatabaseMigration) restoreToTarget(ctx context.Context, snapshotID, targetDBName string) error {
	switch dest := dm.destDB.(type) {
	case *aliyuncloud.RDSClient:
		targetDBID := dm.status.TargetInfo["db_instance_id"].(string)
		if err := dest.RestoreFromSnapshot(ctx, snapshotID, targetDBID); err != nil {
			return fmt.Errorf("restore to Aliyun RDS failed: %w", err)
		}
	default:
		return fmt.Errorf("unsupported destination DB type")
	}
	return nil
}

func (dm *DatabaseMigration) GetStatus() *cloud.MigrationStatus {
	return dm.status
}
