package services

import (
	"fmt"
	"math"
	"regexp"
	"strconv"
	"strings"

	"github.com/prometheus/prometheus/promql/parser"
)

var _ = strconv.ParseInt

type PerformanceAnalysis struct {
	RuleID          string            `json:"rule_id"`
	RuleName        string            `json:"rule_name"`
	Complexity      string            `json:"complexity"`      // low, medium, high, critical
	ComplexityScore int               `json:"complexity_score"` // 0-100
	EstimatedLoad   string            `json:"estimated_load"`
	QueryType       string            `json:"query_type"`
	MetricsUsed     []string          `json:"metrics_used"`
	FunctionsUsed   []string          `json:"functions_used"`
	LabelSelectors  []string          `json:"label_selectors"`
	EstimatedCardinality map[string]int64 `json:"estimated_cardinality"` // 每个指标预估的标签基数
	TotalCardinality int64            `json:"total_cardinality"`
	TimeRange       string            `json:"time_range"`
	HasAggregation  bool              `json:"has_aggregation"`
	HasRateFunction bool              `json:"has_rate_function"`
	HasRegex        bool              `json:"has_regex"`
	Recommendations []string          `json:"recommendations"`
	ExecutionPlan   string            `json:"execution_plan"`
}

type RuleDependency struct {
	RuleID          string   `json:"rule_id"`
	RuleName        string   `json:"rule_name"`
	DependsOn       []string `json:"depends_on"`       // 依赖的规则ID列表
	DependedBy      []string `json:"depended_by"`      // 被哪些规则依赖
	SharedMetrics   []string `json:"shared_metrics"`   // 共享的指标
	ChainLikelihood string   `json:"chain_likelihood"` // high, medium, low
	ChainDescription string  `json:"chain_description"`
	TriggerOrder    int      `json:"trigger_order"`    // 触发顺序估计
}

type DependencyAnalysis struct {
	Rules           []RuleDependency `json:"rules"`
	Chains          [][]string       `json:"chains"`            // 可能的告警链
	CriticalChains  [][]string       `json:"critical_chains"`   // 关键告警链（高影响）
	Independent     []string         `json:"independent_rules"` // 独立规则
	HotMetrics      []HotMetric      `json:"hot_metrics"`       // 热点指标（被多个规则使用）
}

type HotMetric struct {
	MetricName      string   `json:"metric_name"`
	RuleCount       int      `json:"rule_count"`
	RelatedRules    []string `json:"related_rules"`
	CardinalityEst  string   `json:"cardinality_estimate"`
}

type RuleTemplate struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Category    string            `json:"category"` // infra, app, database, network, k8s, security
	Description string            `json:"description"`
	Expr        string            `json:"expr"`
	For         string            `json:"for"`
	Severity    string            `json:"severity"`
	Summary     string            `json:"summary"`
	DescriptionTemplate string    `json:"description_template"`
	Labels      map[string]string `json:"labels"`
	Annotations map[string]string `json:"annotations"`
	Tags        []string          `json:"tags"`
	EstimatedComplexity string   `json:"estimated_complexity"`
	UseCases     []string         `json:"use_cases"`
	Contributor  string           `json:"contributor"`
}

type TemplateCategory struct {
	ID          string         `json:"id"`
	Name        string         `json:"name"`
	Description string         `json:"description"`
	Icon        string         `json:"icon"`
	Count       int            `json:"count"`
	Templates   []RuleTemplate `json:"templates"`
}

func AnalyzeRulePerformance(expr string, ruleName string, ruleID string) (*PerformanceAnalysis, error) {
	if _, err := parser.ParseExpr(expr); err != nil {
		return nil, fmt.Errorf("invalid PromQL: %v", err)
	}

	analysis := &PerformanceAnalysis{
		RuleID:             ruleID,
		RuleName:           ruleName,
		EstimatedCardinality: make(map[string]int64),
		Recommendations:    []string{},
	}

	var complexityScore int
	var metrics []string
	var functions []string
	var labelSelectors []string

	parser.Inspect(parser.MustParseExpr(expr), func(node parser.Node, path []parser.Node) error {
		switch n := node.(type) {
		case *parser.VectorSelector:
			metrics = append(metrics, n.Name)
			for _, matcher := range n.LabelMatchers {
				selector := fmt.Sprintf("%s%s%s", matcher.Name, matcher.Type, matcher.Value)
				labelSelectors = append(labelSelectors, selector)

				if matcher.Type == parser.MatchRegexp || matcher.Type == parser.MatchNotRegexp {
					analysis.HasRegex = true
					complexityScore += 15
				}
			}

		case *parser.MatrixSelector:
			vs := n.VectorSelector.(*parser.VectorSelector)
			metrics = append(metrics, vs.Name)
			analysis.TimeRange = n.Range.String()
			complexityScore += 10

		case *parser.AggregateExpr:
			analysis.HasAggregation = true
			complexityScore += 5
			if n.Op == parser.TOPK || n.Op == parser.BOTTOMK {
				complexityScore += 10
			}

		case *parser.Call:
			functions = append(functions, n.Func.Name)
			switch n.Func.Name {
			case "rate", "irate", "increase", "deriv", "delta", "idelta":
				analysis.HasRateFunction = true
				complexityScore += 5
			case "quantile_over_time", "stddev_over_time", "stdvar_over_time":
				complexityScore += 15
			case "predict_linear", "holt_winters":
				complexityScore += 20
			}

		case *parser.BinaryExpr:
			complexityScore += 3
			if n.VectorMatching != nil && len(n.VectorMatching.MatchingLabels) > 0 {
				complexityScore += 5
			}

		case *parser.SubqueryExpr:
			complexityScore += 25
		}
		return nil
	})

	analysis.MetricsUsed = uniqueStrings(metrics)
	analysis.FunctionsUsed = uniqueStrings(functions)
	analysis.LabelSelectors = uniqueStrings(labelSelectors)

	if len(analysis.MetricsUsed) > 1 {
		complexityScore += 10 * (len(analysis.MetricsUsed) - 1)
	}

	totalCardinality := int64(0)
	for _, metric := range analysis.MetricsUsed {
		card := estimateCardinality(metric, analysis.HasRegex, analysis.LabelSelectors)
		analysis.EstimatedCardinality[metric] = card
		totalCardinality += card
	}
	analysis.TotalCardinality = totalCardinality

	if totalCardinality > 100000 {
		complexityScore += 30
	} else if totalCardinality > 10000 {
		complexityScore += 20
	} else if totalCardinality > 1000 {
		complexityScore += 10
	}

	if analysis.HasRateFunction {
		analysis.QueryType = "Range Query"
	} else if analysis.HasAggregation {
		analysis.QueryType = "Aggregation Query"
	} else {
		analysis.QueryType = "Instant Query"
	}

	if complexityScore <= 20 {
		analysis.Complexity = "low"
		analysis.EstimatedLoad = "Low - 适合高频评估"
	} else if complexityScore <= 40 {
		analysis.Complexity = "medium"
		analysis.EstimatedLoad = "Medium - 建议评估间隔 >= 30s"
	} else if complexityScore <= 60 {
		analysis.Complexity = "high"
		analysis.EstimatedLoad = "High - 建议评估间隔 >= 1m"
		analysis.Recommendations = append(analysis.Recommendations, "考虑增加评估间隔，优化标签匹配器")
	} else {
		analysis.Complexity = "critical"
		analysis.EstimatedLoad = "Critical - 建议评估间隔 >= 5m"
		analysis.Recommendations = append(analysis.Recommendations, "高负载查询，强烈建议优化表达式，增加评估间隔")
	}

	if analysis.HasRegex {
		analysis.Recommendations = append(analysis.Recommendations, "使用了正则匹配，考虑使用更具体的标签匹配以提高性能")
	}

	if analysis.TotalCardinality > 10000 {
		analysis.Recommendations = append(analysis.Recommendations,
			fmt.Sprintf("预估处理 %d 个时间序列，考虑添加更多标签筛选器", analysis.TotalCardinality))
	}

	if len(analysis.MetricsUsed) > 2 {
		analysis.Recommendations = append(analysis.Recommendations,
			"查询涉及多个指标，考虑拆分规则以简化调试")
	}

	analysis.ComplexityScore = int(math.Min(float64(complexityScore), 100))

	analysis.ExecutionPlan = buildExecutionPlan(expr, analysis)

	return analysis, nil
}

func AnalyzeRuleDependencies(rules []struct {
	ID   string
	Name string
	Expr string
}) (*DependencyAnalysis, error) {
	ruleMetrics := make(map[string][]string)
	ruleNames := make(map[string]string)
	metricRules := make(map[string][]string)

	for _, rule := range rules {
		metrics := extractMetricsFromExpr(rule.Expr)
		ruleMetrics[rule.ID] = metrics
		ruleNames[rule.ID] = rule.Name

		for _, m := range metrics {
			metricRules[m] = append(metricRules[m], rule.ID)
		}
	}

	analysis := &DependencyAnalysis{
		Rules:       []RuleDependency{},
		Chains:      [][]string{},
		CriticalChains: [][]string{},
		Independent: []string{},
		HotMetrics:  []HotMetric{},
	}

	for metric, ruleList := range metricRules {
		if len(ruleList) >= 2 {
			analysis.HotMetrics = append(analysis.HotMetrics, HotMetric{
				MetricName:     metric,
				RuleCount:      len(ruleList),
				RelatedRules:   ruleList,
				CardinalityEst: estimateCardinalityStr(metric),
			})
		}
	}

	for _, rule := range rules {
		dep := RuleDependency{
			RuleID:          rule.ID,
			RuleName:        rule.Name,
			DependsOn:       []string{},
			DependedBy:      []string{},
			SharedMetrics:   []string{},
			ChainLikelihood: "low",
			TriggerOrder:    0,
		}

		ruleMetricSet := make(map[string]bool)
		for _, m := range ruleMetrics[rule.ID] {
			ruleMetricSet[m] = true
		}

		for _, otherRule := range rules {
			if otherRule.ID == rule.ID {
				continue
			}

			shared := []string{}
			for _, m := range ruleMetrics[otherRule.ID] {
				if ruleMetricSet[m] {
					shared = append(shared, m)
				}
			}

			if len(shared) > 0 {
				if isLikelyDependent(rule.Expr, otherRule.Expr, shared) {
					dep.DependsOn = append(dep.DependsOn, otherRule.ID)
					dep.SharedMetrics = append(dep.SharedMetrics, shared...)
				}
			}
		}

		for _, otherRule := range rules {
			if otherRule.ID == rule.ID {
				continue
			}

			otherMetrics := make(map[string]bool)
			for _, m := range ruleMetrics[otherRule.ID] {
				otherMetrics[m] = true
			}

			shared := []string{}
			for _, m := range ruleMetrics[rule.ID] {
				if otherMetrics[m] {
					shared = append(shared, m)
				}
			}

			if len(shared) > 0 && isLikelyDependent(otherRule.Expr, rule.Expr, shared) {
				dep.DependedBy = append(dep.DependedBy, otherRule.ID)
			}
		}

		if len(dep.DependsOn) > 2 {
			dep.ChainLikelihood = "high"
			dep.ChainDescription = fmt.Sprintf("依赖 %d 个其他规则，可能是告警链的末端", len(dep.DependsOn))
			dep.TriggerOrder = len(dep.DependsOn) + 1
		} else if len(dep.DependsOn) > 0 {
			dep.ChainLikelihood = "medium"
			dep.ChainDescription = fmt.Sprintf("与 %d 个规则相关联", len(dep.DependsOn))
			dep.TriggerOrder = 2
		} else {
			dep.TriggerOrder = 1
		}

		dep.SharedMetrics = uniqueStrings(dep.SharedMetrics)
		analysis.Rules = append(analysis.Rules, dep)

		if len(dep.DependsOn) == 0 && len(dep.DependedBy) == 0 {
			analysis.Independent = append(analysis.Independent, rule.ID)
		}
	}

	analysis.Chains = findChains(analysis.Rules, 3)
	analysis.CriticalChains = findCriticalChains(analysis.Rules, analysis.HotMetrics)

	return analysis, nil
}

func estimateCardinality(metric string, hasRegex bool, selectors []string) int64 {
	baseCardinality := int64(100)

	highCardMetrics := map[string]int64{
		"http_requests_total":      5000,
		"request_duration_seconds": 10000,
		"cpu_usage":                500,
		"memory_usage":             500,
		"disk_usage":               200,
		"network_bytes":            1000,
		"kube_pod_info":            10000,
		"up":                       100,
	}

	for knownMetric, card := range highCardMetrics {
		if strings.Contains(metric, knownMetric) {
			baseCardinality = card
			break
		}
	}

	if hasRegex {
		baseCardinality *= 2
	}

	hasSpecificSelector := false
	for _, sel := range selectors {
		if strings.Contains(sel, "=") && !strings.Contains(sel, "=~") {
			hasSpecificSelector = true
			break
		}
	}
	if !hasSpecificSelector && len(selectors) > 0 {
		baseCardinality *= 3
	}

	return baseCardinality
}

func estimateCardinalityStr(metric string) string {
	card := estimateCardinality(metric, false, nil)
	switch {
	case card > 10000:
		return "High (10k+)"
	case card > 1000:
		return "Medium (1k-10k)"
	default:
		return "Low (<1k)"
	}
}

func extractMetricsFromExpr(expr string) []string {
	var metrics []string
	ast, err := parser.ParseExpr(expr)
	if err != nil {
		return metrics
	}

	parser.Inspect(ast, func(node parser.Node, path []parser.Node) error {
		switch n := node.(type) {
		case *parser.VectorSelector:
			metrics = append(metrics, n.Name)
		case *parser.MatrixSelector:
			if vs, ok := n.VectorSelector.(*parser.VectorSelector); ok {
				metrics = append(metrics, vs.Name)
			}
		}
		return nil
	})

	return uniqueStrings(metrics)
}

func isLikelyDependent(exprA, exprB string, sharedMetrics []string) bool {
	aggFuncs := []string{"sum", "avg", "min", "max", "count", "stddev", "stdvar", "quantile"}
	thresholdsA := extractThreshold(exprA)
	thresholdsB := extractThreshold(exprB)

	isAggregateA := false
	for _, f := range aggFuncs {
		if strings.Contains(exprA, f+"(") || strings.Contains(exprA, f+" ") {
			isAggregateA = true
			break
		}
	}

	isAggregateB := false
	for _, f := range aggFuncs {
		if strings.Contains(exprB, f+"(") || strings.Contains(exprB, f+" ") {
			isAggregateB = true
			break
		}
	}

	if isAggregateA && !isAggregateB {
		return true
	}

	if len(thresholdsA) > 0 && len(thresholdsB) > 0 {
		minA := minThreshold(thresholdsA)
		minB := minThreshold(thresholdsB)
		if minA < minB {
			return true
		}
	}

	for _, m := range sharedMetrics {
		idxA := strings.Index(exprA, m)
		idxB := strings.Index(exprB, m)
		if idxA != -1 && idxB != -1 {
			restA := exprA[idxA+len(m):]
			restB := exprB[idxB+len(m):]
			if len(restA) > len(restB) {
				return true
			}
		}
	}

	return false
}

func extractThreshold(expr string) []float64 {
	var thresholds []float64
	re := regexp.MustCompile(`[><=!]+\s*([0-9.]+)`)
	matches := re.FindAllStringSubmatch(expr, -1)
	for _, match := range matches {
		if f, err := parseFloat(match[1]); err == nil {
			thresholds = append(thresholds, f)
		}
	}
	return thresholds
}

func parseFloat(s string) (float64, error) {
	return strconv.ParseFloat(strings.TrimSpace(s), 64)
}

func minThreshold(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	min := values[0]
	for _, v := range values[1:] {
		if v < min {
			min = v
		}
	}
	return min
}

func buildExecutionPlan(expr string, analysis *PerformanceAnalysis) string {
	var plan []string

	plan = append(plan, fmt.Sprintf("1. 读取指标数据: %v", analysis.MetricsUsed))

	if analysis.TimeRange != "" {
		plan = append(plan, fmt.Sprintf("2. 范围查询时间窗口: %s", analysis.TimeRange))
	}

	if analysis.HasRateFunction {
		plan = append(plan, fmt.Sprintf("3. 应用速率函数: %v", analysis.FunctionsUsed))
	}

	if analysis.HasAggregation {
		plan = append(plan, "4. 执行聚合计算")
	}

	if len(analysis.MetricsUsed) > 1 {
		plan = append(plan, "5. 多指标关联计算")
	}

	plan = append(plan, "6. 应用阈值条件判断")
	plan = append(plan, fmt.Sprintf("7. 预估处理时间序列数: %d", analysis.TotalCardinality))

	return strings.Join(plan, " → ")
}

func findChains(rules []RuleDependency, maxDepth int) [][]string {
	var chains [][]string
	visited := make(map[string]bool)

	var dfs func(string, []string, int)
	dfs = func(ruleID string, path []string, depth int) {
		if depth > maxDepth {
			return
		}

		path = append(path, ruleID)
		visited[ruleID] = true

		rule := findRule(rules, ruleID)
		if rule == nil {
			return
		}

		if len(path) >= 2 {
			chainCopy := make([]string, len(path))
			copy(chainCopy, path)
			chains = append(chains, chainCopy)
		}

		for _, depID := range rule.DependedBy {
			if !visited[depID] {
				dfs(depID, path, depth+1)
			}
		}

		path = path[:len(path)-1]
		visited[ruleID] = false
	}

	for _, rule := range rules {
		if len(rule.DependsOn) == 0 {
			dfs(rule.RuleID, []string{}, 0)
		}
	}

	return chains
}

func findCriticalChains(rules []RuleDependency, hotMetrics []HotMetric) [][]string {
	var critical [][]string
	chains := findChains(rules, 5)

	for _, chain := range chains {
		if len(chain) >= 3 {
			hasHighSeverity := false
			rule := findRule(rules, chain[len(chain)-1])
			if rule != nil && rule.ChainLikelihood == "high" {
				hasHighSeverity = true
			}

			chainMetrics := make(map[string]bool)
			for _, id := range chain {
				r := findRule(rules, id)
				if r != nil {
					for _, m := range r.SharedMetrics {
						chainMetrics[m] = true
					}
				}
			}

			hasHotMetric := false
			for _, hm := range hotMetrics {
				if hm.RuleCount >= 3 && chainMetrics[hm.MetricName] {
					hasHotMetric = true
					break
				}
			}

			if hasHighSeverity || hasHotMetric {
				critical = append(critical, chain)
			}
		}
	}

	return critical
}

func findRule(rules []RuleDependency, id string) *RuleDependency {
	for i := range rules {
		if rules[i].RuleID == id {
			return &rules[i]
		}
	}
	return nil
}

func GetBuiltinTemplates() []TemplateCategory {
	return []TemplateCategory{
		{
			ID:          "infra",
			Name:        "基础设施",
			Description: "服务器、CPU、内存、磁盘、网络等基础监控",
			Icon:        "server",
			Templates: []RuleTemplate{
				{
					ID:          "high-cpu-usage",
					Name:        "CPU 使用率过高",
					Category:    "infra",
					Description: "当 CPU 使用率持续超过阈值时告警",
					Expr:        "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100 > 80",
					For:         "5m",
					Severity:    "warning",
					Summary:     "High CPU usage on {{ $labels.instance }}",
					DescriptionTemplate: "CPU 使用率已超过 80%，当前值为 {{ $value }}%",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "High CPU usage detected",
						"description": "CPU usage is above 80% for 5 minutes",
						"runbook_url": "https://example.com/runbooks/high-cpu",
					},
					Tags:                 []string{"cpu", "performance", "node"},
					EstimatedComplexity:  "medium",
					UseCases:             []string{"服务器资源监控", "性能瓶颈检测"},
					Contributor:          "builtin",
				},
				{
					ID:          "high-memory-usage",
					Name:        "内存使用率过高",
					Category:    "infra",
					Description: "当内存使用率持续超过阈值时告警",
					Expr:        "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90",
					For:         "10m",
					Severity:    "critical",
					Summary:     "High memory usage on {{ $labels.instance }}",
					DescriptionTemplate: "内存使用率已超过 90%，当前值为 {{ $value }}%",
					Labels:      map[string]string{"severity": "critical"},
					Annotations: map[string]string{
						"summary":     "High memory usage detected",
						"description": "Memory usage is above 90% for 10 minutes",
					},
					Tags:                 []string{"memory", "performance", "node"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"服务器资源监控", "OOM 预防"},
					Contributor:          "builtin",
				},
				{
					ID:          "disk-space-low",
					Name:        "磁盘空间不足",
					Category:    "infra",
					Description: "当磁盘可用空间低于阈值时告警",
					Expr:        "(node_filesystem_avail_bytes{fstype!~\"tmpfs|fuse.*\"} / node_filesystem_size_bytes) * 100 < 10",
					For:         "15m",
					Severity:    "critical",
					Summary:     "Disk space low on {{ $labels.instance }}",
					DescriptionTemplate: "磁盘 {{ $labels.mountpoint }} 可用空间不足 10%",
					Labels:      map[string]string{"severity": "critical"},
					Annotations: map[string]string{
						"summary":     "Low disk space",
						"description": "Disk free space is below 10%",
					},
					Tags:                 []string{"disk", "storage", "node"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"存储容量监控", "磁盘满预防"},
					Contributor:          "builtin",
				},
				{
					ID:          "host-down",
					Name:        "主机宕机",
					Category:    "infra",
					Description: "当节点无法访问时告警",
					Expr:        "up{job=\"node\"} == 0",
					For:         "2m",
					Severity:    "critical",
					Summary:     "Instance {{ $labels.instance }} is down",
					DescriptionTemplate: "节点 {{ $labels.instance }} 已经宕机超过 2 分钟",
					Labels:      map[string]string{"severity": "critical"},
					Annotations: map[string]string{
						"summary":     "Host is down",
						"description": "Node exporter is not responding",
					},
					Tags:                 []string{"availability", "node", "uptime"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"可用性监控", "宕机检测"},
					Contributor:          "builtin",
				},
				{
					ID:          "network-errors-high",
					Name:        "网络错误率过高",
					Category:    "infra",
					Description: "当网络接口错误率超过阈值时告警",
					Expr:        "rate(node_network_receive_errs_total[5m]) / rate(node_network_receive_packets_total[5m]) * 100 > 1",
					For:         "5m",
					Severity:    "warning",
					Summary:     "High network errors on {{ $labels.instance }}",
					DescriptionTemplate: "网络接口 {{ $labels.device }} 错误率超过 1%",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "High network error rate",
						"description": "Network error rate is above 1%",
					},
					Tags:                 []string{"network", "errors", "node"},
					EstimatedComplexity:  "medium",
					UseCases:             []string{"网络质量监控"},
					Contributor:          "builtin",
				},
			},
		},
		{
			ID:          "app",
			Name:        "应用服务",
			Description: "HTTP 请求、错误率、响应时间等应用监控",
			Icon:        "appstore",
			Templates: []RuleTemplate{
				{
					ID:          "high-error-rate",
					Name:        "HTTP 错误率过高",
					Category:    "app",
					Description: "当 HTTP 5xx 错误率超过阈值时告警",
					Expr:        "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100 > 5",
					For:         "2m",
					Severity:    "warning",
					Summary:     "High error rate on {{ $labels.service }}",
					DescriptionTemplate: "服务 {{ $labels.service }} 5xx 错误率已超过 5%",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "High HTTP error rate",
						"description": "5xx error rate is above 5% for 2 minutes",
					},
					Tags:                 []string{"http", "errors", "application"},
					EstimatedComplexity:  "medium",
					UseCases:             []string{"应用可用性监控", "错误率监控"},
					Contributor:          "builtin",
				},
				{
					ID:          "slow-response-time",
					Name:        "响应时间过长",
					Category:    "app",
					Description: "当 HTTP 平均响应时间超过阈值时告警",
					Expr:        "rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m]) > 1",
					For:         "3m",
					Severity:    "warning",
					Summary:     "Slow response time on {{ $labels.service }}",
					DescriptionTemplate: "服务 {{ $labels.service }} 平均响应时间超过 1 秒",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "Slow HTTP response time",
						"description": "Average response time is above 1 second",
					},
					Tags:                 []string{"http", "latency", "performance"},
					EstimatedComplexity:  "medium",
					UseCases:             []string{"应用性能监控", "用户体验监控"},
					Contributor:          "builtin",
				},
				{
					ID:          "high-request-rate",
					Name:        "请求率异常",
					Category:    "app",
					Description: "当请求率异常增高或降低时告警",
					Expr:        "abs(rate(http_requests_total[5m]) - avg_over_time(rate(http_requests_total[5m])[1h:])) > 2 * stddev_over_time(rate(http_requests_total[5m])[1h:])",
					For:         "10m",
					Severity:    "warning",
					Summary:     "Abnormal request rate on {{ $labels.service }}",
					DescriptionTemplate: "服务 {{ $labels.service }} 请求率异常",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "Abnormal request rate",
						"description": "Request rate deviates from normal pattern",
					},
					Tags:                 []string{"http", "anomaly", "traffic"},
					EstimatedComplexity:  "high",
					UseCases:             []string{"流量异常检测", "DDoS 检测"},
					Contributor:          "builtin",
				},
				{
					ID:          "service-down",
					Name:        "服务不可用",
					Category:    "app",
					Description: "当服务探针检测失败时告警",
					Expr:        "probe_success == 0",
					For:         "1m",
					Severity:    "critical",
					Summary:     "Service {{ $labels.job }} is down",
					DescriptionTemplate: "服务 {{ $labels.job }} ({{ $labels.instance }}) 探针失败",
					Labels:      map[string]string{"severity": "critical"},
					Annotations: map[string]string{
						"summary":     "Service is down",
						"description": "Blackbox probe failed",
					},
					Tags:                 []string{"availability", "service", "probe"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"服务可用性监控", "健康检查"},
					Contributor:          "builtin",
				},
			},
		},
		{
			ID:          "database",
			Name:        "数据库",
			Description: "MySQL、PostgreSQL、Redis 等数据库监控",
			Icon:        "database",
			Templates: []RuleTemplate{
				{
					ID:          "db-connections-high",
					Name:        "数据库连接数过高",
					Category:    "database",
					Description: "当数据库连接数接近上限时告警",
					Expr:        "pg_stat_database_numbackends / pg_settings_max_connections * 100 > 80",
					For:         "5m",
					Severity:    "warning",
					Summary:     "High database connections on {{ $labels.instance }}",
					DescriptionTemplate: "数据库连接数已超过 80%",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "High DB connections",
						"description": "Database connection usage is above 80%",
					},
					Tags:                 []string{"database", "connections", "postgresql"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"数据库性能监控", "连接池监控"},
					Contributor:          "builtin",
				},
				{
					ID:          "db-slow-queries",
					Name:        "慢查询过多",
					Category:    "database",
					Description: "当慢查询速率超过阈值时告警",
					Expr:        "rate(mysql_slow_queries_total[5m]) > 10",
					For:         "5m",
					Severity:    "warning",
					Summary:     "High slow query rate on {{ $labels.instance }}",
					DescriptionTemplate: "MySQL 慢查询速率超过 10/s",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "High slow query rate",
						"description": "More than 10 slow queries per second",
					},
					Tags:                 []string{"database", "performance", "mysql"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"数据库性能优化"},
					Contributor:          "builtin",
				},
				{
					ID:          "redis-memory-high",
					Name:        "Redis 内存使用率过高",
					Category:    "database",
					Description: "当 Redis 内存使用率超过 maxmemory 时告警",
					Expr:        "redis_memory_used_bytes / redis_memory_max_bytes * 100 > 95",
					For:         "5m",
					Severity:    "warning",
					Summary:     "High Redis memory usage on {{ $labels.instance }}",
					DescriptionTemplate: "Redis 内存使用已超过 maxmemory 的 95%",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "High Redis memory usage",
						"description": "Redis memory is above 95% of maxmemory",
					},
					Tags:                 []string{"redis", "memory", "database"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"Redis 监控", "内存管理"},
					Contributor:          "builtin",
				},
			},
		},
		{
			ID:          "k8s",
			Name:        "Kubernetes",
			Description: "K8s 集群、Pod、Deployment 等监控",
			Icon:        "cloud-server",
			Templates: []RuleTemplate{
				{
					ID:          "k8s-pod-restarting",
					Name:        "Pod 频繁重启",
					Category:    "k8s",
					Description: "当 Pod 重启频率超过阈值时告警",
					Expr:        "increase(kube_pod_container_status_restarts_total[1h]) > 5",
					For:         "10m",
					Severity:    "warning",
					Summary:     "Pod {{ $labels.pod }} is restarting frequently",
					DescriptionTemplate: "Pod {{ $labels.pod }} 在 1 小时内重启超过 5 次",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "Frequent pod restarts",
						"description": "Pod has restarted more than 5 times in 1 hour",
					},
					Tags:                 []string{"kubernetes", "pod", "restart"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"K8s 工作负载监控", "故障检测"},
					Contributor:          "builtin",
				},
				{
					ID:          "k8s-pod-not-ready",
					Name:        "Pod 未就绪",
					Category:    "k8s",
					Description: "当 Pod 长时间未就绪时告警",
					Expr:        "kube_pod_status_ready{condition=\"true\"} == 0",
					For:         "5m",
					Severity:    "warning",
					Summary:     "Pod {{ $labels.pod }} is not ready",
					DescriptionTemplate: "Pod {{ $labels.pod }} 超过 5 分钟未就绪",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "Pod not ready",
						"description": "Pod has been in non-ready state for 5 minutes",
					},
					Tags:                 []string{"kubernetes", "pod", "readiness"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"K8s 工作负载监控"},
					Contributor:          "builtin",
				},
				{
					ID:          "k8s-deployment-replicas",
					Name:        "Deployment 副本不足",
					Category:    "k8s",
					Description: "当 Deployment 可用副本数少于期望时告警",
					Expr:        "kube_deployment_status_replicas_available < kube_deployment_spec_replicas",
					For:         "5m",
					Severity:    "warning",
					Summary:     "Deployment {{ $labels.deployment }} has unavailable replicas",
					DescriptionTemplate: "Deployment {{ $labels.deployment }} 可用副本数少于期望数",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "Unavailable deployment replicas",
						"description": "Available replicas is less than desired",
					},
					Tags:                 []string{"kubernetes", "deployment", "replicas"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"K8s 工作负载监控", "高可用保障"},
					Contributor:          "builtin",
				},
				{
					ID:          "k8s-node-not-ready",
					Name:        "K8s 节点未就绪",
					Category:    "k8s",
					Description: "当 K8s 节点未就绪时告警",
					Expr:        "kube_node_status_condition{condition=\"Ready\",status=\"true\"} == 0",
					For:         "2m",
					Severity:    "critical",
					Summary:     "Node {{ $labels.node }} is not ready",
					DescriptionTemplate: "K8s 节点 {{ $labels.node }} 未就绪",
					Labels:      map[string]string{"severity": "critical"},
					Annotations: map[string]string{
						"summary":     "K8s node not ready",
						"description": "Node has been in not-ready state for 2 minutes",
					},
					Tags:                 []string{"kubernetes", "node", "readiness"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"K8s 基础设施监控"},
					Contributor:          "builtin",
				},
			},
		},
		{
			ID:          "network",
			Name:        "网络安全",
			Description: "SSL 证书、域名、端口等监控",
			Icon:        "safety",
			Templates: []RuleTemplate{
				{
					ID:          "ssl-cert-expiring",
					Name:        "SSL 证书即将过期",
					Category:    "network",
					Description: "当 SSL 证书有效期不足时告警",
					Expr:        "probe_ssl_earliest_cert_expiry - time() < 86400 * 7",
					For:         "1h",
					Severity:    "warning",
					Summary:     "SSL certificate for {{ $labels.instance }} expiring soon",
					DescriptionTemplate: "SSL 证书将在 7 天内过期",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "SSL certificate expiring soon",
						"description": "Certificate expires in less than 7 days",
					},
					Tags:                 []string{"ssl", "certificate", "security"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"证书监控", "安全运维"},
					Contributor:          "builtin",
				},
				{
					ID:          "domain-expiring",
					Name:        "域名即将过期",
					Category:    "network",
					Description: "当域名有效期不足时告警",
					Expr:        "domain_expiry_days < 30",
					For:         "1h",
					Severity:    "warning",
					Summary:     "Domain {{ $labels.domain }} expiring soon",
					DescriptionTemplate: "域名将在 30 天内过期",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "Domain expiring soon",
						"description": "Domain expires in less than 30 days",
					},
					Tags:                 []string{"domain", "security"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"域名监控", "资产管理"},
					Contributor:          "builtin",
				},
			},
		},
		{
			ID:          "security",
			Name:        "安全监控",
			Description: "安全相关的告警规则",
			Icon:        "shield",
			Templates: []RuleTemplate{
				{
					ID:          "ssh-brute-force",
					Name:        "SSH 暴力破解尝试",
					Category:    "security",
					Description: "当检测到大量 SSH 登录失败时告警",
					Expr:        "rate(node_ssh_login_failures_total[5m]) > 10",
					For:         "5m",
					Severity:    "critical",
					Summary:     "Possible SSH brute force on {{ $labels.instance }}",
					DescriptionTemplate: "检测到可能的 SSH 暴力破解尝试",
					Labels:      map[string]string{"severity": "critical"},
					Annotations: map[string]string{
						"summary":     "Possible SSH brute force attack",
						"description": "More than 10 SSH login failures per second",
					},
					Tags:                 []string{"security", "ssh", "intrusion"},
					EstimatedComplexity:  "low",
					UseCases:             []string{"安全监控", "入侵检测"},
					Contributor:          "builtin",
				},
				{
					ID:          "unusual-traffic-spike",
					Name:        "异常流量峰值",
					Category:    "security",
					Description: "当网络流量异常增高时告警（可能 DDoS）",
					Expr:        "rate(node_network_receive_bytes_total[2m]) > 3 * avg_over_time(rate(node_network_receive_bytes_total[2m])[1d:])",
					For:         "5m",
					Severity:    "warning",
					Summary:     "Unusual traffic spike on {{ $labels.instance }}",
					DescriptionTemplate: "入站流量异常，可能是 DDoS 攻击",
					Labels:      map[string]string{"severity": "warning"},
					Annotations: map[string]string{
						"summary":     "Unusual traffic spike detected",
						"description": "Inbound traffic is 3x higher than average",
					},
					Tags:                 []string{"security", "network", "ddos"},
					EstimatedComplexity:  "high",
					UseCases:             []string{"安全监控", "DDoS 检测"},
					Contributor:          "builtin",
				},
			},
		},
	}
}
