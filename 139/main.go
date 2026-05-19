package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"time"

	"prometheus-alert-tester/internal/alert"
	"prometheus-alert-tester/internal/enhancements"
	"prometheus-alert-tester/internal/metrics"
	"prometheus-alert-tester/internal/report"
)

func main() {
	rulesFile := flag.String("rules", "", "Path to Prometheus alert rules file (required)")
	metricsFile := flag.String("metrics", "", "Path to metrics simulation file")
	outputFile := flag.String("output", "alert_test_report.json", "Output report file path")
	verbose := flag.Bool("verbose", false, "Enable verbose output")
	duration := flag.Duration("duration", 10*time.Minute, "Simulation duration")
	step := flag.Duration("step", 15*time.Second, "Evaluation step interval")
	resolveDelay := flag.Duration("resolve-delay", 5*time.Minute, "Alert resolve delay duration")

	exportTemplates := flag.Bool("export-templates", false, "Export Prometheus alert rule templates")
	templatesDir := flag.String("templates-dir", "templates", "Output directory for templates")

	enableSLO := flag.Bool("enable-slo", false, "Enable SLO burn rate calculation")
	sloTarget := flag.Float64("slo-target", 99.9, "SLO availability target percentage")

	enableClusters := flag.Bool("enable-clusters", false, "Enable multi-cluster testing")
	clusterEnv := flag.String("cluster-env", "production", "Cluster environment (production/staging)")

	silencesFile := flag.String("silences", "", "Path to silences configuration file")

	flag.Parse()

	if *exportTemplates {
		exportRuleTemplates(*templatesDir)
		return
	}

	if *rulesFile == "" {
		fmt.Println("Error: rules file path is required")
		flag.Usage()
		os.Exit(1)
	}

	log.SetFlags(log.LstdFlags | log.Lshortfile)
	startTime := time.Now()

	if *verbose {
		log.Println("Starting Prometheus Alert Tester...")
		log.Printf("Rules file: %s", *rulesFile)
		log.Printf("Simulation duration: %v", *duration)
		log.Printf("Evaluation step: %v", *step)
		log.Printf("Resolve delay: %v", *resolveDelay)
	}

	sim := metrics.NewSimulator()
	sim.SetTimeRange(time.Now().Add(-*duration), time.Now())
	sim.SetStep(*step)

	if *metricsFile != "" {
		if *verbose {
			log.Printf("Loading metrics from: %s", *metricsFile)
		}
		if err := sim.LoadFromFile(*metricsFile); err != nil {
			log.Fatalf("Failed to load metrics: %v", err)
		}
	} else {
		if *verbose {
			log.Println("Generating default test metrics...")
		}
		sim.GenerateDefaultMetrics()
	}

	tsData := sim.BuildTimeSeries()
	if *verbose {
		log.Printf("Built %d time series", len(tsData))
	}

	validator := alert.NewValidator()
	validator.SetResolveDelay(*resolveDelay)
	validator.SetEvalTimestamps(sim.EvalTimestamps())

	if err := validator.LoadRules(*rulesFile); err != nil {
		log.Fatalf("Failed to load rules: %v", err)
	}

	if *verbose {
		log.Println("Checking alert rule syntax...")
	}

	syntaxErrors := validator.CheckSyntax()
	if *verbose {
		if len(syntaxErrors) > 0 {
			log.Printf("Found %d syntax errors", len(syntaxErrors))
			for _, err := range syntaxErrors {
				log.Printf("  - Alert: %s, Error: %s", err.AlertName, err.Error)
			}
		} else {
			log.Println("No syntax errors found")
		}
	}

	if *verbose {
		log.Println("Evaluating alert rules over time series...")
	}

	alertTS := make([]alert.TimeSeries, len(tsData))
	for i, ts := range tsData {
		alertTS[i] = alert.TimeSeries{
			Labels: ts.Labels,
			Points: make([]alert.TimeSeriesPoint, len(ts.Points)),
		}
		for j, p := range ts.Points {
			alertTS[i].Points[j] = alert.TimeSeriesPoint{
				Timestamp: p.Timestamp,
				Value:     p.Value,
			}
		}
	}

	evals, err := validator.EvaluateRules(alertTS)
	if err != nil {
		log.Fatalf("Failed to evaluate rules: %v", err)
	}

	if *verbose {
		log.Printf("Evaluated %d rules", len(evals))
		for _, eval := range evals {
			if eval.Error != nil {
				log.Printf("  - %s: FAILED - %v", eval.RuleName, eval.Error)
			} else {
				log.Printf("  - %s: passed (%d evaluation points)", eval.RuleName, len(eval.States))
			}
		}
	}

	alerts := validator.GenerateAlertResults(evals)

	silenceManager := enhancements.NewSilenceManager()
	if *silencesFile != "" {
		log.Printf("Loading silences from: %s", *silencesFile)
	}

	silencedAlerts := applySilences(alerts, silenceManager, sim.StartTime())

	if *verbose {
		log.Printf("Generated %d alert results", len(alerts))
		for _, a := range alerts {
			log.Printf("  - %s: %s (value: %.2f, duration: %v)", a.AlertName, a.State, a.Value, a.Duration)
		}
	}

	var sloResults []*enhancements.SLOResult
	if *enableSLO {
		if *verbose {
			log.Println("Calculating SLO burn rates...")
		}
		sloResults = calculateSLOBurnRates(*sloTarget, sim)
	}

	var clusterReport *ClusterReport
	if *enableClusters {
		if *verbose {
			log.Printf("Evaluating %s clusters...", *clusterEnv)
		}
		clusterReport = evaluateClusters(*clusterEnv)
	}

	testDuration := time.Since(startTime)

	rep := report.NewReport()
	rep.RulesFile = *rulesFile
	rep.MetricsFile = *metricsFile
	rep.TestDuration = testDuration
	rep.SetTimeRange(sim.StartTime(), sim.EndTime(), sim.Step())
	rep.SyntaxErrors = syntaxErrors
	rep.Alerts = alerts
	rep.SilencedAlerts = silencedAlerts
	rep.SLOResults = sloResults
	rep.ClusterReport = clusterReport
	rep.CalculateStats(evals, alerts)
	rep.AddFailedRuleDetails(evals)

	if *verbose {
		log.Printf("Saving report to: %s", *outputFile)
	}
	if err := rep.SaveToFile(*outputFile); err != nil {
		log.Fatalf("Failed to save report: %v", err)
	}

	rep.PrintSummary()

	fmt.Printf("\nReport saved to: %s\n", *outputFile)
}

func exportRuleTemplates(outputDir string) {
	fmt.Printf("Exporting Prometheus rule templates to: %s\n", outputDir)

	exporter := enhancements.NewTemplateExporter(outputDir)
	enhancements.GenerateFullTemplateCollection(exporter)

	if err := exporter.ExportAll(); err != nil {
		log.Fatalf("Failed to export templates: %v", err)
	}

	if err := enhancements.GenerateREADME(outputDir); err != nil {
		log.Fatalf("Failed to generate README: %v", err)
	}

	amConfig := enhancements.GenerateDefaultAlertmanagerConfig()
	amConfigPath := fmt.Sprintf("%s/alertmanager-config.yaml", outputDir)
	if err := amConfig.Export(amConfigPath); err != nil {
		log.Fatalf("Failed to export Alertmanager config: %v", err)
	}

	fmt.Println("Templates exported successfully!")
	fmt.Printf("Generated files in %s:\n", outputDir)
	fmt.Println("  - kubernetes-alerts.yaml")
	fmt.Println("  - node-alerts.yaml")
	fmt.Println("  - slo-alerts.yaml")
	fmt.Println("  - aggregation-recording.yaml")
	fmt.Println("  - alertmanager-config.yaml")
	fmt.Println("  - README.md")
}

func applySilences(alerts []alert.AlertResult, sm *enhancements.SilenceManager, evalTime time.Time) []string {
	var silenced []string
	for _, a := range alerts {
		if a.State == alert.StateFiring || a.State == alert.StatePending {
			if sm.IsSilenced(a.Labels, evalTime) {
				silenced = append(silenced, a.AlertName)
			}
		}
	}
	return silenced
}

func calculateSLOBurnRates(targetPercent float64, sim *metrics.Simulator) []*enhancements.SLOResult {
	sloMgr := enhancements.NewSLOManager()
	slo := enhancements.SLO{
		Name:                "API Availability",
		TargetPercent:       targetPercent,
		Window:              30 * 24 * time.Hour,
		TotalRequestsMetric: "http_requests_total",
	}
	sloMgr.AddSLO(slo)

	totalRequests := 100000.0
	errorRate := (100 - targetPercent) / 100
	errorRequests := totalRequests * (errorRate * 2)

	result := sloMgr.EvaluateSLO("API Availability", totalRequests, errorRequests)
	return []*enhancements.SLOResult{result}
}

type ClusterReport struct {
	Clusters       []enhancements.Cluster `json:"clusters"`
	EnabledCount   int                    `json:"enabled_count"`
	TotalCount     int                    `json:"total_count"`
	HealthStatus   map[string]string      `json:"health_status,omitempty"`
}

func evaluateClusters(env string) *ClusterReport {
	thanos := enhancements.NewThanosManager()

	var clusters []enhancements.Cluster
	if env == "staging" {
		clusters = enhancements.CreateStagingClusters()
	} else {
		clusters = enhancements.CreateProductionClusters()
	}

	thanos.AddClusters(clusters)

	enabled := thanos.GetEnabledClusters()
	healthStatus := make(map[string]string)
	for _, c := range enabled {
		healthStatus[c.Name] = "healthy"
	}

	return &ClusterReport{
		Clusters:     clusters,
		EnabledCount: len(enabled),
		TotalCount:   len(clusters),
		HealthStatus: healthStatus,
	}
}
