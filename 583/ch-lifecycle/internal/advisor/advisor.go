package advisor

import (
	"context"
	"fmt"
	"math"
	"sort"
	"strings"
	"time"

	ch "ch-lifecycle/internal/clickhouse"
	"go.uber.org/zap"
)

type Advisor struct {
	client *ch.Client
	logger *zap.Logger
}

func NewAdvisor(client *ch.Client, logger *zap.Logger) *Advisor {
	return &Advisor{client: client, logger: logger}
}

type OptimizationSuggestion struct {
	Database    string  `json:"database"`
	Table       string  `json:"table"`
	Partition   string  `json:"partition,omitempty"`
	Type        string  `json:"type"`
	Severity    string  `json:"severity"`
	Description string  `json:"description"`
	Action      string  `json:"action"`
	Impact      string  `json:"impact"`
}

type PartitionGranularity string

const (
	GranularityDaily   PartitionGranularity = "daily"
	GranularityMonthly PartitionGranularity = "monthly"
	GranularityYearly  PartitionGranularity = "yearly"
)

type PartitionPattern struct {
	Granularity   PartitionGranularity `json:"granularity"`
	Count         int                  `json:"count"`
	AvgSizeBytes  uint64               `json:"avg_size_bytes"`
	AvgRows       uint64               `json:"avg_rows"`
	TimeSpanDays  int                  `json:"time_span_days"`
	Confidence    float64              `json:"confidence"`
}

type RecommendedGranularity struct {
	Current       PartitionGranularity  `json:"current"`
	Recommended   PartitionGranularity  `json:"recommended"`
	Reason        string                `json:"reason"`
	EstimatedPartCount int              `json:"estimated_part_count"`
	SqlTemplate   string                `json:"sql_template"`
}

type TableAnalysis struct {
	Database         string                    `json:"database"`
	Table            string                    `json:"table"`
	Engine           string                    `json:"engine"`
	TotalRows        uint64                    `json:"total_rows"`
	TotalBytes       uint64                    `json:"total_bytes"`
	PartitionCount   int                       `json:"partition_count"`
	AvgPartitionSize uint64                    `json:"avg_partition_size"`
	SkewRatio        float64                   `json:"skew_ratio"`
	Fragmentation    float64                   `json:"fragmentation"`
	Suggestions      []OptimizationSuggestion  `json:"suggestions"`
	Pattern          *PartitionPattern         `json:"pattern,omitempty"`
	GranularityRec   *RecommendedGranularity   `json:"granularity_recommendation,omitempty"`
}

func (a *Advisor) AnalyzeTable(ctx context.Context, database, table string) (*TableAnalysis, error) {
	tables, err := a.client.GetTables(ctx, database)
	if err != nil {
		return nil, fmt.Errorf("get table info: %w", err)
	}
	var tableInfo *ch.TableInfo
	for _, t := range tables {
		if t.Name == table {
			tableInfo = &t
			break
		}
	}
	if tableInfo == nil {
		return nil, fmt.Errorf("table %s.%s not found", database, table)
	}
	partitions, err := a.client.GetPartitions(ctx, database, table)
	if err != nil {
		return nil, fmt.Errorf("get partitions: %w", err)
	}
	analysis := &TableAnalysis{
		Database:       database,
		Table:          table,
		Engine:         tableInfo.Engine,
		TotalRows:      tableInfo.TotalRows,
		TotalBytes:     tableInfo.TotalBytes,
		PartitionCount: len(partitions),
	}
	if len(partitions) > 0 {
		var totalPartSize uint64
		var maxSize uint64
		var minSize uint64 = math.MaxUint64
		var totalRows uint64
		for _, p := range partitions {
			totalPartSize += p.BytesOnDisk
			totalRows += p.Rows
			if p.BytesOnDisk > maxSize {
				maxSize = p.BytesOnDisk
			}
			if p.BytesOnDisk < minSize {
				minSize = p.BytesOnDisk
			}
		}
		analysis.AvgPartitionSize = totalPartSize / uint64(len(partitions))
		if minSize > 0 {
			analysis.SkewRatio = float64(maxSize) / float64(minSize)
		}
		var totalParts int
		for _, p := range partitions {
			totalParts += int(p.Level + 1)
		}
		analysis.Fragmentation = float64(totalParts) / float64(len(partitions))
		pattern := a.detectPartitionPattern(partitions)
		if pattern != nil {
			analysis.Pattern = pattern
			rec := a.recommendGranularity(pattern, analysis, tableInfo)
			if rec != nil {
				analysis.GranularityRec = rec
			}
		}
	}
	analysis.Suggestions = a.generateSuggestions(analysis, partitions)
	return analysis, nil
}

func (a *Advisor) detectPartitionPattern(partitions []ch.PartitionInfo) *PartitionPattern {
	if len(partitions) == 0 {
		return nil
	}

	var dailyCount, monthlyCount, yearlyCount int
	var dailySizeSum, monthlySizeSum, yearlySizeSum uint64
	var dailyRowSum, monthlyRowSum, yearlyRowSum uint64

	dailyPartitions := make(map[string][]ch.PartitionInfo)
	monthlyPartitions := make(map[string][]ch.PartitionInfo)
	yearlyPartitions := make(map[string][]ch.PartitionInfo)

	for _, p := range partitions {
		partID := p.Partition

		if looksLikeDateFormat(partID, "20060102") {
			dailyCount++
			dailySizeSum += p.BytesOnDisk
			dailyRowSum += p.Rows
			monthKey := partID[:6]
			yearKey := partID[:4]
			dailyPartitions[monthKey] = append(dailyPartitions[monthKey], p)
			monthlyPartitions[monthKey] = append(monthlyPartitions[monthKey], p)
			yearlyPartitions[yearKey] = append(yearlyPartitions[yearKey], p)
		} else if looksLikeDateFormat(partID, "200601") || looksLikeDateFormat(partID, "2006-01") {
			monthlyCount++
			monthlySizeSum += p.BytesOnDisk
			monthlyRowSum += p.Rows
			yearKey := partID[:4]
			monthlyPartitions[partID] = append(monthlyPartitions[partID], p)
			yearlyPartitions[yearKey] = append(yearlyPartitions[yearKey], p)
		} else if looksLikeDateFormat(partID, "2006") {
			yearlyCount++
			yearlySizeSum += p.BytesOnDisk
			yearlyRowSum += p.Rows
			yearlyPartitions[partID] = append(yearlyPartitions[partID], p)
		} else {
			if len(partID) == 8 && allDigits(partID) {
				dailyCount++
				dailySizeSum += p.BytesOnDisk
				dailyRowSum += p.Rows
				monthKey := partID[:6]
				yearKey := partID[:4]
				dailyPartitions[monthKey] = append(dailyPartitions[monthKey], p)
				monthlyPartitions[monthKey] = append(monthlyPartitions[monthKey], p)
				yearlyPartitions[yearKey] = append(yearlyPartitions[yearKey], p)
			} else if len(partID) == 6 && allDigits(partID) {
				monthlyCount++
				monthlySizeSum += p.BytesOnDisk
				monthlyRowSum += p.Rows
				yearKey := partID[:4]
				monthlyPartitions[partID] = append(monthlyPartitions[partID], p)
				yearlyPartitions[yearKey] = append(yearlyPartitions[yearKey], p)
			} else if len(partID) == 4 && allDigits(partID) {
				yearlyCount++
				yearlySizeSum += p.BytesOnDisk
				yearlyRowSum += p.Rows
				yearlyPartitions[partID] = append(yearlyPartitions[partID], p)
			}
		}
	}

	total := len(partitions)

	if dailyCount > total/2 {
		var avgDailySize uint64
		var avgDailyRows uint64
		if dailyCount > 0 {
			avgDailySize = dailySizeSum / uint64(dailyCount)
			avgDailyRows = dailyRowSum / uint64(dailyCount)
		}
		spanDays := estimateTimeSpan(partitions)
		confidence := float64(dailyCount) / float64(total)
		return &PartitionPattern{
			Granularity:  GranularityDaily,
			Count:        dailyCount,
			AvgSizeBytes: avgDailySize,
			AvgRows:      avgDailyRows,
			TimeSpanDays: spanDays,
			Confidence:   confidence,
		}
	}

	if monthlyCount > total/2 {
		var avgMonthlySize uint64
		var avgMonthlyRows uint64
		if monthlyCount > 0 {
			avgMonthlySize = monthlySizeSum / uint64(monthlyCount)
			avgMonthlyRows = monthlyRowSum / uint64(monthlyCount)
		}
		spanDays := estimateTimeSpan(partitions)
		confidence := float64(monthlyCount) / float64(total)
		return &PartitionPattern{
			Granularity:  GranularityMonthly,
			Count:        monthlyCount,
			AvgSizeBytes: avgMonthlySize,
			AvgRows:      avgMonthlyRows,
			TimeSpanDays: spanDays,
			Confidence:   confidence,
		}
	}

	if yearlyCount > total/2 {
		var avgYearlySize uint64
		var avgYearlyRows uint64
		if yearlyCount > 0 {
			avgYearlySize = yearlySizeSum / uint64(yearlyCount)
			avgYearlyRows = yearlyRowSum / uint64(yearlyCount)
		}
		spanDays := estimateTimeSpan(partitions)
		confidence := float64(yearlyCount) / float64(total)
		return &PartitionPattern{
			Granularity:  GranularityYearly,
			Count:        yearlyCount,
			AvgSizeBytes: avgYearlySize,
			AvgRows:      avgYearlyRows,
			TimeSpanDays: spanDays,
			Confidence:   confidence,
		}
	}

	spanDays := estimateTimeSpan(partitions)
	return &PartitionPattern{
		Granularity:  GranularityDaily,
		Count:        total,
		AvgSizeBytes: 0,
		AvgRows:      0,
		TimeSpanDays: spanDays,
		Confidence:   0.3,
	}
}

func (a *Advisor) recommendGranularity(pattern *PartitionPattern, analysis *TableAnalysis, tableInfo *ch.TableInfo) *RecommendedGranularity {
	current := pattern.Granularity
	var recommended PartitionGranularity
	var reason string
	var estimatedParts int
	var sqlTmpl string

	avgSize := pattern.AvgSizeBytes
	spanDays := pattern.TimeSpanDays

	if spanDays <= 0 {
		spanDays = 365
	}

	switch current {
	case GranularityDaily:
		if avgSize < 10*1024*1024 && spanDays > 180 {
			recommended = GranularityMonthly
			reason = fmt.Sprintf("日均分区仅 %s，跨度 %d 天，按月聚合可减少 %d→%d 分区，降低元数据开销",
				formatBytes(avgSize), spanDays, pattern.Count, max(1, spanDays/30))
			estimatedParts = max(1, spanDays/30)
			sqlTmpl = fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYYMM(date_column)", tableInfo.Database, tableInfo.Name)
		} else if avgSize < 1024*1024 && spanDays > 365 {
			recommended = GranularityYearly
			reason = fmt.Sprintf("日均分区极小 (%s)，跨度 %d 天，按年聚合大幅降低分区数量",
				formatBytes(avgSize), spanDays)
			estimatedParts = max(1, spanDays/365)
			sqlTmpl = fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYY(date_column)", tableInfo.Database, tableInfo.Name)
		} else if pattern.Count > 1000 {
			recommended = GranularityMonthly
			reason = fmt.Sprintf("日分区数量 %d 超过 1000 上限，按月聚合可降至 ~%d",
				pattern.Count, max(1, spanDays/30))
			estimatedParts = max(1, spanDays/30)
			sqlTmpl = fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYYMM(date_column)", tableInfo.Database, tableInfo.Name)
		} else {
			return nil
		}

	case GranularityMonthly:
		if avgSize > 50*1024*1024*1024 && spanDays > 365 {
			recommended = GranularityDaily
			reason = fmt.Sprintf("月分区达 %s，查询延迟高，按天拆分可提升查询和TTL粒度",
				formatBytes(avgSize))
			estimatedParts = min(spanDays, 365)
			sqlTmpl = fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYYMMDD(date_column)", tableInfo.Database, tableInfo.Name)
		} else if avgSize < 1024*1024 && spanDays > 365*3 {
			recommended = GranularityYearly
			reason = fmt.Sprintf("月均分区仅 %s，跨度 %d 天，按年聚合更高效",
				formatBytes(avgSize), spanDays)
			estimatedParts = max(1, spanDays/365)
			sqlTmpl = fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYY(date_column)", tableInfo.Database, tableInfo.Name)
		} else if pattern.Count > 500 {
			recommended = GranularityYearly
			reason = fmt.Sprintf("月分区数量 %d 过多，按年聚合降至 ~%d",
				pattern.Count, max(1, spanDays/365))
			estimatedParts = max(1, spanDays/365)
			sqlTmpl = fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYY(date_column)", tableInfo.Database, tableInfo.Name)
		} else {
			return nil
		}

	case GranularityYearly:
		if avgSize > 100*1024*1024*1024*1024 {
			recommended = GranularityMonthly
			reason = fmt.Sprintf("年分区达 %s，管理粒度过粗，按月拆分可提升TTL精度",
				formatBytes(avgSize))
			estimatedParts = min(spanDays/30, 120)
			sqlTmpl = fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYYMM(date_column)", tableInfo.Database, tableInfo.Name)
		} else {
			return nil
		}
	}

	return &RecommendedGranularity{
		Current:            current,
		Recommended:        recommended,
		Reason:             reason,
		EstimatedPartCount: estimatedParts,
		SqlTemplate:        sqlTmpl,
	}
}

func (a *Advisor) AnalyzeDatabase(ctx context.Context, database string) ([]*TableAnalysis, error) {
	tables, err := a.client.GetTables(ctx, database)
	if err != nil {
		return nil, err
	}
	var analyses []*TableAnalysis
	for _, t := range tables {
		analysis, err := a.AnalyzeTable(ctx, database, t.Name)
		if err != nil {
			a.logger.Warn("failed to analyze table",
				zap.String("table", t.Name),
				zap.Error(err),
			)
			continue
		}
		analyses = append(analyses, analysis)
	}
	return analyses, nil
}

func (a *Advisor) generateSuggestions(analysis *TableAnalysis, partitions []ch.PartitionInfo) []OptimizationSuggestion {
	var suggestions []OptimizationSuggestion

	if analysis.GranularityRec != nil {
		rec := analysis.GranularityRec
		severity := "medium"
		if rec.Current == GranularityDaily && rec.Recommended == GranularityMonthly && analysis.PartitionCount > 1000 {
			severity = "high"
		}
		suggestions = append(suggestions, OptimizationSuggestion{
			Database:    analysis.Database,
			Table:       analysis.Table,
			Type:        "granularity_" + string(rec.Recommended),
			Severity:    severity,
			Description: rec.Reason,
			Action:      fmt.Sprintf("从 %s 粒度调整为 %s 粒度分区", granularityLabel(rec.Current), granularityLabel(rec.Recommended)),
			Impact:      fmt.Sprintf("预计分区数量从 %d 降至 ~%d", analysis.PartitionCount, rec.EstimatedPartCount),
		})
	}

	if analysis.PartitionCount > 1000 {
		suggestions = append(suggestions, OptimizationSuggestion{
			Database:    analysis.Database,
			Table:       analysis.Table,
			Type:        "partition_count",
			Severity:    "high",
			Description: fmt.Sprintf("表有 %d 个分区，超过 1000 上限", analysis.PartitionCount),
			Action:      "考虑使用更粗的分区键或合并分区",
			Impact:      "高分区数量降低查询规划效率，增加后台开销",
		})
	}

	if analysis.SkewRatio > 10 {
		suggestions = append(suggestions, OptimizationSuggestion{
			Database:    analysis.Database,
			Table:       analysis.Table,
			Type:        "partition_skew",
			Severity:    "medium",
			Description: fmt.Sprintf("分区大小倾斜比 %.1f (max/min)，数据分布不均", analysis.SkewRatio),
			Action:      "审查分区键确保均匀分布；考虑重新分区",
			Impact:      "不均匀分区导致查询性能热点和资源争用",
		})
	}

	if analysis.Fragmentation > 3.0 {
		suggestions = append(suggestions, OptimizationSuggestion{
			Database:    analysis.Database,
			Table:       analysis.Table,
			Type:        "fragmentation",
			Severity:    "high",
			Description: fmt.Sprintf("碎片率 %.1f 过高（每分区多小 part）", analysis.Fragmentation),
			Action:      "执行 OPTIMIZE TABLE 合并小 part",
			Impact:      "碎片化降低查询速度，浪费磁盘空间",
		})
	}

	sortedParts := make([]ch.PartitionInfo, len(partitions))
	copy(sortedParts, partitions)
	sort.Slice(sortedParts, func(i, j int) bool {
		return sortedParts[i].BytesOnDisk > sortedParts[j].BytesOnDisk
	})
	for _, p := range sortedParts {
		if p.BytesOnDisk > 10*1024*1024*1024 && p.Level > 5 {
			suggestions = append(suggestions, OptimizationSuggestion{
				Database:    analysis.Database,
				Table:       analysis.Table,
				Partition:   p.Partition,
				Type:        "large_fragmented",
				Severity:    "medium",
				Description: fmt.Sprintf("分区 '%s' 大小 %s，碎片层级 %d", p.Partition, formatBytes(p.BytesOnDisk), p.Level),
				Action:      "对该分区执行 OPTIMIZE FINAL",
				Impact:      "大碎片分区拖慢查询",
			})
		}
	}

	if analysis.TotalRows > 0 && analysis.AvgPartitionSize < 1024*1024 && analysis.Pattern != nil {
		pat := analysis.Pattern
		suggestions = append(suggestions, OptimizationSuggestion{
			Database:    analysis.Database,
			Table:       analysis.Table,
			Type:        "small_partitions",
			Severity:    "low",
			Description: fmt.Sprintf("当前 %s 粒度平均分区仅 %s，元数据开销过高", granularityLabel(pat.Granularity), formatBytes(analysis.AvgPartitionSize)),
			Action:      fmt.Sprintf("建议调整为 %s 粒度分区以减少元数据开销", granularityLabel(coarserGranularity(pat.Granularity))),
			Impact:      "小分区增加 ClickHouse 元数据开销，降低查询规划速度",
		})
	}

	if analysis.TotalBytes > 100*1024*1024*1024 && analysis.PartitionCount < 10 {
		suggestions = append(suggestions, OptimizationSuggestion{
			Database:    analysis.Database,
			Table:       analysis.Table,
			Type:        "insufficient_partitioning",
			Severity:    "medium",
			Description: fmt.Sprintf("大表 (%s) 仅有 %d 个分区", formatBytes(analysis.TotalBytes), analysis.PartitionCount),
			Action:      "考虑更细粒度分区以提升数据管理和TTL效率",
			Impact:      "粗粒度分区限制 TTL 精度，加大数据管理难度",
		})
	}

	return suggestions
}

func (a *Advisor) GetOptimizationSQL(analysis *TableAnalysis) []string {
	var sqls []string
	for _, s := range analysis.Suggestions {
		switch s.Type {
		case "fragmentation", "large_fragmented":
			if s.Partition != "" {
				sqls = append(sqls, fmt.Sprintf("ALTER TABLE %s.%s PARTITION '%s' OPTIMIZE FINAL;", s.Database, s.Table, s.Partition))
			} else {
				sqls = append(sqls, fmt.Sprintf("OPTIMIZE TABLE %s.%s FINAL;", s.Database, s.Table))
			}
		case "granularity_monthly":
			sqls = append(sqls, fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYYMM(date_column);", s.Database, s.Table))
		case "granularity_yearly":
			sqls = append(sqls, fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYY(date_column);", s.Database, s.Table))
		case "granularity_daily":
			sqls = append(sqls, fmt.Sprintf("ALTER TABLE %s.%s MODIFY PARTITION KEY toYYYYMMDD(date_column);", s.Database, s.Table))
		}
	}
	return sqls
}

func looksLikeDateFormat(s, layout string) bool {
	_, err := time.Parse(layout, s)
	return err == nil
}

func allDigits(s string) bool {
	for _, c := range s {
		if c < '0' || c > '9' {
			return false
		}
	}
	return true
}

func estimateTimeSpan(partitions []ch.PartitionInfo) int {
	if len(partitions) == 0 {
		return 0
	}
	var minDate, maxDate time.Time
	first := true
	now := time.Now().UTC()
	for _, p := range partitions {
		for _, layout := range []string{"20060102", "20060102", "2006-01-02", "200601", "2006-01", "2006"} {
			t, err := time.Parse(layout, p.MinDate)
			if err != nil {
				continue
			}
			if t.After(now) {
				continue
			}
			if first {
				minDate = t
				maxDate = t
				first = false
			} else {
				if t.Before(minDate) {
					minDate = t
				}
				if t.After(maxDate) {
					maxDate = t
				}
			}
			break
		}
	}
	if first {
		return 0
	}
	return int(maxDate.Sub(minDate).Hours()/24) + 1
}

func granularityLabel(g PartitionGranularity) string {
	switch g {
	case GranularityDaily:
		return "按天"
	case GranularityMonthly:
		return "按月"
	case GranularityYearly:
		return "按年"
	default:
		return string(g)
	}
}

func coarserGranularity(g PartitionGranularity) PartitionGranularity {
	switch g {
	case GranularityDaily:
		return GranularityMonthly
	case GranularityMonthly:
		return GranularityYearly
	default:
		return g
	}
}

func formatBytes(bytes uint64) string {
	if bytes == 0 {
		return "0 B"
	}
	units := []string{"B", "KB", "MB", "GB", "TB", "PB"}
	i := 0
	f := float64(bytes)
	for f >= 1024 && i < len(units)-1 {
		f /= 1024
		i++
	}
	return fmt.Sprintf("%.1f %s", f, units[i])
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

var _ = strings.TrimSpace
