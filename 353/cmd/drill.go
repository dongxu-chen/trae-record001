package cmd

import (
	"context"
	"fmt"
	"time"

	"github.com/cloud-migration-tool/pkg/drill"
	"github.com/cloud-migration-tool/pkg/sandbox"
	"github.com/spf13/cobra"
)

var drillCmd = &cobra.Command{
	Use:   "drill",
	Short: "Run migration drills and cutover tests",
	Long:  `Run various migration drills including connectivity, data flow, cutover, and rollback tests.`,
	Run:   runDrill,
}

func init() {
	rootCmd.AddCommand(drillCmd)
	drillCmd.Flags().String("type", "connectivity", "Drill type: connectivity, data_flow, cutover, rollback, full")
	drillCmd.Flags().String("name", "", "Drill name")
	drillCmd.Flags().String("output", "", "Output drill report to file")
	drillCmd.Flags().Bool("sandbox", true, "Run drill in isolated sandbox environment")
	drillCmd.Flags().Bool("list-sandboxes", false, "List all active sandboxes")
	drillCmd.Flags().String("cleanup-sandbox", "", "Clean up a specific sandbox by ID")
	drillCmd.Flags().Duration("sandbox-duration", 4*time.Hour, "Sandbox auto-expiry duration")
}

func runDrill(cmd *cobra.Command, args []string) {
	listSandboxes, _ := cmd.Flags().GetBool("list-sandboxes")
	if listSandboxes {
		listActiveSandboxes()
		return
	}

	cleanupSandboxID, _ := cmd.Flags().GetString("cleanup-sandbox")
	if cleanupSandboxID != "" {
		cleanupSandbox(cleanupSandboxID)
		return
	}

	drillTypeStr, _ := cmd.Flags().GetString("type")
	name, _ := cmd.Flags().GetString("name")
	outputPath, _ := cmd.Flags().GetString("output")
	useSandbox, _ := cmd.Flags().GetBool("sandbox")
	sandboxDuration, _ := cmd.Flags().GetDuration("sandbox-duration")

	var drillType drill.DrillType
	switch drillTypeStr {
	case "connectivity":
		drillType = drill.DrillTypeConnectivity
	case "data_flow":
		drillType = drill.DrillTypeDataFlow
	case "cutover":
		drillType = drill.DrillTypeCutover
	case "rollback":
		drillType = drill.DrillTypeRollback
	case "full":
		drillType = drill.DrillTypeFull
	default:
		fmt.Printf("Unknown drill type: %s\n", drillTypeStr)
		return
	}

	if name == "" {
		name = fmt.Sprintf("%s-drill-%d", drillTypeStr, time.Now().Unix())
	}

	fmt.Println("=== Migration Drill ===")
	fmt.Printf("Drill Type: %s\n", drillType)
	fmt.Printf("Drill Name: %s\n", name)
	if useSandbox {
		fmt.Printf("Sandbox: Enabled (auto-expiry: %s)\n", sandboxDuration)
	} else {
		fmt.Println("Sandbox: Disabled (WARNING: Running in production environment)")
	}
	fmt.Println("========================")

	cfg, _ := loadMigrationConfig()

	dm := drill.NewDrillManager()
	dm.EnableSandbox(useSandbox)

	ctx := context.Background()
	result, err := dm.RunDrill(ctx, drillType, name, cfg, nil)
	if err != nil {
		fmt.Printf("Drill error: %v\n", err)
		return
	}

	fmt.Println("\n=== Drill Results ===")
	fmt.Printf("Status: %s\n", result.Status)
	fmt.Printf("Duration: %v\n", result.Duration)
	fmt.Printf("Sandbox Used: %v\n", result.UseSandbox)
	if result.SandboxInfo != nil {
		fmt.Printf("Sandbox ID: %s\n", result.SandboxInfo.SandboxID)
		fmt.Printf("Sandbox VPC: %s\n", result.SandboxInfo.VpcID)
		fmt.Printf("Sandbox Subnet: %s\n", result.SandboxInfo.SubnetID)
		fmt.Printf("Sandbox Sub-Account: %s\n", result.SandboxInfo.SubAccount.UserName)
		fmt.Printf("Sandbox Expires: %s\n", result.SandboxInfo.ExpiresAt.Format(time.RFC3339))
	}
	fmt.Printf("Passed: %d/%d (%.1f%%)\n", result.PassedCount, result.TotalCount, result.SuccessRate*100)
	fmt.Println("\nStep Details:")

	for i, step := range result.Steps {
		status := "PASS"
		if !step.Passed {
			status = "FAIL"
		}
		fmt.Printf("  [%s] Step %d: %s (%v)\n", status, i+1, step.Name, step.Duration)
		if step.Error != nil {
			fmt.Printf("       Error: %v\n", step.Error)
		}
	}

	fmt.Println("\n=== Isolation Policy ===")
	if result.SandboxInfo != nil {
		sm := sandbox.NewSandboxManager()
		policy := sm.GenerateIsolationPolicy(result.SandboxInfo.SandboxID)
		fmt.Printf("VPC Isolation: %v\n", policy["isolation"].(map[string]interface{})["vpc_isolation"])
		fmt.Printf("Subnet Isolation: %v\n", policy["isolation"].(map[string]interface{})["subnet_isolation"])
		fmt.Printf("Security Groups: %v\n", policy["isolation"].(map[string]interface{})["security_groups"])
		fmt.Printf("IAM Restrictions: %v\n", policy["isolation"].(map[string]interface{})["iam_restrictions"])
	} else {
		fmt.Println("No sandbox isolation applied (production mode)")
	}

	fmt.Println("\n=== Drill Report ===")
	fmt.Println(result.Report)

	if outputPath != "" {
		fmt.Printf("\nReport saved to: %s\n", outputPath)
	}

	if result.Status == "passed" {
		fmt.Println("\n✓ Drill PASSED - Ready for migration!")
		if result.UseSandbox {
			fmt.Println("  Tip: Sandbox environment will auto-expire. Run 'drill --cleanup-sandbox <ID>' to clean up early.")
		}
	} else {
		fmt.Println("\n✗ Drill FAILED - Please review and fix issues before migration.")
		if result.UseSandbox {
			fmt.Println("  The isolated sandbox environment is preserved for debugging.")
		}
	}
}

func listActiveSandboxes() {
	sm := sandbox.NewSandboxManager()
	sandboxes := sm.ListSandboxes()

	if len(sandboxes) == 0 {
		fmt.Println("No active sandboxes found.")
		return
	}

	fmt.Println("Active Sandboxes:")
	fmt.Println("================")
	for _, sb := range sandboxes {
		fmt.Printf("\nSandbox ID: %s\n", sb.SandboxID)
		fmt.Printf("  Name: %s\n", sb.Name)
		fmt.Printf("  Status: %s\n", sb.Status)
		fmt.Printf("  Provider: %s (%s)\n", sb.Provider, sb.Region)
		fmt.Printf("  VPC: %s\n", sb.VpcID)
		fmt.Printf("  Subnet: %s\n", sb.SubnetID)
		if sb.SubAccount != nil {
			fmt.Printf("  Sub-Account: %s\n", sb.SubAccount.UserName)
		}
		fmt.Printf("  Created: %s\n", sb.CreatedAt.Format(time.RFC3339))
		fmt.Printf("  Expires: %s\n", sb.ExpiresAt.Format(time.RFC3339))
		if time.Now().After(sb.ExpiresAt) {
			fmt.Println("  WARNING: Sandbox has expired")
		}
	}
}

func cleanupSandbox(sandboxID string) {
	sm := sandbox.NewSandboxManager()
	ctx := context.Background()

	fmt.Printf("Cleaning up sandbox: %s\n", sandboxID)
	if err := sm.DestroySandbox(ctx, sandboxID); err != nil {
		fmt.Printf("Failed to cleanup sandbox: %v\n", err)
		return
	}
	fmt.Println("Sandbox cleaned up successfully.")
}
