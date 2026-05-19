//go:build ignore
// +build ignore

package main

import (
	"fmt"
	"prometheus-alert-tester/internal/alert"
	"prometheus-alert-tester/internal/metrics"
)

func main() {
	fmt.Println("Testing Prometheus Alert Tester...")

	sim := metrics.NewSimulator()
	sim.GenerateDefaultMetrics()
	fmt.Printf("Generated %d metrics\n", len(sim.GetMetrics()))

	validator := alert.NewValidator()
	err := validator.LoadRules("examples/rules.yaml")
	if err != nil {
		fmt.Printf("Error loading rules: %v\n", err)
		return
	}
	fmt.Println("Loaded rules successfully")

	errors := validator.CheckSyntax()
	fmt.Printf("Found %d syntax errors\n", len(errors))
	for _, e := range errors {
		fmt.Printf("  - %s: %s\n", e.AlertName, e.Error)
	}

	fmt.Println("Test completed successfully!")
}
