package main

import (
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	"portscanner/report"
	"portscanner/scanner"
)

func printBanner() {
	banner := `
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║    🔍  PortScanner - 服务器端口扫描和暴露检测工具              ║
║                                                               ║
║    TCP扫描 | 服务识别 | 弱口令 | 版本加固 | 历史对比          ║
║    防火墙封禁 | 等保2.0合规 | 端口变化告警                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
`
	fmt.Println(banner)
}

func printUsage() {
	fmt.Println("使用方法:")
	fmt.Println()
	fmt.Println("  端口扫描:")
	fmt.Println("    portscanner scan [flags]")
	fmt.Println()
	fmt.Println("  特征库管理:")
	fmt.Println("    portscanner sig-update          更新特征库")
	fmt.Println("    portscanner sig-info            查看特征库信息")
	fmt.Println("    portscanner sig-export <file>   导出特征库")
	fmt.Println("    portscanner sig-import <file>   导入特征库")
	fmt.Println()
	fmt.Println("  密码字典管理:")
	fmt.Println("    portscanner dict-info                    查看字典库信息")
	fmt.Println("    portscanner dict-import <file> <source>  导入密码字典")
	fmt.Println("    portscanner dict-leak <file> <source>    导入密码泄露库")
	fmt.Println("    portscanner dict-add <password>          添加自定义密码")
	fmt.Println("    portscanner dict-search <query>           搜索密码")
	fmt.Println("    portscanner dict-export <file> [cats]    导出密码字典")
	fmt.Println()
	fmt.Println("  版本漏洞查询:")
	fmt.Println("    portscanner vuln-search <service> [keyword]  搜索服务漏洞")
	fmt.Println()
	fmt.Println("  端口历史对比:")
	fmt.Println("    portscanner history <host>               查看端口变化历史")
	fmt.Println("    portscanner history-diff <host>          对比最新两次扫描差异")
	fmt.Println("    portscanner history-export <host> <file> 导出历史记录")
	fmt.Println()
	fmt.Println("  防火墙封禁:")
	fmt.Println("    portscanner block-status                 查看封禁规则状态")
	fmt.Println("    portscanner block <port> [port...]       封禁指定端口")
	fmt.Println("    portscanner unblock <port>               解封指定端口")
	fmt.Println("    portscanner block-auto <host>            自动封禁高危端口")
	fmt.Println("    portscanner block-whitelist-add <port> <reason>  添加白名单")
	fmt.Println()
	fmt.Println("  等保合规检查:")
	fmt.Println("    portscanner compliance <host> [level]    等保合规检查(level=1/2/3)")
	fmt.Println()
	fmt.Println("  端口扫描参数:")
	flag.PrintDefaults()
}

func main() {
	printBanner()

	if len(os.Args) < 2 {
		runScan()
		return
	}

	command := strings.ToLower(os.Args[1])

	switch command {
	case "scan":
		os.Args = append([]string{os.Args[0]}, os.Args[2:]...)
		runScan()
	case "sig-update":
		runSigUpdate()
	case "sig-info":
		runSigInfo()
	case "sig-export":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定导出文件名")
			fmt.Println("  用法: portscanner sig-export <file>")
			return
		}
		runSigExport(os.Args[2])
	case "sig-import":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定导入文件名")
			fmt.Println("  用法: portscanner sig-import <file>")
			return
		}
		runSigImport(os.Args[2])
	case "dict-info":
		runDictInfo()
	case "dict-import":
		if len(os.Args) < 4 {
			fmt.Println("❌ 错误: 请指定文件和来源")
			fmt.Println("  用法: portscanner dict-import <file> <source>")
			return
		}
		runDictImport(os.Args[2], os.Args[3])
	case "dict-leak":
		if len(os.Args) < 4 {
			fmt.Println("❌ 错误: 请指定文件和来源")
			fmt.Println("  用法: portscanner dict-leak <file> <source>")
			return
		}
		categories := []string{}
		if len(os.Args) > 4 {
			categories = strings.Split(os.Args[4], ",")
		}
		runDictLeakImport(os.Args[2], os.Args[3], categories)
	case "dict-add":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定密码")
			fmt.Println("  用法: portscanner dict-add <password>")
			return
		}
		runDictAdd(os.Args[2])
	case "dict-search":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定搜索关键词")
			fmt.Println("  用法: portscanner dict-search <query>")
			return
		}
		runDictSearch(os.Args[2])
	case "dict-export":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定导出文件名")
			fmt.Println("  用法: portscanner dict-export <file> [categories]")
			return
		}
		categories := []string{}
		if len(os.Args) > 3 {
			categories = strings.Split(os.Args[3], ",")
		}
		runDictExport(os.Args[2], categories)
	case "vuln-search":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定服务类型")
			fmt.Println("  用法: portscanner vuln-search <service> [keyword]")
			return
		}
		keyword := ""
		if len(os.Args) > 3 {
			keyword = os.Args[3]
		}
		runVulnSearch(os.Args[2], keyword)
	case "history":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定目标主机")
			fmt.Println("  用法: portscanner history <host>")
			return
		}
		runHistory(os.Args[2])
	case "history-diff":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定目标主机")
			fmt.Println("  用法: portscanner history-diff <host>")
			return
		}
		runHistoryDiff(os.Args[2])
	case "history-export":
		if len(os.Args) < 4 {
			fmt.Println("❌ 错误: 请指定目标主机和导出文件")
			fmt.Println("  用法: portscanner history-export <host> <file>")
			return
		}
		runHistoryExport(os.Args[2], os.Args[3])
	case "block-status":
		runBlockStatus()
	case "block":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定要封禁的端口")
			fmt.Println("  用法: portscanner block <port> [port...]")
			return
		}
		runBlockPorts(os.Args[2:])
	case "unblock":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定要解封的端口")
			fmt.Println("  用法: portscanner unblock <port>")
			return
		}
		runUnblockPort(os.Args[2])
	case "block-auto":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定目标主机")
			fmt.Println("  用法: portscanner block-auto <host>")
			return
		}
		runBlockAuto(os.Args[2])
	case "block-whitelist-add":
		if len(os.Args) < 4 {
			fmt.Println("❌ 错误: 请指定端口和原因")
			fmt.Println("  用法: portscanner block-whitelist-add <port> <reason>")
			return
		}
		runWhitelistAdd(os.Args[2], os.Args[3])
	case "compliance":
		if len(os.Args) < 3 {
			fmt.Println("❌ 错误: 请指定目标主机")
			fmt.Println("  用法: portscanner compliance <host> [level=1/2/3]")
			return
		}
		level := "2"
		if len(os.Args) > 3 {
			level = os.Args[3]
		}
		runCompliance(os.Args[2], level)
	case "-h", "--help", "help":
		printUsage()
	default:
		if strings.HasPrefix(command, "-") {
			runScan()
		} else {
			fmt.Printf("❌ 未知命令: %s\n", command)
			fmt.Println()
			printUsage()
			os.Exit(1)
		}
	}
}

func runScan() {
	target := flag.String("host", "127.0.0.1", "目标主机IP或域名")
	startPort := flag.Int("start", 1, "起始端口")
	endPort := flag.Int("end", 10000, "结束端口")
	timeout := flag.Int("timeout", 1000, "连接超时时间(毫秒)")
	threads := flag.Int("threads", 100, "并发线程数")
	outputHTML := flag.String("html", "", "生成HTML报告文件")
	outputText := flag.String("txt", "", "生成文本报告文件")
	skipVulnCheck := flag.Bool("skip-vuln", false, "跳过漏洞检测")
	fastMode := flag.Bool("fast", false, "快速模式(仅扫描常用端口)")
	passwordLimit := flag.Int("password-limit", 100, "密码检测最大数量")
	noVersionAdvice := flag.Bool("no-version-advice", false, "禁用版本化加固建议")
	autoBlock := flag.Bool("auto-block", false, "自动封禁高危端口")
	dryRun := flag.Bool("dry-run", false, "试运行模式(不实际封禁)")
	saveHistory := flag.Bool("save-history", true, "保存端口快照到历史记录")
	diffHistory := flag.Bool("diff", false, "与上次扫描结果对比")
	complianceLevel := flag.String("compliance", "", "等保合规检查(1/2/3)，空则不检查")

	flag.Parse()

	if *fastMode {
		*startPort = 1
		*endPort = 1000
		*threads = 200
	}

	sm := scanner.GetSignatureManager()
	pm := scanner.GetPasswordManager()

	if needUpdate, reason := sm.CheckUpdate(); needUpdate {
		fmt.Printf("⚠️  特征库: %s\n", reason)
		fmt.Println("   运行 'portscanner sig-update' 更新特征库")
		fmt.Println()
	}

	fmt.Printf("🎯 目标主机: %s\n", *target)
	fmt.Printf("📡 端口范围: %d - %d\n", *startPort, *endPort)
	fmt.Printf("⚡ 并发线程: %d\n", *threads)
	fmt.Printf("⏱️  超时时间: %dms\n", *timeout)
	fmt.Printf("🔐 密码检测: %d 个\n", *passwordLimit)
	fmt.Println()

	if *startPort < 1 || *endPort > 65535 || *startPort > *endPort {
		fmt.Println("❌ 错误: 无效的端口范围")
		flag.Usage()
		os.Exit(1)
	}

	scanConfig := scanner.NewScanConfig(
		*target,
		*startPort,
		*endPort,
		time.Duration(*timeout)*time.Millisecond,
		*threads,
	)

	startTime := time.Now()
	fmt.Println("🔍 正在进行TCP端口扫描...")
	openPorts := scanConfig.ScanWithServiceDetectionManager(sm)
	fmt.Printf("✅ 端口扫描完成，发现 %d 个开放端口\n", len(openPorts))

	var vulns []scanner.Vulnerability
	if !*skipVulnCheck && len(openPorts) > 0 {
		fmt.Println("🔐 正在进行漏洞检测...")
		vulns = scanner.CheckVulnerabilitiesWithManagers(
			*target,
			time.Duration(*timeout)*time.Millisecond,
			openPorts,
			pm,
		)
		fmt.Printf("✅ 漏洞检测完成，发现 %d 个漏洞\n", len(vulns))
	}

	fmt.Println("📊 正在进行风险评估...")
	var riskAssessments []scanner.RiskAssessment
	if *noVersionAdvice {
		riskAssessments = scanner.AssessAllRisks(openPorts)
	} else {
		riskAssessments = scanner.AssessAllRisksWithVersion(openPorts)
	}

	scanDuration := time.Since(startTime)

	scanReport := report.NewScanReport(*target)
	scanReport.ScanDuration = scanDuration
	scanReport.OpenPorts = openPorts
	scanReport.Vulnerabilities = vulns
	scanReport.RiskAssessments = riskAssessments

	scanReport.PrintConsole()

	hm := scanner.NewHistoryManager()

	if *diffHistory {
		changes, err := hm.CompareWithLatest(*target, openPorts)
		if err != nil {
			fmt.Printf("\n⚠️  历史对比: %v\n", err)
		} else {
			hm.PrintChangeReport(changes)
		}
	}

	if *saveHistory {
		if err := hm.SaveSnapshot(*target, openPorts); err != nil {
			fmt.Printf("⚠️  保存历史快照失败: %v\n", err)
		} else {
			fmt.Println("💾 端口快照已保存")
		}
	}

	if *autoBlock {
		fm := scanner.NewFirewallManager(*dryRun)
		fmt.Println("\n🛡️  正在自动封禁高危端口...")
		blockResults := fm.AutoBlockHighRiskPorts(openPorts)
		fm.PrintBlockReport(blockResults)
	}

	if *complianceLevel != "" {
		level := scanner.Level2
		switch *complianceLevel {
		case "1":
			level = scanner.Level1
		case "3":
			level = scanner.Level3
		}
		fmt.Println("\n📋 正在执行等保合规检查...")
		compReport := scanner.RunComplianceCheck(*target, level, openPorts, vulns)
		compReport.PrintConsole()
	}

	if *outputHTML != "" {
		err := scanReport.GenerateHTML(*outputHTML)
		if err != nil {
			fmt.Printf("❌ 生成HTML报告失败: %v\n", err)
		} else {
			fmt.Printf("\n📄 HTML报告已生成: %s\n", *outputHTML)
		}
	}

	if *outputText != "" {
		err := scanReport.GenerateText(*outputText)
		if err != nil {
			fmt.Printf("❌ 生成文本报告失败: %v\n", err)
		} else {
			fmt.Printf("\n📄 文本报告已生成: %s\n", *outputText)
		}
	}

	fmt.Println("\n🎉 扫描完成!")
}

func runSigUpdate() {
	sm := scanner.GetSignatureManager()
	err := sm.Update()
	if err != nil {
		fmt.Printf("❌ 更新失败: %v\n", err)
		return
	}

	info := sm.GetDBInfo()
	fmt.Println()
	fmt.Println("📊 特征库信息:")
	fmt.Printf("   版本: %s\n", info["version"])
	fmt.Printf("   最后更新: %v\n", info["last_updated"])
	fmt.Printf("   覆盖服务: %d 个\n", info["count"])
	fmt.Printf("   校验和: %s\n", info["checksum"])
}

func runSigInfo() {
	sm := scanner.GetSignatureManager()
	info := sm.GetDBInfo()

	fmt.Println("📊 特征库信息:")
	fmt.Println(strings.Repeat("-", 50))
	fmt.Printf("   版本:        %s\n", info["version"])
	fmt.Printf("   最后更新:    %v\n", info["last_updated"])
	fmt.Printf("   数据来源:    %s\n", info["source"])
	fmt.Printf("   覆盖服务:    %d 个\n", info["count"])
	fmt.Printf("   校验和:      %s\n", info["checksum"])
	fmt.Println()

	needUpdate, reason := sm.CheckUpdate()
	if needUpdate {
		fmt.Printf("⚠️  更新提示: %s\n", reason)
	} else {
		fmt.Println("✅ 特征库为最新版本")
	}

	fmt.Println()
	fmt.Println("📋 已加载的服务特征:")
	fmt.Println(strings.Repeat("-", 50))
	sigs := sm.GetAllSignatures()
	var ports []int
	for port := range sigs {
		ports = append(ports, port)
	}
	for _, port := range ports {
		sig := sigs[port]
		fmt.Printf("   %-6d %-15s 更新: %s\n", port, sig.Service, sig.UpdatedAt)
	}
}

func runSigExport(filename string) {
	sm := scanner.GetSignatureManager()
	err := sm.ExportSignatures(filename)
	if err != nil {
		fmt.Printf("❌ 导出失败: %v\n", err)
		return
	}
	fmt.Printf("✅ 特征库已导出到: %s\n", filename)
}

func runSigImport(filename string) {
	sm := scanner.GetSignatureManager()
	err := sm.ImportSignatures(filename)
	if err != nil {
		fmt.Printf("❌ 导入失败: %v\n", err)
		return
	}
	fmt.Println("✅ 特征库导入成功")
	runSigInfo()
}

func runDictInfo() {
	pm := scanner.GetPasswordManager()
	info := pm.GetDBInfo()

	fmt.Println("🔐 密码字典库信息:")
	fmt.Println(strings.Repeat("-", 50))
	fmt.Printf("   版本:        %s\n", info["version"])
	fmt.Printf("   最后更新:    %s\n", info["last_updated"])
	fmt.Printf("   密码总数:    %d 个\n", info["total_count"])
	fmt.Printf("   校验和:      %s\n", info["checksum"])
	fmt.Println()

	sources := info["sources"].(map[string]int)
	fmt.Println("📂 数据来源:")
	for source, count := range sources {
		fmt.Printf("   %-20s: %d 个\n", source, count)
	}

	fmt.Println()
	categories := info["categories"].(map[string]int)
	fmt.Println("🏷️  分类统计:")
	for cat, count := range categories {
		fmt.Printf("   %-20s: %d 个\n", cat, count)
	}

	fmt.Println()
	fmt.Printf("📁 自定义字典目录: %s\n", pm.GetCustomDir())
	fmt.Println("   放入 .txt 或 .dict 文件将自动加载")
}

func runDictImport(filename, source string) {
	pm := scanner.GetPasswordManager()
	err := pm.ImportDictionary(filename, source)
	if err != nil {
		fmt.Printf("❌ 导入失败: %v\n", err)
		return
	}
	fmt.Printf("✅ 字典导入成功\n")
	runDictInfo()
}

func runDictLeakImport(filename, source string, categories []string) {
	pm := scanner.GetPasswordManager()
	err := pm.ImportLeakDB(filename, source, categories)
	if err != nil {
		fmt.Printf("❌ 导入失败: %v\n", err)
		return
	}
	fmt.Printf("✅ 泄露库导入成功\n")
	runDictInfo()
}

func runDictAdd(password string) {
	pm := scanner.GetPasswordManager()
	err := pm.AddCustomPassword(password, "manual", []string{"custom", "manual"})
	if err != nil {
		fmt.Printf("❌ 添加失败: %v\n", err)
		return
	}
	fmt.Printf("✅ 密码 '%s' 已添加\n", password)
}

func runDictSearch(query string) {
	pm := scanner.GetPasswordManager()
	results := pm.SearchPasswords(query, 20)

	if len(results) == 0 {
		fmt.Printf("❌ 未找到包含 '%s' 的密码\n", query)
		return
	}

	fmt.Printf("🔍 找到 %d 个包含 '%s' 的密码:\n", len(results), query)
	fmt.Println(strings.Repeat("-", 80))
	fmt.Printf("   %-30s %-10s %-20s %s\n", "密码", "出现次数", "来源", "分类")
	fmt.Println(strings.Repeat("-", 80))
	for _, entry := range results {
		cats := strings.Join(entry.Categories, ", ")
		fmt.Printf("   %-30s %-10d %-20s %s\n", entry.Password, entry.Count, entry.Source, cats)
	}
}

func runDictExport(filename string, categories []string) {
	pm := scanner.GetPasswordManager()
	err := pm.ExportPasswords(filename, categories)
	if err != nil {
		fmt.Printf("❌ 导出失败: %v\n", err)
		return
	}

	if len(categories) > 0 {
		fmt.Printf("✅ 分类 [%s] 的密码已导出到: %s\n", strings.Join(categories, ", "), filename)
	} else {
		fmt.Printf("✅ 所有密码已导出到: %s\n", filename)
	}
}

func runVulnSearch(service, keyword string) {
	vulns := scanner.SearchVulnerabilities(service, keyword)

	if len(vulns) == 0 {
		fmt.Printf("❌ 未找到 %s 服务的漏洞信息\n", service)
		return
	}

	fmt.Printf("🔍 找到 %d 个 %s 服务相关的漏洞:\n", len(vulns), service)
	fmt.Println(strings.Repeat("-", 100))

	for i, vuln := range vulns {
		severityColor := scanner.GetRiskColor(vuln.Severity)
		fmt.Printf("%d. %s[%s]%s %s\n", i+1, severityColor, vuln.Severity, "\033[0m", vuln.CVE)
		fmt.Printf("   CVSS评分: %.1f\n", vuln.CVSSScore)
		fmt.Printf("   描述: %s\n", vuln.Description)
		if len(vuln.AffectedVersions) >= 2 {
			fmt.Printf("   影响版本: %s - %s\n", vuln.AffectedVersions[0], vuln.AffectedVersions[1])
		}
		if len(vuln.FixedVersions) > 0 {
			fmt.Printf("   修复版本: %s\n", strings.Join(vuln.FixedVersions, ", "))
		}
		if len(vuln.Recommendations) > 0 {
			fmt.Printf("   建议: %s\n", strings.Join(vuln.Recommendations, "; "))
		}
		fmt.Println()
	}

	services := scanner.GetAllServicesWithVersions()
	fmt.Println("📋 支持漏洞查询的服务版本:")
	for svc, versions := range services {
		fmt.Printf("   %-10s: %s\n", svc, strings.Join(versions, ", "))
	}
}

func runHistory(target string) {
	hm := scanner.NewHistoryManager()

	stats, err := hm.GetChangeStats(target)
	if err != nil {
		fmt.Printf("❌ 获取历史统计失败: %v\n", err)
		return
	}

	fmt.Printf("📊 端口历史记录 - %s\n", target)
	fmt.Println(strings.Repeat("-", 60))
	fmt.Printf("   快照总数:   %d\n", stats["total_snapshots"])
	fmt.Printf("   新开放端口: %d 次\n", stats["total_new_open"])
	fmt.Printf("   已关闭端口: %d 次\n", stats["total_closed"])
	fmt.Printf("   服务变更:   %d 次\n", stats["total_changed"])

	snapshots, err := hm.GetSnapshotHistory(target, 10)
	if err != nil || len(snapshots) == 0 {
		fmt.Println("\n⚠️  无历史快照记录")
		return
	}

	fmt.Println("\n📅 最近快照:")
	for _, snap := range snapshots {
		fmt.Printf("   %s - 开放端口: %d 个\n",
			snap.ScanTime.Format("2006-01-02 15:04:05"), snap.TotalOpen)

		portList := make([]string, 0, len(snap.OpenPorts))
		for _, p := range snap.OpenPorts {
			portList = append(portList, fmt.Sprintf("%d/%s", p.Port, p.Service))
		}
		if len(portList) > 8 {
			portList = append(portList[:8], "...")
		}
		fmt.Printf("      端口: %s\n", strings.Join(portList, ", "))
	}
}

func runHistoryDiff(target string) {
	hm := scanner.NewHistoryManager()

	snapshots, err := hm.GetSnapshotHistory(target, 2)
	if err != nil || len(snapshots) < 2 {
		fmt.Println("❌ 需要至少2次历史快照才能对比")
		fmt.Println("   请先运行扫描建立基线: portscanner scan -host " + target)
		return
	}

	var currentPorts []scanner.PortResult
	for _, p := range snapshots[0].OpenPorts {
		currentPorts = append(currentPorts, scanner.PortResult{
			Port: p.Port, Service: p.Service, Version: p.Version, State: p.State,
		})
	}

	changes := hm.CompareSnapshots(snapshots[1], currentPorts)
	hm.PrintChangeReport(changes)
}

func runHistoryExport(target, filename string) {
	hm := scanner.NewHistoryManager()
	err := hm.ExportHistory(target, filename)
	if err != nil {
		fmt.Printf("❌ 导出失败: %v\n", err)
		return
	}
	fmt.Printf("✅ 历史记录已导出到: %s\n", filename)
}

func runBlockStatus() {
	fm := scanner.NewFirewallManager(true)
	fm.PrintStatus()
}

func runBlockPorts(portArgs []string) {
	fm := scanner.NewFirewallManager(false)

	var ports []int
	for _, arg := range portArgs {
		var port int
		fmt.Sscanf(arg, "%d", &port)
		if port > 0 && port <= 65535 {
			ports = append(ports, port)
		}
	}

	if len(ports) == 0 {
		fmt.Println("❌ 错误: 无有效端口号")
		return
	}

	results := fm.BlockSpecificPorts(ports, "手动封禁")
	fm.PrintBlockReport(results)
}

func runUnblockPort(portStr string) {
	fm := scanner.NewFirewallManager(false)

	var port int
	fmt.Sscanf(portStr, "%d", &port)
	if port <= 0 {
		fmt.Println("❌ 错误: 无效端口号")
		return
	}

	result := fm.UnblockPort(port)
	if result.Success {
		fmt.Printf("✅ 端口 %d 已解封\n", port)
	} else {
		fmt.Printf("❌ 解封失败: %s\n", result.Output)
	}
}

func runBlockAuto(target string) {
	fmt.Printf("🛡️  自动封禁高危端口 - 目标: %s\n", target)
	fmt.Println("⚠️  注意: 此操作将修改防火墙规则！")
	fmt.Print("确认继续? (y/N): ")

	var confirm string
	fmt.Scanln(&confirm)
	if strings.ToLower(confirm) != "y" {
		fmt.Println("已取消")
		return
	}

	fm := scanner.NewFirewallManager(false)
	fm.SetAutoBlock(true)

	scanConfig := scanner.NewScanConfig(target, 1, 10000, 1000*time.Millisecond, 200)
	openPorts := scanConfig.ScanWithServiceDetectionManager(scanner.GetSignatureManager())

	if len(openPorts) == 0 {
		fmt.Println("未发现开放端口")
		return
	}

	results := fm.AutoBlockHighRiskPorts(openPorts)
	fm.PrintBlockReport(results)
}

func runWhitelistAdd(portStr, reason string) {
	fm := scanner.NewFirewallManager(true)

	var port int
	fmt.Sscanf(portStr, "%d", &port)
	if port <= 0 {
		fmt.Println("❌ 错误: 无效端口号")
		return
	}

	fm.AddWhitelist(port, reason)
	fmt.Printf("✅ 端口 %d 已加入白名单: %s\n", port, reason)
}

func runCompliance(target, levelStr string) {
	var level scanner.ComplianceLevel
	switch levelStr {
	case "1":
		level = scanner.Level1
	case "3":
		level = scanner.Level3
	default:
		level = scanner.Level2
	}

	fmt.Printf("📋 等保%s合规检查 - 目标: %s\n", level, target)
	fmt.Println("🔍 正在扫描端口...")

	scanConfig := scanner.NewScanConfig(target, 1, 10000, 1000*time.Millisecond, 200)
	openPorts := scanConfig.ScanWithServiceDetectionManager(scanner.GetSignatureManager())

	pm := scanner.GetPasswordManager()
	vulns := scanner.CheckVulnerabilitiesWithManagers(target, 1000*time.Millisecond, openPorts, pm)

	fmt.Println("📋 正在执行合规检查...")
	report := scanner.RunComplianceCheck(target, level, openPorts, vulns)
	report.PrintConsole()
}
