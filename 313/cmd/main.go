package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/spf13/cobra"

	"ci-scheduler/pkg/engine"
	"ci-scheduler/pkg/k8sclient"
	"ci-scheduler/pkg/monitor"
	"ci-scheduler/pkg/scheduler"
)

var (
	pipelineFile  string
	mode          string
	namespace     string
	kubeconfig    string
	executors     []string
	executorCPU   []float64
	executorMem   []int64
	strategy      string
	monitorInterval time.Duration
	enableWarmup    bool
	enableAutoscaler bool
	enablePrediction bool
	preheatThreshold int
	minExecutors    int
	maxExecutors    int
	scaleUpThreshold int
	scaleDownThreshold int
	cooldownPeriod  time.Duration
)

func main() {
	rootCmd := &cobra.Command{
		Use:   "ci-scheduler",
		Short: "CI Pipeline Parallel Scheduling Optimization Tool",
		Long: `A CI pipeline parallel scheduling optimization tool that analyzes task dependencies (DAG),
calculates critical paths, and intelligently distributes parallel tasks to executors
with resource-aware scheduling, task priorities, and automatic failure retry.`,
	}

	runCmd := &cobra.Command{
		Use:   "run",
		Short: "Run a CI pipeline",
		RunE:  runPipeline,
	}

	runCmd.Flags().StringVarP(&pipelineFile, "pipeline", "p", "", "Path to pipeline YAML file (required)")
	runCmd.Flags().StringVarP(&mode, "mode", "m", "local", "Execution mode: local or kubernetes")
	runCmd.Flags().StringVarP(&namespace, "namespace", "n", "default", "Kubernetes namespace")
	runCmd.Flags().StringVar(&kubeconfig, "kubeconfig", "", "Path to kubeconfig file")
	runCmd.Flags().StringSliceVar(&executors, "executors", []string{"exec-1", "exec-2", "exec-3"}, "Executor names")
	runCmd.Flags().Float64SliceVar(&executorCPU, "executor-cpu", []float64{4.0, 4.0, 4.0}, "CPU cores per executor")
	runCmd.Flags().Int64SliceVar(&executorMem, "executor-mem", []int64{8192, 8192, 8192}, "Memory in MiB per executor")
	runCmd.Flags().StringVarP(&strategy, "strategy", "s", "balanced", "Scheduling strategy: critical_path_first, priority_first, resource_aware, balanced")
	runCmd.Flags().DurationVar(&monitorInterval, "monitor-interval", 5*time.Second, "Resource monitor interval")

	runCmd.Flags().BoolVar(&enableWarmup, "enable-warmup", true, "Enable task warmup to preload dependencies")
	runCmd.Flags().BoolVar(&enableAutoscaler, "enable-autoscaler", true, "Enable dynamic executor autoscaling")
	runCmd.Flags().BoolVar(&enablePrediction, "enable-prediction", true, "Enable pipeline time prediction")
	runCmd.Flags().IntVar(&preheatThreshold, "preheat-threshold", 2, "Preheat when remaining dependencies <= this value")
	runCmd.Flags().IntVar(&minExecutors, "min-executors", 2, "Minimum number of executors for autoscaling")
	runCmd.Flags().IntVar(&maxExecutors, "max-executors", 10, "Maximum number of executors for autoscaling")
	runCmd.Flags().IntVar(&scaleUpThreshold, "scale-up-threshold", 3, "Scale up when pending tasks >= this value")
	runCmd.Flags().IntVar(&scaleDownThreshold, "scale-down-threshold", 1, "Scale down when pending tasks <= this value")
	runCmd.Flags().DurationVar(&cooldownPeriod, "cooldown-period", 30*time.Second, "Cooldown period between scaling actions")

	_ = runCmd.MarkFlagRequired("pipeline")

	analyzeCmd := &cobra.Command{
		Use:   "analyze",
		Short: "Analyze a pipeline DAG without executing",
		RunE:  analyzePipeline,
	}

	analyzeCmd.Flags().StringVarP(&pipelineFile, "pipeline", "p", "", "Path to pipeline YAML file (required)")
	_ = analyzeCmd.MarkFlagRequired("pipeline")

	rootCmd.AddCommand(runCmd)
	rootCmd.AddCommand(analyzeCmd)

	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func runPipeline(cmd *cobra.Command, args []string) error {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		fmt.Println("\nReceived shutdown signal, stopping...")
		cancel()
	}()

	mon := monitor.NewResourceMonitor(monitorInterval, 100)
	mon.Start()
	defer mon.Stop()

	var schedStrategy scheduler.SchedulingStrategy
	switch strategy {
	case "critical_path_first":
		schedStrategy = scheduler.StrategyCriticalPathFirst
	case "priority_first":
		schedStrategy = scheduler.StrategyPriorityFirst
	case "resource_aware":
		schedStrategy = scheduler.StrategyResourceAware
	case "balanced":
		schedStrategy = scheduler.StrategyBalanced
	default:
		schedStrategy = scheduler.StrategyBalanced
	}

	sched := scheduler.NewScheduler(mon, schedStrategy)

	if len(executors) != len(executorCPU) || len(executors) != len(executorMem) {
		return fmt.Errorf("executor count mismatch: executors=%d, cpu=%d, mem=%d",
			len(executors), len(executorCPU), len(executorMem))
	}

	for i, name := range executors {
		cpu := 4.0
		mem := int64(8192)
		if i < len(executorCPU) {
			cpu = executorCPU[i]
		}
		if i < len(executorMem) {
			mem = executorMem[i]
		}
		sched.AddExecutor(name, cpu, mem)
		fmt.Printf("Added executor %s: CPU=%.2f, Memory=%dMi\n", name, cpu, mem)
	}

	var k8sClient *k8sclient.K8sClient
	var execMode engine.ExecutionMode

	if mode == "kubernetes" {
		var err error
		k8sClient, err = k8sclient.NewK8sClient(namespace, kubeconfig)
		if err != nil {
			return fmt.Errorf("failed to create k8s client: %w", err)
		}
		execMode = engine.ModeKubernetes
		fmt.Println("Running in Kubernetes mode")
	} else {
		execMode = engine.ModeLocal
		fmt.Println("Running in local simulation mode")
	}

	opts := &engine.EngineOptions{
		EnableWarmup:      enableWarmup,
		EnableAutoscaler:  enableAutoscaler,
		EnablePrediction:  enablePrediction,
		PreheatThreshold:  preheatThreshold,
		MinExecutors:      minExecutors,
		MaxExecutors:      maxExecutors,
		ScaleUpThreshold:  scaleUpThreshold,
		ScaleDownThreshold: scaleDownThreshold,
		CooldownPeriod:    cooldownPeriod,
	}

	fmt.Println("\n=== Pipeline Features ===")
	fmt.Printf("Task Warmup: %v\n", enableWarmup)
	fmt.Printf("Dynamic Autoscaling: %v\n", enableAutoscaler)
	fmt.Printf("Time Prediction: %v\n", enablePrediction)
	if enableAutoscaler {
		fmt.Printf("  Executors Range: %d-%d\n", minExecutors, maxExecutors)
		fmt.Printf("  Scale Up Threshold: %d pending\n", scaleUpThreshold)
		fmt.Printf("  Scale Down Threshold: %d pending\n", scaleDownThreshold)
		fmt.Printf("  Cooldown Period: %v\n", cooldownPeriod)
	}
	if enableWarmup {
		fmt.Printf("  Preheat Threshold: <= %d remaining deps\n", preheatThreshold)
	}
	fmt.Println()

	eng := engine.NewPipelineEngine(execMode, mon, sched, k8sClient, opts)

	if err := eng.LoadPipeline(pipelineFile); err != nil {
		return fmt.Errorf("failed to load pipeline: %w", err)
	}

	result, err := eng.Run(ctx)
	if err != nil {
		return fmt.Errorf("pipeline execution failed: %w", err)
	}

	result.Print()

	if !result.Success {
		os.Exit(1)
	}

	return nil
}

func analyzePipeline(cmd *cobra.Command, args []string) error {
	mon := monitor.NewResourceMonitor(0, 0)
	sched := scheduler.NewScheduler(mon, scheduler.StrategyBalanced)
	opts := &engine.EngineOptions{
		EnableWarmup:     false,
		EnableAutoscaler: false,
		EnablePrediction: false,
	}
	eng := engine.NewPipelineEngine(engine.ModeLocal, mon, sched, nil, opts)

	if err := eng.LoadPipeline(pipelineFile); err != nil {
		return fmt.Errorf("failed to load pipeline: %w", err)
	}

	return nil
}
