package cmd

import (
	"fmt"

	"github.com/cloud-migration-tool/pkg/report"
	"github.com/spf13/cobra"
)

var reportCmd = &cobra.Command{
	Use:   "report",
	Short: "Generate migration reports",
	Long:  `Generate detailed migration reports in various formats (text, json, html, markdown).`,
	Run:   runReport,
}

func init() {
	rootCmd.AddCommand(reportCmd)
	reportCmd.Flags().String("format", "text", "Report format: text, json, html, markdown")
	reportCmd.Flags().String("output", "", "Output report to file")
	reportCmd.Flags().String("source-cloud", "aws", "Source cloud provider")
	reportCmd.Flags().String("source-region", "us-east-1", "Source cloud region")
	reportCmd.Flags().String("dest-cloud", "aliyun", "Destination cloud provider")
	reportCmd.Flags().String("dest-region", "cn-hangzhou", "Destination cloud region")
}

func runReport(cmd *cobra.Command, args []string) {
	format, _ := cmd.Flags().GetString("format")
	outputPath, _ := cmd.Flags().GetString("output")
	sourceCloud, _ := cmd.Flags().GetString("source-cloud")
	sourceRegion, _ := cmd.Flags().GetString("source-region")
	destCloud, _ := cmd.Flags().GetString("dest-cloud")
	destRegion, _ := cmd.Flags().GetString("dest-region")

	fmt.Println("=== Generating Migration Report ===")
	fmt.Printf("Format: %s\n", format)
	fmt.Printf("Source: %s (%s)\n", sourceCloud, sourceRegion)
	fmt.Printf("Destination: %s (%s)\n", destCloud, destRegion)
	if outputPath != "" {
		fmt.Printf("Output: %s\n", outputPath)
	}
	fmt.Println("====================================")

	reportGen := report.NewReportGenerator()

	report := reportGen.GenerateReport(sourceCloud, sourceRegion, destCloud, destRegion)

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
		return
	}

	if outputPath != "" {
		fmt.Printf("\nReport successfully generated: %s\n", outputPath)
	}

	fmt.Printf("\nReport Summary:\n")
	fmt.Printf("  Total Tasks: %d\n", report.Summary.TotalTasks)
	fmt.Printf("  Completed: %d\n", report.Summary.CompletedTasks)
	fmt.Printf("  Failed: %d\n", report.Summary.FailedTasks)
	fmt.Printf("  Success Rate: %.1f%%\n", report.Summary.SuccessRate*100)
	fmt.Printf("  Estimated Cost: $%.2f %s\n", report.CostEstimate.TotalEstimatedCost, report.CostEstimate.Currency)
}
