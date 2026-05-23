package main

import (
	"fmt"
	"os"
	"strings"

	"container-scanner/pkg/compliance"
	"container-scanner/pkg/config"
	"container-scanner/pkg/dependency"
	"container-scanner/pkg/remediation"
	"container-scanner/pkg/report"
	"container-scanner/pkg/scanner"

	"github.com/spf13/cobra"
)

var (
	imageName    string
	configFile   string
	outputFile   string
	severities   string
	scanners     string
	failOnError  bool
	remoteMode   bool
	skipDbUpdate bool
)

var rootCmd = &cobra.Command{
	Use:   "container-scanner [image]",
	Short: "容器安全扫描工具 - 基于Trivy",
	Long:  `容器安全扫描工具，支持CVE漏洞扫描、敏感信息检测和配置风险分析`,
	Args:  cobra.MaximumNArgs(1),
	Run:   runScan,
}

func init() {
	rootCmd.Flags().StringVarP(&configFile, "config", "c", "", "配置文件路径")
	rootCmd.Flags().StringVarP(&outputFile, "output", "o", "scan-report.html", "输出报告文件路径")
	rootCmd.Flags().StringVarP(&severities, "severities", "s", "CRITICAL,HIGH,MEDIUM,LOW", "扫描的严重程度 (逗号分隔)")
	rootCmd.Flags().StringVarP(&scanners, "scanners", "", "vuln,secret,config", "启用的扫描器 (逗号分隔)")
	rootCmd.Flags().BoolVarP(&failOnError, "fail", "f", true, "超过阻断阈值时以非零状态退出")
	rootCmd.Flags().BoolVarP(&remoteMode, "remote", "r", false, "强制远程拉取镜像扫描")
	rootCmd.Flags().BoolVar(&skipDbUpdate, "skip-db-update", false, "跳过CVE数据库更新")
}

func runScan(cmd *cobra.Command, args []string) {
	if len(args) > 0 {
		imageName = args[0]
	}

	if imageName == "" {
		fmt.Println("❌ 错误: 请指定要扫描的镜像名称")
		fmt.Println("使用方法: container-scanner <image-name> [flags]")
		os.Exit(1)
	}

	var cfg *config.Config
	var err error

	if configFile != "" {
		cfg, err = config.LoadConfig(configFile)
		if err != nil {
			fmt.Printf("❌ 加载配置文件失败: %v\n", err)
			os.Exit(1)
		}
	} else {
		defaultCfg := config.DefaultConfig()
		cfg = &defaultCfg
	}

	if cmd.Flags().Changed("output") {
		cfg.Output = outputFile
	}
	if cmd.Flags().Changed("severities") {
		cfg.Severities = strings.Split(severities, ",")
	}
	if cmd.Flags().Changed("scanners") {
		cfg.Scanners = strings.Split(scanners, ",")
	}
	if cmd.Flags().Changed("fail") {
		cfg.FailOnError = failOnError
	}
	if cmd.Flags().Changed("skip-db-update") {
		cfg.Database.SkipUpdate = skipDbUpdate
	}

	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("  🔒 容器安全扫描工具")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Printf("📦 镜像名称: %s\n", imageName)
	fmt.Printf("📋 扫描器: %s\n", strings.Join(cfg.Scanners, ", "))
	fmt.Printf("⚠️  严重程度: %s\n", strings.Join(cfg.Severities, ", "))
	fmt.Printf("💾 数据库缓存: %s\n", cfg.Database.CacheDir)
	fmt.Println()

	sc, err := scanner.NewScanner()
	if err != nil {
		fmt.Printf("❌ 初始化扫描器失败: %v\n", err)
		fmt.Println("💡 请确保已安装 Trivy: https://aquasecurity.github.io/trivy/")
		os.Exit(1)
	}

	if cfg.ShouldUpdateDatabase() {
		fmt.Println("🔄 正在更新CVE漏洞数据库...")
		if err := sc.UpdateDatabase(cfg.Database.CacheDir); err != nil {
			fmt.Printf("⚠️  数据库更新警告: %v\n", err)
			fmt.Println("   将使用本地缓存的数据库继续扫描...")
		} else {
			fmt.Println("✅ 数据库更新完成")
		}
		fmt.Println()
	} else {
		fmt.Println("💾 使用本地缓存的CVE数据库")
		fmt.Println()
	}

	fmt.Println("🔍 开始扫描...")
	scanConfig := cfg.ToScanConfig(imageName)
	scanReport, err := sc.Scan(scanConfig)
	if err != nil {
		fmt.Printf("❌ 扫描失败: %v\n", err)
		os.Exit(1)
	}

	originalSecretCount := scanReport.TotalSecrets()
	filteredReport := cfg.FilterWhitelistedSecrets(scanReport)
	whitelistedCount := originalSecretCount - filteredReport.TotalSecrets()

	if whitelistedCount > 0 {
		fmt.Printf("✅ 已过滤 %d 个白名单匹配的敏感信息\n", whitelistedCount)
	}

	report.PrintConsoleSummary(filteredReport, imageName)

	fmt.Println()
	fmt.Println("📋 执行CIS基线合规检查...")
	cisBenchmark := compliance.NewCISBenchmark(sc.TrivyPath())
	cisResult, err := cisBenchmark.Run(imageName)
	if err != nil {
		fmt.Printf("⚠️  CIS合规检查警告: %v\n", err)
	} else {
		fmt.Printf("✅ CIS合规检查完成: 通过 %d/%d, 合规率 %.1f%%\n",
			cisResult.PassCount, cisResult.TotalChecks, cisResult.ComplianceScore())
	}

	fmt.Println()
	fmt.Println("🔧 生成修复建议...")
	fixReport := remediation.GenerateFixReport(filteredReport, cisResult)
	fmt.Print(fixReport.Summary())

	if len(fixReport.GetAutoFixSuggestions()) > 0 {
		if err := fixReport.GenerateFixScript("auto-fix.sh"); err != nil {
			fmt.Printf("⚠️  生成修复脚本警告: %v\n", err)
		} else {
			fmt.Println("✅ 自动修复脚本已生成: auto-fix.sh")
		}

		if err := fixReport.GenerateDockerfilePatch("Dockerfile.fix"); err != nil {
			fmt.Printf("⚠️  生成Dockerfile补丁警告: %v\n", err)
		} else {
			fmt.Println("✅ Dockerfile修复补丁已生成: Dockerfile.fix")
		}
	}

	fmt.Println()
	fmt.Println("📦 执行依赖分析和许可合规检查...")
	depAnalyzer := dependency.NewDependencyAnalyzer(sc.TrivyPath())
	depAnalysis, err := depAnalyzer.Analyze(imageName)
	if err != nil {
		fmt.Printf("⚠️  依赖分析警告: %v\n", err)
	} else {
		fmt.Print(depAnalysis.Summary())

		licenseIssues := depAnalysis.LicenseComplianceReport()
		if len(licenseIssues) > 0 {
			fmt.Println("\n⚠️  许可合规风险:")
			for _, issue := range licenseIssues {
				fmt.Printf("   • %s\n", issue)
			}
		}
	}

	result := cfg.CheckThresholds(filteredReport)

	fmt.Println("\n" + strings.Repeat("-", 80))
	fmt.Println("  🎯 阈值检查结果")
	fmt.Println(strings.Repeat("-", 80))

	if len(result.Blocked) > 0 {
		fmt.Println("\n🚫 阻断项 (将导致构建失败):")
		for _, v := range result.Blocked {
			fmt.Printf("   • %s\n", v.Message)
		}
	}

	if len(result.Warning) > 0 {
		fmt.Println("\n⚠️  警告项 (需要关注):")
		for _, v := range result.Warning {
			fmt.Printf("   • %s\n", v.Message)
		}
	}

	if len(result.Blocked) == 0 && len(result.Warning) == 0 {
		fmt.Println("\n✅ 所有检查通过!")
	}

	blockedMessages := make([]string, len(result.Blocked))
	for i, v := range result.Blocked {
		blockedMessages[i] = v.Message
	}

	warningMessages := make([]string, len(result.Warning))
	for i, v := range result.Warning {
		warningMessages[i] = v.Message
	}

	fmt.Println()
	fmt.Println("📄 生成完整HTML报告...")
	if err := report.GenerateFullReport(
		filteredReport, cisResult, fixReport, depAnalysis,
		imageName, cfg.Output, blockedMessages, warningMessages, whitelistedCount); err != nil {
		fmt.Printf("❌ 生成HTML报告失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("✅ HTML报告已生成: %s\n", cfg.Output)

	if !result.Passed && cfg.FailOnError {
		fmt.Println("\n💀 存在阻断级别的问题，构建失败")
		fmt.Println(strings.Repeat("=", 80))
		os.Exit(1)
	}

	fmt.Println("\n✨ 扫描完成!")
	fmt.Println(strings.Repeat("=", 80))
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
