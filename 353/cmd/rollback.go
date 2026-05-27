package cmd

import (
	"context"
	"fmt"

	"github.com/cloud-migration-tool/pkg/rollback"
	"github.com/spf13/cobra"
)

var rollbackCmd = &cobra.Command{
	Use:   "rollback",
	Short: "Manage migration rollback plans",
	Long:  `List, view, and execute migration rollback plans for disaster recovery.`,
	Run:   runRollback,
}

func init() {
	rootCmd.AddCommand(rollbackCmd)
	rollbackCmd.Flags().String("plan", "", "Rollback plan ID to execute")
	rollbackCmd.Flags().Bool("list", false, "List all rollback plans")
	rollbackCmd.Flags().String("view", "", "View details of a specific rollback plan")
	rollbackCmd.Flags().String("trigger", "manual", "Rollback trigger type: manual, health_check, error_threshold, timeout")
	rollbackCmd.Flags().Bool("execute", false, "Execute the rollback plan")
	rollbackCmd.Flags().Bool("force", false, "Force rollback execution without confirmation")
}

func runRollback(cmd *cobra.Command, args []string) {
	rm, err := rollback.NewRollbackManager("~/.cloud-migration/rollback")
	if err != nil {
		fmt.Printf("Failed to create rollback manager: %v\n", err)
		return
	}

	listPlans, _ := cmd.Flags().GetBool("list")
	viewPlan, _ := cmd.Flags().GetString("view")
	planID, _ := cmd.Flags().GetString("plan")
	execute, _ := cmd.Flags().GetBool("execute")
	triggerType, _ := cmd.Flags().GetString("trigger")

	if listPlans {
		listRollbackPlans(rm)
		return
	}

	if viewPlan != "" {
		viewRollbackPlan(rm, viewPlan)
		return
	}

	if execute && planID != "" {
		trigger := rollback.TriggerManual
		switch triggerType {
		case "health_check":
			trigger = rollback.TriggerHealthCheck
		case "error_threshold":
			trigger = rollback.TriggerErrorThreshold
		case "timeout":
			trigger = rollback.TriggerTimeout
		}
		executeRollback(rm, planID, trigger)
		return
	}

	fmt.Println("Use --list, --view <plan-id>, or --execute --plan <plan-id>")
}

func listRollbackPlans(rm *rollback.RollbackManager) {
	plans := rm.ListPlans()
	if len(plans) == 0 {
		fmt.Println("No rollback plans found.")
		return
	}

	fmt.Println("Rollback Plans:")
	fmt.Println("================")
	for _, plan := range plans {
		fmt.Printf("\nPlan ID: %s\n", plan.ID)
		fmt.Printf("  Migration Task: %s\n", plan.MigrationTaskID)
		fmt.Printf("  Name: %s\n", plan.Name)
		fmt.Printf("  Status: %s\n", plan.CurrentPhase)
		fmt.Printf("  Actions: %d recorded\n", len(plan.Actions))
		fmt.Printf("  Auto-Rollback: %v\n", plan.AutoRollback)
		if plan.Trigger != "" {
			fmt.Printf("  Trigger: %s\n", plan.Trigger)
		}
	}
}

func viewRollbackPlan(rm *rollback.RollbackManager, planID string) {
	report, err := rm.GenerateRollbackReport(planID)
	if err != nil {
		fmt.Printf("Failed to generate report: %v\n", err)
		return
	}
	fmt.Println(report)
}

func executeRollback(rm *rollback.RollbackManager, planID string, trigger rollback.RollbackTrigger) {
	fmt.Printf("Executing rollback plan: %s\n", planID)
	fmt.Printf("Trigger type: %s\n", trigger)

	plan, exists := rm.GetPlan(planID)
	if !exists {
		fmt.Printf("Rollback plan not found: %s\n", planID)
		return
	}

	fmt.Printf("\nThis will rollback %d recorded actions:\n", len(plan.Actions))
	for _, action := range plan.Actions {
		fmt.Printf("  - %s %s: %s\n", action.ResourceType, action.ResourceID, action.Action)
	}

	ctx := context.Background()
	result, err := rm.ExecuteRollback(ctx, planID, trigger)
	if err != nil {
		fmt.Printf("\nRollback error: %v\n", err)
		return
	}

	fmt.Println("\nRollback Results:")
	fmt.Println("=================")
	fmt.Printf("Success: %v\n", result.Success)
	fmt.Printf("Actions processed: %d\n", result.ActionsCount)
	fmt.Printf("Failed actions: %d\n", result.FailedActions)
	fmt.Printf("Duration: %d seconds\n", result.Duration)

	if !result.Success {
		fmt.Printf("Error: %s\n", result.ErrorMessage)
	}

	if result.Success {
		fmt.Println("\n✅ Rollback completed successfully!")
		fmt.Println("All resources have been reverted to their original state.")
	} else {
		fmt.Println("\n⚠️  Rollback completed with errors.")
		fmt.Println("Please check the failed actions manually.")
	}
}
