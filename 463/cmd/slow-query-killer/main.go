package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"slow-query-killer/internal/config"
	"slow-query-killer/internal/monitor"
)

var (
	version = "1.0.0"
)

func main() {
	configPath := flag.String("config", "configs/config.yaml", "Path to configuration file")
	dryRun := flag.Bool("dry-run", false, "Run in dry-run mode (no actual killing)")
	showVersion := flag.Bool("version", false, "Show version information")
	showHelp := flag.Bool("help", false, "Show help")

	flag.Parse()

	if *showHelp {
		printHelp()
		return
	}

	if *showVersion {
		fmt.Printf("Slow Query Killer v%s\n", version)
		return
	}

	fmt.Printf("Slow Query Killer v%s\n", version)
	fmt.Println("=" * 50)

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	if *dryRun {
		cfg.Monitor.DryRun = true
	}

	m, err := monitor.NewMonitor(cfg)
	if err != nil {
		log.Fatalf("Failed to create monitor: %v", err)
	}

	if err := m.Start(); err != nil {
		log.Fatalf("Failed to start monitor: %v", err)
	}

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-sigChan:
			log.Println("\nReceived shutdown signal...")
			m.Stop()
			m.PrintStats()
			log.Println("Shutdown complete")
			return
		case <-ticker.C:
			m.PrintStats()
		}
	}
}

func printHelp() {
	fmt.Println("Slow Query Killer - 自动终止慢查询工具")
	fmt.Println()
	fmt.Println("用法:")
	fmt.Println("  slow-query-killer [选项]")
	fmt.Println()
	fmt.Println("选项:")
	fmt.Println("  -config string     配置文件路径 (默认: configs/config.yaml)")
	fmt.Println("  -dry-run           试运行模式，不实际终止查询")
	fmt.Println("  -version           显示版本信息")
	fmt.Println("  -help              显示帮助")
	fmt.Println()
	fmt.Println("示例:")
	fmt.Println("  slow-query-killer -config configs/config.yaml")
	fmt.Println("  slow-query-killer -dry-run")
	fmt.Println()
	fmt.Println("支持的数据库类型:")
	fmt.Println("  - MySQL")
	fmt.Println("  - PostgreSQL")
}
