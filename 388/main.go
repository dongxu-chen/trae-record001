package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/sirupsen/logrus"

	"container-security-monitor/pkg/baseline"
	"container-security-monitor/pkg/config"
	"container-security-monitor/pkg/correlation"
	"container-security-monitor/pkg/detector"
	"container-security-monitor/pkg/ebpf"
	"container-security-monitor/pkg/metrics"
	"container-security-monitor/pkg/output"
	"container-security-monitor/pkg/remediation"
	"container-security-monitor/pkg/rules"
	"container-security-monitor/pkg/threatintel"
)

func main() {
	logrus.SetFormatter(&logrus.JSONFormatter{})
	logrus.SetLevel(logrus.InfoLevel)

	cfg, err := config.Load("config/config.yaml")
	if err != nil {
		logrus.Fatalf("Failed to load config: %v", err)
	}

	switch cfg.LogLevel {
	case "debug":
		logrus.SetLevel(logrus.DebugLevel)
	case "warn":
		logrus.SetLevel(logrus.WarnLevel)
	case "error":
		logrus.SetLevel(logrus.ErrorLevel)
	}

	ruleEngine, err := rules.NewEngine(cfg.RulesDir)
	if err != nil {
		logrus.Fatalf("Failed to create rule engine: %v", err)
	}
	logrus.Infof("Loaded rules from %s", cfg.RulesDir)

	eventDetector := detector.NewDetector(ruleEngine, cfg.Whitelist)
	logrus.Info("Security detector initialized with whitelist")

	var baselineMgr *baseline.BaselineManager
	if cfg.Baseline.Enabled {
		baselineMode := baseline.ModeHybrid
		switch cfg.Baseline.Mode {
		case "learning":
			baselineMode = baseline.ModeLearning
		case "detecting":
			baselineMode = baseline.ModeDetecting
		}
		baselineMgr = baseline.NewBaselineManager(
			baselineMode,
			cfg.Baseline.LearningPeriod,
			cfg.Baseline.BaselineDir,
		)
		logrus.Infof("Baseline manager initialized in %s mode, learning period: %v",
			baselineMode.String(), cfg.Baseline.LearningPeriod)
	}

	var correlationEng *correlation.CorrelationEngine
	if cfg.Correlation.Enabled {
		correlationEng = correlation.NewCorrelationEngine(
			cfg.Correlation.TimeWindow,
			cfg.Correlation.MaxBufferSize,
		)
		logrus.Infof("Correlation engine initialized, time window: %v, buffer size: %d",
			cfg.Correlation.TimeWindow, cfg.Correlation.MaxBufferSize)
	}

	var threatIntelMgr *threatintel.ThreatIntelManager
	if cfg.ThreatIntel.Enabled {
		threatIntelMgr = threatintel.NewThreatIntelManager(cfg.ThreatIntel)
		threatIntelMgr.Start()
		defer threatIntelMgr.Stop()
		logrus.Infof("Threat intelligence manager initialized, auto-block: %v",
			cfg.ThreatIntel.AutoBlock)
	}

	remediationMgr := remediation.NewRemediationManager(cfg.Remediation)
	remediationMgr.Start()
	defer remediationMgr.Stop()

	metricsServer := metrics.NewServer(cfg.MetricsAddr)
	go func() {
		logrus.Infof("Metrics server listening on %s", cfg.MetricsAddr)
		if err := metricsServer.Start(); err != nil {
			logrus.Errorf("Metrics server error: %v", err)
		}
	}()

	eventOutput, err := output.NewManager(cfg.Outputs)
	if err != nil {
		logrus.Fatalf("Failed to create output manager: %v", err)
	}

	ebpfManager := ebpf.NewManager()
	if err := ebpfManager.Load(); err != nil {
		logrus.Warnf("eBPF load warning: %v", err)
	}
	defer ebpfManager.Close()

	logrus.Infof("Monitor mode: %s", ebpfManager.GetMode().String())

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	eventChan := make(chan interface{}, 1000)

	if err := ebpfManager.Run(ctx, eventChan); err != nil {
		logrus.Errorf("Failed to start monitor: %v", err)
	}

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	logrus.Info("Container Security Monitor started successfully")
	logRunningInfo(cfg, ebpfManager, baselineMgr, correlationEng, threatIntelMgr)

	for {
		select {
		case event := <-eventChan:
			if baselineMgr != nil {
				anomalies := baselineMgr.ProcessEvent(event)
				for _, anomaly := range anomalies {
					alert := &detector.SecurityAlert{
						RuleName:    "baseline_anomaly_" + anomaly.EventType,
						Severity:    anomaly.Severity,
						Message:     anomaly.Description,
						Remediation: "Review the activity against the established baseline and verify if it's legitimate.",
						ContainerID: anomaly.ContainerID,
						Timestamp:   anomaly.Timestamp,
						Tags:        []string{"baseline", "anomaly", anomaly.EventType},
						Fields: map[string]interface{}{
							"deviation":     anomaly.Deviation,
							"current_value": anomaly.CurrentValue,
							"baseline_info": anomaly.BaselineInfo,
						},
					}

					metricsServer.RecordAlert(alert)
					eventOutput.Send(alert)
					logAlert(alert)

					if remediationMgr.ShouldBlock(alert) {
						action := remediationMgr.ProcessAlert(alert)
						if action != nil {
							alert.Blocked = true
							logrus.WithFields(logrus.Fields{
								"action":       action.Type,
								"container_id": action.ContainerID,
								"status":       action.Status,
							}).Info("Remediation action executed for baseline anomaly")
						}
					}
				}
			}

			switch e := event.(type) {
			case ebpf.NetworkEvent:
				if threatIntelMgr != nil {
					daddr := intToIP(e.Daddr)
					match := threatIntelMgr.CheckIPAndPort(daddr, e.Dport)
					if match != nil {
						alert := &detector.SecurityAlert{
							RuleName:    "threat_intel_match",
							Severity:    match.Entry.Severity,
							Message:     fmt.Sprintf("Connection to %s (%s) detected: %s", daddr, match.Entry.Type, match.Entry.Description),
							Remediation: "Block the connection and investigate the source. Check for data exfiltration or C2 communication.",
							ContainerID: bytesToString(e.ContainerID[:]),
							PID:         e.PID,
							Comm:        bytesToString(e.Comm[:]),
							Timestamp:   match.Timestamp,
							Tags:        append([]string{"threat-intel", string(match.Entry.Type)}, match.Entry.Tags...),
							Fields: map[string]interface{}{
								"ip":          daddr,
								"port":        e.Dport,
								"threat_type": match.Entry.Type,
								"confidence":  match.Entry.Confidence,
								"source":      match.Entry.Source,
							},
						}

						metricsServer.RecordAlert(alert)
						eventOutput.Send(alert)
						logAlert(alert)

						if threatIntelMgr.ShouldBlock(match) {
							remediationCfg := remediationMgr.GetConfig()
							if remediationCfg.NetworkIsolate {
								if err := isolateContainer(remediationMgr, alert.ContainerID); err != nil {
									logrus.Errorf("Failed to isolate container for threat intel match: %v", err)
								} else {
									alert.Blocked = true
									logrus.Infof("Container %s isolated due to threat intel match with %s",
										alert.ContainerID, daddr)
								}
							}
						}
					}
				}
			}

			alerts := eventDetector.ProcessEvent(event)
			for _, alert := range alerts {
				metricsServer.RecordAlert(alert)

				if correlationEng != nil {
					chains := correlationEng.ProcessEvent(alert)
					for _, chain := range chains {
						go correlationEng.PrintChainSummary(chain)

						chainAlert := &detector.SecurityAlert{
							RuleName:    "attack_chain_detected",
							Severity:    chain.Severity,
							Message:     fmt.Sprintf("Attack chain detected: %s (confidence: %.1f%%)", chain.Description, chain.TotalConfidence*100),
							Remediation: chain.Remediation,
							ContainerID: chain.ContainerID,
							Timestamp:   chain.EndTime,
							Tags:        append([]string{"attack-chain", "correlation"}, chain.Indicators...),
							Fields: map[string]interface{}{
								"chain_id":     chain.ID,
								"confidence":   chain.TotalConfidence,
								"steps":        len(chain.Steps),
								"indicators":   chain.Indicators,
								"duration_sec": chain.EndTime.Sub(chain.StartTime).Seconds(),
							},
						}

						metricsServer.RecordAlert(chainAlert)
						eventOutput.Send(chainAlert)
						logAlert(chainAlert)

						if remediationMgr.ShouldBlock(chainAlert) {
							action := remediationMgr.ProcessAlert(chainAlert)
							if action != nil {
								chainAlert.Blocked = true
								logrus.WithFields(logrus.Fields{
									"action":       action.Type,
									"container_id": action.ContainerID,
									"status":       action.Status,
									"chain_id":     chain.ID,
								}).Info("Remediation action executed for attack chain")
							}
						}
					}
				}

				action := remediationMgr.ProcessAlert(alert)
				if action != nil {
					alert.Blocked = true
					logrus.WithFields(logrus.Fields{
						"action":       action.Type,
						"container_id": action.ContainerID,
						"status":       action.Status,
					}).Info("Remediation action executed")
				}

				eventOutput.Send(alert)
				logAlert(alert)
			}

		case <-sigChan:
			logrus.Info("Shutting down...")
			printSummary(remediationMgr, baselineMgr, correlationEng, threatIntelMgr)
			cancel()
			return
		}
	}
}

func logRunningInfo(cfg *config.Config, ebpfMgr *ebpf.Manager,
	baselineMgr *baseline.BaselineManager,
	correlationEng *correlation.CorrelationEngine,
	threatIntelMgr *threatintel.ThreatIntelManager) {

	fields := logrus.Fields{
		"mode":            ebpfMgr.GetMode().String(),
		"metrics_addr":    cfg.MetricsAddr,
		"rules_dir":       cfg.RulesDir,
		"auto_block":      cfg.Remediation.AutoBlock,
		"network_isolate": cfg.Remediation.NetworkIsolate,
		"block_severity":  cfg.Remediation.BlockSeverity,
	}

	if baselineMgr != nil {
		fields["baseline_mode"] = baselineMgr.GetMode().String()
		fields["baseline_learning_period"] = cfg.Baseline.LearningPeriod
	}

	if correlationEng != nil {
		fields["correlation_enabled"] = true
		fields["correlation_window"] = cfg.Correlation.TimeWindow
	}

	if threatIntelMgr != nil {
		stats := threatIntelMgr.GetStats()
		fields["threat_intel_enabled"] = true
		fields["threat_intel_ips"] = stats["ip_threats"]
		fields["threat_intel_domains"] = stats["domain_threats"]
	}

	logrus.WithFields(fields).Info("System configuration")
}

func logAlert(alert *detector.SecurityAlert) {
	logrus.WithFields(logrus.Fields{
		"rule":         alert.RuleName,
		"severity":     alert.Severity,
		"container_id": alert.ContainerID,
		"pid":          alert.PID,
		"comm":         alert.Comm,
		"blocked":      alert.Blocked,
	}).Warn(alert.Message)
}

func isolateContainer(rm *remediation.RemediationManager, containerID string) error {
	if containerID == "" {
		return fmt.Errorf("empty container ID")
	}

	if rm.IsQuarantined(containerID) {
		return nil
	}

	alert := &detector.SecurityAlert{
		ContainerID: containerID,
		Severity:    "high",
		RuleName:    "threat_intel_isolation",
	}

	rm.ProcessAlert(alert)
	return nil
}

func printSummary(rm *remediation.RemediationManager,
	baselineMgr *baseline.BaselineManager,
	correlationEng *correlation.CorrelationEngine,
	threatIntelMgr *threatintel.ThreatIntelManager) {

	fmt.Println("\n=== Container Security Monitor Summary ===")

	actions := rm.GetActions()
	quarantined := rm.GetQuarantinedContainers()

	fmt.Printf("Total remediation actions: %d\n", len(actions))
	fmt.Printf("Quarantined containers: %d\n", len(quarantined))

	if len(quarantined) > 0 {
		fmt.Println("\nQuarantined container IDs:")
		for _, id := range quarantined {
			fmt.Printf("  - %s\n", id)
		}
	}

	if len(actions) > 0 {
		fmt.Println("\nRecent remediation actions:")
		for i, action := range actions {
			if i >= 10 {
				fmt.Println("  ... (truncated)")
				break
			}
			fmt.Printf("  [%s] %s - %s (%s)\n",
				action.Timestamp.Format("15:04:05"),
				action.Type,
				action.ContainerID,
				action.Status)
		}
	}

	if baselineMgr != nil {
		baselines := baselineMgr.GetAllBaselines()
		fmt.Printf("\nBaseline profiles: %d containers\n", len(baselines))
		for id, bl := range baselines {
			progress := baselineMgr.GetLearningProgress(id)
			fmt.Printf("  - %s: %d processes, %d files, deviation=%.2f, progress=%.0f%%\n",
				id[:12], len(bl.Processes), len(bl.Files),
				baselineMgr.CalculateDeviationScore(id), progress*100)
		}
	}

	if correlationEng != nil {
		chains := correlationEng.GetAllChains()
		fmt.Printf("\nAttack chains detected: %d\n", len(chains))
		for id, chain := range chains {
			fmt.Printf("  - %s: %s (%s, %.1f%% confidence)\n",
				id[:16], chain.Description, chain.Severity,
				chain.TotalConfidence*100)
		}
	}

	if threatIntelMgr != nil {
		stats := threatIntelMgr.GetStats()
		fmt.Printf("\nThreat intelligence:\n")
		fmt.Printf("  - Known malicious IPs: %v\n", stats["ip_threats"])
		fmt.Printf("  - Known malicious domains: %v\n", stats["domain_threats"])
		fmt.Printf("  - Custom block entries: %v\n", stats["custom_blocks"])
	}

	fmt.Println("==========================================\n")
}

func bytesToString(b []byte) string {
	for i, c := range b {
		if c == 0 {
			return string(b[:i])
		}
	}
	return string(b)
}

func intToIP(ip uint32) string {
	return fmt.Sprintf("%d.%d.%d.%d", byte(ip>>24), byte(ip>>16), byte(ip>>8), byte(ip))
}
