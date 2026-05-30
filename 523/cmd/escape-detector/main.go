package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/sirupsen/logrus"

	"github.com/security/container-escape-detector/internal/alert"
	"github.com/security/container-escape-detector/internal/attacker"
	"github.com/security/container-escape-detector/internal/behavior"
	"github.com/security/container-escape-detector/internal/config"
	"github.com/security/container-escape-detector/internal/container"
	"github.com/security/container-escape-detector/internal/ebpf"
	"github.com/security/container-escape-detector/internal/metrics"
	"github.com/security/container-escape-detector/internal/protection"
	"github.com/security/container-escape-detector/internal/rules"
	"github.com/security/container-escape-detector/internal/simulator"
	"github.com/security/container-escape-detector/internal/threatintel"
	"github.com/security/container-escape-detector/pkg/types"
)

var (
	version   = "1.0.0"
	buildTime = "unknown"
	gitCommit = "unknown"
)

type Detector struct {
	config         *config.Config
	logger         *logrus.Logger
	ebpfCollector  *ebpf.Collector
	containerMgr   *container.Manager
	behaviorEng    *behavior.Analyzer
	rulesEng       *rules.Engine
	attackAnalyz   *attacker.Analyzer
	alertMgr       *alert.Manager
	metricsExp     *metrics.Exporter
	escapeSim      *simulator.EscapeSimulator
	protectionMgr  *protection.Manager
	threatIntelMgr *threatintel.Manager
	eventChan      chan *types.BPFEvent
	wg             sync.WaitGroup
	ctx            context.Context
	cancel         context.CancelFunc
	running        bool
	mu             sync.Mutex
}

func main() {
	configPath := flag.String("config", "", "Path to configuration file")
	logLevel := flag.String("log-level", "", "Log level (debug, info, warn, error)")
	testMode := flag.Bool("test", false, "Run in test mode with simulated events")
	showVersion := flag.Bool("version", false, "Show version information")
	dumpRules := flag.Bool("dump-rules", false, "Dump all loaded detection rules")
	listContainers := flag.Bool("list-containers", false, "List detected containers and exit")

	flag.Parse()

	if *showVersion {
		fmt.Printf("Container Escape Detector v%s\n", version)
		fmt.Printf("  Build time: %s\n", buildTime)
		fmt.Printf("  Git commit: %s\n", gitCommit)
		return
	}

	logger := logrus.New()
	logger.SetFormatter(&logrus.TextFormatter{
		FullTimestamp:   true,
		TimestampFormat: time.RFC3339Nano,
	})
	logger.SetOutput(os.Stdout)

	cfg, err := config.Load(*configPath, logger)
	if err != nil {
		logger.Fatalf("Failed to load config: %v", err)
	}

	if *logLevel != "" {
		cfg.LogLevel = *logLevel
	}
	logger.SetLevel(cfg.GetLogLevel())

	logger.Infof("Starting Container Escape Detector v%s", version)
	logger.Debugf("Configuration: %+v", cfg)

	detector := NewDetector(cfg, logger)

	if *dumpRules {
		if err := detector.Init(); err != nil {
			logger.Fatalf("Failed to initialize: %v", err)
		}
		detector.DumpRules()
		return
	}

	if *listContainers {
		if err := detector.Init(); err != nil {
			logger.Fatalf("Failed to initialize: %v", err)
		}
		detector.ListContainers()
		return
	}

	if *testMode {
		logger.Info("Running in test mode with simulated events")
		detector.RunTestMode()
		return
	}

	if err := detector.Run(); err != nil {
		logger.Fatalf("Detector failed: %v", err)
	}
}

func NewDetector(cfg *config.Config, logger *logrus.Logger) *Detector {
	ctx, cancel := context.WithCancel(context.Background())

	return &Detector{
		config:    cfg,
		logger:    logger,
		eventChan: make(chan *types.BPFEvent, 10000),
		ctx:       ctx,
		cancel:    cancel,
	}
}

func (d *Detector) Init() error {
	var err error

	d.containerMgr = container.NewManager(d.logger, &container.Config{
		RefreshInterval: d.config.Container.RefreshInterval,
		DockerSocket:    d.config.Container.DockerSocket,
		UseProcFS:       d.config.Container.UseProcFS,
		UseDockerAPI:    d.config.Container.UseDockerAPI,
	})
	if err := d.containerMgr.Init(); err != nil {
		d.logger.Errorf("Failed to initialize container manager: %v", err)
		d.logger.Warn("Continuing without container metadata")
	}

	d.behaviorEng = behavior.NewAnalyzer(d.logger, &behavior.Config{
		BaselineMode:     d.config.Behavior.BaselineMode,
		BaselineDuration: d.config.Behavior.BaselineDuration,
		AnomalyThreshold: d.config.Behavior.AnomalyThreshold,
		ProcessTreeDepth: d.config.Behavior.ProcessTreeDepth,
		MaxHistorySize:   d.config.Behavior.MaxHistorySize,
	})

	d.rulesEng = rules.NewEngine(d.logger)
	if d.config.Rules.LoadBuiltin {
		if err := d.rulesEng.LoadBuiltinRules(); err != nil {
			return fmt.Errorf("failed to load builtin rules: %w", err)
		}
		d.logger.Infof("Loaded %d builtin rules", d.rulesEng.RuleCount())
	}

	if d.config.Rules.CustomRulesDir != "" {
		if err := d.rulesEng.LoadRulesFromDir(d.config.Rules.CustomRulesDir); err != nil {
			d.logger.Warnf("Failed to load custom rules: %v", err)
		} else {
			d.logger.Infof("Loaded %d total rules", d.rulesEng.RuleCount())
		}
	}

	if d.config.Behavior.MountWhitelist != nil && d.config.Behavior.MountWhitelist.Enabled {
		whitelist := &types.MountWhitelist{
			ContainerPatterns: d.config.Behavior.MountWhitelist.ContainerPatterns,
		}
		for _, entry := range d.config.Behavior.MountWhitelist.Paths {
			whitelist.Paths = append(whitelist.Paths, types.MountWhitelistEntry{
				Source:      entry.Source,
				Target:      entry.Target,
				FSType:      entry.FSType,
				Description: entry.Description,
			})
		}
		d.behaviorEng.SetMountWhitelist(whitelist)
		d.rulesEng.SetMountWhitelist(whitelist)
		d.logger.Infof("Mount whitelist enabled with %d paths", len(whitelist.Paths))
	}

	d.attackAnalyz = attacker.NewAnalyzer(d.logger, &attacker.Config{
		EnableAttackChain: d.config.Analysis.EnableAttackChain,
		EnableRiskScore:   d.config.Analysis.EnableRiskScore,
		RiskWindowMinutes: d.config.Analysis.RiskWindowMinutes,
	})

	d.alertMgr = alert.NewManager(d.logger, &d.config.Alert)

	if d.config.Metrics.Enabled {
		d.metricsExp = metrics.NewExporter(d.logger)
	}

	if d.config.BPF.Enabled {
		d.ebpfCollector = ebpf.NewCollector(d.logger, &ebpf.Config{
			PerfBufferSize: d.config.BPF.PerfBufferSize,
			Events:         d.config.BPF.Events,
			FallbackMode:   d.config.BPF.FallbackMode,
		})
		if err := d.ebpfCollector.Init(); err != nil {
			d.logger.Errorf("Failed to initialize eBPF collector: %v", err)
			d.logger.Warn("Continuing in fallback mode")
			d.config.BPF.FallbackMode = true
		}
	}

	d.escapeSim = simulator.NewEscapeSimulator(d.logger, &d.config.Simulator)
	d.escapeSim.SetEventCallback(func(event *types.BPFEvent) {
		select {
		case d.eventChan <- event:
		default:
			d.logger.Warn("Event channel full, dropping simulator event")
		}
	})

	d.protectionMgr = protection.NewManager(d.logger, &d.config.Protection)

	d.threatIntelMgr = threatintel.NewManager(d.logger, &d.config.ThreatIntel)

	return nil
}

func (d *Detector) Run() error {
	if err := d.Init(); err != nil {
		return fmt.Errorf("initialization failed: %w", err)
	}

	d.mu.Lock()
	d.running = true
	d.mu.Unlock()

	if err := d.startComponents(); err != nil {
		return fmt.Errorf("failed to start components: %w", err)
	}

	d.wg.Add(1)
	go d.processEvents()

	if d.config.Metrics.Enabled && d.metricsExp != nil {
		if err := d.metricsExp.Start(d.config.Metrics.ListenAddr); err != nil {
			d.logger.Errorf("Failed to start metrics server: %v", err)
		}
	}

	d.logger.Info("Container Escape Detector is running")
	d.printBanner()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM, syscall.SIGHUP)

	select {
	case sig := <-sigChan:
		d.logger.Infof("Received signal %s, shutting down", sig)
	case <-d.ctx.Done():
		d.logger.Info("Context cancelled, shutting down")
	}

	d.Stop()
	return nil
}

func (d *Detector) startComponents() error {
	if err := d.alertMgr.Start(); err != nil {
		return fmt.Errorf("failed to start alert manager: %w", err)
	}

	if d.ebpfCollector != nil && !d.config.BPF.FallbackMode {
		if err := d.ebpfCollector.Start(d.eventChan); err != nil {
			return fmt.Errorf("failed to start eBPF collector: %w", err)
		}
	}

	if err := d.escapeSim.Start(); err != nil {
		return fmt.Errorf("failed to start escape simulator: %w", err)
	}

	if err := d.protectionMgr.Start(); err != nil {
		return fmt.Errorf("failed to start protection manager: %w", err)
	}

	if err := d.threatIntelMgr.Start(); err != nil {
		return fmt.Errorf("failed to start threat intel manager: %w", err)
	}

	return nil
}

func (d *Detector) processEvents() {
	defer d.wg.Done()

	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	alertTicker := time.NewTicker(5 * time.Second)
	defer alertTicker.Stop()

	for {
		select {
		case <-d.ctx.Done():
			return

		case event, ok := <-d.eventChan:
			if !ok {
				return
			}
			d.handleEvent(event)

		case <-ticker.C:
			d.updateMetrics()

		case <-alertTicker.C:
			d.updateAlertEndpoints()
		}
	}
}

func (d *Detector) handleEvent(event *types.BPFEvent) {
	containerInfo := d.containerMgr.AssociateProcess(event.PID, event.PIDNS, event.MNTNS)

	if d.metricsExp != nil {
		d.metricsExp.RecordEvent(event, containerInfo)
	}

	d.behaviorEng.Analyze(event, containerInfo)

	threatMatches := d.threatIntelMgr.MatchEvent(event)
	for _, match := range threatMatches {
		d.logger.Warnf("Threat intel match: %s (%s) - %s on %s",
			match.SignatureName, match.SignatureID, match.MatchedValue, match.MatchedOn)
	}

	matchedRules := d.rulesEng.Evaluate(event, containerInfo)

	for _, rule := range matchedRules {
		if d.metricsExp != nil {
			d.metricsExp.RecordRuleEvaluation(rule.ID, true)
		}

		var attackPath *types.AttackChain
		var processNode *types.ProcessNode
		var profile *types.BehaviorProfile

		if containerInfo != nil {
			profile, _ = d.behaviorEng.GetProfile(containerInfo.ID)
		}

		if d.config.Analysis.EnableAttackChain && containerInfo != nil {
			processNode, _ = d.behaviorEng.GetProcessNode(containerInfo.ID, int(event.PID))
			attackPath, _ = d.attackAnalyz.ReconstructEscapePath(event, containerInfo, processNode, profile)
		}

		alert := d.alertMgr.GenerateAlert(
			event,
			containerInfo,
			rule,
			profile,
			attackPath,
			processNode,
		)

		if len(threatMatches) > 0 {
			alert.Evidence = append(alert.Evidence, fmt.Sprintf("Threat intel matches: %d", len(threatMatches)))
			for _, tm := range threatMatches {
				alert.Evidence = append(alert.Evidence, fmt.Sprintf("  - %s (%s)", tm.SignatureName, tm.SignatureID))
			}
		}

		d.alertMgr.Send(alert)

		if d.metricsExp != nil {
			d.metricsExp.RecordAlert(alert)

			if attackPath != nil {
				d.metricsExp.RecordAttackChain(attackPath, containerInfo)
			}
		}

		protecAction := d.protectionMgr.EvaluateAlert(alert, containerInfo)
		if protecAction != nil && len(protecAction.Actions) > 0 {
			d.logger.Warnf("Protection action triggered: %s", protecAction)
			if err := d.protectionMgr.ExecuteAction(protecAction); err != nil {
				d.logger.Errorf("Failed to execute protection action: %v", err)
			}
		}

		d.logger.Info(alert.FormatAlertForConsole(alert))
	}

	for _, rule := range d.rulesEng.GetRules() {
		notMatched := true
		for _, matched := range matchedRules {
			if matched.ID == rule.ID {
				notMatched = false
				break
			}
		}
		if notMatched && d.metricsExp != nil {
			d.metricsExp.RecordRuleEvaluation(rule.ID, false)
		}
	}

	if event.EventType == types.EventMount {
		suspicious := d.rulesEng.IsSuspiciousMount(event)
		if d.metricsExp != nil {
			d.metricsExp.RecordMountEvent(suspicious, containerInfo)
		}
		if suspicious {
			d.metricsExp.RecordSuspiciousProcess(containerInfo)
		}
	}
}

func (d *Detector) updateMetrics() {
	if d.metricsExp == nil {
		return
	}

	count := d.containerMgr.ContainerCount()
	d.metricsExp.SetMonitoredContainers(count)

	containers := d.containerMgr.GetAllContainers()
	for _, c := range containers {
		profile, _ := d.behaviorEng.GetProfile(c.ID)
		if profile != nil && d.config.Analysis.EnableRiskScore {
			risk := d.attackAnalyz.GenerateRiskAssessment(c, profile)
			d.metricsExp.RecordContainerRisk(c, risk.RiskScore, risk.OverallRisk)
		}
	}
}

func (d *Detector) updateAlertEndpoints() {
	if d.metricsExp == nil {
		return
	}

	recentAlerts := d.alertMgr.GetRecentAlerts(100)
	d.metricsExp.UpdateAlerts(recentAlerts)

	containers := d.containerMgr.GetAllContainers()
	riskAssessments := make(map[string]*types.RiskAssessment)
	for _, c := range containers {
		profile, _ := d.behaviorEng.GetProfile(c.ID)
		if profile != nil {
			risk := d.attackAnalyz.GenerateRiskAssessment(c, profile)
			riskAssessments[c.ID] = risk
		}
	}
	d.metricsExp.UpdateRiskAssessments(riskAssessments)
}

func (d *Detector) RunTestMode() {
	if err := d.Init(); err != nil {
		d.logger.Fatalf("Failed to initialize: %v", err)
	}

	d.mu.Lock()
	d.running = true
	d.mu.Unlock()

	if err := d.startComponents(); err != nil {
		d.logger.Fatalf("Failed to start components: %v", err)
	}

	d.wg.Add(1)
	go d.processEvents()

	if d.config.Metrics.Enabled && d.metricsExp != nil {
		if err := d.metricsExp.Start(d.config.Metrics.ListenAddr); err != nil {
			d.logger.Errorf("Failed to start metrics server: %v", err)
		}
	}

	d.logger.Info("Test mode running. Generating simulated events...")

	d.generateTestEvents()

	d.logger.Info("Test events generated. Press Ctrl+C to exit.")

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
	<-sigChan

	d.Stop()
}

func (d *Detector) generateTestEvents() {
	time.Sleep(2 * time.Second)

	testEvents := []struct {
		name  string
		event *types.BPFEvent
	}{
		{
			name: "Docker Socket Mount",
			event: &types.BPFEvent{
				EventType:    types.EventMount,
				Timestamp:    time.Now(),
				PID:          12345,
				PPID:         12344,
				UID:          0,
				GID:          0,
				Comm:         "mount",
				PIDNS:        4026532456,
				MNTNS:        4026532457,
				MountSource:  "/var/run/docker.sock",
				MountTarget:  "/host/docker.sock",
				FSType:       "bind",
				MountFlags:   0xC0ED,
			},
		},
		{
			name: "Sensitive Directory Mount",
			event: &types.BPFEvent{
				EventType:    types.EventMount,
				Timestamp:    time.Now(),
				PID:          12346,
				PPID:         12344,
				UID:          0,
				GID:          0,
				Comm:         "mount",
				PIDNS:        4026532456,
				MNTNS:        4026532457,
				MountSource:  "/dev/sda1",
				MountTarget:  "/host/root",
				FSType:       "ext4",
				MountFlags:   0,
			},
		},
		{
			name: "Privileged Syscall - mknod",
			event: &types.BPFEvent{
				EventType:    types.EventSyscall,
				Timestamp:    time.Now(),
				PID:          12347,
				PPID:         12344,
				UID:          0,
				GID:          0,
				Comm:         "mknod",
				PIDNS:        4026532456,
				MNTNS:        4026532457,
				SyscallNr:    133,
				SyscallName:  "mknod",
				FileName:     "/host/dev/sda",
			},
		},
		{
			name: "Kernel Module Load",
			event: &types.BPFEvent{
				EventType:    types.EventModule,
				Timestamp:    time.Now(),
				PID:          12348,
				PPID:         12344,
				UID:          0,
				GID:          0,
				Comm:         "insmod",
				PIDNS:        4026532456,
				MNTNS:        4026532457,
				ModuleName:   "evil_module",
			},
		},
		{
			name: "Capability Abuse - SYS_ADMIN",
			event: &types.BPFEvent{
				EventType:    types.EventCapability,
				Timestamp:    time.Now(),
				PID:          12349,
				PPID:         12344,
				UID:          0,
				GID:          0,
				Comm:         "mount",
				PIDNS:        4026532456,
				MNTNS:        4026532457,
				CapName:      "CAP_SYS_ADMIN",
				CapAction:    "granted",
				CapAudit:     1,
			},
		},
		{
			name: "Namespace Manipulation - setns",
			event: &types.BPFEvent{
				EventType:    types.EventNamespace,
				Timestamp:    time.Now(),
				PID:          12350,
				PPID:         12344,
				UID:          0,
				GID:          0,
				Comm:         "nsenter",
				PIDNS:        4026532456,
				MNTNS:        4026532457,
				NsType:       "pid",
				NsTarget:     1,
			},
		},
		{
			name: "Ptrace Attack",
			event: &types.BPFEvent{
				EventType:    types.EventPtrace,
				Timestamp:    time.Now(),
				PID:          12351,
				PPID:         12344,
				UID:          0,
				GID:          0,
				Comm:         "evil_ptrace",
				PIDNS:        4026532456,
				MNTNS:        4026532457,
				PtraceRequest: "PTRACE_ATTACH",
				PtraceTargetPID: 1,
			},
		},
	}

	for _, test := range testEvents {
		d.logger.Infof("Simulating event: %s", test.name)
		select {
		case d.eventChan <- test.event:
		case <-d.ctx.Done():
			return
		}
		time.Sleep(1 * time.Second)
	}

	time.Sleep(3 * time.Second)
	d.logger.Info("All test events processed")
	d.logger.Info("Check /metrics and /alerts endpoints for results")
}

func (d *Detector) Stop() {
	d.mu.Lock()
	if !d.running {
		d.mu.Unlock()
		return
	}
	d.running = false
	d.mu.Unlock()

	d.logger.Info("Shutting down Container Escape Detector")

	d.cancel()

	if d.ebpfCollector != nil {
		d.ebpfCollector.Close()
	}

	if d.alertMgr != nil {
		d.alertMgr.Close()
	}

	if d.metricsExp != nil {
		d.metricsExp.Close()
	}

	if d.escapeSim != nil {
		d.escapeSim.Stop()
	}

	if d.protectionMgr != nil {
		d.protectionMgr.Stop()
	}

	if d.threatIntelMgr != nil {
		d.threatIntelMgr.Stop()
	}

	close(d.eventChan)

	d.wg.Wait()

	d.logger.Info("Container Escape Detector stopped")
}

func (d *Detector) DumpRules() {
	fmt.Println("\n=== Loaded Detection Rules ===")
	for _, rule := range d.rulesEng.GetRules() {
		fmt.Printf("\nRule ID: %s\n", rule.ID)
		fmt.Printf("  Name: %s\n", rule.Name)
		fmt.Printf("  Severity: %s\n", rule.Severity)
		fmt.Printf("  Score: %.1f\n", rule.Score)
		fmt.Printf("  Description: %s\n", rule.Description)
		fmt.Printf("  Mitigation: %s\n", rule.Mitigation)
		fmt.Printf("  Tags: %v\n", rule.Tags)
	}
	fmt.Printf("\nTotal rules: %d\n", d.rulesEng.RuleCount())
}

func (d *Detector) ListContainers() {
	containers := d.containerMgr.GetAllContainers()

	fmt.Println("\n=== Detected Containers ===")
	if len(containers) == 0 {
		fmt.Println("  No containers detected")
		return
	}

	for _, c := range containers {
		fmt.Printf("\nContainer ID: %s\n", c.ID[:12])
		fmt.Printf("  Name: %s\n", c.Name)
		fmt.Printf("  Image: %s\n", c.Image)
		fmt.Printf("  Status: %s\n", c.Status)
		fmt.Printf("  PID: %d\n", c.PID)
		fmt.Printf("  PIDNS: %d\n", c.PIDNS)
		fmt.Printf("  MNTNS: %d\n", c.MNTNS)
		fmt.Printf("  Privileged: %v\n", c.Privileged)
		fmt.Printf("  Capabilities: %v\n", c.Capabilities)
		fmt.Printf("  Mounts: %d\n", len(c.Mounts))
	}
	fmt.Printf("\nTotal containers: %d\n", len(containers))
}

func (d *Detector) printBanner() {
	banner := `
╔══════════════════════════════════════════════════════════════╗
║              Container Escape Detector                       ║
║              Security Monitoring System                      ║
╠══════════════════════════════════════════════════════════════╣
║  Version: %-10s   Build: %-20s   ║
║  Metrics: http://%s/metrics                                  ║
║  Alerts:  http://%s/alerts                                   ║
║  Health:  http://%s/health                                   ║
║  Risk:    http://%s/risk                                     ║
╚══════════════════════════════════════════════════════════════╝
`
	fmt.Printf(banner,
		version,
		gitCommit[:8],
		d.config.Metrics.ListenAddr,
		d.config.Metrics.ListenAddr,
		d.config.Metrics.ListenAddr,
		d.config.Metrics.ListenAddr,
	)
}
