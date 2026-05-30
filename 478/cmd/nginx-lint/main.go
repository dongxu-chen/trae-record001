package main

import (
	"flag"
	"fmt"
	"nginx-lint/internal/fixer"
	"nginx-lint/internal/model"
	"nginx-lint/internal/perf"
	"nginx-lint/internal/validator"
	"os"
	"path/filepath"
	"strings"
)

type options struct {
	files       []string
	directories []string
	recursive   bool
	noInclude   bool
	noVariable  bool
	noDirective bool
	noSecurity  bool
	noPerf      bool
	format      string
	quiet       bool
	verbose     bool
	warnAsError bool
	strict      bool
	showInfo    bool
	fix         bool
	perfOnly    bool
}

func main() {
	opts := parseFlags()

	if len(opts.files) == 0 && len(opts.directories) == 0 {
		fmt.Println("错误: 请指定要检查的配置文件或目录")
		fmt.Println()
		flag.Usage()
		os.Exit(1)
	}

	v := validator.NewValidator()
	v.ResolveIncludes = !opts.noInclude
	v.CheckVariables = !opts.noVariable
	v.CheckDirectives = !opts.noDirective
	v.CheckSecurity = !opts.noSecurity
	v.CheckPerf = !opts.noPerf
	v.StrictMode = opts.strict
	v.ShowInfo = opts.showInfo || opts.verbose

	var results []*validator.LintResult

	for _, file := range opts.files {
		result, err := v.ValidateFile(file)
		if err != nil {
			fmt.Fprintf(os.Stderr, "错误: %v\n", err)
			os.Exit(1)
		}
		results = append(results, result)
	}

	for _, dir := range opts.directories {
		dirResults, err := v.ValidateDirectory(dir, opts.recursive)
		if err != nil {
			fmt.Fprintf(os.Stderr, "错误: %v\n", err)
			os.Exit(1)
		}
		results = append(results, dirResults...)
	}

	exitCode := printResults(results, opts)
	if opts.fix {
		printFixScript(results)
	}
	os.Exit(exitCode)
}

func parseFlags() *options {
	opts := &options{}

	flag.StringVar(&opts.format, "format", "text", "输出格式: text, compact, json")
	flag.BoolVar(&opts.recursive, "r", false, "递归扫描目录")
	flag.BoolVar(&opts.recursive, "recursive", false, "递归扫描目录")
	flag.BoolVar(&opts.noInclude, "no-include", false, "禁用include文件解析")
	flag.BoolVar(&opts.noVariable, "no-variable", false, "禁用变量检测")
	flag.BoolVar(&opts.noDirective, "no-directive", false, "禁用指令校验")
	flag.BoolVar(&opts.noSecurity, "no-security", false, "禁用安全配置检查")
	flag.BoolVar(&opts.noPerf, "no-perf", false, "禁用性能分析")
	flag.BoolVar(&opts.quiet, "q", false, "安静模式，仅显示错误")
	flag.BoolVar(&opts.quiet, "quiet", false, "安静模式，仅显示错误")
	flag.BoolVar(&opts.verbose, "v", false, "详细模式，显示所有信息包括INFO")
	flag.BoolVar(&opts.verbose, "verbose", false, "详细模式，显示所有信息包括INFO")
	flag.BoolVar(&opts.warnAsError, "Werror", false, "将警告视为错误")
	flag.BoolVar(&opts.strict, "strict", false, "严格模式：未知指令报警告(默认白名单模式不报错)")
	flag.BoolVar(&opts.showInfo, "show-info", false, "显示INFO级别信息(如第三方模块指令)")
	flag.BoolVar(&opts.fix, "fix", false, "生成自动修复脚本")
	flag.BoolVar(&opts.perfOnly, "perf-only", false, "仅输出性能分析报告")

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "Nginx 配置语法检查工具\n\n")
		fmt.Fprintf(os.Stderr, "用法:\n")
		fmt.Fprintf(os.Stderr, "  %s [选项] <文件或目录>...\n\n", filepath.Base(os.Args[0]))
		fmt.Fprintf(os.Stderr, "选项:\n")
		flag.PrintDefaults()
		fmt.Fprintf(os.Stderr, "\n示例:\n")
		fmt.Fprintf(os.Stderr, "  检查单个文件: %s /etc/nginx/nginx.conf\n", filepath.Base(os.Args[0]))
		fmt.Fprintf(os.Stderr, "  白名单模式(默认): %s nginx.conf\n", filepath.Base(os.Args[0]))
		fmt.Fprintf(os.Stderr, "  严格模式: %s -strict nginx.conf\n", filepath.Base(os.Args[0]))
		fmt.Fprintf(os.Stderr, "  显示第三方模块指令: %s -show-info nginx.conf\n", filepath.Base(os.Args[0]))
		fmt.Fprintf(os.Stderr, "  生成修复脚本: %s -fix nginx.conf\n", filepath.Base(os.Args[0]))
		fmt.Fprintf(os.Stderr, "  性能分析: %s -perf-only nginx.conf\n", filepath.Base(os.Args[0]))
		fmt.Fprintf(os.Stderr, "  JSON输出: %s -format json nginx.conf\n", filepath.Base(os.Args[0]))
	}

	flag.Parse()

	args := flag.Args()
	for _, arg := range args {
		info, err := os.Stat(arg)
		if err != nil {
			fmt.Fprintf(os.Stderr, "警告: 无法访问 '%s': %v\n", arg, err)
			continue
		}
		if info.IsDir() {
			opts.directories = append(opts.directories, arg)
		} else {
			opts.files = append(opts.files, arg)
		}
	}

	return opts
}

func printResults(results []*validator.LintResult, opts *options) int {
	if opts.perfOnly {
		printPerfReports(results)
		return 0
	}

	totalErrors := 0
	totalWarnings := 0
	totalInfos := 0
	totalFiles := len(results)
	filesWithErrors := 0

	for _, result := range results {
		if result.HasErrors() || (opts.warnAsError && result.HasWarnings()) {
			filesWithErrors++
		}
		totalErrors += result.ErrorCount()
		totalWarnings += result.WarningCount()
		for _, e := range result.Errors {
			if e.Severity == model.SeverityInfo {
				totalInfos++
			}
		}

		shouldPrint := !opts.quiet || result.HasErrors() || (opts.warnAsError && result.HasWarnings())
		if shouldPrint {
			printFileResult(result, opts)
		}
	}

	if !opts.quiet || opts.verbose {
		fmt.Println(strings.Repeat("=", 60))
		fmt.Printf("检查完成: 共 %d 个文件\n", totalFiles)
		if totalErrors > 0 {
			fmt.Printf("  错误: %d\n", totalErrors)
		}
		if totalWarnings > 0 {
			fmt.Printf("  警告: %d\n", totalWarnings)
		}
		if totalInfos > 0 && (opts.showInfo || opts.verbose) {
			fmt.Printf("  信息: %d (第三方模块指令等，使用 -show-info 查看)\n", totalInfos)
		}
		if filesWithErrors > 0 {
			fmt.Printf("  有问题的文件: %d\n", filesWithErrors)
		}
		if totalErrors == 0 && totalWarnings == 0 {
			fmt.Println("  所有配置文件检查通过!")
		}

		for _, result := range results {
			if result.PerfReport != nil && !opts.noPerf {
				fmt.Println()
				fmt.Print(perf.FormatPerfReport(result.PerfReport))
				break
			}
		}
	}

	if totalErrors > 0 || (opts.warnAsError && totalWarnings > 0) {
		return 1
	}
	return 0
}

func printFileResult(result *validator.LintResult, opts *options) {
	if !opts.quiet {
		fmt.Printf("\n文件: %s\n", result.FilePath)
		if !result.HasErrors() && !result.HasWarnings() {
			fmt.Println("  ✓ 检查通过")
		} else {
			if result.ErrorCount() > 0 {
				fmt.Printf("  ✗ %d 个错误", result.ErrorCount())
				if result.WarningCount() > 0 {
					fmt.Printf(", %d 个警告\n", result.WarningCount())
				} else {
					fmt.Println()
				}
			} else if result.WarningCount() > 0 {
				fmt.Printf("  ⚠ %d 个警告\n", result.WarningCount())
			}
		}
	}

	if len(result.Errors) > 0 {
		for _, err := range result.Errors {
			if opts.quiet && err.Severity != model.SeverityError {
				continue
			}
			if err.Severity == model.SeverityInfo && !opts.showInfo && !opts.verbose {
				continue
			}
			fmt.Println(validator.FormatError(err, opts.format))
		}
	}

	if len(result.Fixes) > 0 && opts.verbose {
		fmt.Println()
		fmt.Print(fixer.FormatFixSummary(result.Fixes))
	}
}

func printFixScript(results []*validator.LintResult) {
	var allFixes []*fixer.FixSuggestion
	for _, result := range results {
		allFixes = append(allFixes, result.Fixes...)
	}
	if len(allFixes) == 0 {
		fmt.Println("\n没有可修复的问题")
		return
	}
	fmt.Println()
	fmt.Println(fixer.FormatFixScript(allFixes))
}

func printPerfReports(results []*validator.LintResult) {
	for _, result := range results {
		if result.PerfReport != nil {
			fmt.Printf("文件: %s\n", result.FilePath)
			fmt.Print(perf.FormatPerfReport(result.PerfReport))
			fmt.Println()
		}
	}
}
