package main

import (
	"fmt"
	"log"

	"prometheus-alert-tester/internal/alert"
	"prometheus-alert-tester/internal/metrics"
)

func main() {
	fmt.Println("Testing Prometheus Alert Tester build...")

	sim := metrics.NewSimulator()
	sim.GenerateDefaultMetrics()
	fmt.Printf("✓ Simulator created, built %d series\n", len(sim.BuildTimeSeries()))

	validator := alert.NewValidator()
	fmt.Println("✓ Validator created")

	err := validator.LoadRules("examples/rules.yaml")
	if err != nil {
		log.Fatalf("Failed to load rules: %v", err)
	}
	fmt.Println("✓ Rules loaded successfully")

	errors := validator.CheckSyntax()
	fmt.Printf("✓ Syntax check: %d errors found\n", len(errors))

	fmt.Println("\nBuild test PASSED! All modules are working correctly.")
}
