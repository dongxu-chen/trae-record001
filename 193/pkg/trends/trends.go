package trends

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"k8s-auditor/pkg/audit"
)

type AuditHistory struct {
	Timestamp      time.Time         `json:"timestamp"`
	TotalResources int               `json:"total_resources"`
	ViolationCount int               `json:"violation_count"`
	ComplianceRate float64           `json:"compliance_rate"`
	ViolationTypes map[string]int    `json:"violation_types"`
}

type TrendAnalysis struct {
	History         []AuditHistory `json:"history"`
	ComplianceTrend string         `json:"compliance_trend"`
	AvgCompliance   float64        `json:"avg_compliance"`
	TopViolations   []ViolationStat `json:"top_violations"`
}

type ViolationStat struct {
	RuleType string `json:"rule_type"`
	Count    int    `json:"count"`
	Percent  float64 `json:"percent"`
}

type TrendAnalyzer struct {
	historyFile string
	maxHistory  int
}

func New(outputDir string) *TrendAnalyzer {
	historyFile := filepath.Join(outputDir, "audit-history.json")
	return &TrendAnalyzer{
		historyFile: historyFile,
		maxHistory:  30,
	}
}

func (ta *TrendAnalyzer) Record(report *audit.AuditReport) error {
	history, err := ta.loadHistory()
	if err != nil {
		history = make([]AuditHistory, 0)
	}

	violationTypes := make(map[string]int)
	for _, v := range report.Violations {
		violationTypes[v.RuleType]++
	}

	complianceRate := 0.0
	if report.TotalResources > 0 {
		compliantResources := report.TotalResources
		if len(report.Violations) > 0 {
			violatingResources := make(map[string]bool)
			for _, v := range report.Violations {
				key := fmt.Sprintf("%s/%s/%s", v.ResourceType, v.Namespace, v.ResourceName)
				violatingResources[key] = true
			}
			compliantResources = report.TotalResources - len(violatingResources)
		}
		complianceRate = float64(compliantResources) / float64(report.TotalResources) * 100
	}

	entry := AuditHistory{
		Timestamp:      report.Timestamp,
		TotalResources: report.TotalResources,
		ViolationCount: len(report.Violations),
		ComplianceRate: complianceRate,
		ViolationTypes: violationTypes,
	}

	history = append(history, entry)

	if len(history) > ta.maxHistory {
		history = history[len(history)-ta.maxHistory:]
	}

	return ta.saveHistory(history)
}

func (ta *TrendAnalyzer) Analyze() (*TrendAnalysis, error) {
	history, err := ta.loadHistory()
	if err != nil {
		return nil, err
	}

	if len(history) == 0 {
		return &TrendAnalysis{
			History:         make([]AuditHistory, 0),
			ComplianceTrend: "insufficient_data",
			AvgCompliance:   0,
			TopViolations:   make([]ViolationStat, 0),
		}, nil
	}

	avgCompliance := 0.0
	for _, h := range history {
		avgCompliance += h.ComplianceRate
	}
	avgCompliance /= float64(len(history))

	trend := "stable"
	if len(history) >= 2 {
		recent := history[len(history)-1].ComplianceRate
		previous := history[len(history)-2].ComplianceRate
		if recent > previous+1 {
			trend = "improving"
		} else if recent < previous-1 {
			trend = "declining"
		}
	}

	violationCounts := make(map[string]int)
	totalViolations := 0
	for _, h := range history {
		for ruleType, count := range h.ViolationTypes {
			violationCounts[ruleType] += count
			totalViolations += count
		}
	}

	topViolations := make([]ViolationStat, 0, len(violationCounts))
	for ruleType, count := range violationCounts {
		percent := 0.0
		if totalViolations > 0 {
			percent = float64(count) / float64(totalViolations) * 100
		}
		topViolations = append(topViolations, ViolationStat{
			RuleType: ruleType,
			Count:    count,
			Percent:  percent,
		})
	}

	sort.Slice(topViolations, func(i, j int) bool {
		return topViolations[i].Count > topViolations[j].Count
	})

	if len(topViolations) > 10 {
		topViolations = topViolations[:10]
	}

	return &TrendAnalysis{
		History:         history,
		ComplianceTrend: trend,
		AvgCompliance:   avgCompliance,
		TopViolations:   topViolations,
	}, nil
}

func (ta *TrendAnalyzer) GenerateReport(analysis *TrendAnalysis) string {
	if len(analysis.History) == 0 {
		return "暂无历史审计数据，无法进行趋势分析\n"
	}

	var report string
	report += "========================================\n"
	report += "  审计趋势分析报告\n"
	report += "========================================\n\n"

	report += fmt.Sprintf("历史记录数: %d\n", len(analysis.History))
	report += fmt.Sprintf("平均合规率: %.2f%%\n", analysis.AvgCompliance)
	report += fmt.Sprintf("趋势状态: %s\n\n", getTrendEmoji(analysis.ComplianceTrend)+" "+getTrendText(analysis.ComplianceTrend))

	report += "----------------------------------------\n"
	report += "  合规率趋势\n"
	report += "----------------------------------------\n\n"

	if len(analysis.History) > 0 {
		report += fmt.Sprintf("最近一次合规率: %.2f%%\n", analysis.History[len(analysis.History)-1].ComplianceRate)
		if len(analysis.History) >= 2 {
			prev := analysis.History[len(analysis.History)-2].ComplianceRate
			curr := analysis.History[len(analysis.History)-1].ComplianceRate
			diff := curr - prev
			sign := "+"
			if diff < 0 {
				sign = ""
			}
			report += fmt.Sprintf("较上一次变化: %s%.2f%%\n", sign, diff)
		}
	}

	report += "\n合规率历史 (最近10次):\n"
	startIdx := 0
	if len(analysis.History) > 10 {
		startIdx = len(analysis.History) - 10
	}
	for i := startIdx; i < len(analysis.History); i++ {
		h := analysis.History[i]
		bar := generateBar(h.ComplianceRate, 50)
		report += fmt.Sprintf("  %s  %5.1f%%  %s\n",
			h.Timestamp.Format("01-02 15:04"),
			h.ComplianceRate,
			bar)
	}

	report += "\n----------------------------------------\n"
	report += "  TOP 10 违规类型统计\n"
	report += "----------------------------------------\n\n"

	if len(analysis.TopViolations) == 0 {
		report += "  无违规记录\n"
	} else {
		for i, v := range analysis.TopViolations {
			bar := generateBar(v.Percent, 30)
			report += fmt.Sprintf("  %2d. %-30s %5d次 (%.1f%%)  %s\n",
				i+1, v.RuleType, v.Count, v.Percent, bar)
		}
	}

	return report
}

func (ta *TrendAnalyzer) loadHistory() ([]AuditHistory, error) {
	data, err := os.ReadFile(ta.historyFile)
	if err != nil {
		if os.IsNotExist(err) {
			return make([]AuditHistory, 0), nil
		}
		return nil, err
	}

	var history []AuditHistory
	if err := json.Unmarshal(data, &history); err != nil {
		return nil, err
	}

	return history, nil
}

func (ta *TrendAnalyzer) saveHistory(history []AuditHistory) error {
	dir := filepath.Dir(ta.historyFile)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	data, err := json.MarshalIndent(history, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(ta.historyFile, data, 0644)
}

func generateBar(percent float64, width int) string {
	filled := int(percent / 100 * float64(width))
	if filled > width {
		filled = width
	}
	bar := ""
	for i := 0; i < filled; i++ {
		bar += "█"
	}
	for i := filled; i < width; i++ {
		bar += "░"
	}
	return bar
}

func getTrendEmoji(trend string) string {
	switch trend {
	case "improving":
		return "📈"
	case "declining":
		return "📉"
	case "stable":
		return "➡️"
	default:
		return "❓"
	}
}

func getTrendText(trend string) string {
	switch trend {
	case "improving":
		return "持续改善"
	case "declining":
		return "有所下降"
	case "stable":
		return "保持稳定"
	default:
		return "数据不足"
	}
}
