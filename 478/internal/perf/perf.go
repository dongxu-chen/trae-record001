package perf

import (
	"fmt"
	"nginx-lint/internal/model"
	"strings"
)

type PerfReport struct {
	TotalDirectives    int
	TotalBlocks        int
	TotalIncludes      int
	MaxNestingDepth    int
	ServerCount        int
	LocationCount      int
	UpstreamCount      int
	MapCount           int
	GeoCount           int
	RegexLocations     int
	ComplexRegexLocs   int
	VariableCount      int
	EstMemoryKB        int
	FileSizeBytes      int64
	ComplexityScore    int
	Warnings           []*model.LintError
	Suggestions        []string
	DirectiveHistogram map[string]int
}

type PerfAnalyzer struct {
	report       *PerfReport
	currentDepth int
	maxDepth     int
}

func NewPerfAnalyzer() *PerfAnalyzer {
	return &PerfAnalyzer{
		report: &PerfReport{
			DirectiveHistogram: make(map[string]int),
			Warnings:           []*model.LintError{},
			Suggestions:        []string{},
		},
	}
}

func (pa *PerfAnalyzer) Analyze(nodes []*model.Node) *PerfReport {
	pa.analyzeNodes(nodes)
	pa.calculateMemoryEstimate()
	pa.calculateComplexityScore()
	pa.generateSuggestions()
	return pa.report
}

func (pa *PerfAnalyzer) analyzeNodes(nodes []*model.Node) {
	for _, node := range nodes {
		if node.Type == model.NodeComment {
			continue
		}

		if node.Type == model.NodeDirective {
			pa.report.TotalDirectives++
			pa.report.DirectiveHistogram[node.Directive]++

			switch node.Directive {
			case "set":
				pa.report.VariableCount++
			case "include":
				pa.report.TotalIncludes++
			case "map":
				pa.report.MapCount++
			case "geo":
				pa.report.GeoCount++
			}
		}

		if node.Type == model.NodeBlock {
			pa.report.TotalBlocks++

			switch node.Directive {
			case "server":
				pa.report.ServerCount++
			case "location":
				pa.report.LocationCount++
				pa.analyzeLocationRegex(node)
			case "upstream":
				pa.report.UpstreamCount++
			}

			pa.currentDepth++
			if pa.currentDepth > pa.maxDepth {
				pa.maxDepth = pa.currentDepth
			}
			pa.analyzeNodes(node.Children)
			pa.currentDepth--
		}
	}

	pa.report.MaxNestingDepth = pa.maxDepth
}

func (pa *PerfAnalyzer) analyzeLocationRegex(node *model.Node) {
	if len(node.Arguments) == 0 {
		return
	}

	locPath := node.Arguments[0]

	if strings.HasPrefix(locPath, "~") {
		pa.report.RegexLocations++
		if strings.HasPrefix(locPath, "~*") {
			locPath = locPath[2:]
		} else {
			locPath = locPath[1:]
		}

		complexPatterns := []string{
			"(?:", "(?=", "(?!)", "(?<=", "(?<!",
			"\\d+", "\\w+", "\\S+", ".*", ".+",
			"[^", "{2,", "{3,",
		}
		for _, pattern := range complexPatterns {
			if strings.Contains(locPath, pattern) {
				pa.report.ComplexRegexLocs++
				pa.addPerfWarning(node.Pos, "PERF_COMPLEX_REGEX",
					"location使用复杂正则表达式可能导致性能问题: "+node.Arguments[0],
					"考虑使用前缀匹配代替正则匹配，或简化正则表达式")
				break
			}
		}
	}

	if len(node.Arguments) > 1 {
		for _, arg := range node.Arguments[1:] {
			if strings.HasPrefix(arg, "~") {
				pa.report.RegexLocations++
			}
		}
	}
}

func (pa *PerfAnalyzer) calculateMemoryEstimate() {
	mem := 0

	mem += pa.report.TotalDirectives * 256
	mem += pa.report.TotalBlocks * 512
	mem += pa.report.ServerCount * 8192
	mem += pa.report.LocationCount * 4096
	mem += pa.report.UpstreamCount * 2048
	mem += pa.report.MapCount * 4096
	mem += pa.report.GeoCount * 2048
	mem += pa.report.VariableCount * 128
	mem += pa.report.RegexLocations * 1024

	sslCount := pa.report.DirectiveHistogram["ssl_certificate"]
	mem += sslCount * 16384

	accessLogCount := pa.report.DirectiveHistogram["access_log"]
	mem += accessLogCount * 4096

	proxyPassCount := pa.report.DirectiveHistogram["proxy_pass"]
	mem += proxyPassCount * 2048

	limitReqCount := pa.report.DirectiveHistogram["limit_req_zone"]
	mem += limitReqCount * 8192

	pa.report.EstMemoryKB = mem
}

func (pa *PerfAnalyzer) calculateComplexityScore() {
	score := 0

	score += pa.report.TotalDirectives
	score += pa.report.TotalBlocks * 2
	score += pa.report.ServerCount * 5
	score += pa.report.LocationCount * 3
	score += pa.report.RegexLocations * 5
	score += pa.report.ComplexRegexLocs * 10
	score += pa.report.MapCount * 8
	score += pa.report.GeoCount * 6
	score += pa.report.MaxNestingDepth * 3
	score += pa.report.VariableCount * 2

	if pa.report.MaxNestingDepth > 6 {
		score += (pa.report.MaxNestingDepth - 6) * 10
	}

	pa.report.ComplexityScore = score
}

func (pa *PerfAnalyzer) generateSuggestions() {
	if pa.report.ServerCount > 50 {
		pa.report.Suggestions = append(pa.report.Suggestions,
			fmt.Sprintf("配置包含 %d 个server块，建议拆分为独立配置文件并使用include引入",
				pa.report.ServerCount))
	}

	if pa.report.LocationCount > 200 {
		pa.report.Suggestions = append(pa.report.Suggestions,
			fmt.Sprintf("配置包含 %d 个location块，过多location会增加请求匹配延迟，考虑合并相似配置",
				pa.report.LocationCount))
	}

	if pa.report.RegexLocations > 20 {
		pa.report.Suggestions = append(pa.report.Suggestions,
			fmt.Sprintf("配置包含 %d 个正则location，正则匹配按声明顺序执行，过多正则影响性能，建议使用前缀匹配",
				pa.report.RegexLocations))
	}

	if pa.report.ComplexRegexLocs > 5 {
		pa.report.Suggestions = append(pa.report.Suggestions,
			fmt.Sprintf("配置包含 %d 个复杂正则location，建议简化或使用前缀匹配+rewrite替代",
				pa.report.ComplexRegexLocs))
	}

	if pa.report.MapCount > 10 {
		pa.report.Suggestions = append(pa.report.Suggestions,
			fmt.Sprintf("配置包含 %d 个map块，每个map在请求处理时都会查找，考虑合并相关map",
				pa.report.MapCount))
	}

	if pa.report.MaxNestingDepth > 6 {
		pa.report.Suggestions = append(pa.report.Suggestions,
			fmt.Sprintf("最大嵌套深度为 %d，过深的嵌套增加配置解析开销和维护难度",
				pa.report.MaxNestingDepth))
	}

	if pa.report.EstMemoryKB > 102400 {
		pa.report.Suggestions = append(pa.report.Suggestions,
			fmt.Sprintf("预估内存消耗 %d KB（约 %d MB），确保worker进程有足够内存",
				pa.report.EstMemoryKB, pa.report.EstMemoryKB/1024))
	}

	totalIfCount := pa.report.DirectiveHistogram["if"]
	if totalIfCount > 10 {
		pa.report.Suggestions = append(pa.report.Suggestions,
			fmt.Sprintf("配置包含 %d 个if指令，Nginx的if指令(Evil If)可能导致意外行为，建议使用map或try_files替代",
				totalIfCount))
	}

	rewriteCount := pa.report.DirectiveHistogram["rewrite"]
	if rewriteCount > 15 {
		pa.report.Suggestions = append(pa.report.Suggestions,
			fmt.Sprintf("配置包含 %d 个rewrite指令，过多rewrite增加请求处理延迟，考虑优化路由结构",
				rewriteCount))
	}
}

func (pa *PerfAnalyzer) addPerfWarning(pos model.Position, ruleID, msg, suggestion string) {
	pa.report.Warnings = append(pa.report.Warnings, &model.LintError{
		Pos:        pos,
		Severity:   model.SeverityWarning,
		RuleID:     ruleID,
		Message:    msg,
		Suggestion: suggestion,
	})
}

func Analyze(nodes []*model.Node) *PerfReport {
	analyzer := NewPerfAnalyzer()
	return analyzer.Analyze(nodes)
}

func FormatPerfReport(report *PerfReport) string {
	var sb strings.Builder

	sb.WriteString("性能分析报告\n")
	sb.WriteString(strings.Repeat("=", 50) + "\n\n")

	sb.WriteString("配置统计:\n")
	sb.WriteString(fmt.Sprintf("  指令总数:     %d\n", report.TotalDirectives))
	sb.WriteString(fmt.Sprintf("  块总数:       %d\n", report.TotalBlocks))
	sb.WriteString(fmt.Sprintf("  include引用:  %d\n", report.TotalIncludes))
	sb.WriteString(fmt.Sprintf("  最大嵌套深度: %d\n", report.MaxNestingDepth))
	sb.WriteString("\n")

	sb.WriteString("核心组件:\n")
	sb.WriteString(fmt.Sprintf("  server块:   %d\n", report.ServerCount))
	sb.WriteString(fmt.Sprintf("  location块: %d (正则: %d, 复杂正则: %d)\n",
		report.LocationCount, report.RegexLocations, report.ComplexRegexLocs))
	sb.WriteString(fmt.Sprintf("  upstream块: %d\n", report.UpstreamCount))
	sb.WriteString(fmt.Sprintf("  map块:      %d\n", report.MapCount))
	sb.WriteString(fmt.Sprintf("  geo块:      %d\n", report.GeoCount))
	sb.WriteString(fmt.Sprintf("  变量定义:   %d\n", report.VariableCount))
	sb.WriteString("\n")

	sb.WriteString("资源预估:\n")
	if report.EstMemoryKB >= 1024 {
		sb.WriteString(fmt.Sprintf("  预估内存消耗: %d KB (约 %d MB)\n",
			report.EstMemoryKB, report.EstMemoryKB/1024))
	} else {
		sb.WriteString(fmt.Sprintf("  预估内存消耗: %d KB\n", report.EstMemoryKB))
	}
	sb.WriteString(fmt.Sprintf("  复杂度评分:   %d\n", report.ComplexityScore))

	complexityLevel := "低"
	if report.ComplexityScore > 500 {
		complexityLevel = "极高"
	} else if report.ComplexityScore > 200 {
		complexityLevel = "高"
	} else if report.ComplexityScore > 100 {
		complexityLevel = "中"
	}
	sb.WriteString(fmt.Sprintf("  复杂度等级:   %s\n", complexityLevel))

	if len(report.DirectiveHistogram) > 0 {
		sb.WriteString("\n高频指令 (Top 10):\n")
		topDirectives := getTopDirectives(report.DirectiveHistogram, 10)
		for _, d := range topDirectives {
			sb.WriteString(fmt.Sprintf("  %-25s %d\n", d.Name, d.Count))
		}
	}

	if len(report.Suggestions) > 0 {
		sb.WriteString("\n性能优化建议:\n")
		for i, s := range report.Suggestions {
			sb.WriteString(fmt.Sprintf("  %d. %s\n", i+1, s))
		}
	}

	return sb.String()
}

type directiveFreq struct {
	Name  string
	Count int
}

func getTopDirectives(histogram map[string]int, n int) []directiveFreq {
	all := make([]directiveFreq, 0, len(histogram))
	for name, count := range histogram {
		all = append(all, directiveFreq{Name: name, Count: count})
	}

	for i := 0; i < len(all); i++ {
		for j := i + 1; j < len(all); j++ {
			if all[j].Count > all[i].Count {
				all[i], all[j] = all[j], all[i]
			}
		}
	}

	if len(all) > n {
		all = all[:n]
	}
	return all
}
