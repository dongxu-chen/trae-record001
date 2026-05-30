package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"heatcache/internal/cache"
	"heatcache/internal/config"
	"heatcache/internal/connector"
	"heatcache/internal/preheater"
)

func main() {
	configPath := flag.String("config", "", "path to config file")
	initConfig := flag.Bool("init", false, "generate default config file")
	validate := flag.Bool("validate", false, "validate config and connections")
	preheatOnce := flag.Bool("preheat", false, "run preheat once and exit")
	report := flag.Bool("report", false, "generate preheat report")
	invalidateTable := flag.String("invalidate", "", "invalidate cache for a specific table")
	stats := flag.Bool("stats", false, "show incremental and binlog statistics")
	predictHitrate := flag.Bool("predict", false, "show cache hit rate prediction")
	plan := flag.Bool("plan", false, "generate cache capacity and eviction strategy plan")
	adaptiveStats := flag.Bool("adaptive", false, "show adaptive interval control statistics")
	flag.Parse()

	if *initConfig {
		cfg := config.DefaultConfig()
		if err := cfg.Save("heatcache.json"); err != nil {
			log.Fatalf("failed to generate config: %v", err)
		}
		fmt.Println("default config written to heatcache.json")
		return
	}

	var cfg *config.Config
	if *configPath != "" {
		loaded, err := config.LoadConfig(*configPath)
		if err != nil {
			log.Fatalf("failed to load config: %v", err)
		}
		cfg = loaded
	} else {
		cfg = config.DefaultConfig()
	}

	cacheLayer := cache.NewRedisCache(cfg.ToCacheConfig())
	ctx := context.Background()

	if err := cacheLayer.Connect(ctx); err != nil {
		log.Fatalf("failed to connect to redis: %v", err)
	}
	defer cacheLayer.Close()

	connectors := cfg.ToConnectors()
	for name, conn := range connectors {
		if err := conn.Connect(ctx); err != nil {
			log.Printf("warning: failed to connect to %s: %v", name, err)
		} else {
			log.Printf("connected to database: %s (%s)", name, conn.GetType())
		}
	}
	defer func() {
		for name, conn := range connectors {
			conn.Close()
			log.Printf("disconnected from: %s", name)
		}
	}()

	ph := preheater.NewPreheater(cfg.ToPreheaterConfig(), cacheLayer, connectors)

	mysqlBinlogConfigs := cfg.ToMySQLBinlogConfigs()
	for name, blConfig := range mysqlBinlogConfigs {
		if err := ph.AddMySQLBinlog(name, blConfig); err != nil {
			log.Printf("warning: failed to setup mysql binlog listener %s: %v", name, err)
		} else {
			log.Printf("configured mysql binlog listener: %s", name)
		}
	}

	pgBinlogConfigs := cfg.ToPGBinlogConfigs()
	for name, pgConfig := range pgBinlogConfigs {
		ph.AddPGBinlog(name, pgConfig)
		log.Printf("configured postgres replication listener: %s", name)
	}

	if *validate {
		runValidate(cfg, cacheLayer, connectors)
		return
	}

	if *invalidateTable != "" {
		if err := ph.InvalidateTable(ctx, *invalidateTable); err != nil {
			log.Fatalf("failed to invalidate table %s: %v", *invalidateTable, err)
		}
		fmt.Printf("invalidated cache for table: %s\n", *invalidateTable)
		return
	}

	if *preheatOnce {
		results, err := ph.PreheatBatch(ctx, "mysql_main", []string{
			"SELECT * FROM users WHERE status = 'active'",
		})
		if err != nil {
			log.Fatalf("preheat failed: %v", err)
		}
		for _, r := range results {
			status := "SUCCESS"
			if !r.Success {
				status = "FAILED"
			}
			fmt.Printf("[%s] %s (%v)\n", status, r.Job.QueryHash, r.Duration)
		}
		return
	}

	if *report {
		rpt, err := ph.GenerateReport(ctx)
		if err != nil {
			log.Fatalf("failed to generate report: %v", err)
		}
		fmt.Printf("=== HeatCache Preheat Report ===\n")
		fmt.Printf("Timestamp:        %s\n", rpt.Timestamp.Format(time.RFC3339))
		fmt.Printf("Hot Queries:      %d\n", rpt.HotQueryCount)
		fmt.Printf("Dirty Queries:    %d\n", rpt.DirtyQueryCount)
		fmt.Printf("Total Queries:    %d\n", rpt.TotalQueries)
		fmt.Printf("Cache Keys:       %d\n", rpt.CacheStats.TotalKeys)
		fmt.Printf("Memory Used:      %d bytes\n", rpt.CacheStats.MemoryUsed)
		fmt.Printf("Tracked Tables:   %d\n", rpt.CacheStats.TableCount)
		if rpt.BinlogStats != nil {
			fmt.Printf("Binlog Events:    %v\n", rpt.BinlogStats["processed_events"])
			fmt.Printf("Invalidated Tbls: %v\n", rpt.BinlogStats["invalidated_tables"])
		}
		if rpt.HitRatePrediction != nil {
			fmt.Printf("Current Hit Rate: %.2f%%\n", rpt.HitRatePrediction.CurrentHitRate*100)
			fmt.Printf("Predicted Hit:    %.2f%% (+%.2f%%)\n",
				rpt.HitRatePrediction.PredictedHitRate*100,
				rpt.HitRatePrediction.HitRateImprovement*100)
		}
		if rpt.AdaptiveMetrics != nil {
			fmt.Printf("Current Interval: %v\n", ph.GetCurrentInterval())
			fmt.Printf("Change Rate:      %.2f%%\n", rpt.AdaptiveMetrics.ChangeRate*100)
		}
		if rpt.CachePlan != nil {
			fmt.Printf("Recommended Mem:  %.1f MB\n", float64(rpt.CachePlan.RecommendedMaxMemory)/1024/1024)
			fmt.Printf("Recommended Str:  %s\n", rpt.CachePlan.RecommendedStrategy)
		}
		return
	}

	if *stats {
		rpt, err := ph.GenerateReport(ctx)
		if err != nil {
			log.Fatalf("failed to get stats: %v", err)
		}
		fmt.Printf("=== HeatCache Statistics ===\n")
		fmt.Printf("Incremental Manager:\n")
		fmt.Printf("  Total Registered: %d\n", rpt.TotalQueries)
		fmt.Printf("  Dirty Count:      %d\n", rpt.DirtyQueryCount)
		fmt.Printf("Binlog Listener:\n")
		if rpt.BinlogStats != nil {
			fmt.Printf("  Processed Events: %v\n", rpt.BinlogStats["processed_events"])
			fmt.Printf("  MySQL Listeners:  %v\n", rpt.BinlogStats["mysql_listeners"])
			fmt.Printf("  PG Listeners:     %v\n", rpt.BinlogStats["pg_listeners"])
			if tblCounts, ok := rpt.BinlogStats["table_invalidation_counts"].(map[string]int); ok {
				fmt.Printf("  Table Invalidation Counts:\n")
				for tbl, count := range tblCounts {
					fmt.Printf("    %s: %d\n", tbl, count)
				}
			}
		}
		return
	}

	if *adaptiveStats {
		rpt, err := ph.GenerateReport(ctx)
		if err != nil {
			log.Fatalf("failed to get adaptive stats: %v", err)
		}
		fmt.Printf("=== HeatCache Adaptive Control ===\n")
		fmt.Printf("Current Interval: %v\n", ph.GetCurrentInterval())
		if rpt.AdaptiveMetrics != nil {
			fmt.Printf("Change Rate:      %.2f%%\n", rpt.AdaptiveMetrics.ChangeRate*100)
			fmt.Printf("New Query Rate:   %.2f%%\n", rpt.AdaptiveMetrics.NewQueryRate*100)
			fmt.Printf("Dirty Rate:       %.2f%%\n", rpt.AdaptiveMetrics.DirtyRate*100)
			fmt.Printf("Hit Rate Trend:   %+.2f%%\n", rpt.AdaptiveMetrics.HitRateTrend*100)
			fmt.Printf("Recommended Int:  %v\n", rpt.AdaptiveMetrics.RecommendedInterval)
			fmt.Printf("Confidence:       %.2f%%\n", rpt.AdaptiveMetrics.Confidence*100)
		}
		return
	}

	if *predictHitrate {
		rpt, err := ph.GenerateReport(ctx)
		if err != nil {
			log.Fatalf("failed to get hit rate prediction: %v", err)
		}
		fmt.Printf("=== HeatCache Hit Rate Prediction ===\n")
		if rpt.HitRatePrediction != nil {
			pred := rpt.HitRatePrediction
			fmt.Printf("Current Hit Rate:     %.2f%%\n", pred.CurrentHitRate*100)
			fmt.Printf("Predicted Hit Rate:   %.2f%%\n", pred.PredictedHitRate*100)
			fmt.Printf("Expected Improvement: +%.2f%%\n", pred.HitRateImprovement*100)
			fmt.Printf("Preheated Queries:    %d / %d\n", pred.PreheatedCount, pred.TotalHotQueries)
			fmt.Printf("Coverage Rate:        %.2f%%\n", pred.CoverageRate*100)
			fmt.Printf("Confidence:           %.2f%%\n", pred.Confidence*100)
			if pred.Details != nil {
				fmt.Printf("\nTop Query Predictions:\n")
				for i, q := range pred.Details.QueryPredictions {
					if i >= 5 {
						break
					}
					fmt.Printf("  #%d: %s\n", i+1, q.Fingerprint[:16])
					fmt.Printf("    Cur: %.2f%% -> Pred: %.2f%% | Freq: %d | Priority: %.2f\n",
						q.CurrentHitRate*100, q.PredictedHitRate*100, q.Frequency, q.Priority)
				}
				if pred.Details.TimeSeries != nil && len(pred.Details.TimeSeries) > 0 {
					fmt.Printf("\n24h Projection:\n")
					for _, tp := range pred.Details.TimeSeries {
						if tp.Time.Minute() == 0 {
							fmt.Printf("  %s: %.2f%% [%.2f%% - %.2f%%]\n",
								tp.Time.Format("15:04"),
								tp.PredictedHitRate*100,
								tp.LowerBound*100,
								tp.UpperBound*100)
						}
					}
				}
			}
		} else {
			fmt.Println("Hit rate prediction is not enabled in configuration")
		}
		return
	}

	if *plan {
		rpt, err := ph.GenerateReport(ctx)
		if err != nil {
			log.Fatalf("failed to generate cache plan: %v", err)
		}
		fmt.Printf("=== HeatCache Capacity & Strategy Plan ===\n")
		if rpt.CachePlan != nil {
			cp := rpt.CachePlan
			fmt.Printf("Recommended Max Memory: %d bytes (%.1f MB)\n",
				cp.RecommendedMaxMemory, float64(cp.RecommendedMaxMemory)/1024/1024)
			fmt.Printf("Recommended Strategy:   %s\n", cp.RecommendedStrategy)
			fmt.Printf("Recommended LRU Threshold: %d keys\n", cp.RecommendedLRUThreshold)
			fmt.Printf("Expected Hit Rate:      %.2f%%\n", cp.ExpectedHitRate*100)
			fmt.Printf("Hot Data Ratio:         %.2f%%\n", cp.HotDataRatio*100)
			fmt.Printf("Working Set Size:       %d bytes\n", cp.WorkingSetSize)
			fmt.Printf("Est. Eviction Rate:     %.2f%%\n", cp.EvictionRate*100)

			if cp.MemoryBreakdown != nil {
				mb := cp.MemoryBreakdown
				fmt.Printf("\nMemory Breakdown:\n")
				fmt.Printf("  Hot Data:  %d bytes\n", mb.HotDataSize)
				fmt.Printf("  Warm Data: %d bytes\n", mb.WarmDataSize)
				fmt.Printf("  Cold Data: %d bytes\n", mb.ColdDataSize)
				fmt.Printf("  Avg Entry: %d bytes\n", mb.AvgEntrySize)
				fmt.Printf("  Overhead:  %d bytes/entry\n", mb.OverheadPerEntry)
				fmt.Printf("  Entries:   %d\n", mb.TotalEntries)
			}

			fmt.Printf("\nStrategy Comparison:\n")
			for i, ss := range cp.StrategyComparison {
				marker := "  "
				if ss.Strategy == cp.RecommendedStrategy {
					marker = "★ "
				}
				fmt.Printf("%s#%d %s (score: %.2f)\n", marker, i+1, ss.Strategy, ss.Score)
				fmt.Printf("    Use case: %s\n", ss.UseCase)
				if len(ss.Pros) > 0 {
					fmt.Printf("    Pros: %v\n", ss.Pros)
				}
				if len(ss.Cons) > 0 {
					fmt.Printf("    Cons: %v\n", ss.Cons)
				}
			}
		}
		return
	}

	runServer(ph, cfg)
}

func runValidate(cfg *config.Config, cacheLayer *cache.RedisCache, connectors map[string]connector.Connector) {
	ctx := context.Background()

	fmt.Println("=== HeatCache Validation ===")

	stats, err := cacheLayer.Stats(ctx)
	if err != nil {
		fmt.Printf("[FAIL] Redis stats: %v\n", err)
	} else {
		fmt.Printf("[OK]   Redis connection (keys=%d, mem=%d bytes)\n", stats.TotalKeys, stats.MemoryUsed)
	}

	for name, conn := range connectors {
		if err := conn.Ping(ctx); err != nil {
			fmt.Printf("[FAIL] %s: %v\n", name, err)
		} else {
			fmt.Printf("[OK]   %s (%s)\n", name, conn.GetType())
		}
	}

	fmt.Printf("\n=== Feature Flags ===\n")
	fmt.Printf("Incremental Refresh:    %v\n", cfg.Preheat.EnableIncremental)
	fmt.Printf("Binlog Listening:       %v\n", cfg.Preheat.EnableBinlog)
	fmt.Printf("Adaptive Interval:      %v\n", cfg.Preheat.EnableAdaptiveInterval)
	fmt.Printf("Hit Rate Prediction:    %v\n", cfg.Preheat.EnableHitRatePrediction)
	fmt.Printf("Target Hit Rate:        %.1f%%\n", cfg.Preheat.TargetHitRate*100)
	fmt.Printf("MySQL Binlog Count:     %d\n", len(cfg.ToMySQLBinlogConfigs()))
	fmt.Printf("PG Binlog Count:        %d\n", len(cfg.ToPGBinlogConfigs()))

	fmt.Println("validation complete")
}

func runServer(ph *preheater.Preheater, cfg *config.Config) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	ph.Start(ctx)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	fmt.Println("=== HeatCache Server Running ===")
	fmt.Printf("  Incremental Refresh: %v (interval: %v)\n", cfg.Preheat.EnableIncremental, time.Duration(cfg.Preheat.IncrementalIntervalMs)*time.Millisecond)
	fmt.Printf("  Binlog Listening:    %v\n", cfg.Preheat.EnableBinlog)
	fmt.Printf("  Adaptive Interval:   %v\n", cfg.Preheat.EnableAdaptiveInterval)
	fmt.Printf("  Hit Rate Prediction: %v (target: %.1f%%)\n", cfg.Preheat.EnableHitRatePrediction, cfg.Preheat.TargetHitRate*100)
	fmt.Println("press Ctrl+C to stop")

	<-sigCh
	fmt.Println("\nshutting down...")

	ph.Stop()
	fmt.Println("server stopped")
}
