package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/urfave/cli/v2"

	"github.com/coldstart-optimizer/coldstart/internal/analyzer"
	"github.com/coldstart-optimizer/coldstart/internal/cost"
	"github.com/coldstart-optimizer/coldstart/internal/ebpf"
	"github.com/coldstart-optimizer/coldstart/internal/geo"
	"github.com/coldstart-optimizer/coldstart/internal/optimizer"
	"github.com/coldstart-optimizer/coldstart/internal/pool"
	"github.com/coldstart-optimizer/coldstart/internal/predictive"
	"github.com/coldstart-optimizer/coldstart/internal/scheduler"
	"github.com/coldstart-optimizer/coldstart/internal/snapshot"
)

func main() {
	app := &cli.App{
		Name:    "coldstart",
		Usage:   "serverless cold-start profiler & optimizer",
		Version: "0.2.0",
		Flags: []cli.Flag{
			&cli.StringFlag{Name: "function", Aliases: []string{"f"}, Value: "demo-func", Usage: "function name"},
			&cli.StringFlag{Name: "runtime", Aliases: []string{"r"}, Value: "nodejs", Usage: "runtime: nodejs|python|java|go"},
			&cli.StringFlag{Name: "image", Aliases: []string{"i"}, Value: "", Usage: "image ref to pull"},
			&cli.StringFlag{Name: "container-id", Value: "", Usage: "container id"},
			&cli.StringFlag{Name: "log-path", Value: "", Usage: "containerd log file"},
			&cli.StringFlag{Name: "runtime-name", Value: "containerd", Usage: "runtime name"},
			&cli.StringFlag{Name: "socket", Value: "/run/containerd/containerd.sock", Usage: "runtime socket"},
			&cli.StringFlag{Name: "jaeger", Value: "", Usage: "jaeger collector endpoint (http://host:14268/api/traces)"},
			&cli.StringFlag{Name: "metrics", Value: "", Usage: "prometheus listen address (e.g. :9100)"},
			&cli.StringFlag{Name: "format", Value: "text", Usage: "report format: text|json"},
			&cli.BoolFlag{Name: "ebpf", Value: false, Usage: "enable eBPF tracing"},
		},
		Commands: []*cli.Command{
			{
				Name:  "profile",
				Usage: "profile a single cold start and emit a report",
				Action: func(c *cli.Context) error {
					return runProfile(c)
				},
			},
			{
				Name:  "daemon",
				Usage: "run as a long-running tracing daemon (Jaeger + Prometheus)",
				Action: func(c *cli.Context) error {
					return runDaemon(c)
				},
			},
			{
				Name:  "simulate",
				Usage: "simulate a cold-start profile for demo/test",
				Action: func(c *cli.Context) error {
					return runSimulate(c)
				},
			},
			{
				Name:  "preload-plan",
				Usage: "build a node-affinity aware image preload plan",
				Flags: []cli.Flag{
					&cli.StringSliceFlag{Name: "zone", Value: nil, Usage: "prefer availability zone"},
					&cli.StringFlag{Name: "pin-node", Value: "", Usage: "pin to specific node"},
					&cli.IntFlag{Name: "replicas", Value: 3, Usage: "number of preload replicas"},
					&cli.StringFlag{Name: "nodes-json", Value: "", Usage: "json file describing available nodes"},
				},
				Action: func(c *cli.Context) error {
					return runPreloadPlan(c)
				},
			},
			{
				Name:  "build-snapshot",
				Usage: "build a unified language snapshot",
				Flags: []cli.Flag{
					&cli.StringFlag{Name: "source", Aliases: []string{"s"}, Required: true, Usage: "source directory of the function"},
					&cli.StringFlag{Name: "cache", Aliases: []string{"c"}, Value: "/var/cache/coldstart", Usage: "snapshot cache dir"},
					&cli.StringFlag{Name: "runtime-version", Value: "auto", Usage: "runtime version"},
				},
				Action: func(c *cli.Context) error {
					return runBuildSnapshot(c)
				},
			},
			{
				Name:  "pool-demo",
				Usage: "demonstrate the leak-safe warm pool behavior",
				Flags: []cli.Flag{
					&cli.IntFlag{Name: "max-size", Value: 50, Usage: "max pool size"},
					&cli.IntFlag{Name: "max-conns", Value: 10, Usage: "max connections per env"},
					&cli.DurationFlag{Name: "idle-timeout", Value: 2 * time.Minute, Usage: "idle timeout"},
					&cli.DurationFlag{Name: "max-age", Value: 30 * time.Minute, Usage: "max age of an env"},
					&cli.DurationFlag{Name: "reclaim-timeout", Value: 15 * time.Second, Usage: "leak reclaim timeout"},
				},
				Action: func(c *cli.Context) error {
					return runPoolDemo(c)
				},
			},
			{
				Name:  "predict-preheat",
				Usage: "analyze scheduling history and predict resident functions for preheat",
				Flags: []cli.Flag{
					&cli.StringFlag{Name: "history", Aliases: []string{"h"}, Value: "", Usage: "JSON file with scheduling history"},
					&cli.IntFlag{Name: "lookback-days", Value: 14, Usage: "days to look back"},
					&cli.Float64Flag{Name: "threshold", Value: 0.5, Usage: "probability threshold"},
					&cli.Float64Flag{Name: "hot-threshold", Value: 3.0, Usage: "min invocations/day for hot function"},
					&cli.IntFlag{Name: "min-invocations", Value: 5, Usage: "min total invocations"},
					&cli.IntFlag{Name: "max-predictions", Value: 20, Usage: "max predictions to output"},
				},
				Action: func(c *cli.Context) error {
					return runPredictPreheat(c)
				},
			},
			{
				Name:  "geo-replicate",
				Usage: "plan snapshot replication across regions for local cold-start loading",
				Flags: []cli.Flag{
					&cli.StringFlag{Name: "snapshot-id", Value: "", Required: true, Usage: "snapshot ID to replicate"},
					&cli.StringFlag{Name: "source-region", Value: "cn-shanghai", Usage: "source region"},
					&cli.Int64Flag{Name: "size-bytes", Value: 200 * 1024 * 1024, Usage: "snapshot size in bytes"},
					&cli.IntFlag{Name: "max-regions", Value: 6, Usage: "max target regions"},
				},
				Action: func(c *cli.Context) error {
					return runGeoReplicate(c)
				},
			},
			{
				Name:  "cost-analyze",
				Usage: "analyze cold-start cost based on a profile",
				Flags: []cli.Flag{
					&cli.StringFlag{Name: "profile-json", Value: "", Usage: "path to a ColdStartProfile JSON"},
					&cli.Float64Flag{Name: "cpu-per-ms", Value: 0, Usage: "CPU cost per ms"},
					&cli.Float64Flag{Name: "mem-per-ms", Value: 0, Usage: "memory per ms cost"},
					&cli.Float64Flag{Name: "pull-per-gb", Value: 0, Usage: "pull cost per GB"},
					&cli.Float64Flag{Name: "io-per-gb", Value: 0, Usage: "IO cost per GB"},
					&cli.Float64Flag{Name: "latency-penalty", Value: 0, Usage: "latency penalty factor"},
					&cli.Int64Flag{Name: "monthly-invocations", Value: 1000000, Usage: "monthly invocation count"},
					&cli.StringFlag{Name: "currency", Value: "CNY", Usage: "currency (CNY|USD|EUR)"},
				},
				Action: func(c *cli.Context) error {
					return runCostAnalyze(c)
				},
			},
		},
		Action: func(c *cli.Context) error {
			return runProfile(c)
		},
	}

	if err := app.Run(os.Args); err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}

func runProfile(c *cli.Context) error {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	opts := analyzer.Options{
		Function:     c.String("function"),
		Runtime:      c.String("runtime"),
		ImageRef:     c.String("image"),
		ContainerID:  c.String("container-id"),
		LogPath:      c.String("log-path"),
		RuntimeName:  c.String("runtime-name"),
		SocketPath:   c.String("socket"),
		JaegerEP:     c.String("jaeger"),
		MetricsAddr:  c.String("metrics"),
		OutputFormat: c.String("format"),
		EnableEbpf:   c.Bool("ebpf"),
	}
	if opts.EnableEbpf {
		if err := ebpf.DefaultTracer().Start(ctx); err != nil {
			fmt.Fprintln(os.Stderr, "eBPF start warning:", err)
		}
		defer ebpf.DefaultTracer().Stop()
	}
	a, err := analyzer.New(opts)
	if err != nil {
		return err
	}
	defer a.Close(ctx)
	_, err = a.Run(ctx, os.Stdout)
	return err
}

func runDaemon(c *cli.Context) error {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	opts := analyzer.Options{
		Function:     c.String("function"),
		Runtime:      c.String("runtime"),
		JaegerEP:     c.String("jaeger"),
		MetricsAddr:  c.String("metrics"),
		OutputFormat: c.String("format"),
	}
	a, err := analyzer.New(opts)
	if err != nil {
		return err
	}
	defer a.Close(ctx)

	select {
	case <-ctx.Done():
		return nil
	}
}

func runSimulate(c *cli.Context) error {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	opts := analyzer.Options{
		Function:     c.String("function"),
		Runtime:      c.String("runtime"),
		OutputFormat: c.String("format"),
	}
	a, err := analyzer.New(opts)
	if err != nil {
		return err
	}
	defer a.Close(ctx)
	_, err = a.Run(ctx, os.Stdout)
	return err
}

func runPreloadPlan(c *cli.Context) error {
	eng := optimizer.NewOptimizer().Engine()

	function := c.String("function")
	runtime := c.String("runtime")
	image := c.String("image")
	if image == "" {
		image = fmt.Sprintf("docker.io/%s:latest", function)
	}

	var nodes []*scheduler.Node
	if f := c.String("nodes-json"); f != "" {
		data, err := os.ReadFile(f)
		if err != nil {
			return err
		}
		if err := json.Unmarshal(data, &nodes); err != nil {
			return err
		}
	}
	if len(nodes) == 0 {
		nodes = []*scheduler.Node{
			{Name: "node-0", Zone: "cn-shanghai-a", Labels: map[string]string{"coldstart.io/warm-prefer": "true", "coldstart.io/runtime-nodejs": "true"}},
			{Name: "node-1", Zone: "cn-shanghai-a", Labels: map[string]string{}},
			{Name: "node-2", Zone: "cn-shanghai-b", Labels: map[string]string{"coldstart.io/runtime-python": "true"}},
			{Name: "node-3", Zone: "cn-shanghai-c", Labels: map[string]string{"coldstart.io/warm-prefer": "true"}},
		}
	}

	plan, err := eng.BuildAffinityPlan(function, runtime, image, c.StringSlice("zone"), c.String("pin-node"), nodes, c.Int("replicas"))
	if err != nil {
		return err
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(plan)
}

func runBuildSnapshot(c *cli.Context) error {
	runtimeStr := c.String("runtime")
	sourceDir := c.String("source")
	cacheDir := c.String("cache")
	runtimeVer := c.String("runtime-version")

	lang := snapshot.Language(runtimeStr)
	res, err := snapshot.BuildForLanguage(lang, runtimeVer, sourceDir, cacheDir)
	if err != nil {
		return err
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(map[string]interface{}{
		"id":             res.ID,
		"format":         res.Format,
		"build_ms":       res.BuildTime.Milliseconds(),
		"total_bytes":    res.TotalSize,
		"original_bytes": res.OriginalSize,
		"ratio":          fmt.Sprintf("%.2f", res.Ratio),
		"entries":        len(res.Snapshot.Entries()),
	})
}

func runPoolDemo(c *cli.Context) error {
	cfg := pool.PoolConfig{
		MaxSize:        c.Int("max-size"),
		MaxConnsPerEnv: c.Int("max-conns"),
		IdleTimeout:    c.Duration("idle-timeout"),
		MaxAge:         c.Duration("max-age"),
		ReclaimTimeout: c.Duration("reclaim-timeout"),
		SweepInterval:  5 * time.Second,
	}
	p := pool.NewEnvPool(cfg)
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	p.Start(ctx)
	defer p.Stop()

	ids := []string{"env-1", "env-2", "env-3"}
	for _, id := range ids {
		env := pool.NewEnv(id, c.String("function"), c.String("runtime"), fmt.Sprintf("cont-%s", id), "node-0")
		if err := p.Put(env); err != nil {
			fmt.Fprintln(os.Stderr, "put env:", err)
		}
	}

	_ = ctx
	fmt.Printf("Pool stats after boot: %+v\n", p.Stats())
	fmt.Println("Pool demo running. Press Ctrl+C to stop.")
	<-ctx.Done()
	fmt.Printf("Final pool stats: %+v\n", p.Stats())
	return nil
}

func runPredictPreheat(c *cli.Context) error {
	cfg := predictive.PredictorConfig{
		HotThreshold:   c.Float64("hot-threshold"),
		MinInvocations: int64(c.Int("min-invocations")),
		LookbackDays:   c.Int("lookback-days"),
		ProbThreshold:  c.Float64("threshold"),
		MaxPredictions: c.Int("max-predictions"),
		DecayFactor:    0.9,
	}
	p := predictive.NewPredictor(cfg)

	if f := c.String("history"); f != "" {
		data, err := os.ReadFile(f)
		if err != nil {
			return err
		}
		var entries []predictive.HistoryEntry
		if err := json.Unmarshal(data, &entries); err != nil {
			return err
		}
		p.AddBatch(entries)
	} else {
		now := time.Now()
		for i := 0; i < 50; i++ {
			p.Add(predictive.HistoryEntry{
				Function:    c.String("function"),
				Runtime:     c.String("runtime"),
				ImageRef:    fmt.Sprintf("docker.io/%s:latest", c.String("function")),
				InvokedAt:   now.Add(-time.Duration(i*6)*time.Hour),
				Region:      "cn-shanghai",
				ColdStartMs: 1500,
				Node:        "node-0",
			})
		}
	}

	result := p.Predict(context.Background())
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(result)
}

func runGeoReplicate(c *cli.Context) error {
	store := geo.NewRegionStore()
	for _, r := range geo.DefaultRegionSet() {
		store.RegisterRegion(r)
	}
	cfg := geo.DefaultReplicationConfig()
	cfg.MaxRegions = c.Int("max-regions")
	replicator := geo.NewReplicator(store, cfg)

	plan, err := replicator.BuildPlan(context.Background(),
		c.String("function"),
		c.String("snapshot-id"),
		c.String("source-region"),
		c.Int64("size-bytes"),
		nil)
	if err != nil {
		return err
	}

	if err := replicator.Execute(context.Background(), plan); err != nil {
		return err
	}

	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(plan)
}

func runCostAnalyze(c *cli.Context) error {
	pricing := cost.PricingModel{
		Currency:             c.String("currency"),
		CPUPerMs:             c.Float64("cpu-per-ms"),
		MemoryMBPerMs:        c.Float64("mem-per-ms"),
		PullPerGB:            c.Float64("pull-per-gb"),
		IOPerGB:              c.Float64("io-per-gb"),
		LatencyPenalty:       c.Float64("latency-penalty"),
		InvocationsPerMonth:  c.Int64("monthly-invocations"),
	}
	if pricing.CPUPerMs == 0 {
		switch pricing.Currency {
		case "USD":
			pricing = cost.CheapPricing()
		default:
			pricing = cost.DefaultPricing()
		}
		if c.String("currency") != "" {
			pricing.Currency = c.String("currency")
		}
	}

	var profile model.ColdStartProfile
	if f := c.String("profile-json"); f != "" {
		data, err := os.ReadFile(f)
		if err != nil {
			return err
		}
		if err := json.Unmarshal(data, &profile); err != nil {
			return err
		}
	} else {
		now := time.Now()
		profile = model.ColdStartProfile{
			Function:    c.String("function"),
			Runtime:     c.String("runtime"),
			ContainerID: "demo-container",
			TriggeredAt: now.Add(-1500 * time.Millisecond),
			ReadyAt:     now,
			Total:       1500 * time.Millisecond,
			Phases: []model.PhaseRecord{
				{Phase: model.PhaseImagePull, Duration: 500 * time.Millisecond, Source: "containerd/pull"},
				{Phase: model.PhaseImageExtract, Duration: 150 * time.Millisecond, Source: "containerd/unpack"},
				{Phase: model.PhaseContainerInit, Duration: 200 * time.Millisecond, Source: "containerd/init"},
				{Phase: model.PhaseRuntimeBoot, Duration: 180 * time.Millisecond, Source: "runtime/boot"},
				{Phase: model.PhaseDependencyLoad, Duration: 300 * time.Millisecond, Source: "runtime/deps"},
				{Phase: model.PhaseUserCode, Duration: 170 * time.Millisecond, Source: "user/init"},
			},
			Resources: model.ResourceUsage{
				CPUMillis:  500,
				MemoryMB:   256,
				DiskReadKB: 10240,
				NetRxKB:    51200,
			},
		}
	}

	ca := cost.NewAnalyzer(pricing)
	analysis := ca.Analyze(profile)
	summary := ca.Summarize(analysis)

	fmt.Println("=== COLD START COST ANALYSIS ===")
	fmt.Printf("Per invocation : %s\n", summary.PerInvocation)
	fmt.Printf("Per month est. : %s\n", summary.PerMonth)
	fmt.Printf("Warm savings   : %s (%.1f%%)\n", summary.WarmSavings, summary.SavingsPercent)
	fmt.Println()

	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(analysis)
}
