package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"docker-build-accelerator/pkg/analysis"
	"docker-build-accelerator/pkg/cache"
	"docker-build-accelerator/pkg/cacheshare"
	"docker-build-accelerator/pkg/parallel"
	"docker-build-accelerator/pkg/parser"
	"docker-build-accelerator/pkg/prediction"
	"docker-build-accelerator/pkg/security"
	"docker-build-accelerator/pkg/upload"

	"github.com/docker/docker/api/types"
	"github.com/docker/docker/pkg/archive"
	"github.com/docker/docker/client"
	"github.com/spf13/cobra"
)

var (
	dockerfilePath string
	buildContext   string
	tag            string
	concurrency    int
	registryURL    string
	registryUser   string
	registryPass   string
	historyDir     string
	noCache        bool
	pushImage      bool
	scanImage      bool
	originalDockerfile string
	modifiedDockerfile string
	projectID      string
	branchName     string
	commitSHA      string
	maxCacheGB     float64
	retentionDays  int
	dryRun         bool
	scanFormat     string
	scanOutput     string
	ignoreUnfixed  bool
)

func main() {
	rootCmd := &cobra.Command{
		Use:   "docker-build-accelerator",
		Short: "Docker镜像构建加速工具",
		Long:  `一个基于Go和Docker SDK的Docker镜像构建加速工具，支持层缓存优化、并行构建、构建历史分析和分片并行上传`,
	}

	buildCmd := &cobra.Command{
		Use:   "build",
		Short: "构建Docker镜像（带加速优化）",
		Run:   runBuild,
	}

	analyzeCmd := &cobra.Command{
		Use:   "analyze",
		Short: "分析Dockerfile并给出优化建议",
		Run:   runAnalyze,
	}

	historyCmd := &cobra.Command{
		Use:   "history",
		Short: "查看构建历史分析报告",
		Run:   runHistory,
	}

	pushCmd := &cobra.Command{
		Use:   "push",
		Short: "并行分片上传镜像到私有仓库",
		Run:   runPush,
	}

	predictCmd := &cobra.Command{
		Use:   "predict",
		Short: "预测Dockerfile改动对构建时间和镜像大小的影响",
		Run:   runPredict,
	}

	cacheCmd := &cobra.Command{
		Use:   "cache",
		Short: "管理共享构建缓存卷",
		Run:   runCache,
	}

	scanCmd := &cobra.Command{
		Use:   "scan",
		Short: "扫描镜像安全漏洞",
		Run:   runScan,
	}

	buildCmd.Flags().StringVarP(&dockerfilePath, "file", "f", "Dockerfile", "Dockerfile路径")
	buildCmd.Flags().StringVarP(&buildContext, "context", "c", ".", "构建上下文目录")
	buildCmd.Flags().StringVarP(&tag, "tag", "t", "", "镜像标签 (name:tag)")
	buildCmd.Flags().IntVarP(&concurrency, "concurrency", "j", 4, "并行构建并发数")
	buildCmd.Flags().StringVar(&registryURL, "registry", "", "私有仓库URL (用于推送)")
	buildCmd.Flags().StringVar(&registryUser, "registry-user", "", "私有仓库用户名")
	buildCmd.Flags().StringVar(&registryPass, "registry-pass", "", "私有仓库密码")
	buildCmd.Flags().StringVar(&historyDir, "history-dir", "./.build-history", "构建历史存储目录")
	buildCmd.Flags().BoolVar(&noCache, "no-cache", false, "禁用构建缓存")
	buildCmd.Flags().BoolVar(&pushImage, "push", false, "构建完成后自动推送")
	buildCmd.Flags().BoolVar(&scanImage, "scan", false, "构建完成后自动扫描漏洞")

	analyzeCmd.Flags().StringVarP(&dockerfilePath, "file", "f", "Dockerfile", "Dockerfile路径")
	analyzeCmd.Flags().StringVarP(&buildContext, "context", "c", ".", "构建上下文目录")

	historyCmd.Flags().StringVar(&historyDir, "history-dir", "./.build-history", "构建历史存储目录")

	pushCmd.Flags().StringVarP(&tag, "tag", "t", "", "镜像标签 (name:tag)")
	pushCmd.Flags().StringVar(&registryURL, "registry", "", "私有仓库URL")
	pushCmd.Flags().StringVar(&registryUser, "registry-user", "", "私有仓库用户名")
	pushCmd.Flags().StringVar(&registryPass, "registry-pass", "", "私有仓库密码")
	pushCmd.Flags().IntVarP(&concurrency, "concurrency", "j", 4, "并行上传并发数")

	predictCmd.Flags().StringVar(&originalDockerfile, "original", "Dockerfile", "原始Dockerfile路径")
	predictCmd.Flags().StringVar(&modifiedDockerfile, "modified", "", "修改后的Dockerfile路径")
	predictCmd.Flags().StringVar(&historyDir, "history-dir", "./.build-history", "构建历史存储目录")

	cacheCmd.Flags().StringVar(&projectID, "project-id", "default", "项目ID")
	cacheCmd.Flags().StringVar(&branchName, "branch", "main", "分支名称")
	cacheCmd.Flags().StringVar(&commitSHA, "commit", "", "提交SHA")
	cacheCmd.Flags().Float64Var(&maxCacheGB, "max-size-gb", 50, "最大缓存大小(GB)")
	cacheCmd.Flags().IntVar(&retentionDays, "retention-days", 30, "缓存保留天数")
	cacheCmd.Flags().BoolVar(&dryRun, "dry-run", false, "试运行模式（不实际修改）")

	scanCmd.Flags().StringVarP(&tag, "tag", "t", "", "镜像标签 (name:tag)")
	scanCmd.Flags().StringVar(&scanFormat, "format", "table", "输出格式 (table/json/sarif)")
	scanCmd.Flags().StringVar(&scanOutput, "output", "", "输出文件路径")
	scanCmd.Flags().BoolVar(&ignoreUnfixed, "ignore-unfixed", false, "忽略无修复版本的漏洞")

	rootCmd.AddCommand(buildCmd, analyzeCmd, historyCmd, pushCmd, predictCmd, cacheCmd, scanCmd)

	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func runBuild(cmd *cobra.Command, args []string) {
	ctx := context.Background()

	parsed, err := parser.ParseDockerfile(dockerfilePath)
	if err != nil {
		fmt.Printf("解析Dockerfile失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("成功解析Dockerfile，发现 %d 个构建阶段\n", len(parsed.Stages))
	for _, stage := range parsed.Stages {
		fmt.Printf("  阶段 %d: %s (基础镜像: %s, 依赖: %v)\n", 
			stage.Index, stage.Name, stage.BaseImage, stage.DependsOn)
	}

	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		fmt.Printf("创建Docker客户端失败: %v\n", err)
		os.Exit(1)
	}
	defer cli.Close()

	optimizer, err := cache.NewCacheOptimizer(buildContext, parsed)
	if err != nil {
		fmt.Printf("创建缓存优化器失败: %v\n", err)
	} else {
		for _, stage := range parsed.Stages {
			report, err := optimizer.GetOptimizationReport(stage)
			if err == nil {
				report.Print()
			}
		}
		defer optimizer.SaveCacheDB()
	}

	scheduler, err := parallel.NewScheduler(parsed, concurrency)
	if err != nil {
		fmt.Printf("创建调度器失败: %v\n", err)
		os.Exit(1)
	}
	scheduler.DAG.PrintDAG()
	scheduler.PrintBuildOrder()

	buildID := fmt.Sprintf("%d", time.Now().Unix())
	buildHistory := analysis.NewBuildHistory(buildID, dockerfilePath, tag)

	fmt.Println("\n开始并行构建...")
	startTime := time.Now()

	err = scheduler.Run(ctx, func(ctx context.Context, job *parallel.BuildJob) (string, error) {
		fmt.Printf("[%s] 开始构建\n", job.Stage.Name)
		
		stageStartTime := time.Now()
		
		imageTag := fmt.Sprintf("stage-%s:%s", job.Stage.Name, buildID)
		
		buildArgs := make(map[string]*string)
		for k, v := range parsed.Args {
			val := v
			buildArgs[k] = &val
		}

		opts := types.ImageBuildOptions{
			Dockerfile:     filepath.Base(dockerfilePath),
			Tags:           []string{imageTag},
			BuildArgs:      buildArgs,
			NoCache:        noCache,
			Remove:         true,
			ForceRemove:    true,
			PullParent:     false,
			Target:         job.Stage.Name,
		}

		contextDir := buildContext
		if contextDir == "" {
			contextDir = filepath.Dir(dockerfilePath)
		}

		tar, err := archive.TarWithOptions(contextDir, &archive.TarOptions{})
		if err != nil {
			return "", fmt.Errorf("创建构建上下文失败: %w", err)
		}

		resp, err := cli.ImageBuild(ctx, tar, opts)
		if err != nil {
			return "", fmt.Errorf("构建失败: %w", err)
		}
		defer resp.Body.Close()

		decoder := json.NewDecoder(resp.Body)
		for {
			var message map[string]interface{}
			if err := decoder.Decode(&message); err != nil {
				if err == io.EOF {
					break
				}
				return "", err
			}
			if stream, ok := message["stream"].(string); ok {
				fmt.Printf("[%s] %s", job.Stage.Name, stream)
			}
		}

		inspect, _, err := cli.ImageInspectWithRaw(ctx, imageTag)
		if err == nil {
			layerRecord := &analysis.LayerRecord{
				LayerHash:   inspect.ID,
				Command:     job.Stage.Name,
				CommandType: "STAGE",
				SizeBytes:   inspect.Size,
				DurationMs:  time.Since(stageStartTime).Milliseconds(),
				CacheHit:    false,
				StageName:   job.Stage.Name,
				CreatedAt:   time.Now(),
			}
			buildHistory.AddLayer(layerRecord)
		}

		fmt.Printf("[%s] 构建完成，耗时: %.2fs\n", job.Stage.Name, time.Since(stageStartTime).Seconds())
		return imageTag, nil
	})

	if err != nil {
		fmt.Printf("构建失败: %v\n", err)
		buildHistory.Complete(false)
	} else {
		buildHistory.Complete(true)
		fmt.Printf("\n构建完成！总耗时: %.2fs\n", time.Since(startTime).Seconds())
		scheduler.PrintSummary()
	}

	if analyzer, err := analysis.NewAnalyzer(historyDir); err == nil {
		analyzer.RecordBuild(buildHistory)
		fmt.Printf("构建记录已保存到: %s\n", historyDir)
	}

	if pushImage && registryURL != "" && buildHistory.Success {
		fmt.Println("\n开始并行上传镜像...")
		if err := pushToRegistry(ctx, cli, tag); err != nil {
			fmt.Printf("上传失败: %v\n", err)
		}
	}

	if scanImage && buildHistory.Success && tag != "" {
		fmt.Println("\n开始安全扫描...")
		runSecurityScan(ctx, tag)
	}
}

func runAnalyze(cmd *cobra.Command, args []string) {
	parsed, err := parser.ParseDockerfile(dockerfilePath)
	if err != nil {
		fmt.Printf("解析Dockerfile失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("\n=== Dockerfile 分析报告 ===")
	fmt.Printf("总阶段数: %d\n", len(parsed.Stages))
	fmt.Printf("总命令数: ")
	
	totalCommands := 0
	cmdCount := make(map[string]int)
	
	for _, stage := range parsed.Stages {
		for _, cmd := range stage.Commands {
			totalCommands++
			cmdCount[string(cmd.Type)]++
		}
	}
	fmt.Printf("%d\n\n", totalCommands)

	fmt.Println("命令类型统计:")
	for cmdType, count := range cmdCount {
		fmt.Printf("  %-12s: %d\n", cmdType, count)
	}

	optimizer, err := cache.NewCacheOptimizer(buildContext, parsed)
	if err != nil {
		fmt.Printf("创建缓存优化器失败: %v\n", err)
	} else {
		for _, stage := range parsed.Stages {
			report, err := optimizer.GetOptimizationReport(stage)
			if err == nil {
				report.Print()
			}
		}
		defer optimizer.SaveCacheDB()
	}

	scheduler, err := parallel.NewScheduler(parsed, concurrency)
	if err != nil {
		fmt.Printf("创建调度器失败: %v\n", err)
		os.Exit(1)
	}
	scheduler.DAG.PrintDAG()
	scheduler.PrintBuildOrder()

	fmt.Println("\n=== 构建依赖图 ===")
	for _, stage := range parsed.Stages {
		if len(stage.DependsOn) > 0 {
			fmt.Printf("  %s → depends on → %v\n", stage.Name, stage.DependsOn)
		} else {
			fmt.Printf("  %s (无依赖)\n", stage.Name)
		}
	}
}

func runHistory(cmd *cobra.Command, args []string) {
	analyzer, err := analysis.NewAnalyzer(historyDir)
	if err != nil {
		fmt.Printf("创建分析器失败: %v\n", err)
		os.Exit(1)
	}

	if err := analyzer.LoadHistories(); err != nil {
		fmt.Printf("加载构建历史失败: %v\n", err)
		os.Exit(1)
	}

	report := analyzer.GenerateReport()
	report.Print()

	if len(report.HistoricalTrends) > 1 {
		fmt.Println("\n=== 历史趋势 ===")
		for i, trend := range report.HistoricalTrends {
			fmt.Printf("  批次 %d: 时间=%.1fs 大小=%.1fMB 缓存率=%.1f%%\n",
				i+1,
				float64(trend.DurationMs)/1000,
				float64(trend.SizeBytes)/1024/1024,
				trend.CacheHitRate*100)
		}
	}
}

func runPush(cmd *cobra.Command, args []string) {
	if tag == "" {
		fmt.Println("请使用 -t 指定镜像标签")
		os.Exit(1)
	}
	if registryURL == "" {
		fmt.Println("请使用 --registry 指定私有仓库URL")
		os.Exit(1)
	}

	ctx := context.Background()
	
	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		fmt.Printf("创建Docker客户端失败: %v\n", err)
		os.Exit(1)
	}
	defer cli.Close()

	if err := pushToRegistry(ctx, cli, tag); err != nil {
		fmt.Printf("上传失败: %v\n", err)
		os.Exit(1)
	}
}

func pushToRegistry(ctx context.Context, cli *client.Client, imageTag string) error {
	config := upload.DefaultUploadConfig(registryURL)
	config.Username = registryUser
	config.Password = registryPass
	config.Concurrency = concurrency

	parts := splitImageTag(imageTag)
	imageName := parts[0]
	tagName := "latest"
	if len(parts) > 1 {
		tagName = parts[1]
	}

	fmt.Printf("准备上传 %s/%s:%s\n", registryURL, imageName, tagName)
	
	remoteTag := fmt.Sprintf("%s/%s:%s", registryURL, imageName, tagName)
	if err := cli.ImageTag(ctx, imageTag, remoteTag); err != nil {
		return fmt.Errorf("标记镜像失败: %w", err)
	}

	pushOpts := types.ImagePushOptions{
		RegistryAuth: generateAuthHeader(registryUser, registryPass),
	}

	reader, err := cli.ImagePush(ctx, remoteTag, pushOpts)
	if err != nil {
		return fmt.Errorf("开始推送失败: %w", err)
	}
	defer reader.Close()

	decoder := json.NewDecoder(reader)
	for {
		var message map[string]interface{}
		if err := decoder.Decode(&message); err != nil {
			if err == io.EOF {
				break
			}
			return err
		}
		
		if status, ok := message["status"].(string); ok {
			if id, ok := message["id"].(string); ok {
				fmt.Printf("[%s] %s\n", id[:12], status)
			} else {
				fmt.Println(status)
			}
		}
		
		if errorMsg, ok := message["error"].(string); ok {
			return fmt.Errorf("推送错误: %s", errorMsg)
		}
	}

	fmt.Println("镜像上传完成！")
	return nil
}

func splitImageTag(imageTag string) []string {
	parts := []string{"", ""}
	if idx := lastIndexOf(imageTag, ':'); idx > 0 {
		parts[0] = imageTag[:idx]
		parts[1] = imageTag[idx+1:]
	} else {
		parts[0] = imageTag
		parts[1] = "latest"
	}
	return parts
}

func lastIndexOf(s string, sep byte) int {
	for i := len(s) - 1; i >= 0; i-- {
		if s[i] == sep {
			return i
		}
	}
	return -1
}

func generateAuthHeader(username, password string) string {
	if username == "" {
		return ""
	}
	authConfig := types.AuthConfig{
		Username: username,
		Password: password,
	}
	encoded, _ := json.Marshal(authConfig)
	return string(encoded)
}

func formatBytes(b uint64) string {
	const unit = 1024
	if b < unit {
		return fmt.Sprintf("%d B", b)
	}
	div, exp := uint64(unit), 0
	for n := b / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %ciB", float64(b)/float64(div), "KMGTPE"[exp])
}

func runPredict(cmd *cobra.Command, args []string) {
	if modifiedDockerfile == "" {
		fmt.Println("请使用 --modified 指定修改后的Dockerfile路径")
		os.Exit(1)
	}

	predictor, err := prediction.NewBuildPredictor(filepath.Join(historyDir, "build-history.json"))
	if err != nil {
		fmt.Printf("创建构建预测器失败: %v\n", err)
		fmt.Println("将使用默认统计数据进行预测")
	}

	prediction, err := predictor.PredictChanges(originalDockerfile, modifiedDockerfile)
	if err != nil {
		fmt.Printf("预测失败: %v\n", err)
		os.Exit(1)
	}

	prediction.Print()
}

func runCache(cmd *cobra.Command, args []string) {
	ctx := context.Background()

	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		fmt.Printf("创建Docker客户端失败: %v\n", err)
		os.Exit(1)
	}
	defer cli.Close()

	config := cacheshare.DefaultConfig()
	config.MaxCacheSizeGB = maxCacheGB
	config.RetentionDays = retentionDays

	manager, err := cacheshare.NewCacheShareManager(cli, config)
	if err != nil {
		fmt.Printf("创建缓存管理器失败: %v\n", err)
		os.Exit(1)
	}

	job := &cacheshare.CIJob{
		ID:        fmt.Sprintf("job-%d", time.Now().Unix()),
		ProjectID: projectID,
		Branch:    branchName,
		CommitSHA: commitSHA,
	}

	fmt.Println("=== 获取共享缓存卷 ===")
	volume, err := manager.GetSharedVolume(ctx, job)
	if err != nil {
		fmt.Printf("获取缓存卷失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("缓存卷名称: %s\n", volume.Name)
	fmt.Printf("项目ID: %s\n", volume.ProjectID)
	fmt.Printf("当前引用计数: %d\n", volume.RefCount)

	report, err := manager.GetUsageReport(ctx)
	if err != nil {
		fmt.Printf("获取使用报告失败: %v\n", err)
		os.Exit(1)
	}

	report.Print()

	fmt.Println("\n=== 清理过期缓存 ===")
	freed, err := manager.Cleanup(ctx, dryRun)
	if err != nil {
		fmt.Printf("清理失败: %v\n", err)
		os.Exit(1)
	}

	if dryRun {
		fmt.Printf("(试运行) 预计可释放空间: %s\n", formatBytes(uint64(freed)))
	} else {
		fmt.Printf("已释放空间: %s\n", formatBytes(uint64(freed)))
	}
}

func runScan(cmd *cobra.Command, args []string) {
	if tag == "" {
		fmt.Println("请使用 -t 指定镜像标签")
		os.Exit(1)
	}

	ctx := context.Background()

	config := security.DefaultScanConfig()
	config.Format = security.ScanFormat(scanFormat)
	config.OutputFile = scanOutput
	config.IgnoreUnfixed = ignoreUnfixed

	scanner, err := security.NewSecurityScanner(config)
	if err != nil {
		fmt.Printf("创建安全扫描器失败: %v\n", err)
		if !scanner.CheckScannerAvailable() {
			fmt.Println("Trivy 扫描器未安装，正在尝试安装...")
			if err := scanner.InstallScanner(ctx); err != nil {
				fmt.Printf("安装失败: %v\n", err)
				fmt.Println("请手动安装 Trivy: https://aquasecurity.github.io/trivy/latest/getting-started/installation/")
				os.Exit(1)
			}
		}
		os.Exit(1)
	}

	fmt.Printf("开始扫描镜像: %s\n", tag)
	result, err := scanner.ScanImage(ctx, tag)
	if err != nil {
		fmt.Printf("扫描失败: %v\n", err)
		os.Exit(1)
	}

	result.Print()

	report, err := scanner.GenerateReport(result)
	if err != nil {
		fmt.Printf("生成报告失败: %v\n", err)
		os.Exit(1)
	}

	if scanOutput != "" {
		if err := scanner.SaveReport(report, scanOutput); err != nil {
			fmt.Printf("保存报告失败: %v\n", err)
		} else {
			fmt.Printf("报告已保存到: %s\n", scanOutput)
		}
	}
}

func runSecurityScan(ctx context.Context, imageTag string) {
	config := security.DefaultScanConfig()
	config.Format = security.ScanFormat(scanFormat)
	config.OutputFile = scanOutput
	config.IgnoreUnfixed = ignoreUnfixed

	scanner, err := security.NewSecurityScanner(config)
	if err != nil {
		fmt.Printf("创建安全扫描器失败: %v\n", err)
		return
	}

	result, err := scanner.ScanImage(ctx, imageTag)
	if err != nil {
		fmt.Printf("扫描失败: %v\n", err)
		return
	}

	result.Print()
}
