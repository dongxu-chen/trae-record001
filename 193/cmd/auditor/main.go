package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/sirupsen/logrus"

	"k8s-auditor/pkg/audit"
	"k8s-auditor/pkg/config"
	"k8s-auditor/pkg/rbacchecker"
	"k8s-auditor/pkg/remediator"
	"k8s-auditor/pkg/reporter"
	"k8s-auditor/pkg/scheduler"
	"k8s-auditor/pkg/scanner"
	"k8s-auditor/pkg/trends"
	"k8s-auditor/pkg/webhook"
)

func main() {
	var (
		configPath    = flag.String("config", "config.yaml", "配置文件路径")
		once          = flag.Bool("once", false, "只执行一次审计后退出")
		daemon        = flag.Bool("daemon", false, "以守护进程模式运行，定时执行审计")
		outputDir     = flag.String("output", "", "报告输出目录（覆盖配置文件）")
		namespace     = flag.String("namespace", "", "指定命名空间（覆盖配置文件）")
		remediate     = flag.Bool("remediate", false, "自动修复违规项")
		dryRun        = flag.Bool("dry-run", false, "试运行模式，不实际修改资源")
		skipTrends    = flag.Bool("no-trends", false, "禁用趋势分析")
		skipRBAC      = flag.Bool("no-rbac", false, "禁用RBAC权限审计")
	)
	flag.Parse()

	logger := logrus.New()
	logger.SetFormatter(&logrus.TextFormatter{
		FullTimestamp: true,
	})

	cfg, err := config.Load(*configPath)
	if err != nil {
		logger.Fatalf("加载配置文件失败: %v", err)
	}

	if *outputDir != "" {
		cfg.Audit.OutputDir = *outputDir
	}
	if *namespace != "" {
		cfg.Namespace = *namespace
	}
	if *remediate {
		cfg.Audit.AutoRemediate = true
	}
	if *dryRun {
		cfg.Audit.DryRun = true
	}
	if *skipTrends {
		cfg.Audit.EnableTrends = false
	}
	if *skipRBAC {
		cfg.Audit.EnableRBAC = false
	}

	logger.Info("正在初始化Kubernetes客户端...")
	sc, err := scanner.New(cfg.Kubeconfig, cfg.Namespace)
	if err != nil {
		logger.Fatalf("创建Scanner失败: %v", err)
	}

	auditor := audit.New(sc, cfg)
	rep := reporter.New(cfg.Audit.OutputDir)
	wh := webhook.New(cfg.Webhook)
	rem := remediator.New(sc, cfg.Audit.DryRun)
	trendAnalyzer := trends.New(cfg.Audit.OutputDir)
	rbacChecker := rbacchecker.New(sc)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		<-sigCh
		logger.Info("收到退出信号，正在关闭...")
		cancel()
	}()

	if *once {
		runOnce(ctx, auditor, rep, wh, rem, trendAnalyzer, rbacChecker, cfg, logger)
		return
	}

	if *daemon || cfg.Audit.Schedule != "" {
		sched := scheduler.New(auditor, rep, wh, cfg.Audit.Schedule)
		if err := sched.Start(ctx); err != nil {
			logger.Errorf("调度器错误: %v", err)
		}
		return
	}

	runOnce(ctx, auditor, rep, wh, rem, trendAnalyzer, rbacChecker, cfg, logger)
}

func runOnce(ctx context.Context, auditor *audit.Auditor, rep *reporter.Reporter, wh *webhook.WebhookNotifier,
	rem *remediator.Remediator, trendAnalyzer *trends.TrendAnalyzer, rbacChecker *rbacchecker.RBACChecker,
	cfg *config.Config, logger *logrus.Logger) {

	logger.Info("开始执行Kubernetes资源审计...")

	report, err := auditor.Run(ctx)
	if err != nil {
		logger.Fatalf("审计执行失败: %v", err)
	}

	if cfg.Audit.EnableRBAC {
		logger.Info("执行RBAC权限审计...")
		rbacReport, err := rbacChecker.Check(ctx)
		if err != nil {
			logger.Errorf("RBAC审计失败: %v", err)
		} else {
			rbacViolations := rbacChecker.ConvertToAuditViolations(rbacReport)
			report.Violations = append(report.Violations, rbacViolations...)
			for _, v := range rbacViolations {
				report.Summary[string(v.Severity)]++
				ruleKey := v.RuleType + ":" + string(v.Severity)
				report.Summary[ruleKey]++
			}
			fmt.Println("\n" + rbacChecker.GenerateReport(rbacReport))
		}
	}

	jsonPath, yamlPath, err := rep.GenerateReport(report)
	if err != nil {
		logger.Errorf("生成报告失败: %v", err)
	} else {
		logger.Infof("JSON报告: %s", jsonPath)
		logger.Infof("YAML报告: %s", yamlPath)
	}

	textPath, err := rep.SaveTextReport(report)
	if err != nil {
		logger.Errorf("保存文本报告失败: %v", err)
	} else {
		logger.Infof("文本报告: %s", textPath)
	}

	fmt.Println("\n" + rep.GenerateTextReport(report))

	if cfg.Audit.EnableTrends {
		if err := trendAnalyzer.Record(report); err != nil {
			logger.Errorf("记录审计历史失败: %v", err)
		} else {
			analysis, err := trendAnalyzer.Analyze()
			if err != nil {
				logger.Errorf("趋势分析失败: %v", err)
			} else {
				fmt.Println(trendAnalyzer.GenerateReport(analysis))
			}
		}
	}

	if cfg.Audit.AutoRemediate && len(report.Violations) > 0 {
		logger.Info("开始自动修复违规项...")
		if cfg.Audit.DryRun {
			logger.Info("Dry Run模式: 不会实际修改资源")
		}
		actions, err := rem.Remediate(ctx, report.Violations)
		if err != nil {
			logger.Errorf("自动修复失败: %v", err)
		} else {
			fmt.Println(rem.GenerateReport())
			_ = actions
		}
	}

	if wh.Enabled() {
		if err := wh.Send(report); err != nil {
			logger.Errorf("发送Webhook通知失败: %v", err)
		} else {
			logger.Info("Webhook通知已发送")
		}
	}

	if len(report.Violations) > 0 {
		logger.Warnf("审计完成，发现 %d 个违规项", len(report.Violations))
		os.Exit(1)
	}

	logger.Info("审计完成，未发现违规项")
}
