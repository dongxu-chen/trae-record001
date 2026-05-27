package cmd

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/cloud-migration-tool/config"
	"github.com/cloud-migration-tool/pkg/checkpoint"
	"github.com/cloud-migration-tool/pkg/cost"
	"github.com/cloud-migration-tool/pkg/dependency"
	"github.com/cloud-migration-tool/pkg/migration"
	"github.com/cloud-migration-tool/pkg/report"
	"github.com/cloud-migration-tool/pkg/rollback"
	"github.com/spf13/cobra"
)

var migrateCmd = &cobra.Command{
	Use:   "migrate",
	Short: "Migrate resources from source to destination cloud",
	Long:  `Migrate compute, database, and storage resources from source cloud to destination cloud.`,
	Run:   runMigrate,
}

func init() {
	rootCmd.AddCommand(migrateCmd)
	migrateCmd.Flags().Bool("compute", false, "Migrate compute instances (EC2 -> ECS/CVM)")
	migrateCmd.Flags().Bool("database", false, "Migrate databases (RDS)")
	migrateCmd.Flags().Bool("storage", false, "Migrate storage (S3 -> OSS/COS)")
	migrateCmd.Flags().Bool("all", true, "Migrate all resource types")
	migrateCmd.Flags().String("output", "", "Output migration report to file")
	migrateCmd.Flags().String("format", "text", "Report format: text, json, html, markdown")
	migrateCmd.Flags().String("resume", "", "Resume migration from checkpoint task ID")
	migrateCmd.Flags().Bool("list-checkpoints", false, "List all pending migration checkpoints")
	migrateCmd.Flags().Bool("no-checkpoint", false, "Disable checkpoint/resume functionality")
	migrateCmd.Flags().Bool("convert-image", true, "Enable image format conversion for cross-cloud compatibility")
	migrateCmd.Flags().Bool("analyze-deps", true, "Analyze resource dependencies before migration")
	migrateCmd.Flags().Bool("include-deps", true, "Include all dependent resources in migration")
	migrateCmd.Flags().Bool("auto-rollback", true, "Enable automatic rollback on migration failure")
	migrateCmd.Flags().String("rollback-plan", "", "Specify rollback plan ID")
	migrateCmd.Flags().Bool("cost-estimate", true, "Generate cost comparison report")
	migrateCmd.Flags().Float64("data-transfer-gb", 100, "Estimated data transfer in GB for cost calculation")
}

func runMigrate(cmd *cobra.Command, args []string) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigChan
		fmt.Println("\nReceived shutdown signal. Saving checkpoint and cancelling migration...")
		cancel()
	}()

	listCheckpoints, _ := cmd.Flags().GetBool("list-checkpoints")
	if listCheckpoints {
		listPendingCheckpoints()
		return
	}

	cfg, err := loadMigrationConfig()
	if err != nil {
		fmt.Printf("Failed to load config: %v\n", err)
		return
	}

	reportGen := report.NewReportGenerator()

	migrateCompute, _ := cmd.Flags().GetBool("compute")
	migrateDatabase, _ := cmd.Flags().GetBool("database")
	migrateStorage, _ := cmd.Flags().GetBool("storage")
	migrateAll, _ := cmd.Flags().GetBool("all")
	resumeTaskID, _ := cmd.Flags().GetString("resume")
	noCheckpoint, _ := cmd.Flags().GetBool("no-checkpoint")
	analyzeDeps, _ := cmd.Flags().GetBool("analyze-deps")
	includeDeps, _ := cmd.Flags().GetBool("include-deps")
	autoRollback, _ := cmd.Flags().GetBool("auto-rollback")
	rollbackPlanID, _ := cmd.Flags().GetString("rollback-plan")
	costEstimate, _ := cmd.Flags().GetBool("cost-estimate")
	dataTransferGB, _ := cmd.Flags().GetFloat64("data-transfer-gb")

	if migrateAll {
		migrateCompute = true
		migrateDatabase = true
		migrateStorage = true
	}

	fmt.Println("=== Cloud Migration Tool ===")
	fmt.Printf("Source: %s (%s)\n", cfg.Source.Provider, cfg.Source.Region)
	fmt.Printf("Destination: %s (%s)\n", cfg.Destination.Provider, cfg.Destination.Region)
	if resumeTaskID != "" {
		fmt.Printf("Resuming from checkpoint: %s\n", resumeTaskID)
	}
	if !noCheckpoint {
		fmt.Println("Checkpoint/Resume: Enabled")
	}
	if analyzeDeps {
		fmt.Println("Dependency Analysis: Enabled")
		if includeDeps {
			fmt.Println("Include Dependencies: Enabled")
		}
	}
	if autoRollback {
		fmt.Println("Auto Rollback: Enabled")
	}
	if costEstimate {
		fmt.Println("Cost Estimation: Enabled")
	}
	fmt.Println("============================")

	var rollbackMgr *rollback.RollbackManager
	var rollbackPlan *rollback.RollbackPlan
	if autoRollback {
		rollbackMgr, _ = rollback.NewRollbackManager("~/.cloud-migration/rollback")
		if rollbackPlanID != "" {
			rollbackPlan, _ = rollbackMgr.GetPlan(rollbackPlanID)
		}
		if rollbackPlan == nil {
			taskID := fmt.Sprintf("migration-%d", time.Now().Unix())
			rollbackPlan = rollbackMgr.CreatePlan(taskID, fmt.Sprintf("Migration %s->%s", cfg.Source.Provider, cfg.Destination.Provider), autoRollback)
			fmt.Printf("Rollback plan created: %s\n", rollbackPlan.ID)
		}
		rollbackPlan.UpdatePhase(rollback.PhasePreMigration)
	}

	if analyzeDeps {
		fmt.Println("\n[Dependency Analysis]")
		if err := analyzeDependencies(ctx, cfg, includeDeps); err != nil {
			fmt.Printf("  Warning: %v\n", err)
		}
	}

	if costEstimate {
		fmt.Println("\n[Cost Estimation]")
		if err := generateCostEstimate(ctx, cfg, dataTransferGB); err != nil {
			fmt.Printf("  Warning: %v\n", err)
		}
	}

	startTime := time.Now()

	if migrateCompute && len(cfg.Resources.EC2) > 0 {
		fmt.Println("\n[Compute Migration]")
		fmt.Printf("  Target image format: %s\n", migration.GetTargetFormatForProvider(cfg.Destination.Provider))
		if err := migrateComputeResources(ctx, cfg, reportGen); err != nil {
			fmt.Printf("Compute migration error: %v\n", err)
		}
	}

	if migrateDatabase && len(cfg.Resources.RDS) > 0 {
		fmt.Println("\n[Database Migration]")
		if err := migrateDatabaseResources(ctx, cfg, reportGen); err != nil {
			fmt.Printf("Database migration error: %v\n", err)
		}
	}

	if migrateStorage && len(cfg.Resources.S3) > 0 {
		fmt.Println("\n[Storage Migration]")
		if resumeTaskID != "" {
			if err := resumeStorageMigration(ctx, cfg, reportGen, resumeTaskID); err != nil {
				fmt.Printf("Storage migration resume error: %v\n", err)
			}
		} else {
			if err := migrateStorageResources(ctx, cfg, reportGen, !noCheckpoint); err != nil {
				fmt.Printf("Storage migration error: %v\n", err)
			}
		}
	}

	elapsed := time.Since(startTime)
	fmt.Printf("\n=== Migration Completed in %v ===\n", elapsed)

	report := reportGen.GenerateReport(
		cfg.Source.Provider, cfg.Source.Region,
		cfg.Destination.Provider, cfg.Destination.Region,
	)

	outputPath, _ := cmd.Flags().GetString("output")
	format, _ := cmd.Flags().GetString("format")

	var reportFormat report.ReportFormat
	switch format {
	case "json":
		reportFormat = report.FormatJSON
	case "html":
		reportFormat = report.FormatHTML
	case "markdown":
		reportFormat = report.FormatMarkdown
	default:
		reportFormat = report.FormatText
	}

	if err := reportGen.ExportReport(report, reportFormat, outputPath); err != nil {
		fmt.Printf("Failed to export report: %v\n", err)
	}

	if outputPath != "" {
		fmt.Printf("Report saved to: %s\n", outputPath)
	}
}

func listPendingCheckpoints() {
	cm, err := checkpoint.NewCheckpointManager("")
	if err != nil {
		fmt.Printf("Failed to create checkpoint manager: %v\n", err)
		return
	}

	checkpoints := cm.GetPendingCheckpoints()
	if len(checkpoints) == 0 {
		fmt.Println("No pending checkpoints found.")
		return
	}

	fmt.Println("Pending Migration Checkpoints:")
	fmt.Println("==============================")
	for _, cp := range checkpoints {
		progress, transferred, total := cm.GetProgress(cp.TaskID)
		fmt.Printf("\nTask ID: %s\n", cp.TaskID)
		fmt.Printf("  Type: %s\n", cp.TaskType)
		fmt.Printf("  Source: %s -> %s\n", cp.Source, cp.Destination)
		fmt.Printf("  Status: %s\n", cp.Status)
		fmt.Printf("  Progress: %.2f%% (%d/%d bytes)\n", progress, transferred, total)
		fmt.Printf("  Objects: %d total, %d completed, %d failed\n", 
			cp.TotalObjects, cp.Completed, cp.Failed)
		fmt.Printf("  Checkpoint file: %s\n", cm.GetCheckpointFilePath(cp.TaskID))
	}
}

func loadMigrationConfig() (*config.MigrationConfig, error) {
	if cfgFile != "" {
		return config.LoadConfig(cfgFile)
	}

	return &config.MigrationConfig{
		Source: config.CloudConfig{
			Provider: "aws",
			Region:   "us-east-1",
		},
		Destination: config.CloudConfig{
			Provider: "aliyun",
			Region:   "cn-hangzhou",
		},
		Resources: config.ResourceConfig{},
	}, nil
}

func migrateComputeResources(ctx context.Context, cfg *config.MigrationConfig, reportGen *report.ReportGenerator) error {
	convertImage, _ := rootCmd.Flags().GetBool("convert-image")
	if !convertImage {
		fmt.Println("  Image conversion: Disabled")
	}

	for _, ec2 := range cfg.Resources.EC2 {
		fmt.Printf("  Migrating EC2 instance: %s\n", ec2.InstanceID)

		cm, err := migration.NewComputeMigration(cfg.Source, cfg.Destination)
		if err != nil {
			return fmt.Errorf("failed to create compute migration: %w", err)
		}

		if err := cm.MigrateInstance(ctx, ec2); err != nil {
			fmt.Printf("    Error: %v\n", err)
		} else {
			fmt.Printf("    Status: %s (%.1f%%)\n", cm.GetStatus().Status, cm.GetProgress())
			if targetFormat, ok := cm.GetStatus().TargetInfo["image_format"].(string); ok {
				fmt.Printf("    Image format: %s\n", targetFormat)
			}
		}

		reportGen.AddTaskStatus(cm.GetStatus())
	}
	return nil
}

func migrateDatabaseResources(ctx context.Context, cfg *config.MigrationConfig, reportGen *report.ReportGenerator) error {
	for _, rds := range cfg.Resources.RDS {
		fmt.Printf("  Migrating RDS instance: %s\n", rds.DBInstanceID)

		dm, err := migration.NewDatabaseMigration(cfg.Source, cfg.Destination)
		if err != nil {
			return fmt.Errorf("failed to create database migration: %w", err)
		}

		if err := dm.MigrateDatabase(ctx, rds); err != nil {
			fmt.Printf("    Error: %v\n", err)
		} else {
			fmt.Printf("    Status: %s\n", dm.GetStatus().Status)
		}

		reportGen.AddTaskStatus(dm.GetStatus())
	}
	return nil
}

func migrateStorageResources(ctx context.Context, cfg *config.MigrationConfig, reportGen *report.ReportGenerator, enableCheckpoint bool) error {
	for _, s3 := range cfg.Resources.S3 {
		fmt.Printf("  Migrating S3 bucket: %s -> %s\n", s3.Bucket, s3.TargetBucket)

		sm, err := migration.NewStorageMigration(cfg.Source, cfg.Destination)
		if err != nil {
			return fmt.Errorf("failed to create storage migration: %w", err)
		}

		sm.EnableResume(enableCheckpoint)

		if err := sm.MigrateBucket(ctx, s3); err != nil {
			fmt.Printf("    Error: %v\n", err)
			if enableCheckpoint {
				fmt.Printf("    Checkpoint saved: %s\n", sm.GetCheckpointFilePath())
				fmt.Printf("    To resume, run: cloud-migrate migrate --resume %s\n", sm.GetTaskID())
			}
		} else {
			fmt.Printf("    Status: %s (%.1f%%)\n", sm.GetStatus().Status, sm.GetStatus().Progress)
		}

		reportGen.AddTaskStatus(sm.GetStatus())
	}
	return nil
}

func resumeStorageMigration(ctx context.Context, cfg *config.MigrationConfig, reportGen *report.ReportGenerator, taskID string) error {
	for _, s3 := range cfg.Resources.S3 {
		fmt.Printf("  Resuming migration for bucket: %s -> %s\n", s3.Bucket, s3.TargetBucket)

		sm, err := migration.NewStorageMigration(cfg.Source, cfg.Destination)
		if err != nil {
			return fmt.Errorf("failed to create storage migration: %w", err)
		}

		if err := sm.ResumeFromCheckpoint(ctx, taskID, s3); err != nil {
			fmt.Printf("    Error: %v\n", err)
		} else {
			fmt.Printf("    Status: %s (%.1f%%)\n", sm.GetStatus().Status, sm.GetStatus().Progress)
		}

		reportGen.AddTaskStatus(sm.GetStatus())
	}
	return nil
}

func analyzeDependencies(ctx context.Context, cfg *config.MigrationConfig, includeDeps bool) error {
	analyzer := dependency.NewDependencyAnalyzer()

	targetResources := make([]*dependency.Resource, 0)
	for _, ec2 := range cfg.Resources.EC2 {
		targetResources = append(targetResources, &dependency.Resource{
			ID:       ec2.InstanceID,
			Type:     dependency.ResourceTypeEC2,
			Name:     ec2.Name,
			Provider: cfg.Source.Provider,
			Region:   cfg.Source.Region,
			Attributes: map[string]interface{}{
				"instance_type": ec2.InstanceType,
			},
		})
	}

	result, err := analyzer.Analyze(ctx, cfg.Source.Provider, targetResources)
	if err != nil {
		return fmt.Errorf("dependency analysis failed: %w", err)
	}

	fmt.Printf("  Detected %d resources and %d dependencies\n", len(result.AllResources), len(result.Dependencies))

	if len(result.Warning) > 0 {
		fmt.Println("  Warnings:")
		for _, w := range result.Warning {
			fmt.Printf("    - %s\n", w)
		}
	}

	fmt.Println("  Migration order (by dependency):")
	for i, resID := range result.MigrationOrder {
		res := result.AllResources[0]
		for _, r := range result.AllResources {
			if r.ID == resID {
				res = r
				break
			}
		}
		fmt.Printf("    %d. [%s] %s (%s)\n", i+1, res.Type, res.Name, res.ID)
	}

	if len(result.RootResources) > 0 {
		fmt.Println("  Root resources (no dependencies):")
		for _, res := range result.RootResources {
			fmt.Printf("    - [%s] %s (%s)\n", res.Type, res.Name, res.ID)
		}
	}

	if includeDeps {
		fmt.Println("  All dependent resources will be included in migration")
	}

	return nil
}

func generateCostEstimate(ctx context.Context, cfg *config.MigrationConfig, dataTransferGB float64) error {
	ca, err := cost.NewCostAnalyzer("~/.cloud-migration/cost")
	if err != nil {
		return fmt.Errorf("failed to create cost analyzer: %w", err)
	}

	sourceItems := make([]*cost.CostItem, 0)
	destItems := make([]*cost.CostItem, 0)

	for _, ec2 := range cfg.Resources.EC2 {
		sourceCost, err := ca.GetComputeCost(cfg.Source.Provider, cfg.Source.Region, "m5.large", 0)
		if err != nil {
			sourceCost, _ = ca.GetComputeCost(cfg.Source.Provider, cfg.Source.Region, "t2.large", 0)
		}
		sourceCost.ResourceID = ec2.InstanceID
		sourceCost.ResourceName = ec2.Name
		sourceItems = append(sourceItems, sourceCost)

		destInstanceType := ec2.InstanceType
		if destInstanceType == "" {
			destInstanceType = "ecs.g6.large"
			if cfg.Destination.Provider == "tencent" {
				destInstanceType = "S4.MEDIUM4"
			}
		}
		destCost, _ := ca.GetComputeCost(cfg.Destination.Provider, cfg.Destination.Region, destInstanceType, 0)
		destCost.ResourceID = ec2.InstanceID
		destCost.ResourceName = ec2.Name
		destItems = append(destItems, destCost)
	}

	for _, s3 := range cfg.Resources.S3 {
		sourceStorage, _ := ca.GetStorageCost(cfg.Source.Provider, cfg.Source.Region, "s3", 500)
		sourceStorage.ResourceID = s3.Bucket
		sourceStorage.ResourceName = s3.Bucket
		sourceItems = append(sourceItems, sourceStorage)

		destStorageType := "oss"
		if cfg.Destination.Provider == "tencent" {
			destStorageType = "cos"
		}
		destStorage, _ := ca.GetStorageCost(cfg.Destination.Provider, cfg.Destination.Region, destStorageType, 500)
		destStorage.ResourceID = s3.TargetBucket
		destStorage.ResourceName = s3.TargetBucket
		destItems = append(destItems, destStorage)
	}

	comparison, err := ca.AnalyzeCostComparison(
		ctx,
		cfg.Source.Provider, cfg.Source.Region,
		cfg.Destination.Provider, cfg.Destination.Region,
		sourceItems, destItems,
		dataTransferGB,
	)
	if err != nil {
		return fmt.Errorf("cost comparison failed: %w", err)
	}

	fmt.Println(ca.GenerateCostReport(comparison))

	return nil
}
