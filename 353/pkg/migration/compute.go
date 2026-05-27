package migration

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/cloud-migration-tool/config"
	"github.com/cloud-migration-tool/pkg/cloud"
	awscloud "github.com/cloud-migration-tool/pkg/cloud/aws"
	aliyuncloud "github.com/cloud-migration-tool/pkg/cloud/aliyun"
	tencentcloud "github.com/cloud-migration-tool/pkg/cloud/tencent"
	"github.com/cloud-migration-tool/pkg/imageconv"
)

type ComputeMigration struct {
	sourceCompute  cloud.ComputeProvider
	destCompute    interface{}
	sourceRegion   string
	destRegion     string
	destProvider   string
	status         *cloud.MigrationStatus
	imageConverter *imageconv.ImageConverter
	tempDir        string
	skipConversion bool
}

func NewComputeMigration(sourceCfg, destCfg config.CloudConfig) (*ComputeMigration, error) {
	cm := &ComputeMigration{
		sourceRegion: sourceCfg.Region,
		destRegion:   destCfg.Region,
		destProvider: destCfg.Provider,
		tempDir:      filepath.Join(os.TempDir(), "cloud-migration-images"),
		status: &cloud.MigrationStatus{
			TaskID:     fmt.Sprintf("compute-%d", time.Now().Unix()),
			Status:     "initialized",
			Progress:   0,
			StartTime:  time.Now().Unix(),
			SourceInfo: make(map[string]interface{}),
			TargetInfo: make(map[string]interface{}),
		},
	}

	if err := os.MkdirAll(cm.tempDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create temp directory: %w", err)
	}

	ic, err := imageconv.NewImageConverter(2, cm.tempDir)
	if err != nil {
		cm.skipConversion = true
	} else {
		cm.imageConverter = ic
	}

	switch sourceCfg.Provider {
	case "aws":
		ec2Client, err := awscloud.NewEC2Client(sourceCfg.Region)
		if err != nil {
			return nil, fmt.Errorf("failed to create AWS EC2 client: %w", err)
		}
		cm.sourceCompute = ec2Client
	default:
		return nil, fmt.Errorf("unsupported source provider: %s", sourceCfg.Provider)
	}

	switch destCfg.Provider {
	case "aliyun":
		ecsClient, err := aliyuncloud.NewECSClient(destCfg.Region, "", "")
		if err != nil {
			return nil, fmt.Errorf("failed to create Aliyun ECS client: %w", err)
		}
		cm.destCompute = ecsClient
	case "tencent":
		cvmClient, err := tencentcloud.NewCVMClient(destCfg.Region, "", "")
		if err != nil {
			return nil, fmt.Errorf("failed to create Tencent CVM client: %w", err)
		}
		cm.destCompute = cvmClient
	default:
		return nil, fmt.Errorf("unsupported destination provider: %s", destCfg.Provider)
	}

	return cm, nil
}

func (cm *ComputeMigration) MigrateInstance(ctx context.Context, resource config.EC2Resource) error {
	cm.status.Status = "running"
	cm.status.Message = fmt.Sprintf("Starting migration of instance %s", resource.InstanceID)
	cm.status.SourceInfo["instance_id"] = resource.InstanceID

	snapshotName := fmt.Sprintf("migrate-snap-%s-%d", resource.InstanceID, time.Now().Unix())
	cm.status.Progress = 10
	cm.status.Message = fmt.Sprintf("Creating snapshot: %s", snapshotName)

	snapshotID, err := cm.sourceCompute.CreateSnapshot(ctx, resource.InstanceID, snapshotName)
	if err != nil {
		cm.status.Status = "failed"
		cm.status.Message = fmt.Sprintf("Failed to create snapshot: %v", err)
		return fmt.Errorf("create snapshot failed: %w", err)
	}
	cm.status.SourceInfo["snapshot_id"] = snapshotID
	cm.status.Progress = 20

	cm.status.Message = fmt.Sprintf("Waiting for snapshot %s to complete", snapshotID)
	if err := cm.sourceCompute.WaitForSnapshotComplete(ctx, snapshotID); err != nil {
		cm.status.Status = "failed"
		cm.status.Message = fmt.Sprintf("Snapshot failed: %v", err)
		return fmt.Errorf("snapshot wait failed: %w", err)
	}
	cm.status.Progress = 30

	imageName := fmt.Sprintf("migrate-img-%s-%d", resource.InstanceID, time.Now().Unix())
	cm.status.Message = fmt.Sprintf("Creating image from snapshot: %s", imageName)

	imageID, err := cm.sourceCompute.CreateImageFromSnapshot(ctx, snapshotID, imageName)
	if err != nil {
		cm.status.Status = "failed"
		cm.status.Message = fmt.Sprintf("Failed to create image: %v", err)
		return fmt.Errorf("create image failed: %w", err)
	}
	cm.status.SourceInfo["image_id"] = imageID
	cm.status.Progress = 40

	cm.status.Message = fmt.Sprintf("Waiting for image %s to be available", imageID)
	if err := cm.sourceCompute.WaitForImageComplete(ctx, imageID); err != nil {
		cm.status.Status = "failed"
		cm.status.Message = fmt.Sprintf("Image creation failed: %v", err)
		return fmt.Errorf("image wait failed: %w", err)
	}
	cm.status.Progress = 50

	cm.status.Message = "Exporting image from source cloud"
	exportedImagePath, err := cm.exportImageToLocal(ctx, imageID, imageName)
	if err != nil {
		cm.status.Status = "failed"
		cm.status.Message = fmt.Sprintf("Image export failed: %v", err)
		return fmt.Errorf("export image failed: %w", err)
	}
	cm.status.Progress = 60
	cm.status.SourceInfo["exported_image_path"] = exportedImagePath

	if !cm.skipConversion {
		cm.status.Message = fmt.Sprintf("Converting image to %s format for %s", 
			imageconv.GetTargetFormatForCloud(cm.destProvider), cm.destProvider)
		
		convertedPath, err := cm.convertImageForCloud(ctx, exportedImagePath, imageName)
		if err != nil {
			cm.status.Status = "failed"
			cm.status.Message = fmt.Sprintf("Image conversion failed: %v", err)
			return fmt.Errorf("convert image failed: %w", err)
		}
		cm.status.TargetInfo["converted_image_path"] = convertedPath
		cm.status.Progress = 75

		cm.status.Message = "Verifying converted image"
		if err := cm.verifyImage(ctx, convertedPath); err != nil {
			cm.status.Status = "failed"
			cm.status.Message = fmt.Sprintf("Image verification failed: %v", err)
			return fmt.Errorf("verify image failed: %w", err)
		}
		cm.status.Progress = 80
	}

	cm.status.Message = "Importing converted image to destination cloud"
	if err := cm.importConvertedImage(ctx, imageID, imageName); err != nil {
		cm.status.Status = "failed"
		cm.status.Message = fmt.Sprintf("Image import failed: %v", err)
		return fmt.Errorf("import image failed: %w", err)
	}
	cm.status.Progress = 90

	cm.status.Message = fmt.Sprintf("Creating target instance of type %s", resource.InstanceType)
	if err := cm.createTargetInstance(ctx, resource); err != nil {
		cm.status.Status = "failed"
		cm.status.Message = fmt.Sprintf("Target instance creation failed: %v", err)
		return fmt.Errorf("create target instance failed: %w", err)
	}

	cm.cleanupTempFiles()

	cm.status.Progress = 100
	cm.status.Status = "completed"
	cm.status.EndTime = time.Now().Unix()
	cm.status.Message = "Migration completed successfully"

	return nil
}

func (cm *ComputeMigration) exportImageToLocal(ctx context.Context, imageID, imageName string) (string, error) {
	exportedPath := filepath.Join(cm.tempDir, fmt.Sprintf("%s.vmdk", imageName))
	cm.status.SourceInfo["export_format"] = "vmdk"
	return exportedPath, nil
}

func (cm *ComputeMigration) convertImageForCloud(ctx context.Context, sourcePath, imageName string) (string, error) {
	targetFormat := imageconv.GetTargetFormatForCloud(cm.destProvider)
	destPath := filepath.Join(cm.tempDir, fmt.Sprintf("%s.%s", imageName, targetFormat))

	cm.status.TargetInfo["target_format"] = string(targetFormat)

	status, err := cm.imageConverter.ConvertForCloud(ctx, sourcePath, destPath, cm.destProvider)
	if err != nil {
		return "", err
	}

	for status.Status != "completed" && status.Status != "failed" {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		default:
			time.Sleep(1 * time.Second)
			s, _ := cm.imageConverter.GetStatus(status.TaskID)
			if s != nil {
				status = s
				baseProgress := 60.0
				conversionProgress := s.Progress * 0.15
				cm.status.Progress = baseProgress + conversionProgress
			}
		}
	}

	if status.Status == "failed" {
		return "", fmt.Errorf("conversion failed: %s", status.Error)
	}

	return destPath, nil
}

func (cm *ComputeMigration) verifyImage(ctx context.Context, imagePath string) error {
	ok, err := cm.imageConverter.VerifyImage(ctx, imagePath)
	if err != nil {
		return fmt.Errorf("image verification error: %w", err)
	}
	if !ok {
		return fmt.Errorf("image verification failed")
	}
	cm.status.TargetInfo["image_verified"] = true
	return nil
}

func (cm *ComputeMigration) importConvertedImage(ctx context.Context, imageID, imageName string) error {
	switch dest := cm.destCompute.(type) {
	case *aliyuncloud.ECSClient:
		importedImageID, err := dest.ImportImage(ctx, imageID, imageName, "linux")
		if err != nil {
			return fmt.Errorf("import to Aliyun failed: %w", err)
		}
		cm.status.TargetInfo["image_id"] = importedImageID
		cm.status.TargetInfo["image_format"] = string(imageconv.GetTargetFormatForCloud("aliyun"))
		if err := dest.WaitForImageComplete(ctx, importedImageID); err != nil {
			return fmt.Errorf("wait for Aliyun image failed: %w", err)
		}
	case *tencentcloud.CVMClient:
		importedImageID, err := dest.CreateImageFromSnapshot(ctx, imageID, imageName)
		if err != nil {
			return fmt.Errorf("import to Tencent failed: %w", err)
		}
		cm.status.TargetInfo["image_id"] = importedImageID
		cm.status.TargetInfo["image_format"] = string(imageconv.GetTargetFormatForCloud("tencent"))
		if err := dest.WaitForImageComplete(ctx, importedImageID); err != nil {
			return fmt.Errorf("wait for Tencent image failed: %w", err)
		}
	default:
		return fmt.Errorf("unsupported destination compute type")
	}
	return nil
}

func (cm *ComputeMigration) exportAndImportImage(ctx context.Context, imageID, imageName string) error {
	return cm.importConvertedImage(ctx, imageID, imageName)
}

func (cm *ComputeMigration) createTargetInstance(ctx context.Context, resource config.EC2Resource) error {
	targetImageID := cm.status.TargetInfo["image_id"].(string)

	switch dest := cm.destCompute.(type) {
	case *aliyuncloud.ECSClient:
		instanceID, err := dest.CreateInstanceFromImage(ctx, targetImageID, resource.InstanceType, resource.TargetZone)
		if err != nil {
			return fmt.Errorf("create Aliyun ECS failed: %w", err)
		}
		cm.status.TargetInfo["instance_id"] = instanceID
	case *tencentcloud.CVMClient:
		instanceID, err := dest.RunInstances(ctx, targetImageID, resource.InstanceType, resource.TargetZone)
		if err != nil {
			return fmt.Errorf("create Tencent CVM failed: %w", err)
		}
		cm.status.TargetInfo["instance_id"] = instanceID
	default:
		return fmt.Errorf("unsupported destination compute type")
	}
	return nil
}

func (cm *ComputeMigration) cleanupTempFiles() {
	_ = os.RemoveAll(cm.tempDir)
}

func (cm *ComputeMigration) GetStatus() *cloud.MigrationStatus {
	return cm.status
}

func (cm *ComputeMigration) GetProgress() float64 {
	return cm.status.Progress
}

func (cm *ComputeMigration) GetTaskID() string {
	return cm.status.TaskID
}

func GetSupportedImageFormats() []string {
	return []string{
		string(imageconv.FormatVMDK),
		string(imageconv.FormatQCOW2),
		string(imageconv.FormatRAW),
		string(imageconv.FormatVHD),
		string(imageconv.FormatVHDX),
	}
}

func GetTargetFormatForProvider(provider string) string {
	return string(imageconv.GetTargetFormatForCloud(provider))
}
